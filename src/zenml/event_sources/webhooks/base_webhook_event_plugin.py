#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Abstract BaseEvent class that all Event implementations must implement."""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Type
from uuid import UUID

from zenml.enums import PluginSubType
from zenml.event_sources.base_event_source_plugin import (
    BaseEvent,
    BaseEventSourcePlugin,
    BaseEventSourcePluginFlavor,
    EventFilterConfig,
    EventSourceConfig,
)
from zenml.logger import get_logger
from zenml.models import EventSourceRequest, EventSourceResponse

logger = get_logger(__name__)

if TYPE_CHECKING:
    pass


# -------------------- Event Models -----------------------------------


class BaseWebhookEvent(BaseEvent):
    """Base class for all inbound events."""


# -------------------- Configuration Models ----------------------------------


class WebhookEventSourceConfig(EventSourceConfig):
    """The Event Source configuration."""


class WebhookEventFilterConfig(EventFilterConfig):
    """The Event Filter configuration."""


# -------------------- Plugin -----------------------------------


class BaseWebhookEventSourcePlugin(BaseEventSourcePlugin, ABC):
    """Base implementation for all Webhook event sources."""

    @property
    @abstractmethod
    def config_class(self) -> Type[WebhookEventSourceConfig]:
        """Returns the `BasePluginConfig` config.

        Returns:
            The configuration.
        """

    def _create_event_source(
        self, event_source: EventSourceRequest
    ) -> EventSourceResponse:
        """Wraps the zen_store creation method to add plugin specific functionality."""
        secret_key_value = (
            "something"  # TODO: this needs to actually create a zenml secret
        )
        print("Implementation not done:", secret_key_value)
        # event_source_request.secret_id = ... # Here we add the secret_id to the event_source
        created_event_source = self.zen_store.create_event_source(
            event_source=event_source
        )
        # created_event_source.secret_value = ...
        return created_event_source

    @staticmethod
    @abstractmethod
    def is_valid_signature(
        body: bytes, secret_token: str, signature_header: str
    ) -> bool:
        """Verify that the payload was sent from GitHub by validating SHA256.

        Raise and return 403 if not authorized.

        Args:
            body: original request body to verify (request.body())
            secret_token: GitHub app webhook token (WEBHOOK_SECRET)
            signature_header: header received from GitHub (x-hub-signature-256)
        """

    def get_matching_triggers_for_event(
        self, incoming_event: Dict[str, Any], event_source: EventSourceResponse
    ) -> List[UUID]:
        """Process the incoming event and forward with trigger_ids to event hub.

        Args:
            incoming_event: The inbound event.
            event_source: The Event Source
        """
        event = self._interpret_event(incoming_event)

        # get all triggers that have matching event filters configured
        trigger_ids = self._get_matching_triggers(
            event_source=event_source, event=event
        )

        logger.info(
            "An event came in, the following triggers will be" " used: %s ",
            trigger_ids,
        )
        return trigger_ids


# -------------------- Flavors ----------------------------------


class BaseWebhookEventSourcePluginFlavor(BaseEventSourcePluginFlavor, ABC):
    """Base Event Plugin Flavor to access an event plugin along with its configurations."""

    SUBTYPE: ClassVar[PluginSubType] = PluginSubType.WEBHOOK
