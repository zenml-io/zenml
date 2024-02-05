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
import hashlib
import hmac
import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Type

from zenml.enums import PluginSubType
from zenml.event_hub.event_hub import event_hub
from zenml.event_sources.base_event_source import (
    BaseEvent,
    BaseEventSourceFlavor,
    BaseEventSourceHandler,
    EventFilterConfig,
    EventSourceConfig,
)
from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger
from zenml.models import EventSourceResponse

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


# -------------------- Webhook Event Source -----------------------


class BaseWebhookEventSourceHandler(BaseEventSourceHandler, ABC):
    """Base implementation for all Webhook event sources."""

    @property
    @abstractmethod
    def config_class(self) -> Type[WebhookEventSourceConfig]:
        """Returns the webhook event source configuration class.

        Returns:
            The configuration.
        """

    @property
    @abstractmethod
    def filter_class(self) -> Type[WebhookEventFilterConfig]:
        """Returns the webhook event filter configuration class.

        Returns:
            The event filter configuration class.
        """

    def is_valid_signature(
        self, raw_body: bytes, secret_token: str, signature_header: str
    ) -> bool:
        """Verify the SHA256 signature of the payload.

        Args:
            raw_body: original request body to verify
            secret_token: secret token used to generate the signature
            signature_header: signature header to verify (x-hub-signature-256)

        Returns:
            Whether if the signature is valid.
        """
        hash_object = hmac.new(
            secret_token.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256,
        )
        expected_signature = "sha256=" + hash_object.hexdigest()

        if not hmac.compare_digest(expected_signature, signature_header):
            return False
        return True

    @abstractmethod
    def _interpret_event(self, event: Dict[str, Any]) -> BaseEvent:
        """Converts the generic event body into a event-source specific pydantic model.

        Args:
            event: The generic event body

        Return:
            An instance of the event source specific pydantic model.
        """

    def process_webhook_event(
        self,
        event_source: EventSourceResponse,
        raw_body: bytes,
        headers: Dict[str, str],
    ) -> None:
        """Process the incoming webhook event.

        Args:
            event_source: The event source that the event belongs to.
            raw_body: The raw inbound webhook event.
            headers: The headers of the inbound webhook event.
        """
        # For now assume the x-hub-signature-256 authentication method
        # is used for all webhook events.
        signature_header = headers.get("x-hub-signature-256")
        if not signature_header:
            raise AuthorizationException(
                "x-hub-signature-256 header is missing!"
            )

        # For now assume all webhook events are json encoded and parse
        # the body as such.
        try:
            json_body = json.loads(raw_body)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON body received: {e}")

        # Temporary solution to get the secret value for the Event Source
        webhook_secret_id = event_source.configuration["webhook_secret_id"]
        try:
            secret_value = self.zen_store.get_secret(
                secret_id=webhook_secret_id
            ).secret_values["webhook_secret"]
        except KeyError:
            logger.exception(
                f"Could not retrieve secret value for secret id "
                f"'{webhook_secret_id}'"
            )
            raise AuthorizationException(
                "Could not retrieve webhook signature."
            )

        if not self.is_valid_signature(
            raw_body=raw_body,
            secret_token=secret_value,
            signature_header=signature_header,
        ):
            raise AuthorizationException("Request signatures didn't match!")

        event = self._interpret_event(json_body)

        event_hub.process_event(
            event=event,
            event_source=event_source,
        )


# -------------------- Flavors ----------------------------------


class BaseWebhookEventSourceFlavor(BaseEventSourceFlavor, ABC):
    """Base Event Plugin Flavor to access an event plugin along with its configurations."""

    SUBTYPE: ClassVar[PluginSubType] = PluginSubType.WEBHOOK
