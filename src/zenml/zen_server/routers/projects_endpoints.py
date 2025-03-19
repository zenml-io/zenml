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
"""Endpoint definitions for projects."""

from typing import Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    PROJECTS,
    STATISTICS,
    VERSION_1,
    WORKSPACES,
)
from zenml.models import (
    Page,
    PipelineFilter,
    PipelineRunFilter,
    ProjectFilter,
    ProjectRequest,
    ProjectResponse,
    ProjectStatistics,
    ProjectUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.feature_gate.endpoint_utils import (
    report_decrement,
)
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
    server_config,
    zen_store,
)

workspace_router = APIRouter(
    prefix=API + VERSION_1 + WORKSPACES,
    tags=["workspaces"],
    responses={401: error_response},
)

router = APIRouter(
    prefix=API + VERSION_1 + PROJECTS,
    tags=["projects"],
    responses={401: error_response},
)


# TODO: kept for backwards compatibility only; to be removed after the migration
@workspace_router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
    deprecated=True,
)
@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_projects(
    project_filter_model: ProjectFilter = Depends(
        make_dependable(ProjectFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[ProjectResponse]:
    """Lists all projects in the organization.

    Args:
        project_filter_model: Filter model used for pagination, sorting,
            filtering,
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        A list of projects.
    """
    return verify_permissions_and_list_entities(
        filter_model=project_filter_model,
        resource_type=ResourceType.PROJECT,
        list_method=zen_store().list_projects,
        hydrate=hydrate,
    )


# TODO: kept for backwards compatibility only; to be removed after the migration
@workspace_router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
    deprecated=True,
)
@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_project(
    project_request: ProjectRequest,
    _: AuthContext = Security(authorize),
) -> ProjectResponse:
    """Creates a project based on the requestBody.

    # noqa: DAR401

    Args:
        project_request: Project to create.

    Returns:
        The created project.
    """
    return verify_permissions_and_create_entity(
        request_model=project_request,
        create_method=zen_store().create_project,
    )


# TODO: kept for backwards compatibility only; to be removed after the migration
@workspace_router.get(
    "/{project_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
    deprecated=True,
)
@router.get(
    "/{project_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_project(
    project_name_or_id: Union[str, UUID],
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> ProjectResponse:
    """Get a project for given name.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The requested project.
    """
    return verify_permissions_and_get_entity(
        id=project_name_or_id,
        get_method=zen_store().get_project,
        hydrate=hydrate,
    )


# TODO: kept for backwards compatibility only; to be removed after the migration
@workspace_router.put(
    "/{project_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
    deprecated=True,
)
@router.put(
    "/{project_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_project(
    project_name_or_id: UUID,
    project_update: ProjectUpdate,
    _: AuthContext = Security(authorize),
) -> ProjectResponse:
    """Get a project for given name.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project to update.
        project_update: the project to use to update

    Returns:
        The updated project.
    """
    return verify_permissions_and_update_entity(
        id=project_name_or_id,
        update_model=project_update,
        get_method=zen_store().get_project,
        update_method=zen_store().update_project,
    )


# TODO: kept for backwards compatibility only; to be removed after the migration
@workspace_router.delete(
    "/{project_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
    deprecated=True,
)
@router.delete(
    "/{project_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_project(
    project_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a project.

    Args:
        project_name_or_id: Name or ID of the project.
    """
    project = verify_permissions_and_delete_entity(
        id=project_name_or_id,
        get_method=zen_store().get_project,
        delete_method=zen_store().delete_project,
    )
    if server_config().feature_gate_enabled:
        if ResourceType.PROJECT in server_config().reportable_resources:
            report_decrement(ResourceType.PROJECT, resource_id=project.id)


# TODO: kept for backwards compatibility only; to be removed after the migration
@workspace_router.get(
    "/{project_name_or_id}" + STATISTICS,
    responses={401: error_response, 404: error_response, 422: error_response},
    deprecated=True,
)
@router.get(
    "/{project_name_or_id}" + STATISTICS,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_project_statistics(
    project_name_or_id: Union[str, UUID],
    auth_context: AuthContext = Security(authorize),
) -> ProjectStatistics:
    """Gets statistics of a project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project to get statistics for.
        auth_context: Authentication context.

    Returns:
        Project statistics.
    """
    project = verify_permissions_and_get_entity(
        id=project_name_or_id,
        get_method=zen_store().get_project,
    )

    user_id = auth_context.user.id

    run_filter = PipelineRunFilter(project=project.id)
    run_filter.configure_rbac(
        authenticated_user_id=user_id,
        id=get_allowed_resource_ids(
            resource_type=ResourceType.PIPELINE_RUN, project_id=project.id
        ),
    )

    pipeline_filter = PipelineFilter(project=project.id)
    pipeline_filter.configure_rbac(
        authenticated_user_id=user_id,
        id=get_allowed_resource_ids(
            resource_type=ResourceType.PIPELINE, project_id=project.id
        ),
    )

    return ProjectStatistics(
        pipelines=zen_store().count_pipelines(filter_model=pipeline_filter),
        runs=zen_store().count_runs(filter_model=run_filter),
    )
