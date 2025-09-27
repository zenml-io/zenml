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

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Security,
)

from zenml.constants import (
    API,
    DEPLOYMENT_VISUALIZATIONS,
    DEPLOYMENTS,
    VERSION_1,
)
from zenml.models import (
    DeploymentFilter,
    DeploymentRequest,
    DeploymentResponse,
    DeploymentUpdate,
    DeploymentVisualizationFilter,
    DeploymentVisualizationRequest,
    DeploymentVisualizationResponse,
    DeploymentVisualizationUpdate,
)
from zenml.models.v2.base.page import Page
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

deployment_visualization_router = APIRouter(
    prefix=API + VERSION_1 + DEPLOYMENT_VISUALIZATIONS,
    tags=["deployment_visualizations"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_deployment(
    deployment: DeploymentRequest,
    _: AuthContext = Security(authorize),
) -> DeploymentResponse:
    """Creates a deployment.

    Args:
        deployment: Deployment to create.

    Returns:
        The created deployment.
    """
    return verify_permissions_and_create_entity(
        request_model=deployment,
        create_method=zen_store().create_deployment,
    )


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def list_deployments(
    deployment_filter_model: DeploymentFilter = Depends(
        make_dependable(DeploymentFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[DeploymentResponse]:
    """Gets a list of deployments.

    Args:
        deployment_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        List of deployment objects matching the filter criteria.
    """
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
    """Gets a specific deployment using its unique id.

    Args:
        deployment_id: ID of the deployment to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        A specific deployment object.
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
    """Updates a specific deployment.

    Args:
        deployment_id: ID of the deployment to update.
        deployment_update: Update model for the deployment.

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
    """Deletes a specific deployment.

    Args:
        deployment_id: ID of the deployment to delete.
    """
    verify_permissions_and_delete_entity(
        id=deployment_id,
        get_method=zen_store().get_deployment,
        delete_method=zen_store().delete_deployment,
    )


@router.post(
    "/{deployment_id}/visualizations",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_deployment_visualization(
    visualization: DeploymentVisualizationRequest,
    _: AuthContext = Security(authorize),
) -> DeploymentVisualizationResponse:
    """Creates a curated deployment visualization.

    Args:
        deployment_id: ID of the deployment to add visualization to.
        visualization: Deployment visualization to create.

    Returns:
        The created deployment visualization.
    """
    return verify_permissions_and_create_entity(
        request_model=visualization,
        create_method=zen_store().create_deployment_visualization,
    )


@router.get(
    "/{deployment_id}/visualizations",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def list_deployment_visualizations(
    deployment_id: UUID,
    visualization_filter_model: DeploymentVisualizationFilter = Depends(
        make_dependable(DeploymentVisualizationFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[DeploymentVisualizationResponse]:
    """Gets a list of visualizations for a specific deployment.

    Args:
        deployment_id: ID of the deployment to list visualizations for.
        visualization_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        List of deployment visualization objects for the deployment.
    """
    visualization_filter_model.deployment = deployment_id
    return verify_permissions_and_list_entities(
        filter_model=visualization_filter_model,
        resource_type=ResourceType.DEPLOYMENT,
        list_method=zen_store().list_deployment_visualizations,
        hydrate=hydrate,
    )


@deployment_visualization_router.get(
    "/{deployment_visualization_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def get_deployment_visualization(
    deployment_visualization_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> DeploymentVisualizationResponse:
    """Gets a specific deployment visualization using its unique id.

    Args:
        deployment_visualization_id: ID of the deployment visualization to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        A specific deployment visualization object.
    """
    return verify_permissions_and_get_entity(
        id=deployment_visualization_id,
        get_method=zen_store().get_deployment_visualization,
        hydrate=hydrate,
    )


@deployment_visualization_router.patch(
    "/{deployment_visualization_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def update_deployment_visualization(
    deployment_visualization_id: UUID,
    visualization_update: DeploymentVisualizationUpdate,
    _: AuthContext = Security(authorize),
) -> DeploymentVisualizationResponse:
    """Updates a specific deployment visualization.

    Args:
        deployment_visualization_id: ID of the deployment visualization to update.
        visualization_update: Update model for the deployment visualization.

    Returns:
        The updated deployment visualization.
    """
    return verify_permissions_and_update_entity(
        id=deployment_visualization_id,
        update_model=visualization_update,
        get_method=zen_store().get_deployment_visualization,
        update_method=zen_store().update_deployment_visualization,
    )


@deployment_visualization_router.delete(
    "/{deployment_visualization_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_deployment_visualization(
    deployment_visualization_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a specific deployment visualization.

    Args:
        deployment_visualization_id: ID of the deployment visualization to delete.
    """
    verify_permissions_and_delete_entity(
        id=deployment_visualization_id,
        get_method=zen_store().get_deployment_visualization,
        delete_method=zen_store().delete_deployment_visualization,
    )
