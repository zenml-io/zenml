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
import os
from abc import ABCMeta
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
    Type,
    TypeVar,
    Union,
    cast,
)
from uuid import UUID

from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    ENV_ZENML_ACTIVE_STACK_ID,
    ENV_ZENML_ENABLE_REPO_INIT_WARNINGS,
    ENV_ZENML_REPOSITORY_PATH,
    REPOSITORY_DIRECTORY_NAME,
    handle_bool_env_var,
)
from zenml.enums import PermissionType, StackComponentType, StoreType
from zenml.exceptions import (
    AlreadyExistsException,
    EntityExistsError,
    IllegalOperationError,
    InitializationException,
    ValidationError,
    ZenKeyError,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.models import (
    ComponentRequestModel,
    ComponentResponseModel,
    ComponentUpdateModel,
    FlavorRequestModel,
    FlavorResponseModel,
    PipelineRequestModel,
    PipelineResponseModel,
    PipelineRunResponseModel,
    ProjectRequestModel,
    ProjectResponseModel,
    ProjectUpdateModel,
    RoleAssignmentRequestModel,
    RoleAssignmentResponseModel,
    RoleRequestModel,
    RoleResponseModel,
    RoleUpdateModel,
    StackRequestModel,
    StackResponseModel,
    StackUpdateModel,
    StepRunResponseModel,
    TeamRequestModel,
    TeamResponseModel,
    TeamUpdateModel,
    UserRequestModel,
    UserResponseModel,
    UserUpdateModel,
)
from zenml.models.artifact_models import ArtifactResponseModel
from zenml.models.base_models import BaseResponseModel
from zenml.utils import io_utils
from zenml.utils.analytics_utils import AnalyticsEvent, event_handler, track
from zenml.utils.filesync_model import FileSyncModel

if TYPE_CHECKING:
    from zenml.config.pipeline_configurations import PipelineSpec
    from zenml.stack import Stack, StackComponentConfig
    from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)
AnyResponseModel = TypeVar("AnyResponseModel", bound=BaseResponseModel)


class ClientConfiguration(FileSyncModel):
    """Pydantic object used for serializing client configuration options."""

    _active_project: Optional["ProjectResponseModel"] = None
    active_project_id: Optional[UUID]
    active_stack_id: Optional[UUID]

    @property
    def active_project(self) -> ProjectResponseModel:
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
                "`zenml project set PROJECT_NAME` to set the active "
                "project."
            )

    def set_active_project(self, project: "ProjectResponseModel") -> None:
        """Set the project for the local client.

        Args:
            project: The project to set active.
        """
        self._active_project = project
        self.active_project_id = project.id

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
        used instead to manage the active stack, project etc.

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
        self._root = self.find_repository(root, enable_warnings=enable_warnings)

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
        self._config.set_active_project(active_project)

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

    @track(event=AnalyticsEvent.SET_PROJECT)
    def set_active_project(
        self, project_name_or_id: Union[str, UUID]
    ) -> "ProjectResponseModel":
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
            self.create_role_assignment(
                role_name_or_id=initial_role,
                user_or_team_name_or_id=created_user.id,
                project_name_or_id=None,
                is_user=True,
            )

        return created_user

    def get_user(
        self, name_id_or_prefix: Union[str, UUID]
    ) -> UserResponseModel:
        """Gets a user.

        Args:
            name_id_or_prefix: The name or ID of the user.

        Returns:
            The User
        """
        return self._get_entity_by_id_or_name_or_prefix(
            response_model=UserResponseModel,
            get_method=self.zen_store.get_user,
            list_method=self.zen_store.list_users,
            name_id_or_prefix=name_id_or_prefix,
        )

    def list_users(self, name: Optional[str] = None) -> List[UserResponseModel]:
        """List all users.

        Args:
            name: The name to filter by

        Returns:
            The User
        """
        return self.zen_store.list_users(name=name)

    def delete_user(self, user_name_or_id: str) -> None:
        """Delete a user.

        Args:
            user_name_or_id: The name or ID of the user to delete.
        """
        user = self.get_user(user_name_or_id)
        self.zen_store.delete_user(user_name_or_id=user.name)

    def update_user(
        self,
        user_name_or_id: Union[str, UUID],
        updated_name: Optional[str] = None,
        updated_full_name: Optional[str] = None,
        updated_email: Optional[str] = None,
        updated_email_opt_in: Optional[bool] = None,
    ) -> UserResponseModel:
        """Update a user.

        Args:
            user_name_or_id: The name or ID of the user to update.
            updated_name: The new name of the user.
            updated_full_name: The new full name of the user.
            updated_email: The new email of the user.
            updated_email_opt_in: The new email opt-in status of the user.

        Returns:
            The updated user.
        """
        user = self.get_user(name_id_or_prefix=user_name_or_id)
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
        self, name_id_or_prefix: Union[str, UUID]
    ) -> TeamResponseModel:
        """Gets a team.

        Args:
            name_id_or_prefix: The name or ID of the team.

        Returns:
            The Team
        """
        return self._get_entity_by_id_or_name_or_prefix(
            response_model=TeamResponseModel,
            get_method=self.zen_store.get_team,
            list_method=self.zen_store.list_teams,
            name_id_or_prefix=name_id_or_prefix,
        )

    def list_teams(self, name: Optional[str] = None) -> List[TeamResponseModel]:
        """List all teams.

        Args:
            name: The name to filter by

        Returns:
            The Team
        """
        return self.zen_store.list_teams(name=name)

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

    def delete_team(self, team_name_or_id: str) -> None:
        """Delete a team.

        Args:
            team_name_or_id: The name or ID of the team to delete.
        """
        team = self.get_team(team_name_or_id)
        self.zen_store.delete_team(team_name_or_id=team.name)

    def update_team(
        self,
        team_name_or_id: str,
        new_name: Optional[str] = None,
        remove_users: Optional[List[str]] = None,
        add_users: Optional[List[str]] = None,
    ) -> TeamResponseModel:
        """Update a team.

        Args:
            team_name_or_id: The name or ID of the team to update.
            new_name: The new name of the team.
            remove_users: The users to remove from the team.
            add_users: The users to add to the team.

        Returns:
            The updated team.

        Raises:
            RuntimeError: If the same user is in both `remove_users` and
                `add_users`.
        """
        team = self.get_team(team_name_or_id)

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
        self, name_id_or_prefix: Union[str, UUID]
    ) -> RoleResponseModel:
        """Gets a role.

        Args:
            name_id_or_prefix: The name or ID of the role.

        Returns:
            The fetched role.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            response_model=RoleResponseModel,
            get_method=self.zen_store.get_role,
            list_method=self.zen_store.list_roles,
            name_id_or_prefix=name_id_or_prefix,
        )

    def list_roles(self, name: Optional[str] = None) -> List[RoleResponseModel]:
        """Fetches roles.

        Args:
            name: The name of the roles.

        Returns:
            The list of roles.
        """
        return self.zen_store.list_roles(name=name)

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
        role = self.get_role(name_id_or_prefix=name_id_or_prefix)

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
        self.zen_store.delete_role(role_name_or_id=name_id_or_prefix)

    # ---------------- #
    # ROLE ASSIGNMENTS #
    # ---------------- #

    def get_role_assignment(
        self,
        role_name_or_id: str,
        user_or_team_name_or_id: str,
        is_user: bool,
        project_name_or_id: Optional[str] = None,
    ) -> RoleAssignmentResponseModel:
        """Get a role assignment.

        Args:
            role_name_or_id: The name or ID of the role.
            user_or_team_name_or_id: The name or ID of the user or team.
            is_user: Whether to interpret the `user_or_team_name_or_id` field as
                user (=True) or team (=False).
            project_name_or_id: project scope within which to assign the role.

        Returns:
            The role assignment.

        Raises:
            RuntimeError: If the role assignment does not exist.
        """
        if is_user:
            role_assignments = self.zen_store.list_role_assignments(
                project_name_or_id=project_name_or_id,
                user_name_or_id=user_or_team_name_or_id,
                role_name_or_id=role_name_or_id,
            )
        else:
            role_assignments = self.zen_store.list_role_assignments(
                project_name_or_id=project_name_or_id,
                user_name_or_id=user_or_team_name_or_id,
                role_name_or_id=role_name_or_id,
            )
        # Implicit assumption is that maximally one such assignment can exist
        if role_assignments:
            return role_assignments[0]
        else:
            raise RuntimeError(
                "No such role assignment could be found for "
                f"user/team : {user_or_team_name_or_id} with "
                f"role : {role_name_or_id} within "
                f"project : {project_name_or_id}"
            )

    def create_role_assignment(
        self,
        role_name_or_id: Union[str, UUID],
        user_or_team_name_or_id: Union[str, UUID],
        is_user: bool,
        project_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> RoleAssignmentResponseModel:
        """Create a role assignment.

        Args:
            role_name_or_id: Name or ID of the role to assign.
            user_or_team_name_or_id: Name or ID of the user or team to assign
                the role to.
            is_user: Whether to interpret the `user_or_team_name_or_id` field as
                user (=True) or team (=False).
            project_name_or_id: project scope within which to assign the role.

        Returns:
            The newly created role assignment.
        """
        role = self.get_role(name_id_or_prefix=role_name_or_id)
        project = None
        if project_name_or_id:
            project = self.get_project(name_id_or_prefix=project_name_or_id)
        if is_user:
            user = self.get_user(name_id_or_prefix=user_or_team_name_or_id)
            role_assignment = RoleAssignmentRequestModel(
                role=role.id,
                user=user.id,
                project=project,
            )
        else:
            team = self.get_team(name_id_or_prefix=user_or_team_name_or_id)
            role_assignment = RoleAssignmentRequestModel(
                role=role.id,
                team=team.id,
                project=project,
            )

        return self.zen_store.create_role_assignment(
            role_assignment=role_assignment
        )

    def delete_role_assignment(
        self,
        role_name_or_id: str,
        user_or_team_name_or_id: str,
        is_user: bool,
        project_name_or_id: Optional[str] = None,
    ) -> None:
        """Delete a role assignment.

        Args:
            role_name_or_id: Role to assign
            user_or_team_name_or_id: team to assign the role to
            is_user: Whether to interpret the user_or_team_name_or_id field as
                user (=True) or team (=False)
            project_name_or_id: project scope within which to assign the role
        """
        role_assignment = self.get_role_assignment(
            role_name_or_id=role_name_or_id,
            user_or_team_name_or_id=user_or_team_name_or_id,
            is_user=is_user,
            project_name_or_id=project_name_or_id,
        )
        self.zen_store.delete_role_assignment(role_assignment.id)

    def list_role_assignment(
        self,
        role_name_or_id: Optional[str] = None,
        user_name_or_id: Optional[str] = None,
        team_name_or_id: Optional[str] = None,
        project_name_or_id: Optional[str] = None,
    ) -> List[RoleAssignmentResponseModel]:
        """List role assignments.

        Args:
            role_name_or_id: Only list assignments for this role
            user_name_or_id: Only list assignments for this user
            team_name_or_id: Only list assignments for this team
            project_name_or_id: Only list assignments in this project

        Returns:
            List of role assignments
        """
        return self.zen_store.list_role_assignments(
            project_name_or_id=project_name_or_id,
            role_name_or_id=role_name_or_id,
            user_name_or_id=user_name_or_id,
            team_name_or_id=team_name_or_id,
        )

    # ------- #
    # PROJECT #
    # ------- #

    @property
    def active_project(self) -> "ProjectResponseModel":
        """Get the currently active project of the local client.

        If no active project is configured locally for the client, the
        active project in the global configuration is used instead.

        Returns:
            The active project.

        Raises:
            RuntimeError: If the active project is not set.
        """
        project: Optional["ProjectResponseModel"] = None
        if self._config:
            project = self._config.active_project

        if not project:
            project = GlobalConfiguration().get_active_project()

        if not project:
            raise RuntimeError(
                "No active project is configured. Run "
                "`zenml project set PROJECT_NAME` to set the active "
                "project."
            )

        from zenml.zen_stores.base_zen_store import DEFAULT_PROJECT_NAME

        if project.name != DEFAULT_PROJECT_NAME:
            logger.warning(
                f"You are running with a non-default project "
                f"'{project.name}'. Any stacks, components, "
                f"pipelines and pipeline runs produced in this "
                f"project will currently not be accessible through "
                f"the dashboard. However, this will be possible "
                f"in the near future."
            )
        return project

    def get_project(
        self, name_id_or_prefix: Optional[Union[UUID, str]]
    ) -> ProjectResponseModel:
        """Gets a project.

        Args:
            name_id_or_prefix: The name or ID of the project.

        Returns:
            The Project
        """
        if not name_id_or_prefix:
            return self.active_project
        return self._get_entity_by_id_or_name_or_prefix(
            response_model=ProjectResponseModel,
            get_method=self.zen_store.get_project,
            list_method=self.zen_store.list_projects,
            name_id_or_prefix=name_id_or_prefix,
        )

    def create_project(
        self, name: str, description: str
    ) -> "ProjectResponseModel":
        """Create a new project.

        Args:
            name: Name of the project.
            description: Description of the project.

        Returns:
            The created project.
        """
        return self.zen_store.create_project(
            ProjectRequestModel(name=name, description=description)
        )

    def update_project(
        self,
        name_id_or_prefix: Optional[Union[UUID, str]],
        new_name: Optional[str] = None,
        new_description: Optional[str] = None,
    ) -> "ProjectResponseModel":
        """Update a project.

        Args:
            name_id_or_prefix: Name, ID or prefix of the project to update.
            new_name: New name of the project.
            new_description: New description of the project.

        Returns:
            The updated project.
        """
        project = self.get_project(name_id_or_prefix=name_id_or_prefix)
        project_update = ProjectUpdateModel()
        if new_name:
            project_update.name = new_name
        if new_description:
            project_update.description = new_description
        return self.zen_store.update_project(
            project_id=project.id,
            project_update=project_update,
        )

    def delete_project(self, project_name_or_id: str) -> None:
        """Delete a project.

        Args:
            project_name_or_id: The name or ID of the project to delete.

        Raises:
            IllegalOperationError: If the project to delete is the active
                project.
        """
        project = self.zen_store.get_project(project_name_or_id)
        if self.active_project.id == project.id:
            raise IllegalOperationError(
                f"Project '{project_name_or_id}' cannot be deleted since it is "
                "currently active. Please set another project as active first."
            )
        self.zen_store.delete_project(project_name_or_id=project_name_or_id)

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
                "`zenml stack set PROJECT_NAME` to set the active "
                "stack."
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
        self, name_id_or_prefix: Optional[Union[UUID, str]] = None
    ) -> "StackResponseModel":
        """Get a stack by name, ID or prefix.

        If no name, ID or prefix is provided, the active stack is returned.

        Args:
            name_id_or_prefix: The name, ID or prefix of the stack.

        Returns:
            The stack.
        """
        if name_id_or_prefix is not None:
            return self._get_entity_by_id_or_name_or_prefix(
                response_model=StackResponseModel,
                get_method=self.zen_store.get_stack,
                list_method=self.zen_store.list_stacks,
                name_id_or_prefix=name_id_or_prefix,
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
            if c_identifier:
                component = self.get_stack_component(
                    name_id_or_prefix=c_identifier,
                    component_type=c_type,
                )
                stack_components[c_type] = [component.id]

                if is_shared:
                    if not component.is_shared:
                        raise ValueError(
                            "You attempted to include a private "
                            f"{c_type} {name} in a shared stack. This "
                            f"is not supported. You can either share"
                            f" the {c_type} with the following "
                            f"command: \n `zenml {c_type.replace('_', '-')} "
                            f"share`{component.id}`\n "
                            f"or create the stack privately and "
                            f"then share it and all of its components using: "
                            f"\n `zenml stack share {name} -r`"
                        )

        stack = StackRequestModel(
            name=name,
            components=stack_components,
            is_shared=is_shared,
            project=self.active_project.id,
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
        stack = self.get_stack(name_id_or_prefix=name_id_or_prefix)

        # Create the update model
        update_model = StackUpdateModel(
            project=self.active_project.id,
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
                components_dict[component_type] = [c.id for c in component_list]

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
        stack = self.get_stack(name_id_or_prefix=name_id_or_prefix)

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
        project_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        component_id: Optional[UUID] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List["StackResponseModel"]:
        """Lists all stacks.

        Args:
            project_name_or_id: The name or id of the project to filter by.
            user_name_or_id: The name or id of the user to filter by.
            component_id: The id of the component to filter by.
            name: The name of the stack to filter by.
            is_shared: The shared status of the stack to filter by.

        Returns:
            A list of stacks.
        """
        return self.zen_store.list_stacks(
            project_name_or_id=project_name_or_id or self.active_project.id,
            user_name_or_id=user_name_or_id,
            component_id=component_id,
            name=name,
            is_shared=is_shared,
        )

    @track(event=AnalyticsEvent.SET_STACK)
    def activate_stack(self, stack_name_id_or_prefix: Union[str, UUID]) -> None:
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

    def _validate_stack_configuration(self, stack: "StackRequestModel") -> None:
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
    ) -> "ComponentResponseModel":
        """Fetches a registered stack component.

        If the name_id_or_prefix is provided, it will try to fetch the component
        with the corresponding identifier. If not, it will try to fetch the
        active component of the given type.

        Args:
            component_type: The type of the component to fetch
            name_id_or_prefix: The id of the component to fetch.

        Returns:
            The registered stack component.

        Raises:
            KeyError: If no name_id_or_prefix is provided and no such component
                is part of the active stack.
        """
        if name_id_or_prefix is not None:
            return self._get_component_by_id_or_name_or_prefix(
                name_id_or_prefix=name_id_or_prefix,
                component_type=component_type,
            )
        else:
            components = self.active_stack_model.components.get(
                component_type, None
            )
            if components is None:
                raise KeyError(
                    "No name_id_or_prefix provided and there is no active "
                    f"{component_type} in the current active stack."
                )

            return components[0]

    def list_stack_components(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        component_type: Optional[str] = None,
        flavor_name: Optional[str] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List["ComponentResponseModel"]:
        """Lists all registered stack components.

        Args:
            project_name_or_id: The name or id of the project to filter by.
            user_name_or_id: The name or id of the user to filter by.
            component_type: The type of the component to filter by.
            flavor_name: The name of the flavor to filter by.
            name: The name of the component to filter by.
            is_shared: The shared status of the component to filter by.

        Returns:
            A list of stack components.
        """
        return self.zen_store.list_stack_components(
            project_name_or_id=project_name_or_id or self.active_project.id,
            user_name_or_id=user_name_or_id,
            type=component_type,
            flavor_name=flavor_name,
            name=name,
            is_shared=is_shared,
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
        configuration_obj = flavor_class.config_class(**configuration)

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
            project=self.active_project.id,
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
        )

        update_model = ComponentUpdateModel(
            project=self.active_project.id,
            user=self.active_user.id,
        )

        if name is not None:
            shared_status = is_shared or component.is_shared

            existing_components = self.list_stack_components(
                name=name,
                is_shared=shared_status,
                component_type=component_type,
            )
            if existing_components:
                raise EntityExistsError(
                    f"There are already existing "
                    f"{'shared' if shared_status else 'unshared'} components "
                    f"with the name '{name}'."
                )
            update_model.name = name

        if is_shared is not None:
            current_name = update_model.name or component.name
            existing_components = self.list_stack_components(
                name=current_name, is_shared=True, component_type=component_type
            )
            if any([e.id != component.id for e in existing_components]):
                raise EntityExistsError(
                    f"There are already existing shared components with "
                    f"the name '{current_name}'"
                )
            update_model.is_shared = is_shared

        if configuration is not None:
            existing_configuration = component.configuration
            existing_configuration.update(configuration)

            existing_configuration = {
                k: v for k, v in existing_configuration.items() if v is not None
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

    def deregister_stack_component(
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
        """
        from zenml.utils.source_utils import validate_flavor_source

        flavor = validate_flavor_source(
            source=source,
            component_type=component_type,
        )()

        create_flavor_request = FlavorRequestModel(
            source=source,
            type=flavor.type,
            name=flavor.name,
            config_schema=flavor.config_schema,
            user=self.active_user.id,
            project=self.active_project.id,
        )

        return self.zen_store.create_flavor(flavor=create_flavor_request)

    def get_flavor(self, name_id_or_prefix: str) -> "FlavorResponseModel":
        """Get a stack component flavor.

        Args:
            name_id_or_prefix: The name, ID or prefix to the id of the flavor
                to get.

        Returns:
            The stack component flavor.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            response_model=FlavorResponseModel,
            get_method=self.zen_store.get_flavor,
            list_method=self.zen_store.list_flavors,
            name_id_or_prefix=name_id_or_prefix,
        )

    def delete_flavor(self, name_id_or_prefix: str) -> None:
        """Deletes a flavor.

        Args:
            name_id_or_prefix: The name, id or prefix of the id for the
                flavor to delete.
        """
        flavor = self.get_flavor(name_id_or_prefix)
        self.zen_store.delete_flavor(flavor_id=flavor.id)

        logger.info(f"Deleted flavor '{flavor.name}' of type '{flavor.type}'.")

    def list_flavors(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> List["FlavorResponseModel"]:
        """Fetches all the flavor models.

        Args:
            project_name_or_id: The name or id of the project to filter by.
            user_name_or_id: The name or id of the user to filter by.

        Returns:
            A list of all the flavor models.
        """
        from zenml.stack.flavor_registry import flavor_registry

        zenml_flavors = flavor_registry.flavors
        custom_flavors = self.zen_store.list_flavors(
            project_name_or_id=project_name_or_id or self.active_project.id,
            user_name_or_id=user_name_or_id,
        )
        return zenml_flavors + custom_flavors

    def get_flavors_by_type(
        self, component_type: "StackComponentType"
    ) -> List["FlavorResponseModel"]:
        """Fetches the list of flavor for a stack component type.

        Args:
            component_type: The type of the component to fetch.

        Returns:
            The list of flavors.
        """
        logger.debug(f"Fetching the flavors of type {component_type}.")

        from zenml.stack.flavor_registry import flavor_registry

        zenml_flavors = flavor_registry.get_flavors_by_type(
            component_type=component_type
        )

        custom_flavors = self.zen_store.list_flavors(
            project_name_or_id=self.active_project.id,
            component_type=component_type,
        )

        return zenml_flavors + custom_flavors

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

        from zenml.stack.flavor_registry import flavor_registry

        try:
            zenml_flavor = flavor_registry.get_flavor_by_name_and_type(
                component_type=component_type,
                name=name,
            )
        except KeyError:
            zenml_flavor = None

        custom_flavors = self.zen_store.list_flavors(
            project_name_or_id=self.active_project.id,
            component_type=component_type,
            name=name,
        )

        if custom_flavors:
            if len(custom_flavors) > 1:
                raise KeyError(
                    f"More than one flavor with name {name} and type "
                    f"{component_type} exists."
                )

            if zenml_flavor:
                # If there is one, check whether the same flavor exists as
                # a ZenML flavor to give out a warning
                logger.warning(
                    f"There is a custom implementation for the flavor "
                    f"'{name}' of a {component_type}, which is currently "
                    f"overwriting the same flavor provided by ZenML."
                )
            return custom_flavors[0]
        else:
            if zenml_flavor:
                return zenml_flavor
            else:
                raise KeyError(
                    f"No flavor with name '{name}' and type '{component_type}' "
                    "exists."
                )

    # -------------
    # - PIPELINES -
    # -------------

    def create_pipeline(
        self,
        pipeline_name: str,
        pipeline_spec: "PipelineSpec",
        pipeline_docstring: Optional[str],
    ) -> UUID:
        """Registers a pipeline in the ZenStore within the active project.

        This will do one of the following three things:
        A) If there is no pipeline with this name, register a new pipeline.
        B) If a pipeline exists that has the same config, use that pipeline.
        C) If a pipeline with different config exists, raise an error.

        Args:
            pipeline_name: The name of the pipeline to register.
            pipeline_spec: The spec of the pipeline.
            pipeline_docstring: The docstring of the pipeline.

        Returns:
            The id of the existing or newly registered pipeline.

        Raises:
            AlreadyExistsException: If there is an existing pipeline in the
                project with the same name but a different configuration.
        """
        existing_pipelines = self.zen_store.list_pipelines(
            name=pipeline_name,
            project_name_or_id=self.active_project.id,
        )

        # A) If there is no pipeline with this name, register a new pipeline.
        if len(existing_pipelines) == 0:
            create_pipeline_request = PipelineRequestModel(
                project=self.active_project.id,
                user=self.active_user.id,
                name=pipeline_name,
                spec=pipeline_spec,
                docstring=pipeline_docstring,
            )
            pipeline = self.zen_store.create_pipeline(
                pipeline=create_pipeline_request
            )
            logger.info(f"Registered new pipeline with name {pipeline.name}.")
            return pipeline.id

        else:
            if len(existing_pipelines) == 1:
                existing_pipeline = existing_pipelines[0]
                # B) If a pipeline exists that has the same config, use that
                # pipeline.
                if pipeline_spec == existing_pipeline.spec:
                    logger.debug(
                        "Did not register pipeline since it already exists."
                    )
                    return existing_pipeline.id

        # C) If a pipeline with different config exists, raise an error.
        error_msg = (
            f"Cannot run pipeline '{pipeline_name}' since this name has "
            "already been registered with a different pipeline "
            "configuration. You have three options to resolve this issue:\n"
            "1) You can register a new pipeline by changing the name "
            "of your pipeline, e.g., via `@pipeline(name='new_pipeline_name')."
            "\n2) You can execute the current run without linking it to any "
            "pipeline by setting the 'unlisted' argument to `True`, e.g., "
            "via `my_pipeline_instance.run(unlisted=True)`. "
            "Unlisted runs are not linked to any pipeline, but are still "
            "tracked by ZenML and can be accessed via the 'All Runs' tab. \n"
            "3) You can delete the existing pipeline via "
            f"`zenml pipeline delete {pipeline_name}`. This will then "
            "change all existing runs of this pipeline to become unlisted."
        )
        raise AlreadyExistsException(error_msg)

    def list_pipelines(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        name: Optional[str] = None,
    ) -> List[PipelineResponseModel]:
        """List pipelines.

        Args:
            project_name_or_id: If provided, only list pipelines in this
                project.
            user_name_or_id: If provided, only list pipelines from this user.
            name: If provided, only list pipelines with this name.

        Returns:
            A list of pipelines.
        """
        return self.zen_store.list_pipelines(
            project_name_or_id=project_name_or_id or self.active_project.id,
            user_name_or_id=user_name_or_id,
            name=name,
        )

    def get_pipeline(
        self, name_id_or_prefix: Union[str, UUID]
    ) -> PipelineResponseModel:
        """Get a pipeline by name, id or prefix.

        Args:
            name_id_or_prefix: The name, id or prefix of the pipeline.

        Returns:
            The pipeline.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            response_model=PipelineResponseModel,
            get_method=self.zen_store.get_pipeline,
            list_method=self.zen_store.list_pipelines,
            name_id_or_prefix=name_id_or_prefix,
        )

    def delete_pipeline(self, name_id_or_prefix: Union[str, UUID]) -> None:
        """Delete a pipeline.

        Args:
            name_id_or_prefix: The name, id or prefix id of the pipeline
                to delete.
        """
        pipeline = self.get_pipeline(name_id_or_prefix=name_id_or_prefix)
        self.zen_store.delete_pipeline(pipeline_id=pipeline.id)

    # ----------------------
    # - PIPELINE/STEP RUNS -
    # ----------------------

    def list_runs(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        stack_id: Optional[UUID] = None,
        component_id: Optional[UUID] = None,
        run_name: Optional[str] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        pipeline_id: Optional[UUID] = None,
        unlisted: bool = False,
    ) -> List[PipelineRunResponseModel]:
        """Gets all pipeline runs.

        Args:
            project_name_or_id: If provided, only return runs for this project.
            stack_id: If provided, only return runs for this stack.
            component_id: Optionally filter for runs that used the
                          component
            run_name: Run name if provided
            user_name_or_id: If provided, only return runs for this user.
            pipeline_id: If provided, only return runs for this pipeline.
            unlisted: If True, only return unlisted runs that are not
                associated with any pipeline (filter by `pipeline_id==None`).

        Returns:
            A list of all pipeline runs.
        """
        return self.zen_store.list_runs(
            project_name_or_id=project_name_or_id or self.active_project.id,
            user_name_or_id=user_name_or_id,
            stack_id=stack_id,
            component_id=component_id,
            name=run_name,
            pipeline_id=pipeline_id,
            unlisted=unlisted,
        )

    def get_pipeline_run(
        self,
        name_id_or_prefix: Union[str, UUID],
    ) -> PipelineRunResponseModel:
        """Gets a pipeline run by name, ID, or prefix.

        Args:
            name_id_or_prefix: Name, ID, or prefix of the pipeline run.

        Returns:
            The pipeline run.
        """
        return self._get_entity_by_id_or_name_or_prefix(
            response_model=PipelineRunResponseModel,
            get_method=self.zen_store.get_run,
            list_method=self.zen_store.list_runs,
            name_id_or_prefix=name_id_or_prefix,
        )

    def delete_pipeline_run(
        self,
        name_id_or_prefix: Union[str, UUID],
    ) -> None:
        """Deletes a pipeline run.

        Args:
            name_id_or_prefix: Name, ID, or prefix of the pipeline run.
        """
        run = self.get_pipeline_run(name_id_or_prefix=name_id_or_prefix)
        self.zen_store.delete_run(run_id=run.id)

    def list_run_steps(
        self,
        pipeline_run_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
    ) -> List[StepRunResponseModel]:
        """Get all step runs.

        Args:
            pipeline_run_id: If provided, only return steps for this pipeline run.
            project_id: If provided, only return step runs in this project.

        Returns:
            A list of step runs.
        """
        return self.zen_store.list_run_steps(
            run_id=pipeline_run_id, project_id=project_id
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
        project_name_or_id: Optional[Union[str, UUID]] = None,
        artifact_uri: Optional[str] = None,
        artifact_store_id: Optional[UUID] = None,
        only_unused: bool = False,
    ) -> List[ArtifactResponseModel]:
        """Get all artifacts.

        Args:
            project_name_or_id: If provided, only return artifacts for this
                project. Otherwise, filter by the active project.
            artifact_uri: If provided, only return artifacts with this URI.
            artifact_store_id: If provided, only return artifacts from this
                artifact store.
            only_unused: If True, only return artifacts that are not used in
                any runs.

        Returns:
            A list of artifacts.
        """
        return self.zen_store.list_artifacts(
            project_name_or_id=project_name_or_id or self.active_project.id,
            artifact_uri=artifact_uri,
            artifact_store_id=artifact_store_id,
            only_unused=only_unused,
        )

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
        if artifact not in self.list_artifacts(only_unused=True):
            raise ValueError(
                "The metadata of artifacts that are used in runs cannot be "
                "deleted. Please delete all runs that use this artifact "
                "first."
            )
        self.zen_store.delete_artifact(artifact.id)
        logger.info(f"Deleted metadata of artifact '{artifact.uri}'.")

    # ---- utility prefix matching get functions -----

    # TODO: This prefix matching functionality should be moved to the
    #   corresponding SQL ZenStore list methods

    def _get_component_by_id_or_name_or_prefix(
        self,
        name_id_or_prefix: Union[str, UUID],
        component_type: StackComponentType,
    ) -> "ComponentResponseModel":
        """Fetches a component of given type using the name, id or partial id.

        Args:
            name_id_or_prefix: The id, name or partial id of the component to
                fetch.
            component_type: The type of the component to fetch.

        Returns:
            The component with the given name.

        Raises:
            KeyError: If no component with the given name exists.
            ZenKeyError: If there is more than one component with that name
                or id prefix.
        """
        # First interpret as full UUID
        if isinstance(name_id_or_prefix, UUID):
            return self.zen_store.get_stack_component(name_id_or_prefix)
        else:
            try:
                entity_id = UUID(name_id_or_prefix)
            except ValueError:
                pass
            else:
                return self.zen_store.get_stack_component(entity_id)

        name_id_or_prefix = str(name_id_or_prefix)

        components = self.zen_store.list_stack_components(
            name=name_id_or_prefix,
            type=component_type,
            project_name_or_id=self.active_project.id,
        )
        display_name = component_type.value.replace("_", " ")

        if len(components) > 1:
            component_list = "\n".join(
                [f"{c.name} ({c.id})" for c in components]
            )
            raise ZenKeyError(
                f"Multiple {display_name} instances have been found for "
                f"name '{name_id_or_prefix}':\n{component_list}.\n"
                f"Please specify by full or partial id."
            )
        elif len(components) == 1:
            return components[0]

        logger.debug(
            f"No {display_name} instance with name '{name_id_or_prefix}' "
            f"exists. Trying to resolve as partial_id..."
        )

        components = self.zen_store.list_stack_components(
            type=component_type,
            project_name_or_id=self.active_project.id,
        )

        filtered_comps = [
            component
            for component in components
            if str(component.id).startswith(name_id_or_prefix)
        ]
        if len(filtered_comps) > 1:
            filtered_component_list = "\n ".join(
                [f"{fc.name} ({fc.id})" for fc in filtered_comps]
            )
            raise ZenKeyError(
                f"The {display_name} instances listed below all share the "
                f"provided prefix '{name_id_or_prefix}' on their ids:\n"
                f"{filtered_component_list}.\n"
                f"Please provide more characters to uniquely identify only "
                f"one component."
            )

        elif len(filtered_comps) == 1:
            return filtered_comps[0]

        raise KeyError(
            f"No {display_name} with name or id prefix '{name_id_or_prefix}' "
            f"exists."
        )

    def _get_entity_by_id_or_name_or_prefix(
        self,
        response_model: Type[AnyResponseModel],
        get_method: Callable[..., AnyResponseModel],
        list_method: Callable[..., List[AnyResponseModel]],
        name_id_or_prefix: Union[str, UUID],
    ) -> "AnyResponseModel":
        """Fetches an entity using the name, id or partial id.

        Args:
            response_model: The response model to use for the entity.
            get_method: The method to use to fetch the entity by id.
            list_method: The method to use to fetch all entities.
            name_id_or_prefix: The id, name or partial id of the entity to
                fetch.

        Returns:
            The entity with the given name, id or partial id.

        Raises:
            KeyError: If no entity with the given name exists.
            ZenKeyError: If there is more than one entity with that name
                or id prefix.
        """
        # First interpret as full UUID
        if isinstance(name_id_or_prefix, UUID):
            return get_method(name_id_or_prefix)
        else:
            try:
                entity_id = UUID(name_id_or_prefix)
            except ValueError:
                pass
            else:
                return get_method(entity_id)

        if "project" in response_model.__fields__:
            entities: List[AnyResponseModel] = list_method(
                name=name_id_or_prefix,
                project_name_or_id=self.active_project.id,
            )
        else:
            entities = list_method(
                name=name_id_or_prefix,
            )

        entity_label = list_method.__name__.replace("list_", "").replace(
            "_", " "
        )

        if len(entities) > 1:
            entity_list = "\n".join(
                [
                    f"{getattr(entity, 'name', '')} ({entity.id})"
                    for entity in entities
                ]
            )
            raise ZenKeyError(
                f"Multiple {entity_label} have been found for name "
                f"'{name_id_or_prefix}':\n{entity_list}.\n"
                f"Please specify by full or partial id."
            )

        elif len(entities) == 1:
            return entities[0]
        else:
            logger.debug(
                f"No {entity_label} with name '{name_id_or_prefix}' "
                f"exists. Trying to resolve as partial_id"
            )

            if "project" in response_model.__fields__:
                entities = list_method(
                    project_name_or_id=self.active_project.id,
                )
            else:
                entities = list_method()

            filtered_entities = [
                entity
                for entity in entities
                if str(entity.id).startswith(name_id_or_prefix)
            ]
            if len(filtered_entities) > 1:
                entity_list = "\n".join(
                    [
                        f"{getattr(f_entity, 'name', '')} ({f_entity.id})"
                        for f_entity in filtered_entities
                    ]
                )

                raise ZenKeyError(
                    f"Multiple {entity_label} have been found that share "
                    f"the provided prefix '{name_id_or_prefix}' on their ids:\n"
                    f"{entity_list}\n"
                    f"Please provide more characters to uniquely identify "
                    f"only one of the {entity_label}."
                )

            elif len(filtered_entities) == 1:
                return filtered_entities[0]
            else:
                raise KeyError(
                    f"No {entity_label} with name or id prefix "
                    f"'{name_id_or_prefix}' exists."
                )
