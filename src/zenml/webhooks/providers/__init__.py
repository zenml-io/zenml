#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Webhook provider contracts and registry."""

from zenml.webhooks.providers.base import (
    BaseWebhookProvider,
    ParsedWebhookDelivery,
    ParsedWebhookEvent,
    WebhookAuthenticationError,
    WebhookConfiguration,
    WebhookIntakeResponse,
    WebhookPayloadError,
    WebhookPreValidationResult,
    WebhookTargetEvent,
    WebhookTriggerMatch,
)
from zenml.webhooks.providers.registry import (
    WebhookProviderRegistry,
    get_webhook_provider,
    webhook_provider_registry,
)
from zenml.webhooks.providers.types import BuiltinWebhookType

__all__ = [
    "BaseWebhookProvider",
    "BuiltinWebhookType",
    "ParsedWebhookDelivery",
    "ParsedWebhookEvent",
    "WebhookConfiguration",
    "WebhookAuthenticationError",
    "WebhookIntakeResponse",
    "WebhookPayloadError",
    "WebhookPreValidationResult",
    "WebhookProviderRegistry",
    "WebhookTargetEvent",
    "WebhookTriggerMatch",
    "get_webhook_provider",
    "webhook_provider_registry",
]
