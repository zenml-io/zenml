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

from zenml.webhooks.consumer import (
    WebhookEventConsumer,
    notify_webhook_event_consumers,
    register_webhook_event_consumer,
    unregister_webhook_event_consumer,
)
from zenml.webhooks.events import WebhookEvent
from zenml.webhooks.providers import (
    BaseWebhookProvider,
    CustomWebhookProvider,
    GitHubWebhookProvider,
    WebhookAuthenticationError,
    WebhookPayloadError,
    WebhookPreValidationResult,
    WebhookTargetEvent,
    WebhookTriggerConfiguration,
    get_webhook_provider,
)
from zenml.webhooks.urls import get_webhook_intake_url

__all__ = [
    "BaseWebhookProvider",
    "CustomWebhookProvider",
    "GitHubWebhookProvider",
    "WebhookAuthenticationError",
    "WebhookEvent",
    "WebhookEventConsumer",
    "WebhookPayloadError",
    "WebhookPreValidationResult",
    "WebhookTargetEvent",
    "WebhookTriggerConfiguration",
    "get_webhook_provider",
    "get_webhook_intake_url",
    "notify_webhook_event_consumers",
    "register_webhook_event_consumer",
    "unregister_webhook_event_consumer",
]
