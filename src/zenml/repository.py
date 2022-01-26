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
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Optional

from pydantic import BaseModel, validator

import zenml
from zenml.constants import ENV_ZENML_REPOSITORY_PATH
from zenml.enums import StackComponentType
from zenml.exceptions import (
    InitializationException,
    RepositoryNotFoundError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.post_execution import PipelineView
from zenml.stack import Stack, StackComponent
from zenml.utils import yaml_utils
from zenml.utils.analytics_utils import AnalyticsEvent, track, track_event

logger = get_logger(__name__)
LOCAL_CONFIG_DIRECTORY_NAME = ".zen"


class StackConfiguration(BaseModel):
    """Pydantic object used for serializing stack configuration options."""

    orchestrator: str
    metadata_store: str
    artifact_store: str
    container_registry: Optional[str]

    def contains_component(
        self, component_type: StackComponentType, name: str
    ) -> bool:
        """Checks if the stack contains a specific component."""
        return self.dict().get(component_type.value) == name

    class Config:
        """Pydantic configuration class."""

        allow_mutation = False


class RepositoryConfiguration(BaseModel):
    """Pydantic object used for serializing repository configuration options.

    Attributes:
        version: Version of ZenML that was used to create the repository.
        active_stack_name: Optional name of the active stack.
        stacks: Maps stack names to a configuration object containing the
            names and flavors of all stack components.
        stack_components: Contains names and flavors of all registered stack
            components.
    """

    version: str
    active_stack_name: Optional[str]
    stacks: Dict[str, StackConfiguration]
    stack_components: DefaultDict[StackComponentType, Dict[str, str]]

    @classmethod
    def empty_configuration(cls) -> "RepositoryConfiguration":
        """Helper method to create an empty configuration object."""
        return cls(
            version=zenml.__version__,
            stacks={},
            stack_components={},
        )

    @validator("stack_components")
    def _construct_defaultdict(
        cls, stack_components: Dict[StackComponentType, Dict[str, str]]
    ) -> DefaultDict[StackComponentType, Dict[str, str]]:
        """Ensures that `stack_components` is a defaultdict so stack
        components of a new component type can be added without issues."""
        return defaultdict(dict, stack_components)


class Repository:
    """ZenML repository class.

    ZenML repositories store configuration options for ZenML stacks as well as
    their components.
    """

    def __init__(self, root: Optional[Path] = None):
        """Initializes a repository instance.

        Args:
            root: Optional root directory of the repository. If no path is
                given, this function tries to find the repository using the
                environment variable `ZENML_REPOSITORY_PATH` (if set) and
                recursively searching in the parent directories of the current
                working directory.

        Raises:
            RepositoryNotFoundError: If no ZenML repository directory is found.
        """
        self._root = Repository.find_repository(root)

        # load the repository configuration file if it exists, otherwise use
        # an empty configuration as default
        config_path = self._config_path()
        if fileio.file_exists(config_path):
            config_dict = yaml_utils.read_yaml(config_path)
            self.__config = RepositoryConfiguration.parse_obj(config_dict)
        else:
            self.__config = RepositoryConfiguration.empty_configuration()

        if self.version != zenml.__version__:
            # TODO [ENG-366]: Create compatibility table so we don't have to
            #  warn about mismatching repository and ZenML version each time
            logger.warning(
                "This ZenML repository was created with a different version "
                "of ZenML (Repository version: %s, current ZenML version: %s). "
                "In case you encounter any errors, please delete and "
                "reinitialize this repository.",
                self.version,
                zenml.__version__,
            )

    def _config_path(self) -> str:
        """Path to the repository configuration file."""
        return str(self.config_directory / "config.yaml")

    def _get_stack_component_config_path(
        self, component_type: StackComponentType, name: str
    ) -> str:
        """Path to the configuration file of a stack component."""
        path = self.config_directory / component_type.plural / f"{name}.yaml"
        return str(path)

    def _write_config(self) -> None:
        """Writes the repository configuration file."""
        config_dict = json.loads(self.__config.json())
        yaml_utils.write_yaml(self._config_path(), config_dict)

    @staticmethod
    @track(event=AnalyticsEvent.INITIALIZE_REPO)
    def initialize(root: Path = Path.cwd()) -> None:
        """Initializes a new ZenML repository at the given path.

        The newly created repository will contain a single stack with a local
        orchestrator, a local artifact store and a local SQLite metadata store.

        Args:
            root: The root directory where the repository should be created.

        Raises:
            InitializationException: If the root directory already contains a
                ZenML repository.
        """
        logger.debug("Initializing new repository at path %s.", root)
        if Repository.is_repository_directory(root):
            raise InitializationException(
                f"Found existing ZenML repository at path '{root}'."
            )

        config_directory = str(root / LOCAL_CONFIG_DIRECTORY_NAME)
        fileio.create_dir_recursive_if_not_exists(config_directory)

        # register and activate a local stack
        repo = Repository(root=root)
        stack = Stack.default_local_stack()
        repo.register_stack(stack)
        repo.activate_stack(stack.name)

    @property
    def version(self) -> str:
        """The version of the repository."""
        return self.__config.version

    @property
    def root(self) -> Path:
        """The root directory of this repository."""
        return self._root

    @property
    def config_directory(self) -> Path:
        """The configuration directory of this repository."""
        return self.root / LOCAL_CONFIG_DIRECTORY_NAME

    @property
    def stacks(self) -> List[Stack]:
        """All stacks registered in this repository."""
        return [self.get_stack(name=name) for name in self.__config.stacks]

    @property
    def stack_configurations(self) -> Dict[str, StackConfiguration]:
        """Configuration objects for all stacks registered in this repository.

        This property is intended as a quick way to get information about the
        components of the registered stacks without loading all installed
        integrations. The contained stack configurations might be invalid if
        they were modified by hand, to ensure you get valid stacks use
        `repo.stacks()` instead.

        Modifying the contents of the returned dictionary does not actually
        register/deregister stacks, use `repo.register_stack(...)` or
        `repo.deregister_stack(...)` instead.
        """
        return self.__config.stacks.copy()

    @property
    def active_stack(self) -> Stack:
        """The active stack for this repository.

        Raises:
            RuntimeError: If no active stack name is configured.
            KeyError: If no stack was found for the configured name or one
                of the stack components is not registered.
        """
        if not self.__config.active_stack_name:
            raise RuntimeError(
                "No active stack name configured. Run "
                "`zenml stack set STACK_NAME` to update the active stack."
            )

        return self.get_stack(name=self.__config.active_stack_name)

    @property
    def active_stack_name(self) -> str:
        """The name of the active stack for this repository.

        Raises:
            RuntimeError: If no active stack name is configured.
        """
        if not self.__config.active_stack_name:
            raise RuntimeError(
                "No active stack name configured. Run "
                "`zenml stack set STACK_NAME` to update the active stack."
            )
        return self.__config.active_stack_name

    # TODO [ENG-367]: Should we replace the stack name by the actual stack
    #  object? It would be more consistent with the rest of the API but
    #  requires some additional care (checking if the stack + components are
    #  actually registered in this repository). Downside: We would need to
    #  load all the integrations to create the stack object which makes the CLI
    #  command to set the active stack much slower.
    @track(event=AnalyticsEvent.SET_STACK)
    def activate_stack(self, name: str) -> None:
        """Activates the stack for the given name.

        Args:
            name: Name of the stack to activate.

        Raises:
            KeyError: If no stack exists for the given name.
        """
        if name not in self.__config.stacks:
            raise KeyError(f"Unable to find stack for name '{name}'.")

        self.__config.active_stack_name = name
        self._write_config()

    def get_stack(self, name: str) -> Stack:
        """Fetches a stack.

        Args:
            name: The name of the stack to fetch.

        Raises:
            KeyError: If no stack exists for the given name or one of the
                stacks components is not registered.
        """
        logger.debug("Fetching stack with name '%s'.", name)
        if name not in self.__config.stacks:
            raise KeyError(
                f"Unable to find stack with name '{name}'. Available names: "
                f"{set(self.__config.stacks)}."
            )

        stack_configuration = self.__config.stacks[name]
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

    @track(event=AnalyticsEvent.REGISTERED_STACK)
    def register_stack(self, stack: Stack) -> None:
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
        if stack.name in self.__config.stacks:
            raise StackExistsError(
                f"Unable to register stack with name '{stack.name}': Found "
                f"existing stack with this name."
            )

        components = {}
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

        stack_configuration = StackConfiguration(**components)
        self.__config.stacks[stack.name] = stack_configuration
        self._write_config()
        logger.info("Registered stack with name '%s'.", stack.name)

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
            del self.__config.stacks[name]
            self._write_config()
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
        component_names = self.__config.stack_components[component_type].keys()
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
        logger.debug(
            "Fetching stack component of type '%s' with name '%s'.",
            component_type.value,
            name,
        )

        components = self.__config.stack_components[component_type]
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
        components = self.__config.stack_components[component.type]
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
        self._write_config()
        logger.info(
            "Registered stack component with name '%s'.", component.name
        )

        analytics_metadata = {
            "type": component.type.value,
            "flavor": component.flavor.value,
        }
        track_event(
            AnalyticsEvent.REGISTERED_STACK_COMPONENT,
            metadata=analytics_metadata,
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

        components = self.__config.stack_components[component_type]
        try:
            del components[name]
            self._write_config()
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

    # TODO [ENG-368]: Discuss whether we want to unify these two methods.
    @track(event=AnalyticsEvent.GET_PIPELINES)
    def get_pipelines(
        self, stack_name: Optional[str] = None
    ) -> List[PipelineView]:
        """Fetches post-execution pipeline views.

        Args:
            stack_name: If specified, pipelines in the metadata store of the
                given stack are returned. Otherwise pipelines in the metadata
                store of the currently active stack are returned.

        Returns:
            A list of post-execution pipeline views.

        Raises:
            KeyError: If no stack with the given name exists.
        """
        stack_name = stack_name or self.active_stack_name
        metadata_store = self.get_stack(stack_name).metadata_store
        return metadata_store.get_pipelines()

    @track(event=AnalyticsEvent.GET_PIPELINE)
    def get_pipeline(
        self, pipeline_name: str, stack_name: Optional[str] = None
    ) -> Optional[PipelineView]:
        """Fetches a post-execution pipeline view.

        Args:
            pipeline_name: Name of the pipeline.
            stack_name: If specified, pipelines in the metadata store of the
                given stack are returned. Otherwise pipelines in the metadata
                store of the currently active stack are returned.

        Returns:
            A post-execution pipeline view for the given name or `None` if
            it doesn't exist.

        Raises:
            KeyError: If no stack with the given name exists.
        """
        stack_name = stack_name or self.active_stack_name
        metadata_store = self.get_stack(stack_name).metadata_store
        return metadata_store.get_pipeline(pipeline_name)

    @staticmethod
    def is_repository_directory(path: Path) -> bool:
        """Checks whether a ZenML repository exists at the given path."""
        config_dir = path / LOCAL_CONFIG_DIRECTORY_NAME
        return fileio.is_dir(str(config_dir))

    @staticmethod
    def find_repository(path: Optional[Path] = None) -> Path:
        """Finds path of a ZenML repository directory.

        Args:
            path: Optional path to look for the repository. If no path is
                given, this function tries to find the repository using the
                environment variable `ZENML_REPOSITORY_PATH` (if set) and
                recursively searching in the parent directories of the current
                working directory.

        Returns:
            Absolute path to a ZenML repository directory.

        Raises:
            RepositoryNotFoundError: If no ZenML repository is found.
        """
        if not path:
            # try to get path from the environment variable
            env_var_path = os.getenv(ENV_ZENML_REPOSITORY_PATH)
            if env_var_path:
                path = Path(env_var_path)

        if path:
            # explicit path via parameter or environment variable, don't search
            # parent directories
            search_parent_directories = False
            error_message = (
                f"Unable to find ZenML repository at path '{path}'. Make sure "
                f"to create a ZenML repository by calling `zenml init` when "
                f"specifying an explicit repository path in code or via the "
                f"environment variable '{ENV_ZENML_REPOSITORY_PATH}'."
            )
        else:
            # try to find the repo in the parent directories of the current
            # working directory
            path = Path.cwd()
            search_parent_directories = True
            error_message = (
                f"Unable to find ZenML repository in your current working "
                f"directory ({path}) or any parent directories. If you "
                f"want to use an existing repository which is in a different "
                f"location, set the environment variable "
                f"'{ENV_ZENML_REPOSITORY_PATH}'. If you want to create a new "
                f"repository, run `zenml init`."
            )

        def _find_repo_helper(path_: Path) -> Path:
            """Helper function to recursively search parent directories for a
            ZenML repository."""
            if Repository.is_repository_directory(path_):
                return path_

            if not search_parent_directories or fileio.is_root(str(path_)):
                raise RepositoryNotFoundError(error_message)

            return _find_repo_helper(path_.parent)

        return _find_repo_helper(path).resolve()
