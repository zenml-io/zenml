#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Base class for event hub implementations."""
from abc import ABC, abstractmethod
from typing import Callable

from zenml import EventSourceResponse
from zenml.event_sources.base_event import (
    BaseEvent,
)
from zenml.logger import get_logger
from zenml.models import (
    TriggerResponse,
)

logger = get_logger(__name__)


class BaseEventHub(ABC):
    """Base class for event hub implementations.

    The event hub is responsible for relaying events from event sources to
    triggers and actions. It functions similarly to a pub/sub system where
    event source handlers publish events and action handlers subscribe to them.

    The event hub also serves to decouple event sources from triggers, allowing
    them to be configured independently and their implementations to be unaware
    of each other.
    """

    @abstractmethod
    def subscribe_action_handler(
        self,
        action_flavor: str,
        action_subtype: str,
        callback: Callable[[BaseEvent], None],
    ) -> None:
        """Subscribe an action handler to the event hub.

        Args:
            action_flavor: the flavor of the action to trigger.
            action_subtype: the subtype of the action to trigger.
            callback: the action to trigger when the trigger is activated.
        """

    @abstractmethod
    def unsubscribe_action_handler(
        self,
        action_flavor: str,
        action_subtype: str,
    ) -> None:
        """Unsubscribe an action handler from the event hub.

        Args:
            action_flavor: the flavor of the action to trigger.
            action_subtype: the subtype of the action to trigger.
        """

    @abstractmethod
    def activate_trigger(self, trigger: TriggerResponse) -> None:
        """Add a trigger to the event hub.

        Configure the event hub to trigger an action when an event is received.

        Args:
            trigger: the trigger to activate.
        """

    @abstractmethod
    def deactivate_trigger(self, trigger: TriggerResponse) -> None:
        """Remove a trigger from the event hub.

        Configure the event hub to stop triggering an action when an event is
        received.

        Args:
            trigger: the trigger to deactivate.
        """

    @abstractmethod
    def publish_event(
        self,
        event: BaseEvent,
        event_source: EventSourceResponse,
    ) -> None:
        """Publish an event to the event hub.

        Args:
            event: The event.
            event_source: The event source that produced the event.
        """
