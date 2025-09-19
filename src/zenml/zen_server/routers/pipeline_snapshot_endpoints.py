#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Endpoint definitions for pipeline snapshots."""

from typing import Any, List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Security

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_handler
from zenml.constants import (
    API,
    PIPELINE_SNAPSHOTS,
    RUN_TEMPLATE_TRIGGERS_FEATURE_NAME,
    VERSION_1,
)
from zenml.models import (
    Page,
    PipelineRunResponse,
    PipelineSnapshotFilter,
    PipelineSnapshotRequest,
    PipelineSnapshotResponse,
    PipelineSnapshotRunRequest,
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
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    server_config,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + PIPELINE_SNAPSHOTS,
    tags=["snapshots"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_pipeline_snapshot(
    snapshot: PipelineSnapshotRequest,
    project_name_or_id: Optional[Union[str, UUID]] = None,
    _: AuthContext = Security(authorize),
) -> PipelineSnapshotResponse:
    """Creates a snapshot.

    Args:
        snapshot: Snapshot to create.
        project_name_or_id: Optional name or ID of the project.

    Returns:
        The created snapshot.
    """
    if project_name_or_id:
        project = zen_store().get_project(project_name_or_id)
        snapshot.project = project.id

    return verify_permissions_and_create_entity(
        request_model=snapshot,
        create_method=zen_store().create_snapshot,
    )


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def list_pipeline_snapshots(
    snapshot_filter_model: PipelineSnapshotFilter = Depends(
        make_dependable(PipelineSnapshotFilter)
    ),
    project_name_or_id: Optional[Union[str, UUID]] = None,
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[PipelineSnapshotResponse]:
    """Gets a list of snapshots.

    Args:
        snapshot_filter_model: Filter model used for pagination, sorting,
            filtering.
        project_name_or_id: Optional name or ID of the project to filter by.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        List of snapshot objects matching the filter criteria.
    """
    if project_name_or_id:
        snapshot_filter_model.project = project_name_or_id

    return verify_permissions_and_list_entities(
        filter_model=snapshot_filter_model,
        resource_type=ResourceType.PIPELINE_SNAPSHOT,
        list_method=zen_store().list_snapshots,
        hydrate=hydrate,
    )


@router.get(
    "/{snapshot_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def get_pipeline_snapshot(
    snapshot_id: UUID,
    hydrate: bool = True,
    step_configuration_filter: Optional[List[str]] = Query(None),
    include_config_schema: Optional[bool] = None,
    _: AuthContext = Security(authorize),
) -> PipelineSnapshotResponse:
    """Gets a specific snapshot using its unique id.

    Args:
        snapshot_id: ID of the snapshot to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.
        step_configuration_filter: List of step configurations to include in
            the response. If not given, all step configurations will be
            included.
        include_config_schema: Whether the config schema will be filled.

    Returns:
        A specific snapshot object.
    """
    return verify_permissions_and_get_entity(
        id=snapshot_id,
        get_method=zen_store().get_snapshot,
        hydrate=hydrate,
        step_configuration_filter=step_configuration_filter,
        include_config_schema=include_config_schema,
    )


@router.put(
    "/{snapshot_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_pipeline_snapshot(
    snapshot_id: UUID,
    snapshot_update: PipelineSnapshotUpdate,
    _: AuthContext = Security(authorize),
) -> Any:
    """Update a snapshot.

    Args:
        snapshot_id: ID of the snapshot to update.
        snapshot_update: The update to apply.

    Returns:
        The updated snapshot.
    """
    return verify_permissions_and_update_entity(
        id=snapshot_id,
        update_model=snapshot_update,
        get_method=zen_store().get_snapshot,
        update_method=zen_store().update_snapshot,
    )


@router.delete(
    "/{snapshot_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_pipeline_snapshot(
    snapshot_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a specific snapshot.

    Args:
        snapshot_id: ID of the snapshot to delete.
    """
    verify_permissions_and_delete_entity(
        id=snapshot_id,
        get_method=zen_store().get_snapshot,
        delete_method=zen_store().delete_snapshot,
    )


if server_config().workload_manager_enabled:

    @router.post(
        "/{snapshot_id}/runs",
        responses={
            401: error_response,
            404: error_response,
            422: error_response,
            429: error_response,
        },
    )
    @async_fastapi_endpoint_wrapper
    def create_snapshot_run(
        snapshot_id: UUID,
        run_request: PipelineSnapshotRunRequest,
        auth_context: AuthContext = Security(authorize),
    ) -> PipelineRunResponse:
        """Run a pipeline from a snapshot.

        Args:
            snapshot_id: The ID of the snapshot.
            run_request: Run request.
            auth_context: Authentication context.

        Returns:
            The created pipeline run.
        """
        from zenml.zen_server.pipeline_execution.utils import (
            run_snapshot,
        )

        with track_handler(
            event=AnalyticsEvent.EXECUTED_SNAPSHOT,
        ) as analytics_handler:
            snapshot = verify_permissions_and_get_entity(
                id=snapshot_id,
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

            return run_snapshot(
                snapshot=snapshot,
                auth_context=auth_context,
                request=run_request,
            )
