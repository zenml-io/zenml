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
from typing import Type, Dict, Any, TYPE_CHECKING
from zenml.logger import get_logger

logger = get_logger(__name__)
if TYPE_CHECKING:
    from zenml.events.base_event_flavor import BaseEventFlavor


class EventFlavorRegistry:
    """Registry for event source configurations."""

    def __init__(self) -> None:
        """Initialize the event flavor registry."""
        self.event_source_flavors: Dict[Type[Any], Type[
            "BaseEventFlavor"]] = {}
        self.event_filter_flavors: Dict[Type[Any], Type[
            "BaseEventFlavor"]] = {}

    def register_event_source_flavor(
        self, key: Type[Any], flavor: Type["BaseEventFlavor"]
    ) -> None:
        """Registers a new event_source.

        Args:
            key: Indicates the flavor of the object.
            flavor: A BaseEventConfiguration subclass.
        """
        if key not in self.event_source_flavors:
            self.event_source_flavors[key] = flavor
            logger.debug(f"Registered event source configuration {flavor} for {key}")
        else:
            logger.debug(
                f"Found existing event source configuration class for {key}: "
                f"{self.event_source_flavors[key]}. "
                f"Skipping registration of {flavor}."
            )

    def register_event_filter_flavor(
        self, key: Type[Any], flavor: Type["BaseEventFlavor"]
    ) -> None:
        """Registers a new event_filter.

        Args:
            key: Indicates the flavors of object.
            flavor: A BaseEventConfiguration subclass.
        """
        if key not in self.event_source_flavors:
            self.event_source_flavors[key] = flavor
            logger.debug(f"Registered event source configuration {flavors_} for {key}")
        else:
            logger.debug(
                f"Found existing event source configuration class for {key}: "
                f"{self.event_source_flavors[key]}. "
                f"Skipping registration of {flavor}."
            )

    def get_event_source_flavor(self, key: Type[Any]) -> Type[
        "BaseEventFlavor"]:
        """Get a single event_source based on the key.

        Args:
            key: Indicates the flavors of object.

        Returns:
            `BaseEventConfiguration` subclass that was registered for this key.
        """
        for class_ in key.__mro__:
            event_source = self.event_source_flavors.get(class_, None)
            if event_source:
                return event_source

        raise KeyError(f"No event source configured for flavors {key}")

    def get_event_filter_flavor(self, key: Type[Any]) -> Type[
        "BaseEventFlavor"]:
        """Get a single event_filter based on the key.

        Args:
            key: Indicates the flavors of object.

        Returns:
            `BaseEventConfiguration` subclass that was registered for this key.
        """
        for class_ in key.__mro__:
            event_filter = self.event_filter_flavors.get(class_, None)
            if event_filter:
                return event_filter
        raise KeyError(f"No event filter configured for flavors {key}")

    def get_all_event_source_flavors(
        self,
    ) -> Dict[Type[Any], Type["BaseEventFlavor"]]:
        """Get all registered event_source flavorss.

        Returns:
            A dictionary of registered event_source flavorss.
        """
        return self.event_source_flavors

    def get_all_event_filter_flavors(
        self,
    ) -> Dict[Type[Any], Type["BaseEventFlavor"]]:
        """Get all registered event_filter flavorss.

        Returns:
            A dictionary of registered event_filter flavorss.
        """
        return self.event_filter_flavors

    def is_event_source_registered(self, key: Type[Any]) -> bool:
        """Returns if a event_source class is registered for the given flavors.

        Args:
            key: Indicates the flavors of object.

        Returns:
            True if a event_source is registered for the given flavors, False
            otherwise.
        """
        return any(issubclass(key, flavor) for flavor in self.event_source_flavors)

    def is_event_filter_registered(self, key: Type[Any]) -> bool:
        """Returns if a event_filter class is registered for the given flavors.

        Args:
            key: Indicates the flavors of object.

        Returns:
            True if a event_filter is registered for the given flavors, False
            otherwise.
        """
        return any(issubclass(key, flavors) for flavors in self.event_filter_flavors)


event_configuration_registry = EventFlavorRegistry()
