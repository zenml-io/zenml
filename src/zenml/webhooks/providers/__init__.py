#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Webhook provider contracts and registry."""

from zenml.webhooks.providers.base import (
    BaseWebhookProvider,
    WebhookAuthenticationError,
    WebhookPayloadError,
    WebhookPreValidationResult,
    WebhookTargetEvent,
    WebhookTriggerConfiguration,
)
from zenml.webhooks.providers.registry import (
    WebhookProviderRegistry,
    get_webhook_provider,
    webhook_provider_registry,
)

__all__ = [
    "BaseWebhookProvider",
    "WebhookAuthenticationError",
    "WebhookPayloadError",
    "WebhookPreValidationResult",
    "WebhookProviderRegistry",
    "WebhookTargetEvent",
    "WebhookTriggerConfiguration",
    "get_webhook_provider",
    "webhook_provider_registry",
]
