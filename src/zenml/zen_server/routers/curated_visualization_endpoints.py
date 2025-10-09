"""REST API endpoints for curated visualizations."""

from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, CURATED_VISUALIZATIONS, VERSION_1
from zenml.models import (
    CuratedVisualizationFilter,
    CuratedVisualizationRequest,
    CuratedVisualizationResponse,
    CuratedVisualizationUpdate,
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
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import (
    batch_verify_permissions_for_models,
    dehydrate_page,
)
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + CURATED_VISUALIZATIONS,
    tags=["curated_visualizations"],
    responses={401: error_response, 404: error_response, 422: error_response},
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
    return verify_permissions_and_create_entity(
        request_model=visualization,
        create_method=zen_store().create_curated_visualization,
    )


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def list_curated_visualizations(
    visualization_filter_model: CuratedVisualizationFilter = Depends(
        make_dependable(CuratedVisualizationFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[CuratedVisualizationResponse]:
    """List curated visualizations.

    Args:
        visualization_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        A page of curated visualizations.
    """
    resource_type = None
    if visualization_filter_model.resource_type:
        resource_type = ResourceType.from_visualization_type(
            visualization_filter_model.resource_type
        )

    if resource_type is None:
        # No concrete resource type - call zen store directly and batch verify permissions
        page = zen_store().list_curated_visualizations(
            filter_model=visualization_filter_model,
            hydrate=hydrate,
        )
        batch_verify_permissions_for_models(page.items, action=Action.READ)
        return dehydrate_page(page)
    else:
        # Concrete resource type available - use standard RBAC flow
        return verify_permissions_and_list_entities(
            filter_model=visualization_filter_model,
            resource_type=resource_type,
            list_method=zen_store().list_curated_visualizations,
            hydrate=hydrate,
        )


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
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The curated visualization with the given ID.
    """
    return verify_permissions_and_get_entity(
        id=visualization_id,
        get_method=zen_store().get_curated_visualization,
        hydrate=hydrate,
    )


@router.patch(
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
    return verify_permissions_and_update_entity(
        id=visualization_id,
        update_model=visualization_update,
        get_method=zen_store().get_curated_visualization,
        update_method=zen_store().update_curated_visualization,
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
    verify_permissions_and_delete_entity(
        id=visualization_id,
        get_method=zen_store().get_curated_visualization,
        delete_method=zen_store().delete_curated_visualization,
    )
