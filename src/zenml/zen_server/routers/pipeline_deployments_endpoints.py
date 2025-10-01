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

from zenml.constants import (
    API,
    PIPELINE_DEPLOYMENTS,
    VERSION_1,
)
from zenml.models import (
    PipelineSnapshotFilter,
    PipelineSnapshotRequest,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
)
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.routers.projects_endpoints import workspace_router
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
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

    Returns:
        A specific deployment object.
    """
    deployment = verify_permissions_and_get_entity(
        id=deployment_id,
        get_method=zen_store().get_snapshot,
        hydrate=hydrate,
        step_configuration_filter=step_configuration_filter,
    )

    exclude = None
    if _should_remove_step_config_overrides(request):
        exclude = {
            "metadata": {
                "step_configurations": {"__all__": {"step_config_overrides"}}
            }
        }

    return deployment.model_dump(mode="json", exclude=exclude)


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
