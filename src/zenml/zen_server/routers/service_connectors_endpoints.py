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
    ServiceConnectorResourcesModel,
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
    expand_secrets: bool = True,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> Page[ServiceConnectorResponseModel]:
    """Get a list of all service connectors for a specific type.

    Args:
        connector_filter_model: Filter model used for pagination, sorting,
            filtering
        expand_secrets: Whether to expand secrets or not.
        auth_context: Authentication Context

    Returns:
        Page with list of service connectors for a specific type.
    """
    connector_filter_model.set_scope_user(user_id=auth_context.user.id)
    connectors = zen_store().list_service_connectors(
        filter_model=connector_filter_model
    )

    if expand_secrets and PermissionType.WRITE in auth_context.permissions:
        for connector in connectors.items:
            if not connector.secret_id:
                continue
            secret = zen_store().get_secret(secret_id=connector.secret_id)

            # Update the connector configuration with the secret.
            connector.configuration.update(secret.secret_values)

    return connectors


@router.get(
    "/{connector_id}",
    response_model=ServiceConnectorResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_service_connector(
    connector_id: UUID,
    expand_secrets: bool = True,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> ServiceConnectorResponseModel:
    """Returns the requested service connector.

    Args:
        connector_id: ID of the service connector.
        expand_secrets: Whether to expand secrets or not.
        auth_context: Authentication context.

    Returns:
        The requested service connector.

    Raises:
        KeyError: If the service connector does not exist or is not accessible.
    """
    connector = zen_store().get_service_connector(connector_id)

    # Don't allow users to access service connectors that don't belong to them
    # unless they are shared.
    if (
        connector.user
        and connector.user.id == auth_context.user.id
        or connector.is_shared
    ):
        if PermissionType.WRITE not in auth_context.permissions:
            return connector

        if expand_secrets and connector.secret_id:
            secret = zen_store().get_secret(secret_id=connector.secret_id)

            # Update the connector configuration with the secret.
            connector.configuration.update(secret.secret_values)

        return connector

    raise KeyError(f"Service connector with ID {connector_id} not found.")


@router.put(
    "/{connector_id}",
    response_model=ServiceConnectorResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_service_connector(
    connector_id: UUID,
    connector_update: ServiceConnectorUpdateModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> ServiceConnectorResponseModel:
    """Updates a service connector.

    Args:
        connector_id: ID of the service connector.
        connector_update: Service connector to use to update.
        auth_context: Authentication context.

    Returns:
        Updated service connector.

    Raises:
        KeyError: If the service connector does not exist or is not accessible.
    """
    connector = zen_store().get_service_connector(connector_id)

    # Don't allow users to access service connectors that don't belong to them
    # unless they are shared.
    if (
        connector.user
        and connector.user.id == auth_context.user.id
        or connector.is_shared
    ):
        return zen_store().update_service_connector(
            service_connector_id=connector_id,
            update=connector_update,
        )

    raise KeyError(f"Service connector with ID {connector_id} not found.")


@router.delete(
    "/{connector_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_service_connector(
    connector_id: UUID,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> None:
    """Deletes a service connector.

    Args:
        connector_id: ID of the service connector.
        auth_context: Authentication context.

    Raises:
        KeyError: If the service connector does not exist or is not accessible.
    """
    connector = zen_store().get_service_connector(connector_id)

    # Don't allow users to access service connectors that don't belong to them
    # unless they are shared.
    if (
        connector.user
        and connector.user.id == auth_context.user.id
        or connector.is_shared
    ):
        zen_store().delete_service_connector(connector_id)
        return

    raise KeyError(f"Service connector with ID {connector_id} not found.")


@router.post(
    SERVICE_CONNECTOR_VERIFY,
    response_model=ServiceConnectorResourcesModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def validate_and_verify_service_connector_config(
    connector: ServiceConnectorRequestModel,
    list_resources: bool = True,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> ServiceConnectorResourcesModel:
    """Verifies if a service connector configuration has access to resources.

    This requires the service connector implementation to be installed
    on the ZenML server, otherwise a 501 Not Implemented error will be
    returned.

    Args:
        connector: The service connector configuration to verify.
        list_resources: If True, the list of all resources accessible
            through the service connector is returned.

    Returns:
        The list of resources that the service connector configuration has
        access to.
    """
    return zen_store().verify_service_connector_config(
        service_connector=connector,
        list_resources=list_resources,
    )


@router.put(
    "/{connector_id}" + SERVICE_CONNECTOR_VERIFY,
    response_model=ServiceConnectorResourcesModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def validate_and_verify_service_connector(
    connector_id: UUID,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    list_resources: bool = True,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> ServiceConnectorResourcesModel:
    """Verifies if a service connector instance has access to one or more resources.

    This requires the service connector implementation to be installed
    on the ZenML server, otherwise a 501 Not Implemented error will be
    returned.

    Args:
        connector_id: The ID of the service connector to verify.
        resource_type: The type of resource to verify access to.
        resource_id: The ID of the resource to verify access to.
        list_resources: If True, the list of all resources accessible
            through the service connector and matching the supplied resource
            type and ID are returned.
        auth_context: Authentication context.

    Returns:
        The list of resources that the service connector has access to, scoped
        to the supplied resource type and ID, if provided.

    Raises:
        KeyError: If the service connector does not exist or is not accessible.
    """
    connector = zen_store().get_service_connector(connector_id)

    # Don't allow users to access service connectors that don't belong to them
    # unless they are shared.
    if (
        connector.user
        and connector.user.id == auth_context.user.id
        or connector.is_shared
    ):
        return zen_store().verify_service_connector(
            service_connector_id=connector_id,
            resource_type=resource_type,
            resource_id=resource_id,
            list_resources=list_resources,
        )

    raise KeyError(f"Service connector with ID {connector_id} not found.")


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
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> ServiceConnectorResponseModel:
    """Get a service connector client for a service connector and given resource.

    This requires the service connector implementation to be installed
    on the ZenML server, otherwise a 501 Not Implemented error will be
    returned.

    Args:
        connector_id: ID of the service connector.
        resource_type: Type of the resource to list.
        resource_id: ID of the resource to list.
        auth_context: Authentication context.

    Returns:
        A service connector client that can be used to access the given
        resource.

    Raises:
        KeyError: If the service connector does not exist or is not accessible.
    """
    connector = zen_store().get_service_connector(connector_id)

    # Don't allow users to access service connectors that don't belong to them
    # unless they are shared.
    if (
        connector.user
        and connector.user.id == auth_context.user.id
        or connector.is_shared
    ):
        return zen_store().get_service_connector_client(
            service_connector_id=connector_id,
            resource_type=resource_type,
            resource_id=resource_id,
        )

    raise KeyError(f"Service connector with ID {connector_id} not found.")


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

    Returns:
        List of service connector types.
    """
    connector_types = zen_store().list_service_connector_types(
        connector_type=connector_type,
        resource_type=resource_type,
        auth_method=auth_method,
    )

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

    return c
