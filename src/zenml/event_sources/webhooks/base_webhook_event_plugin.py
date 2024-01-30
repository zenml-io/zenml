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
        self,
        incoming_event: Dict[str, Any],
        raw_body: bytes,
        signature_header: str
    ) -> List[UUID]:
        """Process the incoming event and forward with trigger_ids to event hub.

        Args:
            incoming_event: The inbound event.
            raw_body: Raw body of the incoming request
            signature_header: Signature header sent to the webhook.
        """
        event = self._interpret_event(incoming_event)

        # narrow down to all sources that relate to the repo that
        #  is responsible for the event
        event_sources = self._get_all_relevant_event_sources(
            event=event,
        )

        self.remove_event_sources_with_wrong_signature(
            raw_event_body=raw_body,
            event_sources=event_sources,
            signature_header=signature_header,
        )

        # get all triggers that have matching event filters configured
        if event_sources:
            trigger_ids = self._get_matching_triggers(
                event_sources=event_sources, event=event
            )

            # TODO: Forward the event together with the list of trigger ids
            #  over to the EventHub
            logger.info(
                "An event came in, the following triggers will be"
                " used: %s ",
                trigger_ids,
            )
            return trigger_ids

    def remove_event_sources_with_wrong_signature(
        self,
        event_sources: List[EventSourceResponse],
        raw_event_body: bytes,
        signature_header: str,
    ):
        """Removes all event_sources with mismatching signature.

        Args:
            event_sources: List of theoretically matching event sources.
            raw_event_body: The Body received by the webhook endpoint.
            signature_header: The signature header
        """
        for es in event_sources[:]:  # TO make sure we iterate over a list copy
            if not self.is_valid_signature(
                body=raw_event_body,
                secret_token="asdf",  # TODO: Replace with actual secret
                signature_header=signature_header,
            ):
                logger.info("Request signatures didn't match!")
                event_sources.remove(es)


# -------------------- Flavors ----------------------------------


class BaseWebhookEventSourcePluginFlavor(BaseEventSourcePluginFlavor, ABC):
    """Base Event Plugin Flavor to access an event plugin along with its configurations."""

    SUBTYPE: ClassVar[PluginSubType] = PluginSubType.WEBHOOK
