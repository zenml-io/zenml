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

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Security

from zenml.constants import (
    API,
    PIPELINE_ENDPOINTS,
    VERSION_1,
)
from zenml.models import (
    PipelineEndpointFilter,
    PipelineEndpointRequest,
    PipelineEndpointResponse,
    PipelineEndpointUpdate,
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
    prefix=API + VERSION_1 + PIPELINE_ENDPOINTS,
    tags=["pipeline endpoints"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_pipeline_endpoint(
    request: Request,
    endpoint: PipelineEndpointRequest,
    _: AuthContext = Security(authorize),
) -> PipelineEndpointResponse:
    """Creates a pipeline endpoint.

    Args:
        request: The request object.
        endpoint: Endpoint to create.
        project_name_or_id: Optional name or ID of the project.

    Returns:
        The created deployment.
    """
    return verify_permissions_and_create_entity(
        request_model=endpoint,
        create_method=zen_store().create_pipeline_endpoint,
    )


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def list_pipeline_endpoints(
    request: Request,
    endpoint_filter_model: PipelineEndpointFilter = Depends(
        make_dependable(PipelineEndpointFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[PipelineEndpointResponse]:
    """Gets a list of pipeline endpoints.

    Args:
        request: The request object.
        endpoint_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        List of pipeline endpoint objects matching the filter criteria.
    """
    return verify_permissions_and_list_entities(
        filter_model=endpoint_filter_model,
        resource_type=ResourceType.PIPELINE_ENDPOINT,
        list_method=zen_store().list_pipeline_endpoints,
        hydrate=hydrate,
    )


@router.get(
    "/{endpoint_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def get_pipeline_endpoint(
    endpoint_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> PipelineEndpointResponse:
    """Gets a specific pipeline endpoint using its unique id.

    Args:
        request: The request object.
        endpoint_id: ID of the pipeline endpoint to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        A specific deployment object.
    """
    return verify_permissions_and_get_entity(
        id=endpoint_id,
        get_method=zen_store().get_pipeline_endpoint,
        hydrate=hydrate,
    )


@router.put(
    "/{endpoint_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def update_pipeline_endpoint(
    endpoint_id: UUID,
    endpoint_update: PipelineEndpointUpdate,
    _: AuthContext = Security(authorize),
) -> PipelineEndpointResponse:
    """Updates a specific pipeline endpoint.

    Args:
        endpoint_id: ID of the pipeline endpoint to update.
        endpoint_update: Update model for the pipeline endpoint.

    Returns:
        The updated pipeline endpoint.
    """
    return verify_permissions_and_update_entity(
        id=endpoint_id,
        update_model=endpoint_update,
        get_method=zen_store().get_pipeline_endpoint,
        update_method=zen_store().update_pipeline_endpoint,
    )


@router.delete(
    "/{endpoint_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_pipeline_endpoint(
    endpoint_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a specific pipeline endpoint.

    Args:
        endpoint_id: ID of the pipeline endpoint to delete.
    """
    verify_permissions_and_delete_entity(
        id=endpoint_id,
        get_method=zen_store().get_pipeline_endpoint,
        delete_method=zen_store().delete_pipeline_endpoint,
    )
