#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Custom webhook provider."""

import logging
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from zenml.enums import WebhookType
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


class CustomWebhookProvider(BaseWebhookProvider):
    """Provider for signed custom JSON webhook deliveries."""

    webhook_type = WebhookType.CUSTOM
    configuration_class = WebhookTriggerConfiguration
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

    def validate_configuration(
        self,
        configuration: WebhookTriggerConfiguration | Mapping[str, Any],
    ) -> WebhookTriggerConfiguration:
        """Require an empty custom target event list.

        Args:
            configuration: The custom trigger configuration.

        Returns:
            The normalized configuration.

        Raises:
            ValueError: If custom filtering was configured.
        """
        config = WebhookTriggerConfiguration.model_validate(configuration)
        if config.target_events:
            raise ValueError(
                "Custom webhook triggers require an empty target_events list."
            )
        return config

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
                configuration = WebhookTriggerConfiguration.model_validate(
                    trigger.configuration
                )
            except ValueError:
                logger.exception(
                    "Skipping defective webhook trigger configuration %s",
                    trigger.id,
                )
                continue
            if configuration.target_events:
                logger.warning(
                    "Skipping unsupported custom target events for trigger %s",
                    trigger.id,
                )
                continue
            matches.append(trigger)
        return matches
