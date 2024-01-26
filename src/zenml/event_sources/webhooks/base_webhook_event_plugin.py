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
from typing import TYPE_CHECKING, ClassVar, List, Type
from uuid import UUID

from zenml.enums import PluginType
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
    def config_class(self) -> Type[WebhookEventSourceConfig]:
        """Returns the `BasePluginConfig` config.

        Returns:
            The configuration.
        """
        return WebhookEventSourceConfig

    """Abstract BaseEvent class that all Webhook Listeners need to implement."""

    def create_event_source(
        self, event_source_request: EventSourceRequest
    ) -> EventSourceResponse:
        """Wraps the zen_store creation method to add plugin specific functionality."""
        secret_key_value = (
            "something"  # TODO: this needs to actually create a zenml secret
        )
        print("Implementation not done:", secret_key_value)
        # event_source_request.secret_id = ... # Here we add the secret_id to the event_source
        created_event_source = self.zen_store.create_event_source(
            event_source=event_source_request
        )
        # created_event_source.secret_value = ...
        return created_event_source

    def process_event(self, event: BaseEvent):
        """Process the incoming event and forward with trigger_ids to event hub.

        Args:
            event: THe inbound event.
        """
        # narrow down to all sources that relate to the repo that
        #  is responsible for the event
        event_source_ids = self._get_all_relevant_event_sources(
            event=event,
        )

        # get all triggers that have matching event filters configured
        if event_source_ids:
            trigger_ids = self._get_matching_triggers(
                event_source_ids=event_source_ids, event=event
            )
            # TODO: Forward the event together with the list of trigger ids
            #  over to the EventHub
            logger.info(
                "An event came in and will be forwarded to "
                "the following subscriber %s",
                trigger_ids,
            )

    @abstractmethod
    def _get_all_relevant_event_sources(self, event: BaseEvent) -> List[UUID]:
        """Filter Event Sources for flavor and flavor specific properties.

        Args:
            event: The inbound Event.

        Returns: A list of all matching Event Source IDs.
        """

    @abstractmethod
    def _get_matching_triggers(
        self, event_source_ids: List[UUID], event: BaseEvent
    ) -> List[UUID]:
        """Get all Triggers with matching event filters.

        Args:
            event_source_ids: All matching event source ids.
            event: The inbound Event.
        """


# -------------------- Flavors ----------------------------------


class BaseWebhookEventPluginFlavor(BaseEventSourcePluginFlavor, ABC):
    """Base Event Plugin Flavor to access an event plugin along with its configurations."""

    TYPE: ClassVar[PluginType] = PluginType.WEBHOOK_EVENT
