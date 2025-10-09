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
"""Endpoint definitions for deployments."""

from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    DEPLOYMENTS,
    VERSION_1,
)
from zenml.models import (
    DeploymentFilter,
    DeploymentRequest,
    DeploymentResponse,
    DeploymentUpdate,
    Page,
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
from zenml.zen_server.routers.projects_endpoints import workspace_router
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + DEPLOYMENTS,
    tags=["deployments"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.post(
    "/{project_name_or_id}" + DEPLOYMENTS,
    responses={401: error_response, 409: error_response, 422: error_response},
    deprecated=True,
    tags=["deployments"],
)
@async_fastapi_endpoint_wrapper
def create_deployment(
    deployment: DeploymentRequest,
    project_name_or_id: Optional[Union[str, UUID]] = None,
    _: AuthContext = Security(authorize),
) -> DeploymentResponse:
    """Create a deployment.

    Args:
        deployment: Deployment to create.
        project_name_or_id: Optional project name or ID for backwards
            compatibility.

    Returns:
        The created deployment.
    """
    if project_name_or_id:
        project = zen_store().get_project(project_name_or_id)
        deployment.project = project.id

    return verify_permissions_and_create_entity(
        request_model=deployment,
        create_method=zen_store().create_deployment,
    )


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.get(
    "/{project_name_or_id}" + DEPLOYMENTS,
    responses={401: error_response, 404: error_response, 422: error_response},
    deprecated=True,
    tags=["deployments"],
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def list_deployments(
    deployment_filter_model: DeploymentFilter = Depends(
        make_dependable(DeploymentFilter)
    ),
    project_name_or_id: Optional[Union[str, UUID]] = None,
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[DeploymentResponse]:
    """List deployments.

    Args:
        deployment_filter_model: Filter model used for pagination, sorting, and
            filtering.
        project_name_or_id: Optional project name or ID for backwards
            compatibility.
        hydrate: Whether to hydrate the returned models.

    Returns:
        A page of deployments matching the filter.
    """
    if project_name_or_id:
        deployment_filter_model.project = project_name_or_id

    return verify_permissions_and_list_entities(
        filter_model=deployment_filter_model,
        resource_type=ResourceType.DEPLOYMENT,
        list_method=zen_store().list_deployments,
        hydrate=hydrate,
    )


@router.get(
    "/{deployment_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def get_deployment(
    deployment_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> DeploymentResponse:
    """Get a deployment by ID.

    Args:
        deployment_id: The deployment ID.
        hydrate: Whether to hydrate the returned model.

    Returns:
        The requested deployment.
    """
    return verify_permissions_and_get_entity(
        id=deployment_id,
        get_method=zen_store().get_deployment,
        hydrate=hydrate,
    )


@router.put(
    "/{deployment_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def update_deployment(
    deployment_id: UUID,
    deployment_update: DeploymentUpdate,
    _: AuthContext = Security(authorize),
) -> DeploymentResponse:
    """Update a deployment.

    Args:
        deployment_id: The deployment ID.
        deployment_update: The updates to apply.

    Returns:
        The updated deployment.
    """
    return verify_permissions_and_update_entity(
        id=deployment_id,
        update_model=deployment_update,
        get_method=zen_store().get_deployment,
        update_method=zen_store().update_deployment,
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
    """Delete a deployment.

    Args:
        deployment_id: The deployment ID.
    """
    verify_permissions_and_delete_entity(
        id=deployment_id,
        get_method=zen_store().get_deployment,
        delete_method=zen_store().delete_deployment,
    )
