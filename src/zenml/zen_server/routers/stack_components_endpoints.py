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
"""Endpoint definitions for stack components."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, COMPONENT_TYPES, STACK_COMPONENTS, VERSION_1
from zenml.enums import PermissionType, StackComponentType
from zenml.models import (
    ComponentFilter,
    ComponentResponse,
    ComponentUpdate,
    Page,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + STACK_COMPONENTS,
    tags=["stack_components"],
    responses={401: error_response},
)

types_router = APIRouter(
    prefix=API + VERSION_1 + COMPONENT_TYPES,
    tags=["stack_components"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=Page[ComponentResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_stack_components(
    component_filter_model: ComponentFilter = Depends(
        make_dependable(ComponentFilter)
    ),
    hydrate: bool = False,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> Page[ComponentResponse]:
    """Get a list of all stack components for a specific type.

    Args:
        component_filter_model: Filter model used for pagination, sorting,
                                filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.
        auth_context: Authentication Context.

    Returns:
        List of stack components for a specific type.
    """
    component_filter_model.set_scope_user(user_id=auth_context.user.id)
    return zen_store().list_stack_components(
        component_filter_model=component_filter_model, hydrate=hydrate
    )


@router.get(
    "/{component_id}",
    response_model=ComponentResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_stack_component(
    component_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> ComponentResponse:
    """Returns the requested stack component.

    Args:
        component_id: ID of the stack component.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The requested stack component.
    """
    return zen_store().get_stack_component(component_id, hydrate=hydrate)


@router.put(
    "/{component_id}",
    response_model=ComponentResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_stack_component(
    component_id: UUID,
    component_update: ComponentUpdate,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> ComponentResponse:
    """Updates a stack component.

    Args:
        component_id: ID of the stack component.
        component_update: Stack component to use to update.

    Returns:
        Updated stack component.
    """
    if component_update.configuration:
        from zenml.stack.utils import validate_stack_component_config

        existing_component = zen_store().get_stack_component(component_id)
        validate_stack_component_config(
            configuration_dict=component_update.configuration,
            flavor_name=existing_component.flavor,
            component_type=existing_component.type,
            zen_store=zen_store(),
            # We allow custom flavors to fail import on the server side.
            validate_custom_flavors=False,
        )
    return zen_store().update_stack_component(
        component_id=component_id,
        component_update=component_update,
    )


@router.delete(
    "/{component_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def deregister_stack_component(
    component_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Deletes a stack component.

    Args:
        component_id: ID of the stack component.
    """
    zen_store().delete_stack_component(component_id)


@types_router.get(
    "",
    response_model=List[str],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_stack_component_types(
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ])
) -> List[str]:
    """Get a list of all stack component types.

    Returns:
        List of stack components.
    """
    return StackComponentType.values()
