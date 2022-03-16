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
import base64
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

import yaml

from zenml.enums import StackComponentType
from zenml.exceptions import StackComponentExistsError, StackExistsError
from zenml.logger import get_logger
from zenml.stack_stores.models import StackComponentWrapper, StackWrapper

logger = get_logger(__name__)


class BaseStackStore(ABC):
    """Base class for accessing data in ZenML Repository and new Service."""

    # Public Interface:

    @property
    @abstractmethod
    def version(self) -> str:
        """Get the ZenML version."""

    @abstractmethod
    def get_stack_configuration(
        self, name: str
    ) -> Dict[StackComponentType, str]:
        """Fetches a stack configuration by name.

        Args:
            name: The name of the stack to fetch.

        Returns:
            Dict[StackComponentType, str] for the requested stack name.

        Raises:
            KeyError: If no stack exists for the given name.
        """

    @property
    @abstractmethod
    def stack_configurations(self) -> Dict[str, Dict[StackComponentType, str]]:
        """Configurations for all stacks registered in this stack store.

        Returns:
            Dictionary mapping stack names to Dict[StackComponentType, str]'s
        """

    @abstractmethod
    def register_stack_component(
        self,
        component: StackComponentWrapper,
    ) -> None:
        """Register a stack component.

        Args:
            component: The component to register.

        Raises:
            StackComponentExistsError: If a stack component with the same type
                and name already exists.
        """

    @abstractmethod
    def deregister_stack(self, name: str) -> None:
        """Delete a stack from storage.

        Args:
            name: The name of the stack to be deleted.
        """

    # Private interface (must be implemented, not to be called by user):

    @abstractmethod
    def _create_stack(
        self, name: str, stack_configuration: Dict[StackComponentType, str]
    ) -> None:
        """Add a stack to storage.

        Args:
            name: The name to save the stack as.
            stack_configuration: Dict[StackComponentType, str] to persist.
        """

    @abstractmethod
    def _get_component_flavor_and_config(
        self, component_type: StackComponentType, name: str
    ) -> Tuple[str, bytes]:
        """Fetch the flavor and configuration for a stack component.

        Args:
            component_type: The type of the component to fetch.
            name: The name of the component to fetch.

        Returns:
            Pair of (flavor, congfiguration) for stack component, as string and
            base64-encoded yaml document, respectively

        Raises:
            KeyError: If no stack component exists for the given type and name.
        """

    @abstractmethod
    def _get_stack_component_names(
        self, component_type: StackComponentType
    ) -> List[str]:
        """Get names of all registered stack components of a given type.

        Args:
            component_type: The type of the component to list names for.

        Returns:
            A list of names as strings.
        """

    @abstractmethod
    def _delete_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> None:
        """Remove a StackComponent from storage.

        Args:
            component_type: The type of component to delete.
            name: Then name of the component to delete.
        """

    # Common code (user facing):

    @property
    def stacks(self) -> List[StackWrapper]:
        """All stacks registered in this stack store."""
        return [
            self._stack_from_dict(name, conf)
            for name, conf in self.stack_configurations.items()
        ]

    def get_stack(self, name: str) -> StackWrapper:
        """Fetch a stack by name.

        Args:
            name: The name of the stack to retrieve.

        Returns:
            StackWrapper instance if the stack exists.

        Raises:
            KeyError: If no stack exists for the given name.
        """
        return self._stack_from_dict(name, self.get_stack_configuration(name))

    def register_stack(self, stack: StackWrapper) -> Dict[str, str]:
        """Register a stack and its components.

        If any of the stacks' components aren't registered in the stack store
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

        def __check_component(
            component: StackComponentWrapper,
        ) -> Tuple[StackComponentType, str]:
            try:
                existing_component = self.get_stack_component(
                    component_type=component.type, name=component.name
                )
                if existing_component.uuid != component.uuid:
                    raise StackComponentExistsError(
                        f"Unable to register one of the stacks components: "
                        f"A component of type '{component.type}' and name "
                        f"'{component.name}' already exists."
                    )
            except KeyError:
                self.register_stack_component(component)
            return component.type, component.name

        stack_configuration = {
            typ: name for typ, name in map(__check_component, stack.components)
        }
        metadata = {c.type.value: c.flavor for c in stack.components}
        self._create_stack(stack.name, stack_configuration)
        return metadata

    def get_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> StackComponentWrapper:
        """Get a registered stack component.

        Raises:
            KeyError: If no component with the requested type and name exists.
        """
        flavor, config = self._get_component_flavor_and_config(
            component_type, name=name
        )
        uuid = yaml.safe_load(base64.b64decode(config).decode())["uuid"]
        return StackComponentWrapper(
            type=component_type,
            flavor=flavor,
            name=name,
            uuid=uuid,
            config=config,
        )

    def get_stack_components(
        self, component_type: StackComponentType
    ) -> List[StackComponentWrapper]:
        """Fetches all registered stack components of the given type.

        Args:
            component_type: StackComponentType to list members of

        Returns:
            A list of StackComponentConfiguration instances.
        """
        return [
            self.get_stack_component(component_type=component_type, name=name)
            for name in self._get_stack_component_names(component_type)
        ]

    def deregister_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> None:
        """Deregisters a stack component.

        Args:
            component_type: The type of the component to deregister.
            name: The name of the component to deregister.

        Raises:
            ValueError: if trying to deregister a component that's part
                of a stack.
        """
        for stack_name, stack_config in self.stack_configurations.items():
            if stack_config.get(component_type) == name:
                raise ValueError(
                    f"Unable to deregister stack component (type: "
                    f"{component_type}, name: {name}) that is part of a "
                    f"registered stack (stack name: '{stack_name}')."
                )
        self._delete_stack_component(component_type, name=name)

    # Common code (internal implementations, private):

    def _stack_from_dict(
        self, name: str, stack_configuration: Dict[StackComponentType, str]
    ) -> StackWrapper:
        """Build a StackWrapper from stored configurations"""
        stack_components = [
            self.get_stack_component(
                component_type=component_type, name=component_name
            )
            for component_type, component_name in stack_configuration.items()
        ]
        return StackWrapper(name=name, components=stack_components)
