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
"""Endpoint definitions for resource descriptors."""

from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, RESOURCE_DESCRIPTORS, VERSION_1
from zenml.models import (
    Page,
    ResourceDescriptorFilter,
    ResourceDescriptorRequest,
    ResourceDescriptorResponse,
    ResourceDescriptorUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + RESOURCE_DESCRIPTORS,
    tags=["resource_descriptors"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_resource_descriptor(
    descriptor: ResourceDescriptorRequest,
    _: AuthContext = Security(authorize),
) -> ResourceDescriptorResponse:
    """Create a resource descriptor.

    Args:
        descriptor: Resource descriptor payload supplied by the caller.

    Returns:
        The created resource descriptor.
    """
    return zen_store().create_resource_descriptor(descriptor)


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_resource_descriptors(
    descriptor_filter_model: ResourceDescriptorFilter = Depends(
        make_dependable(ResourceDescriptorFilter)
    ),
    _: AuthContext = Security(authorize),
) -> Page[ResourceDescriptorResponse]:
    """List resource descriptors.

    Args:
        descriptor_filter_model: Filter and pagination parameters. Pagination
            may be ignored by the Resource Manager-backed implementation until
            RM exposes paginated list APIs.

    Returns:
        A page containing matching resource descriptors.
    """
    return zen_store().list_resource_descriptors(descriptor_filter_model)


@router.get(
    "/{descriptor_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_resource_descriptor(
    descriptor_id: UUID,
    _: AuthContext = Security(authorize),
) -> ResourceDescriptorResponse:
    """Get a resource descriptor.

    Args:
        descriptor_id: ID of the resource descriptor to fetch.

    Returns:
        The requested resource descriptor.
    """
    return zen_store().get_resource_descriptor(descriptor_id)


@router.put(
    "/{descriptor_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_resource_descriptor(
    descriptor_id: UUID,
    descriptor_update: ResourceDescriptorUpdate,
    _: AuthContext = Security(authorize),
) -> ResourceDescriptorResponse:
    """Update a resource descriptor.

    Args:
        descriptor_id: ID of the resource descriptor to update.
        descriptor_update: Update payload with descriptor fields to replace.

    Returns:
        The updated resource descriptor.
    """
    return zen_store().update_resource_descriptor(
        descriptor_id=descriptor_id,
        update=descriptor_update,
    )


@router.delete(
    "/{descriptor_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_resource_descriptor(
    descriptor_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Delete a resource descriptor.

    Args:
        descriptor_id: ID of the resource descriptor to delete.
    """
    zen_store().delete_resource_descriptor(descriptor_id)
