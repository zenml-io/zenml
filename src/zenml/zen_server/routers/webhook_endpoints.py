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
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from starlette.background import BackgroundTasks

from zenml.constants import API, VERSION_1, WEBHOOKS
from zenml.enums import PluginSubType, PluginType
from zenml.event_hub.event_hub import event_hub
from zenml.logger import get_logger
from zenml.plugins.plugin_flavor_registry import plugin_flavor_registry
from zenml.zen_server.utils import handle_exceptions, zen_store

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
)
@handle_exceptions
def webhook(
    event_source_id: UUID,
    body: Dict[str, Any],
    background_tasks: BackgroundTasks,
    signature_header: Optional[str] = Header(
        None, alias="x-hub-signature-256"
    ),
    raw_body: bytes = Depends(get_body),
):
    """Webhook to receive events from external event sources.

    Args:
        event_source_id: The event_source_id
        body: The request body.
        raw_body: The raw request body
        background_tasks: BackgroundTask fixture
        signature_header: The signature header
    """
    if not signature_header:
        raise HTTPException(
            status_code=403, detail="x-hub-signature-256 header is missing!"
        )

    # Get the Event Source
    try:
        event_source = zen_store().get_event_source(event_source_id)
    except KeyError:
        raise KeyError(
            f"No webhook is registered at "
            f"'{router.prefix}/{event_source_id}'"
        )

    # Validate the signature
    flavor = event_source.flavor
    webhook_cls = plugin_flavor_registry.get_plugin_implementation(
        flavor=flavor,
        _type=PluginType.EVENT_SOURCE,
        subtype=PluginSubType.WEBHOOK,
    )
    if not webhook_cls.is_valid_signature(
        raw_body=raw_body,
        secret_token="asdf",  # event_source.secret,
        signature_header=signature_header,
    ):
        raise HTTPException(
            status_code=403, detail="Request signatures didn't match!"
        )

    # background_tasks.add_task(
    #     event_hub.process_event,
    #     incoming_event=body,
    #     flavor=flavor_name,
    #     event_source_subtype=PluginSubType.WEBHOOK,
    # )
    event_hub.process_event(
        incoming_event=body,
        flavor=flavor,
        event_source=event_source,
        event_source_subtype=PluginSubType.WEBHOOK,
    )
