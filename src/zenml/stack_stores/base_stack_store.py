#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from zenml.enums import StackComponentFlavor, StackComponentType
from zenml.exceptions import StackComponentExistsError, StackExistsError
from zenml.logger import get_logger
from zenml.stack import Stack, StackComponent
from zenml.stack_stores.models import StackConfiguration

logger = get_logger(__name__)


class BaseStackStore(ABC):
    """Base class for accessing data in ZenML Repository and new Service."""

    # Interface:

    @property
    @abstractmethod
    def version(self) -> str:
        """Get the ZenML version."""

    @property
    @abstractmethod
    def active_stack_name(self) -> str:
        """The name of the active stack for this repository."""

    @abstractmethod
    def activate_stack(self, name: str) -> None:
        """Activates the stack for the given name."""

    @abstractmethod
    def get_stack_configuration(self, name: str) -> StackConfiguration:
        """Fetches a stack configuration."""

    @property
    @abstractmethod
    def stack_configurations(self) -> Dict[str, StackConfiguration]:
        """Configuration for all stacks registered in this repository."""

    @abstractmethod
    def create_stack(
        self, name: str, stack_configuration: StackConfiguration
    ) -> None:
        """Add a stack to storage"""

    @abstractmethod
    def delete_stack(self, name: str) -> None:
        """Delete a stack from storage."""

    @abstractmethod
    def get_component_config(
        self, component_type: StackComponentType, name: str
    ) -> Tuple[StackComponentFlavor, Any]:
        """Fetch the flavor and configuration for a stack component."""

    @abstractmethod
    def get_stack_component_names(
        self, component_type: StackComponentType
    ) -> List[str]:
        """Get names of all registered stack components of a given type."""

    @abstractmethod
    def register_stack_component(
        self,
        component: StackComponent,
    ) -> None:
        """Registers a stack component."""

    @abstractmethod
    def delete_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> None:
        """Remove a StackComponent from storage."""

    # Common code:

    @property
    def stacks(self) -> List[Stack]:
        """All stacks registered in this repository."""
        return [
            self._stack_from_configuration(name, conf)
            for name, conf in self.stack_configurations.items()
        ]

    def get_stack(self, name: str) -> Stack:
        """Fetches a stack."""
        return self._stack_from_configuration(
            name, self.get_stack_configuration(name)
        )

    def _stack_from_configuration(
        self, name: str, stack_configuration: StackConfiguration
    ) -> Stack:
        stack_components = {}
        for (
            component_type_name,
            component_name,
        ) in stack_configuration.dict().items():
            component_type = StackComponentType(component_type_name)
            if not component_name:
                # optional component which is not set, continue
                continue
            component = self.get_stack_component(
                component_type=component_type,
                name=component_name,
            )
            stack_components[component_type] = component

        return Stack.from_components(name=name, components=stack_components)

    def register_stack(self, stack: Stack) -> Dict[str, str]:
        """Registers a stack and it's components.

        If any of the stacks' components aren't registered in the repository
        yet, this method will try to register them as well.

        Args:
            stack: The stack to register.

        Raises:
            StackExistsError: If a stack with the same name already exists.
            StackComponentExistsError: If a component of the stack wasn't
                registered and a different component with the same name
                already exists.
        """
        try:
            self.get_stack(stack.name)
        except KeyError:
            pass
        else:
            raise StackExistsError(
                f"Unable to register stack with name '{stack.name}': Found "
                f"existing stack with this name."
            )

        components = {}
        metadata = {}
        for component_type, component in stack.components.items():
            try:
                existing_component = self.get_stack_component(
                    component_type=component_type, name=component.name
                )
                if existing_component.uuid != component.uuid:
                    raise StackComponentExistsError(
                        f"Unable to register one of the stacks components: "
                        f"A component of type '{component_type}' and name "
                        f"'{component.name}' already exists."
                    )
            except KeyError:
                # a component of the stack isn't registered yet -> register it
                self.register_stack_component(component)

            components[component_type.value] = component.name
            metadata[component_type.value] = component.flavor.value

        stack_configuration = StackConfiguration(**components)
        self.create_stack(stack.name, stack_configuration)
        return metadata

    def deregister_stack(self, name: str) -> None:
        """Deregisters a stack.

        Args:
            name: The name of the stack to deregister.

        Raises:
            ValueError: If the stack is the currently active stack for this
                repository.
        """
        if name == self.active_stack_name:
            raise ValueError(f"Unable to deregister active stack '{name}'.")
        self.delete_stack(name)

    def get_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> StackComponent:
        """Fetches a registered stack component."""
        flavor, config = self.get_component_config(component_type, name=name)
        return self._component_from_configuration(
            component_type=component_type,
            component_flavor=flavor,
            component_config=config,
        )

    def _component_from_configuration(
        self,
        component_type: StackComponentType,
        component_flavor: StackComponentFlavor,
        component_config: Any,
    ) -> StackComponent:
        """Build a stack component from the stored configuration."""
        from zenml.stack.stack_component_class_registry import (
            StackComponentClassRegistry,
        )

        component_class = StackComponentClassRegistry.get_class(
            component_type=component_type, component_flavor=component_flavor
        )
        return component_class.parse_obj(component_config)

    def get_stack_components(
        self, component_type: StackComponentType
    ) -> List[StackComponent]:
        """Fetches all registered stack components of the given type."""
        return [
            self.get_stack_component(component_type=component_type, name=name)
            for name in self.get_stack_component_names(component_type)
        ]

    def deregister_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> None:
        """Deregisters a stack component.

        Args:
            component_type: The type of the component to deregister.
            name: The name of the component to deregister.
        """
        for stack_name, stack_config in self.stack_configurations.items():
            if stack_config.contains_component(
                component_type=component_type, name=name
            ):
                raise ValueError(
                    f"Unable to deregister stack component (type: "
                    f"{component_type}, name: {name}) that is part of a "
                    f"registered stack (stack name: '{stack_name}')."
                )
        self.delete_stack_component(component_type, name=name)
