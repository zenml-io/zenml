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
    Dict,
    Optional,
    Tuple,
    Type,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

import zenml
from zenml.config.global_config import GlobalConfiguration
from zenml.config.server_config import ServerConfiguration
from zenml.config.store_config import StoreConfiguration
from zenml.constants import (
    DEFAULT_PROJECT_NAME,
    DEFAULT_STACK_AND_COMPONENT_NAME,
    ENV_ZENML_DEFAULT_PROJECT_NAME,
    ENV_ZENML_SERVER,
    IS_DEBUG_ENV,
)
from zenml.enums import (
    SecretsStoreType,
    StoreType,
)
from zenml.exceptions import IllegalOperationError
from zenml.logger import get_logger
from zenml.models import (
    ProjectResponse,
    ServerDatabaseType,
    ServerDeploymentType,
    ServerModel,
    StackFilter,
    StackResponse,
    UserFilter,
    UserResponse,
)
from zenml.utils.pydantic_utils import before_validator_handler
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

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def convert_config(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Method to infer the correct type of the config and convert.

        Args:
            data: The provided configuration object, can potentially be a
                generic object

        Raises:
            ValueError: If the provided config object's type does not match
                any of the current implementations.

        Returns:
            The converted configuration object.
        """
        if data["config"].type == StoreType.SQL:
            from zenml.zen_stores.sql_zen_store import SqlZenStoreConfiguration

            data["config"] = SqlZenStoreConfiguration(
                **data["config"].model_dump()
            )

        elif data["config"].type == StoreType.REST:
            from zenml.zen_stores.rest_zen_store import (
                RestZenStoreConfiguration,
            )

            data["config"] = RestZenStoreConfiguration(
                **data["config"].model_dump()
            )
        else:
            raise ValueError(
                f"Unknown type '{data['config'].type}' for the configuration."
            )

        return data

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
        """
        super().__init__(**kwargs)

        self._initialize()

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
            if os.environ.get(ENV_ZENML_SERVER):
                from zenml.zen_server.rbac.rbac_sql_zen_store import (
                    RBACSqlZenStore,
                )

                return RBACSqlZenStore
            else:
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
        from zenml.zen_stores.secrets_stores.sql_secrets_store import (
            SqlSecretsStoreConfiguration,
        )
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
        active_project_name_or_id: Optional[Union[str, UUID]] = None,
        active_stack_id: Optional[UUID] = None,
        config_name: str = "",
    ) -> Tuple[Optional[ProjectResponse], StackResponse]:
        """Validate the active configuration.

        Call this method to validate the supplied active project and active
        stack values.

        This method returns a valid project and stack values. If the
        supplied project and stack are not set or are not valid (e.g. they
        do not exist or are not accessible), the default project and default
        stack will be returned in their stead.

        Args:
            active_project_name_or_id: The name or ID of the active project.
            active_stack_id: The ID of the active stack.
            config_name: The name of the configuration to validate (used in the
                displayed logs/messages).

        Returns:
            A tuple containing the active project and active stack.
        """
        active_project: Optional[ProjectResponse] = None

        if active_project_name_or_id:
            try:
                active_project = self.get_project(active_project_name_or_id)
            except (KeyError, IllegalOperationError):
                active_project_name_or_id = None
                logger.warning(
                    f"The current {config_name} active project is no longer "
                    f"available."
                )

        if active_project is None:
            try:
                active_project = self._get_default_project()
            except (KeyError, IllegalOperationError):
                logger.warning(
                    "An active project is not set. Please set the active "
                    "project by running `zenml project set "
                    "<project-name>`."
                )
            else:
                logger.info(
                    f"Setting the {config_name} active project "
                    f"to '{active_project.name}'."
                )

        active_stack: StackResponse

        # Sanitize the active stack
        if active_stack_id:
            # Ensure that the active stack is still valid
            try:
                active_stack = self.get_stack(stack_id=active_stack_id)
            except (KeyError, IllegalOperationError):
                logger.warning(
                    "The current %s active stack is no longer available. "
                    "Resetting the active stack to default.",
                    config_name,
                )
                active_stack = self._get_default_stack()

        else:
            logger.warning(
                "Setting the %s active stack to default.",
                config_name,
            )
            active_stack = self._get_default_stack()

        return active_project, active_stack

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
        store_info = ServerModel(
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
        )

        # Add ZenML Pro specific store information to the server model, if available.
        if store_info.deployment_type == ServerDeploymentType.CLOUD:
            from zenml.config.server_config import ServerProConfiguration

            pro_config = ServerProConfiguration.get_server_config()

            store_info.pro_api_url = pro_config.api_url
            store_info.pro_dashboard_url = pro_config.dashboard_url
            store_info.pro_organization_id = pro_config.organization_id
            store_info.pro_workspace_id = pro_config.workspace_id
            if pro_config.workspace_name:
                store_info.pro_workspace_name = pro_config.workspace_name
            if pro_config.organization_name:
                store_info.pro_organization_name = pro_config.organization_name

        return store_info

    def is_local_store(self) -> bool:
        """Check if the store is local or connected to a local ZenML server.

        Returns:
            True if the store is local, False otherwise.
        """
        return self.get_store_info().is_local()

    # -----------------------------
    # Default projects and stacks
    # -----------------------------

    @property
    def _default_project_name(self) -> str:
        """Get the default project name.

        Returns:
            The default project name.
        """
        return os.getenv(ENV_ZENML_DEFAULT_PROJECT_NAME, DEFAULT_PROJECT_NAME)

    def _get_default_project(self) -> ProjectResponse:
        """Get the default project.

        Raises:
            KeyError: If the default project doesn't exist.

        Returns:
            The default project.
        """
        try:
            return self.get_project(self._default_project_name)
        except KeyError:
            raise KeyError("Unable to find default project.")

    def _get_default_stack(
        self,
    ) -> StackResponse:
        """Get the default stack.

        Returns:
            The default stack.

        Raises:
            KeyError: if the default stack doesn't exist.
        """
        default_stacks = self.list_stacks(
            StackFilter(
                name=DEFAULT_STACK_AND_COMPONENT_NAME,
            )
        )
        if default_stacks.total == 0:
            raise KeyError("No default stack found.")
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

    model_config = ConfigDict(
        # Validate attributes when assigning them. We need to set this in order
        # to have a mix of mutable and immutable attributes
        validate_assignment=True,
        # Ignore extra attributes from configs of previous ZenML versions
        extra="ignore",
    )
