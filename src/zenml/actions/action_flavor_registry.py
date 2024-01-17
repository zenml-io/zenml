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
"""Registry for all action configurations."""
from typing import TYPE_CHECKING, Any, Dict, Type

from zenml.logger import get_logger

logger = get_logger(__name__)
if TYPE_CHECKING:
    from zenml.actions.base_action_flavor import BaseActionFlavor


class ActionFlavorRegistry:
    """Registry for action configurations."""

    def __init__(self) -> None:
        """Initialize the action flavor registry."""
        self.action_flavors: Dict[Type[Any], Type[
            "BaseActionFlavor"]] = {}

    def register_action_flavor(
        self, key: Type[Any], type_: Type["BaseActionFlavor"]
    ) -> None:
        """Registers a new action.

        Args:
            key: Indicates the type of object.
            type_: A BaseActionConfiguration subclass.
        """
        if key not in self.action_flavors:
            self.action_flavors[key] = type_
            logger.debug(f"Registered action configuration {type_} for {key}")
        else:
            logger.debug(
                f"Found existing action configuration class for {key}: "
                f"{self.action_flavors[key]}. "
                f"Skipping registration of {type_}."
            )

    def get_action_flavor(self, key: Type[Any]) -> Type[
        "BaseActionFlavor"]:
        """Get a single action based on the key.

        Args:
            key: Indicates the type of object.

        Returns:
            `BaseActionConfiguration` subclass that was registered for this key.
        """
        for class_ in key.__mro__:
            action = self.action_flavors.get(class_, None)
            if action:
                return action

        raise KeyError(f"No action configured for type {key}")

    def get_all_action_flavors(
        self,
    ) -> Dict[Type[Any], Type["BaseActionFlavor"]]:
        """Get all registered action flavors.

        Returns:
            A dictionary of registered action flavors.
        """
        return self.action_flavors

    def is_registered(self, key: Type[Any]) -> bool:
        """Returns if a action class is registered for the given type.

        Args:
            key: Indicates the type of object.

        Returns:
            True if a action is registered for the given type, False
            otherwise.
        """
        return any(issubclass(key, type_) for type_ in self.action_flavors)

action_flavor_registry = ActionFlavorRegistry()
