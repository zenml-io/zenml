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
"""Endpoint definitions for resource requests."""

from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, RESOURCE_REQUESTS, VERSION_1
from zenml.models import (
    Page,
    ResourceRequestFilter,
    ResourceRequestRenewalRequest,
    ResourceRequestResponse,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + RESOURCE_REQUESTS,
    tags=["resource_requests"],
    responses={401: error_response, 403: error_response},
)


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_resource_requests(
    resource_request_filter_model: ResourceRequestFilter = Depends(
        make_dependable(ResourceRequestFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[ResourceRequestResponse]:
    """Get a list of all resource requests.

    Args:
        resource_request_filter_model: Filter model used for pagination,
            sorting, filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        List of resource requests matching the filter criteria.
    """
    return zen_store().list_resource_requests(
        filter_model=resource_request_filter_model,
        hydrate=hydrate,
    )


@router.get(
    "/{resource_request_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_resource_request(
    resource_request_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> ResourceRequestResponse:
    """Returns the requested resource request.

    Args:
        resource_request_id: ID of the resource request.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The requested resource request.
    """
    return zen_store().get_resource_request(
        resource_request_id, hydrate=hydrate
    )


@router.post(
    "/{resource_request_id}/renew",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def renew_resource_request(
    resource_request_id: UUID,
    renewal_request: ResourceRequestRenewalRequest,
    _: AuthContext = Security(authorize),
) -> ResourceRequestResponse:
    """Renew a resource request lease.

    Args:
        resource_request_id: ID of the resource request.
        renewal_request: Renewed lease expiration timestamp.

    Returns:
        The renewed resource request.
    """
    return zen_store().renew_resource_request(
        resource_request_id,
        renewal_request,
    )


@router.post(
    "/{resource_request_id}/release",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def release_resource_request(
    resource_request_id: UUID,
    _: AuthContext = Security(authorize),
) -> ResourceRequestResponse:
    """Release a resource request on behalf of its owner.

    Args:
        resource_request_id: ID of the resource request.

    Returns:
        The released resource request.
    """
    return zen_store().release_resource_request(resource_request_id)
