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
import logging
import os
import uuid
from typing import Any, Dict, Optional, cast

from packaging import version
from pydantic import BaseModel, Field, ValidationError, validator
from pydantic.main import ModelMetaclass

from zenml import __version__
from zenml.config.base_config import BaseConfiguration
from zenml.config.profile_config import (
    DEFAULT_PROFILE_NAME,
    ProfileConfiguration,
)
from zenml.io import fileio, utils
from zenml.logger import disable_logging, get_logger
from zenml.utils import yaml_utils
from zenml.utils.analytics_utils import AnalyticsEvent, track_event

logger = get_logger(__name__)


LEGACY_CONFIG_FILE_NAME = ".zenglobal.json"
CONFIG_ENV_VAR_PREFIX = "ZENML_"


class GlobalConfigMetaClass(ModelMetaclass):
    """Global configuration metaclass.

    This metaclass is used to enforce a singleton instance of the
    GlobalConfiguration class with the following additional properties:

    * the GlobalConfiguration is initialized automatically on import with the
    default configuration, if no config file exists yet.
    * an empty default profile is added to the global config on initialization
    if no other profiles are configured yet.
    * the GlobalConfiguration undergoes a schema migration if the version of the
    config file is older than the current version of the ZenML package.
    """

    def __init__(cls, *args: Any, **kwargs: Any) -> None:
        """Initialize a singleton class."""
        super().__init__(*args, **kwargs)
        cls._global_config: Optional["GlobalConfiguration"] = None

    def __call__(cls, *args: Any, **kwargs: Any) -> "GlobalConfiguration":
        """Create or return the default global config instance.

        If the GlobalConfiguration constructor is called with custom arguments,
        the singleton functionality of the metaclass is bypassed: a new
        GlobalConfiguration instance is created and returned immediately and
        without saving it as the global GlobalConfiguration singleton.
        """
        if args or kwargs:
            return cast(
                "GlobalConfiguration", super().__call__(*args, **kwargs)
            )

        if not cls._global_config:
            cls._global_config = cast(
                "GlobalConfiguration", super().__call__(*args, **kwargs)
            )
            cls._global_config._migrate_config()
            cls._global_config._add_and_activate_default_profile()

        return cls._global_config


class GlobalConfiguration(
    BaseModel, BaseConfiguration, metaclass=GlobalConfigMetaClass
):
    """Stores global configuration options.

    Configuration options are read from a config file, but can be overwritten
    by environment variables. See `GlobalConfiguration.__getattribute__` for
    more details.

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
    user_metadata: Optional[Dict[str, str]]
    analytics_opt_in: bool = True
    version: Optional[str]
    activated_profile: Optional[str]
    profiles: Dict[str, ProfileConfiguration] = Field(default_factory=dict)
    _config_path: str

    def __init__(
        self, config_path: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Initializes a GlobalConfiguration object using values from the config
        file.

        GlobalConfiguration is a singleton class: only one instance can exist.
        Calling this constructor multiple times will always yield the same
        instance (see the exception below).

        The `config_path` argument is only meant for internal use and testing
        purposes. User code must never pass it to the constructor. When a custom
        `config_path` value is passed, an anonymous GlobalConfiguration instance
        is created and returned independently of the GlobalConfiguration
        singleton and that will have no effect as far as the rest of the ZenML
        core code is concerned.

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
        config_values.update(**kwargs)
        super().__init__(**config_values)

        if not fileio.exists(self._config_file(config_path)):
            self._write_config()

    @classmethod
    def get_instance(cls) -> Optional["GlobalConfiguration"]:
        """Return the GlobalConfiguration singleton instance.

        Returns:
            The GlobalConfiguration singleton instance or None, if the
            GlobalConfiguration hasn't been initialized yet.
        """
        return cls._global_config

    @classmethod
    def _reset_instance(
        cls, config: Optional["GlobalConfiguration"] = None
    ) -> None:
        """Reset the GlobalConfiguration singleton instance.

        This method is only meant for internal use and testing purposes.

        Args:
            config: The GlobalConfiguration instance to set as the global
                singleton. If None, the global GlobalConfiguration singleton is
                reset to an empty value.
        """
        cls._global_config = config

    @validator("version")
    def _validate_version(cls, v: Optional[str]) -> Optional[str]:
        """Validate the version attribute."""
        if v is None:
            return v

        if not isinstance(version.parse(v), version.Version):
            # If the version parsing fails, it returns a `LegacyVersion` instead.
            # Check to make sure it's an actual `Version` object which represents
            # a valid version.
            raise RuntimeError(f"Invalid version in global configuration: {v}.")

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

        curr_version = version.parse(__version__)
        if self.version is None:
            logger.info(
                "Initializing the ZenML global configuration version to %s",
                curr_version,
            )
        else:
            config_version = version.parse(self.version)
            if config_version > curr_version:
                logger.error(
                    "The ZenML global configuration version (%s) is higher "
                    "than the version of ZenML currently being used (%s). "
                    "This may happen if you recently downgraded ZenML to an "
                    "earlier version, or if you have already used a more "
                    "recent ZenML version on the same machine. "
                    "It is highly recommended that you update ZenML to at "
                    "least match the global configuration version, otherwise "
                    "you may run into unexpected issues such as model schema "
                    "validation failures or even loss of information.",
                    config_version,
                    curr_version,
                )
                # TODO [ENG-899]: Give more detailed instruction on how to resolve
                #  version mismatch.
                return

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
        if fileio.exists(self._config_file()):
            config_values = cast(
                Dict[str, Any],
                yaml_utils.read_yaml(self._config_file()),
            )
        elif fileio.exists(legacy_config_file):
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

        if not fileio.exists(config_file):
            utils.create_dir_recursive_if_not_exists(
                config_path or self.config_directory
            )

        yaml_utils.write_yaml(config_file, yaml_dict)

    @staticmethod
    def default_config_directory() -> str:
        """Path to the default global configuration directory."""
        return utils.get_global_config_directory()

    def _config_file(self, config_path: Optional[str] = None) -> str:
        """Path to the file where global configuration options are stored.

        Args:
            config_path: custom config file path. When not specified, the default
                global configuration path is used.
        """
        return os.path.join(config_path or self._config_path, "config.yaml")

    def copy_active_configuration(
        self,
        config_path: str,
        load_config_path: Optional[str] = None,
    ) -> "GlobalConfiguration":
        """Create a copy of the global config, the active repository profile
        and the active stack using a different configuration path.

        This method is used to extract the active slice of the current state
        (consisting only of the global configuration, the active profile and the
        active stack) and store it in a different configuration path, where it
        can be loaded in the context of a new environment, such as a container
        image.

        Args:
            config_path: path where the active configuration copy should be saved
            load_config_path: path that will be used to load the configuration
                copy. This can be set to a value different from `config_path`
                if the configuration copy will be loaded from a different
                path, e.g. when the global config copy is copied to a
                container image. This will be reflected in the paths and URLs
                encoded in the profile copy.
        """
        from zenml.repository import Repository

        self._write_config(config_path)

        config_copy = GlobalConfiguration(config_path=config_path)
        config_copy.profiles = {}

        repo = Repository()
        profile = ProfileConfiguration(
            name=repo.active_profile_name,
            active_stack=repo.active_stack_name,
        )

        profile._config = config_copy
        # circumvent the profile initialization done in the
        # ProfileConfiguration and the Repository classes to avoid triggering
        # the analytics and interact directly with the store creation
        config_copy.profiles[profile.name] = profile
        # We dont need to track analytics here
        store = Repository.create_store(
            profile,
            skip_default_registrations=True,
            track_analytics=False,
            skip_migration=True,
        )
        # transfer the active stack to the new store. we disable logs for this
        # call so there is no confusion about newly registered stacks/stack
        # components
        with disable_logging(logging.INFO):
            store.register_stack(
                repo.zen_store.get_stack(repo.active_stack_name)
            )

        # if a custom load config path is specified, use it to replace the
        # current store local path in the profile URL
        if load_config_path:
            profile.store_url = store.url.replace(
                str(config_copy.config_directory), load_config_path
            )

        config_copy._write_config()
        return config_copy

    @property
    def config_directory(self) -> str:
        """Directory where the global configuration file is located."""
        return self._config_path

    def add_or_update_profile(
        self, profile: ProfileConfiguration
    ) -> ProfileConfiguration:
        """Adds or updates a profile in the global configuration.

        Args:
            profile: profile configuration

        Returns:
            the profile configuration added to the global configuration
        """
        profile = profile.copy()
        profile._config = self
        if profile.name not in self.profiles:
            profile.initialize()
            track_event(
                AnalyticsEvent.INITIALIZED_PROFILE,
                {"store_type": profile.store_type.value},
            )
        self.profiles[profile.name] = profile
        self._write_config()
        return profile

    def get_profile(self, profile_name: str) -> Optional[ProfileConfiguration]:
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

        Raises:
            KeyError: If the profile with the given name does not exist.
        """
        if profile_name not in self.profiles:
            raise KeyError(f"Profile '{profile_name}' not found.")
        self.activated_profile = profile_name
        self._write_config()

    def _add_and_activate_default_profile(
        self,
    ) -> Optional[ProfileConfiguration]:
        """Creates and activates the default configuration profile if no
        profiles are configured.

        Returns:
            The newly created default profile or None if other profiles are
            configured.
        """

        if self.profiles:
            return None
        logger.info("Creating default profile...")
        default_profile = ProfileConfiguration(
            name=DEFAULT_PROFILE_NAME,
        )
        self.add_or_update_profile(default_profile)
        self.activate_profile(DEFAULT_PROFILE_NAME)
        logger.info("Created and activated default profile.")

        return default_profile

    @property
    def active_profile(self) -> Optional[ProfileConfiguration]:
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

        return self.active_profile.get_active_stack()

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
