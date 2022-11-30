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
from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Security

from zenml.constants import API, COMPONENT_TYPES, STACK_COMPONENTS, VERSION_1
from zenml.enums import PermissionType, StackComponentType
from zenml.models import ComponentResponseModel, ComponentUpdateModel
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

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
    response_model=List[ComponentResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_stack_components(
    project_name_or_id: Optional[Union[str, UUID]] = None,
    user_name_or_id: Optional[Union[str, UUID]] = None,
    type: Optional[str] = None,
    name: Optional[str] = None,
    flavor_name: Optional[str] = None,
    is_shared: Optional[bool] = None,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> List[ComponentResponseModel]:
    """Get a list of all stack components for a specific type.

    Args:
        project_name_or_id: Name or ID of the project
        user_name_or_id: Optionally filter by name or ID of the user.
        name: Optionally filter by component name
        type: Optionally filter by component type
        flavor_name: Optionally filter by flavor
        is_shared: Defines whether to return shared stack components or the
            private stack components of the user. If not set, both are returned.
        auth_context: Authentication Context

    Returns:
        List of stack components for a specific type.
    """
    # TODO: Implement a sensible filtering mechanism

    components: List[ComponentResponseModel] = []

    # Get private stack components unless `is_shared` is set to True
    if is_shared is None or not is_shared:
        own_components = zen_store().list_stack_components(
            name=name,
            user_name_or_id=user_name_or_id or auth_context.user.id,
            project_name_or_id=project_name_or_id,
            flavor_name=flavor_name,
            type=type,
            is_shared=False,
        )
        components += own_components

    # Get shared stacks unless `is_shared` is set to False
    if is_shared is None or is_shared:
        shared_components = zen_store().list_stack_components(
            project_name_or_id=project_name_or_id,
            user_name_or_id=user_name_or_id,
            flavor_name=flavor_name,
            name=name,
            type=type,
            is_shared=True,
        )
        components += shared_components

    return components


@router.get(
    "/{component_id}",
    response_model=ComponentResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_stack_component(
    component_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> ComponentResponseModel:
    """Returns the requested stack component.

    Args:
        component_id: ID of the stack component.

    Returns:
        The requested stack component.
    """
    return zen_store().get_stack_component(component_id)


@router.put(
    "/{component_id}",
    response_model=ComponentResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_stack_component(
    component_id: UUID,
    component_update: ComponentUpdateModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> ComponentResponseModel:
    """Updates a stack component.

    Args:
        component_id: ID of the stack component.
        component_update: Stack component to use to update.

    Returns:
        Updated stack component.
    """
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
