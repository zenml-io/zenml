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

import functools
import json
import os
from abc import ABCMeta
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
from uuid import UUID, uuid4

from pydantic import ConfigDict, SecretStr

from zenml.client_lazy_loader import (
    client_lazy_loader,
    evaluate_all_lazy_load_args_in_client_methods,
)
from zenml.config.global_config import GlobalConfiguration
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.config.source import Source
from zenml.constants import (
    ENV_ZENML_ACTIVE_STACK_ID,
    ENV_ZENML_ACTIVE_WORKSPACE_ID,
    ENV_ZENML_ENABLE_REPO_INIT_WARNINGS,
    ENV_ZENML_REPOSITORY_PATH,
    ENV_ZENML_SERVER,
    PAGE_SIZE_DEFAULT,
    PAGINATION_STARTING_PAGE,
    REPOSITORY_DIRECTORY_NAME,
    TEXT_FIELD_MAX_LENGTH,
    handle_bool_env_var,
)
from zenml.enums import (
    ArtifactType,
    LogicalOperators,
    MetadataResourceTypes,
    ModelStages,
    OAuthDeviceStatus,
    PluginSubType,
    PluginType,
    SecretScope,
    SorterOps,
    StackComponentType,
    StoreType,
)
from zenml.exceptions import (
    AuthorizationException,
    EntityExistsError,
    IllegalOperationError,
    InitializationException,
    ValidationError,
    ZenKeyError,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.models import (
    ActionFilter,
    ActionRequest,
    ActionResponse,
    ActionUpdate,
    APIKeyFilter,
    APIKeyRequest,
    APIKeyResponse,
    APIKeyRotateRequest,
    APIKeyUpdate,
    ArtifactFilter,
    ArtifactResponse,
    ArtifactUpdate,
    ArtifactVersionFilter,
    ArtifactVersionResponse,
    ArtifactVersionUpdate,
    BaseIdentifiedResponse,
    CodeRepositoryFilter,
    CodeRepositoryRequest,
    CodeRepositoryResponse,
    CodeRepositoryUpdate,
    ComponentFilter,
    ComponentRequest,
    ComponentResponse,
    ComponentUpdate,
    EventSourceFilter,
    EventSourceRequest,
    EventSourceResponse,
    EventSourceUpdate,
    FlavorFilter,
    FlavorRequest,
    FlavorResponse,
    ModelFilter,
    ModelRequest,
    ModelResponse,
    ModelUpdate,
    ModelVersionArtifactFilter,
    ModelVersionArtifactResponse,
    ModelVersionFilter,
    ModelVersionPipelineRunFilter,
    ModelVersionPipelineRunResponse,
    ModelVersionRequest,
    ModelVersionResponse,
    ModelVersionUpdate,
    OAuthDeviceFilter,
    OAuthDeviceResponse,
    OAuthDeviceUpdate,
    Page,
    PipelineBuildFilter,
    PipelineBuildResponse,
    PipelineDeploymentFilter,
    PipelineDeploymentResponse,
    PipelineFilter,
    PipelineResponse,
    PipelineRunFilter,
    PipelineRunResponse,
    RunMetadataFilter,
    RunMetadataRequest,
    RunMetadataResponse,
    RunTemplateFilter,
    RunTemplateRequest,
    RunTemplateResponse,
    RunTemplateUpdate,
    ScheduleFilter,
    ScheduleResponse,
    SecretFilter,
    SecretRequest,
    SecretResponse,
    SecretUpdate,
    ServerSettingsResponse,
    ServerSettingsUpdate,
    ServiceAccountFilter,
    ServiceAccountRequest,
    ServiceAccountResponse,
    ServiceAccountUpdate,
    ServiceConnectorFilter,
    ServiceConnectorRequest,
    ServiceConnectorResourcesModel,
    ServiceConnectorResponse,
    ServiceConnectorTypeModel,
    ServiceConnectorUpdate,
    ServiceFilter,
    ServiceRequest,
    ServiceResponse,
    ServiceUpdate,
    StackFilter,
    StackRequest,
    StackResponse,
    StackUpdate,
    StepRunFilter,
    StepRunResponse,
    TagFilter,
    TagRequest,
    TagResponse,
    TagUpdate,
    TriggerExecutionFilter,
    TriggerExecutionResponse,
    TriggerFilter,
    TriggerRequest,
    TriggerResponse,
    TriggerUpdate,
    UserFilter,
    UserRequest,
    UserResponse,
    UserUpdate,
    WorkspaceFilter,
    WorkspaceRequest,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from zenml.services.service import ServiceConfig
from zenml.services.service_status import ServiceState
from zenml.services.service_type import ServiceType
from zenml.utils import io_utils, source_utils
from zenml.utils.dict_utils import dict_to_bytes
from zenml.utils.filesync_model import FileSyncModel
from zenml.utils.pagination_utils import depaginate
from zenml.utils.uuid_utils import is_valid_uuid

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType, MetadataTypeEnum
    from zenml.service_connectors.service_connector import ServiceConnector
    from zenml.stack import Stack
    from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)

AnyResponse = TypeVar("AnyResponse", bound=BaseIdentifiedResponse)  # type: ignore[type-arg]
F = TypeVar("F", bound=Callable[..., Any])


class ClientConfiguration(FileSyncModel):
    """Pydantic object used for serializing client configuration options."""

    _active_workspace: Optional["WorkspaceResponse"] = None
    active_workspace_id: Optional[UUID] = None
    active_stack_id: Optional[UUID] = None
    _active_stack: Optional["StackResponse"] = None

    @property
    def active_workspace(self) -> "WorkspaceResponse":
        """Get the active workspace for the local client.

        Returns:
            The active workspace.

        Raises:
            RuntimeError: If no active workspace is set.
        """
        if self._active_workspace:
            return self._active_workspace
        else:
            raise RuntimeError(
                "No active workspace is configured. Run "
                "`zenml workspace set WORKSPACE_NAME` to set the active "
                "workspace."
            )

    def set_active_workspace(self, workspace: "WorkspaceResponse") -> None:
        """Set the workspace for the local client.

        Args:
            workspace: The workspace to set active.
        """
        self._active_workspace = workspace
        self.active_workspace_id = workspace.id

    def set_active_stack(self, stack: "StackResponse") -> None:
        """Set the stack for the local client.

        Args:
            stack: The stack to set active.
        """
        self.active_stack_id = stack.id
        self._active_stack = stack

    model_config = ConfigDict(
        # Validate attributes when assigning them. We need to set this in order
        # to have a mix of mutable and immutable attributes
        validate_assignment=True,
        # Allow extra attributes from configs of previous ZenML versions to
        # permit downgrading
        extra="allow",
    )


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
        if args or kwargs:
            return cast("Client", super().__call__(*args, **kwargs))

        if not cls._global_client:
            cls._global_client = cast(
                "Client", super().__call__(*args, **kwargs)
            )

        return cls._global_client


def _fail_for_sql_zen_store(method: F) -> F:
    """Decorator for methods that are not allowed with a SQLZenStore.

    Args:
        method: The method to decorate.

    Returns:
        The decorated method.
    """

    @functools.wraps(method)
    def wrapper(self: "Client", *args: Any, **kwargs: Any) -> Any:
        # No isinstance check to avoid importing ZenStore implementations
        if self.zen_store.__class__.__name__ == "SqlZenStore":
            raise TypeError(
                "This method is not allowed when not connected "
                "to a ZenML Server through the API interface."
            )
        return method(self, *args, **kwargs)

    return cast(F, wrapper)


@evaluate_all_lazy_load_args_in_client_methods
class Client(metaclass=ClientMetaClass):
    """ZenML client class.

    The ZenML client manages configuration options for ZenML stacks as well
    as their components.
    """

    _active_user: Optional["UserResponse"] = None

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
        used instead to manage the active stack, workspace etc.

        Args:
            root: The path to set as the active repository root. If not set,
                the repository root is determined using the environment
                variable `ZENML_REPOSITORY_PATH` (if set) and by recursively
                searching in the parent directories of the current working
                directory.
        """
        enable_warnings = handle_bool_env_var(
            ENV_ZENML_ENABLE_REPO_INIT_WARNINGS, False
        )
        self._root = self.find_repository(
            root, enable_warnings=enable_warnings
        )

        if not self._root:
            self._config = None
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
        workspace that no longer exists.
        """
        if not self._config:
            return

        active_workspace, active_stack = self.zen_store.validate_active_config(
            self._config.active_workspace_id,
            self._config.active_stack_id,
            config_name="repo",
        )
        self._config.set_active_stack(active_stack)
        self._config.set_active_workspace(active_workspace)

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

        return ClientConfiguration(config_file=config_path)

    @staticmethod
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

    @staticmethod
    def is_inside_repository(file_path: str) -> bool:
        """Returns whether a file is inside the active ZenML repository.

        Args:
            file_path: A file path.

        Returns:
            True if the file is inside the active ZenML repository, False
            otherwise.
        """
        if repo_path := Client.find_repository():
            return repo_path in Path(file_path).resolve().parents
        return False

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
        return self.root / REPOSITORY_DIRECTORY_NAME if self.root else None

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

    def set_active_workspace(
        self, workspace_name_or_id: Union[str, UUID]
    ) -> "WorkspaceResponse":
        """Set the workspace for the local client.

        Args:
            workspace_name_or_id: The name or ID of the workspace to set active.

        Returns:
            The model of the active workspace.
        """
        workspace = self.zen_store.get_workspace(
            workspace_name_or_id=workspace_name_or_id
        )  # raises KeyError
        if self._config:
            self._config.set_active_workspace(workspace)
            # Sanitize the client configuration to reflect the current
            # settings
            self._sanitize_config()
        else:
            # set the active workspace globally only if the client doesn't use
            # a local configuration
            GlobalConfiguration().set_active_workspace(workspace)
        return workspace

    # ----------------------------- Server Settings ----------------------------

    def get_settings(self, hydrate: bool = True) -> ServerSettingsResponse:
        """Get the server settings.

        Args:
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The server settings.
        """
        return self.zen_store.get_server_settings(hydrate=hydrate)

    def update_server_settings(
        self,
        updated_name: Optional[str] = None,
        updated_logo_url: Optional[str] = None,
        updated_enable_analytics: Optional[bool] = None,
        updated_enable_announcements: Optional[bool] = None,
        updated_enable_updates: Optional[bool] = None,
        updated_onboarding_state: Optional[Dict[str, Any]] = None,
    ) -> ServerSettingsResponse:
        """Update the server settings.

        Args:
            updated_name: Updated name for the server.
            updated_logo_url: Updated logo URL for the server.
            updated_enable_analytics: Updated value whether to enable
                analytics for the server.
            updated_enable_announcements: Updated value whether to display
                announcements about ZenML.
            updated_enable_updates: Updated value whether to display updates
                about ZenML.
            updated_onboarding_state: Updated onboarding state for the server.

        Returns:
            The updated server settings.
        """
        update_model = ServerSettingsUpdate(
            server_name=updated_name,
            logo_url=updated_logo_url,
            enable_analytics=updated_enable_analytics,
            display_announcements=updated_enable_announcements,
            display_updates=updated_enable_updates,
            onboarding_state=updated_onboarding_state,
        )
        return self.zen_store.update_server_settings(update_model)

    # ---------------------------------- Users ---------------------------------

    def create_user(
        self,
        name: str,
        password: Optional[str] = None,
        is_admin: bool = False,
    ) -> UserResponse:
        """Create a new user.

        Args:
            name: The name of the user.
            password: The password of the user. If not provided, the user will
                be created with empty password.
            is_admin: Whether the user should be an admin.

        Returns:
            The model of the created user.
        """
        user = UserRequest(
            name=name, password=password or None, is_admin=is_admin
        )
        user.active = (
            password != "" if self.zen_store.type != StoreType.REST else True
        )
        created_user = self.zen_store.create_user(user=user)

        return created_user

    def get_user(
        self,
        name_id_or_prefix: Union[str, UUID],
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> UserResponse:
        """Gets a user.

        Args:
            name_id_or_prefix: The name or ID of the user.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The User
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_user,
            list_method=self.list_users,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            hydrate=hydrate,
        )

    def list_users(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        external_user_id: Optional[str] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        name: Optional[str] = None,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        active: Optional[bool] = None,
        email_opted_in: Optional[bool] = None,
        hydrate: bool = False,
    ) -> Page[UserResponse]:
        """List all users.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of stacks to filter by.
            external_user_id: Use the external user id for filtering.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            name: Use the username for filtering
            full_name: Use the user full name for filtering
            email: Use the user email for filtering
            active: User the user active status for filtering
            email_opted_in: Use the user opt in status for filtering
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The User
        """
        return self.zen_store.list_users(
            UserFilter(
                sort_by=sort_by,
                page=page,
                size=size,
                logical_operator=logical_operator,
                id=id,
                external_user_id=external_user_id,
                created=created,
                updated=updated,
                name=name,
                full_name=full_name,
                email=email,
                active=active,
                email_opted_in=email_opted_in,
            ),
            hydrate=hydrate,
        )

    def update_user(
        self,
        name_id_or_prefix: Union[str, UUID],
        updated_name: Optional[str] = None,
        updated_full_name: Optional[str] = None,
        updated_email: Optional[str] = None,
        updated_email_opt_in: Optional[bool] = None,
        updated_password: Optional[str] = None,
        old_password: Optional[str] = None,
        updated_is_admin: Optional[bool] = None,
        updated_metadata: Optional[Dict[str, Any]] = None,
        active: Optional[bool] = None,
    ) -> UserResponse:
        """Update a user.

        Args:
            name_id_or_prefix: The name or ID of the user to update.
            updated_name: The new name of the user.
            updated_full_name: The new full name of the user.
            updated_email: The new email of the user.
            updated_email_opt_in: The new email opt-in status of the user.
            updated_password: The new password of the user.
            old_password: The old password of the user. Required for password
                update.
            updated_is_admin: Whether the user should be an admin.
            updated_metadata: The new metadata for the user.
            active: Use to activate or deactivate the user.

        Returns:
            The updated user.

        Raises:
            ValidationError: If the old password is not provided when updating
                the password.
        """
        user = self.get_user(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )
        user_update = UserUpdate(name=updated_name or user.name)
        if updated_full_name:
            user_update.full_name = updated_full_name
        if updated_email is not None:
            user_update.email = updated_email
            user_update.email_opted_in = (
                updated_email_opt_in or user.email_opted_in
            )
        if updated_email_opt_in is not None:
            user_update.email_opted_in = updated_email_opt_in
        if updated_password is not None:
            user_update.password = updated_password
            if old_password is None:
                raise ValidationError(
                    "Old password is required to update the password."
                )
            user_update.old_password = old_password
        if updated_is_admin is not None:
            user_update.is_admin = updated_is_admin
        if active is not None:
            user_update.active = active

        if updated_metadata is not None:
            user_update.user_metadata = updated_metadata

        return self.zen_store.update_user(
            user_id=user.id, user_update=user_update
        )

    @_fail_for_sql_zen_store
    def deactivate_user(self, name_id_or_prefix: str) -> "UserResponse":
        """Deactivate a user and generate an activation token.

        Args:
            name_id_or_prefix: The name or ID of the user to reset.

        Returns:
            The deactivated user.
        """
        from zenml.zen_stores.rest_zen_store import RestZenStore

        user = self.get_user(name_id_or_prefix, allow_name_prefix_match=False)
        assert isinstance(self.zen_store, RestZenStore)
        return self.zen_store.deactivate_user(user_name_or_id=user.name)

    def delete_user(self, name_id_or_prefix: str) -> None:
        """Delete a user.

        Args:
            name_id_or_prefix: The name or ID of the user to delete.
        """
        user = self.get_user(name_id_or_prefix, allow_name_prefix_match=False)
        self.zen_store.delete_user(user_name_or_id=user.name)

    @property
    def active_user(self) -> "UserResponse":
        """Get the user that is currently in use.

        Returns:
            The active user.
        """
        if self._active_user is None:
            self._active_user = self.zen_store.get_user(include_private=True)
        return self._active_user

    # -------------------------------- Workspaces ------------------------------

    def create_workspace(
        self, name: str, description: str
    ) -> WorkspaceResponse:
        """Create a new workspace.

        Args:
            name: Name of the workspace.
            description: Description of the workspace.

        Returns:
            The created workspace.
        """
        return self.zen_store.create_workspace(
            WorkspaceRequest(name=name, description=description)
        )

    def get_workspace(
        self,
        name_id_or_prefix: Optional[Union[UUID, str]],
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> WorkspaceResponse:
        """Gets a workspace.

        Args:
            name_id_or_prefix: The name or ID of the workspace.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The workspace
        """
        if not name_id_or_prefix:
            return self.active_workspace
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_workspace,
            list_method=self.list_workspaces,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            hydrate=hydrate,
        )

    def list_workspaces(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        name: Optional[str] = None,
        hydrate: bool = False,
    ) -> Page[WorkspaceResponse]:
        """List all workspaces.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the workspace ID to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            name: Use the workspace name for filtering
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            Page of workspaces
        """
        return self.zen_store.list_workspaces(
            WorkspaceFilter(
                sort_by=sort_by,
                page=page,
                size=size,
                logical_operator=logical_operator,
                id=id,
                created=created,
                updated=updated,
                name=name,
            ),
            hydrate=hydrate,
        )

    def update_workspace(
        self,
        name_id_or_prefix: Optional[Union[UUID, str]],
        new_name: Optional[str] = None,
        new_description: Optional[str] = None,
    ) -> WorkspaceResponse:
        """Update a workspace.

        Args:
            name_id_or_prefix: Name, ID or prefix of the workspace to update.
            new_name: New name of the workspace.
            new_description: New description of the workspace.

        Returns:
            The updated workspace.
        """
        workspace = self.get_workspace(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )
        workspace_update = WorkspaceUpdate(name=new_name or workspace.name)
        if new_description:
            workspace_update.description = new_description
        return self.zen_store.update_workspace(
            workspace_id=workspace.id,
            workspace_update=workspace_update,
        )

    def delete_workspace(self, name_id_or_prefix: str) -> None:
        """Delete a workspace.

        Args:
            name_id_or_prefix: The name or ID of the workspace to delete.

        Raises:
            IllegalOperationError: If the workspace to delete is the active
                workspace.
        """
        workspace = self.get_workspace(
            name_id_or_prefix, allow_name_prefix_match=False
        )
        if self.active_workspace.id == workspace.id:
            raise IllegalOperationError(
                f"Workspace '{name_id_or_prefix}' cannot be deleted since "
                "it is currently active. Please set another workspace as "
                "active first."
            )
        self.zen_store.delete_workspace(workspace_name_or_id=workspace.id)

    @property
    def active_workspace(self) -> WorkspaceResponse:
        """Get the currently active workspace of the local client.

        If no active workspace is configured locally for the client, the
        active workspace in the global configuration is used instead.

        Returns:
            The active workspace.

        Raises:
            RuntimeError: If the active workspace is not set.
        """
        if ENV_ZENML_ACTIVE_WORKSPACE_ID in os.environ:
            workspace_id = os.environ[ENV_ZENML_ACTIVE_WORKSPACE_ID]
            return self.get_workspace(workspace_id)

        from zenml.constants import DEFAULT_WORKSPACE_NAME

        # If running in a ZenML server environment, the active workspace is
        # not relevant
        if ENV_ZENML_SERVER in os.environ:
            return self.get_workspace(DEFAULT_WORKSPACE_NAME)

        workspace = (
            self._config.active_workspace if self._config else None
        ) or GlobalConfiguration().get_active_workspace()
        if not workspace:
            raise RuntimeError(
                "No active workspace is configured. Run "
                "`zenml workspace set WORKSPACE_NAME` to set the active "
                "workspace."
            )

        if workspace.name != DEFAULT_WORKSPACE_NAME:
            logger.warning(
                f"You are running with a non-default workspace "
                f"'{workspace.name}'. Any stacks, components, "
                f"pipelines and pipeline runs produced in this "
                f"workspace will currently not be accessible through "
                f"the dashboard. However, this will be possible "
                f"in the near future."
            )
        return workspace

    # --------------------------------- Stacks ---------------------------------

    def create_stack(
        self,
        name: str,
        components: Mapping[StackComponentType, Union[str, UUID]],
        stack_spec_file: Optional[str] = None,
        labels: Optional[Dict[str, Any]] = None,
    ) -> StackResponse:
        """Registers a stack and its components.

        Args:
            name: The name of the stack to register.
            components: dictionary which maps component types to component names
            stack_spec_file: path to the stack spec file
            labels: The labels of the stack.

        Returns:
            The model of the registered stack.
        """
        stack_components = {}

        for c_type, c_identifier in components.items():
            # Skip non-existent components.
            if not c_identifier:
                continue

            # Get the component.
            component = self.get_stack_component(
                name_id_or_prefix=c_identifier,
                component_type=c_type,
            )
            stack_components[c_type] = [component.id]

        stack = StackRequest(
            name=name,
            components=stack_components,
            stack_spec_path=stack_spec_file,
            workspace=self.active_workspace.id,
            user=self.active_user.id,
            labels=labels,
        )

        self._validate_stack_configuration(stack=stack)

        return self.zen_store.create_stack(stack=stack)

    def get_stack(
        self,
        name_id_or_prefix: Optional[Union[UUID, str]] = None,
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> StackResponse:
        """Get a stack by name, ID or prefix.

        If no name, ID or prefix is provided, the active stack is returned.

        Args:
            name_id_or_prefix: The name, ID or prefix of the stack.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The stack.
        """
        if name_id_or_prefix is not None:
            return self._get_entity_by_id_or_name_or_prefix(
                get_method=self.zen_store.get_stack,
                list_method=self.list_stacks,
                name_id_or_prefix=name_id_or_prefix,
                allow_name_prefix_match=allow_name_prefix_match,
                hydrate=hydrate,
            )
        else:
            return self.active_stack_model

    def list_stacks(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        component_id: Optional[Union[str, UUID]] = None,
        user: Optional[Union[UUID, str]] = None,
        component: Optional[Union[UUID, str]] = None,
        hydrate: bool = False,
    ) -> Page[StackResponse]:
        """Lists all stacks.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of stacks to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            description: Use the stack description for filtering
            workspace_id: The id of the workspace to filter by.
            user_id: The  id of the user to filter by.
            component_id: The id of the component to filter by.
            user: The name/ID of the user to filter by.
            component: The name/ID of the component to filter by.
            name: The name of the stack to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of stacks.
        """
        stack_filter_model = StackFilter(
            page=page,
            size=size,
            sort_by=sort_by,
            logical_operator=logical_operator,
            workspace_id=workspace_id,
            user_id=user_id,
            component_id=component_id,
            user=user,
            component=component,
            name=name,
            description=description,
            id=id,
            created=created,
            updated=updated,
        )
        stack_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_stacks(stack_filter_model, hydrate=hydrate)

    def update_stack(
        self,
        name_id_or_prefix: Optional[Union[UUID, str]] = None,
        name: Optional[str] = None,
        stack_spec_file: Optional[str] = None,
        labels: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        component_updates: Optional[
            Dict[StackComponentType, List[Union[UUID, str]]]
        ] = None,
    ) -> StackResponse:
        """Updates a stack and its components.

        Args:
            name_id_or_prefix: The name, id or prefix of the stack to update.
            name: the new name of the stack.
            stack_spec_file: path to the stack spec file.
            labels: The new labels of the stack component.
            description: the new description of the stack.
            component_updates: dictionary which maps stack component types to
                lists of new stack component names or ids.

        Returns:
            The model of the updated stack.

        Raises:
            EntityExistsError: If the stack name is already taken.
        """
        # First, get the stack
        stack = self.get_stack(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )

        # Create the update model
        update_model = StackUpdate(
            workspace=self.active_workspace.id,
            user=self.active_user.id,
            stack_spec_path=stack_spec_file,
        )

        if name:
            if self.list_stacks(name=name):
                raise EntityExistsError(
                    "There are already existing stacks with the name "
                    f"'{name}'."
                )

            update_model.name = name

        if description:
            update_model.description = description

        # Get the current components
        if component_updates:
            components_dict = stack.components.copy()

            for component_type, component_id_list in component_updates.items():
                if component_id_list is not None:
                    components_dict[component_type] = [
                        self.get_stack_component(
                            name_id_or_prefix=component_id,
                            component_type=component_type,
                        )
                        for component_id in component_id_list
                    ]

            update_model.components = {
                c_type: [c.id for c in c_list]
                for c_type, c_list in components_dict.items()
            }

        if labels is not None:
            existing_labels = stack.labels or {}
            existing_labels.update(labels)

            existing_labels = {
                k: v for k, v in existing_labels.items() if v is not None
            }
            update_model.labels = existing_labels

        updated_stack = self.zen_store.update_stack(
            stack_id=stack.id,
            stack_update=update_model,
        )
        if updated_stack.id == self.active_stack_model.id:
            if self._config:
                self._config.set_active_stack(updated_stack)
            else:
                GlobalConfiguration().set_active_stack(updated_stack)
        return updated_stack

    def delete_stack(
        self, name_id_or_prefix: Union[str, UUID], recursive: bool = False
    ) -> None:
        """Deregisters a stack.

        Args:
            name_id_or_prefix: The name, id or prefix id of the stack
                to deregister.
            recursive: If `True`, all components of the stack which are not
                associated with any other stack will also be deleted.

        Raises:
            ValueError: If the stack is the currently active stack for this
                client.
        """
        stack = self.get_stack(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )

        if stack.id == self.active_stack_model.id:
            raise ValueError(
                f"Unable to deregister active stack '{stack.name}'. Make "
                f"sure to designate a new active stack before deleting this "
                f"one."
            )

        cfg = GlobalConfiguration()
        if stack.id == cfg.active_stack_id:
            raise ValueError(
                f"Unable to deregister '{stack.name}' as it is the active "
                f"stack within your global configuration. Make "
                f"sure to designate a new active stack before deleting this "
                f"one."
            )

        if recursive:
            stack_components_free_for_deletion = []

            # Get all stack components associated with this stack
            for component_type, component_model in stack.components.items():
                # Get stack associated with the stack component

                stacks = self.list_stacks(
                    component_id=component_model[0].id, size=2, page=1
                )

                # Check if the stack component is part of another stack
                if len(stacks) == 1 and stack.id == stacks[0].id:
                    stack_components_free_for_deletion.append(
                        (component_type, component_model)
                    )

            self.delete_stack(stack.id)

            for (
                stack_component_type,
                stack_component_model,
            ) in stack_components_free_for_deletion:
                self.delete_stack_component(
                    stack_component_model[0].name, stack_component_type
                )

            logger.info("Deregistered stack with name '%s'.", stack.name)
            return

        self.zen_store.delete_stack(stack_id=stack.id)
        logger.info("Deregistered stack with name '%s'.", stack.name)

    @property
    def active_stack(self) -> "Stack":
        """The active stack for this client.

        Returns:
            The active stack for this client.
        """
        from zenml.stack.stack import Stack

        return Stack.from_model(self.active_stack_model)

    @property
    def active_stack_model(self) -> StackResponse:
        """The model of the active stack for this client.

        If no active stack is configured locally for the client, the active
        stack in the global configuration is used instead.

        Returns:
            The model of the active stack for this client.

        Raises:
            RuntimeError: If the active stack is not set.
        """
        if ENV_ZENML_ACTIVE_STACK_ID in os.environ:
            return self.get_stack(os.environ[ENV_ZENML_ACTIVE_STACK_ID])

        stack_id: Optional[UUID] = None

        if self._config:
            if self._config._active_stack:
                return self._config._active_stack

            stack_id = self._config.active_stack_id

        if not stack_id:
            # Initialize the zen store so the global config loads the active
            # stack
            _ = GlobalConfiguration().zen_store
            if active_stack := GlobalConfiguration()._active_stack:
                return active_stack

            stack_id = GlobalConfiguration().get_active_stack_id()

        if not stack_id:
            raise RuntimeError(
                "No active stack is configured. Run "
                "`zenml stack set STACK_NAME` to set the active stack."
            )

        return self.get_stack(stack_id)

    def activate_stack(
        self, stack_name_id_or_prefix: Union[str, UUID]
    ) -> None:
        """Sets the stack as active.

        Args:
            stack_name_id_or_prefix: Model of the stack to activate.

        Raises:
            KeyError: If the stack is not registered.
        """
        # Make sure the stack is registered
        try:
            stack = self.get_stack(name_id_or_prefix=stack_name_id_or_prefix)
        except KeyError as e:
            raise KeyError(
                f"Stack '{stack_name_id_or_prefix}' cannot be activated since "
                f"it is not registered yet. Please register it first."
            ) from e

        if self._config:
            self._config.set_active_stack(stack=stack)

        else:
            # set the active stack globally only if the client doesn't use
            # a local configuration
            GlobalConfiguration().set_active_stack(stack=stack)

    def _validate_stack_configuration(self, stack: StackRequest) -> None:
        """Validates the configuration of a stack.

        Args:
            stack: The stack to validate.

        Raises:
            ValidationError: If the stack configuration is invalid.
        """
        local_components: List[str] = []
        remote_components: List[str] = []
        assert stack.components is not None
        for component_type, components in stack.components.items():
            for component in components:
                if isinstance(component, UUID):
                    component_response = self.get_stack_component(
                        name_id_or_prefix=component,
                        component_type=component_type,
                    )
                    component_config = component_response.configuration
                    component_flavor = component_response.flavor
                else:
                    component_config = component.configuration
                    component_flavor = component.flavor

                # Create and validate the configuration
                from zenml.stack.utils import (
                    validate_stack_component_config,
                    warn_if_config_server_mismatch,
                )

                configuration = validate_stack_component_config(
                    configuration_dict=component_config,
                    flavor_name=component_flavor,
                    component_type=component_type,
                    # Always enforce validation of custom flavors
                    validate_custom_flavors=True,
                )
                # Guaranteed to not be None by setting
                # `validate_custom_flavors=True` above
                assert configuration is not None
                warn_if_config_server_mismatch(configuration)
                if configuration.is_local:
                    local_components.append(
                        f"{component_type.value}: {component_flavor}"
                    )
                elif configuration.is_remote:
                    remote_components.append(
                        f"{component_type.value}: {component_flavor}"
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

    # ----------------------------- Services -----------------------------------

    def create_service(
        self,
        config: ServiceConfig,
        service_type: ServiceType,
        model_version_id: Optional[UUID] = None,
    ) -> ServiceResponse:
        """Registers a service.

        Args:
            config: The configuration of the service.
            service_type: The type of the service.
            model_version_id: The ID of the model version to associate with the
                service.

        Returns:
            The registered service.
        """
        service_request = ServiceRequest(
            name=config.service_name,
            service_type=service_type,
            config=config.model_dump(),
            workspace=self.active_workspace.id,
            user=self.active_user.id,
            model_version_id=model_version_id,
        )
        # Register the service
        return self.zen_store.create_service(service_request)

    def get_service(
        self,
        name_id_or_prefix: Union[str, UUID],
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
        type: Optional[str] = None,
    ) -> ServiceResponse:
        """Gets a service.

        Args:
            name_id_or_prefix: The name or ID of the service.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            type: The type of the service.

        Returns:
            The Service
        """

        def type_scoped_list_method(
            hydrate: bool = True,
            **kwargs: Any,
        ) -> Page[ServiceResponse]:
            """Call `zen_store.list_services` with type scoping.

            Args:
                hydrate: Flag deciding whether to hydrate the output model(s)
                    by including metadata fields in the response.
                **kwargs: Keyword arguments to pass to `ServiceFilterModel`.

            Returns:
                The type-scoped list of services.
            """
            service_filter_model = ServiceFilter(**kwargs)
            if type:
                service_filter_model.set_type(type=type)
            service_filter_model.set_scope_workspace(self.active_workspace.id)
            return self.zen_store.list_services(
                filter_model=service_filter_model,
                hydrate=hydrate,
            )

        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_service,
            list_method=type_scoped_list_method,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            hydrate=hydrate,
        )

    def list_services(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[datetime] = None,
        updated: Optional[datetime] = None,
        type: Optional[str] = None,
        flavor: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        hydrate: bool = False,
        running: Optional[bool] = None,
        service_name: Optional[str] = None,
        pipeline_name: Optional[str] = None,
        pipeline_run_id: Optional[str] = None,
        pipeline_step_name: Optional[str] = None,
        model_version_id: Optional[Union[str, UUID]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Page[ServiceResponse]:
        """List all services.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of services to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            type: Use the service type for filtering
            flavor: Use the service flavor for filtering
            workspace_id: The id of the workspace to filter by.
            user_id: The id of the user to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            running: Use the running status for filtering
            pipeline_name: Use the pipeline name for filtering
            service_name: Use the service name or model name
                for filtering
            pipeline_step_name: Use the pipeline step name for filtering
            model_version_id: Use the model version id for filtering
            config: Use the config for filtering
            pipeline_run_id: Use the pipeline run id for filtering

        Returns:
            The Service response page.
        """
        service_filter_model = ServiceFilter(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            created=created,
            updated=updated,
            type=type,
            flavor=flavor,
            workspace_id=workspace_id,
            user_id=user_id,
            running=running,
            name=service_name,
            pipeline_name=pipeline_name,
            pipeline_step_name=pipeline_step_name,
            model_version_id=model_version_id,
            pipeline_run_id=pipeline_run_id,
            config=dict_to_bytes(config) if config else None,
        )
        service_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_services(
            filter_model=service_filter_model, hydrate=hydrate
        )

    def update_service(
        self,
        id: UUID,
        name: Optional[str] = None,
        service_source: Optional[str] = None,
        admin_state: Optional[ServiceState] = None,
        status: Optional[Dict[str, Any]] = None,
        endpoint: Optional[Dict[str, Any]] = None,
        labels: Optional[Dict[str, str]] = None,
        prediction_url: Optional[str] = None,
        health_check_url: Optional[str] = None,
        model_version_id: Optional[UUID] = None,
    ) -> ServiceResponse:
        """Update a service.

        Args:
            id: The ID of the service to update.
            name: The new name of the service.
            admin_state: The new admin state of the service.
            status: The new status of the service.
            endpoint: The new endpoint of the service.
            service_source: The new service source of the service.
            labels: The new labels of the service.
            prediction_url: The new prediction url of the service.
            health_check_url: The new health check url of the service.
            model_version_id: The new model version id of the service.

        Returns:
            The updated service.
        """
        service_update = ServiceUpdate()
        if name:
            service_update.name = name
        if service_source:
            service_update.service_source = service_source
        if admin_state:
            service_update.admin_state = admin_state
        if status:
            service_update.status = status
        if endpoint:
            service_update.endpoint = endpoint
        if labels:
            service_update.labels = labels
        if prediction_url:
            service_update.prediction_url = prediction_url
        if health_check_url:
            service_update.health_check_url = health_check_url
        if model_version_id:
            service_update.model_version_id = model_version_id
        return self.zen_store.update_service(
            service_id=id, update=service_update
        )

    def delete_service(self, name_id_or_prefix: UUID) -> None:
        """Delete a service.

        Args:
            name_id_or_prefix: The name or ID of the service to delete.
        """
        service = self.get_service(
            name_id_or_prefix,
            allow_name_prefix_match=False,
        )
        self.zen_store.delete_service(service_id=service.id)

    # -------------------------------- Components ------------------------------

    def get_stack_component(
        self,
        component_type: StackComponentType,
        name_id_or_prefix: Optional[Union[str, UUID]] = None,
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> ComponentResponse:
        """Fetches a registered stack component.

        If the name_id_or_prefix is provided, it will try to fetch the component
        with the corresponding identifier. If not, it will try to fetch the
        active component of the given type.

        Args:
            component_type: The type of the component to fetch
            name_id_or_prefix: The id of the component to fetch.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The registered stack component.

        Raises:
            KeyError: If no name_id_or_prefix is provided and no such component
                is part of the active stack.
        """
        # If no `name_id_or_prefix` provided, try to get the active component.
        if not name_id_or_prefix:
            components = self.active_stack_model.components.get(
                component_type, None
            )
            if components:
                return components[0]
            raise KeyError(
                "No name_id_or_prefix provided and there is no active "
                f"{component_type} in the current active stack."
            )

        # Else, try to fetch the component with an explicit type filter
        def type_scoped_list_method(
            hydrate: bool = False,
            **kwargs: Any,
        ) -> Page[ComponentResponse]:
            """Call `zen_store.list_stack_components` with type scoping.

            Args:
                hydrate: Flag deciding whether to hydrate the output model(s)
                    by including metadata fields in the response.
                **kwargs: Keyword arguments to pass to `ComponentFilterModel`.

            Returns:
                The type-scoped list of components.
            """
            component_filter_model = ComponentFilter(**kwargs)
            component_filter_model.set_scope_type(
                component_type=component_type
            )
            component_filter_model.set_scope_workspace(
                self.active_workspace.id
            )
            return self.zen_store.list_stack_components(
                component_filter_model=component_filter_model,
                hydrate=hydrate,
            )

        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_stack_component,
            list_method=type_scoped_list_method,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            hydrate=hydrate,
        )

    def list_stack_components(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[datetime] = None,
        updated: Optional[datetime] = None,
        name: Optional[str] = None,
        flavor: Optional[str] = None,
        type: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        connector_id: Optional[Union[str, UUID]] = None,
        stack_id: Optional[Union[str, UUID]] = None,
        hydrate: bool = False,
    ) -> Page[ComponentResponse]:
        """Lists all registered stack components.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of component to filter by.
            created: Use to component by time of creation
            updated: Use the last updated date for filtering
            flavor: Use the component flavor for filtering
            type: Use the component type for filtering
            workspace_id: The id of the workspace to filter by.
            user_id: The id of the user to filter by.
            connector_id: The id of the connector to filter by.
            stack_id: The id of the stack to filter by.
            name: The name of the component to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of stack components.
        """
        component_filter_model = ComponentFilter(
            page=page,
            size=size,
            sort_by=sort_by,
            logical_operator=logical_operator,
            workspace_id=workspace_id or self.active_workspace.id,
            user_id=user_id,
            connector_id=connector_id,
            stack_id=stack_id,
            name=name,
            flavor=flavor,
            type=type,
            id=id,
            created=created,
            updated=updated,
        )
        component_filter_model.set_scope_workspace(self.active_workspace.id)

        return self.zen_store.list_stack_components(
            component_filter_model=component_filter_model, hydrate=hydrate
        )

    def create_stack_component(
        self,
        name: str,
        flavor: str,
        component_type: StackComponentType,
        configuration: Dict[str, str],
        component_spec_path: Optional[str] = None,
        labels: Optional[Dict[str, Any]] = None,
    ) -> "ComponentResponse":
        """Registers a stack component.

        Args:
            name: The name of the stack component.
            flavor: The flavor of the stack component.
            component_spec_path: The path to the stack spec file.
            component_type: The type of the stack component.
            configuration: The configuration of the stack component.
            labels: The labels of the stack component.

        Returns:
            The model of the registered component.
        """
        from zenml.stack.utils import (
            validate_stack_component_config,
            warn_if_config_server_mismatch,
        )

        validated_config = validate_stack_component_config(
            configuration_dict=configuration,
            flavor_name=flavor,
            component_type=component_type,
            # Always enforce validation of custom flavors
            validate_custom_flavors=True,
        )
        # Guaranteed to not be None by setting
        # `validate_custom_flavors=True` above
        assert validated_config is not None
        warn_if_config_server_mismatch(validated_config)

        create_component_model = ComponentRequest(
            name=name,
            type=component_type,
            flavor=flavor,
            component_spec_path=component_spec_path,
            configuration=configuration,
            user=self.active_user.id,
            workspace=self.active_workspace.id,
            labels=labels,
        )

        # Register the new model
        return self.zen_store.create_stack_component(
            component=create_component_model
        )

    def update_stack_component(
        self,
        name_id_or_prefix: Optional[Union[UUID, str]],
        component_type: StackComponentType,
        name: Optional[str] = None,
        component_spec_path: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
        labels: Optional[Dict[str, Any]] = None,
        disconnect: Optional[bool] = None,
        connector_id: Optional[UUID] = None,
        connector_resource_id: Optional[str] = None,
    ) -> ComponentResponse:
        """Updates a stack component.

        Args:
            name_id_or_prefix: The name, id or prefix of the stack component to
                update.
            component_type: The type of the stack component to update.
            name: The new name of the stack component.
            component_spec_path: The new path to the stack spec file.
            configuration: The new configuration of the stack component.
            labels: The new labels of the stack component.
            disconnect: Whether to disconnect the stack component from its
                service connector.
            connector_id: The new connector id of the stack component.
            connector_resource_id: The new connector resource id of the
                stack component.

        Returns:
            The updated stack component.

        Raises:
            EntityExistsError: If the new name is already taken.
        """
        # Get the existing component model
        component = self.get_stack_component(
            name_id_or_prefix=name_id_or_prefix,
            component_type=component_type,
            allow_name_prefix_match=False,
        )

        update_model = ComponentUpdate(
            workspace=self.active_workspace.id,
            user=self.active_user.id,
            component_spec_path=component_spec_path,
        )

        if name is not None:
            existing_components = self.list_stack_components(
                name=name,
                type=component_type,
            )
            if existing_components.total > 0:
                raise EntityExistsError(
                    f"There are already existing components with the "
                    f"name '{name}'."
                )
            update_model.name = name

        if configuration is not None:
            existing_configuration = component.configuration
            existing_configuration.update(configuration)
            existing_configuration = {
                k: v
                for k, v in existing_configuration.items()
                if v is not None
            }

            from zenml.stack.utils import (
                validate_stack_component_config,
                warn_if_config_server_mismatch,
            )

            validated_config = validate_stack_component_config(
                configuration_dict=existing_configuration,
                flavor_name=component.flavor,
                component_type=component.type,
                # Always enforce validation of custom flavors
                validate_custom_flavors=True,
            )
            # Guaranteed to not be None by setting
            # `validate_custom_flavors=True` above
            assert validated_config is not None
            warn_if_config_server_mismatch(validated_config)

            update_model.configuration = existing_configuration

        if labels is not None:
            existing_labels = component.labels or {}
            existing_labels.update(labels)

            existing_labels = {
                k: v for k, v in existing_labels.items() if v is not None
            }
            update_model.labels = existing_labels

        if disconnect:
            update_model.connector = None
            update_model.connector_resource_id = None
        else:
            existing_component = self.get_stack_component(
                name_id_or_prefix=name_id_or_prefix,
                component_type=component_type,
                allow_name_prefix_match=False,
            )
            update_model.connector = connector_id
            update_model.connector_resource_id = connector_resource_id
            if connector_id is None and existing_component.connector:
                update_model.connector = existing_component.connector.id
                update_model.connector_resource_id = (
                    existing_component.connector_resource_id
                )

        # Send the updated component to the ZenStore
        return self.zen_store.update_stack_component(
            component_id=component.id,
            component_update=update_model,
        )

    def delete_stack_component(
        self,
        name_id_or_prefix: Union[str, UUID],
        component_type: StackComponentType,
    ) -> None:
        """Deletes a registered stack component.

        Args:
            name_id_or_prefix: The model of the component to delete.
            component_type: The type of the component to delete.
        """
        component = self.get_stack_component(
            name_id_or_prefix=name_id_or_prefix,
            component_type=component_type,
            allow_name_prefix_match=False,
        )

        self.zen_store.delete_stack_component(component_id=component.id)
        logger.info(
            "Deregistered stack component (type: %s) with name '%s'.",
            component.type,
            component.name,
        )

    # --------------------------------- Flavors --------------------------------

    def create_flavor(
        self,
        source: str,
        component_type: StackComponentType,
    ) -> FlavorResponse:
        """Creates a new flavor.

        Args:
            source: The flavor to create.
            component_type: The type of the flavor.

        Returns:
            The created flavor (in model form).

        Raises:
            ValueError: in case the config_schema of the flavor is too large.
        """
        from zenml.stack.flavor import validate_flavor_source

        flavor = validate_flavor_source(
            source=source, component_type=component_type
        )()

        if len(flavor.config_schema) > TEXT_FIELD_MAX_LENGTH:
            raise ValueError(
                "Json representation of configuration schema"
                "exceeds max length. This could be caused by an"
                "overly long docstring on the flavors "
                "configuration class' docstring."
            )

        create_flavor_request = FlavorRequest(
            source=source,
            type=flavor.type,
            name=flavor.name,
            config_schema=flavor.config_schema,
            integration="custom",
            user=self.active_user.id,
            workspace=self.active_workspace.id,
        )

        return self.zen_store.create_flavor(flavor=create_flavor_request)

    def get_flavor(
        self,
        name_id_or_prefix: str,
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> FlavorResponse:
        """Get a stack component flavor.

        Args:
            name_id_or_prefix: The name, ID or prefix to the id of the flavor
                to get.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The stack component flavor.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_flavor,
            list_method=self.list_flavors,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            hydrate=hydrate,
        )

    def list_flavors(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[datetime] = None,
        updated: Optional[datetime] = None,
        name: Optional[str] = None,
        type: Optional[str] = None,
        integration: Optional[str] = None,
        user_id: Optional[Union[str, UUID]] = None,
        hydrate: bool = False,
    ) -> Page[FlavorResponse]:
        """Fetches all the flavor models.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of flavors to filter by.
            created: Use to flavors by time of creation
            updated: Use the last updated date for filtering
            user_id: The  id of the user to filter by.
            name: The name of the flavor to filter by.
            type: The type of the flavor to filter by.
            integration: The integration of the flavor to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all the flavor models.
        """
        flavor_filter_model = FlavorFilter(
            page=page,
            size=size,
            sort_by=sort_by,
            logical_operator=logical_operator,
            user_id=user_id,
            name=name,
            type=type,
            integration=integration,
            id=id,
            created=created,
            updated=updated,
        )
        flavor_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_flavors(
            flavor_filter_model=flavor_filter_model, hydrate=hydrate
        )

    def delete_flavor(self, name_id_or_prefix: str) -> None:
        """Deletes a flavor.

        Args:
            name_id_or_prefix: The name, id or prefix of the id for the
                flavor to delete.
        """
        flavor = self.get_flavor(
            name_id_or_prefix, allow_name_prefix_match=False
        )
        self.zen_store.delete_flavor(flavor_id=flavor.id)

        logger.info(f"Deleted flavor '{flavor.name}' of type '{flavor.type}'.")

    def get_flavors_by_type(
        self, component_type: "StackComponentType"
    ) -> Page[FlavorResponse]:
        """Fetches the list of flavor for a stack component type.

        Args:
            component_type: The type of the component to fetch.

        Returns:
            The list of flavors.
        """
        logger.debug(f"Fetching the flavors of type {component_type}.")

        return self.list_flavors(
            type=component_type,
        )

    def get_flavor_by_name_and_type(
        self, name: str, component_type: "StackComponentType"
    ) -> FlavorResponse:
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

        if not (
            flavors := self.list_flavors(
                type=component_type, name=name, hydrate=True
            ).items
        ):
            raise KeyError(
                f"No flavor with name '{name}' and type '{component_type}' "
                "exists."
            )
        if len(flavors) > 1:
            raise KeyError(
                f"More than one flavor with name {name} and type "
                f"{component_type} exists."
            )

        return flavors[0]

    # ------------------------------- Pipelines --------------------------------

    def list_pipelines(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        name: Optional[str] = None,
        latest_run_status: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        user: Optional[Union[UUID, str]] = None,
        tag: Optional[str] = None,
        hydrate: bool = False,
    ) -> Page[PipelineResponse]:
        """List all pipelines.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of pipeline to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            name: The name of the pipeline to filter by.
            latest_run_status: Filter by the status of the latest run of a
                pipeline.
            workspace_id: The id of the workspace to filter by.
            user_id: The id of the user to filter by.
            user: The name/ID of the user to filter by.
            tag: Tag to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page with Pipeline fitting the filter description
        """
        pipeline_filter_model = PipelineFilter(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            created=created,
            updated=updated,
            name=name,
            latest_run_status=latest_run_status,
            workspace_id=workspace_id,
            user_id=user_id,
            user=user,
            tag=tag,
        )
        pipeline_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_pipelines(
            pipeline_filter_model=pipeline_filter_model,
            hydrate=hydrate,
        )

    def get_pipeline(
        self,
        name_id_or_prefix: Union[str, UUID],
        hydrate: bool = True,
    ) -> PipelineResponse:
        """Get a pipeline by name, id or prefix.

        Args:
            name_id_or_prefix: The name, ID or ID prefix of the pipeline.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The pipeline.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_pipeline,
            list_method=self.list_pipelines,
            name_id_or_prefix=name_id_or_prefix,
            hydrate=hydrate,
        )

    def delete_pipeline(
        self,
        name_id_or_prefix: Union[str, UUID],
    ) -> None:
        """Delete a pipeline.

        Args:
            name_id_or_prefix: The name, ID or ID prefix of the pipeline.
        """
        pipeline = self.get_pipeline(name_id_or_prefix=name_id_or_prefix)
        self.zen_store.delete_pipeline(pipeline_id=pipeline.id)

    @_fail_for_sql_zen_store
    def trigger_pipeline(
        self,
        pipeline_name_or_id: Union[str, UUID, None] = None,
        run_configuration: Optional[PipelineRunConfiguration] = None,
        config_path: Optional[str] = None,
        template_id: Optional[UUID] = None,
        stack_name_or_id: Union[str, UUID, None] = None,
        synchronous: bool = False,
    ) -> PipelineRunResponse:
        """Trigger a pipeline from the server.

        Usage examples:
        * Run the latest runnable template for a pipeline:
        ```python
        Client().trigger_pipeline(pipeline_name_or_id=<NAME>)
        ```
        * Run the latest runnable template for a pipeline on a specific stack:
        ```python
        Client().trigger_pipeline(
            pipeline_name_or_id=<NAME>,
            stack_name_or_id=<STACK_NAME_OR_ID>
        )
        ```
        * Run a specific template:
        ```python
        Client().trigger_pipeline(template_id=<ID>)
        ```

        Args:
            pipeline_name_or_id: Name or ID of the pipeline. If this is
                specified, the latest runnable template for this pipeline will
                be used for the run (Runnable here means that the build
                associated with the template is for a remote stack without any
                custom flavor stack components). If not given, a template ID
                that should be run needs to be specified.
            run_configuration: Configuration for the run. Either this or a
                path to a config file can be specified.
            config_path: Path to a YAML configuration file. This file will be
                parsed as a `PipelineRunConfiguration` object. Either this or
                the configuration in code can be specified.
            template_id: ID of the template to run. Either this or a pipeline
                can be specified.
            stack_name_or_id: Name or ID of the stack on which to run the
                pipeline. If not specified, this method will try to find a
                runnable template on any stack.
            synchronous: If `True`, this method will wait until the triggered
                run is finished.

        Raises:
            RuntimeError: If triggering the pipeline failed.

        Returns:
            Model of the pipeline run.
        """
        from zenml.pipelines.run_utils import (
            validate_run_config_is_runnable_from_server,
            validate_stack_is_runnable_from_server,
            wait_for_pipeline_run_to_finish,
        )

        if Counter([template_id, pipeline_name_or_id])[None] != 1:
            raise RuntimeError(
                "You need to specify exactly one of pipeline or template "
                "to trigger."
            )

        if run_configuration and config_path:
            raise RuntimeError(
                "Only config path or runtime configuration can be specified."
            )

        if config_path:
            run_configuration = PipelineRunConfiguration.from_yaml(config_path)

        if run_configuration:
            validate_run_config_is_runnable_from_server(run_configuration)

        if template_id:
            if stack_name_or_id:
                logger.warning(
                    "Template ID and stack specified, ignoring the stack and "
                    "using stack associated with the template instead."
                )

            run = self.zen_store.run_template(
                template_id=template_id,
                run_configuration=run_configuration,
            )
        else:
            assert pipeline_name_or_id
            pipeline = self.get_pipeline(name_id_or_prefix=pipeline_name_or_id)

            stack = None
            if stack_name_or_id:
                stack = self.get_stack(
                    stack_name_or_id, allow_name_prefix_match=False
                )
                validate_stack_is_runnable_from_server(
                    zen_store=self.zen_store, stack=stack
                )

            templates = depaginate(
                self.list_run_templates,
                pipeline_id=pipeline.id,
                stack_id=stack.id if stack else None,
            )

            for template in templates:
                if not template.build:
                    continue

                stack = template.build.stack
                if not stack:
                    continue

                try:
                    validate_stack_is_runnable_from_server(
                        zen_store=self.zen_store, stack=stack
                    )
                except ValueError:
                    continue

                run = self.zen_store.run_template(
                    template_id=template.id,
                    run_configuration=run_configuration,
                )
                break
            else:
                raise RuntimeError(
                    "Unable to find a runnable template for the given stack "
                    "and pipeline."
                )

        if synchronous:
            run = wait_for_pipeline_run_to_finish(run_id=run.id)

        return run

    # -------------------------------- Builds ----------------------------------

    def get_build(
        self,
        id_or_prefix: Union[str, UUID],
        hydrate: bool = True,
    ) -> PipelineBuildResponse:
        """Get a build by id or prefix.

        Args:
            id_or_prefix: The id or id prefix of the build.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The build.

        Raises:
            KeyError: If no build was found for the given id or prefix.
            ZenKeyError: If multiple builds were found that match the given
                id or prefix.
        """
        from zenml.utils.uuid_utils import is_valid_uuid

        # First interpret as full UUID
        if is_valid_uuid(id_or_prefix):
            if not isinstance(id_or_prefix, UUID):
                id_or_prefix = UUID(id_or_prefix, version=4)

            return self.zen_store.get_build(
                id_or_prefix,
                hydrate=hydrate,
            )

        entity = self.list_builds(
            id=f"startswith:{id_or_prefix}", hydrate=hydrate
        )

        # If only a single entity is found, return it.
        if entity.total == 1:
            return entity.items[0]

        # If no entity is found, raise an error.
        if entity.total == 0:
            raise KeyError(
                f"No builds have been found that have either an id or prefix "
                f"that matches the provided string '{id_or_prefix}'."
            )

        raise ZenKeyError(
            f"{entity.total} builds have been found that have "
            f"an ID that matches the provided "
            f"string '{id_or_prefix}':\n"
            f"{[entity.items]}.\n"
            f"Please use the id to uniquely identify "
            f"only one of the builds."
        )

    def list_builds(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        pipeline_id: Optional[Union[str, UUID]] = None,
        stack_id: Optional[Union[str, UUID]] = None,
        is_local: Optional[bool] = None,
        contains_code: Optional[bool] = None,
        zenml_version: Optional[str] = None,
        python_version: Optional[str] = None,
        checksum: Optional[str] = None,
        hydrate: bool = False,
    ) -> Page[PipelineBuildResponse]:
        """List all builds.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of build to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            workspace_id: The id of the workspace to filter by.
            user_id: The  id of the user to filter by.
            pipeline_id: The id of the pipeline to filter by.
            stack_id: The id of the stack to filter by.
            is_local: Use to filter local builds.
            contains_code: Use to filter builds that contain code.
            zenml_version: The version of ZenML to filter by.
            python_version: The Python version to filter by.
            checksum: The build checksum to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page with builds fitting the filter description
        """
        build_filter_model = PipelineBuildFilter(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            created=created,
            updated=updated,
            workspace_id=workspace_id,
            user_id=user_id,
            pipeline_id=pipeline_id,
            stack_id=stack_id,
            is_local=is_local,
            contains_code=contains_code,
            zenml_version=zenml_version,
            python_version=python_version,
            checksum=checksum,
        )
        build_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_builds(
            build_filter_model=build_filter_model,
            hydrate=hydrate,
        )

    def delete_build(self, id_or_prefix: str) -> None:
        """Delete a build.

        Args:
            id_or_prefix: The id or id prefix of the build.
        """
        build = self.get_build(id_or_prefix=id_or_prefix)
        self.zen_store.delete_build(build_id=build.id)

    # --------------------------------- Event Sources -------------------------

    @_fail_for_sql_zen_store
    def create_event_source(
        self,
        name: str,
        configuration: Dict[str, Any],
        flavor: str,
        event_source_subtype: PluginSubType,
        description: str = "",
    ) -> EventSourceResponse:
        """Registers an event source.

        Args:
            name: The name of the event source to create.
            configuration: Configuration for this event source.
            flavor: The flavor of event source.
            event_source_subtype: The event source subtype.
            description: The description of the event source.

        Returns:
            The model of the registered event source.
        """
        event_source = EventSourceRequest(
            name=name,
            configuration=configuration,
            description=description,
            flavor=flavor,
            plugin_type=PluginType.EVENT_SOURCE,
            plugin_subtype=event_source_subtype,
            user=self.active_user.id,
            workspace=self.active_workspace.id,
        )

        return self.zen_store.create_event_source(event_source=event_source)

    @_fail_for_sql_zen_store
    def get_event_source(
        self,
        name_id_or_prefix: Union[UUID, str],
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> EventSourceResponse:
        """Get a event source by name, ID or prefix.

        Args:
            name_id_or_prefix: The name, ID or prefix of the stack.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The event_source.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_event_source,
            list_method=self.list_event_sources,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            hydrate=hydrate,
        )

    def list_event_sources(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[datetime] = None,
        updated: Optional[datetime] = None,
        name: Optional[str] = None,
        flavor: Optional[str] = None,
        event_source_type: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        hydrate: bool = False,
    ) -> Page[EventSourceResponse]:
        """Lists all event_sources.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of event_sources to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            workspace_id: The id of the workspace to filter by.
            user_id: The  id of the user to filter by.
            name: The name of the event_source to filter by.
            flavor: The flavor of the event_source to filter by.
            event_source_type: The subtype of the event_source to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of event_sources.
        """
        event_source_filter_model = EventSourceFilter(
            page=page,
            size=size,
            sort_by=sort_by,
            logical_operator=logical_operator,
            workspace_id=workspace_id,
            user_id=user_id,
            name=name,
            flavor=flavor,
            plugin_subtype=event_source_type,
            id=id,
            created=created,
            updated=updated,
        )
        event_source_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_event_sources(
            event_source_filter_model, hydrate=hydrate
        )

    @_fail_for_sql_zen_store
    def update_event_source(
        self,
        name_id_or_prefix: Union[UUID, str],
        name: Optional[str] = None,
        description: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
        rotate_secret: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> EventSourceResponse:
        """Updates a event_source.

        Args:
            name_id_or_prefix: The name, id or prefix of the event_source to update.
            name: the new name of the event_source.
            description: the new description of the event_source.
            configuration: The event source configuration.
            rotate_secret: Allows rotating of secret, if true, the response will
                contain the new secret value
            is_active: Optional[bool] = Allows for activation/deactivating the
                event source

        Returns:
            The model of the updated event_source.

        Raises:
            EntityExistsError: If the event_source name is already taken.
        """
        # First, get the eve
        event_source = self.get_event_source(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )

        # Create the update model
        update_model = EventSourceUpdate(
            name=name,
            description=description,
            configuration=configuration,
            rotate_secret=rotate_secret,
            is_active=is_active,
        )

        if name:
            if self.list_event_sources(name=name):
                raise EntityExistsError(
                    "There are already existing event_sources with the name "
                    f"'{name}'."
                )

        updated_event_source = self.zen_store.update_event_source(
            event_source_id=event_source.id,
            event_source_update=update_model,
        )
        return updated_event_source

    @_fail_for_sql_zen_store
    def delete_event_source(self, name_id_or_prefix: Union[str, UUID]) -> None:
        """Deletes an event_source.

        Args:
            name_id_or_prefix: The name, id or prefix id of the event_source
                to deregister.
        """
        event_source = self.get_event_source(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )

        self.zen_store.delete_event_source(event_source_id=event_source.id)
        logger.info("Deleted event_source with name '%s'.", event_source.name)

    # --------------------------------- Actions -------------------------

    @_fail_for_sql_zen_store
    def create_action(
        self,
        name: str,
        flavor: str,
        action_type: PluginSubType,
        configuration: Dict[str, Any],
        service_account_id: UUID,
        auth_window: Optional[int] = None,
        description: str = "",
    ) -> ActionResponse:
        """Create an action.

        Args:
            name: The name of the action.
            flavor: The flavor of the action,
            action_type: The action subtype.
            configuration: The action configuration.
            service_account_id: The service account that is used to execute the
                action.
            auth_window: The time window in minutes for which the service
                account is authorized to execute the action. Set this to 0 to
                authorize the service account indefinitely (not recommended).
            description: The description of the action.

        Returns:
            The created action
        """
        action = ActionRequest(
            name=name,
            description=description,
            flavor=flavor,
            plugin_subtype=action_type,
            configuration=configuration,
            service_account_id=service_account_id,
            auth_window=auth_window,
            user=self.active_user.id,
            workspace=self.active_workspace.id,
        )

        return self.zen_store.create_action(action=action)

    @_fail_for_sql_zen_store
    def get_action(
        self,
        name_id_or_prefix: Union[UUID, str],
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> ActionResponse:
        """Get an action by name, ID or prefix.

        Args:
            name_id_or_prefix: The name, ID or prefix of the action.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The action.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_action,
            list_method=self.list_actions,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            hydrate=hydrate,
        )

    @_fail_for_sql_zen_store
    def list_actions(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[datetime] = None,
        updated: Optional[datetime] = None,
        name: Optional[str] = None,
        flavor: Optional[str] = None,
        action_type: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        hydrate: bool = False,
    ) -> Page[ActionResponse]:
        """List actions.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of the action to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            workspace_id: The id of the workspace to filter by.
            user_id: The id of the user to filter by.
            name: The name of the action to filter by.
            flavor: The flavor of the action to filter by.
            action_type: The type of the action to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of actions.
        """
        filter_model = ActionFilter(
            page=page,
            size=size,
            sort_by=sort_by,
            logical_operator=logical_operator,
            workspace_id=workspace_id,
            user_id=user_id,
            name=name,
            id=id,
            flavor=flavor,
            plugin_subtype=action_type,
            created=created,
            updated=updated,
        )
        filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_actions(filter_model, hydrate=hydrate)

    @_fail_for_sql_zen_store
    def update_action(
        self,
        name_id_or_prefix: Union[UUID, str],
        name: Optional[str] = None,
        description: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
        service_account_id: Optional[UUID] = None,
        auth_window: Optional[int] = None,
    ) -> ActionResponse:
        """Update an action.

        Args:
            name_id_or_prefix: The name, id or prefix of the action to update.
            name: The new name of the action.
            description: The new description of the action.
            configuration: The new configuration of the action.
            service_account_id: The new service account that is used to execute
                the action.
            auth_window: The new time window in minutes for which the service
                account is authorized to execute the action. Set this to 0 to
                authorize the service account indefinitely (not recommended).

        Returns:
            The updated action.
        """
        action = self.get_action(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )

        update_model = ActionUpdate(
            name=name,
            description=description,
            configuration=configuration,
            service_account_id=service_account_id,
            auth_window=auth_window,
        )

        return self.zen_store.update_action(
            action_id=action.id,
            action_update=update_model,
        )

    @_fail_for_sql_zen_store
    def delete_action(self, name_id_or_prefix: Union[str, UUID]) -> None:
        """Delete an action.

        Args:
            name_id_or_prefix: The name, id or prefix id of the action
                to delete.
        """
        action = self.get_action(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )

        self.zen_store.delete_action(action_id=action.id)
        logger.info("Deleted action with name '%s'.", action.name)

    # --------------------------------- Triggers -------------------------

    @_fail_for_sql_zen_store
    def create_trigger(
        self,
        name: str,
        event_source_id: UUID,
        event_filter: Dict[str, Any],
        action_id: UUID,
        description: str = "",
    ) -> TriggerResponse:
        """Registers a trigger.

        Args:
            name: The name of the trigger to create.
            event_source_id: The id of the event source id
            event_filter: The event filter
            action_id: The ID of the action that should be triggered.
            description: The description of the trigger

        Returns:
            The created trigger.
        """
        trigger = TriggerRequest(
            name=name,
            description=description,
            event_source_id=event_source_id,
            event_filter=event_filter,
            action_id=action_id,
            user=self.active_user.id,
            workspace=self.active_workspace.id,
        )

        return self.zen_store.create_trigger(trigger=trigger)

    @_fail_for_sql_zen_store
    def get_trigger(
        self,
        name_id_or_prefix: Union[UUID, str],
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> TriggerResponse:
        """Get a trigger by name, ID or prefix.

        Args:
            name_id_or_prefix: The name, ID or prefix of the trigger.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The trigger.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_trigger,
            list_method=self.list_triggers,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            hydrate=hydrate,
        )

    @_fail_for_sql_zen_store
    def list_triggers(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[datetime] = None,
        updated: Optional[datetime] = None,
        name: Optional[str] = None,
        event_source_id: Optional[UUID] = None,
        action_id: Optional[UUID] = None,
        event_source_flavor: Optional[str] = None,
        event_source_subtype: Optional[str] = None,
        action_flavor: Optional[str] = None,
        action_subtype: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        hydrate: bool = False,
    ) -> Page[TriggerResponse]:
        """Lists all triggers.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of triggers to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            workspace_id: The id of the workspace to filter by.
            user_id: The  id of the user to filter by.
            name: The name of the trigger to filter by.
            event_source_id: The event source associated with the trigger.
            action_id: The action associated with the trigger.
            event_source_flavor: Flavor of the event source associated with the
                trigger.
            event_source_subtype: Type of the event source associated with the
                trigger.
            action_flavor: Flavor of the action associated with the trigger.
            action_subtype: Type of the action associated with the trigger.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of triggers.
        """
        trigger_filter_model = TriggerFilter(
            page=page,
            size=size,
            sort_by=sort_by,
            logical_operator=logical_operator,
            workspace_id=workspace_id,
            user_id=user_id,
            name=name,
            event_source_id=event_source_id,
            action_id=action_id,
            event_source_flavor=event_source_flavor,
            event_source_subtype=event_source_subtype,
            action_flavor=action_flavor,
            action_subtype=action_subtype,
            id=id,
            created=created,
            updated=updated,
        )
        trigger_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_triggers(
            trigger_filter_model, hydrate=hydrate
        )

    @_fail_for_sql_zen_store
    def update_trigger(
        self,
        name_id_or_prefix: Union[UUID, str],
        name: Optional[str] = None,
        description: Optional[str] = None,
        event_filter: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None,
    ) -> TriggerResponse:
        """Updates a trigger.

        Args:
            name_id_or_prefix: The name, id or prefix of the trigger to update.
            name: the new name of the trigger.
            description: the new description of the trigger.
            event_filter: The event filter configuration.
            is_active: Whether the trigger is active or not.

        Returns:
            The model of the updated trigger.

        Raises:
            EntityExistsError: If the trigger name is already taken.
        """
        # First, get the eve
        trigger = self.get_trigger(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )

        # Create the update model
        update_model = TriggerUpdate(
            name=name,
            description=description,
            event_filter=event_filter,
            is_active=is_active,
        )

        if name:
            if self.list_triggers(name=name):
                raise EntityExistsError(
                    "There are already is an existing trigger with the name "
                    f"'{name}'."
                )

        updated_trigger = self.zen_store.update_trigger(
            trigger_id=trigger.id,
            trigger_update=update_model,
        )
        return updated_trigger

    @_fail_for_sql_zen_store
    def delete_trigger(self, name_id_or_prefix: Union[str, UUID]) -> None:
        """Deletes an trigger.

        Args:
            name_id_or_prefix: The name, id or prefix id of the trigger
                to deregister.
        """
        trigger = self.get_trigger(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )

        self.zen_store.delete_trigger(trigger_id=trigger.id)
        logger.info("Deleted trigger with name '%s'.", trigger.name)

    # ------------------------------ Deployments -------------------------------

    def get_deployment(
        self,
        id_or_prefix: Union[str, UUID],
        hydrate: bool = True,
    ) -> PipelineDeploymentResponse:
        """Get a deployment by id or prefix.

        Args:
            id_or_prefix: The id or id prefix of the deployment.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The deployment.

        Raises:
            KeyError: If no deployment was found for the given id or prefix.
            ZenKeyError: If multiple deployments were found that match the given
                id or prefix.
        """
        from zenml.utils.uuid_utils import is_valid_uuid

        # First interpret as full UUID
        if is_valid_uuid(id_or_prefix):
            id_ = (
                UUID(id_or_prefix)
                if isinstance(id_or_prefix, str)
                else id_or_prefix
            )
            return self.zen_store.get_deployment(id_, hydrate=hydrate)

        entity = self.list_deployments(
            id=f"startswith:{id_or_prefix}",
            hydrate=hydrate,
        )

        # If only a single entity is found, return it.
        if entity.total == 1:
            return entity.items[0]

        # If no entity is found, raise an error.
        if entity.total == 0:
            raise KeyError(
                f"No deployment have been found that have either an id or "
                f"prefix that matches the provided string '{id_or_prefix}'."
            )

        raise ZenKeyError(
            f"{entity.total} deployments have been found that have "
            f"an ID that matches the provided "
            f"string '{id_or_prefix}':\n"
            f"{[entity.items]}.\n"
            f"Please use the id to uniquely identify "
            f"only one of the deployments."
        )

    def list_deployments(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        pipeline_id: Optional[Union[str, UUID]] = None,
        stack_id: Optional[Union[str, UUID]] = None,
        build_id: Optional[Union[str, UUID]] = None,
        template_id: Optional[Union[str, UUID]] = None,
        hydrate: bool = False,
    ) -> Page[PipelineDeploymentResponse]:
        """List all deployments.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of build to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            workspace_id: The id of the workspace to filter by.
            user_id: The  id of the user to filter by.
            pipeline_id: The id of the pipeline to filter by.
            stack_id: The id of the stack to filter by.
            build_id: The id of the build to filter by.
            template_id: The ID of the template to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page with deployments fitting the filter description
        """
        deployment_filter_model = PipelineDeploymentFilter(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            created=created,
            updated=updated,
            workspace_id=workspace_id,
            user_id=user_id,
            pipeline_id=pipeline_id,
            stack_id=stack_id,
            build_id=build_id,
            template_id=template_id,
        )
        deployment_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_deployments(
            deployment_filter_model=deployment_filter_model,
            hydrate=hydrate,
        )

    def delete_deployment(self, id_or_prefix: str) -> None:
        """Delete a deployment.

        Args:
            id_or_prefix: The id or id prefix of the deployment.
        """
        deployment = self.get_deployment(id_or_prefix=id_or_prefix)
        self.zen_store.delete_deployment(deployment_id=deployment.id)

    # ------------------------------ Run templates -----------------------------

    def create_run_template(
        self,
        name: str,
        deployment_id: UUID,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> RunTemplateResponse:
        """Create a run template.

        Args:
            name: The name of the run template.
            deployment_id: ID of the deployment which this template should be
                based off of.
            description: The description of the run template.
            tags: Tags associated with the run template.

        Returns:
            The created run template.
        """
        return self.zen_store.create_run_template(
            template=RunTemplateRequest(
                name=name,
                description=description,
                source_deployment_id=deployment_id,
                tags=tags,
                user=self.active_user.id,
                workspace=self.active_workspace.id,
            )
        )

    def get_run_template(
        self,
        name_id_or_prefix: Union[str, UUID],
        hydrate: bool = True,
    ) -> RunTemplateResponse:
        """Get a run template.

        Args:
            name_id_or_prefix: Name/ID/ID prefix of the template to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The run template.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_run_template,
            list_method=self.list_run_templates,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
            hydrate=hydrate,
        )

    def list_run_templates(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        name: Optional[str] = None,
        tag: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        pipeline_id: Optional[Union[str, UUID]] = None,
        build_id: Optional[Union[str, UUID]] = None,
        stack_id: Optional[Union[str, UUID]] = None,
        code_repository_id: Optional[Union[str, UUID]] = None,
        user: Optional[Union[UUID, str]] = None,
        pipeline: Optional[Union[UUID, str]] = None,
        stack: Optional[Union[UUID, str]] = None,
        hydrate: bool = False,
    ) -> Page[RunTemplateResponse]:
        """Get a page of run templates.

        Args:
            sort_by: The column to sort by.
            page: The page of items.
            size: The maximum size of all pages.
            logical_operator: Which logical operator to use [and, or].
            created: Filter by the creation date.
            updated: Filter by the last updated date.
            name: Filter by run template name.
            tag: Filter by run template tags.
            workspace_id: Filter by workspace ID.
            user_id: Filter by user ID.
            pipeline_id: Filter by pipeline ID.
            build_id: Filter by build ID.
            stack_id: Filter by stack ID.
            code_repository_id: Filter by code repository ID.
            user: Filter by user name/ID.
            pipeline: Filter by pipeline name/ID.
            stack: Filter by stack name/ID.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of run templates.
        """
        filter = RunTemplateFilter(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            created=created,
            updated=updated,
            name=name,
            tag=tag,
            workspace_id=workspace_id,
            user_id=user_id,
            pipeline_id=pipeline_id,
            build_id=build_id,
            stack_id=stack_id,
            code_repository_id=code_repository_id,
            user=user,
            pipeline=pipeline,
            stack=stack,
        )

        return self.zen_store.list_run_templates(
            template_filter_model=filter, hydrate=hydrate
        )

    def update_run_template(
        self,
        name_id_or_prefix: Union[str, UUID],
        name: Optional[str] = None,
        description: Optional[str] = None,
        add_tags: Optional[List[str]] = None,
        remove_tags: Optional[List[str]] = None,
    ) -> RunTemplateResponse:
        """Update a run template.

        Args:
            name_id_or_prefix: Name/ID/ID prefix of the template to update.
            name: The new name of the run template.
            description: The new description of the run template.
            add_tags: Tags to add to the run template.
            remove_tags: Tags to remove from the run template.

        Returns:
            The updated run template.
        """
        if is_valid_uuid(name_id_or_prefix):
            template_id = (
                UUID(name_id_or_prefix)
                if isinstance(name_id_or_prefix, str)
                else name_id_or_prefix
            )
        else:
            template_id = self.get_run_template(
                name_id_or_prefix, hydrate=False
            ).id

        return self.zen_store.update_run_template(
            template_id=template_id,
            template_update=RunTemplateUpdate(
                name=name,
                description=description,
                add_tags=add_tags,
                remove_tags=remove_tags,
            ),
        )

    def delete_run_template(self, name_id_or_prefix: Union[str, UUID]) -> None:
        """Delete a run template.

        Args:
            name_id_or_prefix: Name/ID/ID prefix of the template to delete.
        """
        if is_valid_uuid(name_id_or_prefix):
            template_id = (
                UUID(name_id_or_prefix)
                if isinstance(name_id_or_prefix, str)
                else name_id_or_prefix
            )
        else:
            template_id = self.get_run_template(
                name_id_or_prefix, hydrate=False
            ).id

        self.zen_store.delete_run_template(template_id=template_id)

    # ------------------------------- Schedules --------------------------------

    def get_schedule(
        self,
        name_id_or_prefix: Union[str, UUID],
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> ScheduleResponse:
        """Get a schedule by name, id or prefix.

        Args:
            name_id_or_prefix: The name, id or prefix of the schedule.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The schedule.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_schedule,
            list_method=self.list_schedules,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            hydrate=hydrate,
        )

    def list_schedules(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        name: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        pipeline_id: Optional[Union[str, UUID]] = None,
        orchestrator_id: Optional[Union[str, UUID]] = None,
        active: Optional[Union[str, bool]] = None,
        cron_expression: Optional[str] = None,
        start_time: Optional[Union[datetime, str]] = None,
        end_time: Optional[Union[datetime, str]] = None,
        interval_second: Optional[int] = None,
        catchup: Optional[Union[str, bool]] = None,
        hydrate: bool = False,
        run_once_start_time: Optional[Union[datetime, str]] = None,
    ) -> Page[ScheduleResponse]:
        """List schedules.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of stacks to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            name: The name of the stack to filter by.
            workspace_id: The id of the workspace to filter by.
            user_id: The  id of the user to filter by.
            pipeline_id: The id of the pipeline to filter by.
            orchestrator_id: The id of the orchestrator to filter by.
            active: Use to filter by active status.
            cron_expression: Use to filter by cron expression.
            start_time: Use to filter by start time.
            end_time: Use to filter by end time.
            interval_second: Use to filter by interval second.
            catchup: Use to filter by catchup.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            run_once_start_time: Use to filter by run once start time.

        Returns:
            A list of schedules.
        """
        schedule_filter_model = ScheduleFilter(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            created=created,
            updated=updated,
            name=name,
            workspace_id=workspace_id,
            user_id=user_id,
            pipeline_id=pipeline_id,
            orchestrator_id=orchestrator_id,
            active=active,
            cron_expression=cron_expression,
            start_time=start_time,
            end_time=end_time,
            interval_second=interval_second,
            catchup=catchup,
            run_once_start_time=run_once_start_time,
        )
        schedule_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_schedules(
            schedule_filter_model=schedule_filter_model,
            hydrate=hydrate,
        )

    def delete_schedule(self, name_id_or_prefix: Union[str, UUID]) -> None:
        """Delete a schedule.

        Args:
            name_id_or_prefix: The name, id or prefix id of the schedule
                to delete.
        """
        schedule = self.get_schedule(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )
        logger.warning(
            f"Deleting schedule '{name_id_or_prefix}'... This will only delete "
            "the reference of the schedule from ZenML. Please make sure to "
            "manually stop/delete this schedule in your orchestrator as well!"
        )
        self.zen_store.delete_schedule(schedule_id=schedule.id)

    # ----------------------------- Pipeline runs ------------------------------

    def get_pipeline_run(
        self,
        name_id_or_prefix: Union[str, UUID],
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> PipelineRunResponse:
        """Gets a pipeline run by name, ID, or prefix.

        Args:
            name_id_or_prefix: Name, ID, or prefix of the pipeline run.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The pipeline run.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_run,
            list_method=self.list_pipeline_runs,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            hydrate=hydrate,
        )

    def list_pipeline_runs(
        self,
        sort_by: str = "desc:created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        name: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        pipeline_id: Optional[Union[str, UUID]] = None,
        pipeline_name: Optional[str] = None,
        user_id: Optional[Union[str, UUID]] = None,
        stack_id: Optional[Union[str, UUID]] = None,
        schedule_id: Optional[Union[str, UUID]] = None,
        build_id: Optional[Union[str, UUID]] = None,
        deployment_id: Optional[Union[str, UUID]] = None,
        code_repository_id: Optional[Union[str, UUID]] = None,
        template_id: Optional[Union[str, UUID]] = None,
        model_version_id: Optional[Union[str, UUID]] = None,
        orchestrator_run_id: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[Union[datetime, str]] = None,
        end_time: Optional[Union[datetime, str]] = None,
        num_steps: Optional[Union[int, str]] = None,
        unlisted: Optional[bool] = None,
        templatable: Optional[bool] = None,
        tag: Optional[str] = None,
        user: Optional[Union[UUID, str]] = None,
        pipeline: Optional[Union[UUID, str]] = None,
        code_repository: Optional[Union[UUID, str]] = None,
        model: Optional[Union[UUID, str]] = None,
        stack: Optional[Union[UUID, str]] = None,
        hydrate: bool = False,
    ) -> Page[PipelineRunResponse]:
        """List all pipeline runs.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: The id of the runs to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            workspace_id: The id of the workspace to filter by.
            pipeline_id: The id of the pipeline to filter by.
            pipeline_name: DEPRECATED. Use `pipeline` instead to filter by
                pipeline name.
            user_id: The id of the user to filter by.
            stack_id: The id of the stack to filter by.
            schedule_id: The id of the schedule to filter by.
            build_id: The id of the build to filter by.
            deployment_id: The id of the deployment to filter by.
            code_repository_id: The id of the code repository to filter by.
            template_id: The ID of the template to filter by.
            model_version_id: The ID of the model version to filter by.
            orchestrator_run_id: The run id of the orchestrator to filter by.
            name: The name of the run to filter by.
            status: The status of the pipeline run
            start_time: The start_time for the pipeline run
            end_time: The end_time for the pipeline run
            num_steps: The number of steps for the pipeline run
            unlisted: If the runs should be unlisted or not.
            templatable: If the runs should be templatable or not.
            tag: Tag to filter by.
            user: The name/ID of the user to filter by.
            pipeline: The name/ID of the pipeline to filter by.
            code_repository: Filter by code repository name/ID.
            model: Filter by model name/ID.
            stack: Filter by stack name/ID.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page with Pipeline Runs fitting the filter description
        """
        runs_filter_model = PipelineRunFilter(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            created=created,
            updated=updated,
            name=name,
            workspace_id=workspace_id,
            pipeline_id=pipeline_id,
            pipeline_name=pipeline_name,
            schedule_id=schedule_id,
            build_id=build_id,
            deployment_id=deployment_id,
            code_repository_id=code_repository_id,
            template_id=template_id,
            model_version_id=model_version_id,
            orchestrator_run_id=orchestrator_run_id,
            user_id=user_id,
            stack_id=stack_id,
            status=status,
            start_time=start_time,
            end_time=end_time,
            num_steps=num_steps,
            tag=tag,
            unlisted=unlisted,
            user=user,
            pipeline=pipeline,
            code_repository=code_repository,
            stack=stack,
            model=model,
            templatable=templatable,
        )
        runs_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_runs(
            runs_filter_model=runs_filter_model,
            hydrate=hydrate,
        )

    def delete_pipeline_run(
        self,
        name_id_or_prefix: Union[str, UUID],
    ) -> None:
        """Deletes a pipeline run.

        Args:
            name_id_or_prefix: Name, ID, or prefix of the pipeline run.
        """
        run = self.get_pipeline_run(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )
        self.zen_store.delete_run(run_id=run.id)

    # -------------------------------- Step run --------------------------------

    def get_run_step(
        self,
        step_run_id: UUID,
        hydrate: bool = True,
    ) -> StepRunResponse:
        """Get a step run by ID.

        Args:
            step_run_id: The ID of the step run to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The step run.
        """
        return self.zen_store.get_run_step(
            step_run_id,
            hydrate=hydrate,
        )

    def list_run_steps(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        name: Optional[str] = None,
        entrypoint_name: Optional[str] = None,
        code_hash: Optional[str] = None,
        cache_key: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[Union[datetime, str]] = None,
        end_time: Optional[Union[datetime, str]] = None,
        pipeline_run_id: Optional[Union[str, UUID]] = None,
        original_step_run_id: Optional[Union[str, UUID]] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        model_version_id: Optional[Union[str, UUID]] = None,
        num_outputs: Optional[Union[int, str]] = None,
        hydrate: bool = False,
    ) -> Page[StepRunResponse]:
        """List all pipelines.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of runs to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            start_time: Use to filter by the time when the step started running
            end_time: Use to filter by the time when the step finished running
            workspace_id: The id of the workspace to filter by.
            user_id: The  id of the user to filter by.
            pipeline_run_id: The  id of the pipeline run to filter by.
            original_step_run_id: The  id of the pipeline run to filter by.
            model_version_id: The ID of the model version to filter by.
            name: The name of the run to filter by.
            entrypoint_name: The entrypoint_name of the run to filter by.
            code_hash: The code_hash of the run to filter by.
            cache_key: The cache_key of the run to filter by.
            status: The name of the run to filter by.
            num_outputs: The number of outputs for the step run
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page with Pipeline fitting the filter description
        """
        step_run_filter_model = StepRunFilter(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            entrypoint_name=entrypoint_name,
            code_hash=code_hash,
            cache_key=cache_key,
            pipeline_run_id=pipeline_run_id,
            original_step_run_id=original_step_run_id,
            status=status,
            created=created,
            updated=updated,
            start_time=start_time,
            end_time=end_time,
            name=name,
            workspace_id=workspace_id,
            user_id=user_id,
            model_version_id=model_version_id,
            num_outputs=num_outputs,
        )
        step_run_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_run_steps(
            step_run_filter_model=step_run_filter_model,
            hydrate=hydrate,
        )

    # ------------------------------- Artifacts -------------------------------

    def get_artifact(
        self,
        name_id_or_prefix: Union[str, UUID],
        hydrate: bool = False,
    ) -> ArtifactResponse:
        """Get an artifact by name, id or prefix.

        Args:
            name_id_or_prefix: The name, ID or prefix of the artifact to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The artifact.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_artifact,
            list_method=self.list_artifacts,
            name_id_or_prefix=name_id_or_prefix,
            hydrate=hydrate,
        )

    def list_artifacts(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        name: Optional[str] = None,
        has_custom_name: Optional[bool] = None,
        hydrate: bool = False,
        tag: Optional[str] = None,
    ) -> Page[ArtifactResponse]:
        """Get a list of artifacts.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of artifact to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            name: The name of the artifact to filter by.
            has_custom_name: Filter artifacts with/without custom names.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            tag: Filter artifacts by tag.

        Returns:
            A list of artifacts.
        """
        artifact_filter_model = ArtifactFilter(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            created=created,
            updated=updated,
            name=name,
            has_custom_name=has_custom_name,
            tag=tag,
        )
        return self.zen_store.list_artifacts(
            artifact_filter_model,
            hydrate=hydrate,
        )

    def update_artifact(
        self,
        name_id_or_prefix: Union[str, UUID],
        new_name: Optional[str] = None,
        add_tags: Optional[List[str]] = None,
        remove_tags: Optional[List[str]] = None,
        has_custom_name: Optional[bool] = None,
    ) -> ArtifactResponse:
        """Update an artifact.

        Args:
            name_id_or_prefix: The name, ID or prefix of the artifact to update.
            new_name: The new name of the artifact.
            add_tags: Tags to add to the artifact.
            remove_tags: Tags to remove from the artifact.
            has_custom_name: Whether the artifact has a custom name.

        Returns:
            The updated artifact.
        """
        artifact = self.get_artifact(name_id_or_prefix=name_id_or_prefix)
        artifact_update = ArtifactUpdate(
            name=new_name,
            add_tags=add_tags,
            remove_tags=remove_tags,
            has_custom_name=has_custom_name,
        )
        return self.zen_store.update_artifact(
            artifact_id=artifact.id, artifact_update=artifact_update
        )

    def delete_artifact(
        self,
        name_id_or_prefix: Union[str, UUID],
    ) -> None:
        """Delete an artifact.

        Args:
            name_id_or_prefix: The name, ID or prefix of the artifact to delete.
        """
        artifact = self.get_artifact(name_id_or_prefix=name_id_or_prefix)
        self.zen_store.delete_artifact(artifact_id=artifact.id)
        logger.info(f"Deleted artifact '{artifact.name}'.")

    def prune_artifacts(
        self,
        only_versions: bool = True,
        delete_from_artifact_store: bool = False,
    ) -> None:
        """Delete all unused artifacts and artifact versions.

        Args:
            only_versions: Only delete artifact versions, keeping artifacts
            delete_from_artifact_store: Delete data from artifact metadata
        """
        if delete_from_artifact_store:
            unused_artifact_versions = depaginate(
                self.list_artifact_versions, only_unused=True
            )
            for unused_artifact_version in unused_artifact_versions:
                self._delete_artifact_from_artifact_store(
                    unused_artifact_version
                )

        self.zen_store.prune_artifact_versions(only_versions)
        logger.info("All unused artifacts and artifact versions deleted.")

    # --------------------------- Artifact Versions ---------------------------

    def get_artifact_version(
        self,
        name_id_or_prefix: Union[str, UUID],
        version: Optional[str] = None,
        hydrate: bool = True,
    ) -> ArtifactVersionResponse:
        """Get an artifact version by ID or artifact name.

        Args:
            name_id_or_prefix: Either the ID of the artifact version or the
                name of the artifact.
            version: The version of the artifact to get. Only used if
                `name_id_or_prefix` is the name of the artifact. If not
                specified, the latest version is returned.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The artifact version.
        """
        if cll := client_lazy_loader(
            method_name="get_artifact_version",
            name_id_or_prefix=name_id_or_prefix,
            version=version,
            hydrate=hydrate,
        ):
            return cll  # type: ignore[return-value]
        return self._get_entity_version_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_artifact_version,
            list_method=self.list_artifact_versions,
            name_id_or_prefix=name_id_or_prefix,
            version=version,
            hydrate=hydrate,
        )

    def list_artifact_versions(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        artifact_id: Optional[Union[str, UUID]] = None,
        name: Optional[str] = None,
        version: Optional[Union[str, int]] = None,
        version_number: Optional[int] = None,
        artifact_store_id: Optional[Union[str, UUID]] = None,
        type: Optional[ArtifactType] = None,
        data_type: Optional[str] = None,
        uri: Optional[str] = None,
        materializer: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        only_unused: Optional[bool] = False,
        has_custom_name: Optional[bool] = None,
        user: Optional[Union[UUID, str]] = None,
        model: Optional[Union[UUID, str]] = None,
        pipeline_run: Optional[Union[UUID, str]] = None,
        tag: Optional[str] = None,
        hydrate: bool = False,
    ) -> Page[ArtifactVersionResponse]:
        """Get a list of artifact versions.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of artifact version to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            artifact_id: The id of the artifact to filter by.
            name: The name of the artifact to filter by.
            version: The version of the artifact to filter by.
            version_number: The version number of the artifact to filter by.
            artifact_store_id: The id of the artifact store to filter by.
            type: The type of the artifact to filter by.
            data_type: The data type of the artifact to filter by.
            uri: The uri of the artifact to filter by.
            materializer: The materializer of the artifact to filter by.
            workspace_id: The id of the workspace to filter by.
            user_id: The  id of the user to filter by.
            only_unused: Only return artifact versions that are not used in
                any pipeline runs.
            has_custom_name: Filter artifacts with/without custom names.
            tag: A tag to filter by.
            user: Filter by user name or ID.
            model: Filter by model name or ID.
            pipeline_run: Filter by pipeline run name or ID.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of artifact versions.
        """
        artifact_version_filter_model = ArtifactVersionFilter(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            created=created,
            updated=updated,
            artifact_id=artifact_id,
            name=name,
            version=str(version) if version else None,
            version_number=version_number,
            artifact_store_id=artifact_store_id,
            type=type,
            data_type=data_type,
            uri=uri,
            materializer=materializer,
            workspace_id=workspace_id,
            user_id=user_id,
            only_unused=only_unused,
            has_custom_name=has_custom_name,
            tag=tag,
            user=user,
            model=model,
            pipeline_run=pipeline_run,
        )
        artifact_version_filter_model.set_scope_workspace(
            self.active_workspace.id
        )
        return self.zen_store.list_artifact_versions(
            artifact_version_filter_model,
            hydrate=hydrate,
        )

    def update_artifact_version(
        self,
        name_id_or_prefix: Union[str, UUID],
        version: Optional[str] = None,
        add_tags: Optional[List[str]] = None,
        remove_tags: Optional[List[str]] = None,
    ) -> ArtifactVersionResponse:
        """Update an artifact version.

        Args:
            name_id_or_prefix: The name, ID or prefix of the artifact to update.
            version: The version of the artifact to update. Only used if
                `name_id_or_prefix` is the name of the artifact. If not
                specified, the latest version is updated.
            add_tags: Tags to add to the artifact version.
            remove_tags: Tags to remove from the artifact version.

        Returns:
            The updated artifact version.
        """
        artifact_version = self.get_artifact_version(
            name_id_or_prefix=name_id_or_prefix,
            version=version,
        )
        artifact_version_update = ArtifactVersionUpdate(
            add_tags=add_tags, remove_tags=remove_tags
        )
        return self.zen_store.update_artifact_version(
            artifact_version_id=artifact_version.id,
            artifact_version_update=artifact_version_update,
        )

    def delete_artifact_version(
        self,
        name_id_or_prefix: Union[str, UUID],
        version: Optional[str] = None,
        delete_metadata: bool = True,
        delete_from_artifact_store: bool = False,
    ) -> None:
        """Delete an artifact version.

        By default, this will delete only the metadata of the artifact from the
        database, not the actual object stored in the artifact store.

        Args:
            name_id_or_prefix: The ID of artifact version or name or prefix of the artifact to
                delete.
            version: The version of the artifact to delete.
            delete_metadata: If True, delete the metadata of the artifact
                version from the database.
            delete_from_artifact_store: If True, delete the artifact object
                itself from the artifact store.
        """
        artifact_version = self.get_artifact_version(
            name_id_or_prefix=name_id_or_prefix, version=version
        )
        if delete_from_artifact_store:
            self._delete_artifact_from_artifact_store(
                artifact_version=artifact_version
            )
        if delete_metadata:
            self._delete_artifact_version(artifact_version=artifact_version)

    def _delete_artifact_version(
        self, artifact_version: ArtifactVersionResponse
    ) -> None:
        """Delete the metadata of an artifact version from the database.

        Args:
            artifact_version: The artifact version to delete.

        Raises:
            ValueError: If the artifact version is still used in any runs.
        """
        if artifact_version not in depaginate(
            self.list_artifact_versions, only_unused=True
        ):
            raise ValueError(
                "The metadata of artifact versions that are used in runs "
                "cannot be deleted. Please delete all runs that use this "
                "artifact first."
            )
        self.zen_store.delete_artifact_version(artifact_version.id)
        logger.info(
            f"Deleted version '{artifact_version.version}' of artifact "
            f"'{artifact_version.artifact.name}'."
        )

    def _delete_artifact_from_artifact_store(
        self, artifact_version: ArtifactVersionResponse
    ) -> None:
        """Delete an artifact object from the artifact store.

        Args:
            artifact_version: The artifact version to delete.

        Raises:
            Exception: If the artifact store is inaccessible.
        """
        from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
        from zenml.stack.stack_component import StackComponent

        if not artifact_version.artifact_store_id:
            logger.warning(
                f"Artifact '{artifact_version.uri}' does not have an artifact "
                "store associated with it. Skipping deletion from artifact "
                "store."
            )
            return
        try:
            artifact_store_model = self.get_stack_component(
                component_type=StackComponentType.ARTIFACT_STORE,
                name_id_or_prefix=artifact_version.artifact_store_id,
            )
            artifact_store = StackComponent.from_model(artifact_store_model)
            assert isinstance(artifact_store, BaseArtifactStore)
            artifact_store.rmtree(artifact_version.uri)
        except Exception as e:
            logger.error(
                f"Failed to delete artifact '{artifact_version.uri}' from the "
                "artifact store. This might happen if your local client "
                "does not have access to the artifact store or does not "
                "have the required integrations installed. Full error: "
                f"{e}"
            )
            raise e
        else:
            logger.info(
                f"Deleted artifact '{artifact_version.uri}' from the artifact "
                "store."
            )

    # ------------------------------ Run Metadata ------------------------------

    def create_run_metadata(
        self,
        metadata: Dict[str, "MetadataType"],
        resource_id: UUID,
        resource_type: MetadataResourceTypes,
        stack_component_id: Optional[UUID] = None,
    ) -> List[RunMetadataResponse]:
        """Create run metadata.

        Args:
            metadata: The metadata to create as a dictionary of key-value pairs.
            resource_id: The ID of the resource for which the
                metadata was produced.
            resource_type: The type of the resource for which the
                metadata was produced.
            stack_component_id: The ID of the stack component that produced
                the metadata.

        Returns:
            The created metadata, as string to model dictionary.
        """
        from zenml.metadata.metadata_types import get_metadata_type

        values: Dict[str, "MetadataType"] = {}
        types: Dict[str, "MetadataTypeEnum"] = {}
        for key, value in metadata.items():
            # Skip metadata that is too large to be stored in the database.
            if len(json.dumps(value)) > TEXT_FIELD_MAX_LENGTH:
                logger.warning(
                    f"Metadata value for key '{key}' is too large to be "
                    "stored in the database. Skipping."
                )
                continue
            # Skip metadata that is not of a supported type.
            try:
                metadata_type = get_metadata_type(value)
            except ValueError as e:
                logger.warning(
                    f"Metadata value for key '{key}' is not of a supported "
                    f"type. Skipping. Full error: {e}"
                )
                continue
            values[key] = value
            types[key] = metadata_type

        run_metadata = RunMetadataRequest(
            workspace=self.active_workspace.id,
            user=self.active_user.id,
            resource_id=resource_id,
            resource_type=resource_type,
            stack_component_id=stack_component_id,
            values=values,
            types=types,
        )
        return self.zen_store.create_run_metadata(run_metadata)

    def list_run_metadata(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        workspace_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        resource_id: Optional[UUID] = None,
        resource_type: Optional[MetadataResourceTypes] = None,
        stack_component_id: Optional[UUID] = None,
        key: Optional[str] = None,
        value: Optional["MetadataType"] = None,
        type: Optional[str] = None,
        hydrate: bool = False,
    ) -> Page[RunMetadataResponse]:
        """List run metadata.

        Args:
            sort_by: The field to sort the results by.
            page: The page number to return.
            size: The number of results to return per page.
            logical_operator: The logical operator to use for filtering.
            id: The ID of the metadata.
            created: The creation time of the metadata.
            updated: The last update time of the metadata.
            workspace_id: The ID of the workspace the metadata belongs to.
            user_id: The ID of the user that created the metadata.
            resource_id: The ID of the resource the metadata belongs to.
            resource_type: The type of the resource the metadata belongs to.
            stack_component_id: The ID of the stack component that produced
                the metadata.
            key: The key of the metadata.
            value: The value of the metadata.
            type: The type of the metadata.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The run metadata.
        """
        metadata_filter_model = RunMetadataFilter(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            created=created,
            updated=updated,
            workspace_id=workspace_id,
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            stack_component_id=stack_component_id,
            key=key,
            value=value,
            type=type,
        )
        metadata_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_run_metadata(
            metadata_filter_model,
            hydrate=hydrate,
        )

    # -------------------------------- Secrets ---------------------------------

    def create_secret(
        self,
        name: str,
        values: Dict[str, str],
        scope: SecretScope = SecretScope.WORKSPACE,
    ) -> SecretResponse:
        """Creates a new secret.

        Args:
            name: The name of the secret.
            values: The values of the secret.
            scope: The scope of the secret.

        Returns:
            The created secret (in model form).

        Raises:
            NotImplementedError: If centralized secrets management is not
                enabled.
        """
        create_secret_request = SecretRequest(
            name=name,
            values=values,
            scope=scope,
            user=self.active_user.id,
            workspace=self.active_workspace.id,
        )
        try:
            return self.zen_store.create_secret(secret=create_secret_request)
        except NotImplementedError:
            raise NotImplementedError(
                "centralized secrets management is not supported or explicitly "
                "disabled in the target ZenML deployment."
            )

    def get_secret(
        self,
        name_id_or_prefix: Union[str, UUID],
        scope: Optional[SecretScope] = None,
        allow_partial_name_match: bool = True,
        allow_partial_id_match: bool = True,
        hydrate: bool = True,
    ) -> SecretResponse:
        """Get a secret.

        Get a secret identified by a name, ID or prefix of the name or ID and
        optionally a scope.

        If a scope is not provided, the secret will be searched for in all
        scopes starting with the innermost scope (user) to the outermost scope
        (workspace). When a name or prefix is used instead of a UUID value, each
        scope is first searched for an exact match, then for a ID prefix or
        name substring match before moving on to the next scope.

        Args:
            name_id_or_prefix: The name, ID or prefix to the id of the secret
                to get.
            scope: The scope of the secret. If not set, all scopes will be
                searched starting with the innermost scope (user) to the
                outermost scope (global) until a secret is found.
            allow_partial_name_match: If True, allow partial name matches.
            allow_partial_id_match: If True, allow partial ID matches.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The secret.

        Raises:
            KeyError: If no secret is found.
            ZenKeyError: If multiple secrets are found.
            NotImplementedError: If centralized secrets management is not
                enabled.
        """
        from zenml.utils.uuid_utils import is_valid_uuid

        try:
            # First interpret as full UUID
            if is_valid_uuid(name_id_or_prefix):
                # Fetch by ID; filter by scope if provided
                secret = self.zen_store.get_secret(
                    secret_id=UUID(name_id_or_prefix)
                    if isinstance(name_id_or_prefix, str)
                    else name_id_or_prefix,
                    hydrate=hydrate,
                )
                if scope is not None and secret.scope != scope:
                    raise KeyError(
                        f"No secret found with ID {str(name_id_or_prefix)}"
                    )

                return secret
        except NotImplementedError:
            raise NotImplementedError(
                "centralized secrets management is not supported or explicitly "
                "disabled in the target ZenML deployment."
            )

        # If not a UUID, try to find by name and then by prefix
        assert not isinstance(name_id_or_prefix, UUID)

        # Scopes to search in order of priority
        search_scopes = (
            [SecretScope.USER, SecretScope.WORKSPACE]
            if scope is None
            else [scope]
        )

        secrets = self.list_secrets(
            logical_operator=LogicalOperators.OR,
            name=f"contains:{name_id_or_prefix}"
            if allow_partial_name_match
            else f"equals:{name_id_or_prefix}",
            id=f"startswith:{name_id_or_prefix}"
            if allow_partial_id_match
            else None,
            hydrate=hydrate,
        )

        for search_scope in search_scopes:
            partial_matches: List[SecretResponse] = []
            for secret in secrets.items:
                if secret.scope != search_scope:
                    continue
                # Exact match
                if secret.name == name_id_or_prefix:
                    # Need to fetch the secret again to get the secret values
                    return self.zen_store.get_secret(
                        secret_id=secret.id,
                        hydrate=hydrate,
                    )
                # Partial match
                partial_matches.append(secret)

            if len(partial_matches) > 1:
                match_summary = "\n".join(
                    [
                        f"[{secret.id}]: name = {secret.name}"
                        for secret in partial_matches
                    ]
                )
                raise ZenKeyError(
                    f"{len(partial_matches)} secrets have been found that have "
                    f"a name or ID that matches the provided "
                    f"string '{name_id_or_prefix}':\n"
                    f"{match_summary}.\n"
                    f"Please use the id to uniquely identify "
                    f"only one of the secrets."
                )

            # If only a single secret is found, return it
            if len(partial_matches) == 1:
                # Need to fetch the secret again to get the secret values
                return self.zen_store.get_secret(
                    secret_id=partial_matches[0].id,
                    hydrate=hydrate,
                )

        msg = (
            f"No secret found with name, ID or prefix "
            f"'{name_id_or_prefix}'"
        )
        if scope is not None:
            msg += f" in scope '{scope}'"

        raise KeyError(msg)

    def list_secrets(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[datetime] = None,
        updated: Optional[datetime] = None,
        name: Optional[str] = None,
        scope: Optional[SecretScope] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        hydrate: bool = False,
    ) -> Page[SecretResponse]:
        """Fetches all the secret models.

        The returned secrets do not contain the secret values. To get the
        secret values, use `get_secret` individually for each secret.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of secrets to filter by.
            created: Use to secrets by time of creation
            updated: Use the last updated date for filtering
            name: The name of the secret to filter by.
            scope: The scope of the secret to filter by.
            workspace_id: The id of the workspace to filter by.
            user_id: The  id of the user to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all the secret models without the secret values.

        Raises:
            NotImplementedError: If centralized secrets management is not
                enabled.
        """
        secret_filter_model = SecretFilter(
            page=page,
            size=size,
            sort_by=sort_by,
            logical_operator=logical_operator,
            user_id=user_id,
            workspace_id=workspace_id,
            name=name,
            scope=scope,
            id=id,
            created=created,
            updated=updated,
        )
        secret_filter_model.set_scope_workspace(self.active_workspace.id)
        try:
            return self.zen_store.list_secrets(
                secret_filter_model=secret_filter_model,
                hydrate=hydrate,
            )
        except NotImplementedError:
            raise NotImplementedError(
                "centralized secrets management is not supported or explicitly "
                "disabled in the target ZenML deployment."
            )

    def update_secret(
        self,
        name_id_or_prefix: Union[str, UUID],
        scope: Optional[SecretScope] = None,
        new_name: Optional[str] = None,
        new_scope: Optional[SecretScope] = None,
        add_or_update_values: Optional[Dict[str, str]] = None,
        remove_values: Optional[List[str]] = None,
    ) -> SecretResponse:
        """Updates a secret.

        Args:
            name_id_or_prefix: The name, id or prefix of the id for the
                secret to update.
            scope: The scope of the secret to update.
            new_name: The new name of the secret.
            new_scope: The new scope of the secret.
            add_or_update_values: The values to add or update.
            remove_values: The values to remove.

        Returns:
            The updated secret.

        Raises:
            KeyError: If trying to remove a value that doesn't exist.
            ValueError: If a key is provided in both add_or_update_values and
                remove_values.
        """
        secret = self.get_secret(
            name_id_or_prefix=name_id_or_prefix,
            scope=scope,
            # Don't allow partial name matches, but allow partial ID matches
            allow_partial_name_match=False,
            allow_partial_id_match=True,
            hydrate=True,
        )

        secret_update = SecretUpdate(name=new_name or secret.name)

        if new_scope:
            secret_update.scope = new_scope
        values: Dict[str, Optional[SecretStr]] = {}
        if add_or_update_values:
            values.update(
                {
                    key: SecretStr(value)
                    for key, value in add_or_update_values.items()
                }
            )
        if remove_values:
            for key in remove_values:
                if key not in secret.values:
                    raise KeyError(
                        f"Cannot remove value '{key}' from secret "
                        f"'{secret.name}' because it does not exist."
                    )
                if key in values:
                    raise ValueError(
                        f"Key '{key}' is supplied both in the values to add or "
                        f"update and the values to be removed."
                    )
                values[key] = None
        if values:
            secret_update.values = values

        return Client().zen_store.update_secret(
            secret_id=secret.id, secret_update=secret_update
        )

    def delete_secret(
        self, name_id_or_prefix: str, scope: Optional[SecretScope] = None
    ) -> None:
        """Deletes a secret.

        Args:
            name_id_or_prefix: The name or ID of the secret.
            scope: The scope of the secret to delete.
        """
        secret = self.get_secret(
            name_id_or_prefix=name_id_or_prefix,
            scope=scope,
            # Don't allow partial name matches, but allow partial ID matches
            allow_partial_name_match=False,
            allow_partial_id_match=True,
        )

        self.zen_store.delete_secret(secret_id=secret.id)

    def get_secret_by_name_and_scope(
        self,
        name: str,
        scope: Optional[SecretScope] = None,
        hydrate: bool = True,
    ) -> SecretResponse:
        """Fetches a registered secret with a given name and optional scope.

        This is a version of get_secret that restricts the search to a given
        name and an optional scope, without doing any prefix or UUID matching.

        If no scope is provided, the search will be done first in the user
        scope, then in the workspace scope.

        Args:
            name: The name of the secret to get.
            scope: The scope of the secret to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The registered secret.

        Raises:
            KeyError: If no secret exists for the given name in the given scope.
        """
        logger.debug(
            f"Fetching the secret with name '{name}' and scope '{scope}'."
        )

        # Scopes to search in order of priority
        search_scopes = (
            [SecretScope.USER, SecretScope.WORKSPACE]
            if scope is None
            else [scope]
        )

        for search_scope in search_scopes:
            secrets = self.list_secrets(
                logical_operator=LogicalOperators.AND,
                name=f"equals:{name}",
                scope=search_scope,
                hydrate=hydrate,
            )

            if len(secrets.items) >= 1:
                # Need to fetch the secret again to get the secret values
                return self.zen_store.get_secret(
                    secret_id=secrets.items[0].id, hydrate=hydrate
                )

        msg = f"No secret with name '{name}' was found"
        if scope is not None:
            msg += f" in scope '{scope.value}'"

        raise KeyError(msg)

    def list_secrets_in_scope(
        self,
        scope: SecretScope,
        hydrate: bool = False,
    ) -> Page[SecretResponse]:
        """Fetches the list of secret in a given scope.

        The returned secrets do not contain the secret values. To get the
        secret values, use `get_secret` individually for each secret.

        Args:
            scope: The secrets scope to search for.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The list of secrets in the given scope without the secret values.
        """
        logger.debug(f"Fetching the secrets in scope {scope.value}.")

        return self.list_secrets(scope=scope, hydrate=hydrate)

    def backup_secrets(
        self,
        ignore_errors: bool = True,
        delete_secrets: bool = False,
    ) -> None:
        """Backs up all secrets to the configured backup secrets store.

        Args:
            ignore_errors: Whether to ignore individual errors during the backup
                process and attempt to backup all secrets.
            delete_secrets: Whether to delete the secrets that have been
                successfully backed up from the primary secrets store. Setting
                this flag effectively moves all secrets from the primary secrets
                store to the backup secrets store.
        """
        self.zen_store.backup_secrets(
            ignore_errors=ignore_errors, delete_secrets=delete_secrets
        )

    def restore_secrets(
        self,
        ignore_errors: bool = False,
        delete_secrets: bool = False,
    ) -> None:
        """Restore all secrets from the configured backup secrets store.

        Args:
            ignore_errors: Whether to ignore individual errors during the
                restore process and attempt to restore all secrets.
            delete_secrets: Whether to delete the secrets that have been
                successfully restored from the backup secrets store. Setting
                this flag effectively moves all secrets from the backup secrets
                store to the primary secrets store.
        """
        self.zen_store.restore_secrets(
            ignore_errors=ignore_errors, delete_secrets=delete_secrets
        )

    # --------------------------- Code repositories ---------------------------

    def create_code_repository(
        self,
        name: str,
        config: Dict[str, Any],
        source: Source,
        description: Optional[str] = None,
        logo_url: Optional[str] = None,
    ) -> CodeRepositoryResponse:
        """Create a new code repository.

        Args:
            name: Name of the code repository.
            config: The configuration for the code repository.
            source: The code repository implementation source.
            description: The code repository description.
            logo_url: URL of a logo (png, jpg or svg) for the code repository.

        Returns:
            The created code repository.

        Raises:
            RuntimeError: If the provided config is invalid.
        """
        from zenml.code_repositories import BaseCodeRepository

        code_repo_class: Type[BaseCodeRepository] = (
            source_utils.load_and_validate_class(
                source=source, expected_class=BaseCodeRepository
            )
        )
        try:
            # Validate the repo config
            code_repo_class(id=uuid4(), config=config)
        except Exception as e:
            raise RuntimeError(
                "Failed to validate code repository config."
            ) from e

        repo_request = CodeRepositoryRequest(
            user=self.active_user.id,
            workspace=self.active_workspace.id,
            name=name,
            config=config,
            source=source,
            description=description,
            logo_url=logo_url,
        )
        return self.zen_store.create_code_repository(
            code_repository=repo_request
        )

    def get_code_repository(
        self,
        name_id_or_prefix: Union[str, UUID],
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> CodeRepositoryResponse:
        """Get a code repository by name, id or prefix.

        Args:
            name_id_or_prefix: The name, ID or ID prefix of the code repository.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The code repository.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_code_repository,
            list_method=self.list_code_repositories,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            hydrate=hydrate,
        )

    def list_code_repositories(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        name: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        hydrate: bool = False,
    ) -> Page[CodeRepositoryResponse]:
        """List all code repositories.

        Args:
            sort_by: The column to sort by.
            page: The page of items.
            size: The maximum size of all pages.
            logical_operator: Which logical operator to use [and, or].
            id: Use the id of the code repository to filter by.
            created: Use to filter by time of creation.
            updated: Use the last updated date for filtering.
            name: The name of the code repository to filter by.
            workspace_id: The id of the workspace to filter by.
            user_id: The id of the user to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of code repositories matching the filter description.
        """
        filter_model = CodeRepositoryFilter(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            created=created,
            updated=updated,
            name=name,
            workspace_id=workspace_id,
            user_id=user_id,
        )
        filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_code_repositories(
            filter_model=filter_model,
            hydrate=hydrate,
        )

    def update_code_repository(
        self,
        name_id_or_prefix: Union[UUID, str],
        name: Optional[str] = None,
        description: Optional[str] = None,
        logo_url: Optional[str] = None,
    ) -> CodeRepositoryResponse:
        """Update a code repository.

        Args:
            name_id_or_prefix: Name, ID or prefix of the code repository to
                update.
            name: New name of the code repository.
            description: New description of the code repository.
            logo_url: New logo URL of the code repository.

        Returns:
            The updated code repository.
        """
        repo = self.get_code_repository(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )
        update = CodeRepositoryUpdate(
            name=name, description=description, logo_url=logo_url
        )
        return self.zen_store.update_code_repository(
            code_repository_id=repo.id, update=update
        )

    def delete_code_repository(
        self,
        name_id_or_prefix: Union[str, UUID],
    ) -> None:
        """Delete a code repository.

        Args:
            name_id_or_prefix: The name, ID or prefix of the code repository.
        """
        repo = self.get_code_repository(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )
        self.zen_store.delete_code_repository(code_repository_id=repo.id)

    # --------------------------- Service Connectors ---------------------------

    def create_service_connector(
        self,
        name: str,
        connector_type: str,
        resource_type: Optional[str] = None,
        auth_method: Optional[str] = None,
        configuration: Optional[Dict[str, str]] = None,
        resource_id: Optional[str] = None,
        description: str = "",
        expiration_seconds: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        expires_skew_tolerance: Optional[int] = None,
        labels: Optional[Dict[str, str]] = None,
        auto_configure: bool = False,
        verify: bool = True,
        list_resources: bool = True,
        register: bool = True,
    ) -> Tuple[
        Optional[
            Union[
                ServiceConnectorResponse,
                ServiceConnectorRequest,
            ]
        ],
        Optional[ServiceConnectorResourcesModel],
    ]:
        """Create, validate and/or register a service connector.

        Args:
            name: The name of the service connector.
            connector_type: The service connector type.
            auth_method: The authentication method of the service connector.
                May be omitted if auto-configuration is used.
            resource_type: The resource type for the service connector.
            configuration: The configuration of the service connector.
            resource_id: The resource id of the service connector.
            description: The description of the service connector.
            expiration_seconds: The expiration time of the service connector.
            expires_at: The expiration time of the service connector.
            expires_skew_tolerance: The allowed expiration skew for the service
                connector credentials.
            labels: The labels of the service connector.
            auto_configure: Whether to automatically configure the service
                connector from the local environment.
            verify: Whether to verify that the service connector configuration
                and credentials can be used to gain access to the resource.
            list_resources: Whether to also list the resources that the service
                connector can give access to (if verify is True).
            register: Whether to register the service connector or not.

        Returns:
            The model of the registered service connector and the resources
            that the service connector can give access to (if verify is True).

        Raises:
            ValueError: If the arguments are invalid.
            KeyError: If the service connector type is not found.
            NotImplementedError: If auto-configuration is not supported or
                not implemented for the service connector type.
            AuthorizationException: If the connector verification failed due
                to authorization issues.
        """
        from zenml.service_connectors.service_connector_registry import (
            service_connector_registry,
        )

        connector_instance: Optional[ServiceConnector] = None
        connector_resources: Optional[ServiceConnectorResourcesModel] = None

        # Get the service connector type class
        try:
            connector = self.zen_store.get_service_connector_type(
                connector_type=connector_type,
            )
        except KeyError:
            raise KeyError(
                f"Service connector type {connector_type} not found."
                "Please check that you have installed all required "
                "Python packages and ZenML integrations and try again."
            )

        if not resource_type and len(connector.resource_types) == 1:
            resource_type = connector.resource_types[0].resource_type

        # If auto_configure is set, we will try to automatically configure the
        # service connector from the local environment
        if auto_configure:
            if not connector.supports_auto_configuration:
                raise NotImplementedError(
                    f"The {connector.name} service connector type "
                    "does not support auto-configuration."
                )
            if not connector.local:
                raise NotImplementedError(
                    f"The {connector.name} service connector type "
                    "implementation is not available locally. Please "
                    "check that you have installed all required Python "
                    "packages and ZenML integrations and try again, or "
                    "skip auto-configuration."
                )

            assert connector.connector_class is not None

            connector_instance = connector.connector_class.auto_configure(
                resource_type=resource_type,
                auth_method=auth_method,
                resource_id=resource_id,
            )
            assert connector_instance is not None
            connector_request = connector_instance.to_model(
                name=name,
                user=self.active_user.id,
                workspace=self.active_workspace.id,
                description=description or "",
                labels=labels,
            )

            if verify:
                # Prefer to verify the connector config server-side if the
                # implementation if available there, because it ensures
                # that the connector can be shared with other users or used
                # from other machines and because some auth methods rely on the
                # server-side authentication environment
                if connector.remote:
                    connector_resources = (
                        self.zen_store.verify_service_connector_config(
                            connector_request,
                            list_resources=list_resources,
                        )
                    )
                else:
                    connector_resources = connector_instance.verify(
                        list_resources=list_resources,
                    )

                if connector_resources.error:
                    # Raise an exception if the connector verification failed
                    raise AuthorizationException(connector_resources.error)

        else:
            if not auth_method:
                if len(connector.auth_methods) == 1:
                    auth_method = connector.auth_methods[0].auth_method
                else:
                    raise ValueError(
                        f"Multiple authentication methods are available for "
                        f"the {connector.name} service connector type. Please "
                        f"specify one of the following: "
                        f"{list(connector.auth_method_dict.keys())}."
                    )

            connector_request = ServiceConnectorRequest(
                name=name,
                connector_type=connector_type,
                description=description,
                auth_method=auth_method,
                expiration_seconds=expiration_seconds,
                expires_at=expires_at,
                expires_skew_tolerance=expires_skew_tolerance,
                user=self.active_user.id,
                workspace=self.active_workspace.id,
                labels=labels or {},
            )
            # Validate and configure the resources
            connector_request.validate_and_configure_resources(
                connector_type=connector,
                resource_types=resource_type,
                resource_id=resource_id,
                configuration=configuration,
            )
            if verify:
                # Prefer to verify the connector config server-side if the
                # implementation if available there, because it ensures
                # that the connector can be shared with other users or used
                # from other machines and because some auth methods rely on the
                # server-side authentication environment
                if connector.remote:
                    connector_resources = (
                        self.zen_store.verify_service_connector_config(
                            connector_request,
                            list_resources=list_resources,
                        )
                    )
                else:
                    connector_instance = (
                        service_connector_registry.instantiate_connector(
                            model=connector_request
                        )
                    )
                    connector_resources = connector_instance.verify(
                        list_resources=list_resources,
                    )

                if connector_resources.error:
                    # Raise an exception if the connector verification failed
                    raise AuthorizationException(connector_resources.error)

                # For resource types that don't support multi-instances, it's
                # better to save the default resource ID in the connector, if
                # available. Otherwise, we'll need to instantiate the connector
                # again to get the default resource ID.
                connector_request.resource_id = (
                    connector_request.resource_id
                    or connector_resources.get_default_resource_id()
                )

        if not register:
            return connector_request, connector_resources

        # Register the new model
        connector_response = self.zen_store.create_service_connector(
            service_connector=connector_request
        )

        if connector_resources:
            connector_resources.id = connector_response.id
            connector_resources.name = connector_response.name
            connector_resources.connector_type = (
                connector_response.connector_type
            )

        return connector_response, connector_resources

    def get_service_connector(
        self,
        name_id_or_prefix: Union[str, UUID],
        allow_name_prefix_match: bool = True,
        load_secrets: bool = False,
        hydrate: bool = True,
    ) -> ServiceConnectorResponse:
        """Fetches a registered service connector.

        Args:
            name_id_or_prefix: The id of the service connector to fetch.
            allow_name_prefix_match: If True, allow matching by name prefix.
            load_secrets: If True, load the secrets for the service connector.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The registered service connector.
        """

        def scoped_list_method(
            hydrate: bool = False,
            **kwargs: Any,
        ) -> Page[ServiceConnectorResponse]:
            """Call `zen_store.list_service_connectors` with workspace scoping.

            Args:
                hydrate: Flag deciding whether to hydrate the output model(s)
                    by including metadata fields in the response.
                **kwargs: Keyword arguments to pass to
                    `ServiceConnectorFilterModel`.

            Returns:
                The list of service connectors.
            """
            filter_model = ServiceConnectorFilter(**kwargs)
            filter_model.set_scope_workspace(self.active_workspace.id)
            return self.zen_store.list_service_connectors(
                filter_model=filter_model,
                hydrate=hydrate,
            )

        connector = self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_service_connector,
            list_method=scoped_list_method,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            hydrate=hydrate,
        )

        if load_secrets and connector.secret_id:
            client = Client()
            try:
                secret = client.get_secret(
                    name_id_or_prefix=connector.secret_id,
                    allow_partial_id_match=False,
                    allow_partial_name_match=False,
                )
            except KeyError as err:
                logger.error(
                    "Unable to retrieve secret values associated with "
                    f"service connector '{connector.name}': {err}"
                )
            else:
                # Add secret values to connector configuration
                connector.secrets.update(secret.values)

        return connector

    def list_service_connectors(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[datetime] = None,
        updated: Optional[datetime] = None,
        name: Optional[str] = None,
        connector_type: Optional[str] = None,
        auth_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        labels: Optional[Dict[str, Optional[str]]] = None,
        secret_id: Optional[Union[str, UUID]] = None,
        hydrate: bool = False,
    ) -> Page[ServiceConnectorResponse]:
        """Lists all registered service connectors.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: The id of the service connector to filter by.
            created: Filter service connectors by time of creation
            updated: Use the last updated date for filtering
            connector_type: Use the service connector type for filtering
            auth_method: Use the service connector auth method for filtering
            resource_type: Filter service connectors by the resource type that
                they can give access to.
            resource_id: Filter service connectors by the resource id that
                they can give access to.
            workspace_id: The id of the workspace to filter by.
            user_id: The id of the user to filter by.
            name: The name of the service connector to filter by.
            labels: The labels of the service connector to filter by.
            secret_id: Filter by the id of the secret that is referenced by the
                service connector.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of service connectors.
        """
        connector_filter_model = ServiceConnectorFilter(
            page=page,
            size=size,
            sort_by=sort_by,
            logical_operator=logical_operator,
            workspace_id=workspace_id or self.active_workspace.id,
            user_id=user_id,
            name=name,
            connector_type=connector_type,
            auth_method=auth_method,
            resource_type=resource_type,
            resource_id=resource_id,
            id=id,
            created=created,
            updated=updated,
            labels=labels,
            secret_id=secret_id,
        )
        connector_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_service_connectors(
            filter_model=connector_filter_model,
            hydrate=hydrate,
        )

    def update_service_connector(
        self,
        name_id_or_prefix: Union[UUID, str],
        name: Optional[str] = None,
        auth_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        configuration: Optional[Dict[str, str]] = None,
        resource_id: Optional[str] = None,
        description: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        expires_skew_tolerance: Optional[int] = None,
        expiration_seconds: Optional[int] = None,
        labels: Optional[Dict[str, Optional[str]]] = None,
        verify: bool = True,
        list_resources: bool = True,
        update: bool = True,
    ) -> Tuple[
        Optional[
            Union[
                ServiceConnectorResponse,
                ServiceConnectorUpdate,
            ]
        ],
        Optional[ServiceConnectorResourcesModel],
    ]:
        """Validate and/or register an updated service connector.

        If the `resource_type`, `resource_id` and `expiration_seconds`
        parameters are set to their "empty" values (empty string for resource
        type and resource ID, 0 for expiration seconds), the existing values
        will be removed from the service connector. Setting them to None or
        omitting them will not affect the existing values.

        If supplied, the `configuration` parameter is a full replacement of the
        existing configuration rather than a partial update.

        Labels can be updated or removed by setting the label value to None.

        Args:
            name_id_or_prefix: The name, id or prefix of the service connector
                to update.
            name: The new name of the service connector.
            auth_method: The new authentication method of the service connector.
            resource_type: The new resource type for the service connector.
                If set to the empty string, the existing resource type will be
                removed.
            configuration: The new configuration of the service connector. If
                set, this needs to be a full replacement of the existing
                configuration rather than a partial update.
            resource_id: The new resource id of the service connector.
                If set to the empty string, the existing resource ID will be
                removed.
            description: The description of the service connector.
            expires_at: The new UTC expiration time of the service connector.
            expires_skew_tolerance: The allowed expiration skew for the service
                connector credentials.
            expiration_seconds: The expiration time of the service connector.
                If set to 0, the existing expiration time will be removed.
            labels: The service connector to update or remove. If a label value
                is set to None, the label will be removed.
            verify: Whether to verify that the service connector configuration
                and credentials can be used to gain access to the resource.
            list_resources: Whether to also list the resources that the service
                connector can give access to (if verify is True).
            update: Whether to update the service connector or not.

        Returns:
            The model of the registered service connector and the resources
            that the service connector can give access to (if verify is True).

        Raises:
            AuthorizationException: If the service connector verification
                fails due to invalid credentials or insufficient permissions.
        """
        from zenml.service_connectors.service_connector_registry import (
            service_connector_registry,
        )

        connector_model = self.get_service_connector(
            name_id_or_prefix,
            allow_name_prefix_match=False,
            load_secrets=True,
        )

        connector_instance: Optional[ServiceConnector] = None
        connector_resources: Optional[ServiceConnectorResourcesModel] = None

        if isinstance(connector_model.connector_type, str):
            connector = self.get_service_connector_type(
                connector_model.connector_type
            )
        else:
            connector = connector_model.connector_type

        resource_types: Optional[Union[str, List[str]]] = None
        if resource_type == "":
            resource_types = None
        elif resource_type is None:
            resource_types = connector_model.resource_types
        else:
            resource_types = resource_type

        if not resource_type and len(connector.resource_types) == 1:
            resource_types = connector.resource_types[0].resource_type

        if resource_id == "":
            resource_id = None
        elif resource_id is None:
            resource_id = connector_model.resource_id

        if expiration_seconds == 0:
            expiration_seconds = None
        elif expiration_seconds is None:
            expiration_seconds = connector_model.expiration_seconds

        connector_update = ServiceConnectorUpdate(
            name=name or connector_model.name,
            connector_type=connector.connector_type,
            description=description or connector_model.description,
            auth_method=auth_method or connector_model.auth_method,
            expires_at=expires_at,
            expires_skew_tolerance=expires_skew_tolerance,
            expiration_seconds=expiration_seconds,
        )

        # Validate and configure the resources
        if configuration is not None:
            # The supplied configuration is a drop-in replacement for the
            # existing configuration and secrets
            connector_update.validate_and_configure_resources(
                connector_type=connector,
                resource_types=resource_types,
                resource_id=resource_id,
                configuration=configuration,
            )
        else:
            connector_update.validate_and_configure_resources(
                connector_type=connector,
                resource_types=resource_types,
                resource_id=resource_id,
                configuration=connector_model.configuration,
                secrets=connector_model.secrets,
            )

        # Add the labels
        if labels is not None:
            # Apply the new label values, but don't keep any labels that
            # have been set to None in the update
            connector_update.labels = {
                **{
                    label: value
                    for label, value in connector_model.labels.items()
                    if label not in labels
                },
                **{
                    label: value
                    for label, value in labels.items()
                    if value is not None
                },
            }
        else:
            connector_update.labels = connector_model.labels

        if verify:
            # Prefer to verify the connector config server-side if the
            # implementation, if available there, because it ensures
            # that the connector can be shared with other users or used
            # from other machines and because some auth methods rely on the
            # server-side authentication environment

            # Convert the update model to a request model for validation
            connector_request_dict = connector_update.model_dump()
            connector_request_dict.update(
                user=self.active_user.id,
                workspace=self.active_workspace.id,
            )
            connector_request = ServiceConnectorRequest.model_validate(
                connector_request_dict
            )

            if connector.remote:
                connector_resources = (
                    self.zen_store.verify_service_connector_config(
                        service_connector=connector_request,
                        list_resources=list_resources,
                    )
                )
            else:
                connector_instance = (
                    service_connector_registry.instantiate_connector(
                        model=connector_request,
                    )
                )
                connector_resources = connector_instance.verify(
                    list_resources=list_resources
                )

            if connector_resources.error:
                raise AuthorizationException(connector_resources.error)

            # For resource types that don't support multi-instances, it's
            # better to save the default resource ID in the connector, if
            # available. Otherwise, we'll need to instantiate the connector
            # again to get the default resource ID.
            connector_update.resource_id = (
                connector_update.resource_id
                or connector_resources.get_default_resource_id()
            )

        if not update:
            return connector_update, connector_resources

        # Update the model
        connector_response = self.zen_store.update_service_connector(
            service_connector_id=connector_model.id,
            update=connector_update,
        )

        if connector_resources:
            connector_resources.id = connector_response.id
            connector_resources.name = connector_response.name
            connector_resources.connector_type = (
                connector_response.connector_type
            )

        return connector_response, connector_resources

    def delete_service_connector(
        self,
        name_id_or_prefix: Union[str, UUID],
    ) -> None:
        """Deletes a registered service connector.

        Args:
            name_id_or_prefix: The ID or name of the service connector to delete.
        """
        service_connector = self.get_service_connector(
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
        )

        self.zen_store.delete_service_connector(
            service_connector_id=service_connector.id
        )
        logger.info(
            "Removed service connector (type: %s) with name '%s'.",
            service_connector.type,
            service_connector.name,
        )

    def verify_service_connector(
        self,
        name_id_or_prefix: Union[UUID, str],
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        list_resources: bool = True,
    ) -> "ServiceConnectorResourcesModel":
        """Verifies if a service connector has access to one or more resources.

        Args:
            name_id_or_prefix: The name, id or prefix of the service connector
                to verify.
            resource_type: The type of the resource for which to verify access.
                If not provided, the resource type from the service connector
                configuration will be used.
            resource_id: The ID of the resource for which to verify access. If
                not provided, the resource ID from the service connector
                configuration will be used.
            list_resources: Whether to list the resources that the service
                connector has access to.

        Returns:
            The list of resources that the service connector has access to,
            scoped to the supplied resource type and ID, if provided.

        Raises:
            AuthorizationException: If the service connector does not have
                access to the resources.
        """
        from zenml.service_connectors.service_connector_registry import (
            service_connector_registry,
        )

        # Get the service connector model
        service_connector = self.get_service_connector(
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
        )

        connector_type = self.get_service_connector_type(
            service_connector.type
        )

        # Prefer to verify the connector config server-side if the
        # implementation if available there, because it ensures
        # that the connector can be shared with other users or used
        # from other machines and because some auth methods rely on the
        # server-side authentication environment
        if connector_type.remote:
            connector_resources = self.zen_store.verify_service_connector(
                service_connector_id=service_connector.id,
                resource_type=resource_type,
                resource_id=resource_id,
                list_resources=list_resources,
            )
        else:
            connector_instance = (
                service_connector_registry.instantiate_connector(
                    model=service_connector
                )
            )
            connector_resources = connector_instance.verify(
                resource_type=resource_type,
                resource_id=resource_id,
                list_resources=list_resources,
            )

        if connector_resources.error:
            raise AuthorizationException(connector_resources.error)

        return connector_resources

    def login_service_connector(
        self,
        name_id_or_prefix: Union[UUID, str],
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> "ServiceConnector":
        """Use a service connector to authenticate a local client/SDK.

        Args:
            name_id_or_prefix: The name, id or prefix of the service connector
                to use.
            resource_type: The type of the resource to connect to. If not
                provided, the resource type from the service connector
                configuration will be used.
            resource_id: The ID of a particular resource instance to configure
                the local client to connect to. If the connector instance is
                already configured with a resource ID that is not the same or
                equivalent to the one requested, a `ValueError` exception is
                raised. May be omitted for connectors and resource types that do
                not support multiple resource instances.
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Returns:
            The service connector client instance that was used to configure the
            local client.
        """
        connector_client = self.get_service_connector_client(
            name_id_or_prefix=name_id_or_prefix,
            resource_type=resource_type,
            resource_id=resource_id,
            verify=False,
        )

        connector_client.configure_local_client(
            **kwargs,
        )

        return connector_client

    def get_service_connector_client(
        self,
        name_id_or_prefix: Union[UUID, str],
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        verify: bool = False,
    ) -> "ServiceConnector":
        """Get the client side of a service connector instance to use with a local client.

        Args:
            name_id_or_prefix: The name, id or prefix of the service connector
                to use.
            resource_type: The type of the resource to connect to. If not
                provided, the resource type from the service connector
                configuration will be used.
            resource_id: The ID of a particular resource instance to configure
                the local client to connect to. If the connector instance is
                already configured with a resource ID that is not the same or
                equivalent to the one requested, a `ValueError` exception is
                raised. May be omitted for connectors and resource types that do
                not support multiple resource instances.
            verify: Whether to verify that the service connector configuration
                and credentials can be used to gain access to the resource.

        Returns:
            The client side of the indicated service connector instance that can
            be used to connect to the resource locally.
        """
        from zenml.service_connectors.service_connector_registry import (
            service_connector_registry,
        )

        # Get the service connector model
        service_connector = self.get_service_connector(
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
        )

        connector_type = self.get_service_connector_type(
            service_connector.type
        )

        # Prefer to fetch the connector client from the server if the
        # implementation if available there, because some auth methods rely on
        # the server-side authentication environment
        if connector_type.remote:
            connector_client_model = (
                self.zen_store.get_service_connector_client(
                    service_connector_id=service_connector.id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                )
            )

            connector_client = (
                service_connector_registry.instantiate_connector(
                    model=connector_client_model
                )
            )

            if verify:
                # Verify the connector client on the local machine, because the
                # server-side implementation may not be able to do so
                connector_client.verify()
        else:
            connector_instance = (
                service_connector_registry.instantiate_connector(
                    model=service_connector
                )
            )

            # Fetch the connector client
            connector_client = connector_instance.get_connector_client(
                resource_type=resource_type,
                resource_id=resource_id,
            )

        return connector_client

    def list_service_connector_resources(
        self,
        connector_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> List[ServiceConnectorResourcesModel]:
        """List resources that can be accessed by service connectors.

        Args:
            connector_type: The type of service connector to filter by.
            resource_type: The type of resource to filter by.
            resource_id: The ID of a particular resource instance to filter by.

        Returns:
            The matching list of resources that available service
            connectors have access to.
        """
        return self.zen_store.list_service_connector_resources(
            workspace_name_or_id=self.active_workspace.id,
            connector_type=connector_type,
            resource_type=resource_type,
            resource_id=resource_id,
        )

    def list_service_connector_types(
        self,
        connector_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        auth_method: Optional[str] = None,
    ) -> List[ServiceConnectorTypeModel]:
        """Get a list of service connector types.

        Args:
            connector_type: Filter by connector type.
            resource_type: Filter by resource type.
            auth_method: Filter by authentication method.

        Returns:
            List of service connector types.
        """
        return self.zen_store.list_service_connector_types(
            connector_type=connector_type,
            resource_type=resource_type,
            auth_method=auth_method,
        )

    def get_service_connector_type(
        self,
        connector_type: str,
    ) -> ServiceConnectorTypeModel:
        """Returns the requested service connector type.

        Args:
            connector_type: the service connector type identifier.

        Returns:
            The requested service connector type.
        """
        return self.zen_store.get_service_connector_type(
            connector_type=connector_type,
        )

    #########
    # Model
    #########

    def create_model(
        self,
        name: str,
        license: Optional[str] = None,
        description: Optional[str] = None,
        audience: Optional[str] = None,
        use_cases: Optional[str] = None,
        limitations: Optional[str] = None,
        trade_offs: Optional[str] = None,
        ethics: Optional[str] = None,
        tags: Optional[List[str]] = None,
        save_models_to_registry: bool = True,
    ) -> ModelResponse:
        """Creates a new model in Model Control Plane.

        Args:
            name: The name of the model.
            license: The license under which the model is created.
            description: The description of the model.
            audience: The target audience of the model.
            use_cases: The use cases of the model.
            limitations: The known limitations of the model.
            trade_offs: The tradeoffs of the model.
            ethics: The ethical implications of the model.
            tags: Tags associated with the model.
            save_models_to_registry: Whether to save the model to the
                registry.

        Returns:
            The newly created model.
        """
        return self.zen_store.create_model(
            model=ModelRequest(
                name=name,
                license=license,
                description=description,
                audience=audience,
                use_cases=use_cases,
                limitations=limitations,
                trade_offs=trade_offs,
                ethics=ethics,
                tags=tags,
                user=self.active_user.id,
                workspace=self.active_workspace.id,
                save_models_to_registry=save_models_to_registry,
            )
        )

    def delete_model(self, model_name_or_id: Union[str, UUID]) -> None:
        """Deletes a model from Model Control Plane.

        Args:
            model_name_or_id: name or id of the model to be deleted.
        """
        self.zen_store.delete_model(model_name_or_id=model_name_or_id)

    def update_model(
        self,
        model_name_or_id: Union[str, UUID],
        name: Optional[str] = None,
        license: Optional[str] = None,
        description: Optional[str] = None,
        audience: Optional[str] = None,
        use_cases: Optional[str] = None,
        limitations: Optional[str] = None,
        trade_offs: Optional[str] = None,
        ethics: Optional[str] = None,
        add_tags: Optional[List[str]] = None,
        remove_tags: Optional[List[str]] = None,
        save_models_to_registry: Optional[bool] = None,
    ) -> ModelResponse:
        """Updates an existing model in Model Control Plane.

        Args:
            model_name_or_id: name or id of the model to be deleted.
            name: The name of the model.
            license: The license under which the model is created.
            description: The description of the model.
            audience: The target audience of the model.
            use_cases: The use cases of the model.
            limitations: The known limitations of the model.
            trade_offs: The tradeoffs of the model.
            ethics: The ethical implications of the model.
            add_tags: Tags to add to the model.
            remove_tags: Tags to remove from to the model.
            save_models_to_registry: Whether to save the model to the
                registry.

        Returns:
            The updated model.
        """
        if not is_valid_uuid(model_name_or_id):
            model_name_or_id = self.zen_store.get_model(model_name_or_id).id
        return self.zen_store.update_model(
            model_id=model_name_or_id,  # type:ignore[arg-type]
            model_update=ModelUpdate(
                name=name,
                license=license,
                description=description,
                audience=audience,
                use_cases=use_cases,
                limitations=limitations,
                trade_offs=trade_offs,
                ethics=ethics,
                add_tags=add_tags,
                remove_tags=remove_tags,
                save_models_to_registry=save_models_to_registry,
            ),
        )

    def get_model(
        self,
        model_name_or_id: Union[str, UUID],
        hydrate: bool = True,
    ) -> ModelResponse:
        """Get an existing model from Model Control Plane.

        Args:
            model_name_or_id: name or id of the model to be retrieved.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The model of interest.
        """
        if cll := client_lazy_loader(
            "get_model", model_name_or_id=model_name_or_id, hydrate=hydrate
        ):
            return cll  # type: ignore[return-value]
        return self.zen_store.get_model(
            model_name_or_id=model_name_or_id,
            hydrate=hydrate,
        )

    def list_models(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        name: Optional[str] = None,
        user: Optional[Union[UUID, str]] = None,
        hydrate: bool = False,
        tag: Optional[str] = None,
    ) -> Page[ModelResponse]:
        """Get models by filter from Model Control Plane.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            name: The name of the model to filter by.
            user: Filter by user name/ID.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            tag: The tag of the model to filter by.

        Returns:
            A page object with all models.
        """
        filter = ModelFilter(
            name=name,
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            created=created,
            updated=updated,
            tag=tag,
            user=user,
        )

        return self.zen_store.list_models(
            model_filter_model=filter, hydrate=hydrate
        )

    #################
    # Model Versions
    #################

    def create_model_version(
        self,
        model_name_or_id: Union[str, UUID],
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> ModelVersionResponse:
        """Creates a new model version in Model Control Plane.

        Args:
            model_name_or_id: the name or id of the model to create model
                version in.
            name: the name of the Model Version to be created.
            description: the description of the Model Version to be created.
            tags: Tags associated with the model.

        Returns:
            The newly created model version.
        """
        if not is_valid_uuid(model_name_or_id):
            model_name_or_id = self.get_model(model_name_or_id).id
        return self.zen_store.create_model_version(
            model_version=ModelVersionRequest(
                name=name,
                description=description,
                user=self.active_user.id,
                workspace=self.active_workspace.id,
                model=model_name_or_id,
                tags=tags,
            )
        )

    def delete_model_version(
        self,
        model_version_id: UUID,
    ) -> None:
        """Deletes a model version from Model Control Plane.

        Args:
            model_version_id: Id of the model version to be deleted.
        """
        self.zen_store.delete_model_version(
            model_version_id=model_version_id,
        )

    def get_model_version(
        self,
        model_name_or_id: Optional[Union[str, UUID]] = None,
        model_version_name_or_number_or_id: Optional[
            Union[str, int, ModelStages, UUID]
        ] = None,
        hydrate: bool = True,
    ) -> ModelVersionResponse:
        """Get an existing model version from Model Control Plane.

        Args:
            model_name_or_id: name or id of the model containing the model
                version.
            model_version_name_or_number_or_id: name, id, stage or number of
                the model version to be retrieved. If skipped - latest version
                is retrieved.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The model version of interest.

        Raises:
            RuntimeError: In case method inputs don't adhere to restrictions.
            KeyError: In case no model version with the identifiers exists.
            ValueError: In case retrieval is attempted using non UUID model version
                identifier and no model identifier provided.
        """
        if (
            not is_valid_uuid(model_version_name_or_number_or_id)
            and model_name_or_id is None
        ):
            raise ValueError(
                "No model identifier provided and model version identifier "
                f"`{model_version_name_or_number_or_id}` is not a valid UUID."
            )
        if cll := client_lazy_loader(
            "get_model_version",
            model_name_or_id=model_name_or_id,
            model_version_name_or_number_or_id=model_version_name_or_number_or_id,
            hydrate=hydrate,
        ):
            return cll  # type: ignore[return-value]

        if model_version_name_or_number_or_id is None:
            model_version_name_or_number_or_id = ModelStages.LATEST

        if isinstance(model_version_name_or_number_or_id, UUID):
            return self.zen_store.get_model_version(
                model_version_id=model_version_name_or_number_or_id,
                hydrate=hydrate,
            )
        elif isinstance(model_version_name_or_number_or_id, int):
            model_versions = self.zen_store.list_model_versions(
                model_name_or_id=model_name_or_id,
                model_version_filter_model=ModelVersionFilter(
                    number=model_version_name_or_number_or_id,
                ),
                hydrate=hydrate,
            ).items
        elif isinstance(model_version_name_or_number_or_id, str):
            if model_version_name_or_number_or_id == ModelStages.LATEST:
                model_versions = self.zen_store.list_model_versions(
                    model_name_or_id=model_name_or_id,
                    model_version_filter_model=ModelVersionFilter(
                        sort_by=f"{SorterOps.DESCENDING}:number"
                    ),
                    hydrate=hydrate,
                ).items

                if len(model_versions) > 0:
                    model_versions = [model_versions[0]]
                else:
                    model_versions = []
            elif model_version_name_or_number_or_id in ModelStages.values():
                model_versions = self.zen_store.list_model_versions(
                    model_name_or_id=model_name_or_id,
                    model_version_filter_model=ModelVersionFilter(
                        stage=model_version_name_or_number_or_id
                    ),
                    hydrate=hydrate,
                ).items
            else:
                model_versions = self.zen_store.list_model_versions(
                    model_name_or_id=model_name_or_id,
                    model_version_filter_model=ModelVersionFilter(
                        name=model_version_name_or_number_or_id
                    ),
                    hydrate=hydrate,
                ).items
        else:
            raise RuntimeError(
                f"The model version identifier "
                f"`{model_version_name_or_number_or_id}` is not"
                f"of the correct type."
            )

        if len(model_versions) == 1:
            return model_versions[0]
        elif len(model_versions) == 0:
            raise KeyError(
                f"No model version found for model "
                f"`{model_name_or_id}` with version identifier "
                f"`{model_version_name_or_number_or_id}`."
            )
        else:
            raise RuntimeError(
                f"The model version identifier "
                f"`{model_version_name_or_number_or_id}` is not"
                f"unique for model `{model_name_or_id}`."
            )

    def list_model_versions(
        self,
        model_name_or_id: Optional[Union[str, UUID]] = None,
        sort_by: str = "number",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        name: Optional[str] = None,
        number: Optional[int] = None,
        stage: Optional[Union[str, ModelStages]] = None,
        user: Optional[Union[UUID, str]] = None,
        hydrate: bool = False,
        tag: Optional[str] = None,
    ) -> Page[ModelVersionResponse]:
        """Get model versions by filter from Model Control Plane.

        Args:
            model_name_or_id: name or id of the model containing the model
                version.
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            name: name or id of the model version.
            number: number of the model version.
            stage: stage of the model version.
            user: Filter by user name/ID.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            tag: The tag to filter by.

        Returns:
            A page object with all model versions.
        """
        model_version_filter_model = ModelVersionFilter(
            page=page,
            size=size,
            sort_by=sort_by,
            logical_operator=logical_operator,
            created=created,
            updated=updated,
            name=name,
            number=number,
            stage=stage,
            tag=tag,
            user=user,
        )

        return self.zen_store.list_model_versions(
            model_name_or_id=model_name_or_id,
            model_version_filter_model=model_version_filter_model,
            hydrate=hydrate,
        )

    def update_model_version(
        self,
        model_name_or_id: Union[str, UUID],
        version_name_or_id: Union[str, UUID],
        stage: Optional[Union[str, ModelStages]] = None,
        force: bool = False,
        name: Optional[str] = None,
        description: Optional[str] = None,
        add_tags: Optional[List[str]] = None,
        remove_tags: Optional[List[str]] = None,
    ) -> ModelVersionResponse:
        """Get all model versions by filter.

        Args:
            model_name_or_id: The name or ID of the model containing model version.
            version_name_or_id: The name or ID of model version to be updated.
            stage: Target model version stage to be set.
            force: Whether existing model version in target stage should be
                silently archived or an error should be raised.
            name: Target model version name to be set.
            description: Target model version description to be set.
            add_tags: Tags to add to the model version.
            remove_tags: Tags to remove from to the model version.

        Returns:
            An updated model version.
        """
        if not is_valid_uuid(model_name_or_id):
            model_name_or_id = self.get_model(model_name_or_id).id
        if not is_valid_uuid(version_name_or_id):
            version_name_or_id = self.get_model_version(
                model_name_or_id, version_name_or_id
            ).id

        return self.zen_store.update_model_version(
            model_version_id=version_name_or_id,  # type:ignore[arg-type]
            model_version_update_model=ModelVersionUpdate(
                model=model_name_or_id,
                stage=stage,
                force=force,
                name=name,
                description=description,
                add_tags=add_tags,
                remove_tags=remove_tags,
            ),
        )

    #################################################
    # Model Versions Artifacts
    #################################################

    def list_model_version_artifact_links(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        workspace_id: Optional[Union[UUID, str]] = None,
        user_id: Optional[Union[UUID, str]] = None,
        model_id: Optional[Union[UUID, str]] = None,
        model_version_id: Optional[Union[UUID, str]] = None,
        artifact_version_id: Optional[Union[UUID, str]] = None,
        artifact_name: Optional[str] = None,
        only_data_artifacts: Optional[bool] = None,
        only_model_artifacts: Optional[bool] = None,
        only_deployment_artifacts: Optional[bool] = None,
        has_custom_name: Optional[bool] = None,
        user: Optional[Union[UUID, str]] = None,
        hydrate: bool = False,
    ) -> Page[ModelVersionArtifactResponse]:
        """Get model version to artifact links by filter in Model Control Plane.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            workspace_id: Use the workspace id for filtering
            user_id: Use the user id for filtering
            model_id: Use the model id for filtering
            model_version_id: Use the model version id for filtering
            artifact_version_id: Use the artifact id for filtering
            artifact_name: Use the artifact name for filtering
            only_data_artifacts: Use to filter by data artifacts
            only_model_artifacts: Use to filter by model artifacts
            only_deployment_artifacts: Use to filter by deployment artifacts
            has_custom_name: Filter artifacts with/without custom names.
            user: Filter by user name/ID.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all model version to artifact links.
        """
        return self.zen_store.list_model_version_artifact_links(
            ModelVersionArtifactFilter(
                sort_by=sort_by,
                logical_operator=logical_operator,
                page=page,
                size=size,
                created=created,
                updated=updated,
                workspace_id=workspace_id,
                user_id=user_id,
                model_id=model_id,
                model_version_id=model_version_id,
                artifact_version_id=artifact_version_id,
                artifact_name=artifact_name,
                only_data_artifacts=only_data_artifacts,
                only_model_artifacts=only_model_artifacts,
                only_deployment_artifacts=only_deployment_artifacts,
                has_custom_name=has_custom_name,
                user=user,
            ),
            hydrate=hydrate,
        )

    def delete_model_version_artifact_link(
        self, model_version_id: UUID, artifact_version_id: UUID
    ) -> None:
        """Delete model version to artifact link in Model Control Plane.

        Args:
            model_version_id: The id of the model version holding the link.
            artifact_version_id: The id of the artifact version to be deleted.

        Raises:
            RuntimeError: If more than one artifact link is found for given filters.
        """
        artifact_links = self.list_model_version_artifact_links(
            model_version_id=model_version_id,
            artifact_version_id=artifact_version_id,
        )
        if artifact_links.items:
            if artifact_links.total > 1:
                raise RuntimeError(
                    "More than one artifact link found for give model version "
                    f"`{model_version_id}` and artifact version "
                    f"`{artifact_version_id}`. This should not be happening and "
                    "might indicate a corrupted state of your ZenML database. "
                    "Please seek support via Community Slack."
                )
            self.zen_store.delete_model_version_artifact_link(
                model_version_id=model_version_id,
                model_version_artifact_link_name_or_id=artifact_links.items[
                    0
                ].id,
            )

    def delete_all_model_version_artifact_links(
        self, model_version_id: UUID, only_links: bool
    ) -> None:
        """Delete all model version to artifact links in Model Control Plane.

        Args:
            model_version_id: The id of the model version holding the link.
            only_links: If true, only delete the link to the artifact.
        """
        self.zen_store.delete_all_model_version_artifact_links(
            model_version_id, only_links
        )

    #################################################
    # Model Versions Pipeline Runs
    #
    # Only view capabilities are exposed via client.
    #################################################

    def list_model_version_pipeline_run_links(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        workspace_id: Optional[Union[UUID, str]] = None,
        user_id: Optional[Union[UUID, str]] = None,
        model_id: Optional[Union[UUID, str]] = None,
        model_version_id: Optional[Union[UUID, str]] = None,
        pipeline_run_id: Optional[Union[UUID, str]] = None,
        pipeline_run_name: Optional[str] = None,
        user: Optional[Union[UUID, str]] = None,
        hydrate: bool = False,
    ) -> Page[ModelVersionPipelineRunResponse]:
        """Get all model version to pipeline run links by filter.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            workspace_id: Use the workspace id for filtering
            user_id: Use the user id for filtering
            model_id: Use the model id for filtering
            model_version_id: Use the model version id for filtering
            pipeline_run_id: Use the pipeline run id for filtering
            pipeline_run_name: Use the pipeline run name for filtering
            user: Filter by user name or ID.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response

        Returns:
            A page of all model version to pipeline run links.
        """
        return self.zen_store.list_model_version_pipeline_run_links(
            ModelVersionPipelineRunFilter(
                sort_by=sort_by,
                logical_operator=logical_operator,
                page=page,
                size=size,
                created=created,
                updated=updated,
                workspace_id=workspace_id,
                user_id=user_id,
                model_id=model_id,
                model_version_id=model_version_id,
                pipeline_run_id=pipeline_run_id,
                pipeline_run_name=pipeline_run_name,
                user=user,
            ),
            hydrate=hydrate,
        )

    # --------------------------- Authorized Devices ---------------------------

    def list_authorized_devices(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        expires: Optional[Union[datetime, str]] = None,
        client_id: Union[UUID, str, None] = None,
        status: Union[OAuthDeviceStatus, str, None] = None,
        trusted_device: Union[bool, str, None] = None,
        failed_auth_attempts: Union[int, str, None] = None,
        last_login: Optional[Union[datetime, str, None]] = None,
        hydrate: bool = False,
    ) -> Page[OAuthDeviceResponse]:
        """List all authorized devices.

        Args:
            sort_by: The column to sort by.
            page: The page of items.
            size: The maximum size of all pages.
            logical_operator: Which logical operator to use [and, or].
            id: Use the id of the code repository to filter by.
            created: Use to filter by time of creation.
            updated: Use the last updated date for filtering.
            expires: Use the expiration date for filtering.
            client_id: Use the client id for filtering.
            status: Use the status for filtering.
            trusted_device: Use the trusted device flag for filtering.
            failed_auth_attempts: Use the failed auth attempts for filtering.
            last_login: Use the last login date for filtering.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of authorized devices matching the filter.
        """
        filter_model = OAuthDeviceFilter(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            created=created,
            updated=updated,
            expires=expires,
            client_id=client_id,
            status=status,
            trusted_device=trusted_device,
            failed_auth_attempts=failed_auth_attempts,
            last_login=last_login,
        )
        return self.zen_store.list_authorized_devices(
            filter_model=filter_model,
            hydrate=hydrate,
        )

    def get_authorized_device(
        self,
        id_or_prefix: Union[UUID, str],
        allow_id_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> OAuthDeviceResponse:
        """Get an authorized device by id or prefix.

        Args:
            id_or_prefix: The ID or ID prefix of the authorized device.
            allow_id_prefix_match: If True, allow matching by ID prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The requested authorized device.

        Raises:
            KeyError: If no authorized device is found with the given ID or
                prefix.
        """
        if isinstance(id_or_prefix, str):
            try:
                id_or_prefix = UUID(id_or_prefix)
            except ValueError:
                if not allow_id_prefix_match:
                    raise KeyError(
                        f"No authorized device found with id or prefix "
                        f"'{id_or_prefix}'."
                    )
        if isinstance(id_or_prefix, UUID):
            return self.zen_store.get_authorized_device(
                id_or_prefix, hydrate=hydrate
            )
        return self._get_entity_by_prefix(
            get_method=self.zen_store.get_authorized_device,
            list_method=self.list_authorized_devices,
            partial_id_or_name=id_or_prefix,
            allow_name_prefix_match=False,
            hydrate=hydrate,
        )

    def update_authorized_device(
        self,
        id_or_prefix: Union[UUID, str],
        locked: Optional[bool] = None,
    ) -> OAuthDeviceResponse:
        """Update an authorized device.

        Args:
            id_or_prefix: The ID or ID prefix of the authorized device.
            locked: Whether to lock or unlock the authorized device.

        Returns:
            The updated authorized device.
        """
        device = self.get_authorized_device(
            id_or_prefix=id_or_prefix, allow_id_prefix_match=False
        )
        return self.zen_store.update_authorized_device(
            device_id=device.id,
            update=OAuthDeviceUpdate(
                locked=locked,
            ),
        )

    def delete_authorized_device(
        self,
        id_or_prefix: Union[str, UUID],
    ) -> None:
        """Delete an authorized device.

        Args:
            id_or_prefix: The ID or ID prefix of the authorized device.
        """
        device = self.get_authorized_device(
            id_or_prefix=id_or_prefix,
            allow_id_prefix_match=False,
        )
        self.zen_store.delete_authorized_device(device.id)

    # --------------------------- Trigger Executions ---------------------------

    def get_trigger_execution(
        self,
        trigger_execution_id: UUID,
        hydrate: bool = True,
    ) -> TriggerExecutionResponse:
        """Get an trigger execution by ID.

        Args:
            trigger_execution_id: The ID of the trigger execution to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The trigger execution.
        """
        return self.zen_store.get_trigger_execution(
            trigger_execution_id=trigger_execution_id, hydrate=hydrate
        )

    def list_trigger_executions(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        trigger_id: Optional[UUID] = None,
        hydrate: bool = False,
    ) -> Page[TriggerExecutionResponse]:
        """List all trigger executions matching the given filter criteria.

        Args:
            sort_by: The column to sort by.
            page: The page of items.
            size: The maximum size of all pages.
            logical_operator: Which logical operator to use [and, or].
            trigger_id: ID of the trigger to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all trigger executions matching the filter criteria.
        """
        filter_model = TriggerExecutionFilter(
            trigger_id=trigger_id,
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
        )
        filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_trigger_executions(
            trigger_execution_filter_model=filter_model, hydrate=hydrate
        )

    def delete_trigger_execution(self, trigger_execution_id: UUID) -> None:
        """Delete a trigger execution.

        Args:
            trigger_execution_id: The ID of the trigger execution to delete.
        """
        self.zen_store.delete_trigger_execution(
            trigger_execution_id=trigger_execution_id
        )

    # ---- utility prefix matching get functions -----

    def _get_entity_by_id_or_name_or_prefix(
        self,
        get_method: Callable[..., AnyResponse],
        list_method: Callable[..., Page[AnyResponse]],
        name_id_or_prefix: Union[str, UUID],
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> AnyResponse:
        """Fetches an entity using the id, name, or partial id/name.

        Args:
            get_method: The method to use to fetch the entity by id.
            list_method: The method to use to fetch all entities.
            name_id_or_prefix: The id, name or partial id of the entity to
                fetch.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The entity with the given name, id or partial id.

        Raises:
            ZenKeyError: If there is more than one entity with that name
                or id prefix.
        """
        from zenml.utils.uuid_utils import is_valid_uuid

        entity_label = get_method.__name__.replace("get_", "") + "s"

        # First interpret as full UUID
        if is_valid_uuid(name_id_or_prefix):
            return get_method(name_id_or_prefix, hydrate=hydrate)

        # If not a UUID, try to find by name
        assert not isinstance(name_id_or_prefix, UUID)
        entity = list_method(
            name=f"equals:{name_id_or_prefix}",
            hydrate=hydrate,
        )

        # If only a single entity is found, return it
        if entity.total == 1:
            return entity.items[0]

        # If still no match, try with prefix now
        if entity.total == 0:
            return self._get_entity_by_prefix(
                get_method=get_method,
                list_method=list_method,
                partial_id_or_name=name_id_or_prefix,
                allow_name_prefix_match=allow_name_prefix_match,
                hydrate=hydrate,
            )

        # If more than one entity with the same name is found, raise an error.
        formatted_entity_items = [
            f"- {item.name}: (id: {item.id})\n"
            if hasattr(item, "name")
            else f"- {item.id}\n"
            for item in entity.items
        ]
        raise ZenKeyError(
            f"{entity.total} {entity_label} have been found that have "
            f"a name that matches the provided "
            f"string '{name_id_or_prefix}':\n"
            f"{formatted_entity_items}.\n"
            f"Please use the id to uniquely identify "
            f"only one of the {entity_label}s."
        )

    def _get_entity_version_by_id_or_name_or_prefix(
        self,
        get_method: Callable[..., AnyResponse],
        list_method: Callable[..., Page[AnyResponse]],
        name_id_or_prefix: Union[str, UUID],
        version: Optional[str],
        hydrate: bool = True,
    ) -> "AnyResponse":
        from zenml.utils.uuid_utils import is_valid_uuid

        entity_label = get_method.__name__.replace("get_", "") + "s"

        if is_valid_uuid(name_id_or_prefix):
            if version:
                logger.warning(
                    "You specified both an ID as well as a version of the "
                    f"{entity_label}. Ignoring the version and fetching the "
                    f"{entity_label} by ID."
                )
            if not isinstance(name_id_or_prefix, UUID):
                name_id_or_prefix = UUID(name_id_or_prefix, version=4)

            return get_method(name_id_or_prefix, hydrate=hydrate)

        assert not isinstance(name_id_or_prefix, UUID)
        exact_name_matches = list_method(
            size=1,
            sort_by="desc:created",
            name=name_id_or_prefix,
            version=version,
            hydrate=hydrate,
        )

        if len(exact_name_matches) == 1:
            # If the name matches exactly, use the explicitly specified version
            # or fallback to the latest if not given
            return exact_name_matches.items[0]

        partial_id_matches = list_method(
            id=f"startswith:{name_id_or_prefix}",
            hydrate=hydrate,
        )
        if partial_id_matches.total == 1:
            if version:
                logger.warning(
                    "You specified both a partial ID as well as a version of "
                    f"the {entity_label}. Ignoring the version and fetching "
                    f"the {entity_label} by partial ID."
                )
            return partial_id_matches[0]
        elif partial_id_matches.total == 0:
            raise KeyError(
                f"No {entity_label} found for name, ID or prefix "
                f"{name_id_or_prefix}."
            )
        else:
            raise ZenKeyError(
                f"{partial_id_matches.total} {entity_label} have been found "
                "that have an id prefix that matches the provided string "
                f"'{name_id_or_prefix}':\n"
                f"{partial_id_matches.items}.\n"
                f"Please provide more characters to uniquely identify "
                f"only one of the {entity_label}s."
            )

    def _get_entity_by_prefix(
        self,
        get_method: Callable[..., AnyResponse],
        list_method: Callable[..., Page[AnyResponse]],
        partial_id_or_name: str,
        allow_name_prefix_match: bool,
        hydrate: bool = True,
    ) -> AnyResponse:
        """Fetches an entity using a partial ID or name.

        Args:
            get_method: The method to use to fetch the entity by id.
            list_method: The method to use to fetch all entities.
            partial_id_or_name: The partial ID or name of the entity to fetch.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The entity with the given partial ID or name.

        Raises:
            KeyError: If no entity with the given partial ID or name is found.
            ZenKeyError: If there is more than one entity with that partial ID
                or name.
        """
        list_method_args: Dict[str, Any] = {
            "logical_operator": LogicalOperators.OR,
            "id": f"startswith:{partial_id_or_name}",
            "hydrate": hydrate,
        }
        if allow_name_prefix_match:
            list_method_args["name"] = f"startswith:{partial_id_or_name}"

        entity = list_method(**list_method_args)

        # If only a single entity is found, return it.
        if entity.total == 1:
            return entity.items[0]

        irregular_plurals = {"code_repository": "code_repositories"}
        entity_label = irregular_plurals.get(
            get_method.__name__.replace("get_", ""),
            get_method.__name__.replace("get_", "") + "s",
        )

        prefix_description = (
            "a name/ID prefix" if allow_name_prefix_match else "an ID prefix"
        )
        # If no entity is found, raise an error.
        if entity.total == 0:
            raise KeyError(
                f"No {entity_label} have been found that have "
                f"{prefix_description} that matches the provided string "
                f"'{partial_id_or_name}'."
            )

        # If more than one entity is found, raise an error.
        ambiguous_entities: List[str] = []
        for model in entity.items:
            model_name = getattr(model, "name", None)
            if model_name:
                ambiguous_entities.append(f"{model_name}: {model.id}")
            else:
                ambiguous_entities.append(str(model.id))
        raise ZenKeyError(
            f"{entity.total} {entity_label} have been found that have "
            f"{prefix_description} that matches the provided "
            f"string '{partial_id_or_name}':\n"
            f"{ambiguous_entities}.\n"
            f"Please provide more characters to uniquely identify "
            f"only one of the {entity_label}s."
        )

    # ---------------------------- Service Accounts ----------------------------

    def create_service_account(
        self,
        name: str,
        description: str = "",
    ) -> ServiceAccountResponse:
        """Create a new service account.

        Args:
            name: The name of the service account.
            description: The description of the service account.

        Returns:
            The created service account.
        """
        service_account = ServiceAccountRequest(
            name=name, description=description, active=True
        )
        created_service_account = self.zen_store.create_service_account(
            service_account=service_account
        )

        return created_service_account

    def get_service_account(
        self,
        name_id_or_prefix: Union[str, UUID],
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> ServiceAccountResponse:
        """Gets a service account.

        Args:
            name_id_or_prefix: The name or ID of the service account.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The ServiceAccount
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_service_account,
            list_method=self.list_service_accounts,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            hydrate=hydrate,
        )

    def list_service_accounts(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        active: Optional[bool] = None,
        hydrate: bool = False,
    ) -> Page[ServiceAccountResponse]:
        """List all service accounts.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of stacks to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            name: Use the service account name for filtering
            description: Use the service account description for filtering
            active: Use the service account active status for filtering
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The list of service accounts matching the filter description.
        """
        return self.zen_store.list_service_accounts(
            ServiceAccountFilter(
                sort_by=sort_by,
                page=page,
                size=size,
                logical_operator=logical_operator,
                id=id,
                created=created,
                updated=updated,
                name=name,
                description=description,
                active=active,
            ),
            hydrate=hydrate,
        )

    def update_service_account(
        self,
        name_id_or_prefix: Union[str, UUID],
        updated_name: Optional[str] = None,
        description: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> ServiceAccountResponse:
        """Update a service account.

        Args:
            name_id_or_prefix: The name or ID of the service account to update.
            updated_name: The new name of the service account.
            description: The new description of the service account.
            active: The new active status of the service account.

        Returns:
            The updated service account.
        """
        service_account = self.get_service_account(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )
        service_account_update = ServiceAccountUpdate(
            name=updated_name,
            description=description,
            active=active,
        )

        return self.zen_store.update_service_account(
            service_account_name_or_id=service_account.id,
            service_account_update=service_account_update,
        )

    def delete_service_account(
        self,
        name_id_or_prefix: Union[str, UUID],
    ) -> None:
        """Delete a service account.

        Args:
            name_id_or_prefix: The name or ID of the service account to delete.
        """
        service_account = self.get_service_account(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )
        self.zen_store.delete_service_account(
            service_account_name_or_id=service_account.id
        )

    # -------------------------------- API Keys --------------------------------

    def create_api_key(
        self,
        service_account_name_id_or_prefix: Union[str, UUID],
        name: str,
        description: str = "",
        set_key: bool = False,
    ) -> APIKeyResponse:
        """Create a new API key and optionally set it as the active API key.

        Args:
            service_account_name_id_or_prefix: The name, ID or prefix of the
                service account to create the API key for.
            name: Name of the API key.
            description: The description of the API key.
            set_key: Whether to set the created API key as the active API key.

        Returns:
            The created API key.
        """
        service_account = self.get_service_account(
            name_id_or_prefix=service_account_name_id_or_prefix,
            allow_name_prefix_match=False,
        )
        request = APIKeyRequest(
            name=name,
            description=description,
        )
        api_key = self.zen_store.create_api_key(
            service_account_id=service_account.id, api_key=request
        )
        assert api_key.key is not None

        if set_key:
            self.set_api_key(key=api_key.key)

        return api_key

    def set_api_key(self, key: str) -> None:
        """Configure the client with an API key.

        Args:
            key: The API key to use.

        Raises:
            NotImplementedError: If the client is not connected to a ZenML
                server.
        """
        from zenml.zen_stores.rest_zen_store import RestZenStore

        zen_store = self.zen_store
        if not zen_store.TYPE == StoreType.REST:
            raise NotImplementedError(
                "API key configuration is only supported if connected to a "
                "ZenML server."
            )
        assert isinstance(zen_store, RestZenStore)
        zen_store.set_api_key(api_key=key)

    def list_api_keys(
        self,
        service_account_name_id_or_prefix: Union[str, UUID],
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        active: Optional[bool] = None,
        last_login: Optional[Union[datetime, str]] = None,
        last_rotated: Optional[Union[datetime, str]] = None,
        hydrate: bool = False,
    ) -> Page[APIKeyResponse]:
        """List all API keys.

        Args:
            service_account_name_id_or_prefix: The name, ID or prefix of the
                service account to list the API keys for.
            sort_by: The column to sort by.
            page: The page of items.
            size: The maximum size of all pages.
            logical_operator: Which logical operator to use [and, or].
            id: Use the id of the API key to filter by.
            created: Use to filter by time of creation.
            updated: Use the last updated date for filtering.
            name: The name of the API key to filter by.
            description: The description of the API key to filter by.
            active: Whether the API key is active or not.
            last_login: The last time the API key was used.
            last_rotated: The last time the API key was rotated.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of API keys matching the filter description.
        """
        service_account = self.get_service_account(
            name_id_or_prefix=service_account_name_id_or_prefix,
            allow_name_prefix_match=False,
        )
        filter_model = APIKeyFilter(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            created=created,
            updated=updated,
            name=name,
            description=description,
            active=active,
            last_login=last_login,
            last_rotated=last_rotated,
        )
        return self.zen_store.list_api_keys(
            service_account_id=service_account.id,
            filter_model=filter_model,
            hydrate=hydrate,
        )

    def get_api_key(
        self,
        service_account_name_id_or_prefix: Union[str, UUID],
        name_id_or_prefix: Union[str, UUID],
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> APIKeyResponse:
        """Get an API key by name, id or prefix.

        Args:
            service_account_name_id_or_prefix: The name, ID or prefix of the
                service account to get the API key for.
            name_id_or_prefix: The name, ID or ID prefix of the API key.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The API key.
        """
        service_account = self.get_service_account(
            name_id_or_prefix=service_account_name_id_or_prefix,
            allow_name_prefix_match=False,
        )

        def get_api_key_method(
            api_key_name_or_id: str, hydrate: bool = True
        ) -> APIKeyResponse:
            return self.zen_store.get_api_key(
                service_account_id=service_account.id,
                api_key_name_or_id=api_key_name_or_id,
                hydrate=hydrate,
            )

        def list_api_keys_method(
            hydrate: bool = True,
            **filter_args: Any,
        ) -> Page[APIKeyResponse]:
            return self.list_api_keys(
                service_account_name_id_or_prefix=service_account.id,
                hydrate=hydrate,
                **filter_args,
            )

        return self._get_entity_by_id_or_name_or_prefix(
            get_method=get_api_key_method,
            list_method=list_api_keys_method,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            hydrate=hydrate,
        )

    def update_api_key(
        self,
        service_account_name_id_or_prefix: Union[str, UUID],
        name_id_or_prefix: Union[UUID, str],
        name: Optional[str] = None,
        description: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> APIKeyResponse:
        """Update an API key.

        Args:
            service_account_name_id_or_prefix: The name, ID or prefix of the
                service account to update the API key for.
            name_id_or_prefix: Name, ID or prefix of the API key to update.
            name: New name of the API key.
            description: New description of the API key.
            active: Whether the API key is active or not.

        Returns:
            The updated API key.
        """
        api_key = self.get_api_key(
            service_account_name_id_or_prefix=service_account_name_id_or_prefix,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
        )
        update = APIKeyUpdate(
            name=name, description=description, active=active
        )
        return self.zen_store.update_api_key(
            service_account_id=api_key.service_account.id,
            api_key_name_or_id=api_key.id,
            api_key_update=update,
        )

    def rotate_api_key(
        self,
        service_account_name_id_or_prefix: Union[str, UUID],
        name_id_or_prefix: Union[UUID, str],
        retain_period_minutes: int = 0,
        set_key: bool = False,
    ) -> APIKeyResponse:
        """Rotate an API key.

        Args:
            service_account_name_id_or_prefix: The name, ID or prefix of the
                service account to rotate the API key for.
            name_id_or_prefix: Name, ID or prefix of the API key to update.
            retain_period_minutes: The number of minutes to retain the old API
                key for. If set to 0, the old API key will be invalidated.
            set_key: Whether to set the rotated API key as the active API key.

        Returns:
            The updated API key.
        """
        api_key = self.get_api_key(
            service_account_name_id_or_prefix=service_account_name_id_or_prefix,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
        )
        rotate_request = APIKeyRotateRequest(
            retain_period_minutes=retain_period_minutes
        )
        new_key = self.zen_store.rotate_api_key(
            service_account_id=api_key.service_account.id,
            api_key_name_or_id=api_key.id,
            rotate_request=rotate_request,
        )
        assert new_key.key is not None
        if set_key:
            self.set_api_key(key=new_key.key)

        return new_key

    def delete_api_key(
        self,
        service_account_name_id_or_prefix: Union[str, UUID],
        name_id_or_prefix: Union[str, UUID],
    ) -> None:
        """Delete an API key.

        Args:
            service_account_name_id_or_prefix: The name, ID or prefix of the
                service account to delete the API key for.
            name_id_or_prefix: The name, ID or prefix of the API key.
        """
        api_key = self.get_api_key(
            service_account_name_id_or_prefix=service_account_name_id_or_prefix,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
        )
        self.zen_store.delete_api_key(
            service_account_id=api_key.service_account.id,
            api_key_name_or_id=api_key.id,
        )

    #############################################
    # Tags
    #
    # Note: tag<>resource are not exposed and
    # can be accessed via relevant resources
    #############################################

    def create_tag(self, tag: TagRequest) -> TagResponse:
        """Creates a new tag.

        Args:
            tag: the Tag to be created.

        Returns:
            The newly created tag.
        """
        return self.zen_store.create_tag(tag=tag)

    def delete_tag(self, tag_name_or_id: Union[str, UUID]) -> None:
        """Deletes a tag.

        Args:
            tag_name_or_id: name or id of the tag to be deleted.
        """
        self.zen_store.delete_tag(tag_name_or_id=tag_name_or_id)

    def update_tag(
        self,
        tag_name_or_id: Union[str, UUID],
        tag_update_model: TagUpdate,
    ) -> TagResponse:
        """Updates an existing tag.

        Args:
            tag_name_or_id: name or UUID of the tag to be updated.
            tag_update_model: the tag to be updated.

        Returns:
            The updated tag.
        """
        return self.zen_store.update_tag(
            tag_name_or_id=tag_name_or_id, tag_update_model=tag_update_model
        )

    def get_tag(
        self, tag_name_or_id: Union[str, UUID], hydrate: bool = True
    ) -> TagResponse:
        """Get an existing tag.

        Args:
            tag_name_or_id: name or id of the model to be retrieved.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The tag of interest.
        """
        return self.zen_store.get_tag(
            tag_name_or_id=tag_name_or_id, hydrate=hydrate
        )

    def list_tags(
        self,
        tag_filter_model: TagFilter,
        hydrate: bool = False,
    ) -> Page[TagResponse]:
        """Get tags by filter.

        Args:
            tag_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all tags.
        """
        return self.zen_store.list_tags(
            tag_filter_model=tag_filter_model, hydrate=hydrate
        )
