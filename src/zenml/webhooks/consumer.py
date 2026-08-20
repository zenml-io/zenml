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
"""Consumer contract and notification helpers for trusted webhook events."""

from abc import ABC, abstractmethod

from zenml.logger import get_logger
from zenml.webhooks.adapters import WebhookEvent

logger = get_logger(__name__)

_webhook_event_consumers: list["WebhookEventConsumer"] = []


class WebhookEventConsumer(ABC):
    """Base class for features that consume trusted webhook events."""

    @abstractmethod
    def consume(self, event: WebhookEvent) -> None:
        """Consume an accepted webhook event.

        Args:
            event: The trusted webhook event.
        """

    @classmethod
    async def create(cls) -> "WebhookEventConsumer":
        """Create a configured webhook event consumer.

        Returns:
            The configured consumer.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            f"{cls.__name__}.create() is not implemented."
        )


def register_webhook_event_consumer(consumer: WebhookEventConsumer) -> None:
    """Add a consumer to the process-wide webhook registry.

    Args:
        consumer: The consumer to register.
    """
    _webhook_event_consumers.append(consumer)


def unregister_webhook_event_consumer(consumer: WebhookEventConsumer) -> None:
    """Remove a consumer from the process-wide webhook registry.

    No-op if the consumer is not registered.

    Args:
        consumer: The consumer to unregister.
    """
    try:
        _webhook_event_consumers.remove(consumer)
    except ValueError:
        pass


def notify_webhook_event_consumers(event: WebhookEvent) -> None:
    """Notify process-wide consumers with per-consumer failure isolation.

    Args:
        event: The trusted webhook event.
    """
    for consumer in list(_webhook_event_consumers):
        try:
            consumer.consume(event)
        except Exception as exc:
            logger.exception(
                "%s failed to consume webhook event",
                consumer.__class__.__name__,
                exc_info=exc,
            )
