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
"""Repository implementation."""

import os
from abc import ABCMeta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, cast
from uuid import UUID

from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    ENV_ZENML_ENABLE_REPO_INIT_WARNINGS,
    ENV_ZENML_REPOSITORY_PATH,
    REPOSITORY_DIRECTORY_NAME,
    handle_bool_env_var,
)
from zenml.environment import Environment
from zenml.exceptions import (
    AlreadyExistsException,
    IllegalOperationError,
    InitializationException,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.models.pipeline_models import PipelineModel, PipelineRunModel
from zenml.utils import io_utils
from zenml.utils.analytics_utils import AnalyticsEvent, track
from zenml.utils.filesync_model import FileSyncModel

if TYPE_CHECKING:
    from zenml.enums import StackComponentType
    from zenml.models import ComponentModel, ProjectModel, StackModel, UserModel
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.stack import Stack, StackComponent
    from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)

# TODO: [server] this is defined in two places now, should be fixed
DEFAULT_STACK_NAME = "default"


class RepositoryConfiguration(FileSyncModel):
    """Pydantic object used for serializing repository configuration options.

    Attributes:
        active_stack_id: Optional name of the active stack.
        active_project_name: Optional name of the active project.
    """

    active_stack_id: Optional[UUID]
    active_project_name: Optional[str]

    class Config:
        """Pydantic configuration class."""

        # Validate attributes when assigning them. We need to set this in order
        # to have a mix of mutable and immutable attributes
        validate_assignment = True
        # Ignore extra attributes from configs of previous ZenML versions
        extra = "ignore"
        # all attributes with leading underscore are private and therefore
        # are mutable and not included in serialization
        underscore_attrs_are_private = True


class RepositoryMetaClass(ABCMeta):
    """Repository singleton metaclass.

    This metaclass is used to enforce a singleton instance of the Repository
    class with the following additional properties:

    * the singleton Repository instance is created on first access to reflect
    the global configuration and local repository configuration.
    * the Repository shouldn't be accessed from within pipeline steps (a warning
    is logged if this is attempted).
    """

    def __init__(cls, *args: Any, **kwargs: Any) -> None:
        """Initialize the Repository class.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.
        """
        super().__init__(*args, **kwargs)
        cls._global_repository: Optional["Repository"] = None

    def __call__(cls, *args: Any, **kwargs: Any) -> "Repository":
        """Create or return the global Repository instance.

        If the Repository constructor is called with custom arguments,
        the singleton functionality of the metaclass is bypassed: a new
        Repository instance is created and returned immediately and without
        saving it as the global Repository singleton.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Repository: The global Repository instance.
        """
        from zenml.steps.step_environment import (
            STEP_ENVIRONMENT_NAME,
            StepEnvironment,
        )

        step_env = cast(
            StepEnvironment, Environment().get_component(STEP_ENVIRONMENT_NAME)
        )

        # `skip_repository_check` is a special kwarg that can be passed to
        # the Repository constructor to silent the message that warns users
        # about accessing external information in their steps.
        if not kwargs.pop("skip_repository_check", False):
            if step_env and step_env.cache_enabled:
                logger.warning(
                    "You are accessing repository information from a step "
                    "that has caching enabled. Future executions of this step "
                    "may be cached even though the repository information may "
                    "be different. You should take this into consideration and "
                    "adjust your step to disable caching if needed. "
                    "Alternatively, use a `StepContext` inside your step "
                    "instead, as covered here: "
                    "https://docs.zenml.io/developer-guide/advanced-usage"
                    "/step-fixtures#step-contexts",
                )

        if args or kwargs:
            return cast("Repository", super().__call__(*args, **kwargs))

        if not cls._global_repository:
            cls._global_repository = cast(
                "Repository", super().__call__(*args, **kwargs)
            )

        return cls._global_repository


class Repository(metaclass=RepositoryMetaClass):
    """ZenML repository class.

    The ZenML repository manages configuration options for ZenML stacks as well
    as their components.
    """

    def __init__(
        self,
        root: Optional[Path] = None,
    ) -> None:
        """Initializes the global repository instance.

        Repository is a singleton class: only one instance can exist. Calling
        this constructor multiple times will always yield the same instance (see
        the exception below).

        The `root` argument is only meant for internal use and testing purposes.
        User code must never pass them to the constructor.
        When a custom `root` value is passed, an anonymous Repository instance
        is created and returned independently of the Repository singleton and
        that will have no effect as far as the rest of the ZenML core code is
        concerned.

        Instead of creating a new Repository instance to reflect a different
        repository root, to change the active root in the global Repository,
        call `Repository().activate_root(<new-root>)`.

        Args:
            root: (internal use) custom root directory for the repository. If
                no path is given, the repository root is determined using the
                environment variable `ZENML_REPOSITORY_PATH` (if set) and by
                recursively searching in the parent directories of the
                current working directory. Only used to initialize new
                repositories internally.
        """
        self._root: Optional[Path] = None
        self._config: Optional[RepositoryConfiguration] = None

        self._set_active_root(root)

    @classmethod
    def get_instance(cls) -> Optional["Repository"]:
        """Return the Repository singleton instance.

        Returns:
            The Repository singleton instance or None, if the Repository hasn't
            been initialized yet.
        """
        return cls._global_repository

    @classmethod
    def _reset_instance(cls, repo: Optional["Repository"] = None) -> None:
        """Reset the Repository singleton instance.

        This method is only meant for internal use and testing purposes.

        Args:
            repo: The Repository instance to set as the global singleton.
                If None, the global Repository singleton is reset to an empty
                value.
        """
        cls._global_repository = repo

    def _set_active_root(self, root: Optional[Path] = None) -> None:
        """Set the supplied path as the repository root.

        If a repository configuration is found at the given path or the
        path, it is loaded and used to initialize the repository.
        If no repository configuration is found, the global configuration is
        used instead to manage the active stack, project etc.

        Args:
            root: The path to set as the active repository root. If not set,
                the repository root is determined using the environment
                variable `ZENML_REPOSITORY_PATH` (if set) and by recursively
                searching in the parent directories of the current working
                directory.
        """
        enable_warnings = handle_bool_env_var(
            ENV_ZENML_ENABLE_REPO_INIT_WARNINGS, True
        )
        self._root = self.find_repository(root, enable_warnings=enable_warnings)

        if not self._root:
            if enable_warnings:
                logger.info("Running without an active repository root.")
        else:
            logger.debug("Using repository root %s.", self._root)
            self._config = self._load_config()

        # Sanitize the repository configuration to reflect the current
        # settings
        self._sanitize_config()

    def _config_path(self) -> Optional[str]:
        """Path to the repository configuration file.

        Returns:
            Path to the repository configuration file or None if the repository
            root has not been initialized yet.
        """
        if not self.config_directory:
            return None
        return str(self.config_directory / "config.yaml")

    def _sanitize_config(self) -> None:
        """Sanitize and save the repository configuration.

        This method is called to ensure that the repository configuration
        doesn't contain outdated information, such as an active stack or
        project that no longer exists.
        """
        from zenml.zen_stores.base_zen_store import DEFAULT_PROJECT_NAME

        if not self._config:
            return

        # Ensure that the current repository active project is still valid
        if self._config.active_project_name:
            try:
                self.zen_store.get_project(self._config.active_project_name)
            except KeyError:
                logger.warning(
                    "Project '%s' not found. Resetting the repository active "
                    "project to the default.",
                    self._config.active_project_name,
                )
                self._config.active_project_name = None
        else:
            logger.warning(
                "Repository active project not set. Resetting it to the default."
            )

        if not self._config.active_project_name:
            self._config.active_project_name = DEFAULT_PROJECT_NAME

        # Auto-select the repository active stack
        if not self._config.active_stack_id:
            logger.warning(
                "The repository active stack is not set. Switching the "
                "repository active stack to the default stack."
            )
            default_stack = self.zen_store.get_default_stack(
                project_name_or_id=self._config.active_project_name,
                user_name_or_id=self.zen_store.default_user_id,
            )
            self._config.active_stack_id = default_stack.id
        else:
            # Ensure that the repository active stack is still valid
            try:
                self.zen_store.get_stack(stack_id=self._config.active_stack_id)
            except KeyError:
                logger.warning(
                    "Stack with id '%s' not found. Switching the repository "
                    "active stack to the default stack.",
                    self._config.active_stack_id,
                )
                default_stack = self.zen_store.get_default_stack(
                    project_name_or_id=self._config.active_project_name,
                    user_name_or_id=self.zen_store.default_user_id,
                )
                self._config.active_stack_id = default_stack.id

    def _load_config(self) -> Optional[RepositoryConfiguration]:
        """Loads the repository configuration from disk.

        This happens if the repository has an active root and the configuration
        file exists. If the configuration file doesn't exist, an empty
        configuration is returned.

        Returns:
            Loaded repository configuration or None if the repository does not
            have an active root.
        """
        config_path = self._config_path()
        if not config_path:
            return None

        # load the repository configuration file if it exists, otherwise use
        # an empty configuration as default
        if fileio.exists(config_path):
            logger.debug(
                f"Loading repository configuration from {config_path}."
            )
        else:
            logger.debug(
                "No repository configuration file found, creating default "
                "configuration."
            )

        return RepositoryConfiguration(config_path)

    @staticmethod
    @track(event=AnalyticsEvent.INITIALIZE_REPO)
    def initialize(
        root: Optional[Path] = None,
    ) -> None:
        """Initializes a new ZenML repository at the given path.

        Args:
            root: The root directory where the repository should be created.
                If None, the current working directory is used.

        Raises:
            InitializationException: If the root directory already contains a
                ZenML repository.
        """
        root = root or Path.cwd()
        logger.debug("Initializing new repository at path %s.", root)
        if Repository.is_repository_directory(root):
            raise InitializationException(
                f"Found existing ZenML repository at path '{root}'."
            )

        config_directory = str(root / REPOSITORY_DIRECTORY_NAME)
        io_utils.create_dir_recursive_if_not_exists(config_directory)
        # Initialize the repository configuration at the custom path
        Repository(root=root)

    @property
    def uses_local_configuration(self) -> bool:
        """Check if the repository is using a local configuration.

        Returns:
            True if the repository is using a local configuration,
            False otherwise.
        """
        return self._config is not None

    @property
    def zen_store(self) -> "BaseZenStore":
        """Shortcut to return the global zen store.

        Returns:
            The global zen store.
        """
        return GlobalConfiguration().zen_store

    @property
    def root(self) -> Optional[Path]:
        """The root directory of this repository.

        Returns:
            The root directory of this repository, or None, if the repository
            has not been initialized.
        """
        return self._root

    @property
    def config_directory(self) -> Optional[Path]:
        """The configuration directory of this repository.

        Returns:
            The configuration directory of this repository, or None, if the
            repository doesn't have an active root.
        """
        if not self.root:
            return None
        return self.root / REPOSITORY_DIRECTORY_NAME

    def activate_root(self, root: Optional[Path] = None) -> None:
        """Set the active repository root directory.

        Args:
            root: The path to set as the active repository root. If not set,
                the repository root is determined using the environment
                variable `ZENML_REPOSITORY_PATH` (if set) and by recursively
                searching in the parent directories of the current working
                directory.
        """
        self._set_active_root(root)

    @property
    def uses_local_active_project(self) -> bool:
        """Check if the repository is using a local active project setting.

        Returns:
            True if the repository is using a local active project setting,
            False
            otherwise.
        """
        return (
            self._config is not None
            and self._config.active_project_name is not None
        )

    def set_active_project(self, project_name: Optional[str] = None) -> None:
        """Set the project for the local repository.

        If no object is passed, this will unset the active project.

        Args:
            project_name: The project name to set as active.
        """
        if project_name:
            self.zen_store.get_project(
                project_name_or_id=project_name
            )  # raises KeyError
        if self._config:
            self._config.active_project_name = project_name
        else:
            # set the active project globally only if the repository doesn't use
            # a local configuration
            GlobalConfiguration().active_project_name = project_name

    @property
    def active_project_name(self) -> Optional[str]:
        """The name of the active project for this repository.

        If no active project is configured locally for the repository, the
        active project in the global configuration is used instead.

        Returns:
            The name of the active project or None, if an active project name is
            set neither in the repository configuration nor in the global
            configuration.
        """
        project_name = None
        if self._config:
            project_name = self._config.active_project_name

        if not project_name:
            project_name = GlobalConfiguration().active_project_name

        if not project_name:
            logger.info(
                "No active project is configured. Run "
                "`zenml project set PROJECT_NAME` to set the active "
                "project."
            )

        return project_name

    @property
    def active_project(self) -> Optional["ProjectModel"]:
        """Get the currently active project of the local repository.

        If no active project is configured locally for the repository, the
        active project in the global configuration is used instead.

        Returns:
            The active project or None, if an active project name is
            set neither in the repository configuration nor in the global
            configuration.
        """
        return self.zen_store.get_project(self.active_project_name)

    @property
    def active_user(self) -> Optional["UserModel"]:
        return self.zen_store.active_user

    @property
    def stacks(self) -> List["StackModel"]:
        """All stacks registered in this repository.

        Returns:
            A list of all stacks registered in this repository.
        """
        return self.zen_store.stacks

    @property
    def stack_configurations(self) -> Dict[str, Dict[str, str]]:
        """Configuration dicts for all stacks registered in this repository.

        This property is intended as a quick way to get information about the
        components of the registered stacks without loading all installed
        integrations. The contained stack configurations might be invalid if
        they were modified by hand, to ensure you get valid stacks use
        `repo.stacks()` instead.

        Modifying the contents of the returned dictionary does not actually
        register/deregister stacks, use `repo.register_stack(...)` or
        `repo.deregister_stack(...)` instead.

        Returns:
            A dictionary containing the configuration of all stacks registered
            in this repository.
        """
        stacks = self.zen_store.list_stacks(
            project_name_or_id=self.active_project_name
        )

        dict_of_stacks = dict()
        for stack in stacks:
            dict_of_stacks[stack.name] = {"shared": str(stack.is_shared)}
            for component_type, component in stack.components.items():
                dict_of_stacks[stack.name][str(component_type)] = component.name

        return dict_of_stacks

    @property
    def active_stack_model(self) -> "StackModel":
        """The model of the active stack for this repository.

        If no active stack is configured locally for the repository, the active
        stack in the global configuration is used instead.

        Returns:
            The model of the active stack for this repository.
        """
        stack_id = None
        if self._config:
            stack_id = self._config.active_stack_id

        if not stack_id:
            stack_id = GlobalConfiguration().active_stack_id

        if not stack_id:
            raise RuntimeError(
                "No active stack is configured. Run "
                "`zenml stack set STACK_NAME` to set the active stack."
            )

        return self.zen_store.get_stack(stack_id=stack_id)

    @property
    def active_stack(self) -> "Stack":
        """The active stack for this repository.

        Returns:
            The active stack for this repository.
        """
        from zenml.stack.stack import Stack

        return Stack.from_model(self.active_stack_model)

    @property
    def uses_local_active_stack(self) -> bool:
        """Check if the repository is using a local active stack setting.

        Returns:
            True if the repository is using a local active stack setting, False
            otherwise.
        """
        return (
            self._config is not None
            and self._config.active_stack_id is not None
        )

    @track(event=AnalyticsEvent.SET_STACK)
    def activate_stack(self, stack: "StackModel") -> None:
        """Activates the stack for the given name.

        Args:
            stack: Model of the stack to activate.
        """
        if self._config:
            self._config.active_stack_id = stack.id

        else:
            # set the active stack globally only if the repository doesn't use
            # a local configuration
            GlobalConfiguration().active_stack_id = stack.id

    def get_stack_by_name(
        self, name: str, is_shared: bool = False
    ) -> "StackModel":
        """Fetches a stack by name within the active stack

        Args:
            name: The name of the stack to fetch.
            is_shared: Boolean whether to get a shared stack or a private stack

        Returns:
            The stack with the given name.
        """
        if is_shared:
            stacks = self.zen_store.list_stacks(
                project_name_or_id=self.active_project.id,
                name=name,
                is_shared=True,
            )
        else:
            # TODO: [server] access the user id in a more elegant way
            stacks = self.zen_store.list_stacks(
                project_name_or_id=self.active_project.id,
                user_name_or_id=self.zen_store.default_user_id,
                # GlobalConfiguration().user_id,
                name=name,
            )

        # TODO: [server] this error handling could be improved
        if not stacks:
            raise KeyError(f"No stack with name '{name}' exists.")
        elif len(stacks) > 1:
            raise RuntimeError(
                f"Multiple stacks have been found for name  '{name}'.", stacks
            )

        return stacks[0]

    def register_stack(self, stack: "StackModel") -> "StackModel":
        """Registers a stack and its components.

        If any of the stack's components aren't registered in the repository
        yet, this method will try to register them as well.

        Args:
            stack: The stack to register.
        """
        # TODO: [server] make sure the stack can be validated here
        if stack.is_valid:
            created_stack = self.zen_store.register_stack(
                user_name_or_id=self.zen_store.default_user_id,
                # TODO: [server] replace with active user
                project_name_or_id=self.active_project.id,
                stack=stack,
            )
            return created_stack
        else:
            raise RuntimeError(
                "Stack configuration is invalid. A valid"
                "stack must contain an Artifact Store and "
                "an Orchestrator."
            )

    def update_stack(self, stack: "StackModel") -> None:
        """Updates a stack and its components.

        Args:
            stack: The new stack to use as the updated version.
        """
        if stack.is_valid:
            self.zen_store.update_stack(stack=stack)
            if self._config.active_stack_id == stack.id:
                self.activate_stack(stack)
        else:
            raise RuntimeError(
                "Stack configuration is invalid. A valid"
                "stack must contain an Artifact Store and "
                "an Orchestrator."
            )

    def deregister_stack(self, stack: "StackModel") -> None:
        """Deregisters a stack.

        Args:
            stack: The model of the stack to deregister.

        Raises:
            ValueError: If the stack is the currently active stack for this
                repository.
        """
        if stack.id == self._config.active_stack_id:
            raise ValueError(
                f"Unable to deregister active stack " f"'{stack.name}'."
            )

        try:
            self.zen_store.delete_stack(stack_id=stack.id)
            logger.info("Deregistered stack with name '%s'.", stack.name)
        except KeyError:
            logger.warning(
                "Unable to deregister stack with name '%s': No stack  "
                "with this name could be found.",
                stack.name,
            )

    def update_stack_component(
        self,
        component: "ComponentModel",
    ) -> None:
        """Updates a stack component.

        Args:
            component: The new component to update with.
        """
        self.zen_store.update_stack_component(component=component)

    def list_stack_components(
        self, component_type: "StackComponentType"
    ) -> List["ComponentModel"]:
        """Fetches all registered stack components of the given type.

        Args:
            component_type: The type of the components to fetch.

        Returns:
            A list of all registered stack components of the given type.
        """
        return self.zen_store.list_stack_components(
            project_name_or_id=self.active_project.id, type=component_type
        )

    def get_stack_component_by_name_and_type(
        self, type: "StackComponentType", name: str, is_shared: bool = False
    ) -> "ComponentModel":
        """Fetches a stack by name within the active stack

        Args:
            type: The type of the stack component
            name: The name of the stack to fetch.
            is_shared: Boolean whether to get a shared stack or a private stack

        Returns:
            The stack with the given name.
        """
        if is_shared:
            components = self.zen_store.list_stack_components(
                project_name_or_id=self.active_project.id,
                name=name,
                type=type,
                is_shared=True,
            )
        else:
            # TODO: [server] access the user id in a more elegant way
            components = self.zen_store.list_stack_components(
                project_name_or_id=self.active_project.id,
                name=name,
                type=type,
                user_name_or_id=self.zen_store.default_user_id,
            )

        # TODO: [server] this error handling could be improved
        if not components:
            raise KeyError(
                f"No stack component of type '{type}' with the name '{name}' exists."
            )
        elif len(components) > 1:
            raise RuntimeError(
                "Multiple components have been found for this name.",
                components,
            )

        return components[0]

    def get_stack_component(self, component_id: UUID) -> "StackComponent":
        """Fetches a registered stack component.

        Args:
            component_id: The id of the component to fetch.

        Returns:
            The registered stack component.
        """
        logger.debug(
            "Fetching stack component with id '%s'.",
            id,
        )
        return self.zen_store.get_stack_component(
            component_id=component_id
        ).to_component()

    def register_stack_component(
        self,
        component: "StackComponent",
    ) -> None:
        """Registers a stack component.

        Args:
            component: The component to register.
        """
        from zenml.models import ComponentModel

        self.zen_store.register_stack_component(
            project_name_or_id=self.active_project.id,
            user_name_or_id=self.zen_store.default_user_id,  # TODO: Do this right
            component=ComponentModel.from_component(component),
        )
        if component.post_registration_message:
            logger.info(component.post_registration_message)

    def deregister_stack_component(
        self, stack_component: "ComponentModel"
    ) -> None:
        """Deregisters a stack component.

        Args:
            id: The id of the component to deregister.
        """
        try:
            self.zen_store.delete_stack_component(
                component_id=stack_component.id
            )
            logger.info(
                "Deregistered stack component (type: %s) with name '%s'.",
                stack_component.type,
                stack_component.name,
            )
        except KeyError:
            logger.warning(
                "Unable to deregister stack component (type: %s) with name "
                "'%s': No stack component with this name could be found.",
                stack_component.type,
                stack_component.name,
            )

    @staticmethod
    def is_repository_directory(path: Path) -> bool:
        """Checks whether a ZenML repository exists at the given path.

        Args:
            path: The path to check.

        Returns:
            True if a ZenML repository exists at the given path,
            False otherwise.
        """
        config_dir = path / REPOSITORY_DIRECTORY_NAME
        return fileio.isdir(str(config_dir))

    @staticmethod
    def find_repository(
        path: Optional[Path] = None, enable_warnings: bool = False
    ) -> Optional[Path]:
        """Search for a ZenML repository directory.

        Args:
            path: Optional path to look for the repository. If no path is
                given, this function tries to find the repository using the
                environment variable `ZENML_REPOSITORY_PATH` (if set) and
                recursively searching in the parent directories of the current
                working directory.
            enable_warnings: If `True`, warnings are printed if the repository
                root cannot be found.

        Returns:
            Absolute path to a ZenML repository directory or None if no
            repository directory was found.
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
            warning_message = (
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
            warning_message = (
                f"Unable to find ZenML repository in your current working "
                f"directory ({path}) or any parent directories. If you "
                f"want to use an existing repository which is in a different "
                f"location, set the environment variable "
                f"'{ENV_ZENML_REPOSITORY_PATH}'. If you want to create a new "
                f"repository, run `zenml init`."
            )

        def _find_repo_helper(path_: Path) -> Optional[Path]:
            """Helper function to recursively search parent directories for a
            ZenML repository.

            Args:
                path_: The path to search.

            Returns:
                Absolute path to a ZenML repository directory or None if no
                repository directory was found.
            """
            if Repository.is_repository_directory(path_):
                return path_

            if not search_parent_directories or io_utils.is_root(str(path_)):
                return None

            return _find_repo_helper(path_.parent)

        repo_path = _find_repo_helper(path)

        if repo_path:
            return repo_path.resolve()
        if enable_warnings:
            logger.warning(warning_message)
        return None

    def get_flavor(
        self, name: str, component_type: "StackComponentType"
    ) -> Type["StackComponent"]:
        """Fetches a registered flavor.

        Args:
            component_type: The type of the component to fetch.
            name: The name of the flavor to fetch.

        Returns:
            The registered flavor.

        Raises:
            KeyError: If no flavor exists for the given type and name.
        """
        logger.debug(
            "Fetching the flavor of type '%s' with name '%s'.",
            component_type,
            name,
        )

        from zenml.stack.flavor_registry import flavor_registry

        zenml_flavors = flavor_registry.get_flavors_by_type(
            component_type=component_type
        )

        # Try to find if there are any custom flavor implementations
        custom_flavors = self.zen_store.list_flavors(
            project_name_or_id=self.active_project_name,
            name=name,
            component_type=component_type,
        )

        # If there is one, check whether the same flavor exists as a default
        # flavor to give out a warning
        if custom_flavors and name in zenml_flavors:
            logger.warning(
                f"There is a custom implementation for the flavor "
                f"'{name}' of a {component_type}, which is currently "
                f"overwriting the same flavor provided by ZenML."
            )

        else:
            if name in zenml_flavors:
                flavor_wrapper = zenml_flavors[name]
            else:
                raise KeyError(
                    f"There is no flavor '{name}' for the type "
                    f"{component_type}"
                )

        return flavor_wrapper.to_flavor()

    def _register_pipeline(
        self, pipeline_name: str, pipeline_configuration: str
    ) -> UUID:
        """Registers a pipeline in the ZenStore within the active project.

        This will do one of the following three things:
        A) If there is no pipeline with this name, register a new pipeline.
        B) If a pipeline exists that has the same config, use that pipeline.
        C) If a pipeline with different config exists, raise an error.

        Args:
            pipeline_name: The name of the pipeline to register.
            pipeline_configuration: The configuration of the pipeline.

        Returns:
            The id of the existing or newly registered pipeline.

        Raises:
            AlreadyExistsError: If there is an existing pipeline in the project
                with the same name but a different configuration.
        """
        try:
            existing_pipeline = self.zen_store.get_pipeline_in_project(
                pipeline_name=pipeline_name,
                project_name_or_id=self.active_project.id,
            )

        # A) If there is no pipeline with this name, register a new pipeline.
        except KeyError:
            pipeline = PipelineModel(
                name=pipeline_name,
                owner=self.active_user.id,
                project_id=self.active_project.id,
                configuration=pipeline_configuration,
            )
            pipeline = self.zen_store.create_pipeline(
                project_name_or_id=self.active_project.id, pipeline=pipeline
            )
            logger.info(f"Registered new pipeline with name {pipeline.name}.")
            return pipeline.id

        # B) If a pipeline exists that has the same config, use that pipeline.
        if pipeline_configuration == existing_pipeline.configuration:
            logger.debug("Did not register pipeline since it already exists.")
            return existing_pipeline.id

        # C) If a pipeline with different config exists, raise an error.
        error_msg = (
            f"Cannot run pipeline '{pipeline_name}' since this name has "
            "already been registered with a different pipeline "
            "configuration. You have three options to resolve this issue: "
            "1) You can register a new pipeline by changing the 'name' "
            "argument of your pipeline, e.g., via "
            '`my_pipeline(step1=..., ..., name="My New Pipeline Name")`. '
            "2) You can execute the current run without linking it to any "
            "pipeline by setting the 'unlisted' argument to `True`, e.g., "
            "via `my_pipeline_instance.run(unlisted=True)`. "
            "Unlisted runs are not linked to any pipeline, but are still "
            "tracked by ZenML and can be accessed via the 'All Runs' tab. "
            "3) You can delete the existing pipeline via "
            f"`zenml pipeline delete {pipeline_name}`. This will then "
            "change all existing runs of this pipeline to become unlisted."
        )
        raise AlreadyExistsException(error_msg)

    def register_pipeline_run(
        self,
        pipeline_name: str,
        pipeline_configuration: Dict[str, str],
        runtime_configuration: "RuntimeConfiguration",
        stack_id: UUID,
        unlisted: bool = False,
    ) -> None:
        """Registers a pipeline run in the ZenStore.

        Args:
            pipeline_name: The name of the pipeline.
            pipeline_configuration: The configuration of the pipeline.
            runtime_configuration: The runtime configuration of the pipeline.
            stack_id: The ID of the stack that was used to run the pipeline.
            unlisted: Whether the pipeline run should be unlisted (not assigned
                to any pipeline).
        """
        # If `unlisted` is True, we don't assign the run to any pipeline
        if unlisted:
            pipeline_id = None
        else:
            pipeline_id = self._register_pipeline(
                pipeline_name=pipeline_name,
                pipeline_configuration=pipeline_configuration,
            )

        pipeline_run = PipelineRunModel(
            name=runtime_configuration.run_name,
            owner=self.active_user.id,
            stack_id=stack_id,
            pipeline_id=pipeline_id,
            runtime_configuration=runtime_configuration,
        )
        self.zen_store.create_run(pipeline_run)

    def delete_user(self, user_name_or_id: str) -> None:
        """Delete a user.

        Args:
            user_name_or_id: The name or ID of the user to delete.
        """
        user = self.zen_store.get_user(user_name_or_id)
        if self.zen_store.active_user_name == user.name:
            raise IllegalOperationError(
                "You cannot delete yourself. If you wish to delete your active "
                "user account, please contact your ZenML administrator."
            )
        Repository().zen_store.delete_user(user_name_or_id=user.id)

    def delete_project(self, project_name_or_id: str) -> None:
        """Delete a project.

        Args:
            project_name_or_id: The name or ID of the project to delete.
        """
        project = self.zen_store.get_project(project_name_or_id)
        if self.active_project_name == project.name:
            raise IllegalOperationError(
                f"Project '{project_name_or_id}' cannot be deleted since it is "
                "currently active. Please set another project as active first."
            )
        Repository().zen_store.delete_project(
            project_name_or_id=project_name_or_id
        )
