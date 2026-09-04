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
"""Tests for webhook event handler dispatch."""

from uuid import uuid4

from zenml.dispatcher import Event, EventDispatcher
from zenml.webhooks import WebhookEvent, WebhookEventHandler


class _RecordingHandler(WebhookEventHandler):
    """Handler that records webhook events."""

    def __init__(self) -> None:
        self.events: list[WebhookEvent] = []

    def handle_webhook_event(self, event: WebhookEvent) -> None:
        """Record one webhook event."""
        self.events.append(event)


class _FailingHandler(WebhookEventHandler):
    """Handler that fails for every webhook event."""

    def handle_webhook_event(self, event: WebhookEvent) -> None:
        """Raise a handler failure."""
        raise RuntimeError("handler failed")


def test_webhook_handlers_route_events_and_isolate_failures() -> None:
    """Webhook handlers ignore other events and isolate failures."""
    event = WebhookEvent(
        project_id=uuid4(),
        webhook_id=uuid4(),
        webhook_type="github",
        event_type="pull_request",
        payload={"action": "closed"},
    )
    dispatcher = EventDispatcher()
    failing_handler = _FailingHandler()
    recording_handler = _RecordingHandler()
    dispatcher.register_event_handler(failing_handler)
    dispatcher.register_event_handler(recording_handler)
    try:
        dispatcher.dispatch_event(Event())
        dispatcher.dispatch_event(event)
    finally:
        dispatcher.unregister_event_handler(failing_handler)
        dispatcher.unregister_event_handler(recording_handler)

    assert recording_handler.events == [event]
