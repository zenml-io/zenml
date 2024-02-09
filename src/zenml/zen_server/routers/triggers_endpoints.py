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
"""Endpoint definitions for triggers."""

from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml import TriggerRequest
from zenml.constants import API, TRIGGER_EXECUTIONS, TRIGGERS, VERSION_1
from zenml.models import (
    Page,
    TriggerExecutionFilter,
    TriggerExecutionResponse,
    TriggerFilter,
    TriggerResponse,
    TriggerUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity, verify_permissions_and_create_entity,
)
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + TRIGGERS,
    tags=["triggers"],
    responses={401: error_response, 403: error_response},
)


@router.get(
    "",
    response_model=Page[TriggerResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_triggers(
    trigger_filter_model: TriggerFilter = Depends(
        make_dependable(TriggerFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[TriggerResponse]:
    """Returns all triggers.

    Args:
        trigger_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        All triggers.
    """
    return verify_permissions_and_list_entities(
        filter_model=trigger_filter_model,
        resource_type=ResourceType.TRIGGER,
        list_method=zen_store().list_triggers,
        hydrate=hydrate,
    )


@router.get(
    "/{trigger_id}",
    response_model=TriggerResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_trigger(
    trigger_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> TriggerResponse:
    """Returns the requested trigger.

    Args:
        trigger_id: ID of the trigger.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The requested trigger.
    """
    return verify_permissions_and_get_entity(
        id=trigger_id, get_method=zen_store().get_trigger, hydrate=hydrate
    )


@router.post(
    "",
    response_model=TriggerResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_trigger(
    trigger: TriggerRequest,
    _: AuthContext = Security(authorize),
) -> TriggerResponse:
    """Creates a trigger.

    Args:
        trigger: Trigger to register.

    Returns:
        The created trigger.

    Raises:
        IllegalOperationError: If the workspace specified in the stack
            component does not match the current workspace.
    """
    # TODO: Validate event_source exists
    # TODO: Validate event_filter is valid
    # TODO: Validate action is valid

    return verify_permissions_and_create_entity(
        request_model=trigger,
        resource_type=ResourceType.TRIGGER,
        create_method=zen_store().create_trigger,
    )


@router.put(
    "/{trigger_id}",
    response_model=TriggerResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_trigger(
    trigger_id: UUID,
    trigger_update: TriggerUpdate,
    _: AuthContext = Security(authorize),
) -> TriggerResponse:
    """Updates a trigger.

    Args:
        trigger_id: Name of the trigger.
        trigger_update: Trigger to use for the update.

    Returns:
        The updated trigger.
    """
    # TODO: Look into updating event/action
    return verify_permissions_and_update_entity(
        id=trigger_id,
        update_model=trigger_update,
        get_method=zen_store().get_trigger,
        update_method=zen_store().update_trigger,
    )


@router.delete(
    "/{trigger_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_trigger(
    trigger_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a trigger.

    Args:
        trigger_id: Name of the trigger.
    """
    verify_permissions_and_delete_entity(
        id=trigger_id,
        get_method=zen_store().get_trigger,
        delete_method=zen_store().delete_trigger,
    )


executions_router = APIRouter(
    prefix=API + VERSION_1 + TRIGGER_EXECUTIONS,
    tags=["trigger_executions"],
    responses={401: error_response, 403: error_response},
)


@executions_router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_trigger_executions(
    trigger_execution_filter_model: TriggerExecutionFilter = Depends(
        make_dependable(TriggerExecutionFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[TriggerExecutionResponse]:
    """List trigger executions.

    Args:
        trigger_execution_filter_model: Filter model used for pagination,
            sorting, filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        Page of trigger executions.
    """
    return verify_permissions_and_list_entities(
        filter_model=trigger_execution_filter_model,
        resource_type=ResourceType.TRIGGER_EXECUTION,
        list_method=zen_store().list_trigger_executions,
        hydrate=hydrate,
    )


@executions_router.get(
    "/{trigger_execution_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_trigger_execution(
    trigger_execution_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> TriggerExecutionResponse:
    """Returns the requested trigger execution.

    Args:
        trigger_execution_id: ID of the trigger execution.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The requested trigger execution.
    """
    return verify_permissions_and_get_entity(
        id=trigger_execution_id,
        get_method=zen_store().get_trigger_execution,
        hydrate=hydrate,
    )


@executions_router.delete(
    "/{trigger_execution_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_trigger_execution(
    trigger_execution_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a trigger execution.

    Args:
        trigger_execution_id: ID of the trigger execution.
    """
    verify_permissions_and_delete_entity(
        id=trigger_execution_id,
        get_method=zen_store().get_trigger_execution,
        delete_method=zen_store().delete_trigger_execution,
    )
