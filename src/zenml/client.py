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
from datetime import datetime
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
from collections.abc import Callable, Generator, Mapping, Sequence
from uuid import UUID

from pydantic import ConfigDict, SecretStr

from zenml.client_lazy_loader import (
    client_lazy_loader,
    evaluate_all_lazy_load_args_in_client_methods,
)
from zenml.config.global_config import GlobalConfiguration
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.config.source import Source
from zenml.constants import (
    ENV_ZENML_ACTIVE_PROJECT_ID,
    ENV_ZENML_ACTIVE_STACK_ID,
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
    ColorVariants,
    CuratedVisualizationSize,
    DeploymentStatus,
    LogicalOperators,
    ModelStages,
    OAuthDeviceStatus,
    PluginSubType,
    PluginType,
    ServiceState,
    SorterOps,
    StackComponentType,
    StoreType,
    TaggableResourceTypes,
    VisualizationResourceTypes,
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
    CuratedVisualizationRequest,
    CuratedVisualizationResponse,
    CuratedVisualizationUpdate,
    DeploymentFilter,
    DeploymentResponse,
    EventSourceFilter,
    EventSourceRequest,
    EventSourceResponse,
    EventSourceUpdate,
    FlavorFilter,
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
    PipelineFilter,
    PipelineResponse,
    PipelineRunFilter,
    PipelineRunResponse,
    PipelineSnapshotFilter,
    PipelineSnapshotResponse,
    PipelineSnapshotRunRequest,
    PipelineSnapshotUpdate,
    ProjectFilter,
    ProjectRequest,
    ProjectResponse,
    ProjectUpdate,
    RunMetadataRequest,
    RunMetadataResource,
    RunTemplateFilter,
    RunTemplateRequest,
    RunTemplateResponse,
    RunTemplateUpdate,
    ScheduleFilter,
    ScheduleResponse,
    ScheduleUpdate,
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
    ServiceType,
    ServiceUpdate,
    StackFilter,
    StackRequest,
    StackResponse,
    StackUpdate,
    StepRunFilter,
    StepRunResponse,
    StepRunUpdate,
    TagFilter,
    TagRequest,
    TagResource,
    TagResourceRequest,
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
)
from zenml.utils import dict_utils, io_utils, source_utils, tag_utils
from zenml.utils.dict_utils import dict_to_bytes
from zenml.utils.filesync_model import FileSyncModel
from zenml.utils.pagination_utils import depaginate
from zenml.utils.uuid_utils import is_valid_uuid

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType, MetadataTypeEnum
    from zenml.orchestrators import BaseOrchestrator
    from zenml.service_connectors.service_connector import ServiceConnector
    from zenml.services.service import ServiceConfig
    from zenml.stack import Stack
    from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)

AnyResponse = TypeVar("AnyResponse", bound=BaseIdentifiedResponse)  # type: ignore[type-arg]
F = TypeVar("F", bound=Callable[..., Any])


class ClientConfiguration(FileSyncModel):
    """Pydantic object used for serializing client configuration options."""

    _active_project: Optional["ProjectResponse"] = None
    active_project_id: UUID | None = None
    active_stack_id: UUID | None = None
    _active_stack: Optional["StackResponse"] = None

    @property
    def active_project(self) -> "ProjectResponse":
        """Get the active project for the local client.

        Returns:
            The active project.

        Raises:
            RuntimeError: If no active project is set.
        """
        if self._active_project:
            return self._active_project
        else:
            raise RuntimeError(
                "No active project is configured. Run "
                "`zenml project set <NAME>` to set the active "
                "project."
            )

    def set_active_project(self, project: "ProjectResponse") -> None:
        """Set the project for the local client.

        Args:
            project: The project to set active.
        """
        self._active_project = project
        self.active_project_id = project.id

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
    _active_project: Optional["ProjectResponse"] = None
    _active_stack: Optional["StackResponse"] = None

    def __init__(
        self,
        root: Path | None = None,
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
        self._root: Path | None = None
        self._config: ClientConfiguration | None = None

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

    def _set_active_root(self, root: Path | None = None) -> None:
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

    def _config_path(self) -> str | None:
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
            self._config.active_project_id,
            self._config.active_stack_id,
            config_name="repo",
        )
        self._config.set_active_stack(active_stack)
        if active_project:
            self._config.set_active_project(active_project)

    def _load_config(self) -> ClientConfiguration | None:
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
        root: Path | None = None,
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
        path: Path | None = None, enable_warnings: bool = False
    ) -> Path | None:
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

        def _find_repository_helper(path_: Path) -> Path | None:
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
    def root(self) -> Path | None:
        """The root directory of this client.

        Returns:
            The root directory of this client, or None, if the client
            has not been initialized.
        """
        return self._root

    @property
    def config_directory(self) -> Path | None:
        """The configuration directory of this client.

        Returns:
            The configuration directory of this client, or None, if the
            client doesn't have an active root.
        """
        return self.root / REPOSITORY_DIRECTORY_NAME if self.root else None

    def activate_root(self, root: Path | None = None) -> None:
        """Set the active repository root directory.

        Args:
            root: The path to set as the active repository root. If not set,
                the repository root is determined using the environment
                variable `ZENML_REPOSITORY_PATH` (if set) and by recursively
                searching in the parent directories of the current working
                directory.
        """
        self._set_active_root(root)

    def set_active_project(
        self, project_name_or_id: str | UUID
    ) -> "ProjectResponse":
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
            # Sanitize the client configuration to reflect the current
            # settings
            self._sanitize_config()
        else:
            # set the active project globally only if the client doesn't use
            # a local configuration
            GlobalConfiguration().set_active_project(project)
        return project

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
        updated_name: str | None = None,
        updated_logo_url: str | None = None,
        updated_enable_analytics: bool | None = None,
        updated_enable_announcements: bool | None = None,
        updated_enable_updates: bool | None = None,
        updated_onboarding_state: dict[str, Any] | None = None,
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
        password: str | None = None,
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
        name_id_or_prefix: str | UUID,
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
        id: UUID | str | None = None,
        external_user_id: str | None = None,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        name: str | None = None,
        full_name: str | None = None,
        email: str | None = None,
        active: bool | None = None,
        email_opted_in: bool | None = None,
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
        name_id_or_prefix: str | UUID,
        updated_name: str | None = None,
        updated_full_name: str | None = None,
        updated_email: str | None = None,
        updated_email_opt_in: bool | None = None,
        updated_password: str | None = None,
        old_password: str | None = None,
        updated_is_admin: bool | None = None,
        updated_metadata: dict[str, Any] | None = None,
        updated_default_project_id: UUID | None = None,
        active: bool | None = None,
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
            updated_default_project_id: The new default project ID for the user.
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

        if updated_default_project_id is not None:
            user_update.default_project_id = updated_default_project_id

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

    # -------------------------------- Projects ------------------------------

    def create_project(
        self,
        name: str,
        description: str,
        display_name: str | None = None,
    ) -> ProjectResponse:
        """Create a new project.

        Args:
            name: Name of the project.
            description: Description of the project.
            display_name: Display name of the project.

        Returns:
            The created project.
        """
        return self.zen_store.create_project(
            ProjectRequest(
                name=name,
                description=description,
                display_name=display_name or "",
            )
        )

    def get_project(
        self,
        name_id_or_prefix: UUID | str | None,
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> ProjectResponse:
        """Gets a project.

        Args:
            name_id_or_prefix: The name or ID of the project.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The project
        """
        if not name_id_or_prefix:
            return self.active_project
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_project,
            list_method=self.list_projects,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            hydrate=hydrate,
        )

    def list_projects(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: UUID | str | None = None,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        name: str | None = None,
        display_name: str | None = None,
        hydrate: bool = False,
    ) -> Page[ProjectResponse]:
        """List all projects.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the project ID to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            name: Use the project name for filtering
            display_name: Use the project display name for filtering
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            Page of projects
        """
        return self.zen_store.list_projects(
            ProjectFilter(
                sort_by=sort_by,
                page=page,
                size=size,
                logical_operator=logical_operator,
                id=id,
                created=created,
                updated=updated,
                name=name,
                display_name=display_name,
            ),
            hydrate=hydrate,
        )

    def update_project(
        self,
        name_id_or_prefix: UUID | str | None,
        new_name: str | None = None,
        new_display_name: str | None = None,
        new_description: str | None = None,
    ) -> ProjectResponse:
        """Update a project.

        Args:
            name_id_or_prefix: Name, ID or prefix of the project to update.
            new_name: New name of the project.
            new_display_name: New display name of the project.
            new_description: New description of the project.

        Returns:
            The updated project.
        """
        project = self.get_project(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )
        project_update = ProjectUpdate(
            name=new_name or project.name,
            display_name=new_display_name or project.display_name,
        )
        if new_description:
            project_update.description = new_description
        return self.zen_store.update_project(
            project_id=project.id,
            project_update=project_update,
        )

    def delete_project(self, name_id_or_prefix: str) -> None:
        """Delete a project.

        Args:
            name_id_or_prefix: The name or ID of the project to delete.

        Raises:
            IllegalOperationError: If the project to delete is the active
                project.
        """
        project = self.get_project(
            name_id_or_prefix, allow_name_prefix_match=False
        )
        if self.active_project.id == project.id:
            raise IllegalOperationError(
                f"Project '{name_id_or_prefix}' cannot be deleted since "
                "it is currently active. Please set another project as "
                "active first."
            )
        self.zen_store.delete_project(project_name_or_id=project.id)

    @property
    def active_project(self) -> ProjectResponse:
        """Get the currently active project of the local client.

        If no active project is configured locally for the client, the
        active project in the global configuration is used instead.

        Returns:
            The active project.

        Raises:
            RuntimeError: If the active project is not set.
        """
        if project_id := os.environ.get(ENV_ZENML_ACTIVE_PROJECT_ID):
            if not self._active_project or self._active_project.id != UUID(
                project_id
            ):
                self._active_project = self.get_project(project_id)

            return self._active_project

        from zenml.constants import DEFAULT_PROJECT_NAME

        # If running in a ZenML server environment, the active project is
        # not relevant
        if ENV_ZENML_SERVER in os.environ:
            return self.get_project(DEFAULT_PROJECT_NAME)

        project = (
            self._config.active_project if self._config else None
        ) or GlobalConfiguration().get_active_project()
        if not project:
            raise RuntimeError(
                "No active project is configured. Run "
                "`zenml project set <NAME>` to set the active "
                "project."
            )

        if project.name != DEFAULT_PROJECT_NAME:
            if not self.zen_store.get_store_info().is_pro_server():
                logger.warning(
                    f"You are running with a non-default project "
                    f"'{project.name}'. The ZenML project feature is "
                    "available only in ZenML Pro. Pipelines, pipeline runs and "
                    "artifacts produced in this project will not be "
                    "accessible through the dashboard. Please visit "
                    "https://zenml.io/pro to learn more."
                )
        return project

    # --------------------------------- Stacks ---------------------------------

    def create_stack(
        self,
        name: str,
        components: Mapping[StackComponentType, str | UUID],
        stack_spec_file: str | None = None,
        labels: dict[str, Any] | None = None,
        secrets: Sequence[UUID | str] | None = None,
    ) -> StackResponse:
        """Registers a stack and its components.

        Args:
            name: The name of the stack to register.
            components: dictionary which maps component types to component names
            stack_spec_file: path to the stack spec file
            labels: The labels of the stack.
            secrets: The secrets of the stack.

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
            labels=labels,
            secrets=secrets,
        )

        self._validate_stack_configuration(stack=stack)

        return self.zen_store.create_stack(stack=stack)

    def get_stack(
        self,
        name_id_or_prefix: UUID | str | None = None,
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
        id: UUID | str | None = None,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        name: str | None = None,
        description: str | None = None,
        component_id: str | UUID | None = None,
        user: UUID | str | None = None,
        component: UUID | str | None = None,
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
            component_id=component_id,
            user=user,
            component=component,
            name=name,
            description=description,
            id=id,
            created=created,
            updated=updated,
        )
        return self.zen_store.list_stacks(stack_filter_model, hydrate=hydrate)

    def update_stack(
        self,
        name_id_or_prefix: UUID | str | None = None,
        name: str | None = None,
        stack_spec_file: str | None = None,
        labels: dict[str, Any] | None = None,
        description: str | None = None,
        component_updates: None | (
            dict[StackComponentType, list[UUID | str]]
        ) = None,
        add_secrets: Sequence[UUID | str] | None = None,
        remove_secrets: Sequence[UUID | str] | None = None,
        environment: dict[str, Any] | None = None,
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
            add_secrets: The secrets to add to the stack.
            remove_secrets: The secrets to remove from the stack.
            environment: The environment to set on the stack. If the value for
                any item is None, the key will be removed from the existing
                environment.

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

        if add_secrets:
            update_model.add_secrets = list(add_secrets)

        if remove_secrets:
            update_model.remove_secrets = list(remove_secrets)

        if environment:
            environment = {
                **stack.environment,
                **environment,
            }
            environment = dict_utils.remove_none_values(environment)
            update_model.environment = environment

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
        self, name_id_or_prefix: str | UUID, recursive: bool = False
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
        """
        if env_stack_id := os.environ.get(ENV_ZENML_ACTIVE_STACK_ID):
            if not self._active_stack or self._active_stack.id != UUID(
                env_stack_id
            ):
                self._active_stack = self.get_stack(env_stack_id)

            return self._active_stack

        stack_id: UUID | None = None

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

        return self.get_stack(stack_id)

    def activate_stack(
        self, stack_name_id_or_prefix: str | UUID
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
        """
        local_components: list[str] = []
        remote_components: list[str] = []
        assert stack.components is not None
        for component_type, components in stack.components.items():
            component_flavor: FlavorResponse | str

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
                    flavor=component_flavor,
                    component_type=component_type,
                    # Always enforce validation of custom flavors
                    validate_custom_flavors=True,
                )
                # Guaranteed to not be None by setting
                # `validate_custom_flavors=True` above
                assert configuration is not None
                warn_if_config_server_mismatch(configuration)
                flavor_name = (
                    component_flavor.name
                    if isinstance(component_flavor, FlavorResponse)
                    else component_flavor
                )
                if configuration.is_local:
                    local_components.append(
                        f"{component_type.value}: {flavor_name}"
                    )
                elif configuration.is_remote:
                    remote_components.append(
                        f"{component_type.value}: {flavor_name}"
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

    # ----------------------------- Services -----------------------------------

    def create_service(
        self,
        config: "ServiceConfig",
        service_type: ServiceType,
        model_version_id: UUID | None = None,
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
            project=self.active_project.id,
            model_version_id=model_version_id,
        )
        # Register the service
        return self.zen_store.create_service(service_request)

    def get_service(
        self,
        name_id_or_prefix: str | UUID,
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
        type: str | None = None,
        project: str | UUID | None = None,
    ) -> ServiceResponse:
        """Gets a service.

        Args:
            name_id_or_prefix: The name or ID of the service.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            type: The type of the service.
            project: The project name/ID to filter by.

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
            return self.zen_store.list_services(
                filter_model=service_filter_model,
                hydrate=hydrate,
            )

        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_service,
            list_method=type_scoped_list_method,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            project=project,
            hydrate=hydrate,
        )

    def list_services(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: UUID | str | None = None,
        created: datetime | None = None,
        updated: datetime | None = None,
        type: str | None = None,
        flavor: str | None = None,
        user: UUID | str | None = None,
        project: str | UUID | None = None,
        hydrate: bool = False,
        running: bool | None = None,
        service_name: str | None = None,
        pipeline_name: str | None = None,
        pipeline_run_id: str | None = None,
        pipeline_step_name: str | None = None,
        model_version_id: str | UUID | None = None,
        config: dict[str, Any] | None = None,
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
            project: The project name/ID to filter by.
            user: Filter by user name/ID.
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
            project=project or self.active_project.id,
            user=user,
            running=running,
            name=service_name,
            pipeline_name=pipeline_name,
            pipeline_step_name=pipeline_step_name,
            model_version_id=model_version_id,
            pipeline_run_id=pipeline_run_id,
            config=dict_to_bytes(config) if config else None,
        )
        return self.zen_store.list_services(
            filter_model=service_filter_model, hydrate=hydrate
        )

    def update_service(
        self,
        id: UUID,
        name: str | None = None,
        service_source: str | None = None,
        admin_state: ServiceState | None = None,
        status: dict[str, Any] | None = None,
        endpoint: dict[str, Any] | None = None,
        labels: dict[str, str] | None = None,
        prediction_url: str | None = None,
        health_check_url: str | None = None,
        model_version_id: UUID | None = None,
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

    def delete_service(
        self,
        name_id_or_prefix: UUID,
        project: str | UUID | None = None,
    ) -> None:
        """Delete a service.

        Args:
            name_id_or_prefix: The name or ID of the service to delete.
            project: The project name/ID to filter by.
        """
        service = self.get_service(
            name_id_or_prefix,
            allow_name_prefix_match=False,
            project=project,
        )
        self.zen_store.delete_service(service_id=service.id)

    # -------------------------------- Components ------------------------------

    def get_stack_component(
        self,
        component_type: StackComponentType,
        name_id_or_prefix: str | UUID | None = None,
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
        id: UUID | str | None = None,
        created: datetime | None = None,
        updated: datetime | None = None,
        name: str | None = None,
        flavor: str | None = None,
        type: str | None = None,
        connector_id: str | UUID | None = None,
        stack_id: str | UUID | None = None,
        user: UUID | str | None = None,
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
            connector_id: The id of the connector to filter by.
            stack_id: The id of the stack to filter by.
            name: The name of the component to filter by.
            user: The ID of name of the user to filter by.
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
            connector_id=connector_id,
            stack_id=stack_id,
            name=name,
            flavor=flavor,
            type=type,
            id=id,
            created=created,
            updated=updated,
            user=user,
        )

        return self.zen_store.list_stack_components(
            component_filter_model=component_filter_model, hydrate=hydrate
        )

    def create_stack_component(
        self,
        name: str,
        flavor: str,
        component_type: StackComponentType,
        configuration: dict[str, str],
        labels: dict[str, Any] | None = None,
        secrets: Sequence[UUID | str] | None = None,
        environment: dict[str, Any] | None = None,
    ) -> "ComponentResponse":
        """Registers a stack component.

        Args:
            name: The name of the stack component.
            flavor: The flavor of the stack component.
            component_type: The type of the stack component.
            configuration: The configuration of the stack component.
            labels: The labels of the stack component.
            secrets: The secrets of the stack component.
            environment: The environment of the stack component.

        Returns:
            The model of the registered component.
        """
        from zenml.stack.utils import (
            validate_stack_component_config,
            warn_if_config_server_mismatch,
        )

        validated_config = validate_stack_component_config(
            configuration_dict=configuration,
            flavor=flavor,
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
            configuration=validated_config.model_dump(
                mode="json", exclude_unset=True
            ),
            labels=labels,
            secrets=secrets,
            environment=environment,
        )

        # Register the new model
        return self.zen_store.create_stack_component(
            component=create_component_model
        )

    def update_stack_component(
        self,
        name_id_or_prefix: UUID | str | None,
        component_type: StackComponentType,
        name: str | None = None,
        configuration: dict[str, Any] | None = None,
        labels: dict[str, Any] | None = None,
        disconnect: bool | None = None,
        connector_id: UUID | None = None,
        connector_resource_id: str | None = None,
        add_secrets: Sequence[UUID | str] | None = None,
        remove_secrets: Sequence[UUID | str] | None = None,
        environment: dict[str, Any] | None = None,
    ) -> ComponentResponse:
        """Updates a stack component.

        Args:
            name_id_or_prefix: The name, id or prefix of the stack component to
                update.
            component_type: The type of the stack component to update.
            name: The new name of the stack component.
            configuration: The new configuration of the stack component.
            labels: The new labels of the stack component.
            disconnect: Whether to disconnect the stack component from its
                service connector.
            connector_id: The new connector id of the stack component.
            connector_resource_id: The new connector resource id of the
                stack component.
            add_secrets: The secrets to add to the stack component.
            remove_secrets: The secrets to remove from the stack component.
            environment: The environment to set on the stack component. If the
                value for any item is None, the key will be removed from the
                existing environment.

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

        update_model = ComponentUpdate()

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
            merged_configuration = {
                **existing_configuration,
                **configuration,
            }
            merged_configuration = {
                k: v for k, v in merged_configuration.items() if v is not None
            }

            from zenml.stack.utils import (
                validate_stack_component_config,
                warn_if_config_server_mismatch,
            )

            validated_config = validate_stack_component_config(
                configuration_dict=merged_configuration,
                flavor=component.flavor,
                component_type=component.type,
                # Always enforce validation of custom flavors
                validate_custom_flavors=True,
                existing_config=existing_configuration,
            )
            # Guaranteed to not be None by setting
            # `validate_custom_flavors=True` above
            assert validated_config is not None
            warn_if_config_server_mismatch(validated_config)

            update_model.configuration = validated_config.model_dump(
                mode="json", exclude_unset=True
            )

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

        if add_secrets:
            update_model.add_secrets = list(add_secrets)

        if remove_secrets:
            update_model.remove_secrets = list(remove_secrets)

        if environment:
            environment = {
                **component.environment,
                **environment,
            }
            environment = dict_utils.remove_none_values(environment)
            update_model.environment = environment

        # Send the updated component to the ZenStore
        return self.zen_store.update_stack_component(
            component_id=component.id,
            component_update=update_model,
        )

    def delete_stack_component(
        self,
        name_id_or_prefix: str | UUID,
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

        flavor_request = flavor.to_model(integration="custom", is_custom=True)
        return self.zen_store.create_flavor(flavor=flavor_request)

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
        id: UUID | str | None = None,
        created: datetime | None = None,
        updated: datetime | None = None,
        name: str | None = None,
        type: str | None = None,
        integration: str | None = None,
        user: UUID | str | None = None,
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
            user: Filter by user name/ID.
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
            user=user,
            name=name,
            type=type,
            integration=integration,
            id=id,
            created=created,
            updated=updated,
        )
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
        id: UUID | str | None = None,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        name: str | None = None,
        latest_run_status: str | None = None,
        latest_run_user: UUID | str | None = None,
        project: str | UUID | None = None,
        user: UUID | str | None = None,
        tag: str | None = None,
        tags: list[str] | None = None,
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
            latest_run_user: Filter by the name or UUID of the user that
                executed the latest run.
            project: The project name/ID to filter by.
            user: The name/ID of the user to filter by.
            tag: Tag to filter by.
            tags: Tags to filter by.
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
            latest_run_user=latest_run_user,
            project=project or self.active_project.id,
            user=user,
            tag=tag,
            tags=tags,
        )
        return self.zen_store.list_pipelines(
            pipeline_filter_model=pipeline_filter_model,
            hydrate=hydrate,
        )

    def get_pipeline(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
        hydrate: bool = True,
    ) -> PipelineResponse:
        """Get a pipeline by name, id or prefix.

        Args:
            name_id_or_prefix: The name, ID or ID prefix of the pipeline.
            project: The project name/ID to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The pipeline.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_pipeline,
            list_method=self.list_pipelines,
            name_id_or_prefix=name_id_or_prefix,
            project=project,
            hydrate=hydrate,
        )

    def delete_pipeline(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
    ) -> None:
        """Delete a pipeline.

        Args:
            name_id_or_prefix: The name, ID or ID prefix of the pipeline.
            project: The project name/ID to filter by.
        """
        pipeline = self.get_pipeline(
            name_id_or_prefix=name_id_or_prefix, project=project
        )
        self.zen_store.delete_pipeline(pipeline_id=pipeline.id)

    # -------------------------------- Builds ----------------------------------

    def get_build(
        self,
        id_or_prefix: str | UUID,
        project: str | UUID | None = None,
        hydrate: bool = True,
    ) -> PipelineBuildResponse:
        """Get a build by id or prefix.

        Args:
            id_or_prefix: The id or id prefix of the build.
            project: The project name/ID to filter by.
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

        list_kwargs: dict[str, Any] = dict(
            id=f"startswith:{id_or_prefix}",
            hydrate=hydrate,
        )
        scope = ""
        if project:
            list_kwargs["project"] = project
            scope = f" in project {project}"

        entity = self.list_builds(**list_kwargs)

        # If only a single entity is found, return it.
        if entity.total == 1:
            return entity.items[0]

        # If no entity is found, raise an error.
        if entity.total == 0:
            raise KeyError(
                f"No builds have been found that have either an id or prefix "
                f"that matches the provided string '{id_or_prefix}'{scope}."
            )

        raise ZenKeyError(
            f"{entity.total} builds have been found{scope} that have "
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
        id: UUID | str | None = None,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        project: str | UUID | None = None,
        user: UUID | str | None = None,
        pipeline_id: str | UUID | None = None,
        stack_id: str | UUID | None = None,
        container_registry_id: UUID | str | None = None,
        is_local: bool | None = None,
        contains_code: bool | None = None,
        zenml_version: str | None = None,
        python_version: str | None = None,
        checksum: str | None = None,
        stack_checksum: str | None = None,
        duration: int | str | None = None,
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
            project: The project name/ID to filter by.
            user: Filter by user name/ID.
            pipeline_id: The id of the pipeline to filter by.
            stack_id: The id of the stack to filter by.
            container_registry_id: The id of the container registry to
                filter by.
            is_local: Use to filter local builds.
            contains_code: Use to filter builds that contain code.
            zenml_version: The version of ZenML to filter by.
            python_version: The Python version to filter by.
            checksum: The build checksum to filter by.
            stack_checksum: The stack checksum to filter by.
            duration: The duration of the build in seconds to filter by.
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
            project=project or self.active_project.id,
            user=user,
            pipeline_id=pipeline_id,
            stack_id=stack_id,
            container_registry_id=container_registry_id,
            is_local=is_local,
            contains_code=contains_code,
            zenml_version=zenml_version,
            python_version=python_version,
            checksum=checksum,
            stack_checksum=stack_checksum,
            duration=duration,
        )
        return self.zen_store.list_builds(
            build_filter_model=build_filter_model,
            hydrate=hydrate,
        )

    def delete_build(
        self, id_or_prefix: str, project: str | UUID | None = None
    ) -> None:
        """Delete a build.

        Args:
            id_or_prefix: The id or id prefix of the build.
            project: The project name/ID to filter by.
        """
        build = self.get_build(id_or_prefix=id_or_prefix, project=project)
        self.zen_store.delete_build(build_id=build.id)

    # --------------------------------- Event Sources -------------------------

    @_fail_for_sql_zen_store
    def create_event_source(
        self,
        name: str,
        configuration: dict[str, Any],
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
            project=self.active_project.id,
        )

        return self.zen_store.create_event_source(event_source=event_source)

    @_fail_for_sql_zen_store
    def get_event_source(
        self,
        name_id_or_prefix: UUID | str,
        allow_name_prefix_match: bool = True,
        project: str | UUID | None = None,
        hydrate: bool = True,
    ) -> EventSourceResponse:
        """Get an event source by name, ID or prefix.

        Args:
            name_id_or_prefix: The name, ID or prefix of the stack.
            allow_name_prefix_match: If True, allow matching by name prefix.
            project: The project name/ID to filter by.
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
            project=project,
            hydrate=hydrate,
        )

    def list_event_sources(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: UUID | str | None = None,
        created: datetime | None = None,
        updated: datetime | None = None,
        name: str | None = None,
        flavor: str | None = None,
        event_source_type: str | None = None,
        project: str | UUID | None = None,
        user: UUID | str | None = None,
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
            project: The project name/ID to filter by.
            user: Filter by user name/ID.
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
            project=project or self.active_project.id,
            user=user,
            name=name,
            flavor=flavor,
            plugin_subtype=event_source_type,
            id=id,
            created=created,
            updated=updated,
        )
        return self.zen_store.list_event_sources(
            event_source_filter_model, hydrate=hydrate
        )

    @_fail_for_sql_zen_store
    def update_event_source(
        self,
        name_id_or_prefix: UUID | str,
        name: str | None = None,
        description: str | None = None,
        configuration: dict[str, Any] | None = None,
        rotate_secret: bool | None = None,
        is_active: bool | None = None,
        project: str | UUID | None = None,
    ) -> EventSourceResponse:
        """Updates an event_source.

        Args:
            name_id_or_prefix: The name, id or prefix of the event_source to update.
            name: the new name of the event_source.
            description: the new description of the event_source.
            configuration: The event source configuration.
            rotate_secret: Allows rotating of secret, if true, the response will
                contain the new secret value
            is_active: Optional[bool] = Allows for activation/deactivating the
                event source
            project: The project name/ID to filter by.

        Returns:
            The model of the updated event_source.

        Raises:
            EntityExistsError: If the event_source name is already taken.
        """
        # First, get the eve
        event_source = self.get_event_source(
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
            project=project,
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
    def delete_event_source(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
    ) -> None:
        """Deletes an event_source.

        Args:
            name_id_or_prefix: The name, id or prefix id of the event_source
                to deregister.
            project: The project name/ID to filter by.
        """
        event_source = self.get_event_source(
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
            project=project,
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
        configuration: dict[str, Any],
        service_account_id: UUID,
        auth_window: int | None = None,
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
            project=self.active_project.id,
        )

        return self.zen_store.create_action(action=action)

    @_fail_for_sql_zen_store
    def get_action(
        self,
        name_id_or_prefix: UUID | str,
        allow_name_prefix_match: bool = True,
        project: str | UUID | None = None,
        hydrate: bool = True,
    ) -> ActionResponse:
        """Get an action by name, ID or prefix.

        Args:
            name_id_or_prefix: The name, ID or prefix of the action.
            allow_name_prefix_match: If True, allow matching by name prefix.
            project: The project name/ID to filter by.
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
            project=project,
            hydrate=hydrate,
        )

    @_fail_for_sql_zen_store
    def list_actions(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: UUID | str | None = None,
        created: datetime | None = None,
        updated: datetime | None = None,
        name: str | None = None,
        flavor: str | None = None,
        action_type: str | None = None,
        project: str | UUID | None = None,
        user: UUID | str | None = None,
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
            project: The project name/ID to filter by.
            user: Filter by user name/ID.
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
            project=project or self.active_project.id,
            user=user,
            name=name,
            id=id,
            flavor=flavor,
            plugin_subtype=action_type,
            created=created,
            updated=updated,
        )
        return self.zen_store.list_actions(filter_model, hydrate=hydrate)

    @_fail_for_sql_zen_store
    def update_action(
        self,
        name_id_or_prefix: UUID | str,
        name: str | None = None,
        description: str | None = None,
        configuration: dict[str, Any] | None = None,
        service_account_id: UUID | None = None,
        auth_window: int | None = None,
        project: str | UUID | None = None,
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
            project: The project name/ID to filter by.

        Returns:
            The updated action.
        """
        action = self.get_action(
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
            project=project,
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
    def delete_action(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
    ) -> None:
        """Delete an action.

        Args:
            name_id_or_prefix: The name, id or prefix id of the action
                to delete.
            project: The project name/ID to filter by.
        """
        action = self.get_action(
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
            project=project,
        )

        self.zen_store.delete_action(action_id=action.id)
        logger.info("Deleted action with name '%s'.", action.name)

    # --------------------------------- Triggers -------------------------

    @_fail_for_sql_zen_store
    def create_trigger(
        self,
        name: str,
        event_source_id: UUID,
        event_filter: dict[str, Any],
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
            project=self.active_project.id,
        )

        return self.zen_store.create_trigger(trigger=trigger)

    @_fail_for_sql_zen_store
    def get_trigger(
        self,
        name_id_or_prefix: UUID | str,
        allow_name_prefix_match: bool = True,
        project: str | UUID | None = None,
        hydrate: bool = True,
    ) -> TriggerResponse:
        """Get a trigger by name, ID or prefix.

        Args:
            name_id_or_prefix: The name, ID or prefix of the trigger.
            allow_name_prefix_match: If True, allow matching by name prefix.
            project: The project name/ID to filter by.
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
            project=project,
            hydrate=hydrate,
        )

    @_fail_for_sql_zen_store
    def list_triggers(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: UUID | str | None = None,
        created: datetime | None = None,
        updated: datetime | None = None,
        name: str | None = None,
        event_source_id: UUID | None = None,
        action_id: UUID | None = None,
        event_source_flavor: str | None = None,
        event_source_subtype: str | None = None,
        action_flavor: str | None = None,
        action_subtype: str | None = None,
        project: str | UUID | None = None,
        user: UUID | str | None = None,
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
            project: The project name/ID to filter by.
            user: Filter by user name/ID.
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
            project=project or self.active_project.id,
            user=user,
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
        return self.zen_store.list_triggers(
            trigger_filter_model, hydrate=hydrate
        )

    @_fail_for_sql_zen_store
    def update_trigger(
        self,
        name_id_or_prefix: UUID | str,
        name: str | None = None,
        description: str | None = None,
        event_filter: dict[str, Any] | None = None,
        is_active: bool | None = None,
        project: str | UUID | None = None,
    ) -> TriggerResponse:
        """Updates a trigger.

        Args:
            name_id_or_prefix: The name, id or prefix of the trigger to update.
            name: the new name of the trigger.
            description: the new description of the trigger.
            event_filter: The event filter configuration.
            is_active: Whether the trigger is active or not.
            project: The project name/ID to filter by.

        Returns:
            The model of the updated trigger.

        Raises:
            EntityExistsError: If the trigger name is already taken.
        """
        # First, get the eve
        trigger = self.get_trigger(
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
            project=project,
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
    def delete_trigger(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
    ) -> None:
        """Deletes an trigger.

        Args:
            name_id_or_prefix: The name, id or prefix id of the trigger
                to deregister.
            project: The project name/ID to filter by.
        """
        trigger = self.get_trigger(
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
            project=project,
        )

        self.zen_store.delete_trigger(trigger_id=trigger.id)
        logger.info("Deleted trigger with name '%s'.", trigger.name)

    # ------------------------------ Snapshots -------------------------------

    def get_snapshot(
        self,
        name_id_or_prefix: str | UUID,
        *,
        pipeline_name_or_id: str | UUID | None = None,
        project: str | UUID | None = None,
        include_config_schema: bool | None = None,
        allow_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> PipelineSnapshotResponse:
        """Get a snapshot by name, id or prefix.

        Args:
            name_id_or_prefix: The name, id or prefix of the snapshot. If a
                pipeline name or id is provided, this will be treated as the
                snapshot name. Otherwise, it will be treated as the snapshot ID
                prefix.
            pipeline_name_or_id: The name or id of the pipeline for which to
                get the snapshot.
            project: The project name/ID.
            include_config_schema: Whether to include the config schema in the
                response.
            allow_prefix_match: If True, allow matching by ID prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Raises:
            KeyError: If no snapshot was found for the given parameters.
            ZenKeyError: If multiple snapshots were found that match the given
                parameters.

        Returns:
            The snapshot.
        """
        from zenml.utils.uuid_utils import is_valid_uuid

        if is_valid_uuid(name_id_or_prefix):
            id_ = (
                UUID(name_id_or_prefix)
                if isinstance(name_id_or_prefix, str)
                else name_id_or_prefix
            )
            return self.zen_store.get_snapshot(
                id_,
                hydrate=hydrate,
                include_config_schema=include_config_schema,
            )

        list_kwargs: dict[str, Any] = {
            "named_only": None,
            "project": project,
            "hydrate": hydrate,
            "size": 1,
        }

        # First, try to get the snapshot by name
        snapshots = self.list_snapshots(
            name=str(name_id_or_prefix),
            pipeline=pipeline_name_or_id,
            **list_kwargs,
        )
        if snapshots.total == 1:
            snapshot = snapshots.items[0]
        elif snapshots.total == 0:
            # No name matches. If the user provided a pipeline, we assume
            # they want to fetch the snapshot by name and fail. Otherwise,
            # we try to fetch by ID prefix.
            if pipeline_name_or_id or not allow_prefix_match:
                raise KeyError(
                    f"No snapshot with name `{name_id_or_prefix}` has been "
                    f"found for pipeline `{pipeline_name_or_id}`."
                )
            else:
                snapshots = self.list_snapshots(
                    id=f"startswith:{name_id_or_prefix}", **list_kwargs
                )

                if snapshots.total == 1:
                    snapshot = snapshots.items[0]
                elif snapshots.total == 0:
                    raise KeyError(
                        f"No snapshot with ID prefix `{name_id_or_prefix}` "
                        "has been found."
                    )
                else:
                    raise ZenKeyError(
                        f"{snapshots.total} snapshots have been found that "
                        "have an ID that matches the provided prefix "
                        f"`{name_id_or_prefix}`. Please use the full ID to "
                        "uniquely identify one of the snapshots."
                    )
        else:
            # Multiple name matches, this is only possible if the user
            # provided no pipeline.
            raise ZenKeyError(
                f"{snapshots.total} snapshots have been found for name "
                f"`{name_id_or_prefix}`. Please either specify which "
                "pipeline the snapshot belongs to or fetch the snapshot "
                "by ID to uniquely identify one of the snapshots."
            )

        if hydrate and include_config_schema:
            # The config schema cannot be fetched using the list
            # call, so we make a second call to fetch it.
            return self.zen_store.get_snapshot(
                snapshot.id,
                include_config_schema=include_config_schema,
                hydrate=hydrate,
            )
        return snapshot

    def list_snapshots(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: UUID | str | None = None,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        project: str | UUID | None = None,
        user: UUID | str | None = None,
        name: str | None = None,
        named_only: bool | None = True,
        pipeline: str | UUID | None = None,
        stack: str | UUID | None = None,
        build_id: str | UUID | None = None,
        schedule_id: str | UUID | None = None,
        source_snapshot_id: str | UUID | None = None,
        runnable: bool | None = None,
        deployable: bool | None = None,
        deployed: bool | None = None,
        tag: str | None = None,
        tags: list[str] | None = None,
        hydrate: bool = False,
    ) -> Page[PipelineSnapshotResponse]:
        """List all snapshots.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of build to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            project: The project name/ID to filter by.
            user: Filter by user name/ID.
            name: Filter by name.
            named_only: If `True`, only snapshots with an assigned name
                will be returned.
            pipeline: Name or ID of the pipeline to filter by.
            stack: Name or ID of the stack to filter by.
            build_id: The id of the build to filter by.
            schedule_id: The ID of the schedule to filter by.
            source_snapshot_id: The ID of the source snapshot to filter by.
            runnable: Whether the snapshot is runnable.
            deployable: Whether the snapshot is deployable.
            deployed: Whether the snapshot is deployed.
            tag: Filter by tag.
            tags: Filter by tags.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page with snapshots fitting the filter description
        """
        snapshot_filter_model = PipelineSnapshotFilter(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            created=created,
            updated=updated,
            project=project or self.active_project.id,
            user=user,
            name=name,
            named_only=named_only,
            pipeline=pipeline,
            stack=stack,
            build_id=build_id,
            schedule_id=schedule_id,
            source_snapshot_id=source_snapshot_id,
            runnable=runnable,
            deployable=deployable,
            deployed=deployed,
            tag=tag,
            tags=tags,
        )
        return self.zen_store.list_snapshots(
            snapshot_filter_model=snapshot_filter_model,
            hydrate=hydrate,
        )

    def update_snapshot(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
        name: str | None = None,
        description: str | None = None,
        replace: bool | None = None,
        add_tags: list[str] | None = None,
        remove_tags: list[str] | None = None,
    ) -> PipelineSnapshotResponse:
        """Update a snapshot.

        Args:
            name_id_or_prefix: Name, ID or ID prefix of the snapshot.
            project: The project name/ID to filter by.
            name: The new name of the snapshot.
            description: The new description of the snapshot.
            replace: Whether to replace the existing snapshot with the same
                name.
            add_tags: Tags to add to the snapshot.
            remove_tags: Tags to remove from the snapshot.

        Returns:
            The updated snapshot.
        """
        snapshot = self.get_snapshot(
            name_id_or_prefix,
            project=project,
            hydrate=False,
        )

        return self.zen_store.update_snapshot(
            snapshot_id=snapshot.id,
            snapshot_update=PipelineSnapshotUpdate(
                name=name,
                description=description,
                replace=replace,
                add_tags=add_tags,
                remove_tags=remove_tags,
            ),
        )

    def delete_snapshot(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
    ) -> None:
        """Delete a snapshot.

        Args:
            name_id_or_prefix: Name, ID or ID prefix of the snapshot.
            project: The project name/ID to filter by.
        """
        snapshot = self.get_snapshot(
            name_id_or_prefix,
            project=project,
            hydrate=False,
        )
        self.zen_store.delete_snapshot(snapshot_id=snapshot.id)

    @_fail_for_sql_zen_store
    def trigger_pipeline(
        self,
        snapshot_name_or_id: str | UUID | None = None,
        pipeline_name_or_id: str | UUID | None = None,
        run_configuration: (
            PipelineRunConfiguration | dict[str, Any] | None
        ) = None,
        config_path: str | None = None,
        stack_name_or_id: str | UUID | None = None,
        synchronous: bool = False,
        project: str | UUID | None = None,
        template_id: UUID | None = None,
    ) -> PipelineRunResponse:
        """Run a pipeline snapshot.

        Usage examples:
        * Run a specific snapshot by ID:
        ```python
        Client().trigger_pipeline(snapshot_name_or_id=<ID>)
        ```
        * Run a specific snapshot by name:
        ```python
        Client().trigger_pipeline(
            snapshot_name_or_id=<NAME>,
            pipeline_name_or_id=<PIPELINE_NAME_OR_ID>
        )
        ```
        * Run the latest runnable snapshot for a pipeline:
        ```python
        Client().trigger_pipeline(pipeline_name_or_id=<NAME>)
        ```
        * Run the latest runnable snapshot for a pipeline on a specific stack:
        ```python
        Client().trigger_pipeline(
            pipeline_name_or_id=<NAME>,
            stack_name_or_id=<STACK_NAME_OR_ID>
        )
        ```

        Args:
            snapshot_name_or_id: Name or ID of the snapshot to run.
            pipeline_name_or_id: Name or ID of the pipeline. If this is
                specified, the latest runnable snapshot for this pipeline will
                be used for the run (Runnable here means that the build
                associated with the snapshot is for a remote stack without any
                custom flavor stack components). If not given, a snapshot
                that should be run needs to be specified.
            run_configuration: Configuration for the run. Either this or a
                path to a config file can be specified.
            config_path: Path to a YAML configuration file. This file will be
                parsed as a `PipelineRunConfiguration` object. Either this or
                the configuration in code can be specified.
            stack_name_or_id: Name or ID of the stack on which to run the
                pipeline. If not specified, this method will try to find a
                runnable snapshot on any stack.
            synchronous: If `True`, this method will wait until the started
                run is finished.
            project: The project name/ID to filter by.
            template_id: DEPRECATED. Use snapshot_id instead.

        Raises:
            RuntimeError: If running the snapshot failed.

        Returns:
            Model of the pipeline run.
        """
        from zenml.pipelines.run_utils import (
            validate_run_config_is_runnable_from_server,
            validate_stack_is_runnable_from_server,
            wait_for_pipeline_run_to_finish,
        )

        if run_configuration and config_path:
            raise RuntimeError(
                "Only config path or runtime configuration can be specified."
            )

        if config_path:
            run_configuration = PipelineRunConfiguration.from_yaml(config_path)

        if isinstance(run_configuration, dict):
            run_configuration = PipelineRunConfiguration.model_validate(
                run_configuration
            )

        if run_configuration:
            validate_run_config_is_runnable_from_server(run_configuration)

        if template_id:
            logger.warning(
                "Triggering a run template is deprecated. Use "
                "`Client().trigger_pipeline(snapshot_id=...)` instead."
            )
            run = self.zen_store.run_template(
                template_id=template_id,
                run_configuration=run_configuration,
            )
        else:
            if snapshot_name_or_id:
                if stack_name_or_id:
                    logger.warning(
                        "Snapshot and stack specified, ignoring the stack and "
                        "using stack associated with the snapshot instead."
                    )

                snapshot_id = self.get_snapshot(
                    name_id_or_prefix=snapshot_name_or_id,
                    pipeline_name_or_id=pipeline_name_or_id,
                    project=project,
                    allow_prefix_match=False,
                    hydrate=False,
                ).id
            else:
                if not pipeline_name_or_id:
                    raise RuntimeError(
                        "You need to specify at least one of snapshot or "
                        "pipeline to run."
                    )

                # Find the latest runnable snapshot for the pipeline (and
                # stack if specified)
                pipeline = self.get_pipeline(
                    name_id_or_prefix=pipeline_name_or_id,
                    project=project,
                )
                stack = None
                if stack_name_or_id:
                    stack = self.get_stack(
                        stack_name_or_id, allow_name_prefix_match=False
                    )
                    validate_stack_is_runnable_from_server(
                        zen_store=self.zen_store, stack=stack
                    )

                all_snapshots = depaginate(
                    self.list_snapshots,
                    pipeline=pipeline.id,
                    stack=stack.id if stack else None,
                    project=pipeline.project_id,
                    runnable=True,
                    # Only try to run named snapshots
                    named_only=True,
                )

                for snapshot in all_snapshots:
                    if not snapshot.build:
                        continue

                    stack = snapshot.build.stack
                    if not stack:
                        continue

                    try:
                        validate_stack_is_runnable_from_server(
                            zen_store=self.zen_store, stack=stack
                        )
                    except ValueError:
                        continue

                    snapshot_id = snapshot.id
                    break
                else:
                    raise RuntimeError(
                        "Unable to find a runnable snapshot for the given "
                        "stack and pipeline."
                    )

            step_run_id = None
            try:
                from zenml.steps.step_context import get_step_context

                step_run_id = get_step_context().step_run.id
            except RuntimeError:
                pass

            run = self.zen_store.run_snapshot(
                snapshot_id=snapshot_id,
                run_request=PipelineSnapshotRunRequest(
                    run_configuration=run_configuration,
                    step_run=step_run_id,
                ),
            )

        if synchronous:
            run = wait_for_pipeline_run_to_finish(run_id=run.id)

        return run

    # ------------------------------ Deployments -----------------------------

    def get_deployment(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
        hydrate: bool = True,
    ) -> DeploymentResponse:
        """Get a deployment.

        Args:
            name_id_or_prefix: Name/ID/ID prefix of the deployment to get.
            project: The project name/ID to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The deployment.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_deployment,
            list_method=self.list_deployments,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
            project=project,
            hydrate=hydrate,
        )

    def create_curated_visualization(
        self,
        artifact_visualization_id: UUID,
        *,
        resource_id: UUID,
        resource_type: VisualizationResourceTypes,
        project_id: UUID | None = None,
        display_name: str | None = None,
        display_order: int | None = None,
        layout_size: CuratedVisualizationSize = CuratedVisualizationSize.FULL_WIDTH,
    ) -> CuratedVisualizationResponse:
        """Create a curated visualization associated with a resource.

        Curated visualizations can be attached to any of the following
        ZenML resource types to provide contextual dashboards throughout the ML
        lifecycle:

        - **Deployments** (VisualizationResourceTypes.DEPLOYMENT): Surface on
          deployment monitoring dashboards
        - **Pipelines** (VisualizationResourceTypes.PIPELINE): Associate with
          pipeline definitions
        - **Pipeline Runs** (VisualizationResourceTypes.PIPELINE_RUN): Attach to
          specific execution runs
        - **Pipeline Snapshots** (VisualizationResourceTypes.PIPELINE_SNAPSHOT):
          Link to captured pipeline configurations

        Each visualization is linked to exactly one resource.

        Args:
            artifact_visualization_id: The UUID of the artifact visualization to curate.
            resource_id: The identifier of the resource tied to the visualization.
            resource_type: The type of resource referenced by the visualization.
            project_id: The ID of the project to associate with the visualization.
            display_name: The display name of the visualization.
            display_order: The display order of the visualization.
            layout_size: The layout size of the visualization in the dashboard.

        Returns:
            The created curated visualization.
        """
        request = CuratedVisualizationRequest(
            project=project_id or self.active_project.id,
            artifact_visualization_id=artifact_visualization_id,
            display_name=display_name,
            display_order=display_order,
            layout_size=layout_size,
            resource_id=resource_id,
            resource_type=resource_type,
        )
        return self.zen_store.create_curated_visualization(request)

    def update_curated_visualization(
        self,
        visualization_id: UUID,
        *,
        display_name: str | None = None,
        display_order: int | None = None,
        layout_size: CuratedVisualizationSize | None = None,
    ) -> CuratedVisualizationResponse:
        """Update display metadata for a curated visualization.

        Args:
            visualization_id: The ID of the curated visualization to update.
            display_name: New display name for the visualization.
            display_order: New display order for the visualization.
            layout_size: Updated layout size for the visualization.

        Returns:
            The updated deployment visualization.
        """
        update_model = CuratedVisualizationUpdate(
            display_name=display_name,
            display_order=display_order,
            layout_size=layout_size,
        )
        return self.zen_store.update_curated_visualization(
            visualization_id=visualization_id,
            visualization_update=update_model,
        )

    def delete_curated_visualization(self, visualization_id: UUID) -> None:
        """Delete a curated visualization.

        Args:
            visualization_id: The ID of the curated visualization to delete.
        """
        self.zen_store.delete_curated_visualization(
            visualization_id=visualization_id
        )

    def list_deployments(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: UUID | str | None = None,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        name: str | None = None,
        snapshot_id: str | UUID | None = None,
        deployer_id: str | UUID | None = None,
        project: str | UUID | None = None,
        status: DeploymentStatus | None = None,
        url: str | None = None,
        user: UUID | str | None = None,
        pipeline: UUID | str | None = None,
        tag: str | None = None,
        tags: list[str] | None = None,
        hydrate: bool = False,
    ) -> Page[DeploymentResponse]:
        """List deployments.

        Args:
            sort_by: The column to sort by.
            page: The page of items.
            size: The maximum size of all pages.
            logical_operator: Which logical operator to use [and, or].
            id: Use the id of deployments to filter by.
            created: Use to filter by time of creation.
            updated: Use the last updated date for filtering.
            name: The name of the deployment to filter by.
            project: The project name/ID to filter by.
            snapshot_id: The id of the snapshot to filter by.
            deployer_id: The id of the deployer to filter by.
            status: The status of the deployment to filter by.
            url: The url of the deployment to filter by.
            user: Filter by user name/ID.
            pipeline: Filter by pipeline name/ID.
            tag: Tag to filter by.
            tags: Tags to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of deployments.
        """
        return self.zen_store.list_deployments(
            deployment_filter_model=DeploymentFilter(
                sort_by=sort_by,
                page=page,
                size=size,
                logical_operator=logical_operator,
                id=id,
                created=created,
                updated=updated,
                project=project or self.active_project.id,
                user=user,
                name=name,
                snapshot_id=snapshot_id,
                deployer_id=deployer_id,
                status=status,
                url=url,
                pipeline=pipeline,
                tag=tag,
                tags=tags,
            ),
            hydrate=hydrate,
        )

    def provision_deployment(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
        snapshot_id: str | UUID | None = None,
        timeout: int | None = None,
    ) -> DeploymentResponse:
        """Provision a deployment.

        Args:
            name_id_or_prefix: Name/ID/ID prefix of the deployment to provision.
            project: The project name/ID to filter by.
            snapshot_id: The ID of the snapshot to use. If not provided,
                the previous snapshot configured for the deployment will be
                used.
            timeout: The maximum time in seconds to wait for the pipeline
                deployment to be provisioned.

        Returns:
            The provisioned deployment.

        Raises:
            NotImplementedError: If the deployer cannot be instantiated.
            ValueError: If the existing deployment has no associated
                snapshot.
            KeyError: If the deployment is not found and no snapshot
                ID was provided.
        """
        from zenml.deployers.base_deployer import (
            BaseDeployer,
        )
        from zenml.stack.stack import Stack
        from zenml.stack.stack_component import StackComponent

        deployment: DeploymentResponse | None = None
        deployment_name_or_id = name_id_or_prefix
        try:
            deployment = self.get_deployment(
                name_id_or_prefix=name_id_or_prefix,
                project=project,
                hydrate=True,
            )
            deployment_name_or_id = deployment.id
        except KeyError:
            if isinstance(name_id_or_prefix, UUID):
                raise

        stack = Client().active_stack
        deployer: BaseDeployer | None = None

        if snapshot_id:
            snapshot = self.get_snapshot(
                name_id_or_prefix=snapshot_id,
                project=project,
                hydrate=True,
            )
        elif not deployment:
            raise KeyError(
                f"Deployment with name '{name_id_or_prefix}' was not "
                "found and no snapshot ID was provided."
            )
        else:
            # Use the current snapshot
            if not deployment.snapshot:
                raise ValueError(
                    f"Deployment '{deployment.name}' has no associated "
                    "snapshot."
                )
            snapshot = deployment.snapshot

            if deployment.deployer:
                try:
                    deployer = cast(
                        BaseDeployer,
                        StackComponent.from_model(deployment.deployer),
                    )
                except ImportError:
                    raise NotImplementedError(
                        f"Deployer '{deployment.deployer.name}' could "
                        f"not be instantiated. This is likely because the "
                        f"deployer's dependencies are not installed."
                    )

        if snapshot.stack and snapshot.stack.id != stack.id:
            # We really need to use the original stack for which the deployment
            # was created for to provision the deployment, otherwise the deployment
            # might not have the correct dependencies installed.
            stack = Stack.from_model(snapshot.stack)

        if not deployer:
            if stack.deployer:
                deployer = stack.deployer
            else:
                raise ValueError(
                    f"No deployer was found in the deployment's stack "
                    f"'{stack.name}' or in your active stack. Please add a "
                    "deployer to your stack to be able to provision a "
                    "deployment."
                )

        # Provision the endpoint through the deployer
        deployment = deployer.provision_deployment(
            snapshot=snapshot,
            stack=stack,
            deployment_name_or_id=deployment_name_or_id,
            replace=True,
            timeout=timeout,
        )
        logger.info(
            f"Provisioned deployment with name '{deployment.name}'.",
        )

        return deployment

    def deprovision_deployment(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
        timeout: int | None = None,
    ) -> None:
        """Deprovision a deployment.

        Args:
            name_id_or_prefix: Name/ID/ID prefix of the deployment to deprovision.
            project: The project name/ID to filter by.
            timeout: The maximum time in seconds to wait for the deployment to
                be deprovisioned.

        Raises:
            NotImplementedError: If the deployer cannot be instantiated.
        """
        from zenml.deployers.base_deployer import (
            BaseDeployer,
        )
        from zenml.stack.stack_component import StackComponent

        deployment = self.get_deployment(
            name_id_or_prefix=name_id_or_prefix,
            project=project,
            hydrate=False,
        )
        if deployment.deployer:
            # Instantiate and deprovision the deployment through the pipeline
            # server

            try:
                deployer = cast(
                    BaseDeployer,
                    StackComponent.from_model(deployment.deployer),
                )
            except ImportError:
                raise NotImplementedError(
                    f"Deployer '{deployment.deployer.name}' could "
                    f"not be instantiated. This is likely because the "
                    f"deployer's dependencies are not installed."
                )
            deployer.deprovision_deployment(
                deployment_name_or_id=deployment.id,
                timeout=timeout,
            )
            logger.info(
                "Deprovisioned deployment with name '%s'.",
                deployment.name,
            )
        else:
            logger.info(
                f"Deployment with name '{deployment.name}' is no longer "
                "managed by a deployer. This is likely because the deployer "
                "was deleted. Please delete the deployment instead.",
            )

    def delete_deployment(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
        force: bool = False,
        timeout: int | None = None,
    ) -> None:
        """Deprovision and delete a deployment.

        Args:
            name_id_or_prefix: Name/ID/ID prefix of the deployment to delete.
            project: The project name/ID to filter by.
            force: If True, force the deletion even if the deployment cannot be
                deprovisioned.
            timeout: The maximum time in seconds to wait for the pipeline
                deployment to be deprovisioned.

        Raises:
            NotImplementedError: If the deployer cannot be instantiated.
        """
        from zenml.deployers.base_deployer import (
            BaseDeployer,
        )
        from zenml.stack.stack_component import StackComponent

        deployment = self.get_deployment(
            name_id_or_prefix=name_id_or_prefix,
            project=project,
            hydrate=False,
        )
        if deployment.deployer:
            # Instantiate and deprovision the deployment through the pipeline
            # server

            try:
                deployer = cast(
                    BaseDeployer,
                    StackComponent.from_model(deployment.deployer),
                )
            except ImportError as e:
                msg = (
                    f"Deployer '{deployment.deployer.name}' could "
                    f"not be instantiated. This is likely because the "
                    f"deployer's dependencies are not installed: {e}"
                )
                if force:
                    logger.warning(msg + " Forcing deletion.")
                    self.zen_store.delete_deployment(
                        deployment_id=deployment.id
                    )
                else:
                    raise NotImplementedError(msg)
            except Exception as e:
                msg = (
                    f"Failed to instantiate deployer '{deployment.deployer.name}'."
                    f"Error: {e}"
                )
                if force:
                    logger.warning(msg + " Forcing deletion.")
                    self.zen_store.delete_deployment(
                        deployment_id=deployment.id
                    )
                else:
                    raise NotImplementedError(msg)
            else:
                deployer.delete_deployment(
                    deployment_name_or_id=deployment.id,
                    force=force,
                    timeout=timeout,
                )
        else:
            self.zen_store.delete_deployment(deployment_id=deployment.id)
        logger.info("Deleted deployment with name '%s'.", deployment.name)

    def refresh_deployment(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
    ) -> DeploymentResponse:
        """Refresh the status of a deployment.

        Args:
            name_id_or_prefix: Name/ID/ID prefix of the deployment to refresh.
            project: The project name/ID to filter by.

        Returns:
            The refreshed deployment.

        Raises:
            NotImplementedError: If the deployer cannot be instantiated or if
                the deployment is no longer managed by a deployer.
        """
        from zenml.deployers.base_deployer import (
            BaseDeployer,
        )
        from zenml.stack.stack_component import StackComponent

        deployment = self.get_deployment(
            name_id_or_prefix=name_id_or_prefix,
            project=project,
            hydrate=False,
        )
        if deployment.deployer:
            try:
                deployer = cast(
                    BaseDeployer,
                    StackComponent.from_model(deployment.deployer),
                )
            except ImportError:
                raise NotImplementedError(
                    f"Deployer '{deployment.deployer.name}' could "
                    f"not be instantiated. This is likely because the "
                    f"deployer's dependencies are not installed."
                )
            return deployer.refresh_deployment(
                deployment_name_or_id=deployment.id
            )
        else:
            raise NotImplementedError(
                f"Deployment '{deployment.name}' is no longer managed by "
                "a deployer. This is likely because the deployer "
                "was deleted. Please delete the deployment instead."
            )

    def get_deployment_logs(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
        follow: bool = False,
        tail: int | None = None,
    ) -> Generator[str, bool, None]:
        """Get the logs of a deployment.

        Args:
            name_id_or_prefix: Name/ID/ID prefix of the deployment to get the logs
                of.
            project: The project name/ID to filter by.
            follow: If True, follow the logs.
            tail: The number of lines to show from the end of the logs.

        Yields:
            The logs of the deployment.

        Raises:
            NotImplementedError: If the deployer cannot be instantiated or if
                the deployment is no longer managed by a deployer.
        """
        from zenml.deployers.base_deployer import (
            BaseDeployer,
        )
        from zenml.stack.stack_component import StackComponent

        deployment = self.get_deployment(
            name_id_or_prefix=name_id_or_prefix,
            project=project,
            hydrate=False,
        )
        if deployment.deployer:
            try:
                deployer = cast(
                    BaseDeployer,
                    StackComponent.from_model(deployment.deployer),
                )
            except ImportError:
                raise NotImplementedError(
                    f"Deployer '{deployment.deployer.name}' could "
                    f"not be instantiated. This is likely because the "
                    f"deployer's dependencies are not installed."
                )
            yield from deployer.get_deployment_logs(
                deployment_name_or_id=deployment.id,
                follow=follow,
                tail=tail,
            )
        else:
            raise NotImplementedError(
                f"Deployment '{deployment.name}' is no longer managed by "
                "a deployer. This is likely because the deployer "
                "was deleted. Please delete the deployment instead."
            )

    # ------------------------------ Run templates -----------------------------

    def create_run_template(
        self,
        name: str,
        snapshot_id: UUID,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> RunTemplateResponse:
        """Create a run template.

        Args:
            name: The name of the run template.
            snapshot_id: ID of the snapshot which this template should be
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
                source_snapshot_id=snapshot_id,
                tags=tags,
                project=self.active_project.id,
            )
        )

    def get_run_template(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
        hydrate: bool = True,
    ) -> RunTemplateResponse:
        """Get a run template.

        Args:
            name_id_or_prefix: Name/ID/ID prefix of the template to get.
            project: The project name/ID to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The run template.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_run_template,
            list_method=functools.partial(
                self.list_run_templates, hidden=None
            ),
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
            project=project,
            hydrate=hydrate,
        )

    def list_run_templates(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        id: UUID | str | None = None,
        name: str | None = None,
        hidden: bool | None = False,
        tag: str | None = None,
        project: str | UUID | None = None,
        pipeline_id: str | UUID | None = None,
        build_id: str | UUID | None = None,
        stack_id: str | UUID | None = None,
        code_repository_id: str | UUID | None = None,
        user: UUID | str | None = None,
        pipeline: UUID | str | None = None,
        stack: UUID | str | None = None,
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
            id: Filter by run template ID.
            name: Filter by run template name.
            hidden: Filter by run template hidden status.
            tag: Filter by run template tags.
            project: Filter by project name/ID.
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
            id=id,
            name=name,
            hidden=hidden,
            tag=tag,
            project=project or self.active_project.id,
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
        name_id_or_prefix: str | UUID,
        name: str | None = None,
        description: str | None = None,
        hidden: bool | None = None,
        add_tags: list[str] | None = None,
        remove_tags: list[str] | None = None,
        project: str | UUID | None = None,
    ) -> RunTemplateResponse:
        """Update a run template.

        Args:
            name_id_or_prefix: Name/ID/ID prefix of the template to update.
            name: The new name of the run template.
            description: The new description of the run template.
            hidden: The new hidden status of the run template.
            add_tags: Tags to add to the run template.
            remove_tags: Tags to remove from the run template.
            project: The project name/ID to filter by.

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
                name_id_or_prefix,
                project=project,
                hydrate=False,
            ).id

        return self.zen_store.update_run_template(
            template_id=template_id,
            template_update=RunTemplateUpdate(
                name=name,
                description=description,
                hidden=hidden,
                add_tags=add_tags,
                remove_tags=remove_tags,
            ),
        )

    def delete_run_template(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
    ) -> None:
        """Delete a run template.

        Args:
            name_id_or_prefix: Name/ID/ID prefix of the template to delete.
            project: The project name/ID to filter by.
        """
        if is_valid_uuid(name_id_or_prefix):
            template_id = (
                UUID(name_id_or_prefix)
                if isinstance(name_id_or_prefix, str)
                else name_id_or_prefix
            )
        else:
            template_id = self.get_run_template(
                name_id_or_prefix,
                project=project,
                hydrate=False,
            ).id

        self.zen_store.delete_run_template(template_id=template_id)

    # ------------------------------- Schedules --------------------------------

    def get_schedule(
        self,
        name_id_or_prefix: str | UUID,
        allow_name_prefix_match: bool = True,
        project: str | UUID | None = None,
        hydrate: bool = True,
    ) -> ScheduleResponse:
        """Get a schedule by name, id or prefix.

        Args:
            name_id_or_prefix: The name, id or prefix of the schedule.
            allow_name_prefix_match: If True, allow matching by name prefix.
            project: The project name/ID to filter by.
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
            project=project,
            hydrate=hydrate,
        )

    def list_schedules(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: UUID | str | None = None,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        name: str | None = None,
        project: str | UUID | None = None,
        user: UUID | str | None = None,
        pipeline_id: str | UUID | None = None,
        orchestrator_id: str | UUID | None = None,
        active: str | bool | None = None,
        cron_expression: str | None = None,
        start_time: datetime | str | None = None,
        end_time: datetime | str | None = None,
        interval_second: int | None = None,
        catchup: str | bool | None = None,
        hydrate: bool = False,
        run_once_start_time: datetime | str | None = None,
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
            project: The project name/ID to filter by.
            user: Filter by user name/ID.
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
            project=project or self.active_project.id,
            user=user,
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
        return self.zen_store.list_schedules(
            schedule_filter_model=schedule_filter_model,
            hydrate=hydrate,
        )

    def _get_orchestrator_for_schedule(
        self, schedule: ScheduleResponse
    ) -> Optional["BaseOrchestrator"]:
        """Get the orchestrator for a schedule.

        Args:
            schedule: The schedule to get the orchestrator for.

        Returns:
            The orchestrator for the schedule.
        """
        from zenml.orchestrators import BaseOrchestrator

        if not schedule.orchestrator_id:
            return None

        try:
            orchestrator_model = self.get_stack_component(
                component_type=StackComponentType.ORCHESTRATOR,
                name_id_or_prefix=schedule.orchestrator_id,
            )
        except KeyError:
            return None

        return cast(
            BaseOrchestrator, BaseOrchestrator.from_model(orchestrator_model)
        )

    def update_schedule(
        self,
        name_id_or_prefix: str | UUID,
        cron_expression: str | None = None,
    ) -> ScheduleResponse:
        """Update a schedule.

        Args:
            name_id_or_prefix: The name, id or prefix of the schedule to update.
            cron_expression: The new cron expression for the schedule.

        Returns:
            The updated schedule.
        """
        schedule = self.get_schedule(
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
            project=self.active_project.id,
        )

        orchestrator = self._get_orchestrator_for_schedule(schedule)
        if not orchestrator:
            logger.warning(
                "Unable to find orchestrator for schedule, skipping update."
            )
            return schedule
        elif not orchestrator.supports_schedule_updates:
            logger.warning(
                "Orchestrator does not support schedule updates, skipping "
                "update."
            )
            return schedule

        update = ScheduleUpdate(cron_expression=cron_expression)
        orchestrator.update_schedule(schedule, update)
        return self.zen_store.update_schedule(
            schedule_id=schedule.id,
            schedule_update=update,
        )

    def delete_schedule(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
    ) -> None:
        """Delete a schedule.

        Args:
            name_id_or_prefix: The name, id or prefix id of the schedule
                to delete.
            project: The project name/ID to filter by.
        """
        schedule = self.get_schedule(
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
            project=project,
        )

        orchestrator = self._get_orchestrator_for_schedule(schedule)
        if not orchestrator:
            logger.warning(
                "Unable to find orchestrator for schedule. Will only delete "
                "the schedule reference from ZenML."
            )
        elif not orchestrator.supports_schedule_deletion:
            logger.warning(
                "Orchestrator does not support schedule deletion. Will only "
                "delete the schedule reference from ZenML."
            )
        else:
            orchestrator.delete_schedule(schedule)

        self.zen_store.delete_schedule(schedule_id=schedule.id)

    # ----------------------------- Pipeline runs ------------------------------

    def get_pipeline_run(
        self,
        name_id_or_prefix: str | UUID,
        allow_name_prefix_match: bool = True,
        project: str | UUID | None = None,
        hydrate: bool = True,
        include_full_metadata: bool = False,
    ) -> PipelineRunResponse:
        """Gets a pipeline run by name, ID, or prefix.

        Args:
            name_id_or_prefix: Name, ID, or prefix of the pipeline run.
            allow_name_prefix_match: If True, allow matching by name prefix.
            project: The project name/ID to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            include_full_metadata: If True, include metadata of all steps in
                the response.

        Returns:
            The pipeline run.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_run,
            list_method=self.list_pipeline_runs,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            project=project,
            hydrate=hydrate,
            include_full_metadata=include_full_metadata,
        )

    def list_pipeline_runs(
        self,
        sort_by: str = "desc:created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: UUID | str | None = None,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        name: str | None = None,
        project: str | UUID | None = None,
        pipeline_id: str | UUID | None = None,
        pipeline_name: str | None = None,
        stack_id: str | UUID | None = None,
        schedule_id: str | UUID | None = None,
        build_id: str | UUID | None = None,
        snapshot_id: str | UUID | None = None,
        code_repository_id: str | UUID | None = None,
        template_id: str | UUID | None = None,
        source_snapshot_id: str | UUID | None = None,
        model_version_id: str | UUID | None = None,
        linked_to_model_version_id: str | UUID | None = None,
        orchestrator_run_id: str | None = None,
        status: str | None = None,
        start_time: datetime | str | None = None,
        end_time: datetime | str | None = None,
        unlisted: bool | None = None,
        templatable: bool | None = None,
        tag: str | None = None,
        tags: list[str] | None = None,
        user: UUID | str | None = None,
        run_metadata: list[str] | None = None,
        pipeline: UUID | str | None = None,
        code_repository: UUID | str | None = None,
        model: UUID | str | None = None,
        stack: UUID | str | None = None,
        stack_component: UUID | str | None = None,
        in_progress: bool | None = None,
        hydrate: bool = False,
        include_full_metadata: bool = False,
        triggered_by_step_run_id: UUID | str | None = None,
        triggered_by_deployment_id: UUID | str | None = None,
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
            project: The project name/ID to filter by.
            pipeline_id: The id of the pipeline to filter by.
            pipeline_name: DEPRECATED. Use `pipeline` instead to filter by
                pipeline name.
            stack_id: The id of the stack to filter by.
            schedule_id: The id of the schedule to filter by.
            build_id: The id of the build to filter by.
            snapshot_id: The id of the snapshot to filter by.
            code_repository_id: The id of the code repository to filter by.
            template_id: The ID of the template to filter by.
            source_snapshot_id: The ID of the source snapshot to filter by.
            model_version_id: The ID of the model version to filter by.
            linked_to_model_version_id: Filter by model version linked to the
                pipeline run. The difference to `model_version_id` is that this
                filter will not only include pipeline runs which are directly
                linked to the model version, but also if any step run is linked
                to the model version.
            orchestrator_run_id: The run id of the orchestrator to filter by.
            name: The name of the run to filter by.
            status: The status of the pipeline run
            start_time: The start_time for the pipeline run
            end_time: The end_time for the pipeline run
            unlisted: If the runs should be unlisted or not.
            templatable: If the runs should be templatable or not.
            tag: Tag to filter by.
            tags: Tags to filter by.
            user: The name/ID of the user to filter by.
            run_metadata: The run_metadata of the run to filter by.
            pipeline: The name/ID of the pipeline to filter by.
            code_repository: Filter by code repository name/ID.
            model: Filter by model name/ID.
            stack: Filter by stack name/ID.
            stack_component: Filter by stack component name/ID.
            in_progress: Filter by in_progress.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            include_full_metadata: If True, include metadata of all steps in
                the response.
            triggered_by_step_run_id: The ID of the step run that triggered
                the pipeline run.
            triggered_by_deployment_id: The ID of the deployment that triggered
                the pipeline run.

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
            project=project or self.active_project.id,
            pipeline_id=pipeline_id,
            pipeline_name=pipeline_name,
            schedule_id=schedule_id,
            build_id=build_id,
            snapshot_id=snapshot_id,
            code_repository_id=code_repository_id,
            template_id=template_id,
            source_snapshot_id=source_snapshot_id,
            model_version_id=model_version_id,
            linked_to_model_version_id=linked_to_model_version_id,
            orchestrator_run_id=orchestrator_run_id,
            stack_id=stack_id,
            status=status,
            start_time=start_time,
            end_time=end_time,
            tag=tag,
            tags=tags,
            unlisted=unlisted,
            user=user,
            run_metadata=run_metadata,
            pipeline=pipeline,
            code_repository=code_repository,
            stack=stack,
            model=model,
            stack_component=stack_component,
            in_progress=in_progress,
            templatable=templatable,
            triggered_by_step_run_id=triggered_by_step_run_id,
            triggered_by_deployment_id=triggered_by_deployment_id,
        )
        return self.zen_store.list_runs(
            runs_filter_model=runs_filter_model,
            hydrate=hydrate,
            include_full_metadata=include_full_metadata,
        )

    def delete_pipeline_run(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
    ) -> None:
        """Deletes a pipeline run.

        Args:
            name_id_or_prefix: Name, ID, or prefix of the pipeline run.
            project: The project name/ID to filter by.
        """
        run = self.get_pipeline_run(
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
            project=project,
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
        id: UUID | str | None = None,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        name: str | None = None,
        cache_key: str | None = None,
        cache_expires_at: datetime | str | None = None,
        cache_expired: bool | None = None,
        code_hash: str | None = None,
        status: str | None = None,
        start_time: datetime | str | None = None,
        end_time: datetime | str | None = None,
        pipeline_run_id: str | UUID | None = None,
        snapshot_id: str | UUID | None = None,
        original_step_run_id: str | UUID | None = None,
        project: str | UUID | None = None,
        user: UUID | str | None = None,
        model_version_id: str | UUID | None = None,
        model: UUID | str | None = None,
        run_metadata: list[str] | None = None,
        exclude_retried: bool | None = None,
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
            project: The project name/ID to filter by.
            user: Filter by user name/ID.
            pipeline_run_id: The id of the pipeline run to filter by.
            snapshot_id: The id of the snapshot to filter by.
            original_step_run_id: The id of the original step run to filter by.
            model_version_id: The ID of the model version to filter by.
            model: Filter by model name/ID.
            name: The name of the step run to filter by.
            cache_key: The cache key of the step run to filter by.
            cache_expires_at: The cache expiration time of the step run to
                filter by.
            cache_expired: Whether the cache expiration time of the step run
                has passed.
            code_hash: The code hash of the step run to filter by.
            status: The name of the run to filter by.
            run_metadata: Filter by run metadata.
            exclude_retried: Whether to exclude retried step runs.
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
            cache_key=cache_key,
            cache_expires_at=cache_expires_at,
            cache_expired=cache_expired,
            code_hash=code_hash,
            pipeline_run_id=pipeline_run_id,
            snapshot_id=snapshot_id,
            original_step_run_id=original_step_run_id,
            status=status,
            created=created,
            updated=updated,
            start_time=start_time,
            end_time=end_time,
            name=name,
            project=project or self.active_project.id,
            user=user,
            model_version_id=model_version_id,
            model=model,
            run_metadata=run_metadata,
            exclude_retried=exclude_retried,
        )
        return self.zen_store.list_run_steps(
            step_run_filter_model=step_run_filter_model,
            hydrate=hydrate,
        )

    def update_step_run(
        self,
        step_run_id: UUID,
        cache_expires_at: datetime | None = None,
    ) -> StepRunResponse:
        """Update a step run.

        Args:
            step_run_id: The ID of the step run to update.
            cache_expires_at: The time at which this step run should not be
                used for cached results anymore.

        Returns:
            The updated step run.
        """
        update = StepRunUpdate(cache_expires_at=cache_expires_at)
        return self.zen_store.update_run_step(
            step_run_id=step_run_id, step_run_update=update
        )

    # ------------------------------- Artifacts -------------------------------

    def get_artifact(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
        hydrate: bool = False,
    ) -> ArtifactResponse:
        """Get an artifact by name, id or prefix.

        Args:
            name_id_or_prefix: The name, ID or prefix of the artifact to get.
            project: The project name/ID to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The artifact.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_artifact,
            list_method=self.list_artifacts,
            name_id_or_prefix=name_id_or_prefix,
            project=project,
            hydrate=hydrate,
        )

    def list_artifacts(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: UUID | str | None = None,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        name: str | None = None,
        has_custom_name: bool | None = None,
        user: UUID | str | None = None,
        project: str | UUID | None = None,
        hydrate: bool = False,
        tag: str | None = None,
        tags: list[str] | None = None,
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
            user: Filter by user name or ID.
            project: The project name/ID to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            tag: Filter artifacts by tag.
            tags: Tags to filter by.

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
            tags=tags,
            user=user,
            project=project or self.active_project.id,
        )
        return self.zen_store.list_artifacts(
            artifact_filter_model,
            hydrate=hydrate,
        )

    def update_artifact(
        self,
        name_id_or_prefix: str | UUID,
        new_name: str | None = None,
        add_tags: list[str] | None = None,
        remove_tags: list[str] | None = None,
        has_custom_name: bool | None = None,
        project: str | UUID | None = None,
    ) -> ArtifactResponse:
        """Update an artifact.

        Args:
            name_id_or_prefix: The name, ID or prefix of the artifact to update.
            new_name: The new name of the artifact.
            add_tags: Tags to add to the artifact.
            remove_tags: Tags to remove from the artifact.
            has_custom_name: Whether the artifact has a custom name.
            project: The project name/ID to filter by.

        Returns:
            The updated artifact.
        """
        artifact = self.get_artifact(
            name_id_or_prefix=name_id_or_prefix,
            project=project,
        )
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
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
    ) -> None:
        """Delete an artifact.

        Args:
            name_id_or_prefix: The name, ID or prefix of the artifact to delete.
            project: The project name/ID to filter by.
        """
        artifact = self.get_artifact(
            name_id_or_prefix=name_id_or_prefix,
            project=project,
        )
        self.zen_store.delete_artifact(artifact_id=artifact.id)
        logger.info(f"Deleted artifact '{artifact.name}'.")

    def prune_artifacts(
        self,
        only_versions: bool = True,
        delete_from_artifact_store: bool = False,
        project: str | UUID | None = None,
    ) -> None:
        """Delete all unused artifacts and artifact versions.

        Args:
            only_versions: Only delete artifact versions, keeping artifacts
            delete_from_artifact_store: Delete data from artifact metadata
            project: The project name/ID to filter by.
        """
        if delete_from_artifact_store:
            unused_artifact_versions = depaginate(
                self.list_artifact_versions,
                only_unused=True,
                project=project,
            )
            for unused_artifact_version in unused_artifact_versions:
                self._delete_artifact_from_artifact_store(
                    unused_artifact_version
                )

        project = project or self.active_project.id

        self.zen_store.prune_artifact_versions(
            project_name_or_id=project, only_versions=only_versions
        )
        logger.info("All unused artifacts and artifact versions deleted.")

    # --------------------------- Artifact Versions ---------------------------

    def get_artifact_version(
        self,
        name_id_or_prefix: str | UUID,
        version: str | None = None,
        project: str | UUID | None = None,
        hydrate: bool = True,
    ) -> ArtifactVersionResponse:
        """Get an artifact version by ID or artifact name.

        Args:
            name_id_or_prefix: Either the ID of the artifact version or the
                name of the artifact.
            version: The version of the artifact to get. Only used if
                `name_id_or_prefix` is the name of the artifact. If not
                specified, the latest version is returned.
            project: The project name/ID to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The artifact version.
        """
        from zenml import get_step_context

        if cll := client_lazy_loader(
            method_name="get_artifact_version",
            name_id_or_prefix=name_id_or_prefix,
            version=version,
            project=project,
            hydrate=hydrate,
        ):
            return cll  # type: ignore[return-value]

        artifact = self._get_entity_version_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_artifact_version,
            list_method=self.list_artifact_versions,
            name_id_or_prefix=name_id_or_prefix,
            version=version,
            project=project,
            hydrate=hydrate,
        )
        try:
            step_run = get_step_context().step_run
            client = Client()
            client.zen_store.update_run_step(
                step_run_id=step_run.id,
                step_run_update=StepRunUpdate(
                    loaded_artifact_versions={artifact.name: artifact.id}
                ),
            )
        except RuntimeError:
            pass  # Cannot link to step run if called outside a step
        return artifact

    def list_artifact_versions(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: UUID | str | None = None,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        artifact: str | UUID | None = None,
        name: str | None = None,
        version: str | int | None = None,
        version_number: int | None = None,
        artifact_store_id: str | UUID | None = None,
        type: ArtifactType | str | None = None,
        data_type: str | None = None,
        uri: str | None = None,
        materializer: str | None = None,
        project: str | UUID | None = None,
        model_version_id: str | UUID | None = None,
        only_unused: bool | None = False,
        has_custom_name: bool | None = None,
        user: UUID | str | None = None,
        model: UUID | str | None = None,
        pipeline_run: UUID | str | None = None,
        run_metadata: list[str] | None = None,
        tag: str | None = None,
        tags: list[str] | None = None,
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
            artifact: The name or ID of the artifact to filter by.
            name: The name of the artifact to filter by.
            version: The version of the artifact to filter by.
            version_number: The version number of the artifact to filter by.
            artifact_store_id: The id of the artifact store to filter by.
            type: The type of the artifact to filter by.
            data_type: The data type of the artifact to filter by.
            uri: The uri of the artifact to filter by.
            materializer: The materializer of the artifact to filter by.
            project: The project name/ID to filter by.
            model_version_id: Filter by model version ID.
            only_unused: Only return artifact versions that are not used in
                any pipeline runs.
            has_custom_name: Filter artifacts with/without custom names.
            tag: A tag to filter by.
            tags: Tags to filter by.
            user: Filter by user name or ID.
            model: Filter by model name or ID.
            pipeline_run: Filter by pipeline run name or ID.
            run_metadata: Filter by run metadata.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of artifact versions.
        """
        if name:
            artifact = name

        artifact_version_filter_model = ArtifactVersionFilter(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            created=created,
            updated=updated,
            artifact=artifact,
            version=str(version) if version else None,
            version_number=version_number,
            artifact_store_id=artifact_store_id,
            type=type,
            data_type=data_type,
            uri=uri,
            materializer=materializer,
            project=project or self.active_project.id,
            model_version_id=model_version_id,
            only_unused=only_unused,
            has_custom_name=has_custom_name,
            tag=tag,
            tags=tags,
            user=user,
            model=model,
            pipeline_run=pipeline_run,
            run_metadata=run_metadata,
        )
        return self.zen_store.list_artifact_versions(
            artifact_version_filter_model,
            hydrate=hydrate,
        )

    def update_artifact_version(
        self,
        name_id_or_prefix: str | UUID,
        version: str | None = None,
        add_tags: list[str] | None = None,
        remove_tags: list[str] | None = None,
        project: str | UUID | None = None,
    ) -> ArtifactVersionResponse:
        """Update an artifact version.

        Args:
            name_id_or_prefix: The name, ID or prefix of the artifact to update.
            version: The version of the artifact to update. Only used if
                `name_id_or_prefix` is the name of the artifact. If not
                specified, the latest version is updated.
            add_tags: Tags to add to the artifact version.
            remove_tags: Tags to remove from the artifact version.
            project: The project name/ID to filter by.

        Returns:
            The updated artifact version.
        """
        artifact_version = self.get_artifact_version(
            name_id_or_prefix=name_id_or_prefix,
            version=version,
            project=project,
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
        name_id_or_prefix: str | UUID,
        version: str | None = None,
        delete_metadata: bool = True,
        delete_from_artifact_store: bool = False,
        project: str | UUID | None = None,
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
            project: The project name/ID to filter by.
        """
        artifact_version = self.get_artifact_version(
            name_id_or_prefix=name_id_or_prefix,
            version=version,
            project=project,
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
        metadata: dict[str, "MetadataType"],
        resources: list[RunMetadataResource],
        stack_component_id: UUID | None = None,
        publisher_step_id: UUID | None = None,
    ) -> None:
        """Create run metadata.

        Args:
            metadata: The metadata to create as a dictionary of key-value pairs.
            resources: The list of IDs and types of the resources for that the
                metadata was produced.
            stack_component_id: The ID of the stack component that produced
                the metadata.
            publisher_step_id: The ID of the step execution that publishes
                this metadata automatically.
        """
        from zenml.metadata.metadata_types import get_metadata_type

        values: dict[str, "MetadataType"] = {}
        types: dict[str, "MetadataTypeEnum"] = {}
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
            project=self.active_project.id,
            resources=resources,
            stack_component_id=stack_component_id,
            publisher_step_id=publisher_step_id,
            values=values,
            types=types,
        )
        self.zen_store.create_run_metadata(run_metadata)

    # -------------------------------- Secrets ---------------------------------

    def create_secret(
        self,
        name: str,
        values: dict[str, str],
        private: bool = False,
    ) -> SecretResponse:
        """Creates a new secret.

        Args:
            name: The name of the secret.
            values: The values of the secret.
            private: Whether the secret is private. A private secret is only
                accessible to the user who created it.

        Returns:
            The created secret (in model form).

        Raises:
            NotImplementedError: If centralized secrets management is not
                enabled.
        """
        create_secret_request = SecretRequest(
            name=name,
            values=values,
            private=private,
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
        name_id_or_prefix: str | UUID,
        private: bool | None = None,
        allow_partial_name_match: bool = True,
        allow_partial_id_match: bool = True,
        hydrate: bool = True,
    ) -> SecretResponse:
        """Get a secret.

        Get a secret identified by a name, ID or prefix of the name or ID and
        optionally a scope.

        If a private status is not provided, privately scoped secrets will be
        searched for first, followed by publicly scoped secrets. When a name or
        prefix is used instead of a UUID value, each scope is first searched for
        an exact match, then for a ID prefix or name substring match before
        moving on to the next scope.

        Args:
            name_id_or_prefix: The name, ID or prefix to the id of the secret
                to get.
            private: Whether the secret is private. If not set, all secrets will
                be searched for, prioritizing privately scoped secrets.
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
                if private is not None and secret.private != private:
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

        # Private statuses to search in order of priority
        search_private_statuses = (
            [False, True] if private is None else [private]
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

        for search_private_status in search_private_statuses:
            partial_matches: list[SecretResponse] = []
            for secret in secrets.items:
                if secret.private != search_private_status:
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
        private_status = ""
        if private is not None:
            private_status = "private " if private else "public "
        msg = (
            f"No {private_status}secret found with name, ID or prefix "
            f"'{name_id_or_prefix}'"
        )

        raise KeyError(msg)

    def list_secrets(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: UUID | str | None = None,
        created: datetime | None = None,
        updated: datetime | None = None,
        name: str | None = None,
        private: bool | None = None,
        user: UUID | str | None = None,
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
            private: The private status of the secret to filter by.
            user: Filter by user name/ID.
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
            user=user,
            name=name,
            private=private,
            id=id,
            created=created,
            updated=updated,
        )
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
        name_id_or_prefix: str | UUID,
        private: bool | None = None,
        new_name: str | None = None,
        update_private: bool | None = None,
        add_or_update_values: dict[str, str] | None = None,
        remove_values: list[str] | None = None,
    ) -> SecretResponse:
        """Updates a secret.

        Args:
            name_id_or_prefix: The name, id or prefix of the id for the
                secret to update.
            private: The private status of the secret to update.
            new_name: The new name of the secret.
            update_private: New value used to update the private status of the
                secret.
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
            private=private,
            # Don't allow partial name matches, but allow partial ID matches
            allow_partial_name_match=False,
            allow_partial_id_match=True,
            hydrate=True,
        )

        secret_update = SecretUpdate(name=new_name or secret.name)

        if update_private:
            secret_update.private = update_private
        values: dict[str, SecretStr | None] = {}
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
        self, name_id_or_prefix: str, private: bool | None = None
    ) -> None:
        """Deletes a secret.

        Args:
            name_id_or_prefix: The name or ID of the secret.
            private: The private status of the secret to delete.
        """
        secret = self.get_secret(
            name_id_or_prefix=name_id_or_prefix,
            private=private,
            # Don't allow partial name matches, but allow partial ID matches
            allow_partial_name_match=False,
            allow_partial_id_match=True,
        )

        self.zen_store.delete_secret(secret_id=secret.id)

    def get_secret_by_name_and_private_status(
        self,
        name: str,
        private: bool | None = None,
        hydrate: bool = True,
    ) -> SecretResponse:
        """Fetches a registered secret with a given name and optional private status.

        This is a version of get_secret that restricts the search to a given
        name and an optional private status, without doing any prefix or UUID
        matching.

        If no private status is provided, the search will be done first for
        private secrets, then for public secrets.

        Args:
            name: The name of the secret to get.
            private: The private status of the secret to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The registered secret.

        Raises:
            KeyError: If no secret exists for the given name in the given scope.
        """
        logger.debug(
            f"Fetching the secret with name '{name}' and private status "
            f"'{private}'."
        )

        # Private statuses to search in order of priority
        search_private_statuses = (
            [False, True] if private is None else [private]
        )

        for search_private_status in search_private_statuses:
            secrets = self.list_secrets(
                logical_operator=LogicalOperators.AND,
                name=f"equals:{name}",
                private=search_private_status,
                hydrate=hydrate,
            )

            if len(secrets.items) >= 1:
                # Need to fetch the secret again to get the secret values
                return self.zen_store.get_secret(
                    secret_id=secrets.items[0].id, hydrate=hydrate
                )

        private_status = ""
        if private is not None:
            private_status = "private " if private else "public "
        msg = f"No {private_status}secret with name '{name}' was found"

        raise KeyError(msg)

    def list_secrets_by_private_status(
        self,
        private: bool,
        hydrate: bool = False,
    ) -> Page[SecretResponse]:
        """Fetches the list of secrets with a given private status.

        The returned secrets do not contain the secret values. To get the
        secret values, use `get_secret` individually for each secret.

        Args:
            private: The private status of the secrets to search for.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The list of secrets in the given scope without the secret values.
        """
        logger.debug(f"Fetching the secrets with private status '{private}'.")

        return self.list_secrets(private=private, hydrate=hydrate)

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

    @staticmethod
    def _validate_code_repository_config(
        source: Source, config: dict[str, Any]
    ) -> None:
        """Validate a code repository config.

        Args:
            source: The code repository source.
            config: The code repository config.

        Raises:
            RuntimeError: If the provided config is invalid.
        """
        from zenml.code_repositories import BaseCodeRepository

        code_repo_class: type[BaseCodeRepository] = (
            source_utils.load_and_validate_class(
                source=source, expected_class=BaseCodeRepository
            )
        )
        try:
            code_repo_class.validate_config(config)
        except Exception as e:
            raise RuntimeError(
                "Failed to validate code repository config."
            ) from e

    def create_code_repository(
        self,
        name: str,
        config: dict[str, Any],
        source: Source,
        description: str | None = None,
        logo_url: str | None = None,
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
        """
        self._validate_code_repository_config(source=source, config=config)
        repo_request = CodeRepositoryRequest(
            project=self.active_project.id,
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
        name_id_or_prefix: str | UUID,
        allow_name_prefix_match: bool = True,
        project: str | UUID | None = None,
        hydrate: bool = True,
    ) -> CodeRepositoryResponse:
        """Get a code repository by name, id or prefix.

        Args:
            name_id_or_prefix: The name, ID or ID prefix of the code repository.
            allow_name_prefix_match: If True, allow matching by name prefix.
            project: The project name/ID to filter by.
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
            project=project,
        )

    def list_code_repositories(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: UUID | str | None = None,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        name: str | None = None,
        project: str | UUID | None = None,
        user: UUID | str | None = None,
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
            project: The project name/ID to filter by.
            user: Filter by user name/ID.
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
            project=project or self.active_project.id,
            user=user,
        )
        return self.zen_store.list_code_repositories(
            filter_model=filter_model,
            hydrate=hydrate,
        )

    def update_code_repository(
        self,
        name_id_or_prefix: UUID | str,
        name: str | None = None,
        description: str | None = None,
        logo_url: str | None = None,
        config: dict[str, Any] | None = None,
        project: str | UUID | None = None,
    ) -> CodeRepositoryResponse:
        """Update a code repository.

        Args:
            name_id_or_prefix: Name, ID or prefix of the code repository to
                update.
            name: New name of the code repository.
            description: New description of the code repository.
            logo_url: New logo URL of the code repository.
            config: New configuration options for the code repository. Will
                be used to update the existing configuration values. To remove
                values from the existing configuration, set the value for that
                key to `None`.
            project: The project name/ID to filter by.

        Returns:
            The updated code repository.
        """
        repo = self.get_code_repository(
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
            project=project,
        )
        update = CodeRepositoryUpdate(
            name=name, description=description, logo_url=logo_url
        )
        if config is not None:
            combined_config = repo.config
            combined_config.update(config)
            combined_config = {
                k: v for k, v in combined_config.items() if v is not None
            }

            self._validate_code_repository_config(
                source=repo.source, config=combined_config
            )
            update.config = combined_config

        return self.zen_store.update_code_repository(
            code_repository_id=repo.id, update=update
        )

    def delete_code_repository(
        self,
        name_id_or_prefix: str | UUID,
        project: str | UUID | None = None,
    ) -> None:
        """Delete a code repository.

        Args:
            name_id_or_prefix: The name, ID or prefix of the code repository.
            project: The project name/ID to filter by.
        """
        repo = self.get_code_repository(
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=False,
            project=project,
        )
        self.zen_store.delete_code_repository(code_repository_id=repo.id)

    # --------------------------- Service Connectors ---------------------------

    def create_service_connector(
        self,
        name: str,
        connector_type: str,
        resource_type: str | None = None,
        auth_method: str | None = None,
        configuration: dict[str, str] | None = None,
        resource_id: str | None = None,
        description: str = "",
        expiration_seconds: int | None = None,
        expires_at: datetime | None = None,
        expires_skew_tolerance: int | None = None,
        labels: dict[str, str] | None = None,
        auto_configure: bool = False,
        verify: bool = True,
        list_resources: bool = True,
        register: bool = True,
    ) -> tuple[
        None | (
                ServiceConnectorResponse |
                ServiceConnectorRequest
        ),
        ServiceConnectorResourcesModel | None,
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

        connector_instance: ServiceConnector | None = None
        connector_resources: ServiceConnectorResourcesModel | None = None

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
        name_id_or_prefix: str | UUID,
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
        expand_secrets: bool = False,
    ) -> ServiceConnectorResponse:
        """Fetches a registered service connector.

        Args:
            name_id_or_prefix: The id of the service connector to fetch.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            expand_secrets: If True, expand the secrets for the service
                connector.

        Returns:
            The registered service connector.
        """
        connector = self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_service_connector,
            list_method=self.list_service_connectors,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
            hydrate=hydrate,
            expand_secrets=expand_secrets,
        )

        return connector

    def list_service_connectors(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: UUID | str | None = None,
        created: datetime | None = None,
        updated: datetime | None = None,
        name: str | None = None,
        connector_type: str | None = None,
        auth_method: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        user: UUID | str | None = None,
        labels: dict[str, str | None] | None = None,
        hydrate: bool = False,
        expand_secrets: bool = False,
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
            user: Filter by user name/ID.
            name: The name of the service connector to filter by.
            labels: The labels of the service connector to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            expand_secrets: If True, expand the secrets for the service
                connectors.

        Returns:
            A page of service connectors.
        """
        connector_filter_model = ServiceConnectorFilter(
            page=page,
            size=size,
            sort_by=sort_by,
            logical_operator=logical_operator,
            user=user,
            name=name,
            connector_type=connector_type,
            auth_method=auth_method,
            resource_type=resource_type,
            resource_id=resource_id,
            id=id,
            created=created,
            updated=updated,
            labels=labels,
        )
        return self.zen_store.list_service_connectors(
            filter_model=connector_filter_model,
            hydrate=hydrate,
            expand_secrets=expand_secrets,
        )

    def update_service_connector(
        self,
        name_id_or_prefix: UUID | str,
        name: str | None = None,
        auth_method: str | None = None,
        resource_type: str | None = None,
        configuration: dict[str, str] | None = None,
        resource_id: str | None = None,
        description: str | None = None,
        expires_at: datetime | None = None,
        expires_skew_tolerance: int | None = None,
        expiration_seconds: int | None = None,
        labels: dict[str, str | None] | None = None,
        verify: bool = True,
        list_resources: bool = True,
        update: bool = True,
    ) -> tuple[
        None | (
                ServiceConnectorResponse |
                ServiceConnectorUpdate
        ),
        ServiceConnectorResourcesModel | None,
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
            # We need the existing secrets only if a new configuration is not
            # provided.
            expand_secrets=configuration is None,
        )

        connector_instance: ServiceConnector | None = None
        connector_resources: ServiceConnectorResourcesModel | None = None

        if isinstance(connector_model.connector_type, str):
            connector = self.get_service_connector_type(
                connector_model.connector_type
            )
        else:
            connector = connector_model.connector_type

        resource_types: str | list[str] | None = None
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
        connector_update.validate_and_configure_resources(
            connector_type=connector,
            resource_types=resource_types,
            resource_id=resource_id,
            # The supplied configuration is a drop-in replacement for the
            # existing configuration
            configuration=configuration
            if configuration is not None
            else connector_model.configuration,
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
        name_id_or_prefix: str | UUID,
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
        name_id_or_prefix: UUID | str,
        resource_type: str | None = None,
        resource_id: str | None = None,
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
            # Get the service connector model, with full secrets
            service_connector = self.get_service_connector(
                name_id_or_prefix=name_id_or_prefix,
                allow_name_prefix_match=False,
                expand_secrets=True,
            )
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
        name_id_or_prefix: UUID | str,
        resource_type: str | None = None,
        resource_id: str | None = None,
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
        name_id_or_prefix: UUID | str,
        resource_type: str | None = None,
        resource_id: str | None = None,
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
            # Get the service connector model, with full secrets
            service_connector = self.get_service_connector(
                name_id_or_prefix=name_id_or_prefix,
                allow_name_prefix_match=False,
                expand_secrets=True,
            )
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
        connector_type: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> list[ServiceConnectorResourcesModel]:
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
            ServiceConnectorFilter(
                connector_type=connector_type,
                resource_type=resource_type,
                resource_id=resource_id,
            )
        )

    def list_service_connector_types(
        self,
        connector_type: str | None = None,
        resource_type: str | None = None,
        auth_method: str | None = None,
    ) -> list[ServiceConnectorTypeModel]:
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
        license: str | None = None,
        description: str | None = None,
        audience: str | None = None,
        use_cases: str | None = None,
        limitations: str | None = None,
        trade_offs: str | None = None,
        ethics: str | None = None,
        tags: list[str] | None = None,
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
                project=self.active_project.id,
                save_models_to_registry=save_models_to_registry,
            )
        )

    def delete_model(
        self,
        model_name_or_id: str | UUID,
        project: str | UUID | None = None,
    ) -> None:
        """Deletes a model from Model Control Plane.

        Args:
            model_name_or_id: name or id of the model to be deleted.
            project: The project name/ID to filter by.
        """
        model = self.get_model(
            model_name_or_id=model_name_or_id, project=project
        )
        self.zen_store.delete_model(model_id=model.id)

    def update_model(
        self,
        model_name_or_id: str | UUID,
        name: str | None = None,
        license: str | None = None,
        description: str | None = None,
        audience: str | None = None,
        use_cases: str | None = None,
        limitations: str | None = None,
        trade_offs: str | None = None,
        ethics: str | None = None,
        add_tags: list[str] | None = None,
        remove_tags: list[str] | None = None,
        save_models_to_registry: bool | None = None,
        project: str | UUID | None = None,
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
            project: The project name/ID to filter by.

        Returns:
            The updated model.
        """
        model = self.get_model(
            model_name_or_id=model_name_or_id, project=project
        )
        return self.zen_store.update_model(
            model_id=model.id,
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
        model_name_or_id: str | UUID,
        project: str | UUID | None = None,
        hydrate: bool = True,
        bypass_lazy_loader: bool = False,
    ) -> ModelResponse:
        """Get an existing model from Model Control Plane.

        Args:
            model_name_or_id: name or id of the model to be retrieved.
            project: The project name/ID to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            bypass_lazy_loader: Whether to bypass the lazy loader.

        Returns:
            The model of interest.
        """
        if not bypass_lazy_loader:
            if cll := client_lazy_loader(
                "get_model",
                model_name_or_id=model_name_or_id,
                hydrate=hydrate,
                project=project,
            ):
                return cll  # type: ignore[return-value]

        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_model,
            list_method=self.list_models,
            name_id_or_prefix=model_name_or_id,
            project=project,
            hydrate=hydrate,
        )

    def list_models(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        name: str | None = None,
        id: UUID | str | None = None,
        user: UUID | str | None = None,
        project: str | UUID | None = None,
        hydrate: bool = False,
        tag: str | None = None,
        tags: list[str] | None = None,
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
            id: The id of the model to filter by.
            user: Filter by user name/ID.
            project: The project name/ID to filter by.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            tag: The tag of the model to filter by.
            tags: Tags to filter by.

        Returns:
            A page object with all models.
        """
        filter = ModelFilter(
            name=name,
            id=id,
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            created=created,
            updated=updated,
            tag=tag,
            tags=tags,
            user=user,
            project=project or self.active_project.id,
        )

        return self.zen_store.list_models(
            model_filter_model=filter, hydrate=hydrate
        )

    #################
    # Model Versions
    #################

    def create_model_version(
        self,
        model_name_or_id: str | UUID,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        project: str | UUID | None = None,
    ) -> ModelVersionResponse:
        """Creates a new model version in Model Control Plane.

        Args:
            model_name_or_id: the name or id of the model to create model
                version in.
            name: the name of the Model Version to be created.
            description: the description of the Model Version to be created.
            tags: Tags associated with the model.
            project: The project name/ID to filter by.

        Returns:
            The newly created model version.
        """
        model = self.get_model(
            model_name_or_id=model_name_or_id, project=project
        )
        return self.zen_store.create_model_version(
            model_version=ModelVersionRequest(
                name=name,
                description=description,
                project=model.project_id,
                model=model.id,
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
        model_name_or_id: str | UUID | None = None,
        model_version_name_or_number_or_id: None | (
            str | int | ModelStages | UUID
        ) = None,
        project: str | UUID | None = None,
        hydrate: bool = True,
    ) -> ModelVersionResponse:
        """Get an existing model version from Model Control Plane.

        Args:
            model_name_or_id: name or id of the model containing the model
                version.
            model_version_name_or_number_or_id: name, id, stage or number of
                the model version to be retrieved. If skipped - latest version
                is retrieved.
            project: The project name/ID to filter by.
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
            project=project,
            hydrate=hydrate,
        ):
            return cll  # type: ignore[return-value]

        if model_version_name_or_number_or_id is None:
            model_version_name_or_number_or_id = ModelStages.LATEST

        if is_valid_uuid(model_version_name_or_number_or_id):
            assert not isinstance(model_version_name_or_number_or_id, int)
            model_version_id = (
                UUID(model_version_name_or_number_or_id)
                if isinstance(model_version_name_or_number_or_id, str)
                else model_version_name_or_number_or_id
            )
            return self.zen_store.get_model_version(
                model_version_id=model_version_id,
                hydrate=hydrate,
            )
        elif isinstance(model_version_name_or_number_or_id, int):
            model_versions = self.zen_store.list_model_versions(
                model_version_filter_model=ModelVersionFilter(
                    model=model_name_or_id,
                    number=model_version_name_or_number_or_id,
                    project=project or self.active_project.id,
                ),
                hydrate=hydrate,
            ).items
        elif isinstance(model_version_name_or_number_or_id, str):
            if model_version_name_or_number_or_id == ModelStages.LATEST:
                model_versions = self.zen_store.list_model_versions(
                    model_version_filter_model=ModelVersionFilter(
                        model=model_name_or_id,
                        sort_by=f"{SorterOps.DESCENDING}:number",
                        project=project or self.active_project.id,
                    ),
                    hydrate=hydrate,
                ).items

                if len(model_versions) > 0:
                    model_versions = [model_versions[0]]
                else:
                    model_versions = []
            elif model_version_name_or_number_or_id in ModelStages.values():
                model_versions = self.zen_store.list_model_versions(
                    model_version_filter_model=ModelVersionFilter(
                        model=model_name_or_id,
                        stage=model_version_name_or_number_or_id,
                        project=project or self.active_project.id,
                    ),
                    hydrate=hydrate,
                ).items
            else:
                model_versions = self.zen_store.list_model_versions(
                    model_version_filter_model=ModelVersionFilter(
                        model=model_name_or_id,
                        name=model_version_name_or_number_or_id,
                        project=project or self.active_project.id,
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
        model: str | UUID | None = None,
        model_name_or_id: str | UUID | None = None,
        sort_by: str = "number",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        name: str | None = None,
        id: UUID | str | None = None,
        number: int | None = None,
        stage: str | ModelStages | None = None,
        run_metadata: list[str] | None = None,
        user: UUID | str | None = None,
        hydrate: bool = False,
        tag: str | None = None,
        tags: list[str] | None = None,
        project: str | UUID | None = None,
    ) -> Page[ModelVersionResponse]:
        """Get model versions by filter from Model Control Plane.

        Args:
            model: The model to filter by.
            model_name_or_id: name or id of the model containing the model
                version.
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            name: name or id of the model version.
            id: id of the model version.
            number: number of the model version.
            stage: stage of the model version.
            run_metadata: run metadata of the model version.
            user: Filter by user name/ID.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            tag: The tag to filter by.
            tags: Tags to filter by.
            project: The project name/ID to filter by.

        Returns:
            A page object with all model versions.
        """
        if model_name_or_id:
            logger.warning(
                "The `model_name_or_id` argument is deprecated. "
                "Please use the `model` argument instead."
            )
            if model is None:
                model = model_name_or_id
            else:
                logger.warning(
                    "Ignoring `model_name_or_id` argument as `model` argument "
                    "was also provided."
                )

        model_version_filter_model = ModelVersionFilter(
            page=page,
            size=size,
            sort_by=sort_by,
            logical_operator=logical_operator,
            created=created,
            updated=updated,
            name=name,
            id=id,
            number=number,
            stage=stage,
            run_metadata=run_metadata,
            tag=tag,
            tags=tags,
            user=user,
            model=model,
            project=project or self.active_project.id,
        )

        return self.zen_store.list_model_versions(
            model_version_filter_model=model_version_filter_model,
            hydrate=hydrate,
        )

    def update_model_version(
        self,
        model_name_or_id: str | UUID,
        version_name_or_id: str | UUID,
        stage: str | ModelStages | None = None,
        force: bool = False,
        name: str | None = None,
        description: str | None = None,
        add_tags: list[str] | None = None,
        remove_tags: list[str] | None = None,
        project: str | UUID | None = None,
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
            project: The project name/ID to filter by.

        Returns:
            An updated model version.
        """
        if not is_valid_uuid(model_name_or_id):
            model = self.get_model(model_name_or_id, project=project)
            model_name_or_id = model.id
            project = project or model.project_id
        if not is_valid_uuid(version_name_or_id):
            version_name_or_id = self.get_model_version(
                model_name_or_id, version_name_or_id, project=project
            ).id

        return self.zen_store.update_model_version(
            model_version_id=version_name_or_id,  # type:ignore[arg-type]
            model_version_update_model=ModelVersionUpdate(
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
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        model_version_id: UUID | str | None = None,
        artifact_version_id: UUID | str | None = None,
        artifact_name: str | None = None,
        only_data_artifacts: bool | None = None,
        only_model_artifacts: bool | None = None,
        only_deployment_artifacts: bool | None = None,
        has_custom_name: bool | None = None,
        user: UUID | str | None = None,
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
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        model_version_id: UUID | str | None = None,
        pipeline_run_id: UUID | str | None = None,
        pipeline_run_name: str | None = None,
        user: UUID | str | None = None,
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
        id: UUID | str | None = None,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        expires: datetime | str | None = None,
        client_id: UUID | str | None = None,
        status: OAuthDeviceStatus | str | None = None,
        trusted_device: bool | str | None = None,
        user: UUID | str | None = None,
        failed_auth_attempts: int | str | None = None,
        last_login: datetime | str | None | None = None,
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
            user: Filter by user name/ID.
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
            user=user,
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
        id_or_prefix: UUID | str,
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
        id_or_prefix: UUID | str,
        locked: bool | None = None,
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
        id_or_prefix: str | UUID,
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
        """Get a trigger execution by ID.

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
        trigger_id: UUID | str | None = None,
        step_run_id: UUID | str | None = None,
        user: UUID | str | None = None,
        project: UUID | str | None = None,
        hydrate: bool = False,
    ) -> Page[TriggerExecutionResponse]:
        """List all trigger executions matching the given filter criteria.

        Args:
            sort_by: The column to sort by.
            page: The page of items.
            size: The maximum size of all pages.
            logical_operator: Which logical operator to use [and, or].
            trigger_id: ID of the trigger to filter by.
            step_run_id: ID of the step run to filter by.
            user: Filter by user name/ID.
            project: Filter by project name/ID.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all trigger executions matching the filter criteria.
        """
        filter_model = TriggerExecutionFilter(
            trigger_id=trigger_id,
            step_run_id=step_run_id,
            sort_by=sort_by,
            page=page,
            size=size,
            user=user,
            logical_operator=logical_operator,
            project=project or self.active_project.id,
        )
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
        name_id_or_prefix: str | UUID,
        allow_name_prefix_match: bool = True,
        project: str | UUID | None = None,
        hydrate: bool = True,
        **kwargs: Any,
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
            project: The project name/ID to filter by.
            **kwargs: Additional keyword arguments to pass to the get and list
                methods.

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
            return get_method(name_id_or_prefix, hydrate=hydrate, **kwargs)

        # If not a UUID, try to find by name
        assert not isinstance(name_id_or_prefix, UUID)
        list_kwargs: dict[str, Any] = dict(
            name=f"equals:{name_id_or_prefix}",
            hydrate=hydrate,
            **kwargs,
        )
        scope = ""
        if project:
            scope = f"in project {project} "
            list_kwargs["project"] = project
        entity = list_method(**list_kwargs)

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
                project=project,
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
            f"{entity.total} {entity_label} have been found {scope}that have "
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
        name_id_or_prefix: str | UUID,
        version: str | None,
        project: str | UUID | None = None,
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
        list_kwargs: dict[str, Any] = dict(
            size=1,
            sort_by="desc:created",
            name=name_id_or_prefix,
            version=version,
            hydrate=hydrate,
        )
        scope = ""
        if project:
            scope = f" in project {project}"
            list_kwargs["project"] = project
        exact_name_matches = list_method(**list_kwargs)

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
                f"{name_id_or_prefix}{scope}."
            )
        else:
            raise ZenKeyError(
                f"{partial_id_matches.total} {entity_label} have been found"
                f"{scope} that have an id prefix that matches the provided "
                f"string '{name_id_or_prefix}':\n"
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
        project: str | UUID | None = None,
        hydrate: bool = True,
        **kwargs: Any,
    ) -> AnyResponse:
        """Fetches an entity using a partial ID or name.

        Args:
            get_method: The method to use to fetch the entity by id.
            list_method: The method to use to fetch all entities.
            partial_id_or_name: The partial ID or name of the entity to fetch.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            project: The project name/ID to filter by.
            **kwargs: Additional keyword arguments to pass to the get and list
                methods.

        Returns:
            The entity with the given partial ID or name.

        Raises:
            KeyError: If no entity with the given partial ID or name is found.
            ZenKeyError: If there is more than one entity with that partial ID
                or name.
        """
        list_method_args: dict[str, Any] = {
            "logical_operator": LogicalOperators.OR,
            "id": f"startswith:{partial_id_or_name}",
            "hydrate": hydrate,
            **kwargs,
        }
        if allow_name_prefix_match:
            list_method_args["name"] = f"startswith:{partial_id_or_name}"
        scope = ""
        if project:
            scope = f"in project {project} "
            list_method_args["project"] = project

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
                f"No {entity_label} have been found{scope} that have "
                f"{prefix_description} that matches the provided string "
                f"'{partial_id_or_name}'."
            )

        # If more than one entity is found, raise an error.
        ambiguous_entities: list[str] = []
        for model in entity.items:
            model_name = getattr(model, "name", None)
            if model_name:
                ambiguous_entities.append(f"{model_name}: {model.id}")
            else:
                ambiguous_entities.append(str(model.id))
        raise ZenKeyError(
            f"{entity.total} {entity_label} have been found{scope} that have "
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
        full_name: str | None = None,
        description: str = "",
    ) -> ServiceAccountResponse:
        """Create a new service account.

        Args:
            name: The name of the service account.
            full_name: The display name of the service account.
            description: The description of the service account.

        Returns:
            The created service account.
        """
        service_account = ServiceAccountRequest(
            name=name,
            full_name=full_name or "",
            description=description,
            active=True,
        )
        created_service_account = self.zen_store.create_service_account(
            service_account=service_account
        )

        return created_service_account

    def get_service_account(
        self,
        name_id_or_prefix: str | UUID,
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
        id: UUID | str | None = None,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        name: str | None = None,
        description: str | None = None,
        active: bool | None = None,
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
        name_id_or_prefix: str | UUID,
        updated_name: str | None = None,
        description: str | None = None,
        active: bool | None = None,
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
        name_id_or_prefix: str | UUID,
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
        service_account_name_id_or_prefix: str | UUID,
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
        from zenml.login.credentials_store import get_credentials_store
        from zenml.zen_stores.rest_zen_store import RestZenStore

        zen_store = self.zen_store
        if not zen_store.TYPE == StoreType.REST:
            raise NotImplementedError(
                "API key configuration is only supported if connected to a "
                "ZenML server."
            )

        credentials_store = get_credentials_store()
        assert isinstance(zen_store, RestZenStore)

        credentials_store.set_api_key(server_url=zen_store.url, api_key=key)

        # Force a re-authentication to start using the new API key
        # right away.
        zen_store.authenticate(force=True)

    def list_api_keys(
        self,
        service_account_name_id_or_prefix: str | UUID,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: UUID | str | None = None,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        name: str | None = None,
        description: str | None = None,
        active: bool | None = None,
        last_login: datetime | str | None = None,
        last_rotated: datetime | str | None = None,
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
        service_account_name_id_or_prefix: str | UUID,
        name_id_or_prefix: str | UUID,
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
        service_account_name_id_or_prefix: str | UUID,
        name_id_or_prefix: UUID | str,
        name: str | None = None,
        description: str | None = None,
        active: bool | None = None,
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
        service_account_name_id_or_prefix: str | UUID,
        name_id_or_prefix: UUID | str,
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
        service_account_name_id_or_prefix: str | UUID,
        name_id_or_prefix: str | UUID,
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

    # ---------------------------------- Tags ----------------------------------
    def create_tag(
        self,
        name: str,
        exclusive: bool = False,
        color: str | ColorVariants | None = None,
    ) -> TagResponse:
        """Creates a new tag.

        Args:
            name: the name of the tag.
            exclusive: the boolean to decide whether the tag is an exclusive tag.
                An exclusive tag means that the tag can exist only for a single:
                    - pipeline run within the scope of a pipeline
                    - artifact version within the scope of an artifact
                    - run template
            color: the color of the tag

        Returns:
            The newly created tag.
        """
        request_model = TagRequest(name=name, exclusive=exclusive)

        if color is not None:
            request_model.color = ColorVariants(color)

        return self.zen_store.create_tag(tag=request_model)

    def delete_tag(
        self,
        tag_name_or_id: str | UUID,
    ) -> None:
        """Deletes a tag.

        Args:
            tag_name_or_id: name or id of the tag to be deleted.
        """
        tag = self.get_tag(tag_name_or_id, allow_name_prefix_match=False)
        self.zen_store.delete_tag(tag_id=tag.id)

    def update_tag(
        self,
        tag_name_or_id: str | UUID,
        name: str | None = None,
        exclusive: bool | None = None,
        color: str | ColorVariants | None = None,
    ) -> TagResponse:
        """Updates an existing tag.

        Args:
            tag_name_or_id: name or UUID of the tag to be updated.
            name: the name of the tag.
            exclusive: the boolean to decide whether the tag is an exclusive tag.
                An exclusive tag means that the tag can exist only for a single:
                    - pipeline run within the scope of a pipeline
                    - artifact version within the scope of an artifact
                    - run template
            color: the color of the tag

        Returns:
            The updated tag.
        """
        update_model = TagUpdate()

        if name is not None:
            update_model.name = name

        if exclusive is not None:
            update_model.exclusive = exclusive

        if color is not None:
            if isinstance(color, str):
                update_model.color = ColorVariants(color)
            else:
                update_model.color = color

        tag = self.get_tag(tag_name_or_id, allow_name_prefix_match=False)

        return self.zen_store.update_tag(
            tag_id=tag.id,
            tag_update_model=update_model,
        )

    def get_tag(
        self,
        tag_name_or_id: str | UUID,
        allow_name_prefix_match: bool = True,
        hydrate: bool = True,
    ) -> TagResponse:
        """Get an existing tag.

        Args:
            tag_name_or_id: name or id of the tag to be retrieved.
            allow_name_prefix_match: If True, allow matching by name prefix.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The tag of interest.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_tag,
            list_method=self.list_tags,
            name_id_or_prefix=tag_name_or_id,
            allow_name_prefix_match=allow_name_prefix_match,
            hydrate=hydrate,
        )

    def list_tags(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: UUID | str | None = None,
        user: UUID | str | None = None,
        created: datetime | str | None = None,
        updated: datetime | str | None = None,
        name: str | None = None,
        color: str | ColorVariants | None = None,
        exclusive: bool | None = None,
        resource_type: str | TaggableResourceTypes | None = None,
        hydrate: bool = False,
    ) -> Page[TagResponse]:
        """Get tags by filter.

        Args:
            sort_by: The column to sort by.
            page: The page of items.
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or].
            id: Use the id of stacks to filter by.
            user: Use the user to filter by.
            created: Use to filter by time of creation.
            updated: Use the last updated date for filtering.
            name: The name of the tag.
            color: The color of the tag.
            exclusive: Flag indicating whether the tag is exclusive.
            resource_type: Filter tags associated with a specific resource type.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all tags.
        """
        return self.zen_store.list_tags(
            tag_filter_model=TagFilter(
                sort_by=sort_by,
                page=page,
                size=size,
                logical_operator=logical_operator,
                id=id,
                user=user,
                created=created,
                updated=updated,
                name=name,
                color=color,
                exclusive=exclusive,
                resource_type=resource_type,
            ),
            hydrate=hydrate,
        )

    def attach_tag(
        self,
        tag: str | tag_utils.Tag,
        resources: list[TagResource],
    ) -> None:
        """Attach a tag to resources.

        Args:
            tag: name of the tag or tag_utils.Tag object to be attached.
            resources: the resources to attach the tag to.

        Raises:
            ValueError: If the tag is an exclusive tag and is being
                attached to multiple resources or if the tag is a
                cascading tag as cascading tags can only be used
                with the pipeline decorator.
        """
        if isinstance(tag, str):
            tag_request = TagRequest(name=tag)
        else:
            tag_request = tag.to_request()

        try:
            tag_model = self.create_tag(**tag_request.model_dump())
        except EntityExistsError:
            tag_model = self.get_tag(
                tag_name_or_id=tag_request.name, allow_name_prefix_match=False
            )

        if isinstance(tag, tag_utils.Tag):
            if bool(tag.exclusive) != tag_model.exclusive:
                raise ValueError(
                    f"The tag `{tag.name}` is "
                    f"{'an exclusive' if tag_model.exclusive else 'a non-exclusive'} "
                    "tag. Please update it before attaching it to a resource."
                )
            if tag.cascade is not None:
                raise ValueError(
                    "Cascading tags can only be used with the "
                    "pipeline decorator."
                )

        self.zen_store.batch_create_tag_resource(
            tag_resources=[
                TagResourceRequest(
                    tag_id=tag_model.id,
                    resource_id=resource.id,
                    resource_type=resource.type,
                )
                for resource in resources
            ]
        )

    def detach_tag(
        self,
        tag_name_or_id: str | UUID,
        resources: list[TagResource],
    ) -> None:
        """Detach a tag from resources.

        Args:
            tag_name_or_id: name or id of the tag to be detached.
            resources: the resources to detach the tag from.
        """
        tag_model = self.get_tag(
            tag_name_or_id=tag_name_or_id, allow_name_prefix_match=False
        )

        self.zen_store.batch_delete_tag_resource(
            tag_resources=[
                TagResourceRequest(
                    tag_id=tag_model.id,
                    resource_id=resource.id,
                    resource_type=resource.type,
                )
                for resource in resources
            ]
        )
