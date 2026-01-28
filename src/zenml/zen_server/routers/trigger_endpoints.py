#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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

from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, PIPELINE_SNAPSHOTS, TRIGGERS, VERSION_1
from zenml.models import (
    Page,
    TriggerFilter,
    TriggerRequest,
    TriggerResponse,
    TriggerUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import verify_permission_for_model
from zenml.zen_server.routers.projects_endpoints import workspace_router
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + TRIGGERS,
    tags=["triggers"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.post(
    "/{project_name_or_id}" + TRIGGERS,
    responses={401: error_response, 409: error_response, 422: error_response},
    deprecated=True,
    tags=["triggers"],
)
@async_fastapi_endpoint_wrapper
def create_trigger(
    trigger: TriggerRequest,
    project_name_or_id: Optional[Union[str, UUID]] = None,
    _: AuthContext = Security(authorize),
) -> TriggerResponse:
    """Creates a trigger.

    Args:
        trigger: The trigger to create.
        project_name_or_id: Optional name or ID of the project.

    Returns:
        The created trigger.
    """
    if project_name_or_id:
        project = zen_store().get_project(project_name_or_id)
        trigger.project = project.id

    return verify_permissions_and_create_entity(
        request_model=trigger,
        create_method=zen_store().create_trigger,
    )


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.get(
    "/{project_name_or_id}" + TRIGGERS,
    responses={401: error_response, 404: error_response, 422: error_response},
    deprecated=True,
    tags=["triggers"],
)
@async_fastapi_endpoint_wrapper
def list_triggers(
    trigger_filter_model: TriggerFilter = Depends(
        make_dependable(TriggerFilter)
    ),
    project_name_or_id: Optional[Union[str, UUID]] = None,
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[TriggerResponse]:
    """Gets a list of triggers.

    Args:
        trigger_filter_model: Filter model used for pagination, sorting,
            filtering
        project_name_or_id: Optional name or ID of the project.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        List of trigger objects.
    """
    if project_name_or_id:
        trigger_filter_model.project = project_name_or_id

    return verify_permissions_and_list_entities(
        filter_model=trigger_filter_model,
        resource_type=ResourceType.TRIGGER,
        list_method=zen_store().list_triggers,
        hydrate=hydrate,
    )


@router.get(
    "/{trigger_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_trigger(
    trigger_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> TriggerResponse:
    """Gets a specific trigger using its unique id.

    Args:
        trigger_id: ID of the trigger to retrieve.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        A specific trigger object.
    """
    return verify_permissions_and_get_entity(
        id=trigger_id,
        get_method=zen_store().get_trigger,
        hydrate=hydrate,
    )


@router.put(
    "/{trigger_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_trigger(
    trigger_id: UUID,
    trigger_update: TriggerUpdate,
    _: AuthContext = Security(authorize),
) -> TriggerResponse:
    """Updates the attributes on a specific trigger using its unique id.

    Args:
        trigger_id: ID of the trigger to update.
        trigger_update: the model containing the attributes to update.

    Returns:
        The updated trigger object.
    """
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
@async_fastapi_endpoint_wrapper
def delete_trigger(
    trigger_id: UUID,
    soft: bool,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a specific trigger using its unique id.

    Args:
        trigger_id: ID of the trigger to delete.
        soft: Soft deletion will archive the trigger.
    """
    verify_permissions_and_delete_entity(
        id=trigger_id,
        get_method=zen_store().get_trigger,
        delete_method=zen_store().delete_trigger,
        soft=soft,
    )


@router.put(
    "/{trigger_id}}" + PIPELINE_SNAPSHOTS + "/{snapshot_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def attach_trigger_to_snapshot(
    trigger_id: UUID,
    snapshot_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Attaches a trigger to a snapshot.

    Args:
        trigger_id: The ID of the trigger.
        snapshot_id: The ID of the snapshot.
    """
    verify_permission_for_model(
        model=zen_store().get_trigger(trigger_id=trigger_id, hydrate=True),
        action=Action.UPDATE,
    )

    zen_store().attach_trigger_to_snapshot(
        trigger_id=trigger_id,
        snapshot_id=snapshot_id,
    )


@router.delete(
    "/{trigger_id}}" + PIPELINE_SNAPSHOTS + "/{snapshot_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def detach_trigger_from_snapshot(
    trigger_id: UUID,
    snapshot_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Detaches a trigger from a snapshot.

    Args:
        trigger_id: The ID of the trigger.
        snapshot_id: The ID of the snapshot.
    """
    verify_permission_for_model(
        model=zen_store().get_trigger(trigger_id=trigger_id, hydrate=True),
        action=Action.UPDATE,
    )

    zen_store().detach_trigger_from_snapshot(
        trigger_id=trigger_id,
        snapshot_id=snapshot_id,
    )
