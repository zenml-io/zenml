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
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from zenml.constants import LOCAL_CONFIG_DIRECTORY_NAME
from zenml.enums import StackComponentType
from zenml.exceptions import StackComponentExistsError, StackExistsError
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.stack import Stack, StackComponent
from zenml.stack_stores import BaseStackStore
from zenml.stack_stores.models import StackConfiguration, StackStoreModel
from zenml.utils import yaml_utils

logger = get_logger(__name__)


class LocalStackStore(BaseStackStore):
    def __init__(
        self,
        base_directory: str,
        stack_data: Optional[StackStoreModel] = None,
    ) -> None:
        """Initializes a local stack store instance.

        Args:
            base_directory: root directory of the repository to use for
                stack storage.
            stack_data: optional stack data store object to pre-populate the
                stack store with.
        """
        self._root = base_directory
        if stack_data is not None:
            self.__store = stack_data
        elif fileio.file_exists(self._store_path()):
            config_dict = yaml_utils.read_yaml(self._store_path())
            self.__store = StackStoreModel.parse_obj(config_dict)
        else:
            self.__store = StackStoreModel.empty_store()

    def _get_stack_component_config_path(
        self, component_type: StackComponentType, name: str
    ) -> str:
        """Path to the configuration file of a stack component."""
        path = self.config_directory / component_type.plural / f"{name}.yaml"
        return str(path)

    @property
    def root(self) -> Path:
        """The root directory of this repository."""
        return Path(self._root)

    @property
    def config_directory(self) -> Path:
        """The configuration directory of this repository."""
        return self.root / LOCAL_CONFIG_DIRECTORY_NAME

    def _store_path(self) -> str:
        """Path to the repository configuration file."""
        return str(self.config_directory / "stacks.yaml")

    def _write_store(self) -> None:
        """Writes the repository configuration file."""
        config_dict = json.loads(self.__store.json())
        yaml_utils.write_yaml(self._store_path(), config_dict)

    @property
    def version(self) -> str:
        """Get the ZenML version."""
        return self.__store.version

    @property
    def stacks(self) -> List[Stack]:
        """All stacks registered in this repository."""
        return [self.get_stack(name=name) for name in self.__store.stacks]

    @property
    def stack_configurations(self) -> Dict[str, StackConfiguration]:
        """Configuration for all stacks registered in this repository."""
        return self.__store.stacks.copy()

    @property
    def active_stack_name(self) -> str:
        """The name of the active stack for this repository.

        Raises:
            RuntimeError: If no active stack name is configured.
        """
        if not self.__store.active_stack_name:
            raise RuntimeError(
                "No active stack name configured. Run "
                "`zenml stack set STACK_NAME` to update the active stack."
            )
        return self.__store.active_stack_name

    def activate_stack(self, name: str) -> None:
        """Activates the stack for the given name.

        Args:
            name: Name of the stack to activate.

        Raises:
            KeyError: If no stack exists for the given name.
        """
        if name not in self.__store.stacks:
            raise KeyError(f"Unable to find stack for name '{name}'.")

        self.__store.active_stack_name = name
        self._write_store()

    def get_stack(self, name: str) -> Stack:
        """Fetches a stack.

        Args:
            name: The name of the stack to fetch.

        Raises:
            KeyError: If no stack exists for the given name or one of the
                stacks components is not registered.
        """
        logger.debug("Fetching stack with name '%s'.", name)
        if name not in self.__store.stacks:
            raise KeyError(
                f"Unable to find stack with name '{name}'. Available names: "
                f"{set(self.__store.stacks)}."
            )

        stack_configuration = self.__store.stacks[name]
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
        if stack.name in self.__store.stacks:
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
        self.__store.stacks[stack.name] = stack_configuration
        self._write_store()
        logger.info("Registered stack with name '%s'.", stack.name)
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

        try:
            del self.__store.stacks[name]
            self._write_store()
            logger.info("Deregistered stack with name '%s'.", name)
        except KeyError:
            logger.warning(
                "Unable to deregister stack with name '%s': No stack exists "
                "with this name.",
                name,
            )

    def get_stack_components(
        self, component_type: StackComponentType
    ) -> List[StackComponent]:
        """Fetches all registered stack components of the given type."""
        component_names = self.__store.stack_components[component_type].keys()
        return [
            self.get_stack_component(component_type=component_type, name=name)
            for name in component_names
        ]

    def get_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> StackComponent:
        """Fetches a registered stack component.

        Args:
            component_type: The type of the component to fetch.
            name: The name of the component to fetch.

        Raises:
            KeyError: If no stack component exists for the given type and name.
        """
        components = self.__store.stack_components[component_type]
        if name not in components:
            raise KeyError(
                f"Unable to find stack component (type: {component_type}) "
                f"with name '{name}'. Available names: {set(components)}."
            )

        from zenml.stack.stack_component_class_registry import (
            StackComponentClassRegistry,
        )

        component_flavor = components[name]
        component_class = StackComponentClassRegistry.get_class(
            component_type=component_type, component_flavor=component_flavor
        )
        component_config_path = self._get_stack_component_config_path(
            component_type=component_type, name=name
        )
        component_config = yaml_utils.read_yaml(component_config_path)
        return component_class.parse_obj(component_config)

    def register_stack_component(
        self,
        component: StackComponent,
    ) -> None:
        """Registers a stack component.

        Args:
            component: The component to register.

        Raises:
            StackComponentExistsError: If a stack component with the same type
                and name already exists.
        """
        components = self.__store.stack_components[component.type]
        if component.name in components:
            raise StackComponentExistsError(
                f"Unable to register stack component (type: {component.type}) "
                f"with name '{component.name}': Found existing stack component "
                f"with this name."
            )

        # write the component configuration file
        component_config_path = self._get_stack_component_config_path(
            component_type=component.type, name=component.name
        )
        fileio.create_dir_recursive_if_not_exists(
            os.path.dirname(component_config_path)
        )
        yaml_utils.write_yaml(
            component_config_path, json.loads(component.json())
        )

        # add the component to the repository configuration and write it to disk
        components[component.name] = component.flavor.value
        self._write_store()
        logger.info(
            "Registered stack component with name '%s'.", component.name
        )

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

        components = self.__store.stack_components[component_type]
        try:
            del components[name]
            self._write_store()
            logger.info(
                "Deregistered stack component (type: %s) with name '%s'.",
                component_type.value,
                name,
            )
        except KeyError:
            logger.warning(
                "Unable to deregister stack component (type: %s) with name "
                "'%s': No stack component exists with this name.",
                component_type.value,
                name,
            )
        component_config_path = self._get_stack_component_config_path(
            component_type=component_type, name=name
        )

        if fileio.file_exists(component_config_path):
            fileio.remove(component_config_path)
