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
    SERVICE_CONNECTOR_FULL_STACK,
    SERVICE_CONNECTOR_TYPES,
    SERVICE_CONNECTOR_VERIFY,
    SERVICE_CONNECTORS,
    VERSION_1,
)
from zenml.models import (
    Page,
    ServiceConnectorFilter,
    ServiceConnectorRequest,
    ServiceConnectorResourcesModel,
    ServiceConnectorResponse,
    ServiceConnectorTypeModel,
    ServiceConnectorUpdate,
)
from zenml.models.v2.misc.full_stack import (
    ServiceConnectorInfo,
    ServiceConnectorResourcesInfo,
)
from zenml.service_connectors.service_connector_utils import (
    get_resources_options_from_resource_model_for_full_stack,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_delete_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import (
    dehydrate_response_model,
    get_allowed_resource_ids,
    has_permissions_for_model,
    is_owned_by_authenticated_user,
    verify_permission,
    verify_permission_for_model,
)
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + SERVICE_CONNECTORS,
    tags=["service_connectors"],
    responses={401: error_response, 403: error_response},
)

types_router = APIRouter(
    prefix=API + VERSION_1 + SERVICE_CONNECTOR_TYPES,
    tags=["service_connectors"],
    responses={401: error_response, 403: error_response},
)


@router.get(
    "",
    response_model=Page[ServiceConnectorResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_service_connectors(
    connector_filter_model: ServiceConnectorFilter = Depends(
        make_dependable(ServiceConnectorFilter)
    ),
    expand_secrets: bool = True,
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[ServiceConnectorResponse]:
    """Get a list of all service connectors for a specific type.

    Args:
        connector_filter_model: Filter model used for pagination, sorting,
            filtering
        expand_secrets: Whether to expand secrets or not.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        Page with list of service connectors for a specific type.
    """
    connectors = verify_permissions_and_list_entities(
        filter_model=connector_filter_model,
        resource_type=ResourceType.SERVICE_CONNECTOR,
        list_method=zen_store().list_service_connectors,
        hydrate=hydrate,
    )

    if expand_secrets:
        # This will be `None` if the user is allowed to read secret values
        # for all service connectors
        allowed_ids = get_allowed_resource_ids(
            resource_type=ResourceType.SERVICE_CONNECTOR,
            action=Action.READ_SECRET_VALUE,
        )

        for connector in connectors.items:
            if not connector.secret_id:
                continue

            if allowed_ids is None or is_owned_by_authenticated_user(
                connector
            ):
                # The user either owns the connector or has permissions to
                # read secret values for all service connectors
                pass
            elif connector.id not in allowed_ids:
                # The user is not allowed to read secret values for this
                # connector. We don't raise an exception here but don't include
                # the secret values
                continue

            secret = zen_store().get_secret(secret_id=connector.secret_id)

            # Update the connector configuration with the secret.
            connector.configuration.update(secret.secret_values)

    return connectors


@router.get(
    "/{connector_id}",
    response_model=ServiceConnectorResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_service_connector(
    connector_id: UUID,
    expand_secrets: bool = True,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> ServiceConnectorResponse:
    """Returns the requested service connector.

    Args:
        connector_id: ID of the service connector.
        expand_secrets: Whether to expand secrets or not.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The requested service connector.
    """
    connector = zen_store().get_service_connector(
        connector_id, hydrate=hydrate
    )
    verify_permission_for_model(connector, action=Action.READ)

    if (
        expand_secrets
        and connector.secret_id
        and has_permissions_for_model(
            connector, action=Action.READ_SECRET_VALUE
        )
    ):
        secret = zen_store().get_secret(secret_id=connector.secret_id)

        # Update the connector configuration with the secret.
        connector.configuration.update(secret.secret_values)

    return dehydrate_response_model(connector)


@router.put(
    "/{connector_id}",
    response_model=ServiceConnectorResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_service_connector(
    connector_id: UUID,
    connector_update: ServiceConnectorUpdate,
    _: AuthContext = Security(authorize),
) -> ServiceConnectorResponse:
    """Updates a service connector.

    Args:
        connector_id: ID of the service connector.
        connector_update: Service connector to use to update.

    Returns:
        Updated service connector.
    """
    return verify_permissions_and_update_entity(
        id=connector_id,
        update_model=connector_update,
        get_method=zen_store().get_service_connector,
        update_method=zen_store().update_service_connector,
    )


@router.delete(
    "/{connector_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_service_connector(
    connector_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a service connector.

    Args:
        connector_id: ID of the service connector.
    """
    verify_permissions_and_delete_entity(
        id=connector_id,
        get_method=zen_store().get_service_connector,
        delete_method=zen_store().delete_service_connector,
    )


@router.post(
    SERVICE_CONNECTOR_VERIFY,
    response_model=ServiceConnectorResourcesModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def validate_and_verify_service_connector_config(
    connector: ServiceConnectorRequest,
    list_resources: bool = True,
    _: AuthContext = Security(authorize),
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
    verify_permission(
        resource_type=ResourceType.SERVICE_CONNECTOR, action=Action.CREATE
    )

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
    _: AuthContext = Security(authorize),
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

    Returns:
        The list of resources that the service connector has access to, scoped
        to the supplied resource type and ID, if provided.
    """
    connector = zen_store().get_service_connector(connector_id)
    verify_permission_for_model(model=connector, action=Action.READ)

    return zen_store().verify_service_connector(
        service_connector_id=connector_id,
        resource_type=resource_type,
        resource_id=resource_id,
        list_resources=list_resources,
    )


@router.get(
    "/{connector_id}" + SERVICE_CONNECTOR_CLIENT,
    response_model=ServiceConnectorResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_service_connector_client(
    connector_id: UUID,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    _: AuthContext = Security(authorize),
) -> ServiceConnectorResponse:
    """Get a service connector client for a service connector and given resource.

    This requires the service connector implementation to be installed
    on the ZenML server, otherwise a 501 Not Implemented error will be
    returned.

    Args:
        connector_id: ID of the service connector.
        resource_type: Type of the resource to list.
        resource_id: ID of the resource to list.

    Returns:
        A service connector client that can be used to access the given
        resource.
    """
    connector = zen_store().get_service_connector(connector_id)
    verify_permission_for_model(model=connector, action=Action.READ)
    verify_permission_for_model(model=connector, action=Action.CLIENT)

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
    _: AuthContext = Security(authorize),
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
    _: AuthContext = Security(authorize),
) -> ServiceConnectorTypeModel:
    """Returns the requested service connector type.

    Args:
        connector_type: the service connector type identifier.

    Returns:
        The requested service connector type.
    """
    return zen_store().get_service_connector_type(connector_type)


@router.post(
    SERVICE_CONNECTOR_FULL_STACK,
    response_model=ServiceConnectorResourcesInfo,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def get_resources_based_on_service_connector_info(
    connector_info: Optional[ServiceConnectorInfo] = None,
    connector_uuid: Optional[UUID] = None,
    _: AuthContext = Security(authorize),
) -> ServiceConnectorResourcesInfo:
    """Gets the list of resources that a service connector can access.

    Args:
        connector_info: The service connector info.
        connector_uuid: The service connector uuid.

    Returns:
        The list of resources that the service connector configuration has
        access to and consumable from UI/CLI.

    Raises:
        ValueError: If both connector_info and connector_uuid are provided.
        ValueError: If neither connector_info nor connector_uuid are provided.
    """
    if connector_info is not None and connector_uuid is not None:
        raise ValueError(
            "Only one of connector_info or connector_uuid must be provided."
        )
    if connector_info is None and connector_uuid is None:
        raise ValueError(
            "Either connector_info or connector_uuid must be provided."
        )

    if connector_info is not None:
        verify_permission(
            resource_type=ResourceType.SERVICE_CONNECTOR, action=Action.CREATE
        )
    elif connector_uuid is not None:
        verify_permission(
            resource_type=ResourceType.SERVICE_CONNECTOR,
            action=Action.READ,
            resource_id=connector_uuid,
        )

    return get_resources_options_from_resource_model_for_full_stack(
        connector_details=connector_info or connector_uuid  # type: ignore[arg-type]
    )
