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
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Optional, Type

from zenml.enums import PluginSubType
from zenml.event_sources.base_event import BaseEvent
from zenml.event_sources.base_event_source import (
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

    @property
    @abstractmethod
    def flavor_class(self) -> "Type[BaseWebhookEventSourceFlavor]":
        """Returns the flavor class of the plugin.

        Returns:
            The flavor class of the plugin.
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

    @abstractmethod
    def _get_webhook_secret(
        self, event_source: EventSourceResponse
    ) -> Optional[str]:
        """Get the webhook secret for the event source.

        Inheriting classes should implement this method to retrieve the webhook
        secret associated with an event source. If a webhook secret is not
        applicable for the event source, this method should return None.

        Args:
            event_source: The event source to retrieve the secret for.

        Return:
            The webhook secret associated with the event source, or None if a
            secret is not applicable.
        """

    def _validate_webhook_event_signature(
        self, raw_body: bytes, headers: Dict[str, str], webhook_secret: str
    ) -> None:
        """Validate the signature of an incoming webhook event.

        Args:
            raw_body: The raw inbound webhook event.
            headers: The headers of the inbound webhook event.
            webhook_secret: The webhook secret to use for signature validation.

        Raises:
            AuthorizationException: If the signature validation fails.
        """
        signature_header = headers.get("x-hub-signature-256") or headers.get(
            "x-hub-signature"
        )
        if not signature_header:
            raise AuthorizationException(
                "x-hub-signature-256 or x-hub-signature header is missing!"
            )

        if not self.is_valid_signature(
            raw_body=raw_body,
            secret_token=webhook_secret,
            signature_header=signature_header,
        ):
            raise AuthorizationException(
                "Webhook signature verification failed!"
            )

    def _load_payload(
        self, raw_body: bytes, headers: Dict[str, str]
    ) -> Dict[Any, Any]:
        """Converts the raw body of the request into a python dictionary.

        Args:
            raw_body: The raw event body.
            headers: The request headers.

        Returns:
            An instance of the event source specific pydantic model.

        Raises:
            ValueError: In case the body can not be parsed.
        """
        # For now assume all webhook events are json encoded and parse
        # the body as such.
        try:
            body_dict: Dict[Any, Any] = json.loads(raw_body)
            return body_dict
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON body received: {e}")

    def process_webhook_event(
        self,
        event_source: EventSourceResponse,
        raw_body: bytes,
        headers: Dict[str, str],
    ) -> None:
        """Process an incoming webhook event.

        Args:
            event_source: The event source that the event belongs to.
            raw_body: The raw inbound webhook event.
            headers: The headers of the inbound webhook event.
        """
        json_body = self._load_payload(raw_body=raw_body, headers=headers)

        webhook_secret = self._get_webhook_secret(event_source)
        if webhook_secret:
            self._validate_webhook_event_signature(
                raw_body=raw_body,
                headers=headers,
                webhook_secret=webhook_secret,
            )

        event = self._interpret_event(json_body)

        self.dispatch_event(
            event=event,
            event_source=event_source,
        )


# -------------------- Flavors ----------------------------------


class BaseWebhookEventSourceFlavor(BaseEventSourceFlavor, ABC):
    """Base Event Plugin Flavor to access an event plugin along with its configurations."""

    SUBTYPE: ClassVar[PluginSubType] = PluginSubType.WEBHOOK
