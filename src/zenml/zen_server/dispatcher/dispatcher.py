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
"""Event dispatcher base functionality."""

from zenml.models import (
    BaseRequest,
    BaseUpdate,
    ProjectScopedResponse,
)
from zenml.zen_server.dispatcher.handler import EventHandler


class EventDispatcher:
    """Event Dispatcher class."""

    def __init__(self, event_handlers: list[EventHandler]):
        """Event Dispatcher constructor.

        Args:
            event_handlers: A list of registered event handlers.
        """
        self._event_handlers = event_handlers

    def handle_update(
        self,
        original: ProjectScopedResponse,
        update: BaseUpdate,
        response: ProjectScopedResponse,
    ) -> None:
        """Handle an update request.

        Args:
            original: The object before the update.
            update: The update payload.
            response: The object after the update.
        """
        for event_handler in self._event_handlers:
            if event_handler.is_subscribed(update):
                event_handler.handle_update(
                    original=original,
                    update=update,
                    response=response,
                )

    def handle_request(
        self,
        request: BaseRequest,
        response: ProjectScopedResponse,
    ) -> None:
        """Handle a create request.

        Args:
            request: The object to create.
            response: The created object.
        """
        for event_handler in self._event_handlers:
            if event_handler.is_subscribed(request):
                event_handler.handle_request(
                    request=request,
                    response=response,
                )
