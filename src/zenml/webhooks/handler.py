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
"""Event handler contract for trusted webhook events."""

from abc import abstractmethod

from zenml.dispatcher import Event, EventHandler
from zenml.webhooks.events import WebhookEvent


class WebhookEventHandler(EventHandler):
    """Base handler for trusted webhook events."""

    def handle_event(self, event: Event) -> None:
        """Route trusted webhook events to the specialized handler.

        Args:
            event: The dispatched event envelope.
        """
        if isinstance(event, WebhookEvent):
            self.handle_webhook_event(event)

    @abstractmethod
    def handle_webhook_event(self, event: WebhookEvent) -> None:
        """Handle a trusted webhook event.

        Args:
            event: The trusted webhook event.
        """
