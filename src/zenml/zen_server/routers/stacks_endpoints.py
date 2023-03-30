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

from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, STACKS, VERSION_1
from zenml.enums import PermissionType
from zenml.models import StackFilterModel, StackResponseModel, StackUpdateModel
from zenml.models.page_model import Page
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + STACKS,
    tags=["stacks"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=Page[StackResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_stacks(
    stack_filter_model: StackFilterModel = Depends(
        make_dependable(StackFilterModel)
    ),
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> Page[StackResponseModel]:
    """Returns all stacks.

    Args:
        stack_filter_model: Filter model used for pagination, sorting, filtering
        auth_context: Authentication Context

    Returns:
        All stacks.
    """
    stack_filter_model.set_scope_user(user_id=auth_context.user.id)

    return zen_store().list_stacks(stack_filter_model=stack_filter_model)


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
