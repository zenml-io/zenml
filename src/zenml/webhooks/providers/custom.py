#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Custom webhook provider."""

import logging
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from pydantic import Field

from zenml.webhooks.providers.base import (
    BaseWebhookProvider,
    WebhookPayloadError,
    WebhookTriggerConfiguration,
    authenticate_hmac_sha256,
)

if TYPE_CHECKING:
    from zenml.models import WebhookTriggerResponse
    from zenml.webhooks.events import WebhookEvent

logger = logging.getLogger(__name__)


class CustomWebhookTriggerConfiguration(WebhookTriggerConfiguration):
    """Configuration for an unfiltered custom webhook trigger."""

    target_events: list[Any] = Field(max_length=0)


class CustomWebhookProvider(BaseWebhookProvider):
    """Provider for signed custom JSON webhook deliveries."""

    webhook_type = "custom"
    configuration_class = CustomWebhookTriggerConfiguration
    signature_header = "x-zenml-signature-256"
    event_header = "x-zenml-event"
    delivery_header = "x-zenml-delivery"

    def authenticate(
        self, body: bytes, headers: Mapping[str, str], secret: str
    ) -> None:
        """Authenticate a custom delivery.

        Args:
            body: The raw request body.
            headers: The request headers.
            secret: The signing secret.
        """
        authenticate_hmac_sha256(
            body=body,
            headers=headers,
            secret=secret,
            header=self.signature_header,
        )

    def get_event_type(
        self, payload: dict[str, Any], headers: Mapping[str, str]
    ) -> str:
        """Extract the custom event type.

        Args:
            payload: The parsed payload.
            headers: The request headers.

        Returns:
            The event type.

        Raises:
            WebhookPayloadError: If the event header is missing.
        """
        event_type = headers.get(self.event_header)
        if not event_type:
            raise WebhookPayloadError(
                f"Missing required {self.event_header} header."
            )
        return event_type

    def get_delivery_id(
        self, payload: dict[str, Any], headers: Mapping[str, str]
    ) -> str | None:
        """Extract the optional custom delivery ID.

        Args:
            payload: The parsed payload.
            headers: The request headers.

        Returns:
            The delivery ID, if present.
        """
        return headers.get(self.delivery_header)

    def match_triggers(
        self,
        *,
        event: "WebhookEvent",
        candidates: Sequence["WebhookTriggerResponse"],
    ) -> list["WebhookTriggerResponse"]:
        """Match candidates with valid unfiltered custom configuration.

        Args:
            event: The trusted custom event.
            candidates: The associated candidate triggers.

        Returns:
            Candidates whose stored configuration remains unfiltered.
        """
        matches: list[WebhookTriggerResponse] = []
        for trigger in candidates:
            try:
                self.validate_configuration(trigger.configuration)
            except (TypeError, ValueError):
                logger.exception(
                    "Skipping defective webhook trigger configuration %s",
                    trigger.id,
                )
                continue
            matches.append(trigger)
        return matches
