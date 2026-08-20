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
"""Tests for webhook event consumer notification."""

from uuid import uuid4

from zenml.enums import WebhookType
from zenml.webhooks import (
    WebhookEvent,
    WebhookEventConsumer,
    notify_webhook_event_consumers,
    register_webhook_event_consumer,
    unregister_webhook_event_consumer,
)


class _RecordingConsumer(WebhookEventConsumer):
    """Consumer that records received events."""

    def __init__(self) -> None:
        self.events: list[WebhookEvent] = []

    def consume(self, event: WebhookEvent) -> None:
        """Record one event."""
        self.events.append(event)


class _FailingConsumer(WebhookEventConsumer):
    """Consumer that fails for every event."""

    def consume(self, event: WebhookEvent) -> None:
        """Raise a consumer failure."""
        raise RuntimeError("consumer failed")


def test_webhook_consumers_are_failure_isolated() -> None:
    """One consumer failure must not block subsequent consumers."""
    event = WebhookEvent(
        project_id=uuid4(),
        webhook_integration_id=uuid4(),
        webhook_type=WebhookType.GITHUB,
        event_type="pull_request",
        payload={"action": "closed"},
    )
    consumer = _RecordingConsumer()

    failing_consumer = _FailingConsumer()
    register_webhook_event_consumer(failing_consumer)
    register_webhook_event_consumer(consumer)
    try:
        notify_webhook_event_consumers(event)
    finally:
        unregister_webhook_event_consumer(failing_consumer)
        unregister_webhook_event_consumer(consumer)

    assert consumer.events == [event]
