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
import json
import os
import random
from abc import ABCMeta
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, cast

import yaml
from pydantic import BaseModel, ValidationError

from zenml.config.base_config import BaseConfiguration
from zenml.config.global_config import GlobalConfiguration
from zenml.config.profile_config import ProfileConfiguration
from zenml.constants import ENV_ZENML_REPOSITORY_PATH, REPOSITORY_DIRECTORY_NAME
from zenml.enums import StackComponentFlavor, StackComponentType, StoreType
from zenml.environment import Environment
from zenml.exceptions import (
    ForbiddenRepositoryAccessError,
    InitializationException,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.post_execution import PipelineView
from zenml.stack import Stack, StackComponent
from zenml.stack_stores import BaseStackStore, LocalStackStore, SqlStackStore
from zenml.stack_stores.models import (
    StackComponentWrapper,
    StackStoreModel,
    StackWrapper,
)
from zenml.utils import yaml_utils
from zenml.utils.analytics_utils import AnalyticsEvent, track, track_event

logger = get_logger(__name__)


class RepositoryConfiguration(BaseModel):
    """Pydantic object used for serializing repository configuration options.

    Attributes:
        active_profile_name: The name of the active profile.
        active_stack_name: Optional name of the active stack.
    """

    active_profile_name: Optional[str]
    active_stack_name: Optional[str]

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


class LegacyRepositoryConfig(BaseModel):
    version: str
    active_stack_name: Optional[str]
    stacks: Dict[str, Dict[StackComponentType, Optional[str]]]
    stack_components: Dict[StackComponentType, Dict[str, str]]

    def get_stack_data(self) -> StackStoreModel:
        """Extract stack data from Legacy Repository file."""
        return StackStoreModel(
            stacks={
                name: {
                    component_type: value
                    for component_type, value in stack.items()
                    if value is not None  # filter out null components
                }
                for name, stack in self.stacks.items()
            },
            stack_components=defaultdict(dict, self.stack_components),
            **self.dict(exclude={"stacks", "stack_components"}),
        )


class RepositoryMetaClass(ABCMeta):
    """Repository singleton metaclass.

    This metaclass is used to enforce a singleton instance of the Repository
    class with the following additional properties:

    * the singleton Repository instance is created on first access to reflect
    the currently active global configuration profile.
    * the Repository mustn't be accessed from within pipeline steps

    """

    def __init__(cls, *args: Any, **kwargs: Any) -> None:
        """Initialize the Repository class."""
        super().__init__(*args, **kwargs)
        cls._global_repository: Optional["Repository"] = None

    def __call__(cls, *args: Any, **kwargs: Any) -> "Repository":
        """Create or return the global Repository instance.

        If the Repository constructor is called with custom arguments,
        the singleton functionality of the metaclass is bypassed: a new
        Repository instance is created and returned immediately and without
        saving it as the global Repository singleton.

        Raises:
            ForbiddenRepositoryAccessError: If trying to create a `Repository`
                instance while a ZenML step is being executed.
        """
        if Environment().step_is_running:
            raise ForbiddenRepositoryAccessError(
                "Unable to access repository during step execution. If you "
                "require access to the artifact or metadata store, please use "
                "a `StepContext` inside your step instead.",
                url="https://docs.zenml.io/features/step-fixtures#using-the-stepcontext",
            )

        if args or kwargs:
            return cast("Repository", super().__call__(*args, **kwargs))

        if not cls._global_repository:
            cls._global_repository = cast(
                "Repository", super().__call__(*args, **kwargs)
            )

        return cls._global_repository


class Repository(BaseConfiguration, metaclass=RepositoryMetaClass):
    """ZenML repository class.

    The ZenML repository manages configuration options for ZenML stacks as well
    as their components.
    """

    def __init__(
        self,
        root: Optional[Path] = None,
        profile: Optional[ProfileConfiguration] = None,
    ) -> None:
        """Initializes the global repository instance.

        Repository is a singleton class: only one instance can exist. Calling
        this constructor multiple times will always yield the same instance (see
        the exception below).

        The `root` and `profile` arguments are only meant for internal use
        and testing purposes. User code must never pass them to the constructor.
        When a custom `root` or `profile` value is passed, an anonymous
        Repository instance is created and returned independently of the
        Repository singleton and that will have no effect as far as the rest of
        the ZenML core code is concerned.

        Instead of creating a new Repository instance to reflect a different
        profile or repository root:

          * to change the active profile in the global Repository,
          call `Repository().activate_profile(<new-profile>)`.
          * to change the active root in the global Repository,
          call `Repository().activate_root(<new-root>)`.

        Args:
            root: (internal use) custom root directory for the repository. If
                no path is given, the repository root is determined using the
                environment variable `ZENML_REPOSITORY_PATH` (if set) and by
                recursively searching in the parent directories of the
                current working directory. Only used to initialize new
                repositories internally.
            profile: (internal use) custom configuration profile to use for the
                repository. If not provided, the active profile is determined
                from the loaded repository configuration. If no repository
                configuration is found (i.e. repository root is not
                initialized), the default global profile is used. Only used to
                initialize new profiles internally.
        """

        self._root: Optional[Path] = None
        self._profile: Optional[ProfileConfiguration] = None
        self.__config: Optional[RepositoryConfiguration] = None

        # The repository constructor is called with a custom profile only when
        # the profile needs to be initialized, in which case all matters related
        # to repository initialization, like the repository active root and the
        # repository configuration stored there are ignored
        if profile:
            # calling this will initialize the store and create the default
            # stack configuration, if missing
            self._set_active_profile(profile)
            return

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
        path, it is loaded and used to initialize the repository and its
        active profile. If no repository configuration is found, the
        global configuration is used instead (e.g. to manage the active
        profile and active stack).

        Args:
            root: The path to set as the active repository root. If not set,
                the repository root is determined using the environment
                variable `ZENML_REPOSITORY_PATH` (if set) and by recursively
                searching in the parent directories of the current working
                directory.
        """

        self._root = self.find_repository(root, enable_warnings=True)

        global_cfg = GlobalConfiguration()
        new_profile = self._profile

        if not self._root:
            logger.info("Runnning without an active repository root.")
        else:
            logger.debug("Using repository root %s.", self._root)
            self.__config = self._load_config()

            if self.__config and self.__config.active_profile_name:
                new_profile = global_cfg.get_profile(
                    self.__config.active_profile_name
                )

        # fall back to the global active profile if one cannot be determined
        # from the repository configuration
        new_profile = new_profile or global_cfg.active_profile

        if not new_profile:
            # this should theoretically never happen, because there is always
            # a globally active profile, but we need to be prepared for it
            raise RuntimeError(
                "No active configuration profile found. Please set the active "
                "profile in the global configuration by running `zenml profile "
                "set <profile-name>`."
            )

        if new_profile != self._profile:
            logger.debug(
                "Activating configuration profile %s.", new_profile.name
            )
            self._set_active_profile(new_profile)

        # Sanitize the repository configuration to reflect the new active
        # profile
        self._sanitize_config()

    def _set_active_profile(self, profile: ProfileConfiguration) -> None:
        """Set the supplied configuration profile as the active profile for
        this repository.

        This method initializes the repository store associated with the
        supplied profile and also initializes it with the default stack
        configuration, if no other stacks are configured.

        Args:
            profile: configuration profile to set as active.
        """
        self._profile = profile
        self.stack_store: BaseStackStore = self.create_store(profile)

        # Sanitize the repository configuration to reflect the active
        # profile and its store contents
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
        doesn't contain outdated information, such as an active profile or an
        active stack that no longer exists.

        Raises:
            RuntimeError: If the repository configuration doesn't contain a
            valid active stack and a new active stack cannot be automatically
            determined based on the active profile and available stacks.
        """
        if not self.__config:
            return

        global_cfg = GlobalConfiguration()

        # Sanitize the repository active profile
        if self.__config.active_profile_name != self.active_profile_name:
            if (
                self.__config.active_profile_name
                and not global_cfg.has_profile(
                    self.__config.active_profile_name
                )
            ):
                logger.warning(
                    "Profile `%s` not found. Switching repository to the "
                    "global active profile `%s`",
                    self.__config.active_profile_name,
                    self.active_profile_name,
                )
            # reset the active stack when switching to a different profile
            self.__config.active_stack_name = None
            self.__config.active_profile_name = self.active_profile_name

        # As a backup for the active stack, use the profile's default stack
        # or to the first stack in the repository
        backup_stack_name = self.active_profile.active_stack
        if not backup_stack_name:
            stacks = self.stack_store.stacks
            if stacks:
                backup_stack_name = stacks[0].name

        # Sanitize the repository active stack
        if not self.__config.active_stack_name:
            self.__config.active_stack_name = backup_stack_name

        if not self.__config.active_stack_name:
            raise RuntimeError(
                "Could not determine active stack. Please set the active stack "
                "by running `zenml stack set <stack-name>`."
            )

        # Ensure that the repository active stack is still valid
        try:
            self.stack_store.get_stack(self.__config.active_stack_name)
        except KeyError:
            logger.warning(
                "Stack `%s` not found. Switching the repository active stack "
                "to `%s`",
                self.__config.active_stack_name,
                backup_stack_name,
            )
            self.__config.active_stack_name = backup_stack_name

        self._write_config()

    @staticmethod
    def _migrate_legacy_repository(
        config_file: str,
    ) -> Optional[ProfileConfiguration]:
        """Migrate a legacy repository configuration to the new format and
        create a new Profile out of it.

        Args:
            config_file: Path to the legacy repository configuration file.

        Returns:
            The new Profile instance created for the legacy repository or None
            if a legacy repository configuration was not found at the supplied
            path.
        """
        from zenml.console import console

        if not fileio.file_exists(config_file):
            return None

        config_dict = yaml_utils.read_yaml(config_file)

        try:
            legacy_config = LegacyRepositoryConfig.parse_obj(config_dict)
        except ValidationError:
            # legacy configuration not detected
            return None

        config_path = str(Path(config_file).parent)
        profile_name = f"legacy-repository-{random.getrandbits(32):08x}"

        # a legacy repository configuration was detected
        console.print(
            f"A legacy ZenML repository with locally configured stacks was "
            f"found at '{config_path}'.\n"
            f"Beginning with ZenML 0.7.0, stacks are no longer stored inside "
            f"the ZenML repository root, they are stored globally using the "
            f"newly introduced concept of Profiles.\n\n"
            f"The stacks configured in this repository will be automatically "
            f"migrated to a newly created profile: '{profile_name}'.\n\n"
            f"If you no longer need to use the stacks configured in this "
            f"repository, please delete the profile using the following "
            f"command:\n\n"
            f"'zenml profile delete {profile_name}'\n\n"
            f"More information about Profiles can be found at "
            f"https://docs.zenml.io.\n"
            f"This warning will not be shown again for this Repository."
        )

        stack_data = legacy_config.get_stack_data()
        store = LocalStackStore()
        store.initialize(url=config_path, stack_data=stack_data)
        store._write_store()
        profile = ProfileConfiguration(
            name=profile_name,
            store_url=store.url,
            active_stack=legacy_config.active_stack_name,
        )

        new_config = RepositoryConfiguration(
            active_profile_name=profile.name,
            active_stack_name=legacy_config.active_stack_name,
        )
        new_config_dict = json.loads(new_config.json())
        yaml_utils.write_yaml(config_file, new_config_dict)
        GlobalConfiguration().add_or_update_profile(profile)

        return profile

    def _load_config(self) -> Optional[RepositoryConfiguration]:
        """Loads the repository configuration from disk, if the repository has
        an active root and the configuration file exists. If the configuration
        file doesn't exist, an empty configuration is returned.

        If a legacy repository configuration is found in the repository root,
        it is migrated to the new configuration format and a new profile is
        automatically created out of it and activated for the repository root.

        If the repository doesn't have an active root, no repository
        configuration is used and the active profile configuration takes
        precedence.

        Returns:
            Loaded repository configuration or None if the repository does not
            have an active root.
        """

        config_path = self._config_path()
        if not config_path:
            return None

        # load the repository configuration file if it exists, otherwise use
        # an empty configuration as default
        if fileio.file_exists(config_path):
            logger.debug(
                f"Loading repository configuration from {config_path}."
            )

            # detect an old style repository configuration and migrate it to
            # the new format and create a profile out of it if necessary
            self._migrate_legacy_repository(config_path)

            config_dict = yaml_utils.read_yaml(config_path)
            config = RepositoryConfiguration.parse_obj(config_dict)

            return config

        logger.debug(
            "No repository configuration file found, creating default "
            "configuration."
        )
        return RepositoryConfiguration()

    def _write_config(self) -> None:
        """Writes the repository configuration to disk, if the repository has
        been initialized."""
        config_path = self._config_path()
        if not config_path or not self.__config:
            return
        config_dict = json.loads(self.__config.json())
        yaml_utils.write_yaml(config_path, config_dict)

    @staticmethod
    def get_store_class(type: StoreType) -> Optional[Type[BaseStackStore]]:
        """Returns the class of the given store type."""
        return {
            StoreType.LOCAL: LocalStackStore,
            StoreType.SQL: SqlStackStore,
        }.get(type)

    @staticmethod
    def create_store(
        profile: ProfileConfiguration, skip_default_stack: bool = False
    ) -> BaseStackStore:
        """Create the repository persistance back-end store from a configuration
        profile.

        If the configuration profile doesn't specify all necessary configuration
        options (e.g. the type or URL), a default configuration will be used.

        Args:
            profile: The configuration profile to use for persisting the
                repository information.
            skip_default_stack: If True, the creation of the default stack in
                the store will be skipped.

        Returns:
            The initialized repository store.
        """
        if not profile.store_type:
            raise RuntimeError(
                f"Store type not configured in profile {profile.name}"
            )

        store_class = Repository.get_store_class(profile.store_type)
        if not store_class:
            raise RuntimeError(
                f"No store implementation found for store type "
                f"`{profile.store_type}`."
            )

        if not profile.store_url:
            profile.store_url = store_class.get_local_url(
                profile.config_directory
            )

        if store_class.is_valid_url(profile.store_url):
            store = store_class()
            store.initialize(
                url=profile.store_url, skip_default_stack=skip_default_stack
            )
            return store

        raise ValueError(
            f"Invalid URL for store type `{profile.store_type.value}`: "
            f"{profile.store_url}"
        )

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
        fileio.create_dir_recursive_if_not_exists(config_directory)
        # Initialize the repository configuration at the custom path
        Repository(root=root)

    def initialize_store(self) -> None:
        """Initializes the ZenML store for the repository.

        The store will contain a single stack with a local orchestrator,
        a local artifact store and a local SQLite metadata store.
        """

        # register and activate a local stack
        stack = Stack.default_local_stack()
        self.register_stack(stack)
        self.activate_stack(stack.name)

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

    def activate_profile(self, profile_name: str) -> None:
        """Set a profile as the active profile for the repository.

        Args:
            profile_name: name of the profile to add

        Raises:
            KeyError: If the profile with the given name does not exist.
        """
        global_cfg = GlobalConfiguration()
        profile = global_cfg.get_profile(profile_name)
        if not profile:
            raise KeyError(f"Profile '{profile_name}' not found.")
        if profile is self._profile:
            # profile is already active
            return

        self._set_active_profile(profile)

        # set the active profile in the global configuration if the repository
        # doesn't have a root configured (i.e. if a repository root has not been
        # initialized)
        if not self.root:
            global_cfg.activate_profile(profile_name)

    @property
    def active_profile(self) -> ProfileConfiguration:
        """Return the profile set as active for the repository.

        Returns:
            The active profile.

        Raises:
            RuntimeError: If no profile is set as active.
        """
        if not self._profile:
            # this should theoretically never happen, because there is always
            # a globally active profile, but we need to be prepared for it
            raise RuntimeError(
                "No active configuration profile found. Please set the active "
                "profile in the global configuration by running `zenml profile "
                "set <profile-name>`."
            )

        return self._profile

    @property
    def active_profile_name(self) -> str:
        """Return the name of the profile set as active for the repository.

        Returns:
            The active profile name.

        Raises:
            RuntimeError: If no profile is set as active.
        """
        return self.active_profile.name

    @property
    def stacks(self) -> List[Stack]:
        """All stacks registered in this repository."""
        return [self._stack_from_wrapper(s) for s in self.stack_store.stacks]

    @property
    def stack_configurations(self) -> Dict[str, Dict[StackComponentType, str]]:
        """Configuration dicts for all stacks registered in this repository.

        This property is intended as a quick way to get information about the
        components of the registered stacks without loading all installed
        integrations. The contained stack configurations might be invalid if
        they were modified by hand, to ensure you get valid stacks use
        `repo.stacks()` instead.

        Modifying the contents of the returned dictionary does not actually
        register/deregister stacks, use `repo.register_stack(...)` or
        `repo.deregister_stack(...)` instead.
        """
        return self.stack_store.stack_configurations

    @property
    def active_stack(self) -> Stack:
        """The active stack for this repository.

        Raises:
            RuntimeError: If no active stack name is configured.
            KeyError: If no stack was found for the configured name or one
                of the stack components is not registered.
        """
        return self.get_stack(name=self.active_stack_name)

    @property
    def active_stack_name(self) -> str:
        """The name of the active stack for this repository.

        If no active stack is configured for the repository, or if the
        repository does not have an active root, the active stack from the
        associated or global profile is used instead.

        Raises:
            RuntimeError: If no active stack name is set neither in the
            repository configuration nor in the associated profile.
        """
        stack_name = None
        if self.__config:
            stack_name = self.__config.active_stack_name

        if not stack_name:
            stack_name = self.active_profile.active_stack

        if not stack_name:
            raise RuntimeError(
                "No active stack is configured for the repository. Run "
                "`zenml stack set STACK_NAME` to update the active stack."
            )

        return stack_name

    @track(event=AnalyticsEvent.SET_STACK)
    def activate_stack(self, name: str) -> None:
        """Activates the stack for the given name.

        Args:
            name: Name of the stack to activate.

        Raises:
            KeyError: If no stack exists for the given name.
        """
        self.stack_store.get_stack_configuration(name)  # raises KeyError
        if self.__config:
            self.__config.active_stack_name = name
            self._write_config()

        # set the active stack globally in the active profile only if the
        # repository doesn't have a root configured (i.e. repository root hasn't
        # been initialized) or if no active stack has been set for it yet
        if not self.root or not self.active_profile.active_stack:
            self.active_profile.activate_stack(name)

    def get_stack(self, name: str) -> Stack:
        """Fetches a stack.

        Args:
            name: The name of the stack to fetch.

        Raises:
            KeyError: If no stack exists for the given name or one of the
                stacks components is not registered.
        """
        return self._stack_from_wrapper(self.stack_store.get_stack(name))

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
        metadata = self.stack_store.register_stack(
            StackWrapper.from_stack(stack)
        )
        metadata["store_type"] = self.active_profile.store_type.value
        track_event(AnalyticsEvent.REGISTERED_STACK, metadata=metadata)

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
        self.stack_store.deregister_stack(name)

    def get_stack_components(
        self, component_type: StackComponentType
    ) -> List[StackComponent]:
        """Fetches all registered stack components of the given type."""
        return [
            self._component_from_wrapper(c)
            for c in self.stack_store.get_stack_components(component_type)
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
        return self._component_from_wrapper(
            self.stack_store.get_stack_component(component_type, name=name)
        )

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
        self.stack_store.register_stack_component(
            StackComponentWrapper.from_component(component)
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
        self.stack_store.deregister_stack_component(component_type, name=name)

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
            RuntimeError: If no stack name is specified and no active stack name
                is configured.
            KeyError: If no stack with the given name exists.
        """
        stack_name = stack_name or self.active_stack_name
        if not stack_name:
            raise RuntimeError(
                "No active stack is configured for the repository. Run "
                "`zenml stack set STACK_NAME` to update the active stack."
            )
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
            RuntimeError: If no stack name is specified and no active stack name
                is configured.
            KeyError: If no stack with the given name exists.
        """
        stack_name = stack_name or self.active_stack_name
        if not stack_name:
            raise RuntimeError(
                "No active stack is configured for the repository. Run "
                "`zenml stack set STACK_NAME` to update the active stack."
            )
        metadata_store = self.get_stack(stack_name).metadata_store
        return metadata_store.get_pipeline(pipeline_name)

    @staticmethod
    def is_repository_directory(path: Path) -> bool:
        """Checks whether a ZenML repository exists at the given path."""
        config_dir = path / REPOSITORY_DIRECTORY_NAME
        return fileio.is_dir(str(config_dir))

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
            ZenML repository."""
            if Repository.is_repository_directory(path_):
                return path_

            if not search_parent_directories or fileio.is_root(str(path_)):
                return None

            return _find_repo_helper(path_.parent)

        repo_path = _find_repo_helper(path)

        if repo_path:
            return repo_path.resolve()
        if enable_warnings:
            logger.warning(warning_message)
        return None

    def _component_from_wrapper(
        self, wrapper: StackComponentWrapper
    ) -> StackComponent:
        """Instantiate a StackComponent from the Configuration."""
        from zenml.stack.stack_component_class_registry import (
            StackComponentClassRegistry,
        )

        flavor = StackComponentFlavor.for_type(wrapper.type)(wrapper.flavor)
        component_class = StackComponentClassRegistry.get_class(
            component_type=wrapper.type, component_flavor=flavor
        )
        component_config = yaml.safe_load(
            base64.b64decode(wrapper.config).decode()
        )
        return component_class.parse_obj(component_config)

    def _stack_from_wrapper(self, wrapper: StackWrapper) -> Stack:
        """Instantiate a Stack from the serializable Wrapper."""
        stack_components = {}
        for component_wrapper in wrapper.components:
            component_type = component_wrapper.type
            component = self._component_from_wrapper(component_wrapper)
            stack_components[component_type] = component

        return Stack.from_components(
            name=wrapper.name, components=stack_components
        )
