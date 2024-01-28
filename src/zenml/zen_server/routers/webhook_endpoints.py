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
from typing import Any, Dict

from fastapi import APIRouter

from zenml.constants import API, VERSION_1, WEBHOOKS
from zenml.enums import PluginSubType, PluginType
from zenml.event_sources.webhooks.base_webhook_event_plugin import (
    BaseWebhookEventSourcePlugin,
)
from zenml.logger import get_logger
from zenml.plugins.plugin_flavor_registry import plugin_flavor_registry
from zenml.zen_server.utils import handle_exceptions

logger = get_logger(__name__)

router = APIRouter(
    prefix=API + VERSION_1 + WEBHOOKS,
    tags=["webhook"],
)


@router.post(
    "/{flavor_name}",
)
@handle_exceptions
def webhook(flavor_name: str, body: Dict[str, Any]):
    """Webhook that can be used by external tools.

    Args:
        flavor_name: Path param that indicates which plugin flavor will handle the event.
        body: The request body.
    """
    try:
        plugin_cls = plugin_flavor_registry.get_plugin_implementation(
            flavor=flavor_name,
            _type=PluginType.EVENT_SOURCE,
            subtype=PluginSubType.WEBHOOK,
        )
        #
    except KeyError as e:
        # TODO: raise the appropriate exception
        logger.exception(e)
    else:
        assert isinstance(plugin_cls, BaseWebhookEventSourcePlugin)
        plugin_cls.process_event(body)
