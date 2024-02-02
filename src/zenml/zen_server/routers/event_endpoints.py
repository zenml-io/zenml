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
"""Endpoint definitions for event sources."""
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml import (
    EventSourceFilter,
    EventSourceResponse,
    EventSourceUpdate,
    Page,
)
from zenml.constants import API, EVENT_SOURCES, VERSION_1
from zenml.event_sources.base_event_source import BaseEventSource
from zenml.plugins.plugin_flavor_registry import plugin_flavor_registry
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

event_source_router = APIRouter(
    prefix=API + VERSION_1 + EVENT_SOURCES,
    tags=["event-sources"],
    responses={401: error_response, 403: error_response},
)


# -------------------- Event Sources --------------------


@event_source_router.get(
    "",
    response_model=Page[EventSourceResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_event_sources(
    event_source_filter_model: EventSourceFilter = Depends(
        make_dependable(EventSourceFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[EventSourceResponse]:
    """Returns all event_sources.

    Args:
        event_source_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        All event_sources.
    """
    return verify_permissions_and_list_entities(
        filter_model=event_source_filter_model,
        resource_type=ResourceType.TRIGGER,
        list_method=zen_store().list_event_sources,
        hydrate=hydrate,
    )


@event_source_router.get(
    "/{event_source_id}",
    response_model=EventSourceResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_event_source(
    event_source_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> EventSourceResponse:
    """Returns the requested event_source.

    Args:
        event_source_id: ID of the event_source.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The requested event_source.
    """
    return verify_permissions_and_get_entity(
        id=event_source_id,
        get_method=zen_store().get_event_source,
        hydrate=hydrate,
    )


@event_source_router.put(
    "/{event_source_id}",
    response_model=EventSourceResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_event_source(
    event_source_id: UUID,
    event_source_update: EventSourceUpdate,
    _: AuthContext = Security(authorize),
) -> EventSourceResponse:
    """Updates an event_source.

    Args:
        event_source_id: Name of the event_source.
        event_source_update: EventSource to use for the update.

    Returns:
        The updated event_source.
    """
    # TODO: Find a way to not call this get method twice
    event_source = zen_store().get_event_source(
        event_source_id=event_source_id
    )

    event_source_impl = plugin_flavor_registry.get_plugin_implementation(
        event_source.flavor,
        event_source.plugin_type,
        event_source.plugin_subtype,
    )

    assert issubclass(type(event_source_impl), BaseEventSource)  # We know this
    return verify_permissions_and_update_entity(
        id=event_source_id,
        update_model=event_source_update,
        get_method=zen_store().get_event_source,
        update_method=event_source_impl.update_event_source,
    )


@event_source_router.delete(
    "/{event_source_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_event_source(
    event_source_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a event_source.

    Args:
        event_source_id: Name of the event_source.
    """
    verify_permissions_and_delete_entity(
        id=event_source_id,
        get_method=zen_store().get_event_source,
        delete_method=zen_store().delete_event_source,
    )
