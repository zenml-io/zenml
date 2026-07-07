# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Provider adapters for webhook authentication and basic validation."""

import hashlib
import hmac
import json
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from zenml.enums import WebhookType


class WebhookAuthenticationError(ValueError):
    """Raised when a webhook signature cannot be authenticated."""


class WebhookPayloadError(ValueError):
    """Raised when a webhook payload fails fundamental validation."""


class WebhookEvent(BaseModel):
    """Authenticated provider event produced by an intake adapter."""

    webhook_type: WebhookType
    event_type: str
    delivery_id: str | None = None
    payload: dict[str, Any]


class BaseWebhookAdapter(ABC):
    """Base class for provider-specific webhook adapters."""

    webhook_type: WebhookType
    signature_header: str
    event_header: str
    delivery_header: str

    def validate(
        self, body: bytes, headers: Mapping[str, str], secret: str
    ) -> WebhookEvent:
        """Authenticate and structurally validate a provider event.

        Args:
            body: The exact raw request body.
            headers: The request headers.
            secret: The integration signing secret.

        Returns:
            The authenticated webhook event.

        Raises:
            WebhookAuthenticationError: If the signature is invalid.
            WebhookPayloadError: If the event metadata or payload is invalid.
        """  # noqa: DOC502
        self.authenticate(body=body, headers=headers, secret=secret)
        return self.parse(body=body, headers=headers)

    def parse(self, body: bytes, headers: Mapping[str, str]) -> WebhookEvent:
        """Structurally validate and parse a provider event.

        Args:
            body: The exact raw request body.
            headers: The request headers.

        Returns:
            The parsed webhook event.

        Raises:
            WebhookPayloadError: If the event metadata or payload is invalid.
        """
        event_type = headers.get(self.event_header)
        if not event_type:
            raise WebhookPayloadError(
                f"Missing required {self.event_header} header."
            )
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise WebhookPayloadError(
                "Request body must be valid JSON."
            ) from error
        if not isinstance(payload, dict):
            raise WebhookPayloadError(
                "Request body must contain a top-level JSON object."
            )
        return WebhookEvent(
            webhook_type=self.webhook_type,
            event_type=event_type,
            delivery_id=headers.get(self.delivery_header),
            payload=payload,
        )

    @abstractmethod
    def authenticate(
        self, body: bytes, headers: Mapping[str, str], secret: str
    ) -> None:
        """Authenticate the raw request body.

        Args:
            body: The exact raw request body.
            headers: The request headers.
            secret: The integration signing secret.
        """


class HMACSHA256WebhookAdapter(BaseWebhookAdapter):
    """Webhook adapter using a sha256-prefixed HMAC signature."""

    def authenticate(
        self, body: bytes, headers: Mapping[str, str], secret: str
    ) -> None:
        """Validate an HMAC-SHA256 signature over the raw request body.

        Args:
            body: The exact raw request body.
            headers: The request headers.
            secret: The integration signing secret.

        Raises:
            WebhookAuthenticationError: If the signature is missing,
                malformed, or invalid.
        """
        signature = headers.get(self.signature_header)
        if not signature or not signature.startswith("sha256="):
            raise WebhookAuthenticationError(
                f"Missing or malformed {self.signature_header} header."
            )
        expected = (
            "sha256="
            + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        )
        if not hmac.compare_digest(signature, expected):
            raise WebhookAuthenticationError("Invalid webhook signature.")


class GitHubWebhookAdapter(HMACSHA256WebhookAdapter):
    """GitHub webhook adapter."""

    webhook_type = WebhookType.GITHUB
    signature_header = "x-hub-signature-256"
    event_header = "x-github-event"
    delivery_header = "x-github-delivery"


class CustomWebhookAdapter(HMACSHA256WebhookAdapter):
    """ZenML custom webhook adapter."""

    webhook_type = WebhookType.CUSTOM
    signature_header = "x-zenml-signature-256"
    event_header = "x-zenml-event"
    delivery_header = "x-zenml-delivery"


_ADAPTERS: dict[WebhookType, BaseWebhookAdapter] = {
    WebhookType.GITHUB: GitHubWebhookAdapter(),
    WebhookType.CUSTOM: CustomWebhookAdapter(),
}


def get_webhook_adapter(webhook_type: WebhookType) -> BaseWebhookAdapter:
    """Return the registered adapter for a webhook provider type.

    Args:
        webhook_type: The webhook provider type.

    Returns:
        The registered provider adapter.
    """
    return _ADAPTERS[webhook_type]
