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
"""Event Handler base functionality."""

from abc import ABC, abstractmethod

from zenml.models import (
    BaseRequest,
    BaseUpdate,
    BaseZenModel,
    ProjectScopedResponse,
)


class EventHandler(ABC):
    """Abstraction for EventHandler classes."""

    def __init__(self, subscriptions: list[type[BaseZenModel]]):
        """Event Handler constructor.

        Args:
            subscriptions: A list of ZenML classes to subscribe to (as events).
        """
        self._subscription = {sub.__name__ for sub in subscriptions}

    def is_subscribed(self, event_cls: type[BaseZenModel] | BaseZenModel):
        """Helper utility - check is event class is one of handler's subscriptions.

        Args:
            event_cls: The event class to check.

        Returns:
            True if the event class is one of handler's subscriptions.
        """
        if isinstance(event_cls, BaseZenModel):
            return event_cls.__class__.__name__ in self._subscription
        return event_cls.__name__ in self._subscription

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @staticmethod
    @abstractmethod
    def create() -> "EventHandler":
        """Factory method.

        Returns:
            An EventHandler instance.
        """
        pass
