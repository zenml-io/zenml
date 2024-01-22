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
"""Registry all event source configurations."""
from typing import TYPE_CHECKING, Dict, List, Type

from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger

logger = get_logger(__name__)
if TYPE_CHECKING:
    from zenml.events.base_event_flavor import BaseEventFlavor


class EventFlavorRegistry:
    """Registry for event source configurations."""

    def __init__(self) -> None:
        """Initialize the event flavor registry."""
        self.event_flavors: Dict[
            str, Type["BaseEventFlavor"]
        ] = {}
        self.register_event_flavors()

    @property
    def builtin_flavors(self) -> List[Type["BaseEventFlavor"]]:
        """A list of all default in-built flavors.

        Returns:
            A list of builtin flavors.
        """
        flavors = []
        return flavors

    @property
    def integration_flavors(self) -> List[Type["BaseEventFlavor"]]:
        """A list of all integration event flavors.

        Returns:
            A list of integration flavors.
        """
        integrated_flavors = []
        for _, integration in integration_registry.integrations.items():
            for flavor in integration.event_flavors():
                integrated_flavors.append(flavor)

        return integrated_flavors

    def register_event_flavors(self) -> None:
        """Registers all flavors."""
        for flavor in self.builtin_flavors:
            self.register_event_flavor(flavor().name, flavor)
        for flavor in self.integration_flavors:
            self.register_event_flavor(flavor().name, flavor)

    def register_event_flavor(
        self, key: str, flavor: Type["BaseEventFlavor"]
    ) -> None:
        """Registers a new event_source.

        Args:
            key: Indicates the flavor of the object.
            flavor: A BaseEventConfiguration subclass.
        """
        if key not in self.event_flavors:
            self.event_flavors[key] = flavor
            logger.debug(
                f"Registered event source configuration {flavor} for {key}"
            )
        else:
            logger.debug(
                f"Found existing event source configuration class for {key}: "
                f"{self.event_flavors[key]}. "
                f"Skipping registration of {flavor}."
            )

    def get_event_flavor(
        self, key: str
    ) -> Type["BaseEventFlavor"]:
        """Get a single event_source based on the key.

        Args:
            key: Indicates the flavors of object.

        Returns:
            `BaseEventConfiguration` subclass that was registered for this key.
        """
        event_source = self.event_flavors.get(key, None)
        if event_source:
            return event_source

        raise KeyError(f"No event source configured for flavors {key}")

    def get_all_event_flavors(
        self,
    ) -> Dict[str, Type["BaseEventFlavor"]]:
        """Get all registered event_source flavorss.

        Returns:
            A dictionary of registered event_source flavorss.
        """
        return self.event_flavors
