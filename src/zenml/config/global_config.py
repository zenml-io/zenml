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
"""Functionality to support ZenML GlobalConfiguration."""

import json
import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, cast
from uuid import UUID

from packaging import version
from pydantic import BaseModel, Field, SecretStr, ValidationError, validator
from pydantic.main import ModelMetaclass

from zenml import __version__
from zenml.analytics import group
from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.config.store_config import StoreConfiguration
from zenml.constants import (
    DEFAULT_STORE_DIRECTORY_NAME,
    ENV_ZENML_BACKUP_SECRETS_STORE_PREFIX,
    ENV_ZENML_LOCAL_STORES_PATH,
    ENV_ZENML_SECRETS_STORE_PREFIX,
    ENV_ZENML_SERVER,
    ENV_ZENML_STORE_PREFIX,
    LOCAL_STORES_DIRECTORY_NAME,
)
from zenml.enums import StoreType
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import io_utils, yaml_utils

if TYPE_CHECKING:
    from zenml.models import StackResponse, WorkspaceResponse
    from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)

CONFIG_ENV_VAR_PREFIX = "ZENML_"


class GlobalConfigMetaClass(ModelMetaclass):
    """Global configuration metaclass.

    This metaclass is used to enforce a singleton instance of the
    GlobalConfiguration class with the following additional properties:

    * the GlobalConfiguration is initialized automatically on import with the
    default configuration, if no config file exists yet.
    * the GlobalConfiguration undergoes a schema migration if the version of the
    config file is older than the current version of the ZenML package.
    * a default store is set if no store is configured yet.
    """

    def __init__(cls, *args: Any, **kwargs: Any) -> None:
        """Initialize a singleton class.

        Args:
            *args: positional arguments
            **kwargs: keyword arguments
        """
        super().__init__(*args, **kwargs)
        cls._global_config: Optional["GlobalConfiguration"] = None

    def __call__(cls, *args: Any, **kwargs: Any) -> "GlobalConfiguration":
        """Create or return the default global config instance.

        Args:
            *args: positional arguments
            **kwargs: keyword arguments

        Returns:
            The global GlobalConfiguration instance.
        """
        if not cls._global_config:
            cls._global_config = cast(
                "GlobalConfiguration", super().__call__()
            )
            cls._global_config._migrate_config()
        return cls._global_config


class GlobalConfiguration(BaseModel, metaclass=GlobalConfigMetaClass):
    """Stores global configuration options.

    Configuration options are read from a config file, but can be overwritten
    by environment variables. See `GlobalConfiguration.__getattribute__` for
    more details.

    Attributes:
        user_id: Unique user id.
        user_email: Email address associated with this client.
        user_email_opt_in: Whether the user has opted in to email communication.
        analytics_opt_in: If a user agreed to sending analytics or not.
        version: Version of ZenML that was last used to create or update the
            global config.
        store: Store configuration.
        active_stack_id: The ID of the active stack.
        active_workspace_name: The name of the active workspace.
        jwt_secret_key: The secret key used to sign and verify JWT tokens.
    """

    user_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_email: Optional[str] = None
    user_email_opt_in: Optional[bool] = None
    analytics_opt_in: bool = True
    version: Optional[str]
    store: Optional[StoreConfiguration]
    active_stack_id: Optional[uuid.UUID]
    active_workspace_name: Optional[str]

    _zen_store: Optional["BaseZenStore"] = None
    _active_workspace: Optional["WorkspaceResponse"] = None
    _active_stack: Optional["StackResponse"] = None

    def __init__(self) -> None:
        """Initializes a GlobalConfiguration using values from the config file.

        GlobalConfiguration is a singleton class: only one instance can exist.
        Calling this constructor multiple times will always yield the same
        instance.
        """
        config_values = self._read_config()

        super().__init__(**config_values)

        if not fileio.exists(self._config_file):
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
        if config:
            config._write_config()

    @validator("version")
    def _validate_version(cls, v: Optional[str]) -> Optional[str]:
        """Validate the version attribute.

        Args:
            v: The version attribute value.

        Returns:
            The version attribute value.

        Raises:
            RuntimeError: If the version parsing fails.
        """
        if v is None:
            return v

        if not isinstance(version.parse(v), version.Version):
            # If the version parsing fails, it returns a `LegacyVersion`
            # instead. Check to make sure it's an actual `Version` object
            # which represents a valid version.
            raise RuntimeError(
                f"Invalid version in global configuration: {v}."
            )

        return v

    def __setattr__(self, key: str, value: Any) -> None:
        """Sets an attribute and persists it in the global configuration.

        Args:
            key: The attribute name.
            value: The attribute value.
        """
        super().__setattr__(key, value)
        if key.startswith("_"):
            return
        self._write_config()

    def __custom_getattribute__(self, key: str) -> Any:
        """Gets an attribute value for a specific key.

        If a value for this attribute was specified using an environment
        variable called `$(CONFIG_ENV_VAR_PREFIX)$(ATTRIBUTE_NAME)` and its
        value can be parsed to the attribute type, the value from this
        environment variable is returned instead.

        Args:
            key: The attribute name.

        Returns:
            The attribute value.
        """
        value = super().__getattribute__(key)
        if key.startswith("_") or key not in type(self).__fields__:
            return value

        environment_variable_name = f"{CONFIG_ENV_VAR_PREFIX}{key.upper()}"
        try:
            environment_variable_value = os.environ[environment_variable_name]
            # set the environment variable value to leverage Pydantic's type
            # conversion and validation
            super().__setattr__(key, environment_variable_value)
            return_value = super().__getattribute__(key)
            # set back the old value as we don't want to permanently store
            # the environment variable value here
            super().__setattr__(key, value)
            return return_value
        except (ValidationError, KeyError, TypeError):
            return value

    if not TYPE_CHECKING:
        # When defining __getattribute__, mypy allows accessing non-existent
        # attributes without failing
        # (see https://github.com/python/mypy/issues/13319).
        __getattribute__ = __custom_getattribute__

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
                    "Read more about this issue and how to solve it here: "
                    "`https://docs.zenml.io/user-guide/advanced-guide/environment-management/global-settings-of-zenml#version-mismatch-downgrading`",
                    config_version,
                    curr_version,
                )
                # TODO [ENG-899]: Give more detailed instruction on how to
                #  resolve version mismatch.
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

        If the config file doesn't exist yet, this method returns an empty
        dictionary.

        Returns:
            A dictionary containing the configuration options.
        """
        config_file = self._config_file
        config_values = {}
        if fileio.exists(config_file):
            config_values = cast(
                Dict[str, Any],
                yaml_utils.read_yaml(config_file),
            )

        return config_values

    def _write_config(self) -> None:
        """Writes the global configuration options to disk."""
        config_file = self._config_file
        yaml_dict = json.loads(self.json(exclude_none=True))
        logger.debug(f"Writing config to {config_file}")

        if not fileio.exists(config_file):
            io_utils.create_dir_recursive_if_not_exists(self.config_directory)

        yaml_utils.write_yaml(config_file, yaml_dict)

    def _configure_store(
        self,
        config: StoreConfiguration,
        skip_default_registrations: bool = False,
        **kwargs: Any,
    ) -> None:
        """Configure the global zen store.

        This method creates and initializes the global store according to the
        supplied configuration.

        Args:
            config: The new store configuration to use.
            skip_default_registrations: If `True`, the creation of the default
                stack and user in the store will be skipped.
            **kwargs: Additional keyword arguments to pass to the store
                constructor.
        """
        from zenml.zen_stores.base_zen_store import BaseZenStore

        if self.store == config and self._zen_store:
            # TODO: Do we actually need to create/initialize the store here
            #   or can we just return instead? We think this is just getting
            #   called for default registrations.
            BaseZenStore.create_store(
                config, skip_default_registrations, **kwargs
            )
            return

        # TODO: Revisit the flow regarding the registration of the default
        #  entities once the analytics v1 is removed.
        store = BaseZenStore.create_store(config, True, **kwargs)

        logger.debug(f"Configuring the global store to {store.config}")
        self.store = store.config
        self._zen_store = store

        if not skip_default_registrations:
            store._initialize_database()

        # Sanitize the global configuration to reflect the new store
        self._sanitize_config()
        self._write_config()

        local_stores_path = Path(self.local_stores_path)
        local_stores_path.mkdir(parents=True, exist_ok=True)

    def _sanitize_config(self) -> None:
        """Sanitize and save the global configuration.

        This method is called to ensure that the active stack and workspace
        are set to their default values, if possible.
        """
        # If running in a ZenML server environment, the active stack and
        # workspace are not relevant
        if ENV_ZENML_SERVER in os.environ:
            return
        active_workspace, active_stack = self.zen_store.validate_active_config(
            self.active_workspace_name,
            self.active_stack_id,
            config_name="global",
        )
        self.active_workspace_name = active_workspace.name
        self._active_workspace = active_workspace
        self.set_active_stack(active_stack)

    @property
    def _config_file(self) -> str:
        """Path to the file where global configuration options are stored.

        Args:
            config_path: custom config file path. When not specified, the
                default global configuration path is used.

        Returns:
            The path to the global configuration file.
        """
        return os.path.join(self.config_directory, "config.yaml")

    @property
    def config_directory(self) -> str:
        """Directory where the global configuration file is located.

        Returns:
            The directory where the global configuration file is located.
        """
        return io_utils.get_global_config_directory()

    @property
    def local_stores_path(self) -> str:
        """Path where local stores information is stored.

        Returns:
            The path where local stores information is stored.
        """
        if ENV_ZENML_LOCAL_STORES_PATH in os.environ:
            return os.environ[ENV_ZENML_LOCAL_STORES_PATH]

        return os.path.join(
            self.config_directory,
            LOCAL_STORES_DIRECTORY_NAME,
        )

    def get_config_environment_vars(self) -> Dict[str, str]:
        """Convert the global configuration to environment variables.

        Returns:
            Environment variables dictionary.
        """
        from zenml.zen_stores.rest_zen_store import RestZenStore

        environment_vars = {}

        for key in self.__fields__.keys():
            if key == "store":
                # The store configuration uses its own environment variable
                # naming scheme
                continue

            value = getattr(self, key)
            if value is not None:
                environment_vars[CONFIG_ENV_VAR_PREFIX + key.upper()] = str(
                    value
                )

        store_dict = self.store_configuration.dict(exclude_none=True)

        # The secrets store and backup secrets store configurations use their
        # own environment variables naming scheme
        secrets_store_dict = store_dict.pop("secrets_store", None) or {}
        backup_secrets_store_dict = (
            store_dict.pop("backup_secrets_store", None) or {}
        )

        for key, value in store_dict.items():
            if key in ["username", "password"]:
                # Never include the username and password in the env vars. Use
                # the API token instead.
                continue

            environment_vars[ENV_ZENML_STORE_PREFIX + key.upper()] = str(value)

        for key, value in secrets_store_dict.items():
            environment_vars[
                ENV_ZENML_SECRETS_STORE_PREFIX + key.upper()
            ] = str(value)

        for key, value in backup_secrets_store_dict.items():
            environment_vars[
                ENV_ZENML_BACKUP_SECRETS_STORE_PREFIX + key.upper()
            ] = str(value)

        return environment_vars

    def get_default_store(self) -> StoreConfiguration:
        """Get the default store configuration.

        Returns:
            The default store configuration.
        """
        from zenml.zen_stores.base_zen_store import BaseZenStore

        env_store_config: Dict[str, str] = {}
        env_secrets_store_config: Dict[str, str] = {}
        env_backup_secrets_store_config: Dict[str, str] = {}
        for k, v in os.environ.items():
            if v == "":
                continue
            if k.startswith(ENV_ZENML_STORE_PREFIX):
                env_store_config[k[len(ENV_ZENML_STORE_PREFIX) :].lower()] = v
            elif k.startswith(ENV_ZENML_SECRETS_STORE_PREFIX):
                env_secrets_store_config[
                    k[len(ENV_ZENML_SECRETS_STORE_PREFIX) :].lower()
                ] = v
            elif k.startswith(ENV_ZENML_BACKUP_SECRETS_STORE_PREFIX):
                env_backup_secrets_store_config[
                    k[len(ENV_ZENML_BACKUP_SECRETS_STORE_PREFIX) :].lower()
                ] = v

        if len(env_store_config):
            if "type" not in env_store_config and "url" in env_store_config:
                env_store_config["type"] = BaseZenStore.get_store_type(
                    env_store_config["url"]
                )

            logger.debug(
                "Using environment variables to configure the default store"
            )

            config = StoreConfiguration(
                **env_store_config,
            )
        elif self.store:
            config = self.store
        else:
            config = BaseZenStore.get_default_store_config(
                path=os.path.join(
                    self.local_stores_path,
                    DEFAULT_STORE_DIRECTORY_NAME,
                )
            )

        if len(env_secrets_store_config):
            if "type" not in env_secrets_store_config:
                env_secrets_store_config["type"] = config.type.value

            logger.debug(
                "Using environment variables to configure the secrets store"
            )

            config.secrets_store = SecretsStoreConfiguration(
                **env_secrets_store_config
            )

        if len(env_backup_secrets_store_config):
            if "type" not in env_backup_secrets_store_config:
                env_backup_secrets_store_config["type"] = config.type.value

            logger.debug(
                "Using environment variables to configure the backup secrets "
                "store"
            )

            config.backup_secrets_store = SecretsStoreConfiguration(
                **env_backup_secrets_store_config
            )

        return config

    def set_default_store(self) -> None:
        """Creates and sets the default store configuration.

        Call this method to initialize or revert the store configuration to the
        default store.
        """
        default_store_cfg = self.get_default_store()
        self._configure_store(default_store_cfg)
        logger.debug("Using the default store for the global config.")

    def uses_default_store(self) -> bool:
        """Check if the global configuration uses the default store.

        Returns:
            `True` if the global configuration uses the default store.
        """
        return (
            self.store is not None
            and self.store.url == self.get_default_store().url
        )

    def set_store(
        self,
        config: StoreConfiguration,
        skip_default_registrations: bool = False,
        **kwargs: Any,
    ) -> None:
        """Update the active store configuration.

        Call this method to validate and update the active store configuration.

        Args:
            config: The new store configuration to use.
            skip_default_registrations: If `True`, the creation of the default
                stack and user in the store will be skipped.
            **kwargs: Additional keyword arguments to pass to the store
                constructor.
        """
        self._configure_store(config, skip_default_registrations, **kwargs)
        logger.info("Updated the global store configuration.")

        if self.zen_store.type == StoreType.REST:
            # Every time a client connects to a ZenML server, we want to
            # group the client ID and the server ID together. This records
            # only that a particular client has successfully connected to a
            # particular server at least once, but no information about the
            # user account is recorded here.
            server_info = self.zen_store.get_store_info()

            group(
                group_id=server_info.id,
                group_metadata={
                    "version": server_info.version,
                    "deployment_type": str(server_info.deployment_type),
                    "database_type": str(server_info.database_type),
                },
            )

    @property
    def zen_store(self) -> "BaseZenStore":
        """Initialize and/or return the global zen store.

        If the store hasn't been initialized yet, it is initialized when this
        property is first accessed according to the global store configuration.

        Returns:
            The current zen store.
        """
        if self._zen_store is None:
            self.set_default_store()
        assert self._zen_store is not None

        return self._zen_store

    def set_active_workspace(
        self, workspace: "WorkspaceResponse"
    ) -> "WorkspaceResponse":
        """Set the workspace for the local client.

        Args:
            workspace: The workspace to set active.

        Returns:
            The workspace that was set active.
        """
        self.active_workspace_name = workspace.name
        self._active_workspace = workspace
        # Sanitize the global configuration to reflect the new workspace
        self._sanitize_config()
        return workspace

    def set_active_stack(self, stack: "StackResponse") -> None:
        """Set the active stack for the local client.

        Args:
            stack: The model of the stack to set active.
        """
        self.active_stack_id = stack.id
        self._active_stack = stack

    def get_active_workspace(self) -> "WorkspaceResponse":
        """Get a model of the active workspace for the local client.

        Returns:
            The model of the active workspace.
        """
        workspace_name = self.get_active_workspace_name()

        if self._active_workspace is not None:
            return self._active_workspace

        workspace = self.zen_store.get_workspace(
            workspace_name_or_id=workspace_name,
        )
        return self.set_active_workspace(workspace)

    def get_active_workspace_name(self) -> str:
        """Get the name of the active workspace.

        If the active workspace doesn't exist yet, the ZenStore is reinitialized.

        Returns:
            The name of the active workspace.
        """
        if self.active_workspace_name is None:
            _ = self.zen_store
            assert self.active_workspace_name is not None

        return self.active_workspace_name

    def get_active_stack_id(self) -> UUID:
        """Get the ID of the active stack.

        If the active stack doesn't exist yet, the ZenStore is reinitialized.

        Returns:
            The active stack ID.
        """
        if self.active_stack_id is None:
            _ = self.zen_store
            assert self.active_stack_id is not None

        return self.active_stack_id

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

        # This is needed to allow correct handling of SecretStr values during
        # serialization.
        json_encoders = {
            SecretStr: lambda v: v.get_secret_value() if v else None
        }
