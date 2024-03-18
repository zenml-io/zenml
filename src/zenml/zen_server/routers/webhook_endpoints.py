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
"""Endpoint definitions for webhooks."""

from typing import Dict
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from zenml.constants import API, VERSION_1, WEBHOOKS
from zenml.enums import PluginSubType, PluginType
from zenml.event_sources.webhooks.base_webhook_event_source import (
    BaseWebhookEventSourceHandler,
)
from zenml.exceptions import AuthorizationException, WebhookInactiveError
from zenml.logger import get_logger
from zenml.zen_server.utils import (
    handle_exceptions,
    plugin_flavor_registry,
    zen_store,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix=API + VERSION_1 + WEBHOOKS,
    tags=["webhook"],
)


async def get_body(request: Request) -> bytes:
    """Get access to the raw body.

    Args:
        request: The request

    Returns:
        The raw request body.
    """
    return await request.body()


@router.post(
    "/{event_source_id}",
    response_model=Dict[str, str],
)
@handle_exceptions
def webhook(
    event_source_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    raw_body: bytes = Depends(get_body),
) -> Dict[str, str]:
    """Webhook to receive events from external event sources.

    Args:
        event_source_id: The event_source_id
        request: The request object
        background_tasks: Background task handler
        raw_body: The raw request body

    Returns:
        Static dict stating that event is received.

    Raises:
        AuthorizationException: If the Event Source does not exist.
        KeyError: If no appropriate Plugin found in the plugin registry
        ValueError: If the id of the Event Source is not actually a webhook event source
        WebhookInactiveError: In case this webhook has been deactivated
    """
    # Get the Event Source
    try:
        event_source = zen_store().get_event_source(event_source_id)
    except KeyError:
        logger.error(
            f"Webhook HTTP request received for unknown event source "
            f"'{event_source_id}'."
        )
        raise AuthorizationException(  # TODO: Are we sure about this error message?
            f"No webhook is registered at "
            f"'{router.prefix}/{event_source_id}'"
        )
    if not event_source.is_active:
        raise WebhookInactiveError(f"Webhook {event_source_id} is inactive.")

    flavor = event_source.flavor
    try:
        plugin = plugin_flavor_registry().get_plugin(
            name=flavor,
            _type=PluginType.EVENT_SOURCE,
            subtype=PluginSubType.WEBHOOK,
        )
    except KeyError:
        logger.error(
            f"Webhook HTTP request received for event source "
            f"'{event_source_id}' and flavor {flavor} but no matching "
            f"plugin was found."
        )
        raise KeyError(
            f"No listener plugin found for event source {event_source_id}."
        )

    if not isinstance(plugin, BaseWebhookEventSourceHandler):
        raise ValueError(
            f"Event Source {event_source_id} is not a valid Webhook event "
            "source!"
        )

    # Pass the raw event and headers to the plugin
    background_tasks.add_task(
        plugin.process_webhook_event,
        event_source=event_source,
        raw_body=raw_body,
        headers=dict(request.headers.items()),
    )

    return {"status": "Event Received."}
