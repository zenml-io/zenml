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
"""REST Zen Store implementation."""

import os
import re
from pathlib import Path, PurePath
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

import requests
import urllib3
from pydantic import BaseModel, validator

from zenml.config.global_config import GlobalConfiguration
from zenml.config.store_config import StoreConfiguration
from zenml.constants import (
    API,
    ARTIFACTS,
    EMAIL_ANALYTICS,
    FLAVORS,
    INFO,
    INPUTS,
    LOGIN,
    METADATA_CONFIG,
    OUTPUTS,
    PIPELINES,
    PROJECTS,
    ROLES,
    RUNS,
    STACK_COMPONENTS,
    STACKS,
    STATUS,
    STEPS,
    TEAMS,
    USERS,
    VERSION_1,
)
from zenml.enums import ExecutionStatus, StackComponentType, StoreType
from zenml.exceptions import (
    AuthorizationException,
    DoesNotExistException,
    EntityExistsError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.models import (
    ProjectModel,
    RoleAssignmentModel,
    RoleModel,
    TeamModel,
    UserModel,
)
from zenml.models.server_models import ServerModel
from zenml.new_models import (
    ArtifactModel,
    ComponentModel,
    ComponentRequestModel,
    FlavorModel,
    FlavorRequestModel,
    PipelineModel,
    PipelineRequestModel,
    PipelineRunModel,
    StackModel,
    StackRequestModel,
    StepRunModel,
    ProjectModel,
    ProjectRequestModel,
    RoleModel,
    RoleRequestModel,
    TeamModel,
    TeamRequestModel,
    UserModel,
    UserRequestModel,

)
from zenml.new_models.base_models import (
    BaseRequestModel,
    BaseResponseModel,
    ProjectScopedRequestModel,
    ProjectScopedResponseModel,
)
from zenml.utils.analytics_utils import AnalyticsEvent, track

from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)

if TYPE_CHECKING:
    from ml_metadata.proto.metadata_store_pb2 import ConnectionConfig

# type alias for possible json payloads (the Anys are recursive Json instances)
Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

AnyRequestModel = TypeVar("AnyRequestModel", bound=BaseRequestModel)
AnyProjestRequestModel = TypeVar(
    "AnyProjestRequestModel", bound=ProjectScopedRequestModel
)

AnyResponseModel = TypeVar("AnyResponseModel", bound=BaseResponseModel)
AnyProjestResponseModel = TypeVar(
    "AnyProjestResponseModel", bound=ProjectScopedResponseModel
)

DEFAULT_HTTP_TIMEOUT = 5


class RestZenStoreConfiguration(StoreConfiguration):
    """REST ZenML store configuration.

    Attributes:
        username: The username to use to connect to the Zen server.
        password: The password to use to connect to the Zen server.
        verify_ssl: Either a boolean, in which case it controls whether we
            verify the server's TLS certificate, or a string, in which case it
            must be a path to a CA bundle to use or the CA bundle value itself.
        http_timeout: The timeout to use for all requests.
    """

    type: StoreType = StoreType.REST
    username: str
    password: str = ""
    verify_ssl: Union[bool, str] = True
    http_timeout: int = DEFAULT_HTTP_TIMEOUT

    @validator("url")
    def validate_url(cls, url: str) -> str:
        """Validates that the URL is a well-formed REST store URL.

        Args:
            url: The URL to be validated.

        Returns:
            The validated URL without trailing slashes.

        Raises:
            ValueError: If the URL is not a well-formed REST store URL.
        """
        url = url.rstrip("/")
        scheme = re.search("^([a-z0-9]+://)", url)
        if scheme is None or scheme.group() not in ("https://", "http://"):
            raise ValueError(
                "Invalid URL for REST store: {url}. Should be in the form "
                "https://hostname[:port] or http://hostname[:port]."
            )

        return url

    @validator("verify_ssl")
    def validate_verify_ssl(
        cls, verify_ssl: Union[bool, str]
    ) -> Union[bool, str]:
        """Validates that the verify_ssl field either points to a file or is a bool.

        Args:
            verify_ssl: The verify_ssl value to be validated.

        Returns:
            The validated verify_ssl value.
        """
        secret_folder = Path(
            GlobalConfiguration().local_stores_path,
            "certificates",
        )
        if isinstance(verify_ssl, bool) or verify_ssl.startswith(
            str(secret_folder)
        ):
            return verify_ssl

        if os.path.isfile(verify_ssl):
            with open(verify_ssl, "r") as f:
                verify_ssl = f.read()

        fileio.makedirs(str(secret_folder))
        file_path = Path(secret_folder, "ca_bundle.pem")
        with open(file_path, "w") as f:
            f.write(verify_ssl)
        file_path.chmod(0o600)
        verify_ssl = str(file_path)

        return verify_ssl

    def expand_certificates(self) -> None:
        """Expands the certificates in the verify_ssl field."""
        # Load the certificate values back into the configuration
        if isinstance(self.verify_ssl, str) and os.path.isfile(self.verify_ssl):
            with open(self.verify_ssl, "r") as f:
                self.verify_ssl = f.read()

    @classmethod
    def copy_configuration(
        cls,
        config: "StoreConfiguration",
        config_path: str,
        load_config_path: Optional[PurePath] = None,
    ) -> "StoreConfiguration":
        """Create a copy of the store config using a different configuration path.

        This method is used to create a copy of the store configuration that can
        be loaded using a different configuration path or in the context of a
        new environment, such as a container image.

        The configuration files accompanying the store configuration are also
        copied to the new configuration path (e.g. certificates etc.).

        Args:
            config: The store configuration to copy.
            config_path: new path where the configuration copy will be loaded
                from.
            load_config_path: absolute path that will be used to load the copied
                configuration. This can be set to a value different from
                `config_path` if the configuration copy will be loaded from
                a different environment, e.g. when the configuration is copied
                to a container image and loaded using a different absolute path.
                This will be reflected in the paths and URLs encoded in the
                copied configuration.

        Returns:
            A new store configuration object that reflects the new configuration
            path.
        """
        assert isinstance(config, RestZenStoreConfiguration)
        config = config.copy(deep=True)

        # Load the certificate values back into the configuration
        config.expand_certificates()
        return config

    class Config:
        """Pydantic configuration class."""

        # Don't validate attributes when assigning them. This is necessary
        # because the `verify_ssl` attribute can be expanded to the contents
        # of the certificate file.
        validate_assignment = False
        # Forbid extra attributes set in the class.
        extra = "forbid"


class RestZenStore(BaseZenStore):
    """Store implementation for accessing data from a REST API."""

    config: RestZenStoreConfiguration
    TYPE: ClassVar[StoreType] = StoreType.REST
    CONFIG_TYPE: ClassVar[Type[StoreConfiguration]] = RestZenStoreConfiguration
    _api_token: Optional[str] = None
    _session: Optional[requests.Session] = None

    def _initialize_database(self) -> None:
        """Initialize the database."""
        # don't do anything for a REST store

    # ====================================
    # ZenML Store interface implementation
    # ====================================

    # --------------------------------
    # Initialization and configuration
    # --------------------------------

    def _initialize(self) -> None:
        """Initialize the REST store."""
        # try to connect to the server to validate the configuration
        self.active_user

    def get_store_info(self) -> ServerModel:
        """Get information about the server.

        Returns:
            Information about the server.
        """
        body = self.get(INFO)
        return ServerModel.parse_obj(body)

    # ------------
    # TFX Metadata
    # ------------

    def get_metadata_config(
        self, expand_certs: bool = False
    ) -> "ConnectionConfig":
        """Get the TFX metadata config of this ZenStore.

        Args:
            expand_certs: Whether to expand the certificate paths in the
                connection config to their value.

        Raises:
            ValueError: if the server response is invalid.

        Returns:
            The TFX metadata config of this ZenStore.
        """
        from google.protobuf.json_format import Parse
        from ml_metadata.proto.metadata_store_pb2 import ConnectionConfig

        from zenml.zen_stores.sql_zen_store import SqlZenStoreConfiguration

        body = self.get(f"{METADATA_CONFIG}")
        if not isinstance(body, str):
            raise ValueError(
                f"Invalid response from server: {body}. Expected string."
            )
        metadata_config_pb = Parse(body, ConnectionConfig())

        # if the server returns a SQLite connection config, but the file is not
        # available locally, we need to replace the path with the local path of
        # the default local SQLite database
        if metadata_config_pb.HasField("sqlite") and not os.path.isfile(
            metadata_config_pb.sqlite.filename_uri
        ):
            message = (
                f"The ZenML server is using a SQLite database at "
                f"{metadata_config_pb.sqlite.filename_uri} that is not "
                f"available locally. Using the default local SQLite "
                f"database instead."
            )
            if not self.is_local_store():
                logger.warning(message)
            else:
                logger.debug(message)
            default_store_cfg = GlobalConfiguration().get_default_store()
            assert isinstance(default_store_cfg, SqlZenStoreConfiguration)
            return default_store_cfg.get_metadata_config()

        if not expand_certs:
            if metadata_config_pb.HasField(
                "mysql"
            ) and metadata_config_pb.mysql.HasField("ssl_options"):
                # Save the certificates in a secure location on disk
                secret_folder = Path(
                    GlobalConfiguration().local_stores_path,
                    "certificates",
                )
                for key in ["ssl_key", "ssl_ca", "ssl_cert"]:
                    if not metadata_config_pb.mysql.ssl_options.HasField(
                        key.lstrip("ssl_")
                    ):
                        continue
                    content = getattr(
                        metadata_config_pb.mysql.ssl_options, key.lstrip("ssl_")
                    )
                    if content and not os.path.isfile(content):
                        fileio.makedirs(str(secret_folder))
                        file_path = Path(secret_folder, f"{key}.pem")
                        with open(file_path, "w") as f:
                            f.write(content)
                        file_path.chmod(0o600)
                        setattr(
                            metadata_config_pb.mysql.ssl_options,
                            key.lstrip("ssl_"),
                            str(file_path),
                        )

        return metadata_config_pb

    # ------
    # Stacks
    # ------

    @track(AnalyticsEvent.REGISTERED_STACK)
    def create_stack(self, stack: StackRequestModel) -> StackModel:
        """Register a new stack.

        Args:
            stack: The stack to register.

        Returns:
            The registered stack.
        """
        return self._create_project_scoped_resource(
            resource=stack,
            route=STACKS,
            response_model=StackModel,
        )

    def get_stack(self, stack_id: UUID) -> StackModel:
        """Get a stack by its unique ID.

        Args:
            stack_id: The ID of the stack to get.

        Returns:
            The stack with the given ID.
        """
        return self._get_resource(
            resource_id=stack_id,
            route=STACKS,
            response_model=StackModel,
        )

    def list_stacks(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        component_id: Optional[UUID] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[StackModel]:
        """List all stacks matching the given filter criteria.

        Args:
            project_name_or_id: ID or name of the Project containing the stack
            user_name_or_id: Optionally filter stacks by their owner
            component_id: Optionally filter for stacks that contain the
                          component
            name: Optionally filter stacks by their name
            is_shared: Optionally filter out stacks by whether they are shared
                or not

        Returns:
            A list of all stacks matching the filter criteria.
        """
        filters = locals()
        filters.pop("self")
        return self._list_resources(
            route=STACKS,
            response_model=StackModel,
            **filters,
        )

    @track(AnalyticsEvent.UPDATED_STACK)
    def update_stack(
        self, stack_id: UUID, stack_update: StackRequestModel
    ) -> StackModel:
        """Update a stack.


        Args:
            stack_id: The ID of the stack update.
            stack_update: The update request on the stack.

        Returns:
            The updated stack.

        Raises:
            KeyError: if the stack doesn't exist.
        """
        return self._update_resource(
            resource_id=stack_id,
            resource_update=stack_update,
            route=STACKS,
            response_model=StackModel,
        )

    @track(AnalyticsEvent.DELETED_STACK)
    def delete_stack(self, stack_id: UUID) -> None:
        """Delete a stack.

        Args:
            stack_id: The ID of the stack to delete.
        """
        self._delete_resource(
            resource_id=stack_id,
            route=STACKS,
        )

    # ----------------
    # Stack components
    # ----------------

    @track(AnalyticsEvent.REGISTERED_STACK_COMPONENT)
    def create_stack_component(
        self,
        component: ComponentModel,
    ) -> ComponentModel:
        """Create a stack component.

        Args:
            component: The stack component to create.

        Returns:
            The created stack component.
        """
        return self._create_project_scoped_resource(
            resource=component,
            route=STACK_COMPONENTS,
            response_model=ComponentModel,
        )

    def get_stack_component(self, component_id: UUID) -> ComponentModel:
        """Get a stack component by ID.

        Args:
            component_id: The ID of the stack component to get.

        Returns:
            The stack component.
        """
        return self._get_resource(
            resource_id=component_id,
            route=STACK_COMPONENTS,
            response_model=ComponentModel,
        )

    def list_stack_components(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        type: Optional[str] = None,
        flavor_name: Optional[str] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[ComponentModel]:
        """List all stack components matching the given filter criteria.

        Args:
            project_name_or_id: The ID or name of the Project to which the stack
                components belong
            type: Optionally filter by type of stack component
            flavor_name: Optionally filter by flavor
            user_name_or_id: Optionally filter stack components by the owner
            name: Optionally filter stack component by name
            is_shared: Optionally filter out stack component by whether they are
                shared or not

        Returns:
            A list of all stack components matching the filter criteria.
        """
        filters = locals()
        filters.pop("self")
        return self._list_resources(
            route=STACK_COMPONENTS,
            response_model=ComponentModel,
            **filters,
        )

    @track(AnalyticsEvent.UPDATED_STACK_COMPONENT)
    def update_stack_component(
        self,
        component_id: UUID,
        component_update: ComponentRequestModel,
    ) -> ComponentModel:
        """Update an existing stack component.

        Args:
            component_id: The ID of the stack component to update.
            component_update: The update to be applied to the stack component.

        Returns:
            The updated stack component.
        """
        return self._update_resource(
            resource_id=component_id,
            resource_update=component_update,
            route=STACK_COMPONENTS,
            response_model=ComponentModel,
        )

    @track(AnalyticsEvent.DELETED_STACK_COMPONENT)
    def delete_stack_component(self, component_id: UUID) -> None:
        """Delete a stack component.

        Args:
            component_id: The ID of the stack component to delete.
        """
        self._delete_resource(
            resource_id=component_id,
            route=STACK_COMPONENTS,
        )

    # -----------------------
    # Stack component flavors
    # -----------------------

    @track(AnalyticsEvent.CREATED_FLAVOR)
    def create_flavor(self, flavor: FlavorRequestModel) -> FlavorModel:
        """Creates a new stack component flavor.

        Args:
            flavor: The stack component flavor to create.

        Returns:
            The newly created flavor.
        """
        return self._create_project_scoped_resource(
            resource=flavor,
            route=FLAVORS,
            response_model=FlavorModel,
        )

    def get_flavor(self, flavor_id: UUID) -> FlavorModel:
        """Get a stack component flavor by ID.

        Args:
            flavor_id: The ID of the stack component flavor to get.

        Returns:
            The stack component flavor.
        """
        return self._get_resource(
            resource_id=flavor_id,
            route=FLAVORS,
            response_model=FlavorModel,
        )

    def list_flavors(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        component_type: Optional[StackComponentType] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[FlavorModel]:
        """List all stack component flavors matching the given filter criteria.

        Args:
            project_name_or_id: Optionally filter by the Project to which the
                component flavors belong
            user_name_or_id: Optionally filter by the owner
            component_type: Optionally filter by type of stack component
            name: Optionally filter flavors by name
            is_shared: Optionally filter out flavors by whether they are
                shared or not

        Returns:
            List of all the stack component flavors matching the given criteria.
        """
        filters = locals()
        filters.pop("self")
        return self._list_resources(
            route=FLAVORS,
            response_model=FlavorModel,
            **filters,
        )

    @track(AnalyticsEvent.DELETED_FLAVOR)
    def delete_flavor(self, flavor_id: UUID) -> None:
        """Delete a stack component flavor.

        Args:
            flavor_id: The ID of the stack component flavor to delete.
        """
        self._delete_resource(
            resource_id=flavor_id,
            route=FLAVORS,
        )

    # -----
    # Users
    # -----

    @property
    def active_user_name(self) -> str:
        """Gets the active username.

        Returns:
            The active username.
        """
        return self.config.username

    @track(AnalyticsEvent.CREATED_USER)
    def create_user(self, user: UserRequestModel) -> UserModel:
        """Creates a new user.

        Args:
            user: User to be created.

        Returns:
            The newly created user.
        """
        return self._create_resource(
            resource=user,
            route=USERS,
            response_model=UserModel,
        )

    # TODO: Should this be name or id?
    def get_user(self, user_name_or_id: Union[str, UUID]) -> UserModel:
        """Gets a specific user.

        Args:
            user_name_or_id: The name or ID of the user to get.

        Returns:
            The requested user, if it was found.
        """
        return self._get_resource(
            resource_id=user_name_or_id,
            route=USERS,
            response_model=UserModel,
        )

    def list_users(self) -> List[UserModel]:
        """List all users.

        Returns:
            A list of all users.
        """
        filters = locals()
        filters.pop("self")
        return self._list_resources(
            route=USERS,
            response_model=UserModel,
            **filters,
        )

    @track(AnalyticsEvent.UPDATED_USER)
    def update_user(
        self, user_id: UUID, user_update: UserRequestModel
    ) -> UserModel:
        """Updates an existing user.

        Args:
            user_id: The id of the user to update.
            user_update: The update to be applied to the user.

        Returns:
            The updated user.
        """
        return self._update_resource(
            resource_id=user_id,
            resource_update=user_update,
            route=USERS,
            response_model=UserModel,
        )

    @track(AnalyticsEvent.DELETED_USER)
    def delete_user(self, user_name_or_id: Union[str, UUID]) -> None:
        """Deletes a user.

        Args:
            user_name_or_id: The name or ID of the user to delete.
        """
        self._delete_resource(
            resource_id=user_name_or_id,
            route=USERS,
        )

    def user_email_opt_in(
        self,
        user_name_or_id: Union[str, UUID],
        user_opt_in_response: bool,
        email: Optional[str] = None,
    ) -> UserModel:
        """Persist user response to the email prompt.

        Args:
            user_name_or_id: The name or the ID of the user.
            user_opt_in_response: Whether this email should be associated
                with the user id in the telemetry
            email: The users email

        Returns:
            The updated user.
        """
        request = EmailOptInModel(
            email=email, email_opted_in=user_opt_in_response
        )
        route = f"{USERS}/{str(user_name_or_id)}{EMAIL_ANALYTICS}"

        response_body = self.put(route, body=request)
        user = UserModel.parse_obj(response_body)
        return user

    # -----
    # Teams
    # -----

    @track(AnalyticsEvent.CREATED_TEAM)
    def create_team(self, team: TeamRequestModel) -> TeamModel:
        """Creates a new team.

        Args:
            team: The team model to create.

        Returns:
            The newly created team.
        """
        return self._create_resource(
            resource=team,
            route=TEAMS,
            response_model=TeamModel,
        )

    def get_team(self, team_name_or_id: Union[str, UUID]) -> TeamModel:
        """Gets a specific team.

        Args:
            team_name_or_id: Name or ID of the team to get.

        Returns:
            The requested team.
        """
        return self._get_resource(
            resource_id=team_name_or_id,
            route=TEAMS,
            response_model=TeamModel,
        )

    def list_teams(self) -> List[TeamModel]:
        """List all teams.

        Returns:
            A list of all teams.
        """
        filters = locals()
        filters.pop("self")
        return self._list_resources(
            route=TEAMS,
            response_model=TeamModel,
            **filters,
        )

    @track(AnalyticsEvent.UPDATED_TEAM)
    def update_team(
        self, team_id: UUID, team_update: TeamRequestModel
    ) -> TeamModel:
        """Update an existing team.

        Args:
            team_id: The ID of the team to be updated.
            team_update: The update to be applied to the team.


        Returns:
            The updated team.
        """
        return self._update_resource(
            resource_id=team_id,
            resource_update=team_update,
            route=TEAMS,
            response_model=TeamModel,
        )

    @track(AnalyticsEvent.DELETED_TEAM)
    def delete_team(self, team_name_or_id: Union[str, UUID]) -> None:
        """Deletes a team.

        Args:
            team_name_or_id: Name or ID of the team to delete.
        """
        self._delete_resource(
            resource_id=team_name_or_id,
            route=TEAMS,
        )

    # ---------------
    # Team membership
    # ---------------

    def get_users_for_team(
        self, team_name_or_id: Union[str, UUID]
    ) -> List[UserModel]:
        """Fetches all users of a team.

        Args:
            team_name_or_id: The name or ID of the team for which to get users.
        """

    def get_teams_for_user(
        self, user_name_or_id: Union[str, UUID]
    ) -> List[TeamModel]:
        """Fetches all teams for a user.

        Args:
            user_name_or_id: The name or ID of the user for which to get all
                teams.
        """

    def add_user_to_team(
        self,
        user_name_or_id: Union[str, UUID],
        team_name_or_id: Union[str, UUID],
    ) -> None:
        """Adds a user to a team.

        Args:
            user_name_or_id: Name or ID of the user to add to the team.
            team_name_or_id: Name or ID of the team to which to add the user to.
        """

    def remove_user_from_team(
        self,
        user_name_or_id: Union[str, UUID],
        team_name_or_id: Union[str, UUID],
    ) -> None:
        """Removes a user from a team.

        Args:
            user_name_or_id: Name or ID of the user to remove from the team.
            team_name_or_id: Name or ID of the team from which to remove the user.
        """

    # -----
    # Roles
    # -----

    @track(AnalyticsEvent.CREATED_ROLE)
    def create_role(self, role: RoleRequestModel) -> RoleModel:
        """Creates a new role.

        Args:
            role: The role model to create.

        Returns:
            The newly created role.
        """
        return self._create_resource(
            resource=role,
            route=ROLES,
            response_model=RoleModel,
        )

    # TODO: Should it be name or id or just id?
    def get_role(self, role_name_or_id: Union[str, UUID]) -> RoleModel:
        """Gets a specific role.

        Args:
            role_name_or_id: Name or ID of the role to get.

        Returns:
            The requested role.
        """
        return self._get_resource(
            resource_id=role_name_or_id,
            route=ROLES,
            response_model=RoleModel,
        )

    def list_roles(self) -> List[RoleModel]:
        """List all roles.

        Returns:
            A list of all roles.
        """
        filters = locals()
        filters.pop("self")
        return self._list_resources(
            route=ROLES,
            response_model=RoleModel,
            **filters,
        )

    @track(AnalyticsEvent.UPDATED_ROLE)
    def update_role(
        self, role_id: UUID, role_update: RoleRequestModel
    ) -> RoleModel:
        """Update an existing role.

        Args:
            role_id: The ID of the role to be updated.
            role_update: The update to be applied to the role.

        Returns:
            The updated role.
        """
        return self._update_resource(
            resource_id=role_id,
            resource_update=role_update,
            route=ROLES,
            response_model=RoleModel,
        )

    @track(AnalyticsEvent.DELETED_ROLE)
    def delete_role(self, role_name_or_id: Union[str, UUID]) -> None:
        """Deletes a role.

        Args:
            role_name_or_id: Name or ID of the role to delete.
        """
        self._delete_resource(
            resource_id=role_name_or_id,
            route=ROLES,
        )

    # ----------------
    # Role assignments
    # ----------------

    def list_role_assignments(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        team_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> List[RoleAssignmentModel]:
        """List all role assignments.

        Args:
            project_name_or_id: If provided, only list assignments for the given
                project
            team_name_or_id: If provided, only list assignments for the given
                team
            user_name_or_id: If provided, only list assignments for the given
                user

        Returns:
            A list of all role assignments.
        """
        roles: List[RoleAssignmentModel] = []
        if user_name_or_id:
            roles.extend(
                self._list_resources(
                    route=f"{USERS}/{user_name_or_id}{ROLES}",
                    resource_model=RoleAssignmentModel,
                    project_name_or_id=project_name_or_id,
                )
            )
        if team_name_or_id:
            roles.extend(
                self._list_resources(
                    route=f"{TEAMS}/{team_name_or_id}{ROLES}",
                    resource_model=RoleAssignmentModel,
                    project_name_or_id=project_name_or_id,
                )
            )
        return roles

    def assign_role(
        self,
        role_name_or_id: Union[str, UUID],
        user_or_team_name_or_id: Union[str, UUID],
        project_name_or_id: Optional[Union[str, UUID]] = None,
        is_user: bool = True,
    ) -> None:
        """Assigns a role to a user or team, scoped to a specific project.

        Args:
            role_name_or_id: Name or ID of the role to assign.
            user_or_team_name_or_id: Name or ID of the user or team to which to
                assign the role.
            is_user: Whether `user_or_team_id` refers to a user or a team.
            project_name_or_id: Optional Name or ID of a project in which to
                assign the role. If this is not provided, the role will be
                assigned globally.
        """

    def revoke_role(
        self,
        role_name_or_id: Union[str, UUID],
        user_or_team_name_or_id: Union[str, UUID],
        is_user: bool = True,
        project_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> None:
        """Revokes a role from a user or team for a given project.

        Args:
            role_name_or_id: ID of the role to revoke.
            user_or_team_name_or_id: Name or ID of the user or team from which
                to revoke the role.
            is_user: Whether `user_or_team_id` refers to a user or a team.
            project_name_or_id: Optional ID of a project in which to revoke
                the role. If this is not provided, the role will be revoked
                globally.
        """

    # --------
    # Projects
    # --------

    @track(AnalyticsEvent.CREATED_PROJECT)
    def create_project(self, project: ProjectRequestModel) -> ProjectModel:
        """Creates a new project.

        Args:
            project: The project to create.

        Returns:
            The newly created project.
        """
        return self._create_resource(
            resource=project,
            route=PROJECTS,
            response_model=ProjectModel,
        )

    # TODO: Should this be just the id?
    def get_project(self, project_name_or_id: Union[UUID, str]) -> ProjectModel:
        """Get an existing project by name or ID.

        Args:
            project_name_or_id: Name or ID of the project to get.

        Returns:
            The requested project.
        """
        return self._get_resource(
            resource_id=project_name_or_id,
            route=PROJECTS,
            response_model=ProjectModel,
        )

    def list_projects(self) -> List[ProjectModel]:
        """List all projects.

        Returns:
            A list of all projects.
        """
        filters = locals()
        filters.pop("self")
        return self._list_resources(
            route=PROJECTS,
            response_model=ProjectModel,
            **filters,
        )

    @track(AnalyticsEvent.UPDATED_PROJECT)
    def update_project(
        self, project_id: UUID, project_update: ProjectRequestModel
    ) -> ProjectModel:
        """Update an existing project.

        Args:
            project_id: The ID of the project to be updated.
            project_update: The update to be applied to the project.

        Returns:
            The updated project.
        """
        return self._update_resource(
            resource_id=project_id,
            resource_update=project_update,
            route=PROJECTS,
            response_model=ProjectModel,
        )

    @track(AnalyticsEvent.DELETED_PROJECT)
    def delete_project(self, project_name_or_id: Union[str, UUID]) -> None:
        """Deletes a project.

        Args:
            project_name_or_id: Name or ID of the project to delete.
        """
        self._delete_resource(
            resource_id=project_name_or_id,
            route=PROJECTS,
        )

    # ---------
    # Pipelines
    # ---------

    @track(AnalyticsEvent.CREATE_PIPELINE)
    def create_pipeline(self, pipeline: PipelineRequestModel) -> PipelineModel:
        """Creates a new pipeline in a project.

        Args:
            pipeline: The pipeline to create.

        Returns:
            The newly created pipeline.
        """
        return self._create_project_scoped_resource(
            resource=pipeline,
            route=PIPELINES,
            response_model=PipelineModel,
        )

    def get_pipeline(self, pipeline_id: UUID) -> PipelineModel:
        """Get a pipeline with a given ID.

        Args:
            pipeline_id: ID of the pipeline.

        Returns:
            The pipeline.
        """
        return self._get_resource(
            resource_id=pipeline_id,
            route=PIPELINES,
            response_model=PipelineModel,
        )

    def list_pipelines(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        name: Optional[str] = None,
    ) -> List[PipelineModel]:
        """List all pipelines in the project.

        Args:
            project_name_or_id: If provided, only list pipelines in this
            project.
            user_name_or_id: If provided, only list pipelines from this user.
            name: If provided, only list pipelines with this name.

        Returns:
            A list of pipelines.
        """
        filters = locals()
        filters.pop("self")
        return self._list_resources(
            route=PIPELINES,
            response_model=PipelineModel,
            **filters,
        )

    @track(AnalyticsEvent.UPDATE_PIPELINE)
    def update_pipeline(
        self, pipeline_id: UUID, pipeline_update: PipelineModel
    ) -> PipelineModel:
        """Updates a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to be updated.
            pipeline_update: The update to be applied.

        Returns:
            The updated pipeline.
        """
        return self._update_resource(
            resource_id=pipeline_id,
            resource_update=pipeline_update,
            route=PIPELINES,
            response_model=PipelineModel,
        )

    @track(AnalyticsEvent.DELETE_PIPELINE)
    def delete_pipeline(self, pipeline_id: UUID) -> None:
        """Deletes a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to delete.
        """
        self._delete_resource(
            resource_id=pipeline_id,
            route=PIPELINES,
        )

    # --------------
    # Pipeline runs
    # --------------

    def get_run(self, run_id: UUID) -> PipelineRunModel:
        """Gets a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            The pipeline run.
        """
        return self._get_resource(
            resource_id=run_id,
            route=RUNS,
            response_model=PipelineRunModel,
        )

    def list_runs(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        stack_id: Optional[UUID] = None,
        component_id: Optional[UUID] = None,
        run_name: Optional[str] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        pipeline_id: Optional[UUID] = None,
        unlisted: bool = False,
    ) -> List[PipelineRunModel]:
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
        filters = locals()
        filters.pop("self")
        return self._list_resources(
            route=RUNS,
            response_model=PipelineRunModel,
            **filters,
        )

    def get_run_status(self, run_id: UUID) -> ExecutionStatus:
        """Gets the execution status of a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get the status for.

        Returns:
            The execution status of the pipeline run.
        """
        body = self.get(f"{RUNS}/{str(run_id)}{STATUS}")
        return ExecutionStatus(body)

    # ------------------
    # Pipeline run steps
    # ------------------

    def get_run_step(self, step_id: UUID) -> StepRunModel:
        """Get a step by ID.

        Args:
            step_id: The ID of the step to get.

        Returns:
            The step.
        """
        return self._get_resource(
            resource_id=step_id,
            route=STEPS,
            response_model=StepRunModel,
        )

    def get_run_step_outputs(self, step_id: UUID) -> Dict[str, ArtifactModel]:
        """Get a list of outputs for a specific step.

        Args:
            step_id: The id of the step to get outputs for.

        Returns:
            A dict mapping artifact names to the output artifacts for the step.

        Raises:
            ValueError: if the response from the API is not a dict.
        """
        body = self.get(f"{STEPS}/{str(step_id)}{OUTPUTS}")
        if not isinstance(body, dict):
            raise ValueError(
                f"Bad API Response. Expected dict, got {type(body)}"
            )
        return {
            name: ArtifactModel.parse_obj(entry) for name, entry in body.items()
        }

    def get_run_step_inputs(self, step_id: UUID) -> Dict[str, ArtifactModel]:
        """Get a list of inputs for a specific step.

        Args:
            step_id: The id of the step to get inputs for.

        Returns:
            A dict mapping artifact names to the input artifacts for the step.

        Raises:
            ValueError: if the response from the API is not a dict.
        """
        body = self.get(f"{STEPS}/{str(step_id)}{INPUTS}")
        if not isinstance(body, dict):
            raise ValueError(
                f"Bad API Response. Expected dict, got {type(body)}"
            )
        return {
            name: ArtifactModel.parse_obj(entry) for name, entry in body.items()
        }

    def get_run_step_status(self, step_id: UUID) -> ExecutionStatus:
        """Gets the execution status of a single step.

        Args:
            step_id: The ID of the step to get the status for.

        Returns:
            The execution status of the step.
        """
        body = self.get(f"{STEPS}/{str(step_id)}{STATUS}")
        return ExecutionStatus(body)

    def list_run_steps(self, run_id: UUID) -> List[StepRunModel]:
        """Gets all steps in a pipeline run.

        Args:
            run_id: The ID of the pipeline run for which to list runs.

        Returns:
            A mapping from step names to step models for all steps in the run.
        """
        return self._list_resources(
            route=f"{RUNS}/{str(run_id)}{STEPS}",
            response_model=StepRunModel,
        )

    def list_artifacts(
        self, artifact_uri: Optional[str] = None
    ) -> List[ArtifactModel]:
        """Lists all artifacts.

        Args:
            artifact_uri: If specified, only artifacts with the given URI will
                be returned.

        Returns:
            A list of all artifacts.
        """
        filters = locals()
        filters.pop("self")
        return self._list_resources(
            route=ARTIFACTS,
            response_model=ArtifactModel,
            **filters,
        )

    # =======================
    # Internal helper methods
    # =======================

    def _get_auth_token(self) -> str:
        """Get the authentication token for the REST store.

        Returns:
            The authentication token.

        Raises:
            ValueError: if the response from the server isn't in the right format.
        """
        if self._api_token is None:
            response = self._handle_response(
                requests.post(
                    self.url + API + VERSION_1 + LOGIN,
                    data={
                        "username": self.config.username,
                        "password": self.config.password,
                    },
                    verify=self.config.verify_ssl,
                    timeout=self.config.http_timeout,
                )
            )
            if not isinstance(response, dict) or "access_token" not in response:
                raise ValueError(
                    f"Bad API Response. Expected access token dict, got "
                    f"{type(response)}"
                )
            self._api_token = response["access_token"]
        return self._api_token

    @property
    def session(self) -> requests.Session:
        """Authenticate to the ZenML server.

        Returns:
            A requests session with the authentication token.
        """
        if self._session is None:
            if self.config.verify_ssl is False:
                urllib3.disable_warnings(
                    urllib3.exceptions.InsecureRequestWarning
                )

            self._session = requests.Session()
            self._session.verify = self.config.verify_ssl
            token = self._get_auth_token()
            self._session.headers.update({"Authorization": "Bearer " + token})
            logger.debug("Authenticated to ZenML server.")
        return self._session

    @staticmethod
    def _handle_response(response: requests.Response) -> Json:
        """Handle API response, translating http status codes to Exception.

        Args:
            response: The response to handle.

        Returns:
            The parsed response.

        Raises:
            DoesNotExistException: If the response indicates that the
                requested entity does not exist.
            EntityExistsError: If the response indicates that the requested
                entity already exists.
            AuthorizationException: If the response indicates that the request
                is not authorized.
            KeyError: If the response indicates that the requested entity
                does not exist.
            RuntimeError: If the response indicates that the requested entity
                does not exist.
            StackComponentExistsError: If the response indicates that the
                requested entity already exists.
            StackExistsError: If the response indicates that the requested
                entity already exists.
            ValueError: If the response indicates that the requested entity
                does not exist.
        """
        if 200 <= response.status_code < 300:
            try:
                payload: Json = response.json()
                return payload
            except requests.exceptions.JSONDecodeError:
                raise ValueError(
                    "Bad response from API. Expected json, got\n"
                    f"{response.text}"
                )
        elif response.status_code == 401:
            raise AuthorizationException(
                f"{response.status_code} Client Error: Unauthorized request to "
                f"URL {response.url}: {response.json().get('detail')}"
            )
        elif response.status_code == 404:
            if "KeyError" in response.text:
                raise KeyError(
                    response.json().get("detail", (response.text,))[1]
                )
            elif "DoesNotExistException" in response.text:
                message = ": ".join(
                    response.json().get("detail", (response.text,))
                )
                raise DoesNotExistException(message)
            raise DoesNotExistException("Endpoint does not exist.")
        elif response.status_code == 409:
            if "StackComponentExistsError" in response.text:
                raise StackComponentExistsError(
                    message=": ".join(
                        response.json().get("detail", (response.text,))
                    )
                )
            elif "StackExistsError" in response.text:
                raise StackExistsError(
                    message=": ".join(
                        response.json().get("detail", (response.text,))
                    )
                )
            elif "EntityExistsError" in response.text:
                raise EntityExistsError(
                    message=": ".join(
                        response.json().get("detail", (response.text,))
                    )
                )
            else:
                raise ValueError(
                    ": ".join(response.json().get("detail", (response.text,)))
                )
        elif response.status_code == 422:
            raise RuntimeError(
                ": ".join(response.json().get("detail", (response.text,)))
            )
        elif response.status_code == 500:
            raise RuntimeError(response.text)
        else:
            raise RuntimeError(
                "Error retrieving from API. Got response "
                f"{response.status_code} with body:\n{response.text}"
            )

    def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Json:
        """Make a request to the REST API.

        Args:
            method: The HTTP method to use.
            url: The URL to request.
            params: The query parameters to pass to the endpoint.
            kwargs: Additional keyword arguments to pass to the request.

        Returns:
            The parsed response.
        """
        params = {k: str(v) for k, v in params.items()} if params else {}
        try:
            return self._handle_response(
                self.session.request(
                    method,
                    url,
                    params=params,
                    verify=self.config.verify_ssl,
                    timeout=self.config.http_timeout,
                    **kwargs,
                )
            )
        except AuthorizationException:
            # The authentication token could have expired; refresh it and try
            # again
            self._session = None
            return self._handle_response(
                self.session.request(
                    method,
                    url,
                    params=params,
                    verify=self.config.verify_ssl,
                    timeout=self.config.http_timeout,
                    **kwargs,
                )
            )

    def get(
        self, path: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> Json:
        """Make a GET request to the given endpoint path.

        Args:
            path: The path to the endpoint.
            params: The query parameters to pass to the endpoint.
            kwargs: Additional keyword arguments to pass to the request.

        Returns:
            The response body.
        """
        logger.debug(f"Sending GET request to {path}...")
        return self._request(
            "GET", self.url + API + VERSION_1 + path, params=params, **kwargs
        )

    def delete(
        self, path: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> Json:
        """Make a DELETE request to the given endpoint path.

        Args:
            path: The path to the endpoint.
            params: The query parameters to pass to the endpoint.
            kwargs: Additional keyword arguments to pass to the request.

        Returns:
            The response body.
        """
        logger.debug(f"Sending DELETE request to {path}...")
        return self._request(
            "DELETE", self.url + API + VERSION_1 + path, params=params, **kwargs
        )

    def post(
        self,
        path: str,
        body: BaseModel,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Json:
        """Make a POST request to the given endpoint path.

        Args:
            path: The path to the endpoint.
            body: The body to send.
            params: The query parameters to pass to the endpoint.
            kwargs: Additional keyword arguments to pass to the request.

        Returns:
            The response body.
        """
        logger.debug(f"Sending POST request to {path}...")
        return self._request(
            "POST",
            self.url + API + VERSION_1 + path,
            data=body.json(),
            params=params,
            **kwargs,
        )

    def put(
        self,
        path: str,
        body: BaseModel,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Json:
        """Make a PUT request to the given endpoint path.

        Args:
            path: The path to the endpoint.
            body: The body to send.
            params: The query parameters to pass to the endpoint.
            kwargs: Additional keyword arguments to pass to the request.

        Returns:
            The response body.
        """
        logger.debug(f"Sending PUT request to {path}...")
        return self._request(
            "PUT",
            self.url + API + VERSION_1 + path,
            data=body.json(),
            params=params,
            **kwargs,
        )

    def _create_resource(
        self,
        resource: BaseRequestModel,
        response_model: Type[AnyResponseModel],
        route: str,
    ) -> AnyResponseModel:
        """Create a new resource.

        Args:
            resource: The resource to create.
            route: The resource REST API route to use.
            response_model: Optional model to use to deserialize the response
                body. If not provided, the resource class itself will be used.

        Returns:
            The created resource.
        """
        response_body = self.post(f"{route}", body=resource)
        return response_model.parse_obj(response_body)

    def _create_project_scoped_resource(
        self,
        resource: ProjectScopedRequestModel,
        response_model: Type[AnyProjestResponseModel],
        route: str,
    ) -> AnyProjestResponseModel:
        """Create a new project scoped resource.

        Args:
            resource: The resource to create.
            route: The resource REST API route to use.
            response_model: Optional model to use to deserialize the response
                body. If not provided, the resource class itself will be used.

        Returns:
            The created resource.
        """
        return self._create_resource(
            resource=resource,
            response_model=response_model,
            route=f"{PROJECTS}/{str(resource.project)}{route}",
        )

    def _get_resource(
        self,
        resource_id: Union[str, UUID],
        route: str,
        response_model: Type[AnyResponseModel],
    ) -> AnyResponseModel:
        """Retrieve a single resource.

        Args:
            resource_id: The ID of the resource to retrieve.
            route: The resource REST API route to use.
            response_model: Model to use to serialize the response body.

        Returns:
            The retrieved resource.
        """
        body = self.get(f"{route}/{str(resource_id)}")
        return response_model.parse_obj(body)

    def _list_resources(
        self,
        route: str,
        response_model: Type[AnyResponseModel],
        **filters: Any,
    ) -> List[AnyResponseModel]:
        """Retrieve a list of resources filtered by some criteria.

        Args:
            route: The resource REST API route to use.
            resource_model: Model to use to serialize the response body.
            filters: Filter parameters to use in the query.

        Returns:
            List of retrieved resources matching the filter criteria.

        Raises:
            ValueError: If the value returned by the server is not a list.
        """
        # leave out filter params that are not supplied
        params = dict(filter(lambda x: x[1] is not None, filters.items()))
        body = self.get(f"{route}", params=params)
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [response_model.parse_obj(entry) for entry in body]

    def _update_resource(
        self,
        resource_id: UUID,
        resource_update: BaseRequestModel,
        response_model: Type[AnyResponseModel],
        route: str,
    ) -> AnyResponseModel:
        """Update an existing resource.

        Args:
            resource_id: The id of the resource to update.
            resource_update: The resource update.
            route: The resource REST API route to use.
            response_model: Optional model to use to deserialize the response
                body. If not provided, the resource class itself will be used.

        Returns:
            The updated resource.
        """
        response_body = self.put(
            f"{route}/{str(resource_id)}", body=resource_update
        )

        return response_model.parse_obj(response_body)

    def _delete_resource(
        self, resource_id: Union[str, UUID], route: str
    ) -> None:
        """Delete a resource.

        Args:
            resource_id: The ID of the resource to delete.
            route: The resource REST API route to use.
        """
        self.delete(f"{route}/{str(resource_id)}")

    def _sync_runs(self) -> None:
        """Syncs runs from MLMD.

        Raises:
            NotImplementedError: This internal method may not be called on a
                `RestZenStore`.
        """
        raise NotImplementedError
