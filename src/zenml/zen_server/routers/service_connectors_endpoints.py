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
    SERVICE_CONNECTOR_TYPES,
    SERVICE_CONNECTOR_VERIFY,
    SERVICE_CONNECTORS,
    VERSION_1,
)
from zenml.enums import PermissionType
from zenml.models import (
    ServiceConnectorFilterModel,
    ServiceConnectorResponseModel,
    ServiceConnectorTypeModel,
    ServiceConnectorUpdateModel,
)
from zenml.models.page_model import Page
from zenml.service_connectors.service_connector_registry import (
    service_connector_registry,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.utils import (
    error_response,
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


@router.put(
    "/{connector_id}" + SERVICE_CONNECTOR_VERIFY,
    response_model=ServiceConnectorResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def verify_service_connector(
    connector_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> ServiceConnectorResponseModel:
    """Verifies a service connector.

    Args:
        connector_id: ID of the service connector.
        auth_context: Authentication context.

    Returns:
        The verified service connector.
    """
    connector = zen_store().get_service_connector(connector_id)

    connector_instance = (
        service_connector_registry.instantiate_service_connector(
            model=connector
        )
    )

    connector_instance.verify()

    return connector


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
    """Get a list of all service connector types.

    Args:
        connector_type: Filter by connector type.
        resource_type: Filter by resource type.
        auth_method: Filter by auth method.
        auth_context: Authentication Context

    Returns:
        List of service connector types.
    """
    from zenml.service_connectors.service_connector_registry import (
        service_connector_registry,
    )

    connectors = service_connector_registry.list_service_connectors(
        connector_type=connector_type,
        resource_type=resource_type,
        auth_method=auth_method,
    )
    return [connector.get_type() for connector in connectors]


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
    """Returns the requested service connector type specification.

    Args:
        connector_type: the service connector type identifier.

    Returns:
        The requested service connector type specification.
    """
    from zenml.service_connectors.service_connector_registry import (
        service_connector_registry,
    )

    return service_connector_registry.get_service_connector(
        connector_type
    ).get_type()
