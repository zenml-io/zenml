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

from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.constants import (
    API,
    PIPELINE_SNAPSHOTS,
    SCHEDULE_FEATURE,
    TRIGGER_SNAPSHOT_DISPATCH_STATE,
    TRIGGERS,
    VERSION_1,
)
from zenml.enums import SourceType
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    TRIGGER_CREATE_TYPE_UNION,
    TRIGGER_RETURN_TYPE_UNION,
    TRIGGER_UPDATE_TYPE_UNION,
    Page,
    PlatformEventTriggerRequest,
    PlatformEventTriggerUpdate,
    TriggerFilter,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.feature_gate.endpoint_utils import check_entitlement
from zenml.zen_server.pipeline_execution.utils import (
    create_snapshot_from_source,
    validate_snapshot_for_server_execution,
)
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import (
    verify_permission,
    verify_permission_for_model,
)
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1,
    tags=["triggers"],
    responses={401: error_response, 403: error_response},
)


def verify_permissions_for_source_entity(
    source_type: SourceType, source_id: UUID
) -> None:
    """Validation helper for PlatformEventTrigger requests/updates.

    Validates source exists and user has read access to it.

    Args:
        source_type: The type of the entity to validate.
        source_id: The ID of the entity to validate.

    Raises:
        ValueError: If source type is invalid/unexpected.
    """
    if source_type == SourceType.PIPELINE:
        verify_permission_for_model(
            model=zen_store().get_pipeline(source_id),
            action=Action.UPDATE,
        )
    elif source_type == SourceType.PIPELINE_RUN:
        verify_permission_for_model(
            model=zen_store().get_run(run_id=source_id),
            action=Action.UPDATE,
        )
    elif source_type == SourceType.PIPELINE_SNAPSHOT:
        verify_permission_for_model(
            model=zen_store().get_snapshot(snapshot_id=source_id),
            action=Action.UPDATE,
        )
    else:
        raise ValueError(f"Unexpected source type: {format(source_type)}")


@router.post(
    TRIGGERS,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_trigger(
    trigger: TRIGGER_CREATE_TYPE_UNION,
    _: AuthContext = Security(authorize),
) -> TRIGGER_RETURN_TYPE_UNION:
    """Creates a trigger.

    Args:
        trigger: The trigger to create.

    Returns:
        The created trigger.
    """
    if isinstance(trigger, PlatformEventTriggerRequest):
        verify_permissions_for_source_entity(
            source_type=trigger.source_entity.type,
            source_id=trigger.source_entity.id,
        )

    check_entitlement(feature=SCHEDULE_FEATURE)

    return verify_permissions_and_create_entity(
        request_model=trigger,
        create_method=zen_store().create_trigger,
    )


@router.get(
    TRIGGERS,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_triggers(
    trigger_filter_model: TriggerFilter = Depends(
        make_dependable(TriggerFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[TRIGGER_RETURN_TYPE_UNION]:
    """Gets a list of triggers.

    Args:
        trigger_filter_model: Filter model used for pagination, sorting,
            filtering
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        List of trigger objects.
    """
    return verify_permissions_and_list_entities(
        filter_model=trigger_filter_model,
        resource_type=ResourceType.TRIGGER,
        list_method=zen_store().list_triggers,
        hydrate=hydrate,
    )


@router.get(
    TRIGGERS + "/{trigger_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_trigger(
    trigger_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> TRIGGER_RETURN_TYPE_UNION:
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
    TRIGGERS + "/{trigger_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_trigger(
    trigger_id: UUID,
    trigger_update: TRIGGER_UPDATE_TYPE_UNION,
    _: AuthContext = Security(authorize),
) -> TRIGGER_RETURN_TYPE_UNION:
    """Updates the attributes on a specific trigger using its unique id.

    Args:
        trigger_id: ID of the trigger to update.
        trigger_update: the model containing the attributes to update.

    Returns:
        The updated trigger object.
    """
    if isinstance(trigger_update, PlatformEventTriggerUpdate):
        verify_permissions_for_source_entity(
            source_type=trigger_update.source_entity.type,
            source_id=trigger_update.source_entity.id,
        )

    check_entitlement(feature=SCHEDULE_FEATURE)

    return verify_permissions_and_update_entity(
        id=trigger_id,
        update_model=trigger_update,
        get_method=zen_store().get_trigger,
        update_method=zen_store().update_trigger,
    )


@router.delete(
    TRIGGERS + "/{trigger_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_trigger(
    trigger_id: UUID,
    soft: bool = True,
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
    TRIGGERS + "/{trigger_id}" + PIPELINE_SNAPSHOTS + "/{snapshot_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def attach_trigger_to_snapshot(
    trigger_id: UUID,
    snapshot_id: UUID,
    run_configuration: PipelineRunConfiguration | None = None,
    allow_replace: bool = False,
    _: AuthContext = Security(authorize),
) -> None:
    """Attaches a trigger to a snapshot.

    Args:
        trigger_id: The ID of the trigger.
        snapshot_id: The ID of the snapshot.
        run_configuration: Configuration for the follow-up trigger runs.
        allow_replace: Allow replacement if attachment already exists.

    Raises:
        IllegalOperationError: If the trigger is already attached to the snapshot.
    """
    trigger = zen_store().get_trigger(trigger_id=trigger_id, hydrate=True)

    snapshot = zen_store().get_snapshot(snapshot_id=snapshot_id, hydrate=True)

    if trigger.project_id != snapshot.project_id:
        raise IllegalOperationError(
            "Trigger and snapshot must be in the same project"
        )

    if not snapshot.name:
        raise IllegalOperationError(
            "Can not attach a snapshot without name to a trigger."
        )

    snapshot_replaced_id = None

    for s in trigger.snapshots:
        if snapshot_id in {s.source_snapshot_id, s.id}:
            if not allow_replace:
                raise IllegalOperationError(
                    f"Trigger {trigger_id} is already attached to snapshot {snapshot_id}. "
                    f"To attach {snapshot_id} with a different configuration, please detach "
                    f"the current attachment first or use the `allow_replace` flag."
                )
            else:
                snapshot_replaced_id = s.id

    check_entitlement(feature=SCHEDULE_FEATURE)

    verify_permission_for_model(
        model=trigger,
        action=Action.UPDATE,
    )

    verify_permission_for_model(
        model=snapshot,
        action=Action.READ,
    )

    verify_permission(
        resource_type=ResourceType.PIPELINE_SNAPSHOT,
        action=Action.CREATE,
        project_id=snapshot.project_id,
    )

    verify_permission(
        resource_type=ResourceType.PIPELINE_RUN,
        action=Action.CREATE,
        project_id=snapshot.project_id,
    )

    # Validates and creates a runnable snapshot from the source snapshot + run configuration
    build, stack, model_version = validate_snapshot_for_server_execution(
        snapshot=snapshot,
        run_configuration=run_configuration,
    )
    target_snapshot = create_snapshot_from_source(
        snapshot=snapshot,
        stack=stack,
        run_configuration=run_configuration,
    )

    if snapshot_replaced_id is not None:
        zen_store().detach_trigger_from_snapshot(
            trigger_id=trigger_id, snapshot_id=snapshot_replaced_id
        )

    zen_store().attach_trigger_to_snapshot(
        trigger_id=trigger_id,
        snapshot_id=target_snapshot.id,
    )


@router.delete(
    TRIGGERS + "/{trigger_id}" + PIPELINE_SNAPSHOTS + "/{snapshot_id}",
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
    trigger = zen_store().get_trigger(trigger_id=trigger_id, hydrate=True)

    verify_permission_for_model(
        model=trigger,
        action=Action.UPDATE,
    )

    verify_permission_for_model(
        model=zen_store().get_snapshot(snapshot_id=snapshot_id, hydrate=True),
        action=Action.READ,
    )

    zen_store().detach_trigger_from_snapshot(
        trigger_id=trigger_id,
        snapshot_id=snapshot_id,
    )


@router.delete(
    TRIGGERS + "/{trigger_id}" + TRIGGER_SNAPSHOT_DISPATCH_STATE,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def clear_trigger_dispatch_error(
    trigger_id: UUID,
    snapshot_id: UUID | None = None,
    _: AuthContext = Security(authorize),
) -> None:
    """Clears recorded dispatch errors for one or all trigger snapshots.

    Args:
        trigger_id: The ID of the trigger.
        snapshot_id: Optional snapshot ID. If omitted all trigger snapshot
            dispatch errors are cleared.
    """
    trigger = zen_store().get_trigger(trigger_id=trigger_id, hydrate=True)

    verify_permission_for_model(
        model=trigger,
        action=Action.UPDATE,
    )

    zen_store().clear_trigger_dispatch_error(
        trigger_id=trigger_id,
        snapshot_id=snapshot_id,
    )


@router.get(
    "/supported-events",
    responses={422: error_response},
)
def list_supported_events(
    source_type: SourceType,
) -> list[dict[str, str | None]]:
    """Helper endpoint. Lists supported events by source type.

    Args:
        source_type: The source type.

    Returns:
        A list of {"value": "", "description": ""} objects.
    """
    from zenml.enums import PLATFORM_EVENT_REGISTRY

    if source_type not in PLATFORM_EVENT_REGISTRY:
        return []
    return PLATFORM_EVENT_REGISTRY[source_type].described_values()
