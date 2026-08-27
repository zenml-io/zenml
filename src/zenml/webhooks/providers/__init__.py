#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Built-in webhook providers and their resolver."""

from zenml.enums import WebhookType
from zenml.webhooks.providers.base import (
    BaseWebhookProvider,
    WebhookAuthenticationError,
    WebhookPayloadError,
    WebhookPreValidationResult,
    WebhookTargetEvent,
    WebhookTriggerConfiguration,
)
from zenml.webhooks.providers.custom import CustomWebhookProvider
from zenml.webhooks.providers.github import GitHubWebhookProvider

_PROVIDERS: dict[WebhookType, BaseWebhookProvider] = {
    WebhookType.GITHUB: GitHubWebhookProvider(),
    WebhookType.CUSTOM: CustomWebhookProvider(),
}


def get_webhook_provider(webhook_type: WebhookType) -> BaseWebhookProvider:
    """Get the built-in provider for a webhook type.

    Args:
        webhook_type: The closed webhook type identifier.

    Returns:
        The stateless webhook provider.
    """
    return _PROVIDERS[webhook_type]


__all__ = [
    "BaseWebhookProvider",
    "CustomWebhookProvider",
    "GitHubWebhookProvider",
    "WebhookAuthenticationError",
    "WebhookPayloadError",
    "WebhookPreValidationResult",
    "WebhookTargetEvent",
    "WebhookTriggerConfiguration",
    "get_webhook_provider",
]
