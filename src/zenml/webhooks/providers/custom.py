#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Custom webhook provider."""

import logging
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, cast

from pydantic import Field

from zenml.webhooks.providers.base import (
    WEBHOOK_MAX_TARGET_EVENTS,
    BaseWebhookProvider,
    WebhookConfiguration,
    WebhookPayloadError,
    WebhookTriggerMatch,
    authenticate_hmac_sha256,
)
from zenml.webhooks.providers.dynamic import (
    DynamicWebhookTargetEvent,
    matches_webhook_target,
)
from zenml.webhooks.providers.types import BuiltinWebhookType

if TYPE_CHECKING:
    from zenml.models import WebhookTriggerResponse
    from zenml.webhooks.events import WebhookEvent

logger = logging.getLogger(__name__)

CUSTOM_SIGNATURE_HEADER = "x-zenml-signature-256"
CUSTOM_EVENT_HEADER = "x-zenml-event"
CUSTOM_DELIVERY_HEADER = "x-zenml-delivery"


class CustomWebhookConfiguration(WebhookConfiguration):
    """Optional dynamic filtering for a custom webhook trigger."""

    target_events: list[DynamicWebhookTargetEvent] | None = Field(
        default=None, max_length=WEBHOOK_MAX_TARGET_EVENTS
    )


class CustomWebhookProvider(BaseWebhookProvider):
    """Provider for signed custom JSON webhook deliveries."""

    webhook_type = BuiltinWebhookType.CUSTOM
    configuration_class = CustomWebhookConfiguration

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
            header=CUSTOM_SIGNATURE_HEADER,
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
        event_type = headers.get(CUSTOM_EVENT_HEADER)
        if not event_type:
            raise WebhookPayloadError(
                f"Missing required {CUSTOM_EVENT_HEADER} header."
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
        return headers.get(CUSTOM_DELIVERY_HEADER)

    def match_triggers(
        self,
        *,
        event: "WebhookEvent",
        candidates: Sequence["WebhookTriggerResponse"],
    ) -> "WebhookTriggerMatch[WebhookTriggerResponse]":
        """Match candidates using optional dynamic custom filters.

        Args:
            event: The trusted custom event.
            candidates: The associated candidate triggers.

        Returns:
            Matching candidates without semantic event metadata.
        """
        matches: list[WebhookTriggerResponse] = []
        for trigger in candidates:
            try:
                configuration = self.validate_configuration(
                    trigger.configuration
                )
            except (TypeError, ValueError):
                logger.exception(
                    "Skipping defective webhook trigger configuration %s",
                    trigger.id,
                )
                continue
            targets = cast(
                CustomWebhookConfiguration, configuration
            ).target_events
            if not targets or any(
                matches_webhook_target(
                    target=target,
                    event_type=event.event_type,
                    payload=event.payload,
                    semantic_matcher=None,
                )
                for target in targets
            ):
                matches.append(trigger)
        return WebhookTriggerMatch(triggers=matches)
