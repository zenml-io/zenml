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

from fastapi import APIRouter, Depends

from zenml.constants import API, COMPONENT_TYPES, STACK_COMPONENTS, VERSION_1
from zenml.enums import StackComponentType
from zenml.models import ComponentModel
from zenml.models.component_model import HydratedComponentModel
from zenml.zen_server.auth import authorize
from zenml.zen_server.models.component_models import UpdateComponentModel
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + STACK_COMPONENTS,
    tags=["stack_components"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)

types_router = APIRouter(
    prefix=API + VERSION_1 + COMPONENT_TYPES,
    tags=["stack_components"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=Union[List[ComponentModel], List[HydratedComponentModel]],  # type: ignore[arg-type]
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
    hydrated: bool = False,
) -> Union[List[ComponentModel], List[HydratedComponentModel]]:
    """Get a list of all stack components for a specific type.

    Args:
        project_name_or_id: Name or ID of the project
        user_name_or_id: Optionally filter by name or ID of the user.
        name: Optionally filter by component name
        type: Optionally filter by component type
        flavor_name: Optionally filter by flavor
        is_shared: Optionally filter by shared status of the component
        hydrated: Defines if users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        List of stack components for a specific type.
    """
    components_list = zen_store().list_stack_components(
        project_name_or_id=project_name_or_id,
        user_name_or_id=user_name_or_id,
        type=type,
        name=name,
        flavor_name=flavor_name,
        is_shared=is_shared,
    )
    if hydrated:
        return [comp.to_hydrated_model() for comp in components_list]
    else:
        return components_list


@router.get(
    "/{component_id}",
    response_model=Union[ComponentModel, HydratedComponentModel],  # type: ignore[arg-type]
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_stack_component(
    component_id: UUID, hydrated: bool = False
) -> Union[ComponentModel, HydratedComponentModel]:
    """Returns the requested stack component.

    Args:
        component_id: ID of the stack component.
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        The requested stack component.
    """
    component = zen_store().get_stack_component(component_id)
    if hydrated:
        return component.to_hydrated_model()
    else:
        return component


@router.put(
    "/{component_id}",
    response_model=Union[ComponentModel, HydratedComponentModel],  # type: ignore[arg-type]
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_stack_component(
    component_id: UUID,
    component_update: UpdateComponentModel,
    hydrated: bool = False,
) -> Union[ComponentModel, HydratedComponentModel]:
    """Updates a stack component.

    Args:
        component_id: ID of the stack component.
        component_update: Stack component to use to update.
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        Updated stack component.
    """
    component_in_db = zen_store().get_stack_component(component_id)

    updated_component = zen_store().update_stack_component(
        component=component_update.apply_to_model(component_in_db)
    )
    if hydrated:
        return updated_component.to_hydrated_model()
    else:
        return updated_component


@router.delete(
    "/{component_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def deregister_stack_component(component_id: UUID) -> None:
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
def get_stack_component_types() -> List[str]:
    """Get a list of all stack component types.

    Returns:
        List of stack components.
    """
    return StackComponentType.values()
