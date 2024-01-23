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
from typing import TYPE_CHECKING, Dict, List, Type

from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger

logger = get_logger(__name__)
if TYPE_CHECKING:
    from zenml.actions.base_action_flavor import BaseActionFlavor


class ActionFlavorRegistry:
    """Registry for action configurations."""

    def __init__(self) -> None:
        """Initialize the action flavor registry."""
        self.action_flavors: Dict[str, Type["BaseActionFlavor"]] = {}
        self.register_action_flavors()

    @property
    def builtin_flavors(self) -> List[Type["BaseActionFlavor"]]:
        """A list of all default in-built flavors.

        Returns:
            A list of builtin flavors.
        """
        from zenml.actions.builtin.pipeline_run_action_flavor import (
            PipelineRunActionFlavor,
        )

        flavors = [
            PipelineRunActionFlavor,
        ]
        return flavors

    @property
    def integration_flavors(self) -> List[Type["BaseActionFlavor"]]:
        """A list of all default integration flavors.

        Returns:
            A list of integration flavors.
        """
        integrated_flavors = []
        for _, integration in integration_registry.integrations.items():
            for flavor in integration.action_flavors():
                integrated_flavors.append(flavor)

        return integrated_flavors

    def register_action_flavors(self) -> None:
        """Registers default flavors."""
        for flavor in self.builtin_flavors:
            self.register_action_flavor(flavor().name, flavor)
        for flavor in self.integration_flavors:
            self.register_action_flavor(flavor().name, flavor)

    def register_action_flavor(
        self, key: str, type_: Type["BaseActionFlavor"]
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

    def get_action_flavor(self, key: str) -> Type["BaseActionFlavor"]:
        """Get a single action based on the key.

        Args:
            key: Indicates the type of object.

        Returns:
            `BaseActionConfiguration` subclass that was registered for this key.
        """
        action = self.action_flavors.get(key, None)
        if action:
            return action

        raise KeyError(f"No action configured for type {key}")

    def get_all_action_flavors(
        self,
    ) -> Dict[str, Type["BaseActionFlavor"]]:
        """Get all registered action flavors.

        Returns:
            A dictionary of registered action flavors.
        """
        return self.action_flavors
