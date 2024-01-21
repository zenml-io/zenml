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
from typing import Any

from zenml.events.base_event_flavor import EventConfig, EventSourceConfig


class BaseEvent:
    """Abstract BaseEvent class that all Event Flavors need to implement."""

    def __init__(
        self,
        flavor: str,
        config: EventSourceConfig,
        *args: Any,
        **kwargs: Any,
    ):
        """Initializes a BaseEvent.

        Args:
            flavor: The flavor of the event.
            config: The configuration needed to create the EventSource.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        self.flavor = flavor
        self._config = config

    @property
    def config(self) -> EventConfig:
        """Returns the configuration of the stack component.

        This should be overwritten by any subclasses that define custom configs
        to return the correct config class.

        Returns:
            The configuration of the stack component.
        """
        return self._config

