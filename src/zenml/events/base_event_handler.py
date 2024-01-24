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
"""Abstract BaseEvent class that all Event implementations must implement."""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, List
from uuid import UUID

from pydantic import BaseModel

from zenml.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.zen_stores.base_zen_store import BaseZenStore

# -------------------- Event Models -----------------------------------


class BaseEvent(BaseModel):
    """Base class for all inbound events."""


# -------------------- Event Handler -----------------------------------


class BaseEventHandler(ABC):
    """Abstract BaseEvent class that all Event Flavors need to implement."""

    def __init__(
        self,
        flavor: str,
        zen_store: "BaseZenStore",
        *args: Any,
        **kwargs: Any,
    ):
        """Initializes a BaseEvent.

        Args:
            flavor: The flavor of the event.
            zen_store: The zen_store to use.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        self.flavor = flavor
        self.zen_store = zen_store

    def process_event(self, event: BaseEvent):
        """Process the incoming event and forward with trigger_ids to event hub.

        Args:
            event: THe inbound event.
        """
        # narrow down to all sources that relate to the repo that is responsible for the event
        event_source_ids = self._get_all_relevant_event_sources(event=event)

        # get all triggers that have matching event filters configured
        if event_source_ids:
            trigger_ids = self._get_matching_triggers(
                event_source_ids=event_source_ids, event=event
            )
            # TODO: Forward the event together with the list of trigger ids over to the EventHub
            logger.info(
                "An %s event came in and will be forwarded to "
                "the following subscriber %s",
                self.flavor,
                trigger_ids,
            )

    @abstractmethod
    def _get_all_relevant_event_sources(self, event: BaseEvent) -> List[UUID]:
        """Filter Event Sources for flavor and flavor specific properties.

        Args:
            event: The inbound Event.

        Returns: A list of all matching Event Source IDs.
        """

    @abstractmethod
    def _get_matching_triggers(
        self, event_source_ids: List[UUID], event: BaseEvent
    ) -> List[UUID]:
        """Get all Triggers with matching event filters.

        Args:
            event_source_ids: All matching event source ids.
            event: The inbound Event.
        """
