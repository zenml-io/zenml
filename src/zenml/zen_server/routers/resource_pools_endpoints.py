#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Endpoint definitions for resource pools."""

from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, RESOURCE_POOLS, VERSION_1
from zenml.models import (
    Page,
    ResourcePoolFilter,
    ResourcePoolRequest,
    ResourcePoolResponse,
    ResourcePoolUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + RESOURCE_POOLS,
    tags=["resource_pools"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_resource_pool(
    resource_pool: ResourcePoolRequest,
    _: AuthContext = Security(authorize),
) -> ResourcePoolResponse:
    """Creates a resource pool.

    Args:
        resource_pool: Resource pool to register.
    """
    return zen_store().create_resource_pool(resource_pool=resource_pool)
    # return verify_permissions_and_create_entity(
    #     request_model=resource_pool,
    #     create_method=zen_store().create_resource_pool,
    # )


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_resource_pools(
    resource_pool_filter_model: ResourcePoolFilter = Depends(
        make_dependable(ResourcePoolFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[ResourcePoolResponse]:
    """Get a list of all resource pools.

    Args:
        resource_pool_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        List of resource pools matching the filter criteria.
    """
    return zen_store().list_resource_pools(
        filter_model=resource_pool_filter_model,
        hydrate=hydrate,
    )
    # return verify_permissions_and_list_entities(
    #     filter_model=resource_pool_filter_model,
    #     resource_type=ResourceType.RESOURCE_POOL,
    #     list_method=zen_store().list_resource_pools,
    #     hydrate=hydrate,
    # )


@router.get(
    "/{resource_pool_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_resource_pool(
    resource_pool_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> ResourcePoolResponse:
    """Returns the requested resource pool.

    Args:
        resource_pool_id: ID of the resource pool.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The requested resource pool.
    """
    return zen_store().get_resource_pool(
        resource_pool_id=resource_pool_id, hydrate=hydrate
    )
    # return verify_permissions_and_get_entity(
    #     id=resource_pool_id,
    #     get_method=zen_store().get_resource_pool,
    #     hydrate=hydrate,
    # )


@router.put(
    "/{resource_pool_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_resource_pool(
    resource_pool_id: UUID,
    resource_pool_update: ResourcePoolUpdate,
    _: AuthContext = Security(authorize),
) -> ResourcePoolResponse:
    """Updates a resource pool.

    Args:
        resource_pool_id: ID of the resource pool.
        resource_pool_update: Resource pool to use to update.

    Returns:
        Updated resource pool.
    """
    return zen_store().update_resource_pool(
        resource_pool_id=resource_pool_id, update=resource_pool_update
    )
    # return verify_permissions_and_update_entity(
    #     id=resource_pool_id,
    #     update_model=resource_pool_update,
    #     get_method=zen_store().get_resource_pool,
    #     update_method=zen_store().update_resource_pool,
    # )


@router.delete(
    "/{resource_pool_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_resource_pool(
    resource_pool_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a resource pool.

    Args:
        resource_pool_id: ID of the resource pool.
    """
    return zen_store().delete_resource_pool(resource_pool_id=resource_pool_id)
    # verify_permissions_and_delete_entity(
    #     id=resource_pool_id,
    #     get_method=zen_store().get_resource_pool,
    #     delete_method=zen_store().delete_resource_pool,
    # )
