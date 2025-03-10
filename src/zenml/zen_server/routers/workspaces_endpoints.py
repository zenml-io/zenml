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
"""Endpoint definitions for workspaces."""

from typing import Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    STATISTICS,
    VERSION_1,
    WORKSPACES,
)
from zenml.models import (
    Page,
    PipelineFilter,
    PipelineRunFilter,
    WorkspaceFilter,
    WorkspaceRequest,
    WorkspaceResponse,
    WorkspaceStatistics,
    WorkspaceUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.rbac.utils import (
    get_allowed_resource_ids,
)
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + WORKSPACES,
    tags=["workspaces"],
    responses={401: error_response},
)


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspaces(
    workspace_filter_model: WorkspaceFilter = Depends(
        make_dependable(WorkspaceFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[WorkspaceResponse]:
    """Lists all workspaces in the organization.

    Args:
        workspace_filter_model: Filter model used for pagination, sorting,
            filtering,
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        A list of workspaces.
    """
    return verify_permissions_and_list_entities(
        filter_model=workspace_filter_model,
        resource_type=ResourceType.WORKSPACE,
        list_method=zen_store().list_workspaces,
        hydrate=hydrate,
    )


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_workspace(
    workspace_request: WorkspaceRequest,
    _: AuthContext = Security(authorize),
) -> WorkspaceResponse:
    """Creates a workspace based on the requestBody.

    # noqa: DAR401

    Args:
        workspace_request: Workspace to create.

    Returns:
        The created workspace.
    """
    return verify_permissions_and_create_entity(
        request_model=workspace_request,
        create_method=zen_store().create_workspace,
    )


@router.get(
    "/{workspace_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_workspace(
    workspace_name_or_id: Union[str, UUID],
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> WorkspaceResponse:
    """Get a workspace for given name.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The requested workspace.
    """
    return verify_permissions_and_get_entity(
        id=workspace_name_or_id,
        get_method=zen_store().get_workspace,
        hydrate=hydrate,
    )


@router.put(
    "/{workspace_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_workspace(
    workspace_name_or_id: UUID,
    workspace_update: WorkspaceUpdate,
    _: AuthContext = Security(authorize),
) -> WorkspaceResponse:
    """Get a workspace for given name.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace to update.
        workspace_update: the workspace to use to update

    Returns:
        The updated workspace.
    """
    return verify_permissions_and_update_entity(
        id=workspace_name_or_id,
        update_model=workspace_update,
        get_method=zen_store().get_workspace,
        update_method=zen_store().update_workspace,
    )


@router.delete(
    "/{workspace_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_workspace(
    workspace_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a workspace.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
    """
    verify_permissions_and_delete_entity(
        id=workspace_name_or_id,
        get_method=zen_store().get_workspace,
        delete_method=zen_store().delete_workspace,
    )


@router.get(
    "/{workspace_name_or_id}" + STATISTICS,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_workspace_statistics(
    workspace_name_or_id: Union[str, UUID],
    auth_context: AuthContext = Security(authorize),
) -> WorkspaceStatistics:
    """Gets statistics of a workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace to get statistics for.
        auth_context: Authentication context.

    Returns:
        All pipelines within the workspace.
    """
    workspace = verify_permissions_and_get_entity(
        id=workspace_name_or_id,
        get_method=zen_store().get_workspace,
    )

    user_id = auth_context.user.id

    run_filter = PipelineRunFilter(workspace=workspace.id)
    run_filter.configure_rbac(
        authenticated_user_id=user_id,
        id=get_allowed_resource_ids(resource_type=ResourceType.PIPELINE_RUN),
    )

    pipeline_filter = PipelineFilter(workspace=workspace.id)
    pipeline_filter.configure_rbac(
        authenticated_user_id=user_id,
        id=get_allowed_resource_ids(resource_type=ResourceType.PIPELINE),
    )

    return WorkspaceStatistics(
        pipelines=zen_store().count_pipelines(filter_model=pipeline_filter),
        runs=zen_store().count_runs(filter_model=run_filter),
    )
