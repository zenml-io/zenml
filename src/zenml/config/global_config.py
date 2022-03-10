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
import shutil
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, cast

from pydantic import BaseModel, Field, ValidationError, validator
from pydantic.main import ModelMetaclass
from semver import VersionInfo  # type: ignore [import]

from zenml import __version__
from zenml.constants import ENV_ZENML_DEFAULT_STORE_TYPE
from zenml.enums import StoreType
from zenml.io import fileio
from zenml.io.utils import get_global_config_directory
from zenml.logger import get_logger
from zenml.utils import yaml_utils

logger = get_logger(__name__)


LEGACY_CONFIG_FILE_NAME = ".zenglobal.json"
DEFAULT_PROFILE_NAME = "default"
CONFIG_ENV_VAR_PREFIX = "ZENML_"


class GlobalConfigMetaClass(ModelMetaclass):
    """Global configuration metaclass.

    This metaclass is used to enforce a singleton instance of the GlobalConfig
    class with the following additional properties:

    * the GlobalConfig is initialized automatically on import with the
    default configuration, if no config file exists yet.
    * an empty default profile is added to the global config on initialization
    if no other profiles are configured yet.
    * the GlobalConfig undergoes a schema migration if the version of the
    config file is older than the current version of the ZenML package.
    """

    def __init__(cls, *args: Any, **kwargs: Any) -> None:
        """Initialize a singleton class."""
        super().__init__(*args, **kwargs)
        cls._global_config: Optional["GlobalConfig"] = None

    def __call__(cls, *args: Any, **kwargs: Any) -> "GlobalConfig":
        """Create or return the default global config instance.

        If the GlobalConfig constructor is called with custom arguments,
        the singleton functionality of the metaclass is bypassed: a new
        GlobalConfig instance is created and returned immediately and without
        saving it as the global GlobalConfig singleton.
        """
        if args or kwargs:
            return cast("GlobalConfig", super().__call__(*args, **kwargs))

        if not cls._global_config:
            cls._global_config = cast(
                "GlobalConfig", super().__call__(*args, **kwargs)
            )
            cls._global_config._migrate_config()
            cls._global_config._add_and_activate_default_profile()

        return cls._global_config


class BaseGlobalConfiguration(ABC):
    """Base class for global configuration management.

    This class defines the common interface related to profile and stack
    management that all global configuration classes must implement.
    Both the GlobalConfig and Repository classes implement this class, since
    they share similarities concerning the management of active profiles and
    stacks.
    """

    @abstractmethod
    def activate_profile(self, profile_name: str) -> None:
        """Set the active profile

        Args:
            profile_name: The name of the profile to set as active.
        """

    @property
    @abstractmethod
    def active_profile(self) -> Optional["ConfigProfile"]:
        """Return the profile set as active for the repository.

        Returns:
            The active profile or None, if no active profile is set.
        """

    @property
    @abstractmethod
    def active_profile_name(self) -> Optional[str]:
        """Return the name of the profile set as active.

        Returns:
            The active profile name or None, if no active profile is set.
        """

    @abstractmethod
    def activate_stack(self, stack_name: str) -> None:
        """Set the active stack for the active profile.

        Args:
            stack_name: name of the stack to activate
        """

    @property
    @abstractmethod
    def active_stack_name(self) -> Optional[str]:
        """Get the active stack name from the active profile.

        Returns:
            The active stack name or None if no active stack is set or if
            no active profile is set.
        """


def get_default_store_type() -> StoreType:
    """Return the default store type.

    The default store type can be set via the environment variable
    ZENML_DEFAULT_STORE_TYPE. If this variable is not set, the default
    store type is set to 'LOCAL'.

    NOTE: this is a global function instead of a default
    `ConfigProfile.store_type` value because it makes it easier to mock in the
    unit tests.

    Returns:
        The default store type.
    """
    store_type = os.getenv(ENV_ZENML_DEFAULT_STORE_TYPE)
    if store_type and store_type in StoreType.values():
        return StoreType(store_type)
    return StoreType.LOCAL


class ConfigProfile(BaseModel):
    """Stores configuration profile options.

    Attributes:
        name: Name of the profile.
        store_url: URL pointing to the ZenML store backend.
        store_type: Type of the store backend.
        active_stack: Optional name of the active stack.
        _config: global configuration to which this profile belongs.
    """

    name: str
    store_url: Optional[str]
    store_type: StoreType = Field(default_factory=get_default_store_type)
    active_stack: Optional[str]
    _config: Optional["GlobalConfig"]

    def __init__(
        self, config: Optional["GlobalConfig"] = None, **kwargs: Any
    ) -> None:
        """Initializes a GlobalConfig object using values from the config file.

        If the config file doesn't exist yet, we try to read values from the
        legacy (ZenML version < 0.6) config file.

        Args:
            config: global configuration to which this profile belongs. When not
                specified, the default global configuration path is used.
            **kwargs: additional keyword arguments are passed to the
                BaseModel constructor.
        """
        self._config = config
        super().__init__(**kwargs)

    @property
    def config_directory(self) -> str:
        """Directory where the profile configuration is stored."""
        return os.path.join(
            self.global_config.config_directory, "profiles", self.name
        )

    def initialize(self) -> None:
        """Initialize the profile."""

        # import here to avoid circular dependency
        from zenml.repository import Repository

        logger.info("Initializing profile `%s`...", self.name)

        # Create and initialize the profile using a special repository instance.
        # This also validates and updates the store URL configuration and creates
        # all necessary resources (e.g. paths, initial DB, default stacks).
        repo = Repository(profile=self)

        if not self.active_stack:
            stacks = repo.stacks
            if stacks:
                self.active_stack = stacks[0].name

    def cleanup(self) -> None:
        """Cleanup the profile directory."""
        if fileio.is_dir(self.config_directory):
            fileio.rm_dir(self.config_directory)

    @property
    def global_config(self) -> "GlobalConfig":
        """Return the global configuration to which this profile belongs."""
        return self._config or GlobalConfig()

    def activate_stack(self, stack_name: str) -> None:
        """Set the active stack for the profile.

        Args:
            stack_name: name of the stack to activate
        """
        self.active_stack = stack_name
        self.global_config._write_config()

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


class GlobalConfig(
    BaseModel, BaseGlobalConfiguration, metaclass=GlobalConfigMetaClass
):
    """Stores global configuration options.

    Configuration options are read from a config file, but can be overwritten
    by environment variables. See `GlobalConfig.__getattribute__` for more
    details.

    Attributes:
        user_id: Unique user id.
        analytics_opt_in: If a user agreed to sending analytics or not.
        version: Version of ZenML that was last used to create or update the
            global config.
        activated_profile: The name of the active configuration profile.
        profiles: Map of configuration profiles, indexed by name.
        _config_path: Directory where the global config file is stored.
    """

    user_id: uuid.UUID = Field(default_factory=uuid.uuid4, allow_mutation=False)
    analytics_opt_in: bool = True
    version: Optional[str]
    activated_profile: Optional[str]
    profiles: Dict[str, ConfigProfile] = Field(default_factory=dict)
    _config_path: str

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initializes a GlobalConfig object using values from the config file.

        GlobalConfig is a singleton class: only one instance can exist. Calling
        this constructor multiple times will always yield the same instance (see
        the exception below).

        The `config_path` argument is only meant for internal use and testing
        purposes. User code must never pass it to the constructor. When a custom
        `config_path` value is passed, an anonymous GlobalConfig instance is
        created and returned independently of the GlobalConfig singleton and
        that will have no effect as far as the rest of the ZenML core code is
        concerned.

        If the config file doesn't exist yet, we try to read values from the
        legacy (ZenML version < 0.6) config file.

        Args:
            config_path: (internal use) custom config file path. When not
                specified, the default global configuration path is used and the
                global configuration singleton instance is returned. Only used
                to create configuration copies for transfer to different
                runtime environments.
        """
        self._config_path = config_path or self.default_config_directory()
        config_values = self._read_config()
        super().__init__(**config_values)

        if not fileio.file_exists(self._config_file(config_path)):
            # if the config file hasn't been written to disk, write it now to
            # make sure to persist the unique user id
            self._write_config()

    @classmethod
    def get_instance(cls) -> Optional["GlobalConfig"]:
        """Return the GlobalConfig singleton instance.

        Returns:
            The GlobalConfig singleton instance or None, if the GlobalConfig
            hasn't been initialized yet.
        """
        return cls._global_config

    @classmethod
    def _reset_instance(cls, config: Optional["GlobalConfig"] = None) -> None:
        """Reset the GlobalConfig singleton instance.

        This method is only meant for internal use and testing purposes.

        Args:
            repo: The GlobalConfig instance to set as the global singleton.
                If None, the global GlobalConfig singleton is reset to an empty
                value.
        """
        cls._global_config = config

    @validator("version")
    def _validate_version(cls, v: Optional[str]) -> Optional[str]:
        """Validate the version attribute."""
        if v is None:
            return v

        VersionInfo.parse(v)
        return v

    def __setattr__(self, key: str, value: Any) -> None:
        """Sets an attribute on the config and persists the new value in the
        global configuration."""
        super().__setattr__(key, value)
        if key.startswith("_"):
            return
        self._write_config()

    def __getattribute__(self, key: str) -> Any:
        """Gets an attribute value for a specific key.

        If a value for this attribute was specified using an environment
        variable called `$(CONFIG_ENV_VAR_PREFIX)$(ATTRIBUTE_NAME)` and its
        value can be parsed to the attribute type, the value from this
        environment variable is returned instead.
        """
        value = super().__getattribute__(key)
        if key.startswith("_"):
            return value

        environment_variable_name = f"{CONFIG_ENV_VAR_PREFIX}{key.upper()}"
        try:
            environment_variable_value = os.environ[environment_variable_name]
            # set the environment variable value to leverage pydantics type
            # conversion and validation
            super().__setattr__(key, environment_variable_value)
            return_value = super().__getattribute__(key)
            # set back the old value as we don't want to permanently store
            # the environment variable value here
            super().__setattr__(key, value)
            return return_value
        except (ValidationError, KeyError, TypeError):
            return value

    def _migrate_config(self) -> None:
        """Migrates the global config to the latest version."""

        curr_version = VersionInfo.parse(__version__)
        if self.version is None:
            logger.info(
                "Initializing the ZenML global configuration version to %s",
                curr_version,
            )
        else:
            config_version = VersionInfo.parse(self.version)
            if self.version > curr_version:
                raise RuntimeError(
                    "The ZenML global configuration version (%s) is higher "
                    "than the version of ZenML currently being used (%s). "
                    "Please update ZenML to at least match the global "
                    "configuration version to avoid loss of information.",
                    config_version,
                    curr_version,
                )
            if config_version == curr_version:
                return

            logger.info(
                "Migrating the ZenML global configuration from version %s "
                "to version %s...",
                config_version,
                curr_version,
            )

        # this will also trigger rewriting the config file to disk
        # to ensure the schema migration results are persisted
        self.version = __version__

    def _read_config(self) -> Dict[str, Any]:
        """Reads configuration options from disk.

        If the config file doesn't exist yet, this method falls back to reading
        options from a legacy config file or returns an empty dictionary.
        """
        legacy_config_file = os.path.join(
            self.config_directory, LEGACY_CONFIG_FILE_NAME
        )

        config_values = {}
        if fileio.file_exists(self._config_file()):
            config_values = cast(
                Dict[str, Any],
                yaml_utils.read_yaml(self._config_file()),
            )
        elif fileio.file_exists(legacy_config_file):
            config_values = cast(
                Dict[str, Any], yaml_utils.read_json(legacy_config_file)
            )

        return config_values

    def _write_config(self, config_path: Optional[str] = None) -> None:
        """Writes the global configuration options to disk.

        Args:
            config_path: custom config file path. When not specified, the default
                global configuration path is used.
        """
        config_file = self._config_file(config_path)
        yaml_dict = json.loads(self.json())
        logger.debug(f"Writing config to {config_file}")

        if not fileio.file_exists(config_file):
            fileio.create_dir_recursive_if_not_exists(
                config_path or self.config_directory
            )

        yaml_utils.write_yaml(config_file, yaml_dict)

    @staticmethod
    def default_config_directory() -> str:
        """Path to the default global configuration directory."""
        return get_global_config_directory()

    def _config_file(self, config_path: Optional[str] = None) -> str:
        """Path to the file where global configuration options are stored.

        Args:
            config_path: custom config file path. When not specified, the default
                global configuration path is used.
        """
        return os.path.join(config_path or self._config_path, "config.yaml")

    def copy_config_with_active_profile(
        self,
        config_path: str,
        load_config_path: Optional[str] = None,
    ) -> "GlobalConfig":
        """Create a copy of the global config and the active repository profile
        using a different config path.

        Args:
            config_path: path where the global config copy should be saved
            load_config_path: path that will be used to load the global config
                copy. This can be set to a value different than `config_path`
                if the global config copy will be loaded from a different
                path, e.g. when the global config copy is copied to a
                container image. This will be reflected in the paths and URLs
                encoded in the copied profile.
        """
        from zenml.repository import Repository

        self._write_config(config_path)

        config_copy = GlobalConfig(config_path=config_path)
        config_copy.profiles = {}
        profile = Repository().active_profile

        profile_copy = config_copy.add_or_update_profile(profile)
        profile_copy.active_stack = Repository().active_stack_name
        config_copy.activate_profile(profile.name)

        if not profile.store_type or not profile.store_url:
            # should not happen, but just in case
            raise RuntimeError(
                f"No store type or URL set for profile " f"`{profile.name}`."
            )

        # if the profile stores its state locally inside a local directory,
        # we need to copy that as well
        store_class = Repository.get_store_class(profile.store_type)
        if not store_class:
            raise RuntimeError(
                f"No store implementation found for store type "
                f"`{profile.store_type}`."
            )

        profile_path = store_class.get_path_from_url(profile.store_url)
        dst_profile_url = store_class.get_local_url(
            profile_copy.config_directory
        )
        dst_profile_path = store_class.get_path_from_url(dst_profile_url)
        if profile_path and dst_profile_path:
            if profile_path.is_dir():
                shutil.copytree(
                    profile_path,
                    dst_profile_path,
                )
            else:
                fileio.create_dir_recursive_if_not_exists(
                    str(dst_profile_path.parent)
                )
                shutil.copyfile(profile_path, dst_profile_path)

            if load_config_path:
                dst_profile_url = dst_profile_url.replace(
                    config_path, load_config_path
                )
            profile_copy.store_url = dst_profile_url
        config_copy._write_config()
        return config_copy

    @property
    def config_directory(self) -> str:
        """Directory where the global configuration file is located."""
        return self._config_path

    def add_or_update_profile(self, profile: ConfigProfile) -> ConfigProfile:
        """Adds or updates a profile in the global configuration.

        Args:
            profile: profile configuration
        """
        profile = profile.copy()
        profile._config = self
        if profile.name not in self.profiles:
            profile.initialize()
        self.profiles[profile.name] = profile
        self._write_config()
        return profile

    def get_profile(self, profile_name: str) -> Optional[ConfigProfile]:
        """Get a global configuration profile.

        Args:
            profile_name: name of the profile to get

        Returns:
            The profile configuration or None if the profile doesn't exist
        """
        return self.profiles.get(profile_name)

    def has_profile(self, profile_name: str) -> bool:
        """Check if a named global configuration profile exists.

        Args:
            profile_name: name of the profile to check

        Returns:
            True if the profile exists, otherwise False
        """
        return profile_name in self.profiles

    def activate_profile(self, profile_name: str) -> None:
        """Set a profile as the active.

        Args:
            profile_name: name of the profile to add
        """
        if profile_name not in self.profiles:
            raise KeyError(f"Profile '{profile_name}' not found.")
        self.activated_profile = profile_name
        self._write_config()

    def _add_and_activate_default_profile(self) -> Optional[ConfigProfile]:
        """Creates and activates the default configuration profile if no
        profiles are configured.

        Returns:
            The newly created default profile or None if other profiles are
            configured.
        """

        if self.profiles:
            return None
        logger.info("Creating default profile...")
        default_profile = ConfigProfile(
            name=DEFAULT_PROFILE_NAME,
        )
        self.add_or_update_profile(default_profile)
        self.activate_profile(DEFAULT_PROFILE_NAME)
        logger.info("Created and activated default profile.")

        return default_profile

    @property
    def active_profile(self) -> Optional[ConfigProfile]:
        """Return the active profile.

        Returns:
            The active profile.
        """
        if not self.activated_profile:
            return None
        return self.profiles[self.activated_profile]

    @property
    def active_profile_name(self) -> Optional[str]:
        """Return the name of the active profile.

        Returns:
            The name of the active profile.
        """
        return self.activated_profile

    def delete_profile(self, profile_name: str) -> None:
        """Deletes a profile from the global configuration.

        If the profile is active, it cannot be removed.

        Args:
            profile_name: name of the profile to delete

        Raises:
            KeyError: if the profile does not exist
            ValueError: if the profile is active
        """
        if profile_name not in self.profiles:
            raise KeyError(f"Profile '{profile_name}' not found.")
        if profile_name == self.active_profile:
            raise ValueError(
                f"Unable to delete active profile '{profile_name}'."
            )

        profile = self.profiles[profile_name]
        del self.profiles[profile_name]
        profile.cleanup()

        self._write_config()

    def activate_stack(self, stack_name: str) -> None:
        """Set the active stack for the active profile.

        Args:
            stack_name: name of the stack to activate
        """
        if not self.active_profile:
            return
        self.active_profile.active_stack = stack_name
        self._write_config()

    @property
    def active_stack_name(self) -> Optional[str]:
        """Get the active stack name from the active profile.

        Returns:
            The active stack name or None if no active stack is set or if
            no active profile is set.
        """
        if not self.active_profile:
            return None
        return self.active_profile.active_stack

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
