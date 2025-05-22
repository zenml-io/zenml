#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Endpoint definitions for services."""

from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, SERVICES, VERSION_1
from zenml.models import (
    Page,
    ServiceFilter,
    ServiceResponse,
    ServiceUpdate,
)
from zenml.models.v2.core.service import ServiceRequest
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
    prefix=API + VERSION_1 + SERVICES,
    tags=["services"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.post(
    "/{project_name_or_id}" + SERVICES,
    responses={401: error_response, 409: error_response, 422: error_response},
    deprecated=True,
    tags=["services"],
)
@async_fastapi_endpoint_wrapper
def create_service(
    service: ServiceRequest,
    project_name_or_id: Optional[Union[str, UUID]] = None,
    _: AuthContext = Security(authorize),
) -> ServiceResponse:
    """Creates a new service.

    Args:
        service: The service to create.
        project_name_or_id: Optional name or ID of the project.

    Returns:
        The created service.
    """
    if project_name_or_id:
        project = zen_store().get_project(project_name_or_id)
        service.project = project.id

    return verify_permissions_and_create_entity(
        request_model=service,
        create_method=zen_store().create_service,
    )


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_services(
    filter_model: ServiceFilter = Depends(make_dependable(ServiceFilter)),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[ServiceResponse]:
    """Gets a page of service objects.

    Args:
        filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        Page of service objects.
    """
    return verify_permissions_and_list_entities(
        filter_model=filter_model,
        resource_type=ResourceType.SERVICE,
        list_method=zen_store().list_services,
        hydrate=hydrate,
    )


@router.get(
    "/{service_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_service(
    service_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> ServiceResponse:
    """Gets a specific service using its unique ID.

    Args:
        service_id: The ID of the service to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        A specific service object.
    """
    return verify_permissions_and_get_entity(
        id=service_id,
        get_method=zen_store().get_service,
        hydrate=hydrate,
    )


@router.put(
    "/{service_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_service(
    service_id: UUID,
    update: ServiceUpdate,
    _: AuthContext = Security(authorize),
) -> ServiceResponse:
    """Updates a service.

    Args:
        service_id: The ID of the service to update.
        update: The model containing the attributes to update.

    Returns:
        The updated service object.
    """
    return verify_permissions_and_update_entity(
        id=service_id,
        update_model=update,
        get_method=zen_store().get_service,
        update_method=zen_store().update_service,
    )


@router.delete(
    "/{service_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_service(
    service_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a specific service.

    Args:
        service_id: The ID of the service to delete.
    """
    verify_permissions_and_delete_entity(
        id=service_id,
        get_method=zen_store().get_service,
        delete_method=zen_store().delete_service,
    )
