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
    EventSourceRequest,
    EventSourceResponse,
    EventSourceUpdate,
    Page,
)
from zenml.constants import API, EVENT_SOURCES, VERSION_1
from zenml.enums import PluginType
from zenml.event_sources.base_event_source import BaseEventSourceHandler
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_list_entities,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import (
    dehydrate_response_model,
    verify_permission_for_model,
)
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    plugin_flavor_registry,
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

    def list_event_sources_fn(
        filter_model: EventSourceFilter,
    ) -> Page[EventSourceResponse]:
        """List event sources through their associated plugins.

        Args:
            filter_model: Filter model used for pagination, sorting,
                filtering.

        Returns:
            All event sources.

        Raises:
            ValueError: If the plugin for an event source is not a valid event
                source plugin.
        """
        event_sources = zen_store().list_event_sources(
            event_source_filter_model=filter_model, hydrate=hydrate
        )

        # Process the event sources through their associated plugins
        for idx, event_source in enumerate(event_sources.items):
            event_source_handler = plugin_flavor_registry().get_plugin(
                name=event_source.flavor,
                _type=PluginType.EVENT_SOURCE,
                subtype=event_source.plugin_subtype,
            )

            # Validate that the flavor and plugin_type correspond to an event
            # source implementation
            if not isinstance(event_source_handler, BaseEventSourceHandler):
                raise ValueError(
                    f"Event source plugin {event_source.plugin_subtype} "
                    f"for flavor {event_source.flavor} is not a valid event "
                    "source handler implementation."
                )

            event_sources.items[idx] = event_source_handler.get_event_source(
                event_source, hydrate=hydrate
            )

        return event_sources

    return verify_permissions_and_list_entities(
        filter_model=event_source_filter_model,
        resource_type=ResourceType.EVENT_SOURCE,
        list_method=list_event_sources_fn,
    )


@event_source_router.get(
    "/{event_source_id}",
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

    Raises:
        ValueError: If the plugin for an event source is not a valid event
            source plugin.
    """
    event_source = zen_store().get_event_source(
        event_source_id=event_source_id, hydrate=hydrate
    )

    verify_permission_for_model(event_source, action=Action.READ)

    event_source_handler = plugin_flavor_registry().get_plugin(
        name=event_source.flavor,
        _type=PluginType.EVENT_SOURCE,
        subtype=event_source.plugin_subtype,
    )

    # Validate that the flavor and plugin_type correspond to an event source
    # implementation
    if not isinstance(event_source_handler, BaseEventSourceHandler):
        raise ValueError(
            f"Event source plugin {event_source.plugin_subtype} "
            f"for flavor {event_source.flavor} is not a valid event source "
            "handler implementation."
        )

    event_source = event_source_handler.get_event_source(
        event_source, hydrate=hydrate
    )

    return dehydrate_response_model(event_source)


@event_source_router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_event_source(
    event_source: EventSourceRequest,
    _: AuthContext = Security(authorize),
) -> EventSourceResponse:
    """Creates an event source.

    Args:
        event_source: EventSource to register.

    Returns:
        The created event source.

    Raises:
        ValueError: If the plugin for an event source is not a valid event
            source plugin.
    """
    event_source_handler = plugin_flavor_registry().get_plugin(
        name=event_source.flavor,
        _type=PluginType.EVENT_SOURCE,
        subtype=event_source.plugin_subtype,
    )

    # Validate that the flavor and plugin_type correspond to an event source
    # implementation
    if not isinstance(event_source_handler, BaseEventSourceHandler):
        raise ValueError(
            f"Event source plugin {event_source.plugin_subtype} "
            f"for flavor {event_source.flavor} is not a valid event source "
            "handler implementation."
        )

    return verify_permissions_and_create_entity(
        request_model=event_source,
        create_method=event_source_handler.create_event_source,
    )


@event_source_router.put(
    "/{event_source_id}",
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

    Raises:
        ValueError: If the plugin for an event source is not a valid event
            source plugin.
    """
    event_source = zen_store().get_event_source(
        event_source_id=event_source_id
    )

    verify_permission_for_model(event_source, action=Action.UPDATE)

    event_source_handler = plugin_flavor_registry().get_plugin(
        name=event_source.flavor,
        _type=PluginType.EVENT_SOURCE,
        subtype=event_source.plugin_subtype,
    )

    # Validate that the flavor and plugin_type correspond to an event source
    # implementation
    if not isinstance(event_source_handler, BaseEventSourceHandler):
        raise ValueError(
            f"Event source plugin {event_source.plugin_subtype} "
            f"for flavor {event_source.flavor} is not a valid event source "
            "handler implementation."
        )

    updated_event_source = event_source_handler.update_event_source(
        event_source=event_source,
        event_source_update=event_source_update,
    )

    return dehydrate_response_model(updated_event_source)


@event_source_router.delete(
    "/{event_source_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_event_source(
    event_source_id: UUID,
    force: bool = False,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a event_source.

    Args:
        event_source_id: Name of the event_source.
        force: Flag deciding whether to force delete the event source.

    Raises:
        ValueError: If the plugin for an event source is not a valid event
            source plugin.
    """
    event_source = zen_store().get_event_source(
        event_source_id=event_source_id
    )

    verify_permission_for_model(event_source, action=Action.DELETE)

    event_source_handler = plugin_flavor_registry().get_plugin(
        name=event_source.flavor,
        _type=PluginType.EVENT_SOURCE,
        subtype=event_source.plugin_subtype,
    )

    # Validate that the flavor and plugin_type correspond to an event source
    # implementation
    if not isinstance(event_source_handler, BaseEventSourceHandler):
        raise ValueError(
            f"Event source plugin {event_source.plugin_subtype} "
            f"for flavor {event_source.flavor} is not a valid event source "
            "handler implementation."
        )

    event_source_handler.delete_event_source(
        event_source=event_source,
        force=force,
    )
