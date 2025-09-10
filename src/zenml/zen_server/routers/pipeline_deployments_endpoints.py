#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Endpoint definitions for deployments."""

from typing import Any, List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Security

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_handler
from zenml.constants import (
    API,
    PIPELINE_DEPLOYMENTS,
    RUN_TEMPLATE_TRIGGERS_FEATURE_NAME,
    VERSION_1,
)
from zenml.logging.step_logging import fetch_logs
from zenml.models import (
    PipelineRunFilter,
    PipelineRunResponse,
    PipelineSnapshotFilter,
    PipelineSnapshotRequest,
    PipelineSnapshotTriggerRequest,
    PipelineSnapshotUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.feature_gate.endpoint_utils import (
    check_entitlement,
)
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import verify_permission
from zenml.zen_server.routers.projects_endpoints import workspace_router
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    server_config,
    workload_manager,
    zen_store,
)


# TODO: Remove this as soon as there is only a low number of users running
# versions < 0.82.0. Also change back the return type to
# `PipelineDeploymentResponse` once we have removed the `exclude` logic.
def _should_remove_step_config_overrides(
    request: Request,
) -> bool:
    """Check if the step config overrides should be removed from the response.

    Args:
        request: The request object.

    Returns:
        If the step config overrides should be removed from the response.
    """
    from packaging import version

    user_agent = request.headers.get("User-Agent", "")

    if not user_agent.startswith("zenml/"):
        # This request is not coming from a ZenML client
        return False

    client_version = version.parse(user_agent.removeprefix("zenml/"))

    # Versions before 0.82.0 did have `extra="forbid"` in the pydantic model
    # that stores the step configurations. This means it would crash if we
    # included the `step_config_overrides` in the response.
    return client_version < version.parse("0.82.0")


router = APIRouter(
    prefix=API + VERSION_1 + PIPELINE_DEPLOYMENTS,
    tags=["deployments"],
    responses={401: error_response, 403: error_response},
    deprecated=True,
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.post(
    "/{project_name_or_id}" + PIPELINE_DEPLOYMENTS,
    responses={401: error_response, 409: error_response, 422: error_response},
    deprecated=True,
    tags=["deployments"],
)
@async_fastapi_endpoint_wrapper
def create_deployment(
    request: Request,
    deployment: PipelineSnapshotRequest,
    project_name_or_id: Optional[Union[str, UUID]] = None,
    _: AuthContext = Security(authorize),
) -> Any:
    """Creates a deployment.

    Args:
        request: The request object.
        deployment: Deployment to create.
        project_name_or_id: Optional name or ID of the project.

    Returns:
        The created deployment.
    """
    if project_name_or_id:
        project = zen_store().get_project(project_name_or_id)
        deployment.project = project.id

    deployment_response = verify_permissions_and_create_entity(
        request_model=deployment,
        create_method=zen_store().create_snapshot,
    )

    exclude = None
    if _should_remove_step_config_overrides(request):
        exclude = {
            "metadata": {
                "step_configurations": {"__all__": {"step_config_overrides"}}
            }
        }

    return deployment_response.model_dump(mode="json", exclude=exclude)


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.get(
    "/{project_name_or_id}" + PIPELINE_DEPLOYMENTS,
    responses={401: error_response, 404: error_response, 422: error_response},
    deprecated=True,
    tags=["deployments"],
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def list_deployments(
    request: Request,
    deployment_filter_model: PipelineSnapshotFilter = Depends(
        make_dependable(PipelineSnapshotFilter)
    ),
    project_name_or_id: Optional[Union[str, UUID]] = None,
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Any:
    """Gets a list of deployments.

    Args:
        request: The request object.
        deployment_filter_model: Filter model used for pagination, sorting,
            filtering.
        project_name_or_id: Optional name or ID of the project to filter by.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        List of deployment objects matching the filter criteria.
    """
    if project_name_or_id:
        deployment_filter_model.project = project_name_or_id

    page = verify_permissions_and_list_entities(
        filter_model=deployment_filter_model,
        resource_type=ResourceType.PIPELINE_SNAPSHOT,
        list_method=zen_store().list_snapshots,
        hydrate=hydrate,
    )

    exclude = None
    if _should_remove_step_config_overrides(request):
        exclude = {
            "items": {
                "__all__": {
                    "metadata": {
                        "step_configurations": {
                            "__all__": {"step_config_overrides"}
                        }
                    }
                }
            }
        }

    return page.model_dump(mode="json", exclude=exclude)


@router.get(
    "/{deployment_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def get_deployment(
    request: Request,
    deployment_id: UUID,
    hydrate: bool = True,
    step_configuration_filter: Optional[List[str]] = Query(None),
    include_config_schema: Optional[bool] = None,
    _: AuthContext = Security(authorize),
) -> Any:
    """Gets a specific deployment using its unique id.

    Args:
        request: The request object.
        deployment_id: ID of the deployment to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.
        step_configuration_filter: List of step configurations to include in
            the response. If not given, all step configurations will be
            included.
        include_config_schema: Whether the config schema will be filled.

    Returns:
        A specific deployment object.
    """
    deployment = verify_permissions_and_get_entity(
        id=deployment_id,
        get_method=zen_store().get_snapshot,
        hydrate=hydrate,
        step_configuration_filter=step_configuration_filter,
        include_config_schema=include_config_schema,
    )

    exclude = None
    if _should_remove_step_config_overrides(request):
        exclude = {
            "metadata": {
                "step_configurations": {"__all__": {"step_config_overrides"}}
            }
        }

    return deployment.model_dump(mode="json", exclude=exclude)


@router.put(
    "/{deployment_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_deployment(
    deployment_id: UUID,
    deployment_update: PipelineSnapshotUpdate,
    _: AuthContext = Security(authorize),
) -> Any:
    """Update a deployment.

    Args:
        deployment_id: ID of the deployment to update.
        deployment_update: The update to apply.

    Returns:
        The updated deployment.
    """
    return verify_permissions_and_update_entity(
        id=deployment_id,
        update_model=deployment_update,
        get_method=zen_store().get_snapshot,
        update_method=zen_store().update_snapshot,
    )


@router.delete(
    "/{deployment_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_deployment(
    deployment_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a specific deployment.

    Args:
        deployment_id: ID of the deployment to delete.
    """
    verify_permissions_and_delete_entity(
        id=deployment_id,
        get_method=zen_store().get_snapshot,
        delete_method=zen_store().delete_snapshot,
    )


@router.get(
    "/{deployment_id}/logs",
    responses={
        401: error_response,
        404: error_response,
        422: error_response,
    },
)
@async_fastapi_endpoint_wrapper
def deployment_logs(
    deployment_id: UUID,
    offset: int = 0,
    length: int = 1024 * 1024 * 16,  # Default to 16MiB of data
    _: AuthContext = Security(authorize),
) -> str:
    """Get deployment logs.

    Args:
        deployment_id: ID of the deployment.
        offset: The offset from which to start reading.
        length: The amount of bytes that should be read.

    Returns:
        The deployment logs.

    Raises:
        KeyError: If no logs are available for the deployment.
    """
    store = zen_store()

    deployment = verify_permissions_and_get_entity(
        id=deployment_id,
        get_method=store.get_snapshot,
        hydrate=True,
    )

    if (
        deployment.source_snapshot_id
        and server_config().workload_manager_enabled
    ):
        return workload_manager().get_logs(workload_id=deployment.id)

    # Get the last pipeline run for this deployment
    pipeline_runs = store.list_runs(
        runs_filter_model=PipelineRunFilter(
            project=deployment.project_id,
            sort_by="asc:created",
            size=1,
            deployment_id=deployment.id,
        )
    )

    if len(pipeline_runs.items) == 0:
        return ""

    run = pipeline_runs.items[0]

    logs = run.logs
    if logs is None:
        raise KeyError("No logs available for this deployment")

    return fetch_logs(
        zen_store=store,
        artifact_store_id=logs.artifact_store_id,
        logs_uri=logs.uri,
        offset=offset,
        length=length,
    )


if server_config().workload_manager_enabled:

    @router.post(
        "/{deployment_id}/runs",
        responses={
            401: error_response,
            404: error_response,
            422: error_response,
            429: error_response,
        },
    )
    @async_fastapi_endpoint_wrapper
    def create_deployment_run(
        deployment_id: UUID,
        trigger_request: PipelineSnapshotTriggerRequest,
        auth_context: AuthContext = Security(authorize),
    ) -> PipelineRunResponse:
        """Run a pipeline from a deployment.

        Args:
            deployment_id: The ID of the deployment.
            trigger_request: Trigger request.
            auth_context: Authentication context.

        Returns:
            The created pipeline run.
        """
        from zenml.zen_server.pipeline_execution.utils import (
            trigger_snapshot,
        )

        with track_handler(
            event=AnalyticsEvent.EXECUTED_SNAPSHOT,
        ) as analytics_handler:
            snapshot = verify_permissions_and_get_entity(
                id=deployment_id,
                get_method=zen_store().get_snapshot,
                hydrate=True,
            )
            analytics_handler.metadata = {
                "project_id": snapshot.project_id,
            }

            verify_permission(
                resource_type=ResourceType.PIPELINE_SNAPSHOT,
                action=Action.CREATE,
                project_id=snapshot.project_id,
            )
            verify_permission(
                resource_type=ResourceType.PIPELINE_RUN,
                action=Action.CREATE,
                project_id=snapshot.project_id,
            )

            check_entitlement(feature=RUN_TEMPLATE_TRIGGERS_FEATURE_NAME)

            return trigger_snapshot(
                snapshot=snapshot,
                auth_context=auth_context,
                trigger_request=trigger_request,
            )
