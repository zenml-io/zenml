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
    Callable,
    ClassVar,
    Dict,
    List,
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
from zenml.analytics.utils import analytics_disabler
from zenml.config.global_config import GlobalConfiguration
from zenml.config.store_config import StoreConfiguration
from zenml.constants import (
    ENV_ZENML_DEFAULT_USER_NAME,
    ENV_ZENML_DEFAULT_USER_PASSWORD,
    ENV_ZENML_DEFAULT_WORKSPACE_NAME,
    ENV_ZENML_SERVER_DEPLOYMENT_TYPE,
    IS_DEBUG_ENV,
)
from zenml.enums import (
    PermissionType,
    SecretsStoreType,
    StackComponentType,
    StoreType,
)
from zenml.logger import get_logger
from zenml.models import (
    ComponentRequestModel,
    RoleFilterModel,
    RoleRequestModel,
    RoleResponseModel,
    StackFilterModel,
    StackRequestModel,
    StackResponseModel,
    UserRequestModel,
    UserResponseModel,
    UserRoleAssignmentRequestModel,
    WorkspaceRequestModel,
    WorkspaceResponseModel,
)
from zenml.models.page_model import Page
from zenml.models.server_models import (
    ServerDatabaseType,
    ServerDeploymentType,
    ServerModel,
)
from zenml.utils.proxy_utils import make_proxy_class
from zenml.zen_stores.enums import StoreEvent
from zenml.zen_stores.secrets_stores.base_secrets_store import BaseSecretsStore
from zenml.zen_stores.secrets_stores.secrets_store_interface import (
    SecretsStoreInterface,
)
from zenml.zen_stores.secrets_stores.sql_secrets_store import (
    SqlSecretsStoreConfiguration,
)
from zenml.zen_stores.zen_store_interface import ZenStoreInterface

logger = get_logger(__name__)

DEFAULT_USERNAME = "default"
DEFAULT_PASSWORD = ""
DEFAULT_WORKSPACE_NAME = "default"
DEFAULT_STACK_NAME = "default"
DEFAULT_STACK_COMPONENT_NAME = "default"
DEFAULT_ADMIN_ROLE = "admin"
DEFAULT_GUEST_ROLE = "guest"


@make_proxy_class(SecretsStoreInterface, "_secrets_store")
class BaseZenStore(
    BaseModel,
    ZenStoreInterface,
    SecretsStoreInterface,
    ABC,
):
    """Base class for accessing and persisting ZenML core objects.

    Attributes:
        config: The configuration of the store.
    """

    config: StoreConfiguration
    _secrets_store: Optional[BaseSecretsStore] = None
    _event_handlers: Dict[StoreEvent, List[Callable[..., Any]]] = {}

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

        secrets_store_config = store.config.secrets_store

        # Initialize the secrets store
        if (
            secrets_store_config
            and secrets_store_config.type != SecretsStoreType.NONE
        ):
            secrets_store_class = BaseSecretsStore.get_store_class(
                secrets_store_config
            )
            store._secrets_store = secrets_store_class(
                zen_store=store,
                config=secrets_store_config,
            )
            # Update the config with the actual secrets store config
            # to reflect the default values in the saved configuration
            store.config.secrets_store = store._secrets_store.config
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
        try:
            default_workspace = self._default_workspace
        except KeyError:
            default_workspace = self._create_default_workspace()
        try:
            assert self._admin_role
        except KeyError:
            self._create_admin_role()
        try:
            assert self._guest_role
        except KeyError:
            self._create_guest_role()
        try:
            default_user = self._default_user
        except KeyError:
            default_user = self._create_default_user()
        try:
            self._get_default_stack(
                workspace_name_or_id=default_workspace.id,
                user_name_or_id=default_user.id,
            )
        except KeyError:
            self._create_default_stack(
                workspace_name_or_id=default_workspace.id,
                user_name_or_id=default_user.id,
            )

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

    @property
    def secrets_store(self) -> Optional["BaseSecretsStore"]:
        """The secrets store associated with this store.

        Returns:
            The secrets store associated with this store.
        """
        return self._secrets_store

    def validate_active_config(
        self,
        active_workspace_name_or_id: Optional[Union[str, UUID]] = None,
        active_stack_id: Optional[UUID] = None,
        config_name: str = "",
    ) -> Tuple[WorkspaceResponseModel, StackResponseModel]:
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
        active_workspace: WorkspaceResponseModel

        if active_workspace_name_or_id:
            try:
                active_workspace = self.get_workspace(
                    active_workspace_name_or_id
                )
            except KeyError:
                active_workspace = self._get_or_create_default_workspace()

                logger.warning(
                    f"The current {config_name} active workspace is no longer "
                    f"available. Resetting the active workspace to "
                    f"'{active_workspace.name}'."
                )
        else:
            active_workspace = self._get_or_create_default_workspace()

            logger.info(
                f"Setting the {config_name} active workspace "
                f"to '{active_workspace.name}'."
            )

        active_stack: StackResponseModel

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
                active_stack = self._get_or_create_default_stack(
                    active_workspace
                )
            else:
                if active_stack.workspace.id != active_workspace.id:
                    logger.warning(
                        "The current %s active stack is not part of the active "
                        "workspace. Resetting the active stack to default.",
                        config_name,
                    )
                    active_stack = self._get_or_create_default_stack(
                        active_workspace
                    )
                elif not active_stack.is_shared and (
                    not active_stack.user
                    or (active_stack.user.id != self.get_user().id)
                ):
                    logger.warning(
                        "The current %s active stack is not shared and not "
                        "owned by the active user. "
                        "Resetting the active stack to default.",
                        config_name,
                    )
                    active_stack = self._get_or_create_default_stack(
                        active_workspace
                    )
        else:
            logger.warning(
                "Setting the %s active stack to default.",
                config_name,
            )
            active_stack = self._get_or_create_default_stack(active_workspace)

        return active_workspace, active_stack

    def get_store_info(self) -> ServerModel:
        """Get information about the store.

        Returns:
            Information about the store.
        """
        return ServerModel(
            id=GlobalConfiguration().user_id,
            version=zenml.__version__,
            deployment_type=os.environ.get(
                ENV_ZENML_SERVER_DEPLOYMENT_TYPE, ServerDeploymentType.OTHER
            ),
            database_type=ServerDatabaseType.OTHER,
            debug=IS_DEBUG_ENV,
            secrets_store_type=self.secrets_store.type
            if self.secrets_store
            else SecretsStoreType.NONE,
        )

    def is_local_store(self) -> bool:
        """Check if the store is local or connected to a local ZenML server.

        Returns:
            True if the store is local, False otherwise.
        """
        return self.get_store_info().is_local()

    def _get_or_create_default_stack(
        self, workspace: "WorkspaceResponseModel"
    ) -> "StackResponseModel":
        try:
            return self._get_default_stack(
                workspace_name_or_id=workspace.id,
                user_name_or_id=self.get_user().id,
            )
        except KeyError:
            return self._create_default_stack(
                workspace_name_or_id=workspace.id,
                user_name_or_id=self.get_user().id,
            )

    def _get_or_create_default_workspace(self) -> "WorkspaceResponseModel":
        try:
            return self._default_workspace
        except KeyError:
            return self._create_default_workspace()

    # --------------
    # Event Handlers
    # --------------

    def register_event_handler(
        self,
        event: StoreEvent,
        handler: Callable[..., Any],
    ) -> None:
        """Register an external event handler.

        The handler will be called when the store event is triggered.

        Args:
            event: The event to register the handler for.
            handler: The handler function to register.
        """
        self._event_handlers.setdefault(event, []).append(handler)

    def _trigger_event(self, event: StoreEvent, **kwargs: Any) -> None:
        """Trigger an event and call all registered handlers.

        Args:
            event: The event to trigger.
            **kwargs: The event arguments.
        """
        for handler in self._event_handlers.get(event, []):
            try:
                handler(event, **kwargs)
            except Exception as e:
                logger.error(
                    f"Silently ignoring error caught while triggering event "
                    f"store handler for event {event.value}: {e}",
                    exc_info=True,
                )

    # ------
    # Stacks
    # ------

    def _create_default_stack(
        self,
        workspace_name_or_id: Union[str, UUID],
        user_name_or_id: Union[str, UUID],
    ) -> StackResponseModel:
        """Create the default stack components and stack.

        The default stack contains a local orchestrator and a local artifact
        store.

        Args:
            workspace_name_or_id: Name or ID of the workspace to which the stack
                belongs.
            user_name_or_id: The name or ID of the user that owns the stack.

        Returns:
            The model of the created default stack.
        """
        with analytics_disabler():
            workspace = self.get_workspace(
                workspace_name_or_id=workspace_name_or_id
            )
            user = self.get_user(user_name_or_id=user_name_or_id)

            logger.info(
                f"Creating default stack for user '{user.name}' in workspace "
                f"{workspace.name}..."
            )

            # Register the default orchestrator
            orchestrator = self.create_stack_component(
                component=ComponentRequestModel(
                    user=user.id,
                    workspace=workspace.id,
                    name=DEFAULT_STACK_COMPONENT_NAME,
                    type=StackComponentType.ORCHESTRATOR,
                    flavor="local",
                    configuration={},
                ),
            )

            # Register the default artifact store
            artifact_store = self.create_stack_component(
                component=ComponentRequestModel(
                    user=user.id,
                    workspace=workspace.id,
                    name=DEFAULT_STACK_COMPONENT_NAME,
                    type=StackComponentType.ARTIFACT_STORE,
                    flavor="local",
                    configuration={},
                ),
            )

            components = {
                c.type: [c.id] for c in [orchestrator, artifact_store]
            }
            # Register the default stack
            stack = StackRequestModel(
                name=DEFAULT_STACK_NAME,
                components=components,
                is_shared=False,
                workspace=workspace.id,
                user=user.id,
            )
            return self.create_stack(stack=stack)

    def _get_default_stack(
        self,
        workspace_name_or_id: Union[str, UUID],
        user_name_or_id: Union[str, UUID],
    ) -> StackResponseModel:
        """Get the default stack for a user in a workspace.

        Args:
            workspace_name_or_id: Name or ID of the workspace.
            user_name_or_id: Name or ID of the user.

        Returns:
            The default stack in the workspace owned by the supplied user.

        Raises:
            KeyError: if the workspace or default stack doesn't exist.
        """
        default_stacks = self.list_stacks(
            StackFilterModel(
                workspace_id=workspace_name_or_id,
                user_id=user_name_or_id,
                name=DEFAULT_STACK_NAME,
            )
        )
        if default_stacks.total == 0:
            raise KeyError(
                f"No default stack found for user {str(user_name_or_id)} in "
                f"workspace {str(workspace_name_or_id)}"
            )
        return default_stacks.items[0]

    # -----
    # Roles
    # -----
    @property
    def _admin_role(self) -> RoleResponseModel:
        """Get the admin role.

        Returns:
            The default admin role.
        """
        return self.get_role(DEFAULT_ADMIN_ROLE)

    def _create_admin_role(self) -> RoleResponseModel:
        """Creates the admin role.

        Returns:
            The admin role
        """
        logger.info(f"Creating '{DEFAULT_ADMIN_ROLE}' role ...")
        return self.create_role(
            RoleRequestModel(
                name=DEFAULT_ADMIN_ROLE,
                permissions={
                    PermissionType.READ,
                    PermissionType.WRITE,
                    PermissionType.ME,
                },
            )
        )

    @property
    def _guest_role(self) -> RoleResponseModel:
        """Get the guest role.

        Returns:
            The guest role.
        """
        return self.get_role(DEFAULT_GUEST_ROLE)

    def _create_guest_role(self) -> RoleResponseModel:
        """Creates the guest role.

        Returns:
            The guest role
        """
        logger.info(f"Creating '{DEFAULT_GUEST_ROLE}' role ...")
        return self.create_role(
            RoleRequestModel(
                name=DEFAULT_GUEST_ROLE,
                permissions={
                    PermissionType.READ,
                    PermissionType.ME,
                },
            )
        )

    # -----
    # Users
    # -----

    @property
    def _default_user_name(self) -> str:
        """Get the default user name.

        Returns:
            The default user name.
        """
        return os.getenv(ENV_ZENML_DEFAULT_USER_NAME, DEFAULT_USERNAME)

    @property
    def _default_user(self) -> UserResponseModel:
        """Get the default user.

        Returns:
            The default user.

        Raises:
            KeyError: If the default user doesn't exist.
        """
        user_name = self._default_user_name
        try:
            return self.get_user(user_name)
        except KeyError:
            raise KeyError(f"The default user '{user_name}' is not configured")

    def _create_default_user(self) -> UserResponseModel:
        """Creates a default user with the admin role.

        Returns:
            The default user.
        """
        user_name = os.getenv(ENV_ZENML_DEFAULT_USER_NAME, DEFAULT_USERNAME)
        user_password = os.getenv(
            ENV_ZENML_DEFAULT_USER_PASSWORD, DEFAULT_PASSWORD
        )

        logger.info(f"Creating default user '{user_name}' ...")
        new_user = self.create_user(
            UserRequestModel(
                name=user_name,
                active=True,
                password=user_password,
            )
        )
        self.create_user_role_assignment(
            UserRoleAssignmentRequestModel(
                role=self._admin_role.id,
                user=new_user.id,
                workspace=None,
            )
        )
        return new_user

    # -----
    # Roles
    # -----

    @property
    def roles(self) -> Page[RoleResponseModel]:
        """All existing roles.

        Returns:
            A list of all existing roles.
        """
        return self.list_roles(RoleFilterModel())

    # --------
    # Workspaces
    # --------

    @property
    def _default_workspace_name(self) -> str:
        """Get the default workspace name.

        Returns:
            The default workspace name.
        """
        return os.getenv(
            ENV_ZENML_DEFAULT_WORKSPACE_NAME, DEFAULT_WORKSPACE_NAME
        )

    @property
    def _default_workspace(self) -> WorkspaceResponseModel:
        """Get the default workspace.

        Returns:
            The default workspace.

        Raises:
            KeyError: if the default workspace doesn't exist.
        """
        workspace_name = self._default_workspace_name
        try:
            return self.get_workspace(workspace_name)
        except KeyError:
            raise KeyError(
                f"The default workspace '{workspace_name}' is not configured"
            )

    def _create_default_workspace(self) -> WorkspaceResponseModel:
        """Creates a default workspace.

        Returns:
            The default workspace.
        """
        workspace_name = self._default_workspace_name
        logger.info(f"Creating default workspace '{workspace_name}' ...")
        return self.create_workspace(
            WorkspaceRequestModel(name=workspace_name)
        )

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
