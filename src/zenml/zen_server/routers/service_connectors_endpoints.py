#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Endpoint definitions for service connectors."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    SERVICE_CONNECTOR_CLIENT,
    SERVICE_CONNECTOR_TYPES,
    SERVICE_CONNECTOR_VERIFY,
    SERVICE_CONNECTORS,
    VERSION_1,
)
from zenml.enums import PermissionType
from zenml.models import (
    ServiceConnectorFilterModel,
    ServiceConnectorRequestModel,
    ServiceConnectorResourceListModel,
    ServiceConnectorResponseModel,
    ServiceConnectorTypeModel,
    ServiceConnectorUpdateModel,
)
from zenml.models.page_model import Page
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + SERVICE_CONNECTORS,
    tags=["service_connectors"],
    responses={401: error_response},
)

types_router = APIRouter(
    prefix=API + VERSION_1 + SERVICE_CONNECTOR_TYPES,
    tags=["service_connectors"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=Page[ServiceConnectorResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_service_connectors(
    connector_filter_model: ServiceConnectorFilterModel = Depends(
        make_dependable(ServiceConnectorFilterModel)
    ),
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> Page[ServiceConnectorResponseModel]:
    """Get a list of all service connectors for a specific type.

    Args:
        connector_filter_model: Filter model used for pagination, sorting,
                                filtering
        auth_context: Authentication Context

    Returns:
        List of service connectors for a specific type.
    """
    connector_filter_model.set_scope_user(user_id=auth_context.user.id)
    return zen_store().list_service_connectors(
        filter_model=connector_filter_model
    )


@router.get(
    "/{connector_id}",
    response_model=ServiceConnectorResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_service_connector(
    connector_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> ServiceConnectorResponseModel:
    """Returns the requested service connector.

    Args:
        connector_id: ID of the service connector.

    Returns:
        The requested service connector.
    """
    return zen_store().get_service_connector(connector_id)


@router.put(
    "/{connector_id}",
    response_model=ServiceConnectorResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_service_connector(
    connector_id: UUID,
    connector_update: ServiceConnectorUpdateModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> ServiceConnectorResponseModel:
    """Updates a service connector.

    Args:
        connector_id: ID of the service connector.
        connector_update: Service connector to use to update.

    Returns:
        Updated service connector.
    """
    return zen_store().update_service_connector(
        service_connector_id=connector_id,
        update=connector_update,
    )


@router.delete(
    "/{connector_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_service_connector(
    connector_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Deletes a service connector.

    Args:
        connector_id: ID of the service connector.
    """
    zen_store().delete_service_connector(connector_id)


@router.post(
    SERVICE_CONNECTOR_VERIFY,
    response_model=ServiceConnectorResourceListModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def verify_service_connector_config(
    connector: ServiceConnectorRequestModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> ServiceConnectorResourceListModel:
    """Verifies if a service connector configuration has access to resources.

    This requires the service connector implementation to be installed
    on the ZenML server, otherwise a 501 Not Implemented error will be
    returned.

    Args:
        connector: The service connector configuration to verify.
        auth_context: Authentication context.

    Returns:
        The list of resources that the service connector configuration has
        access to.
    """
    return zen_store().verify_service_connector_config(
        service_connector=connector
    )


@router.put(
    "/{connector_id}" + SERVICE_CONNECTOR_VERIFY,
    response_model=ServiceConnectorResourceListModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def verify_service_connector(
    connector_id: UUID,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> ServiceConnectorResourceListModel:
    """Verifies if a service connector instance has access to one or more resources.

    This requires the service connector implementation to be installed
    on the ZenML server, otherwise a 501 Not Implemented error will be
    returned.

    Args:
        connector_id: The ID of the service connector to verify.
        resource_type: The type of resource to verify access to.
        resource_id: The ID of the resource to verify access to.

    Returns:
        The list of resources that the service connector has access to, scoped
        to the supplied resource type and ID, if provided.
    """
    return zen_store().verify_service_connector(
        service_connector_id=connector_id,
        resource_type=resource_type,
        resource_id=resource_id,
    )


@router.get(
    "/{connector_id}" + SERVICE_CONNECTOR_CLIENT,
    response_model=ServiceConnectorResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_service_connector_client(
    connector_id: UUID,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> ServiceConnectorResponseModel:
    """Get a client service connector for a service connector and given resource.

    This requires the service connector implementation to be installed
    on the ZenML server, otherwise a 501 Not Implemented error will be
    returned.

    Args:
        connector_id: ID of the service connector.
        resource_type: Type of the resource to list.
        resource_id: ID of the resource to list.
        auth_context: Authentication context.

    Returns:
        A client service connector that can be used to access the given
        resource.
    """
    return zen_store().get_service_connector_client(
        service_connector_id=connector_id,
        resource_type=resource_type,
        resource_id=resource_id,
    )


@types_router.get(
    "",
    response_model=List[ServiceConnectorTypeModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_service_connector_types(
    connector_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    auth_method: Optional[str] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> List[ServiceConnectorTypeModel]:
    """Get a list of service connector types.

    Args:
        connector_type: Filter by connector type.
        resource_type: Filter by resource type.
        auth_method: Filter by auth method.
        auth_context: Authentication Context

    Returns:
        List of service connector types.
    """
    connector_types = zen_store().list_service_connector_types(
        connector_type=connector_type,
        resource_type=resource_type,
        auth_method=auth_method,
    )

    for c in connector_types:
        # Mark the connector as not being available in the environment
        # that issued the request but as being available in the server.
        c.local = False
        c.remote = True

    return connector_types


@types_router.get(
    "/{connector_type}",
    response_model=ServiceConnectorTypeModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_service_connector_type(
    connector_type: str,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> ServiceConnectorTypeModel:
    """Returns the requested service connector type.

    Args:
        connector_type: the service connector type identifier.

    Returns:
        The requested service connector type.
    """
    c = zen_store().get_service_connector_type(connector_type)

    # Mark the connector as not being available in the environment
    # that issued the request but as being available in the server.
    c.local = False
    c.remote = True

    return c
