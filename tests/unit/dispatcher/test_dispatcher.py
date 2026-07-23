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
"""Tests for event dispatcher webhook fan-out."""

from uuid import uuid4

from zenml.dispatcher import EventDispatcher, EventHandler
from zenml.enums import WebhookType
from zenml.models import PipelineRunResponse
from zenml.webhooks import WebhookEvent


class _RunStatusOnlyHandler(EventHandler):
    """Event handler that does not implement webhook handling."""

    def handle_run_status_update(self, run: PipelineRunResponse) -> None:
        pass


class _WebhookRecordingHandler(_RunStatusOnlyHandler):
    """Event handler that records webhook events."""

    def __init__(self) -> None:
        self.events: list[WebhookEvent] = []

    def handle_webhook_event(self, event: WebhookEvent) -> None:
        self.events.append(event)


class _FailingWebhookHandler(_RunStatusOnlyHandler):
    """Event handler that fails while processing webhook events."""

    def handle_webhook_event(self, event: WebhookEvent) -> None:
        raise RuntimeError("handler failed")


def test_webhook_event_fan_out_is_failure_isolated() -> None:
    """One webhook handler failure does not block remaining handlers."""
    dispatcher = EventDispatcher()
    status_only_handler = _RunStatusOnlyHandler()
    failing_handler = _FailingWebhookHandler()
    recording_handler = _WebhookRecordingHandler()
    handlers = [status_only_handler, failing_handler, recording_handler]
    event = WebhookEvent(
        project_id=uuid4(),
        webhook_integration_id=uuid4(),
        webhook_type=WebhookType.GITHUB,
        event_type="pull_request",
        payload={"action": "closed"},
    )

    for handler in handlers:
        dispatcher.register_event_handler(handler)

    try:
        dispatcher.handle_webhook_event(event)
    finally:
        for handler in handlers:
            dispatcher.unregister_event_handler(handler)

    assert recording_handler.events == [event]
