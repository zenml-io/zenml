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
"""Base Zen Store implementation."""

import os
from abc import ABC
from typing import (
    Any,
    ClassVar,
    Optional,
    Tuple,
    Type,
    Union,
)
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel
from requests import ConnectionError

import zenml
from zenml.config.global_config import GlobalConfiguration
from zenml.config.server_config import ServerConfiguration
from zenml.config.store_config import StoreConfiguration
from zenml.constants import (
    DEFAULT_STACK_AND_COMPONENT_NAME,
    DEFAULT_WORKSPACE_NAME,
    ENV_ZENML_DEFAULT_WORKSPACE_NAME,
    IS_DEBUG_ENV,
)
from zenml.enums import (
    SecretsStoreType,
    StoreType,
)
from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger
from zenml.models import (
    ServerDatabaseType,
    ServerModel,
    StackFilter,
    StackResponse,
    UserFilter,
    UserResponse,
    WorkspaceResponse,
)
from zenml.zen_stores.secrets_stores.sql_secrets_store import (
    SqlSecretsStoreConfiguration,
)
from zenml.zen_stores.zen_store_interface import ZenStoreInterface

logger = get_logger(__name__)


class BaseZenStore(
    BaseModel,
    ZenStoreInterface,
    ABC,
):
    """Base class for accessing and persisting ZenML core objects.

    Attributes:
        config: The configuration of the store.
    """

    config: StoreConfiguration

    TYPE: ClassVar[StoreType]
    CONFIG_TYPE: ClassVar[Type[StoreConfiguration]]

    # ---------------------------------
    # Initialization and configuration
    # ---------------------------------

    def __init__(
        self,
        skip_default_registrations: bool = False,
        **kwargs: Any,
    ) -> None:
        """Create and initialize a store.

        Args:
            skip_default_registrations: If `True`, the creation of the default
                stack and user in the store will be skipped.
            **kwargs: Additional keyword arguments to pass to the Pydantic
                constructor.

        Raises:
            RuntimeError: If the store cannot be initialized.
            AuthorizationException: If the store cannot be initialized due to
                authentication errors.
        """
        super().__init__(**kwargs)

        try:
            self._initialize()

        # Handle cases where the ZenML server is not available
        except ConnectionError as e:
            error_message = (
                "Cannot connect to the ZenML database because the ZenML server "
                f"at {self.url} is not running."
            )
            if urlparse(self.url).hostname in ["localhost", "127.0.0.1"]:
                recommendation = (
                    "Please run `zenml down` and `zenml up` to restart the "
                    "server."
                )
            else:
                recommendation = (
                    "Please run `zenml disconnect` and `zenml connect --url "
                    f"{self.url}` to reconnect to the server."
                )
            raise RuntimeError(f"{error_message}\n{recommendation}") from e

        except AuthorizationException as e:
            raise AuthorizationException(
                f"Authorization failed for store at '{self.url}'. Please check "
                f"your credentials: {str(e)}"
            )

        except Exception as e:
            raise RuntimeError(
                f"Error initializing {self.type.value} store with URL "
                f"'{self.url}': {str(e)}"
            ) from e

        if not skip_default_registrations:
            logger.debug("Initializing database")
            self._initialize_database()
        else:
            logger.debug("Skipping database initialization")

    @staticmethod
    def get_store_class(store_type: StoreType) -> Type["BaseZenStore"]:
        """Returns the class of the given store type.

        Args:
            store_type: The type of the store to get the class for.

        Returns:
            The class of the given store type or None if the type is unknown.

        Raises:
            TypeError: If the store type is unsupported.
        """
        if store_type == StoreType.SQL:
            from zenml.zen_stores.sql_zen_store import SqlZenStore

            return SqlZenStore
        elif store_type == StoreType.REST:
            from zenml.zen_stores.rest_zen_store import RestZenStore

            return RestZenStore
        else:
            raise TypeError(
                f"No store implementation found for store type "
                f"`{store_type.value}`."
            )

    @staticmethod
    def get_store_config_class(
        store_type: StoreType,
    ) -> Type["StoreConfiguration"]:
        """Returns the store config class of the given store type.

        Args:
            store_type: The type of the store to get the class for.

        Returns:
            The config class of the given store type.
        """
        store_class = BaseZenStore.get_store_class(store_type)
        return store_class.CONFIG_TYPE

    @staticmethod
    def get_store_type(url: str) -> StoreType:
        """Returns the store type associated with a URL schema.

        Args:
            url: The store URL.

        Returns:
            The store type associated with the supplied URL schema.

        Raises:
            TypeError: If no store type was found to support the supplied URL.
        """
        from zenml.zen_stores.rest_zen_store import RestZenStoreConfiguration
        from zenml.zen_stores.sql_zen_store import SqlZenStoreConfiguration

        if SqlZenStoreConfiguration.supports_url_scheme(url):
            return StoreType.SQL
        elif RestZenStoreConfiguration.supports_url_scheme(url):
            return StoreType.REST
        else:
            raise TypeError(f"No store implementation found for URL: {url}.")

    @staticmethod
    def create_store(
        config: StoreConfiguration,
        skip_default_registrations: bool = False,
        **kwargs: Any,
    ) -> "BaseZenStore":
        """Create and initialize a store from a store configuration.

        Args:
            config: The store configuration to use.
            skip_default_registrations: If `True`, the creation of the default
                stack and user in the store will be skipped.
            **kwargs: Additional keyword arguments to pass to the store class

        Returns:
            The initialized store.
        """
        logger.debug(f"Creating store with config '{config}'...")
        store_class = BaseZenStore.get_store_class(config.type)
        store = store_class(
            config=config,
            skip_default_registrations=skip_default_registrations,
            **kwargs,
        )

        return store

    @staticmethod
    def get_default_store_config(path: str) -> StoreConfiguration:
        """Get the default store configuration.

        The default store is a SQLite store that saves the DB contents on the
        local filesystem.

        Args:
            path: The local path where the store DB will be stored.

        Returns:
            The default store configuration.
        """
        from zenml.zen_stores.sql_zen_store import SqlZenStoreConfiguration

        config = SqlZenStoreConfiguration(
            type=StoreType.SQL,
            url=SqlZenStoreConfiguration.get_local_url(path),
            secrets_store=SqlSecretsStoreConfiguration(
                type=SecretsStoreType.SQL,
            ),
        )
        return config

    def _initialize_database(self) -> None:
        """Initialize the database on first use."""

    @property
    def url(self) -> str:
        """The URL of the store.

        Returns:
            The URL of the store.
        """
        return self.config.url

    @property
    def type(self) -> StoreType:
        """The type of the store.

        Returns:
            The type of the store.
        """
        return self.TYPE

    def validate_active_config(
        self,
        active_workspace_name_or_id: Optional[Union[str, UUID]] = None,
        active_stack_id: Optional[UUID] = None,
        config_name: str = "",
    ) -> Tuple[WorkspaceResponse, StackResponse]:
        """Validate the active configuration.

        Call this method to validate the supplied active workspace and active
        stack values.

        This method is guaranteed to return valid workspace ID and stack ID
        values. If the supplied workspace and stack are not set or are not valid
        (e.g. they do not exist or are not accessible), the default workspace and
        default workspace stack will be returned in their stead.

        Args:
            active_workspace_name_or_id: The name or ID of the active workspace.
            active_stack_id: The ID of the active stack.
            config_name: The name of the configuration to validate (used in the
                displayed logs/messages).

        Returns:
            A tuple containing the active workspace and active stack.
        """
        active_workspace: WorkspaceResponse

        if active_workspace_name_or_id:
            try:
                active_workspace = self.get_workspace(
                    active_workspace_name_or_id
                )
            except KeyError:
                active_workspace = self._get_default_workspace()

                logger.warning(
                    f"The current {config_name} active workspace is no longer "
                    f"available. Resetting the active workspace to "
                    f"'{active_workspace.name}'."
                )
        else:
            active_workspace = self._get_default_workspace()

            logger.info(
                f"Setting the {config_name} active workspace "
                f"to '{active_workspace.name}'."
            )

        active_stack: StackResponse

        # Sanitize the active stack
        if active_stack_id:
            # Ensure that the active stack is still valid
            try:
                active_stack = self.get_stack(stack_id=active_stack_id)
            except KeyError:
                logger.warning(
                    "The current %s active stack is no longer available. "
                    "Resetting the active stack to default.",
                    config_name,
                )
                active_stack = self._get_default_stack(
                    workspace_id=active_workspace.id
                )
            else:
                if active_stack.workspace.id != active_workspace.id:
                    logger.warning(
                        "The current %s active stack is not part of the active "
                        "workspace. Resetting the active stack to default.",
                        config_name,
                    )
                    active_stack = self._get_default_stack(
                        workspace_id=active_workspace.id
                    )

        else:
            logger.warning(
                "Setting the %s active stack to default.",
                config_name,
            )
            active_stack = self._get_default_stack(
                workspace_id=active_workspace.id
            )

        return active_workspace, active_stack

    def get_store_info(self) -> ServerModel:
        """Get information about the store.

        Returns:
            Information about the store.
        """
        from zenml.zen_stores.sql_zen_store import SqlZenStore

        server_config = ServerConfiguration.get_server_config()
        deployment_type = server_config.deployment_type
        auth_scheme = server_config.auth_scheme
        metadata = server_config.metadata
        secrets_store_type = SecretsStoreType.NONE
        if isinstance(self, SqlZenStore) and self.config.secrets_store:
            secrets_store_type = self.config.secrets_store.type
        use_legacy_dashboard = server_config.use_legacy_dashboard
        return ServerModel(
            id=GlobalConfiguration().user_id,
            active=True,
            version=zenml.__version__,
            deployment_type=deployment_type,
            database_type=ServerDatabaseType.OTHER,
            debug=IS_DEBUG_ENV,
            secrets_store_type=secrets_store_type,
            auth_scheme=auth_scheme,
            server_url=server_config.server_url or "",
            dashboard_url=server_config.dashboard_url or "",
            analytics_enabled=GlobalConfiguration().analytics_opt_in,
            metadata=metadata,
            use_legacy_dashboard=use_legacy_dashboard,
        )

    def is_local_store(self) -> bool:
        """Check if the store is local or connected to a local ZenML server.

        Returns:
            True if the store is local, False otherwise.
        """
        return self.get_store_info().is_local()

    # -----------------------------
    # Default workspaces and stacks
    # -----------------------------

    @property
    def _default_workspace_name(self) -> str:
        """Get the default workspace name.

        Returns:
            The default workspace name.
        """
        return os.getenv(
            ENV_ZENML_DEFAULT_WORKSPACE_NAME, DEFAULT_WORKSPACE_NAME
        )

    def _get_default_workspace(self) -> WorkspaceResponse:
        """Get the default workspace.

        Raises:
            KeyError: If the default workspace doesn't exist.

        Returns:
            The default workspace.
        """
        try:
            return self.get_workspace(self._default_workspace_name)
        except KeyError:
            raise KeyError("Unable to find default workspace.")

    def _get_default_stack(
        self,
        workspace_id: UUID,
    ) -> StackResponse:
        """Get the default stack for a user in a workspace.

        Args:
            workspace_id: ID of the workspace.

        Returns:
            The default stack in the workspace.

        Raises:
            KeyError: if the workspace or default stack doesn't exist.
        """
        default_stacks = self.list_stacks(
            StackFilter(
                workspace_id=workspace_id,
                name=DEFAULT_STACK_AND_COMPONENT_NAME,
            )
        )
        if default_stacks.total == 0:
            raise KeyError(
                f"No default stack found in workspace {workspace_id}."
            )
        return default_stacks.items[0]

    def get_external_user(self, user_id: UUID) -> UserResponse:
        """Get a user by external ID.

        Args:
            user_id: The external ID of the user.

        Returns:
            The user with the supplied external ID.

        Raises:
            KeyError: If the user doesn't exist.
        """
        users = self.list_users(UserFilter(external_user_id=user_id))
        if users.total == 0:
            raise KeyError(f"User with external ID '{user_id}' not found.")
        return users.items[0]

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
