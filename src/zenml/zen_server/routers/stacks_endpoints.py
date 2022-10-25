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

from fastapi import APIRouter, Depends

from zenml.constants import API, STACKS, VERSION_1
from zenml.models import StackModel
from zenml.models.stack_models import HydratedStackModel
from zenml.zen_server.auth import authorize
from zenml.zen_server.models.stack_models import UpdateStackRequest
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + STACKS,
    tags=["stacks"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=Union[List[HydratedStackModel], List[StackModel]],  # type: ignore[arg-type]
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_stacks(
    project_name_or_id: Optional[Union[str, UUID]] = None,
    user_name_or_id: Optional[Union[str, UUID]] = None,
    component_id: Optional[UUID] = None,
    name: Optional[str] = None,
    is_shared: Optional[bool] = None,
    hydrated: bool = False,
) -> Union[List[HydratedStackModel], List[StackModel]]:
    """Returns all stacks.

    Args:
        project_name_or_id: Name or ID of the project
        user_name_or_id: Optionally filter by name or ID of the user.
        component_id: Optionally filter by component that is part of the stack.
        name: Optionally filter by stack name
        is_shared: Optionally filter by shared status of the stack
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        All stacks.
    """
    return zen_store().list_stacks(
        project_name_or_id=project_name_or_id,
        user_name_or_id=user_name_or_id,
        component_id=component_id,
        is_shared=is_shared,
        name=name,
        hydrated=hydrated,
    )


@router.get(
    "/{stack_id}",
    response_model=Union[HydratedStackModel, StackModel],  # type: ignore[arg-type]
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_stack(
    stack_id: UUID, hydrated: bool = False
) -> Union[HydratedStackModel, StackModel]:
    """Returns the requested stack.

    Args:
        stack_id: ID of the stack.
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        The requested stack.
    """
    stack = zen_store().get_stack(stack_id)
    if hydrated:
        return stack.to_hydrated_model()
    else:
        return stack


@router.put(
    "/{stack_id}",
    response_model=Union[HydratedStackModel, StackModel],  # type: ignore[arg-type]
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_stack(
    stack_id: UUID, stack_update: UpdateStackRequest, hydrated: bool = False
) -> Union[HydratedStackModel, StackModel]:
    """Updates a stack.

    Args:
        stack_id: Name of the stack.
        stack_update: Stack to use for the update.
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        The updated stack.
    """
    stack_in_db = zen_store().get_stack(stack_id)
    updated_stack = zen_store().update_stack(
        stack=stack_update.apply_to_model(stack_in_db)
    )
    if hydrated:
        return updated_stack.to_hydrated_model()
    else:
        return updated_stack


@router.delete(
    "/{stack_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_stack(stack_id: UUID) -> None:
    """Deletes a stack.

    Args:
        stack_id: Name of the stack.
    """
    zen_store().delete_stack(stack_id)  # aka 'deregister_stack'
