#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Registry for webhook provider implementations."""

import threading

from zenml.logger import get_logger
from zenml.webhooks.providers.base import BaseWebhookProvider

logger = get_logger(__name__)


class WebhookProviderRegistry:
    """Registry for webhook provider implementations."""

    def __init__(self) -> None:
        """Initialize the webhook provider registry."""
        self._provider_classes: dict[str, type[BaseWebhookProvider]] = {}
        self._builtins_registered = False
        self._lock = threading.RLock()

    def register(
        self,
        provider_class: type[BaseWebhookProvider],
        *,
        overwrite: bool = False,
    ) -> None:
        """Register a webhook provider class.

        Args:
            provider_class: The provider class to register.
            overwrite: Whether to replace an existing registration.
        """
        webhook_type = provider_class.webhook_type
        with self._lock:
            if webhook_type in self._provider_classes and not overwrite:
                logger.debug(
                    "Webhook provider type %s is already registered. "
                    "Skipping registration of %s.",
                    webhook_type,
                    provider_class.__name__,
                )
                return

            self._provider_classes[webhook_type] = provider_class
            logger.debug(
                "Registered webhook provider %s for type %s.",
                provider_class.__name__,
                webhook_type,
            )

    def get(self, webhook_type: str) -> BaseWebhookProvider:
        """Instantiate the provider registered for a webhook type.

        Args:
            webhook_type: The webhook type identifier.

        Returns:
            A new provider instance.

        Raises:
            KeyError: If no provider is registered for the webhook type.
        """
        self.register_builtin_providers()
        try:
            provider_class = self._provider_classes[webhook_type]
        except KeyError:
            raise KeyError(
                f"No webhook provider is registered for type {webhook_type}."
            ) from None
        return provider_class()

    def register_builtin_providers(self) -> None:
        """Register the built-in webhook providers once, on demand."""
        with self._lock:
            if self._builtins_registered:
                return

            from zenml.webhooks.providers.clickup import ClickUpWebhookProvider
            from zenml.webhooks.providers.custom import CustomWebhookProvider
            from zenml.webhooks.providers.github import GitHubWebhookProvider
            from zenml.webhooks.providers.slack import SlackWebhookProvider

            self.register(CustomWebhookProvider)
            self.register(GitHubWebhookProvider)
            self.register(ClickUpWebhookProvider)
            self.register(SlackWebhookProvider)
            self._builtins_registered = True


webhook_provider_registry = WebhookProviderRegistry()


def get_webhook_provider(webhook_type: str) -> BaseWebhookProvider:
    """Get the provider registered for a webhook type.

    Args:
        webhook_type: The webhook type identifier.

    Returns:
        A new provider instance.
    """
    return webhook_provider_registry.get(webhook_type)
