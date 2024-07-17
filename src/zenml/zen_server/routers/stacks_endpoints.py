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

from zenml.constants import API, STACKS, VERSION_1, REPORTABLE_RESOURCES
from zenml.models import Page, StackFilter, StackResponse, StackUpdate
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.feature_gate.endpoint_utils import report_decrement
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import batch_verify_permissions_for_models
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + STACKS,
    tags=["stacks"],
    responses={401: error_response, 403: error_response},
)


@router.get(
    "",
    response_model=Page[StackResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_stacks(
    stack_filter_model: StackFilter = Depends(make_dependable(StackFilter)),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[StackResponse]:
    """Returns all stacks.

    Args:
        stack_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        All stacks.
    """
    return verify_permissions_and_list_entities(
        filter_model=stack_filter_model,
        resource_type=ResourceType.STACK,
        list_method=zen_store().list_stacks,
        hydrate=hydrate,
    )


@router.get(
    "/{stack_id}",
    response_model=StackResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_stack(
    stack_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> StackResponse:
    """Returns the requested stack.

    Args:
        stack_id: ID of the stack.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The requested stack.
    """
    return verify_permissions_and_get_entity(
        id=stack_id, get_method=zen_store().get_stack, hydrate=hydrate
    )


@router.put(
    "/{stack_id}",
    response_model=StackResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_stack(
    stack_id: UUID,
    stack_update: StackUpdate,
    _: AuthContext = Security(authorize),
) -> StackResponse:
    """Updates a stack.

    Args:
        stack_id: Name of the stack.
        stack_update: Stack to use for the update.

    Returns:
        The updated stack.
    """
    if stack_update.components:
        updated_components = [
            zen_store().get_stack_component(id)
            for ids in stack_update.components.values()
            for id in ids
        ]

        batch_verify_permissions_for_models(
            updated_components, action=Action.READ
        )

    return verify_permissions_and_update_entity(
        id=stack_id,
        update_model=stack_update,
        get_method=zen_store().get_stack,
        update_method=zen_store().update_stack,
    )


@router.delete(
    "/{stack_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_stack(
    stack_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a stack.

    Args:
        stack_id: Name of the stack.
    """
    verify_permissions_and_delete_entity(
        id=stack_id,
        get_method=zen_store().get_stack,
        delete_method=zen_store().delete_stack,
    )

    should_decrement = (
        ResourceType.STACK in REPORTABLE_RESOURCES
    )
    if should_decrement:
        report_decrement(ResourceType.STACK, resource_id=stack_id)
