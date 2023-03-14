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
import json
import os
from abc import ABCMeta
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Set,
    TypeVar,
    Union,
    cast,
)
from uuid import UUID

from pydantic import SecretStr

from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    ENV_ZENML_ACTIVE_STACK_ID,
    ENV_ZENML_ENABLE_REPO_INIT_WARNINGS,
    ENV_ZENML_REPOSITORY_PATH,
    PAGE_SIZE_DEFAULT,
    PAGINATION_STARTING_PAGE,
    REPOSITORY_DIRECTORY_NAME,
    handle_bool_env_var,
)
from zenml.enums import (
    ArtifactType,
    LogicalOperators,
    PermissionType,
    SecretScope,
    StackComponentType,
    StoreType,
)
from zenml.exceptions import (
    EntityExistsError,
    IllegalOperationError,
    InitializationException,
    ValidationError,
    ZenKeyError,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.models import (
    ComponentFilterModel,
    ComponentRequestModel,
    ComponentResponseModel,
    ComponentUpdateModel,
    FlavorFilterModel,
    FlavorRequestModel,
    FlavorResponseModel,
    PipelineBuildFilterModel,
    PipelineBuildResponseModel,
    PipelineDeploymentFilterModel,
    PipelineDeploymentResponseModel,
    PipelineFilterModel,
    PipelineResponseModel,
    PipelineRunFilterModel,
    PipelineRunResponseModel,
    RoleFilterModel,
    RoleRequestModel,
    RoleResponseModel,
    RoleUpdateModel,
    RunMetadataRequestModel,
    RunMetadataResponseModel,
    SecretFilterModel,
    SecretRequestModel,
    SecretResponseModel,
    SecretUpdateModel,
    StackFilterModel,
    StackRequestModel,
    StackResponseModel,
    StackUpdateModel,
    StepRunFilterModel,
    StepRunResponseModel,
    TeamFilterModel,
    TeamRequestModel,
    TeamResponseModel,
    TeamRoleAssignmentFilterModel,
    TeamRoleAssignmentRequestModel,
    TeamRoleAssignmentResponseModel,
    TeamUpdateModel,
    UserFilterModel,
    UserRequestModel,
    UserResponseModel,
    UserRoleAssignmentFilterModel,
    UserRoleAssignmentRequestModel,
    UserRoleAssignmentResponseModel,
    UserUpdateModel,
    WorkspaceFilterModel,
    WorkspaceRequestModel,
    WorkspaceResponseModel,
    WorkspaceUpdateModel,
)
from zenml.models.artifact_models import (
    ArtifactFilterModel,
    ArtifactResponseModel,
)
from zenml.models.base_models import BaseResponseModel
from zenml.models.constants import TEXT_FIELD_MAX_LENGTH
from zenml.models.page_model import Page
from zenml.models.run_metadata_models import RunMetadataFilterModel
from zenml.models.schedule_model import (
    ScheduleFilterModel,
    ScheduleResponseModel,
)
from zenml.utils import io_utils
from zenml.utils.analytics_utils import AnalyticsEvent, event_handler, track
from zenml.utils.filesync_model import FileSyncModel
from zenml.utils.pagination_utils import depaginate

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType
    from zenml.stack import Stack, StackComponentConfig
    from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)
AnyResponseModel = TypeVar("AnyResponseModel", bound=BaseResponseModel)


class ClientConfiguration(FileSyncModel):
    """Pydantic object used for serializing client configuration options."""

    _active_workspace: Optional["WorkspaceResponseModel"] = None
    active_workspace_id: Optional[UUID]
    active_stack_id: Optional[UUID]

    @property
    def active_workspace(self) -> WorkspaceResponseModel:
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

    def set_active_workspace(
        self, workspace: "WorkspaceResponseModel"
    ) -> None:
        """Set the workspace for the local client.

        Args:
            workspace: The workspace to set active.
        """
        self._active_workspace = workspace
        self.active_workspace_id = workspace.id

    def set_active_stack(self, stack: "StackResponseModel") -> None:
        """Set the stack for the local client.

        Args:
            stack: The stack to set active.
        """
        self.active_stack_id = stack.id

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

    _active_user: Optional[UserResponseModel] = None

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
            ENV_ZENML_ENABLE_REPO_INIT_WARNINGS, True
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

        return ClientConfiguration(config_path)

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
        with event_handler(AnalyticsEvent.INITIALIZE_REPO):
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

    @track(event=AnalyticsEvent.SET_WORKSPACE)
    def set_active_workspace(
        self, workspace_name_or_id: Union[str, UUID]
    ) -> "WorkspaceResponseModel":
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

    # ---- #
    # USER #
    # ---- #

    @property
    def active_user(self) -> "UserResponseModel":
        """Get the user that is currently in use.

        Returns:
            The active user.
        """
        if self._active_user is None:
            self._active_user = self.zen_store.get_user(include_private=True)
        return self._active_user

    def create_user(
        self,
        name: str,
        initial_role: Optional[str] = None,
        password: Optional[str] = None,
    ) -> UserResponseModel:
        """Create a new user.

        Args:
            name: The name of the user.
            initial_role: Optionally, an initial role to assign to the user.
            password: The password of the user. If not provided, the user will
                be created with empty password.

        Returns:
            The model of the created user.
        """
        user = UserRequestModel(name=name, password=password or None)
        if self.zen_store.type != StoreType.REST:
            user.active = password != ""
        else:
            user.active = True

        created_user = self.zen_store.create_user(user=user)

        if initial_role:
            self.create_user_role_assignment(
                role_name_or_id=initial_role,
                user_name_or_id=created_user.id,
                workspace_name_or_id=None,
            )

        return created_user

    def get_user(
        self,
        name_id_or_prefix: Union[str, UUID],
        allow_name_prefix_match: bool = True,
    ) -> UserResponseModel:
        """Gets a user.

        Args:
            name_id_or_prefix: The name or ID of the user.
            allow_name_prefix_match: If True, allow matching by name prefix.

        Returns:
            The User
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_user,
            list_method=self.list_users,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
        )

    def list_users(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        name: Optional[str] = None,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        active: Optional[bool] = None,
        email_opted_in: Optional[bool] = None,
    ) -> Page[UserResponseModel]:
        """List all users.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of stacks to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            name: Use the username for filtering
            full_name: Use the user full name for filtering
            email: Use the user email for filtering
            active: User the user active status for filtering
            email_opted_in: Use the user opt in status for filtering

        Returns:
            The User
        """
        return self.zen_store.list_users(
            UserFilterModel(
                sort_by=sort_by,
                page=page,
                size=size,
                logical_operator=logical_operator,
                id=id,
                created=created,
                updated=updated,
                name=name,
                full_name=full_name,
                email=email,
                active=active,
                email_opted_in=email_opted_in,
            )
        )

    def delete_user(self, name_id_or_prefix: str) -> None:
        """Delete a user.

        Args:
            name_id_or_prefix: The name or ID of the user to delete.
        """
        user = self.get_user(name_id_or_prefix, allow_name_prefix_match=False)
        self.zen_store.delete_user(user_name_or_id=user.name)

    def update_user(
        self,
        name_id_or_prefix: Union[str, UUID],
        updated_name: Optional[str] = None,
        updated_full_name: Optional[str] = None,
        updated_email: Optional[str] = None,
        updated_email_opt_in: Optional[bool] = None,
    ) -> UserResponseModel:
        """Update a user.

        Args:
            name_id_or_prefix: The name or ID of the user to update.
            updated_name: The new name of the user.
            updated_full_name: The new full name of the user.
            updated_email: The new email of the user.
            updated_email_opt_in: The new email opt-in status of the user.

        Returns:
            The updated user.
        """
        user = self.get_user(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )
        user_update = UserUpdateModel()
        if updated_name:
            user_update.name = updated_name
        if updated_full_name:
            user_update.full_name = updated_full_name
        if updated_email is not None:
            user_update.email = updated_email
            user_update.email_opted_in = (
                updated_email_opt_in or user.email_opted_in
            )
        if updated_email_opt_in is not None:
            user_update.email_opted_in = updated_email_opt_in

        return self.zen_store.update_user(
            user_id=user.id, user_update=user_update
        )

    # ---- #
    # TEAM #
    # ---- #

    def get_team(
        self,
        name_id_or_prefix: Union[str, UUID],
        allow_name_prefix_match: bool = True,
    ) -> TeamResponseModel:
        """Gets a team.

        Args:
            name_id_or_prefix: The name or ID of the team.
            allow_name_prefix_match: If True, allow matching by name prefix.

        Returns:
            The Team
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_team,
            list_method=self.list_teams,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
        )

    def list_teams(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        name: Optional[str] = None,
    ) -> Page[TeamResponseModel]:
        """List all teams.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of teams to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            name: Use the team name for filtering

        Returns:
            The Team
        """
        return self.zen_store.list_teams(
            TeamFilterModel(
                sort_by=sort_by,
                page=page,
                size=size,
                logical_operator=logical_operator,
                id=id,
                created=created,
                updated=updated,
                name=name,
            )
        )

    def create_team(
        self, name: str, users: Optional[List[str]] = None
    ) -> TeamResponseModel:
        """Create a team.

        Args:
            name: Name of the team.
            users: Users to add to the team.

        Returns:
            The created team.
        """
        user_list = []
        if users:
            for user_name_or_id in users:
                user_list.append(
                    self.get_user(name_id_or_prefix=user_name_or_id).id
                )

        team = TeamRequestModel(name=name, users=user_list)

        return self.zen_store.create_team(team=team)

    def delete_team(self, name_id_or_prefix: str) -> None:
        """Delete a team.

        Args:
            name_id_or_prefix: The name or ID of the team to delete.
        """
        team = self.get_team(name_id_or_prefix, allow_name_prefix_match=False)
        self.zen_store.delete_team(team_name_or_id=team.id)

    def update_team(
        self,
        name_id_or_prefix: str,
        new_name: Optional[str] = None,
        remove_users: Optional[List[str]] = None,
        add_users: Optional[List[str]] = None,
    ) -> TeamResponseModel:
        """Update a team.

        Args:
            name_id_or_prefix: The name or ID of the team to update.
            new_name: The new name of the team.
            remove_users: The users to remove from the team.
            add_users: The users to add to the team.

        Returns:
            The updated team.

        Raises:
            RuntimeError: If the same user is in both `remove_users` and
                `add_users`.
        """
        team = self.get_team(name_id_or_prefix, allow_name_prefix_match=False)

        team_update = TeamUpdateModel()

        if new_name:
            team_update.name = new_name

        if remove_users is not None and add_users is not None:
            union_add_rm = set(remove_users) & set(add_users)
            if union_add_rm:
                raise RuntimeError(
                    f"The `remove_user` and `add_user` "
                    f"options both contain the same value(s): "
                    f"`{union_add_rm}`. Please rerun command and make sure "
                    f"that the same user does not show up for "
                    f"`remove_user` and `add_user`."
                )

        # Only if permissions are being added or removed will they need to be
        #  set for the update model
        team_users = []

        if remove_users or add_users:
            team_users = [u.id for u in team.users]
        if remove_users:
            for rm_p in remove_users:
                user = self.get_user(rm_p)
                try:
                    team_users.remove(user.id)
                except KeyError:
                    logger.warning(
                        f"Role {remove_users} was already not "
                        f"part of the '{team.name}' Team."
                    )
        if add_users:
            for add_u in add_users:
                team_users.append(self.get_user(add_u).id)

        if team_users:
            team_update.users = team_users

        return self.zen_store.update_team(
            team_id=team.id, team_update=team_update
        )

    # ----- #
    # ROLES #
    # ----- #

    def get_role(
        self,
        name_id_or_prefix: Union[str, UUID],
        allow_name_prefix_match: bool = True,
    ) -> RoleResponseModel:
        """Gets a role.

        Args:
            name_id_or_prefix: The name or ID of the role.
            allow_name_prefix_match: If True, allow matching by name prefix.

        Returns:
            The fetched role.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_role,
            list_method=self.list_roles,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
        )

    def list_roles(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        name: Optional[str] = None,
    ) -> Page[RoleResponseModel]:
        """List all roles.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: The logical operator to use between column filters
            id: Use the id of roles to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            name: Use the role name for filtering

        Returns:
            The Role
        """
        return self.zen_store.list_roles(
            RoleFilterModel(
                sort_by=sort_by,
                page=page,
                size=size,
                logical_operator=logical_operator,
                id=id,
                created=created,
                updated=updated,
                name=name,
            )
        )

    def create_role(
        self, name: str, permissions_list: List[str]
    ) -> RoleResponseModel:
        """Creates a role.

        Args:
            name: The name for the new role.
            permissions_list: The permissions to attach to this role.

        Returns:
            The newly created role.
        """
        permissions: Set[PermissionType] = set()
        for permission in permissions_list:
            if permission in PermissionType.values():
                permissions.add(PermissionType(permission))

        new_role = RoleRequestModel(name=name, permissions=permissions)
        return self.zen_store.create_role(new_role)

    def update_role(
        self,
        name_id_or_prefix: str,
        new_name: Optional[str] = None,
        remove_permission: Optional[List[str]] = None,
        add_permission: Optional[List[str]] = None,
    ) -> RoleResponseModel:
        """Updates a role.

        Args:
            name_id_or_prefix: The name or ID of the role.
            new_name: The new name for the role
            remove_permission: Permissions to remove from this role.
            add_permission: Permissions to add to this role.

        Returns:
            The updated role.

        Raises:
            RuntimeError: If the same permission is in both the
                `remove_permission` and `add_permission` lists.
        """
        role = self.get_role(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )

        role_update = RoleUpdateModel()

        if remove_permission is not None and add_permission is not None:
            union_add_rm = set(remove_permission) & set(add_permission)
            if union_add_rm:
                raise RuntimeError(
                    f"The `remove_permission` and `add_permission` "
                    f"options both contain the same value(s): "
                    f"`{union_add_rm}`. Please rerun command and make sure "
                    f"that the same role does not show up for "
                    f"`remove_permission` and `add_permission`."
                )

        # Only if permissions are being added or removed will they need to be
        #  set for the update model
        if remove_permission or add_permission:
            role_permissions = role.permissions

            if remove_permission:
                for rm_p in remove_permission:
                    if rm_p in PermissionType:
                        try:
                            role_permissions.remove(PermissionType(rm_p))
                        except KeyError:
                            logger.warning(
                                f"Role {remove_permission} was already not "
                                f"part of the {role} Role."
                            )
            if add_permission:
                for add_p in add_permission:
                    if add_p in PermissionType.values():
                        # Set won't throw an error if the item was already in it
                        role_permissions.add(PermissionType(add_p))

            if role_permissions is not None:
                role_update.permissions = set(role_permissions)

        if new_name:
            role_update.name = new_name

        return Client().zen_store.update_role(
            role_id=role.id, role_update=role_update
        )

    def delete_role(self, name_id_or_prefix: str) -> None:
        """Deletes a role.

        Args:
            name_id_or_prefix: The name or ID of the role.
        """
        role = self.get_role(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )
        self.zen_store.delete_role(role_name_or_id=role.id)

    # --------------------- #
    # USER ROLE ASSIGNMENTS #
    # --------------------- #

    def get_user_role_assignment(
        self, role_assignment_id: UUID
    ) -> UserRoleAssignmentResponseModel:
        """Get a role assignment.

        Args:
            role_assignment_id: The id of the role assignments

        Returns:
            The role assignment.
        """
        return self.zen_store.get_user_role_assignment(
            user_role_assignment_id=role_assignment_id
        )

    def create_user_role_assignment(
        self,
        role_name_or_id: Union[str, UUID],
        user_name_or_id: Union[str, UUID],
        workspace_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> UserRoleAssignmentResponseModel:
        """Create a role assignment.

        Args:
            role_name_or_id: Name or ID of the role to assign.
            user_name_or_id: Name or ID of the user or team to assign
                the role to.
            workspace_name_or_id: workspace scope within which to assign the role.

        Returns:
            The newly created role assignment.
        """
        role = self.get_role(name_id_or_prefix=role_name_or_id)
        workspace = None
        if workspace_name_or_id:
            workspace = self.get_workspace(
                name_id_or_prefix=workspace_name_or_id
            )
        user = self.get_user(name_id_or_prefix=user_name_or_id)
        role_assignment = UserRoleAssignmentRequestModel(
            role=role.id,
            user=user.id,
            workspace=workspace,
        )
        return self.zen_store.create_user_role_assignment(
            user_role_assignment=role_assignment
        )

    def delete_user_role_assignment(self, role_assignment_id: UUID) -> None:
        """Delete a role assignment.

        Args:
            role_assignment_id: The id of the role assignments

        """
        self.zen_store.delete_user_role_assignment(role_assignment_id)

    def list_user_role_assignment(
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
        role_id: Optional[Union[str, UUID]] = None,
    ) -> Page[UserRoleAssignmentResponseModel]:
        """List all user role assignments.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of the user role assignment to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            workspace_id: The id of the workspace to filter by.
            user_id: The id of the user to filter by.
            role_id: The id of the role to filter by.

        Returns:
            The Team
        """
        return self.zen_store.list_user_role_assignments(
            UserRoleAssignmentFilterModel(
                sort_by=sort_by,
                page=page,
                size=size,
                logical_operator=logical_operator,
                id=id,
                created=created,
                updated=updated,
                workspace_id=workspace_id,
                user_id=user_id,
                role_id=role_id,
            )
        )

    # --------------------- #
    # TEAM ROLE ASSIGNMENTS #
    # --------------------- #

    def get_team_role_assignment(
        self, team_role_assignment_id: UUID
    ) -> TeamRoleAssignmentResponseModel:
        """Get a role assignment.

        Args:
            team_role_assignment_id: The id of the role assignments

        Returns:
            The role assignment.
        """
        return self.zen_store.get_team_role_assignment(
            team_role_assignment_id=team_role_assignment_id
        )

    def create_team_role_assignment(
        self,
        role_name_or_id: Union[str, UUID],
        team_name_or_id: Union[str, UUID],
        workspace_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> TeamRoleAssignmentResponseModel:
        """Create a role assignment.

        Args:
            role_name_or_id: Name or ID of the role to assign.
            team_name_or_id: Name or ID of the team to assign
                the role to.
            workspace_name_or_id: workspace scope within which to assign the role.

        Returns:
            The newly created role assignment.
        """
        role = self.get_role(name_id_or_prefix=role_name_or_id)
        workspace = None
        if workspace_name_or_id:
            workspace = self.get_workspace(
                name_id_or_prefix=workspace_name_or_id
            )
        team = self.get_team(name_id_or_prefix=team_name_or_id)
        role_assignment = TeamRoleAssignmentRequestModel(
            role=role.id,
            team=team.id,
            workspace=workspace,
        )
        return self.zen_store.create_team_role_assignment(
            team_role_assignment=role_assignment
        )

    def delete_team_role_assignment(self, role_assignment_id: UUID) -> None:
        """Delete a role assignment.

        Args:
            role_assignment_id: The id of the role assignments

        """
        self.zen_store.delete_team_role_assignment(role_assignment_id)

    def list_team_role_assignment(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[Union[datetime, str]] = None,
        updated: Optional[Union[datetime, str]] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        team_id: Optional[Union[str, UUID]] = None,
        role_id: Optional[Union[str, UUID]] = None,
    ) -> Page[TeamRoleAssignmentResponseModel]:
        """List all team role assignments.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of the team role assignment to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            workspace_id: The id of the workspace to filter by.
            team_id: The id of the team to filter by.
            role_id: The id of the role to filter by.

        Returns:
            The Team
        """
        return self.zen_store.list_team_role_assignments(
            TeamRoleAssignmentFilterModel(
                sort_by=sort_by,
                page=page,
                size=size,
                logical_operator=logical_operator,
                id=id,
                created=created,
                updated=updated,
                workspace_id=workspace_id,
                team_id=team_id,
                role_id=role_id,
            )
        )

    # --------- #
    # WORKSPACE #
    # --------- #

    @property
    def active_workspace(self) -> "WorkspaceResponseModel":
        """Get the currently active workspace of the local client.

        If no active workspace is configured locally for the client, the
        active workspace in the global configuration is used instead.

        Returns:
            The active workspace.

        Raises:
            RuntimeError: If the active workspace is not set.
        """
        workspace: Optional["WorkspaceResponseModel"] = None
        if self._config:
            workspace = self._config.active_workspace

        if not workspace:
            workspace = GlobalConfiguration().get_active_workspace()

        if not workspace:
            raise RuntimeError(
                "No active workspace is configured. Run "
                "`zenml workspace set WORKSPACE_NAME` to set the active "
                "workspace."
            )

        from zenml.zen_stores.base_zen_store import DEFAULT_WORKSPACE_NAME

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

    def get_workspace(
        self,
        name_id_or_prefix: Optional[Union[UUID, str]],
        allow_name_prefix_match: bool = True,
    ) -> WorkspaceResponseModel:
        """Gets a workspace.

        Args:
            name_id_or_prefix: The name or ID of the workspace.
            allow_name_prefix_match: If True, allow matching by name prefix.

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
    ) -> Page[WorkspaceResponseModel]:
        """List all workspaces.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of teams to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            name: Use the team name for filtering

        Returns:
            The Team
        """
        return self.zen_store.list_workspaces(
            WorkspaceFilterModel(
                sort_by=sort_by,
                page=page,
                size=size,
                logical_operator=logical_operator,
                id=id,
                created=created,
                updated=updated,
                name=name,
            )
        )

    def create_workspace(
        self, name: str, description: str
    ) -> "WorkspaceResponseModel":
        """Create a new workspace.

        Args:
            name: Name of the workspace.
            description: Description of the workspace.

        Returns:
            The created workspace.
        """
        return self.zen_store.create_workspace(
            WorkspaceRequestModel(name=name, description=description)
        )

    def update_workspace(
        self,
        name_id_or_prefix: Optional[Union[UUID, str]],
        new_name: Optional[str] = None,
        new_description: Optional[str] = None,
    ) -> "WorkspaceResponseModel":
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
        workspace_update = WorkspaceUpdateModel()
        if new_name:
            workspace_update.name = new_name
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

    # ------ #
    # STACKS #
    # ------ #
    @property
    def active_stack_model(self) -> "StackResponseModel":
        """The model of the active stack for this client.

        If no active stack is configured locally for the client, the active
        stack in the global configuration is used instead.

        Returns:
            The model of the active stack for this client.

        Raises:
            RuntimeError: If the active stack is not set.
        """
        stack: Optional["StackResponseModel"] = None

        if ENV_ZENML_ACTIVE_STACK_ID in os.environ:
            return self.get_stack(ENV_ZENML_ACTIVE_STACK_ID)

        if self._config:
            stack = self.get_stack(self._config.active_stack_id)

        if not stack:
            stack = self.get_stack(GlobalConfiguration().get_active_stack_id())

        if not stack:
            raise RuntimeError(
                "No active stack is configured. Run "
                "`zenml stack set STACK_NAME` to set the active stack."
            )

        return stack

    @property
    def active_stack(self) -> "Stack":
        """The active stack for this client.

        Returns:
            The active stack for this client.
        """
        from zenml.stack.stack import Stack

        return Stack.from_model(self.active_stack_model)

    def get_stack(
        self,
        name_id_or_prefix: Optional[Union[UUID, str]] = None,
        allow_name_prefix_match: bool = True,
    ) -> "StackResponseModel":
        """Get a stack by name, ID or prefix.

        If no name, ID or prefix is provided, the active stack is returned.

        Args:
            name_id_or_prefix: The name, ID or prefix of the stack.
            allow_name_prefix_match: If True, allow matching by name prefix.

        Returns:
            The stack.
        """
        if name_id_or_prefix is not None:
            return self._get_entity_by_id_or_name_or_prefix(
                get_method=self.zen_store.get_stack,
                list_method=self.list_stacks,
                name_id_or_prefix=name_id_or_prefix,
                allow_name_prefix_match=allow_name_prefix_match,
            )
        else:
            return self.active_stack_model

    def create_stack(
        self,
        name: str,
        components: Mapping[StackComponentType, Union[str, UUID]],
        is_shared: bool = False,
    ) -> "StackResponseModel":
        """Registers a stack and its components.

        Args:
            name: The name of the stack to register.
            components: dictionary which maps component types to component names
            is_shared: boolean to decide whether the stack is shared

        Returns:
            The model of the registered stack.

        Raises:
            ValueError: If the stack contains private components and is
                attempted to be registered as shared.
        """
        stack_components = dict()

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

            # Raise an error if private components are used in a shared stack.
            if is_shared and not component.is_shared:
                raise ValueError(
                    f"You attempted to include the private {c_type} "
                    f"'{component.name}' in a shared stack. This is not "
                    f"supported. You can either share the {c_type} with the "
                    f"following command:\n"
                    f"`zenml {c_type.replace('_', '-')} share`{component.id}`\n"
                    f"or create the stack privately and then share it and all "
                    f"of its components using:\n`zenml stack share {name} -r`"
                )

        stack = StackRequestModel(
            name=name,
            components=stack_components,
            is_shared=is_shared,
            workspace=self.active_workspace.id,
            user=self.active_user.id,
        )

        self._validate_stack_configuration(stack=stack)

        return self.zen_store.create_stack(stack=stack)

    def update_stack(
        self,
        name_id_or_prefix: Optional[Union[UUID, str]] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
        description: Optional[str] = None,
        component_updates: Optional[
            Dict[StackComponentType, List[Union[UUID, str]]]
        ] = None,
    ) -> "StackResponseModel":
        """Updates a stack and its components.

        Args:
            name_id_or_prefix: The name, id or prefix of the stack to update.
            name: the new name of the stack.
            is_shared: the new shared status of the stack.
            description: the new description of the stack.
            component_updates: dictionary which maps stack component types to
                lists of new stack component names or ids.

        Returns:
            The model of the updated stack.

        Raises:
            ValueError: If the stack contains private components and is
                attempted to be shared.
            EntityExistsError: If the stack name is already taken.
        """
        # First, get the stack
        stack = self.get_stack(
            name_id_or_prefix=name_id_or_prefix, allow_name_prefix_match=False
        )

        # Create the update model
        update_model = StackUpdateModel(
            workspace=self.active_workspace.id,
            user=self.active_user.id,
        )

        if name:
            shared_status = is_shared or stack.is_shared

            existing_stacks = self.list_stacks(
                name=name, is_shared=shared_status
            )
            if existing_stacks:
                raise EntityExistsError(
                    "There are already existing stacks with the name "
                    f"'{name}'."
                )

            update_model.name = name

        if is_shared:
            current_name = update_model.name or stack.name
            existing_stacks = self.list_stacks(
                name=current_name, is_shared=True
            )
            if existing_stacks:
                raise EntityExistsError(
                    "There are already existing shared stacks with the name "
                    f"'{current_name}'."
                )

            for component_type, components in stack.components.items():
                for c in components:
                    if not c.is_shared:
                        raise ValueError(
                            f"A Stack can only be shared when all its "
                            f"components are also shared. Component "
                            f"'{component_type}:{c.name}' is not shared. Set "
                            f"the {component_type} to shared like this and "
                            f"then try re-sharing your stack:\n "
                            f"`zenml {component_type.replace('_', '-')} "
                            f"share {c.id}`\nAlternatively, you can rerun "
                            f"your command with `-r` to recursively "
                            f"share all components within the stack."
                        )

            update_model.is_shared = is_shared

        if description:
            update_model.description = description

        # Get the current components
        if component_updates:
            components_dict = {}
            for component_type, component_list in stack.components.items():
                components_dict[component_type] = [
                    c.id for c in component_list
                ]

            for component_type, component_id_list in component_updates.items():
                if component_id_list is not None:
                    components_dict[component_type] = [
                        self.get_stack_component(
                            name_id_or_prefix=c,
                            component_type=component_type,
                        ).id
                        for c in component_id_list
                    ]

            update_model.components = components_dict

        return self.zen_store.update_stack(
            stack_id=stack.id,
            stack_update=update_model,
        )

    def delete_stack(self, name_id_or_prefix: Union[str, UUID]) -> None:
        """Deregisters a stack.

        Args:
            name_id_or_prefix: The name, id or prefix id of the stack
                to deregister.

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

        self.zen_store.delete_stack(stack_id=stack.id)
        logger.info("Deregistered stack with name '%s'.", stack.name)

    def list_stacks(
        self,
        sort_by: str = "created",
        page: int = PAGINATION_STARTING_PAGE,
        size: int = PAGE_SIZE_DEFAULT,
        logical_operator: LogicalOperators = LogicalOperators.AND,
        id: Optional[Union[UUID, str]] = None,
        created: Optional[datetime] = None,
        updated: Optional[datetime] = None,
        is_shared: Optional[bool] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        component_id: Optional[Union[str, UUID]] = None,
    ) -> Page[StackResponseModel]:
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
            name: The name of the stack to filter by.
            is_shared: The shared status of the stack to filter by.

        Returns:
            A page of stacks.
        """
        stack_filter_model = StackFilterModel(
            page=page,
            size=size,
            sort_by=sort_by,
            logical_operator=logical_operator,
            workspace_id=workspace_id,
            user_id=user_id,
            component_id=component_id,
            name=name,
            is_shared=is_shared,
            description=description,
            id=id,
            created=created,
            updated=updated,
        )
        stack_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_stacks(stack_filter_model)

    @track(event=AnalyticsEvent.SET_STACK)
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
        except KeyError:
            raise KeyError(
                f"Stack '{stack_name_id_or_prefix}' cannot be activated since "
                f"it is not registered yet. Please register it first."
            )

        if self._config:
            self._config.set_active_stack(stack=stack)

        else:
            # set the active stack globally only if the client doesn't use
            # a local configuration
            GlobalConfiguration().set_active_stack(stack=stack)

    def _validate_stack_configuration(
        self, stack: "StackRequestModel"
    ) -> None:
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
                    component = self.get_stack_component(
                        name_id_or_prefix=component_id,
                        component_type=component_type,
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

    # .------------.
    # | COMPONENTS |
    # '------------'
    def get_stack_component(
        self,
        component_type: StackComponentType,
        name_id_or_prefix: Optional[Union[str, UUID]] = None,
        allow_name_prefix_match: bool = True,
    ) -> "ComponentResponseModel":
        """Fetches a registered stack component.

        If the name_id_or_prefix is provided, it will try to fetch the component
        with the corresponding identifier. If not, it will try to fetch the
        active component of the given type.

        Args:
            component_type: The type of the component to fetch
            name_id_or_prefix: The id of the component to fetch.
            allow_name_prefix_match: If True, allow matching by name prefix.

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
            **kwargs: Any,
        ) -> Page[ComponentResponseModel]:
            """Call `zen_store.list_stack_components` with type scoping.

            Args:
                **kwargs: Keyword arguments to pass to `ComponentFilterModel`.

            Returns:
                The type-scoped list of components.
            """
            component_filter_model = ComponentFilterModel(**kwargs)
            component_filter_model.set_scope_type(
                component_type=component_type
            )
            component_filter_model.set_scope_workspace(
                self.active_workspace.id
            )
            return self.zen_store.list_stack_components(
                component_filter_model=component_filter_model,
            )

        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_stack_component,
            list_method=type_scoped_list_method,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
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
        is_shared: Optional[bool] = None,
        name: Optional[str] = None,
        flavor: Optional[str] = None,
        type: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
    ) -> Page[ComponentResponseModel]:
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
            name: The name of the component to filter by.
            is_shared: The shared status of the component to filter by.

        Returns:
            A page of stack components.
        """
        component_filter_model = ComponentFilterModel(
            page=page,
            size=size,
            sort_by=sort_by,
            logical_operator=logical_operator,
            workspace_id=workspace_id or self.active_workspace.id,
            user_id=user_id,
            name=name,
            is_shared=is_shared,
            flavor=flavor,
            type=type,
            id=id,
            created=created,
            updated=updated,
        )
        component_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_stack_components(
            component_filter_model=component_filter_model
        )

    def create_stack_component(
        self,
        name: str,
        flavor: str,
        component_type: StackComponentType,
        configuration: Dict[str, str],
        is_shared: bool = False,
    ) -> "ComponentResponseModel":
        """Registers a stack component.

        Args:
            name: The name of the stack component.
            flavor: The flavor of the stack component.
            component_type: The type of the stack component.
            configuration: The configuration of the stack component.
            is_shared: Whether the stack component is shared or not.

        Returns:
            The model of the registered component.
        """
        # Get the flavor model
        flavor_model = self.get_flavor_by_name_and_type(
            name=flavor,
            component_type=component_type,
        )

        # Create and validate the configuration
        from zenml.stack import Flavor

        flavor_class = Flavor.from_model(flavor_model)
        configuration_obj = flavor_class.config_class(
            warn_about_plain_text_secrets=True, **configuration
        )

        self._validate_stack_component_configuration(
            component_type, configuration=configuration_obj
        )

        create_component_model = ComponentRequestModel(
            name=name,
            type=component_type,
            flavor=flavor,
            configuration=configuration,
            is_shared=is_shared,
            user=self.active_user.id,
            workspace=self.active_workspace.id,
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
        configuration: Optional[Dict[str, Any]] = None,
        is_shared: Optional[bool] = None,
    ) -> "ComponentResponseModel":
        """Updates a stack component.

        Args:
            name_id_or_prefix: The name, id or prefix of the stack component to
                update.
            component_type: The type of the stack component to update.
            name: The new name of the stack component.
            configuration: The new configuration of the stack component.
            is_shared: The new shared status of the stack component.

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

        update_model = ComponentUpdateModel(
            workspace=self.active_workspace.id,
            user=self.active_user.id,
        )

        if name is not None:
            shared_status = is_shared or component.is_shared

            existing_components = self.list_stack_components(
                name=name,
                is_shared=shared_status,
                type=component_type,
            )
            if existing_components.total > 0:
                raise EntityExistsError(
                    f"There are already existing "
                    f"{'shared' if shared_status else 'unshared'} components "
                    f"with the name '{name}'."
                )
            update_model.name = name

        if is_shared is not None:
            current_name = update_model.name or component.name
            existing_components = self.list_stack_components(
                name=current_name, is_shared=is_shared, type=component_type
            )
            if any([e.id != component.id for e in existing_components.items]):
                raise EntityExistsError(
                    f"There are already existing shared components with "
                    f"the name '{current_name}'"
                )
            update_model.is_shared = is_shared

        if configuration is not None:
            existing_configuration = component.configuration
            existing_configuration.update(configuration)

            existing_configuration = {
                k: v
                for k, v in existing_configuration.items()
                if v is not None
            }

            flavor_model = self.get_flavor_by_name_and_type(
                name=component.flavor,
                component_type=component.type,
            )

            from zenml.stack import Flavor

            flavor = Flavor.from_model(flavor_model)
            configuration_obj = flavor.config_class(**existing_configuration)

            self._validate_stack_component_configuration(
                component.type, configuration=configuration_obj
            )
            update_model.configuration = existing_configuration

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
        from zenml.enums import StoreType

        if configuration.is_remote and self.zen_store.is_local_store():
            if self.zen_store.type != StoreType.REST:
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

    # .---------.
    # | FLAVORS |
    # '---------'

    def create_flavor(
        self,
        source: str,
        component_type: StackComponentType,
    ) -> "FlavorResponseModel":
        """Creates a new flavor.

        Args:
            source: The flavor to create.
            component_type: The type of the flavor.

        Returns:
            The created flavor (in model form).

        Raises:
            ValueError: in case the config_schema of the flavor is too large.
        """
        from zenml.utils.source_utils import validate_flavor_source

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

        create_flavor_request = FlavorRequestModel(
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
    ) -> "FlavorResponseModel":
        """Get a stack component flavor.

        Args:
            name_id_or_prefix: The name, ID or prefix to the id of the flavor
                to get.
            allow_name_prefix_match: If True, allow matching by name prefix.

        Returns:
            The stack component flavor.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_flavor,
            list_method=self.list_flavors,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
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
    ) -> Page[FlavorResponseModel]:
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

        Returns:
            A list of all the flavor models.
        """
        flavor_filter_model = FlavorFilterModel(
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
            flavor_filter_model=flavor_filter_model
        )

    def get_flavors_by_type(
        self, component_type: "StackComponentType"
    ) -> Page[FlavorResponseModel]:
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
    ) -> "FlavorResponseModel":
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

        flavors = self.list_flavors(
            type=component_type,
            name=name,
        ).items

        if flavors:
            if len(flavors) > 1:
                raise KeyError(
                    f"More than one flavor with name {name} and type "
                    f"{component_type} exists."
                )

            return flavors[0]
        else:
            raise KeyError(
                f"No flavor with name '{name}' and type '{component_type}' "
                "exists."
            )

    # -------------
    # - PIPELINES -
    # -------------

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
        version: Optional[str] = None,
        version_hash: Optional[str] = None,
        docstring: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
    ) -> Page[PipelineResponseModel]:
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
            version: The version of the pipeline to filter by.
            version_hash: The version hash of the pipeline to filter by.
            docstring: The docstring of the pipeline to filter by.
            workspace_id: The id of the workspace to filter by.
            user_id: The id of the user to filter by.

        Returns:
            A page with Pipeline fitting the filter description
        """
        pipeline_filter_model = PipelineFilterModel(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            created=created,
            updated=updated,
            name=name,
            version=version,
            version_hash=version_hash,
            docstring=docstring,
            workspace_id=workspace_id,
            user_id=user_id,
        )
        pipeline_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_pipelines(
            pipeline_filter_model=pipeline_filter_model
        )

    def get_pipeline(
        self,
        name_id_or_prefix: Union[str, UUID],
        version: Optional[str] = None,
    ) -> PipelineResponseModel:
        """Get a pipeline by name, id or prefix.

        Args:
            name_id_or_prefix: The name, ID or ID prefix of the pipeline.
            version: The pipeline version. If left empty, will return
                the latest version.

        Returns:
            The pipeline.

        Raises:
            KeyError: If no pipelines were found for the given ID/name and
                version.
            ZenKeyError: If multiple pipelines match the ID prefix.
        """
        from zenml.utils.uuid_utils import is_valid_uuid

        if is_valid_uuid(name_id_or_prefix):
            if version:
                logger.warning(
                    "You specified both an ID as well as a version of the "
                    "pipeline. Ignoring the version and fetching the "
                    "pipeline by ID."
                )
            if not isinstance(name_id_or_prefix, UUID):
                name_id_or_prefix = UUID(name_id_or_prefix, version=4)

            return self.zen_store.get_pipeline(name_id_or_prefix)

        assert not isinstance(name_id_or_prefix, UUID)
        exact_name_matches = self.list_pipelines(
            size=1,
            sort_by="desc:created",
            name=f"equals:{name_id_or_prefix}",
            version=version,
        )

        if len(exact_name_matches) == 1:
            # If the name matches exactly, use the explicitly specified version
            # or fallback to the latest if not given
            return exact_name_matches.items[0]

        partial_id_matches = self.list_pipelines(
            id=f"startswith:{name_id_or_prefix}"
        )
        if partial_id_matches.total == 1:
            if version:
                logger.warning(
                    "You specified both an ID as well as a version of the "
                    "pipeline. Ignoring the version and fetching the "
                    "pipeline by ID."
                )
            return partial_id_matches[0]
        elif partial_id_matches.total == 0:
            raise KeyError(
                f"No pipelines found for name, ID or prefix "
                f"{name_id_or_prefix}."
            )
        else:
            raise ZenKeyError(
                f"{partial_id_matches.total} pipelines have been found that "
                "have an id prefix that matches the provided string "
                f"'{name_id_or_prefix}':\n"
                f"{partial_id_matches.items}.\n"
                f"Please provide more characters to uniquely identify "
                f"only one of the pipelines."
            )

    def delete_pipeline(
        self,
        name_id_or_prefix: Union[str, UUID],
        version: Optional[str] = None,
    ) -> None:
        """Delete a pipeline.

        Args:
            name_id_or_prefix: The name, ID or ID prefix of the pipeline.
            version: The pipeline version. If left empty, will delete
                the latest version.
        """
        pipeline = self.get_pipeline(
            name_id_or_prefix=name_id_or_prefix, version=version
        )
        self.zen_store.delete_pipeline(pipeline_id=pipeline.id)

    # ----------
    # - BUILDS -
    # ----------

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
    ) -> Page[PipelineBuildResponseModel]:
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

        Returns:
            A page with builds fitting the filter description
        """
        build_filter_model = PipelineBuildFilterModel(
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
        )
        build_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_builds(
            build_filter_model=build_filter_model
        )

    def get_build(self, id_or_prefix: str) -> PipelineBuildResponseModel:
        """Get a build by id or prefix.

        Args:
            id_or_prefix: The id or id prefix of the build.

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
            return self.zen_store.get_build(UUID(id_or_prefix))

        entity = self.list_builds(
            id=f"startswith:{id_or_prefix}",
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

    def delete_build(self, id_or_prefix: str) -> None:
        """Delete a build.

        Args:
            id_or_prefix: The id or id prefix of the build.
        """
        build = self.get_build(id_or_prefix=id_or_prefix)
        self.zen_store.delete_build(build_id=build.id)

    # ---------------
    # - DEPLOYMENTS -
    # ---------------

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
    ) -> Page[PipelineDeploymentResponseModel]:
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

        Returns:
            A page with deployments fitting the filter description
        """
        deployment_filter_model = PipelineDeploymentFilterModel(
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
        )
        deployment_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_deployments(
            deployment_filter_model=deployment_filter_model
        )

    def get_deployment(
        self, id_or_prefix: str
    ) -> PipelineDeploymentResponseModel:
        """Get a deployment by id or prefix.

        Args:
            id_or_prefix: The id or id prefix of the build.

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
            return self.zen_store.get_deployment(UUID(id_or_prefix))

        entity = self.list_deployments(
            id=f"startswith:{id_or_prefix}",
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

    def delete_deployment(self, id_or_prefix: str) -> None:
        """Delete a deployment.

        Args:
            id_or_prefix: The id or id prefix of the deployment.
        """
        deployment = self.get_deployment(id_or_prefix=id_or_prefix)
        self.zen_store.delete_deployment(deployment_id=deployment.id)

    # -------------
    # - SCHEDULES -
    # -------------

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
    ) -> Page[ScheduleResponseModel]:
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

        Returns:
            A list of schedules.
        """
        schedule_filter_model = ScheduleFilterModel(
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
        )
        schedule_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_schedules(
            schedule_filter_model=schedule_filter_model
        )

    def get_schedule(
        self,
        name_id_or_prefix: Union[str, UUID],
        allow_name_prefix_match: bool = True,
    ) -> ScheduleResponseModel:
        """Get a schedule by name, id or prefix.

        Args:
            name_id_or_prefix: The name, id or prefix of the schedule.
            allow_name_prefix_match: If True, allow matching by name prefix.

        Returns:
            The schedule.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_schedule,
            list_method=self.list_schedules,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
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

    # -----------------
    # - PIPELINE RUNS -
    # -----------------

    def list_runs(
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
        pipeline_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        stack_id: Optional[Union[str, UUID]] = None,
        schedule_id: Optional[Union[str, UUID]] = None,
        build_id: Optional[Union[str, UUID]] = None,
        deployment_id: Optional[Union[str, UUID]] = None,
        orchestrator_run_id: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[Union[datetime, str]] = None,
        end_time: Optional[Union[datetime, str]] = None,
        num_steps: Optional[Union[int, str]] = None,
        unlisted: Optional[bool] = None,
    ) -> Page[PipelineRunResponseModel]:
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
            user_id: The id of the user to filter by.
            stack_id: The id of the stack to filter by.
            schedule_id: The id of the schedule to filter by.
            build_id: The id of the build to filter by.
            deployment_id: The id of the deployment to filter by.
            orchestrator_run_id: The run id of the orchestrator to filter by.
            name: The name of the run to filter by.
            status: The status of the pipeline run
            start_time: The start_time for the pipeline run
            end_time: The end_time for the pipeline run
            num_steps: The number of steps for the pipeline run
            unlisted: If the runs should be unlisted or not.

        Returns:
            A page with Pipeline Runs fitting the filter description
        """
        runs_filter_model = PipelineRunFilterModel(
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
            schedule_id=schedule_id,
            build_id=build_id,
            deployment_id=deployment_id,
            orchestrator_run_id=orchestrator_run_id,
            user_id=user_id,
            stack_id=stack_id,
            status=status,
            start_time=start_time,
            end_time=end_time,
            num_steps=num_steps,
            unlisted=unlisted,
        )
        runs_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_runs(runs_filter_model=runs_filter_model)

    def get_pipeline_run(
        self,
        name_id_or_prefix: Union[str, UUID],
        allow_name_prefix_match: bool = True,
    ) -> PipelineRunResponseModel:
        """Gets a pipeline run by name, ID, or prefix.

        Args:
            name_id_or_prefix: Name, ID, or prefix of the pipeline run.
            allow_name_prefix_match: If True, allow matching by name prefix.

        Returns:
            The pipeline run.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            get_method=self.zen_store.get_run,
            list_method=self.list_runs,
            name_id_or_prefix=name_id_or_prefix,
            allow_name_prefix_match=allow_name_prefix_match,
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

    # -------------
    # - STEP RUNS -
    # -------------

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
        num_outputs: Optional[Union[int, str]] = None,
    ) -> Page[StepRunResponseModel]:
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
            name: The name of the run to filter by.
            entrypoint_name: The entrypoint_name of the run to filter by.
            code_hash: The code_hash of the run to filter by.
            cache_key: The cache_key of the run to filter by.
            status: The name of the run to filter by.
            num_outputs: The number of outputs for the step run

        Returns:
            A page with Pipeline fitting the filter description
        """
        step_run_filter_model = StepRunFilterModel(
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
            num_outputs=num_outputs,
        )
        step_run_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_run_steps(
            step_run_filter_model=step_run_filter_model
        )

    def get_run_step(self, step_run_id: UUID) -> StepRunResponseModel:
        """Get a step run by ID.

        Args:
            step_run_id: The ID of the step run to get.

        Returns:
            The step run.
        """
        return self.zen_store.get_run_step(step_run_id)

    # -------------
    # - Artifacts -
    # -------------

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
        artifact_store_id: Optional[Union[str, UUID]] = None,
        type: Optional[ArtifactType] = None,
        data_type: Optional[str] = None,
        uri: Optional[str] = None,
        materializer: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        only_unused: Optional[bool] = False,
    ) -> Page[ArtifactResponseModel]:
        """Get all artifacts.

        Args:
            sort_by: The column to sort by
            page: The page of items
            size: The maximum size of all pages
            logical_operator: Which logical operator to use [and, or]
            id: Use the id of runs to filter by.
            created: Use to filter by time of creation
            updated: Use the last updated date for filtering
            name: The name of the run to filter by.
            artifact_store_id: The id of the artifact store to filter by.
            type: The type of the artifact to filter by.
            data_type: The data type of the artifact to filter by.
            uri: The uri of the artifact to filter by.
            materializer: The materializer of the artifact to filter by.
            workspace_id: The id of the workspace to filter by.
            user_id: The  id of the user to filter by.
            only_unused: Only return artifacts that are not used in any runs.

        Returns:
            A list of artifacts.
        """
        artifact_filter_model = ArtifactFilterModel(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            created=created,
            updated=updated,
            name=name,
            artifact_store_id=artifact_store_id,
            type=type,
            data_type=data_type,
            uri=uri,
            materializer=materializer,
            workspace_id=workspace_id,
            user_id=user_id,
            only_unused=only_unused,
        )
        artifact_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_artifacts(artifact_filter_model)

    def get_artifact(self, artifact_id: UUID) -> ArtifactResponseModel:
        """Get an artifact by ID.

        Args:
            artifact_id: The ID of the artifact to get.

        Returns:
            The artifact.
        """
        return self.zen_store.get_artifact(artifact_id)

    def delete_artifact(
        self,
        artifact_id: UUID,
        delete_metadata: bool = True,
        delete_from_artifact_store: bool = False,
    ) -> None:
        """Delete an artifact.

        By default, this will delete only the metadata of the artifact from the
        database, not the artifact itself.

        Args:
            artifact_id: The ID of the artifact to delete.
            delete_metadata: If True, delete the metadata of the artifact from
                the database.
            delete_from_artifact_store: If True, delete the artifact itself from
                the artifact store.
        """
        artifact = self.get_artifact(artifact_id=artifact_id)
        if delete_from_artifact_store:
            self._delete_artifact_from_artifact_store(artifact=artifact)
        if delete_metadata:
            self._delete_artifact_metadata(artifact=artifact)

    def _delete_artifact_from_artifact_store(
        self, artifact: ArtifactResponseModel
    ) -> None:
        """Delete an artifact from the artifact store.

        Args:
            artifact: The artifact to delete.

        Raises:
            Exception: If the artifact store is inaccessible.
        """
        from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
        from zenml.stack.stack_component import StackComponent

        if not artifact.artifact_store_id:
            logger.warning(
                f"Artifact '{artifact.uri}' does not have an artifact store "
                "associated with it. Skipping deletion from artifact store."
            )
            return
        try:
            artifact_store_model = self.get_stack_component(
                component_type=StackComponentType.ARTIFACT_STORE,
                name_id_or_prefix=artifact.artifact_store_id,
            )
            artifact_store = StackComponent.from_model(artifact_store_model)
            assert isinstance(artifact_store, BaseArtifactStore)
            artifact_store.rmtree(artifact.uri)
        except Exception as e:
            logger.error(
                f"Failed to delete artifact '{artifact.uri}' from the "
                "artifact store. This might happen if your local client "
                "does not have access to the artifact store or does not "
                "have the required integrations installed. Full error: "
                f"{e}"
            )
            raise e
        else:
            logger.info(
                f"Deleted artifact '{artifact.uri}' from the artifact store."
            )

    def _delete_artifact_metadata(
        self, artifact: ArtifactResponseModel
    ) -> None:
        """Delete the metadata of an artifact from the database.

        Args:
            artifact: The artifact to delete.

        Raises:
            ValueError: If the artifact is still used in any runs.
        """
        if artifact not in depaginate(
            partial(self.list_artifacts, only_unused=True)
        ):
            raise ValueError(
                "The metadata of artifacts that are used in runs cannot be "
                "deleted. Please delete all runs that use this artifact "
                "first."
            )
        self.zen_store.delete_artifact(artifact.id)
        logger.info(f"Deleted metadata of artifact '{artifact.uri}'.")

    # ----------------
    # - Run Metadata -
    # ----------------

    def create_run_metadata(
        self,
        metadata: Dict[str, "MetadataType"],
        pipeline_run_id: Optional[UUID] = None,
        step_run_id: Optional[UUID] = None,
        artifact_id: Optional[UUID] = None,
        stack_component_id: Optional[UUID] = None,
    ) -> Dict[str, RunMetadataResponseModel]:
        """Create run metadata.

        Args:
            metadata: The metadata to create as a dictionary of key-value pairs.
            pipeline_run_id: The ID of the pipeline run during which the
                metadata was produced. If provided, `step_run_id` and
                `artifact_id` must be None.
            step_run_id: The ID of the step run during which the metadata was
                produced. If provided, `pipeline_run_id` and `artifact_id` must
                be None.
            artifact_id: The ID of the artifact for which the metadata was
                produced. If provided, `pipeline_run_id` and `step_run_id` must
                be None.
            stack_component_id: The ID of the stack component that produced
                the metadata.

        Returns:
            The created metadata, as string to model dictionary.

        Raises:
            ValueError: If not exactly one of either `pipeline_run_id`,
                `step_run_id`, or `artifact_id` is provided.
        """
        from zenml.metadata.metadata_types import get_metadata_type

        if not (pipeline_run_id or step_run_id or artifact_id):
            raise ValueError(
                "Cannot create run metadata without linking it to any entity. "
                "Please provide either a `pipeline_run_id`, `step_run_id`, or "
                "`artifact_id`."
            )
        if (
            (pipeline_run_id and step_run_id)
            or (pipeline_run_id and artifact_id)
            or (step_run_id and artifact_id)
        ):
            raise ValueError(
                "Cannot create run metadata linked to multiple entities. "
                "Please provide only a `pipeline_run_id` or only a "
                "`step_run_id` or only an `artifact_id`."
            )

        created_metadata: Dict[str, RunMetadataResponseModel] = {}
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

            run_metadata = RunMetadataRequestModel(
                workspace=self.active_workspace.id,
                user=self.active_user.id,
                pipeline_run_id=pipeline_run_id,
                step_run_id=step_run_id,
                artifact_id=artifact_id,
                stack_component_id=stack_component_id,
                key=key,
                value=value,
                type=metadata_type,
            )
            metadata_model = self.zen_store.create_run_metadata(run_metadata)
            created_metadata[key] = metadata_model
        return created_metadata

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
        pipeline_run_id: Optional[UUID] = None,
        step_run_id: Optional[UUID] = None,
        artifact_id: Optional[UUID] = None,
        stack_component_id: Optional[UUID] = None,
        key: Optional[str] = None,
        value: Optional["MetadataType"] = None,
        type: Optional[str] = None,
    ) -> Page[RunMetadataResponseModel]:
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
            pipeline_run_id: The ID of the pipeline run the metadata belongs to.
            step_run_id: The ID of the step run the metadata belongs to.
            artifact_id: The ID of the artifact the metadata belongs to.
            stack_component_id: The ID of the stack component that produced
                the metadata.
            key: The key of the metadata.
            value: The value of the metadata.
            type: The type of the metadata.

        Returns:
            The run metadata.
        """
        metadata_filter_model = RunMetadataFilterModel(
            sort_by=sort_by,
            page=page,
            size=size,
            logical_operator=logical_operator,
            id=id,
            created=created,
            updated=updated,
            workspace_id=workspace_id,
            user_id=user_id,
            pipeline_run_id=pipeline_run_id,
            step_run_id=step_run_id,
            artifact_id=artifact_id,
            stack_component_id=stack_component_id,
            key=key,
            value=value,
            type=type,
        )
        metadata_filter_model.set_scope_workspace(self.active_workspace.id)
        return self.zen_store.list_run_metadata(metadata_filter_model)

    # .---------.
    # | SECRETS |
    # '---------'

    def create_secret(
        self,
        name: str,
        values: Dict[str, str],
        scope: SecretScope = SecretScope.WORKSPACE,
    ) -> "SecretResponseModel":
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
        create_secret_request = SecretRequestModel(
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
    ) -> "SecretResponseModel":
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
                    else name_id_or_prefix
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
        )

        for search_scope in search_scopes:

            partial_matches: List[SecretResponseModel] = []
            for secret in secrets.items:
                if secret.scope != search_scope:
                    continue
                # Exact match
                if secret.name == name_id_or_prefix:
                    # Need to fetch the secret again to get the secret values
                    return self.zen_store.get_secret(secret_id=secret.id)
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
                    secret_id=partial_matches[0].id
                )

        msg = (
            f"No secret found with name, ID or prefix "
            f"'{name_id_or_prefix}'"
        )
        if scope is not None:
            msg += f" in scope '{scope}'"

        raise KeyError(msg)

    def get_secret_by_name_and_scope(
        self, name: str, scope: Optional[SecretScope] = None
    ) -> "SecretResponseModel":
        """Fetches a registered secret with a given name and optional scope.

        This is a version of get_secret that restricts the search to a given
        name and an optional scope, without doing any prefix or UUID matching.

        If no scope is provided, the search will be done first in the user
        scope, then in the workspace scope.

        Args:
            name: The name of the secret to get.
            scope: The scope of the secret to get.

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
            )

            if len(secrets.items) >= 1:
                # Need to fetch the secret again to get the secret values
                return self.zen_store.get_secret(secret_id=secrets.items[0].id)

        msg = f"No secret with name '{name}' was found"
        if scope is not None:
            msg += f" in scope '{scope.value}'"

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
    ) -> Page[SecretResponseModel]:
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

        Returns:
            A list of all the secret models without the secret values.

        Raises:
            NotImplementedError: If centralized secrets management is not
                enabled.
        """
        secret_filter_model = SecretFilterModel(
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
                secret_filter_model=secret_filter_model
            )
        except NotImplementedError:
            raise NotImplementedError(
                "centralized secrets management is not supported or explicitly "
                "disabled in the target ZenML deployment."
            )

    def list_secrets_in_scope(
        self,
        scope: SecretScope,
    ) -> Page[SecretResponseModel]:
        """Fetches the list of secret in a given scope.

        The returned secrets do not contain the secret values. To get the
        secret values, use `get_secret` individually for each secret.

        Args:
            scope: The secrets scope to search for.

        Returns:
            The list of secrets in the given scope without the secret values.
        """
        logger.debug(f"Fetching the secrets in scope {scope.value}.")

        return self.list_secrets(
            scope=scope,
        )

    def update_secret(
        self,
        name_id_or_prefix: Union[str, UUID],
        scope: Optional[SecretScope] = None,
        new_name: Optional[str] = None,
        new_scope: Optional[SecretScope] = None,
        add_or_update_values: Optional[Dict[str, str]] = None,
        remove_values: Optional[List[str]] = None,
    ) -> SecretResponseModel:
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
        )

        secret_update = SecretUpdateModel()

        if new_name:
            secret_update.name = new_name
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

    # ---- utility prefix matching get functions -----

    @staticmethod
    def _get_entity_by_id_or_name_or_prefix(
        get_method: Callable[..., AnyResponseModel],
        list_method: Callable[..., Page[AnyResponseModel]],
        name_id_or_prefix: Union[str, UUID],
        allow_name_prefix_match: bool = True,
    ) -> "AnyResponseModel":
        """Fetches an entity using the id, name, or partial id/name.

        Args:
            get_method: The method to use to fetch the entity by id.
            list_method: The method to use to fetch all entities.
            name_id_or_prefix: The id, name or partial id of the entity to
                fetch.
            allow_name_prefix_match: If True, allow matching by name prefix.

        Returns:
            The entity with the given name, id or partial id.

        Raises:
            ZenKeyError: If there is more than one entity with that name
                or id prefix.
        """
        from zenml.utils.uuid_utils import is_valid_uuid

        # First interpret as full UUID
        if is_valid_uuid(name_id_or_prefix):
            return get_method(name_id_or_prefix)

        # If not a UUID, try to find by name
        assert not isinstance(name_id_or_prefix, UUID)
        entity = list_method(name=f"equals:{name_id_or_prefix}")

        # If only a single entity is found, return it
        if entity.total == 1:
            return entity.items[0]

        # If still no match, try with prefix now
        if entity.total == 0:
            return Client._get_entity_by_prefix(
                get_method=get_method,
                list_method=list_method,
                partial_id_or_name=name_id_or_prefix,
                allow_name_prefix_match=allow_name_prefix_match,
            )

        # If more than one entity with the same name is found, raise an error.
        entity_label = get_method.__name__.replace("get_", "") + "s"
        raise ZenKeyError(
            f"{entity.total} {entity_label} have been found that have "
            f"a name that matches the provided "
            f"string '{name_id_or_prefix}':\n"
            f"{[entity.items]}.\n"
            f"Please use the id to uniquely identify "
            f"only one of the {entity_label}s."
        )

    @staticmethod
    def _get_entity_by_prefix(
        get_method: Callable[..., AnyResponseModel],
        list_method: Callable[..., Page[AnyResponseModel]],
        partial_id_or_name: str,
        allow_name_prefix_match: bool,
    ) -> "AnyResponseModel":
        """Fetches an entity using a partial ID or name.

        Args:
            get_method: The method to use to fetch the entity by id.
            list_method: The method to use to fetch all entities.
            partial_id_or_name: The partial ID or name of the entity to fetch.
            allow_name_prefix_match: If True, allow matching by name prefix.

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
        }
        if allow_name_prefix_match:
            list_method_args["name"] = f"startswith:{partial_id_or_name}"

        entity = list_method(**list_method_args)

        # If only a single entity is found, return it.
        if entity.total == 1:
            return entity.items[0]

        entity_label = get_method.__name__.replace("get_", "") + "s"

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
