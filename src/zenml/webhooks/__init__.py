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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Webhook provider and trusted event contracts."""

from zenml.webhooks.events import WebhookEvent
from zenml.webhooks.handler import WebhookEventHandler
from zenml.webhooks.intake import WebhookIntakeConfig
from zenml.webhooks.providers import (
    BaseWebhookProvider,
    WebhookAuthenticationError,
    WebhookConfiguration,
    WebhookPayloadError,
    WebhookPreValidationResult,
    WebhookProviderRegistry,
    WebhookTargetEvent,
    get_webhook_provider,
    webhook_provider_registry,
)

__all__ = [
    "BaseWebhookProvider",
    "WebhookConfiguration",
    "WebhookAuthenticationError",
    "WebhookEvent",
    "WebhookEventHandler",
    "WebhookIntakeConfig",
    "WebhookPayloadError",
    "WebhookPreValidationResult",
    "WebhookProviderRegistry",
    "WebhookTargetEvent",
    "get_webhook_provider",
    "webhook_provider_registry",
]
