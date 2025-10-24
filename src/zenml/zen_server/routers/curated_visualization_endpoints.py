"""REST API endpoints for curated visualizations."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Security

from zenml.constants import API, CURATED_VISUALIZATIONS, VERSION_1
from zenml.enums import VisualizationResourceTypes
from zenml.models import (
    CuratedVisualizationRequest,
    CuratedVisualizationResponse,
    CuratedVisualizationUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.rbac.utils import verify_permission_for_model
from zenml.zen_server.utils import async_fastapi_endpoint_wrapper, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + CURATED_VISUALIZATIONS,
    tags=["curated_visualizations"],
    responses={401: error_response, 404: error_response, 422: error_response},
)


def _get_resource_model(
    resource_type: VisualizationResourceTypes,
    resource_id: UUID,
) -> Any:
    """Fetch the concrete resource model for a curated visualization.

    Args:
        resource_type: The type of resource linked to the curated visualization.
        resource_id: The unique identifier of the linked resource.

    Returns:
        The hydrated resource model retrieved from the Zen store.

    Raises:
        RuntimeError: If the provided resource type is not supported.
    """
    store = zen_store()

    if resource_type == VisualizationResourceTypes.DEPLOYMENT:
        return store.get_deployment(resource_id)
    if resource_type == VisualizationResourceTypes.MODEL:
        return store.get_model(resource_id)
    if resource_type == VisualizationResourceTypes.PIPELINE:
        return store.get_pipeline(resource_id)
    if resource_type == VisualizationResourceTypes.PIPELINE_RUN:
        return store.get_run(resource_id)
    if resource_type == VisualizationResourceTypes.PIPELINE_SNAPSHOT:
        return store.get_snapshot(resource_id)
    if resource_type == VisualizationResourceTypes.PROJECT:
        return store.get_project(resource_id)

    raise RuntimeError(
        f"Unsupported curated visualization resource type: {resource_type}"
    )


@router.post(
    "",
    responses={
        401: error_response,
        404: error_response,
        409: error_response,
        422: error_response,
    },
)
@async_fastapi_endpoint_wrapper
def create_curated_visualization(
    visualization: CuratedVisualizationRequest,
    _: AuthContext = Security(authorize),
) -> CuratedVisualizationResponse:
    """Create a curated visualization.

    Args:
        visualization: The curated visualization to create.

    Returns:
        The created curated visualization.
    """
    store = zen_store()
    resource_model = _get_resource_model(
        visualization.resource_type, visualization.resource_id
    )
    artifact_visualization = store.get_artifact_visualization(
        visualization.artifact_visualization_id
    )

    verify_permission_for_model(resource_model, action=Action.UPDATE)
    verify_permission_for_model(artifact_visualization, action=Action.READ)

    return store.create_curated_visualization(visualization)


@router.get(
    "/{visualization_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def get_curated_visualization(
    visualization_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> CuratedVisualizationResponse:
    """Retrieve a curated visualization by ID.

    Args:
        visualization_id: The ID of the curated visualization to retrieve.
        hydrate: Flag deciding whether to return the hydrated model.

    Returns:
        The curated visualization with the given ID.
    """
    store = zen_store()
    hydrated_visualization = store.get_curated_visualization(
        visualization_id, hydrate=hydrate
    )
    resource_type = hydrated_visualization.resource_type
    resource_id = hydrated_visualization.resource_id

    resource_model = _get_resource_model(resource_type, resource_id)
    verify_permission_for_model(resource_model, action=Action.READ)

    return hydrated_visualization


@router.put(
    "/{visualization_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def update_curated_visualization(
    visualization_id: UUID,
    visualization_update: CuratedVisualizationUpdate,
    _: AuthContext = Security(authorize),
) -> CuratedVisualizationResponse:
    """Update a curated visualization.

    Args:
        visualization_id: The ID of the curated visualization to update.
        visualization_update: The update to apply to the curated visualization.

    Returns:
        The updated curated visualization.
    """
    store = zen_store()
    existing_visualization = store.get_curated_visualization(
        visualization_id, hydrate=True
    )
    resource_type = existing_visualization.resource_type
    resource_id = existing_visualization.resource_id

    resource_model = _get_resource_model(resource_type, resource_id)
    verify_permission_for_model(resource_model, action=Action.UPDATE)

    return store.update_curated_visualization(
        visualization_id, visualization_update
    )


@router.delete(
    "/{visualization_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_curated_visualization(
    visualization_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Delete a curated visualization.

    Args:
        visualization_id: The ID of the curated visualization to delete.
    """
    store = zen_store()
    existing_visualization = store.get_curated_visualization(
        visualization_id, hydrate=True
    )
    resource_type = existing_visualization.resource_type
    resource_id = existing_visualization.resource_id

    resource_model = _get_resource_model(resource_type, resource_id)
    verify_permission_for_model(resource_model, action=Action.UPDATE)

    store.delete_curated_visualization(visualization_id)
