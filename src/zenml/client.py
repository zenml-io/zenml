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
"""Client implementation."""

import os
from abc import ABCMeta
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Union, cast
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
    ValidationError,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import io_utils
from zenml.utils.analytics_utils import AnalyticsEvent, track
from zenml.utils.filesync_model import FileSyncModel

if TYPE_CHECKING:
    from zenml.config.pipeline_configurations import PipelineSpec
    from zenml.enums import StackComponentType
    from zenml.models import (
        ComponentModel,
        FlavorModel,
        HydratedStackModel,
        PipelineModel,
        ProjectModel,
        StackModel,
        UserModel,
    )
    from zenml.stack import Stack, StackComponentConfig
    from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)

# TODO: [server] this is defined in two places now, should be fixed
DEFAULT_STACK_NAME = "default"


class ClientConfiguration(FileSyncModel):
    """Pydantic object used for serializing client configuration options.

    Attributes:
        active_stack_id: Optional name of the active stack.
        active_project_name: Optional name of the active project.
    """

    active_stack_id: Optional[UUID]
    active_project_name: Optional[str]
    _active_project: Optional["ProjectModel"] = None

    def set_active_project(self, project: "ProjectModel") -> None:
        """Set the project for the local client.

        Args:
            project: The project to set active.
        """
        self.active_project_name = project.name
        self._active_project = project

    class Config:
        """Pydantic configuration class."""

        # Validate attributes when assigning them. We need to set this in order
        # to have a mix of mutable and immutable attributes
        validate_assignment = True
        # Allow extra attributes from configs of previous ZenML versions to
        # permit downgrading
        extra = "allow"
        # all attributes with leading underscore are private and therefore
        # are mutable and not included in serialization
        underscore_attrs_are_private = True


class ClientMetaClass(ABCMeta):
    """Client singleton metaclass.

    This metaclass is used to enforce a singleton instance of the Client
    class with the following additional properties:

    * the singleton Client instance is created on first access to reflect
    the global configuration and local client configuration.
    * the Client shouldn't be accessed from within pipeline steps (a warning
    is logged if this is attempted).
    """

    def __init__(cls, *args: Any, **kwargs: Any) -> None:
        """Initialize the Client class.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.
        """
        super().__init__(*args, **kwargs)
        cls._global_client: Optional["Client"] = None

    def __call__(cls, *args: Any, **kwargs: Any) -> "Client":
        """Create or return the global Client instance.

        If the Client constructor is called with custom arguments,
        the singleton functionality of the metaclass is bypassed: a new
        Client instance is created and returned immediately and without
        saving it as the global Client singleton.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Client: The global Client instance.
        """
        from zenml.steps.step_environment import (
            STEP_ENVIRONMENT_NAME,
            StepEnvironment,
        )

        step_env = cast(
            StepEnvironment, Environment().get_component(STEP_ENVIRONMENT_NAME)
        )

        # `skip_client_check` is a special kwarg that can be passed to
        # the Client constructor to silent the message that warns users
        # about accessing external information in their steps.
        if not kwargs.pop("skip_client_check", False):
            if step_env and step_env.cache_enabled:
                logger.warning(
                    "You are accessing client information from a step "
                    "that has caching enabled. Future executions of this step "
                    "may be cached even though the client information may "
                    "be different. You should take this into consideration and "
                    "adjust your step to disable caching if needed. "
                    "Alternatively, use a `StepContext` inside your step "
                    "instead, as covered here: "
                    "https://docs.zenml.io/advanced-guide/pipelines/step-metadata"
                    "/step-fixtures#step-contexts",
                )

        if args or kwargs:
            return cast("Client", super().__call__(*args, **kwargs))

        if not cls._global_client:
            cls._global_client = cast(
                "Client", super().__call__(*args, **kwargs)
            )

        return cls._global_client


class Client(metaclass=ClientMetaClass):
    """ZenML client class.

    The ZenML client manages configuration options for ZenML stacks as well
    as their components.
    """

    def __init__(
        self,
        root: Optional[Path] = None,
    ) -> None:
        """Initializes the global client instance.

        Client is a singleton class: only one instance can exist. Calling
        this constructor multiple times will always yield the same instance (see
        the exception below).

        The `root` argument is only meant for internal use and testing purposes.
        User code must never pass them to the constructor.
        When a custom `root` value is passed, an anonymous Client instance
        is created and returned independently of the Client singleton and
        that will have no effect as far as the rest of the ZenML core code is
        concerned.

        Instead of creating a new Client instance to reflect a different
        repository root, to change the active root in the global Client,
        call `Client().activate_root(<new-root>)`.

        Args:
            root: (internal use) custom root directory for the client. If
                no path is given, the repository root is determined using the
                environment variable `ZENML_REPOSITORY_PATH` (if set) and by
                recursively searching in the parent directories of the
                current working directory. Only used to initialize new
                clients internally.
        """
        self._root: Optional[Path] = None
        self._config: Optional[ClientConfiguration] = None

        self._set_active_root(root)

    @classmethod
    def get_instance(cls) -> Optional["Client"]:
        """Return the Client singleton instance.

        Returns:
            The Client singleton instance or None, if the Client hasn't
            been initialized yet.
        """
        return cls._global_client

    @classmethod
    def _reset_instance(cls, client: Optional["Client"] = None) -> None:
        """Reset the Client singleton instance.

        This method is only meant for internal use and testing purposes.

        Args:
            client: The Client instance to set as the global singleton.
                If None, the global Client singleton is reset to an empty
                value.
        """
        cls._global_client = client

    def _set_active_root(self, root: Optional[Path] = None) -> None:
        """Set the supplied path as the repository root.

        If a client configuration is found at the given path or the
        path, it is loaded and used to initialize the client.
        If no client configuration is found, the global configuration is
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

        # Sanitize the client configuration to reflect the current
        # settings
        self._sanitize_config()

    def _config_path(self) -> Optional[str]:
        """Path to the client configuration file.

        Returns:
            Path to the client configuration file or None if the client
            root has not been initialized yet.
        """
        if not self.config_directory:
            return None
        return str(self.config_directory / "config.yaml")

    def _sanitize_config(self) -> None:
        """Sanitize and save the client configuration.

        This method is called to ensure that the client configuration
        doesn't contain outdated information, such as an active stack or
        project that no longer exists.
        """
        if not self._config:
            return

        active_project, active_stack = self.zen_store.validate_active_config(
            self._config.active_project_name,
            self._config.active_stack_id,
            config_name="repo",
        )
        self._config.active_stack_id = active_stack.id
        self._config.set_active_project(active_project)

    def _load_config(self) -> Optional[ClientConfiguration]:
        """Loads the client configuration from disk.

        This happens if the client has an active root and the configuration
        file exists. If the configuration file doesn't exist, an empty
        configuration is returned.

        Returns:
            Loaded client configuration or None if the client does not
            have an active root.
        """
        config_path = self._config_path()
        if not config_path:
            return None

        # load the client configuration file if it exists, otherwise use
        # an empty configuration as default
        if fileio.exists(config_path):
            logger.debug(f"Loading client configuration from {config_path}.")
        else:
            logger.debug(
                "No client configuration file found, creating default "
                "configuration."
            )

        return ClientConfiguration(config_path)

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
        if Client.is_repository_directory(root):
            raise InitializationException(
                f"Found existing ZenML repository at path '{root}'."
            )

        config_directory = str(root / REPOSITORY_DIRECTORY_NAME)
        io_utils.create_dir_recursive_if_not_exists(config_directory)
        # Initialize the repository configuration at the custom path
        Client(root=root)

    @property
    def uses_local_configuration(self) -> bool:
        """Check if the client is using a local configuration.

        Returns:
            True if the client is using a local configuration,
            False otherwise.
        """
        return self._config is not None

    @staticmethod
    def is_repository_directory(path: Path) -> bool:
        """Checks whether a ZenML client exists at the given path.

        Args:
            path: The path to check.

        Returns:
            True if a ZenML client exists at the given path,
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
            # try to find the repository in the parent directories of the
            # current working directory
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

        def _find_repository_helper(path_: Path) -> Optional[Path]:
            """Recursively search parent directories for a ZenML repository.

            Args:
                path_: The path to search.

            Returns:
                Absolute path to a ZenML repository directory or None if no
                repository directory was found.
            """
            if Client.is_repository_directory(path_):
                return path_

            if not search_parent_directories or io_utils.is_root(str(path_)):
                return None

            return _find_repository_helper(path_.parent)

        repository_path = _find_repository_helper(path)

        if repository_path:
            return repository_path.resolve()
        if enable_warnings:
            logger.warning(warning_message)
        return None

    @property
    def zen_store(self) -> "BaseZenStore":
        """Shortcut to return the global zen store.

        Returns:
            The global zen store.
        """
        return GlobalConfiguration().zen_store

    @property
    def root(self) -> Optional[Path]:
        """The root directory of this client.

        Returns:
            The root directory of this client, or None, if the client
            has not been initialized.
        """
        return self._root

    @property
    def config_directory(self) -> Optional[Path]:
        """The configuration directory of this client.

        Returns:
            The configuration directory of this client, or None, if the
            client doesn't have an active root.
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

    @track(event=AnalyticsEvent.SET_PROJECT)
    def set_active_project(
        self, project_name_or_id: Union[str, UUID]
    ) -> "ProjectModel":
        """Set the project for the local client.

        Args:
            project_name_or_id: The name or ID of the project to set active.

        Returns:
            The model of the active project.
        """
        project = self.zen_store.get_project(
            project_name_or_id=project_name_or_id
        )  # raises KeyError
        if self._config:
            self._config.set_active_project(project)
        else:
            # set the active project globally only if the client doesn't use
            # a local configuration
            GlobalConfiguration().set_active_project(project)
        return project

    @property
    def active_project_name(self) -> str:
        """The name of the active project for this client.

        If no active project is configured locally for the client, the
        active project in the global configuration is used instead.

        Returns:
            The name of the active project.
        """
        return self.active_project.name

    @property
    def active_project(self) -> "ProjectModel":
        """Get the currently active project of the local client.

        If no active project is configured locally for the client, the
        active project in the global configuration is used instead.

        Returns:
            The active project.

        Raises:
            RuntimeError: If the active project is not set.
        """
        project: Optional["ProjectModel"] = None
        if self._config:
            project = self._config._active_project

        if not project:
            project = GlobalConfiguration().active_project

        if not project:
            raise RuntimeError(
                "No active project is configured. Run "
                "`zenml project set PROJECT_NAME` to set the active "
                "project."
            )

        from zenml.zen_stores.base_zen_store import DEFAULT_PROJECT_NAME

        if project.name != DEFAULT_PROJECT_NAME:
            logger.warning(
                f"You are running with a non-default project "
                f"'{project.name}'. Any stacks, components, "
                f"pipelines and pipeline runs produced in this "
                f"project will currently not be accessible through "
                f"the dashboard. However, this will be possible "
                f"in the near future."
            )
        return project

    @property
    def active_user(self) -> "UserModel":
        """Get the user that is currently in use.

        Returns:
            The active user.
        """
        return self.zen_store.active_user

    @property
    def stacks(self) -> List["HydratedStackModel"]:
        """All stack models in the active project, owned by the user or shared.

        This property is intended as a quick way to get information about the
        components of the registered stacks without loading all installed
        integrations.

        Returns:
            A list of all stacks available in the current project and owned by
            the current user.
        """
        owned_stacks = cast(
            List["HydratedStackModel"],
            self.zen_store.list_stacks(
                project_name_or_id=self.active_project_name,
                user_name_or_id=self.active_user.id,
                is_shared=False,
                hydrated=True,
            ),
        )
        shared_stacks = cast(
            List["HydratedStackModel"],
            self.zen_store.list_stacks(
                project_name_or_id=self.active_project_name,
                is_shared=True,
                hydrated=True,
            ),
        )

        return owned_stacks + shared_stacks

    @property
    def active_stack_model(self) -> "HydratedStackModel":
        """The model of the active stack for this client.

        If no active stack is configured locally for the client, the active
        stack in the global configuration is used instead.

        Returns:
            The model of the active stack for this client.

        Raises:
            RuntimeError: If the active stack is not set.
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

        return self.zen_store.get_stack(stack_id=stack_id).to_hydrated_model()

    @property
    def active_stack(self) -> "Stack":
        """The active stack for this client.

        Returns:
            The active stack for this client.
        """
        from zenml.stack.stack import Stack

        return Stack.from_model(self.active_stack_model)

    @track(event=AnalyticsEvent.SET_STACK)
    def activate_stack(self, stack: "StackModel") -> None:
        """Sets the stack as active.

        Args:
            stack: Model of the stack to activate.

        Raises:
            KeyError: If the stack is not registered.
        """
        # Make sure the stack is registered
        try:
            self.zen_store.get_stack(stack_id=stack.id)
        except KeyError:
            raise KeyError(
                f"Stack '{stack.name}' cannot be activated since it is "
                "not registered yet. Please register it first."
            )

        if self._config:
            self._config.active_stack_id = stack.id

        else:
            # set the active stack globally only if the client doesn't use
            # a local configuration
            GlobalConfiguration().active_stack_id = stack.id

    def _validate_stack_configuration(self, stack: "StackModel") -> None:
        """Validates the configuration of a stack.

        Args:
            stack: The stack to validate.

        Raises:
            KeyError: If the stack references missing components.
            ValidationError: If the stack configuration is invalid.
        """
        local_components: List[str] = []
        remote_components: List[str] = []
        for component_type, component_ids in stack.components.items():
            for component_id in component_ids:
                try:
                    component = self.get_stack_component_by_id(
                        component_id=component_id
                    )
                except KeyError:
                    raise KeyError(
                        f"Cannot register stack '{stack.name}' since it has an "
                        f"unregistered {component_type} with id "
                        f"'{component_id}'."
                    )
            # Get the flavor model
            flavor_model = self.get_flavor_by_name_and_type(
                name=component.flavor, component_type=component.type
            )

            # Create and validate the configuration
            from zenml.stack import Flavor

            flavor = Flavor.from_model(flavor_model)
            configuration = flavor.config_class(**component.configuration)
            if configuration.is_local:
                local_components.append(
                    f"{component.type.value}: {component.name}"
                )
            elif configuration.is_remote:
                remote_components.append(
                    f"{component.type.value}: {component.name}"
                )

        if local_components and remote_components:
            logger.warning(
                f"You are configuring a stack that is composed of components "
                f"that are relying on local resources "
                f"({', '.join(local_components)}) as well as "
                f"components that are running remotely "
                f"({', '.join(remote_components)}). This is not recommended as "
                f"it can lead to unexpected behavior, especially if the remote "
                f"components need to access the local resources. Please make "
                f"sure that your stack is configured correctly, or try to use "
                f"component flavors or configurations that do not require "
                f"local resources."
            )

        if not stack.is_valid:
            raise ValidationError(
                "Stack configuration is invalid. A valid"
                "stack must contain an Artifact Store and "
                "an Orchestrator."
            )

    def register_stack(self, stack: "StackModel") -> "StackModel":
        """Registers a stack and its components.

        Args:
            stack: The stack to register.

        Returns:
            The model of the registered stack.
        """
        self._validate_stack_configuration(stack=stack)

        created_stack = self.zen_store.create_stack(
            stack=stack,
        )
        return created_stack

    def update_stack(self, stack: "StackModel") -> None:
        """Updates a stack and its components.

        Args:
            stack: The new stack to use as the updated version.
        """
        self._validate_stack_configuration(stack=stack)

        self.zen_store.update_stack(stack=stack)

    def deregister_stack(self, stack: "StackModel") -> None:
        """Deregisters a stack.

        Args:
            stack: The model of the stack to deregister.

        Raises:
            ValueError: If the stack is the currently active stack for this
                client.
        """
        if stack.id == self.active_stack_model.id:
            raise ValueError(
                f"Unable to deregister active stack "
                f"'{stack.name}'. Make "
                f"sure to designate a new active stack before deleting this "
                f"one."
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

    # .------------.
    # | COMPONENTS |
    # '------------'

    def _validate_stack_component_configuration(
        self,
        component_type: "StackComponentType",
        configuration: "StackComponentConfig",
    ) -> None:
        """Validates the configuration of a stack component.

        Args:
            component_type: The type of the component.
            configuration: The component configuration to validate.
        """
        from zenml.enums import StackComponentType, StoreType

        if configuration.is_remote and self.zen_store.is_local_store():
            if self.zen_store.type == StoreType.REST:
                logger.warning(
                    "You are configuring a stack component that is running "
                    "remotely while using a local database. The component "
                    "may not be able to reach the local database and will "
                    "therefore not be functional. Please consider deploying "
                    "and/or using a remote ZenML server instead."
                )
            else:
                logger.warning(
                    "You are configuring a stack component that is running "
                    "remotely while using a local ZenML server. The component "
                    "may not be able to reach the local ZenML server and will "
                    "therefore not be functional. Please consider deploying "
                    "and/or using a remote ZenML server instead."
                )
        elif configuration.is_local and not self.zen_store.is_local_store():
            logger.warning(
                "You are configuring a stack component that is using "
                "local resources while connected to a remote ZenML server. The "
                "stack component may not be usable from other hosts or by "
                "other users. You should consider using a non-local stack "
                "component alternative instead."
            )
            if component_type in [
                StackComponentType.ORCHESTRATOR,
                StackComponentType.STEP_OPERATOR,
            ]:
                logger.warning(
                    "You are configuring a stack component that is running "
                    "pipeline code on your local host while connected to a "
                    "remote ZenML server. This will significantly affect the "
                    "performance of your pipelines. You will likely encounter "
                    "long running times caused by network latency. You should "
                    "consider using a non-local stack component alternative "
                    "instead."
                )

    def register_stack_component(
        self,
        component: "ComponentModel",
    ) -> "ComponentModel":
        """Registers a stack component.

        Args:
            component: The component to register.

        Returns:
            The model of the registered component.
        """
        # Get the flavor model
        flavor_model = self.get_flavor_by_name_and_type(
            name=component.flavor, component_type=component.type
        )

        # Create and validate the configuration
        from zenml.stack import Flavor

        flavor = Flavor.from_model(flavor_model)
        configuration = flavor.config_class(**component.configuration)

        # Update the configuration in the model
        component.configuration = configuration.dict()

        self._validate_stack_component_configuration(
            component.type, configuration=configuration
        )

        # Register the new model
        return self.zen_store.create_stack_component(component=component)

    def update_stack_component(
        self,
        component: "ComponentModel",
    ) -> "ComponentModel":
        """Updates a stack component.

        Args:
            component: The new component to update with.

        Returns:
            The updated component.
        """
        # Get the existing component model
        existing_component_model = self.get_stack_component_by_id(
            component.id,
        )

        # Get the flavor model of the existing component
        flavor_model = self.get_flavor_by_name_and_type(
            name=existing_component_model.flavor,
            component_type=existing_component_model.type,
        )

        # Use the flavor class to validate the new configuration
        from zenml.stack import Flavor

        flavor = Flavor.from_model(flavor_model)
        configuration = flavor.config_class(**component.configuration)

        # Update the configuration in the model
        component.configuration = configuration.dict()

        self._validate_stack_component_configuration(
            component.type, configuration=configuration
        )

        # Send the updated component to the ZenStore
        return self.zen_store.update_stack_component(component=component)

    def deregister_stack_component(self, component: "ComponentModel") -> None:
        """Deletes a registered stack component.

        Args:
            component: The model of the component to delete.
        """
        try:
            self.zen_store.delete_stack_component(component_id=component.id)
            logger.info(
                "Deregistered stack component (type: %s) with name '%s'.",
                component.type,
                component.name,
            )
        except KeyError:
            logger.warning(
                "Unable to deregister stack component (type: %s) with name "
                "'%s': No stack component with this name could be found.",
                component.type,
                component.name,
            )

    def get_stack_component_by_id(self, component_id: UUID) -> "ComponentModel":
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
        return self.zen_store.get_stack_component(component_id=component_id)

    def list_stack_components_by_type(
        self, type_: "StackComponentType", is_shared: bool = False
    ) -> List["ComponentModel"]:
        """Fetches all registered stack components of a given type.

        Args:
            type_: The type of the components to fetch.
            is_shared: Whether to fetch shared components or not.

        Returns:
            The registered stack components.
        """
        owned_stack_components = self.zen_store.list_stack_components(
            project_name_or_id=self.active_project_name,
            user_name_or_id=self.active_user.id,
            type=type_,
            is_shared=False,
        )
        shared_stack_components = self.zen_store.list_stack_components(
            project_name_or_id=self.active_project_name,
            is_shared=True,
            type=type_,
        )
        return owned_stack_components + shared_stack_components

    # .---------.
    # | FLAVORS |
    # '---------'
    @property
    def flavors(self) -> List["FlavorModel"]:
        """Fetches all the flavor models.

        Returns:
            The list of flavor models.
        """
        return self.get_flavors()

    def create_flavor(self, flavor: "FlavorModel") -> "FlavorModel":
        """Creates a new flavor.

        Args:
            flavor: The flavor to create.

        Returns:
            The created flavor (in model form).
        """
        from zenml.utils.source_utils import validate_flavor_source

        flavor_class = validate_flavor_source(
            source=flavor.source,
            component_type=flavor.type,
        )

        flavor_model = flavor_class().to_model()

        flavor_model.project = self.active_project.id
        flavor_model.user = self.active_user.id
        flavor_model.name = flavor_class().name
        flavor_model.config_schema = flavor_class().config_schema

        return self.zen_store.create_flavor(flavor=flavor_model)

    def delete_flavor(self, flavor: "FlavorModel") -> None:
        """Deletes a flavor.

        Args:
            flavor: The flavor to delete.
        """
        try:
            self.zen_store.delete_flavor(flavor_id=flavor.id)
            logger.info(
                f"Deleted flavor '{flavor.name}' of type '{flavor.type}'.",
            )
        except KeyError:
            logger.warning(
                f"Unable to delete flavor '{flavor.name}' of type "
                f"'{flavor.type}': No flavor with this name could be found.",
            )

    def get_flavors(self) -> List["FlavorModel"]:
        """Fetches all the flavor models.

        Returns:
            A list of all the flavor models.
        """
        from zenml.stack.flavor_registry import flavor_registry

        zenml_flavors = flavor_registry.flavors
        custom_flavors = self.zen_store.list_flavors(
            user_name_or_id=self.active_user.id,
            project_name_or_id=self.active_project.id,
        )
        return zenml_flavors + custom_flavors

    def get_flavors_by_type(
        self, component_type: "StackComponentType"
    ) -> List["FlavorModel"]:
        """Fetches the list of flavor for a stack component type.

        Args:
            component_type: The type of the component to fetch.

        Returns:
            The list of flavors.
        """
        logger.debug(f"Fetching the flavors of type {component_type}.")

        from zenml.stack.flavor_registry import flavor_registry

        zenml_flavors = flavor_registry.get_flavors_by_type(
            component_type=component_type
        )

        custom_flavors = self.zen_store.list_flavors(
            project_name_or_id=self.active_project.id,
            component_type=component_type,
        )

        return zenml_flavors + custom_flavors

    def get_flavor_by_name_and_type(
        self, name: str, component_type: "StackComponentType"
    ) -> "FlavorModel":
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
            f"Fetching the flavor of type {component_type} with name {name}."
        )

        from zenml.stack.flavor_registry import flavor_registry

        try:
            zenml_flavor = flavor_registry.get_flavor_by_name_and_type(
                component_type=component_type,
                name=name,
            )
        except KeyError:
            zenml_flavor = None

        custom_flavors = self.zen_store.list_flavors(
            project_name_or_id=self.active_project.id,
            component_type=component_type,
            name=name,
        )

        if custom_flavors:
            if len(custom_flavors) > 1:
                raise KeyError(
                    f"More than one flavor with name {name} and type "
                    f"{component_type} exists."
                )

            if zenml_flavor:
                # If there is one, check whether the same flavor exists as
                # a ZenML flavor to give out a warning
                logger.warning(
                    f"There is a custom implementation for the flavor "
                    f"'{name}' of a {component_type}, which is currently "
                    f"overwriting the same flavor provided by ZenML."
                )
            return custom_flavors[0]
        else:
            if zenml_flavor:
                return zenml_flavor
            else:
                raise KeyError(
                    f"No flavor with name '{name}' and type '{component_type}' "
                    "exists."
                )

    def get_pipeline_by_name(self, name: str) -> "PipelineModel":
        """Fetches a pipeline by name.

        Args:
            name: The name of the pipeline to fetch.

        Returns:
            The pipeline model.
        """
        return self.zen_store.get_pipeline_in_project(
            pipeline_name=name, project_name_or_id=self.active_project_name
        )

    def register_pipeline(
        self,
        pipeline_name: str,
        pipeline_spec: "PipelineSpec",
        pipeline_docstring: Optional[str],
    ) -> UUID:
        """Registers a pipeline in the ZenStore within the active project.

        This will do one of the following three things:
        A) If there is no pipeline with this name, register a new pipeline.
        B) If a pipeline exists that has the same config, use that pipeline.
        C) If a pipeline with different config exists, raise an error.

        Args:
            pipeline_name: The name of the pipeline to register.
            pipeline_spec: The spec of the pipeline.
            pipeline_docstring: The docstring of the pipeline.

        Returns:
            The id of the existing or newly registered pipeline.

        Raises:
            AlreadyExistsException: If there is an existing pipeline in the
                project with the same name but a different configuration.
        """
        try:
            existing_pipeline = self.get_pipeline_by_name(pipeline_name)

        # A) If there is no pipeline with this name, register a new pipeline.
        except KeyError:
            from zenml.models import PipelineModel

            pipeline = PipelineModel(
                project=self.active_project.id,
                user=self.active_user.id,
                name=pipeline_name,
                spec=pipeline_spec,
                docstring=pipeline_docstring,
            )
            pipeline = self.zen_store.create_pipeline(pipeline=pipeline)
            logger.info(f"Registered new pipeline with name {pipeline.name}.")
            return pipeline.id

        # B) If a pipeline exists that has the same config, use that pipeline.
        if pipeline_spec == existing_pipeline.spec:
            logger.debug("Did not register pipeline since it already exists.")
            return existing_pipeline.id

        # C) If a pipeline with different config exists, raise an error.
        error_msg = (
            f"Cannot run pipeline '{pipeline_name}' since this name has "
            "already been registered with a different pipeline "
            "configuration. You have three options to resolve this issue:\n"
            "1) You can register a new pipeline by changing the name "
            "of your pipeline, e.g., via `@pipeline(name='new_pipeline_name')."
            "\n2) You can execute the current run without linking it to any "
            "pipeline by setting the 'unlisted' argument to `True`, e.g., "
            "via `my_pipeline_instance.run(unlisted=True)`. "
            "Unlisted runs are not linked to any pipeline, but are still "
            "tracked by ZenML and can be accessed via the 'All Runs' tab. \n"
            "3) You can delete the existing pipeline via "
            f"`zenml pipeline delete {pipeline_name}`. This will then "
            "change all existing runs of this pipeline to become unlisted."
        )
        raise AlreadyExistsException(error_msg)

    def delete_user(self, user_name_or_id: str) -> None:
        """Delete a user.

        Args:
            user_name_or_id: The name or ID of the user to delete.

        Raises:
            IllegalOperationError: If the user to delete is the active user.
        """
        user = self.zen_store.get_user(user_name_or_id)
        if self.zen_store.active_user_name == user.name:
            raise IllegalOperationError(
                "You cannot delete yourself. If you wish to delete your active "
                "user account, please contact your ZenML administrator."
            )
        Client().zen_store.delete_user(user_name_or_id=user.name)

    def delete_project(self, project_name_or_id: str) -> None:
        """Delete a project.

        Args:
            project_name_or_id: The name or ID of the project to delete.

        Raises:
            IllegalOperationError: If the project to delete is the active
                project.
        """
        project = self.zen_store.get_project(project_name_or_id)
        if self.active_project_name == project.name:
            raise IllegalOperationError(
                f"Project '{project_name_or_id}' cannot be deleted since it is "
                "currently active. Please set another project as active first."
            )
        Client().zen_store.delete_project(project_name_or_id=project_name_or_id)
