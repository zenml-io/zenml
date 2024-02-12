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
    """Base class for event hub implementations."""

    @abstractmethod
    def activate_trigger(self, trigger: TriggerResponse) -> None:
        """Configure the event hub to trigger an action.

        Args:
            trigger: the trigger to activate.
        """

    @abstractmethod
    def deactivate_trigger(self, trigger: TriggerResponse) -> None:
        """Remove a trigger from the event hub.

        Args:
            trigger: the trigger to deactivate.
        """

    @abstractmethod
    def process_event(
        self,
        event: BaseEvent,
        event_source: EventSourceResponse,
    ) -> None:
        """Process an incoming event and trigger all configured actions.

        Args:
            event: The event.
            event_source: The event source that produced the event.
        """
