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
"""Endpoint definitions for stacks."""

from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Security

from zenml.constants import API, STACKS, VERSION_1
from zenml.enums import PermissionType
from zenml.models import StackResponseModel, StackUpdateModel
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + STACKS,
    tags=["stacks"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=List[StackResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_stacks(
    project_name_or_id: Optional[Union[str, UUID]] = None,
    user_name_or_id: Optional[Union[str, UUID]] = None,
    component_id: Optional[UUID] = None,
    name: Optional[str] = None,
    is_shared: Optional[bool] = None,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> List[StackResponseModel]:
    """Returns all stacks.

    Args:
        project_name_or_id: Name or ID of the project
        user_name_or_id: Optionally filter by name or ID of the user.
        component_id: Optionally filter by component that is part of the stack.
        name: Optionally filter by stack name
        is_shared: Defines whether to return shared stacks or the private stacks
            of the user. If not set, both are returned.
        auth_context: Authentication Context

    Returns:
        All stacks.
    """
    stacks: List[StackResponseModel] = []

    # Get private stacks unless `is_shared` is set to True
    if is_shared is None or not is_shared:
        own_stacks = zen_store().list_stacks(
            project_name_or_id=project_name_or_id,
            user_name_or_id=user_name_or_id or auth_context.user.id,
            component_id=component_id,
            is_shared=False,
            name=name,
        )
        stacks += own_stacks

    # Get shared stacks unless `is_shared` is set to False
    if is_shared is None or is_shared:
        shared_stacks = zen_store().list_stacks(
            project_name_or_id=project_name_or_id,
            user_name_or_id=user_name_or_id,
            component_id=component_id,
            is_shared=True,
            name=name,
        )
        stacks += shared_stacks

    return stacks


@router.get(
    "/{stack_id}",
    response_model=StackResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_stack(
    stack_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> StackResponseModel:
    """Returns the requested stack.

    Args:
        stack_id: ID of the stack.

    Returns:
        The requested stack.
    """
    return zen_store().get_stack(stack_id)


@router.put(
    "/{stack_id}",
    response_model=StackResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_stack(
    stack_id: UUID,
    stack_update: StackUpdateModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> StackResponseModel:
    """Updates a stack.

    Args:
        stack_id: Name of the stack.
        stack_update: Stack to use for the update.

    Returns:
        The updated stack.
    """
    return zen_store().update_stack(
        stack_id=stack_id,
        stack_update=stack_update,
    )


@router.delete(
    "/{stack_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_stack(
    stack_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Deletes a stack.

    Args:
        stack_id: Name of the stack.
    """
    zen_store().delete_stack(stack_id)  # aka 'delete_stack'
