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
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from urllib.parse import urlparse
from uuid import UUID

import requests
import urllib3
from pydantic import BaseModel, root_validator, validator

import zenml
from zenml.analytics import source_context
from zenml.config.global_config import GlobalConfiguration
from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.config.store_config import StoreConfiguration
from zenml.constants import (
    API,
    ARTIFACTS,
    CODE_REPOSITORIES,
    CURRENT_USER,
    DISABLE_CLIENT_SERVER_MISMATCH_WARNING,
    ENV_ZENML_DISABLE_CLIENT_SERVER_MISMATCH_WARNING,
    FLAVORS,
    GET_OR_CREATE,
    INFO,
    LOGIN,
    PIPELINE_BUILDS,
    PIPELINE_DEPLOYMENTS,
    PIPELINES,
    ROLES,
    RUN_METADATA,
    RUNS,
    SCHEDULES,
    SERVICE_CONNECTOR_CLIENT,
    SERVICE_CONNECTOR_RESOURCES,
    SERVICE_CONNECTOR_TYPES,
    SERVICE_CONNECTOR_VERIFY,
    SERVICE_CONNECTORS,
    STACK_COMPONENTS,
    STACKS,
    STEPS,
    TEAM_ROLE_ASSIGNMENTS,
    TEAMS,
    USER_ROLE_ASSIGNMENTS,
    USERS,
    VERSION_1,
    WORKSPACES,
)
from zenml.enums import SecretsStoreType, StoreType
from zenml.exceptions import (
    AuthorizationException,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.models import (
    ArtifactFilterModel,
    ArtifactRequestModel,
    ArtifactResponseModel,
    BaseFilterModel,
    CodeRepositoryFilterModel,
    CodeRepositoryRequestModel,
    CodeRepositoryResponseModel,
    CodeRepositoryUpdateModel,
    ComponentFilterModel,
    ComponentRequestModel,
    ComponentResponseModel,
    ComponentUpdateModel,
    FlavorFilterModel,
    FlavorRequestModel,
    FlavorResponseModel,
    FlavorUpdateModel,
    PipelineBuildFilterModel,
    PipelineBuildRequestModel,
    PipelineBuildResponseModel,
    PipelineDeploymentFilterModel,
    PipelineDeploymentRequestModel,
    PipelineDeploymentResponseModel,
    PipelineFilterModel,
    PipelineRequestModel,
    PipelineResponseModel,
    PipelineRunFilterModel,
    PipelineRunRequestModel,
    PipelineRunResponseModel,
    PipelineRunUpdateModel,
    PipelineUpdateModel,
    RoleFilterModel,
    RoleRequestModel,
    RoleResponseModel,
    RoleUpdateModel,
    RunMetadataRequestModel,
    RunMetadataResponseModel,
    ScheduleRequestModel,
    ScheduleResponseModel,
    ScheduleUpdateModel,
    ServiceConnectorFilterModel,
    ServiceConnectorRequestModel,
    ServiceConnectorResourcesModel,
    ServiceConnectorResponseModel,
    ServiceConnectorTypeModel,
    ServiceConnectorUpdateModel,
    StackFilterModel,
    StackRequestModel,
    StackResponseModel,
    StackUpdateModel,
    StepRunFilterModel,
    StepRunRequestModel,
    StepRunResponseModel,
    StepRunUpdateModel,
    TeamRequestModel,
    TeamResponseModel,
    TeamRoleAssignmentFilterModel,
    TeamRoleAssignmentRequestModel,
    TeamRoleAssignmentResponseModel,
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
from zenml.models.base_models import (
    BaseRequestModel,
    BaseResponseModel,
    WorkspaceScopedRequestModel,
)
from zenml.models.page_model import Page
from zenml.models.run_metadata_models import RunMetadataFilterModel
from zenml.models.schedule_model import ScheduleFilterModel
from zenml.models.server_models import ServerModel
from zenml.models.team_models import TeamFilterModel, TeamUpdateModel
from zenml.service_connectors.service_connector_registry import (
    service_connector_registry,
)
from zenml.utils.networking_utils import (
    replace_localhost_with_internal_hostname,
)
from zenml.zen_server.exceptions import exception_from_response
from zenml.zen_stores.base_zen_store import BaseZenStore
from zenml.zen_stores.secrets_stores.rest_secrets_store import (
    RestSecretsStoreConfiguration,
)

logger = get_logger(__name__)

# type alias for possible json payloads (the Anys are recursive Json instances)
Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

AnyRequestModel = TypeVar("AnyRequestModel", bound=BaseRequestModel)
AnyResponseModel = TypeVar("AnyResponseModel", bound=BaseResponseModel)


DEFAULT_HTTP_TIMEOUT = 30


class RestZenStoreConfiguration(StoreConfiguration):
    """REST ZenML store configuration.

    Attributes:
        type: The type of the store.
        secrets_store: The configuration of the secrets store to use.
            This defaults to a REST secrets store that extends the REST ZenML
            store.
        username: The username to use to connect to the Zen server.
        password: The password to use to connect to the Zen server.
        verify_ssl: Either a boolean, in which case it controls whether we
            verify the server's TLS certificate, or a string, in which case it
            must be a path to a CA bundle to use or the CA bundle value itself.
        http_timeout: The timeout to use for all requests.

    """

    type: StoreType = StoreType.REST

    secrets_store: Optional[SecretsStoreConfiguration] = None

    username: Optional[str] = None
    password: Optional[str] = None
    api_token: Optional[str] = None
    verify_ssl: Union[bool, str] = True
    http_timeout: int = DEFAULT_HTTP_TIMEOUT

    @validator("secrets_store")
    def validate_secrets_store(
        cls, secrets_store: Optional[SecretsStoreConfiguration]
    ) -> SecretsStoreConfiguration:
        """Ensures that the secrets store uses an associated REST secrets store.

        Args:
            secrets_store: The secrets store config to be validated.

        Returns:
            The validated secrets store config.

        Raises:
            ValueError: If the secrets store is not of type REST.
        """
        if secrets_store is None:
            secrets_store = RestSecretsStoreConfiguration()
        elif secrets_store.type != SecretsStoreType.REST:
            raise ValueError(
                "The secrets store associated with a REST zen store must be "
                f"of type REST, but is of type {secrets_store.type}."
            )

        return secrets_store

    @root_validator
    def validate_credentials(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validates the credentials provided in the values dictionary.

        Args:
            values: A dictionary containing the values to be validated.

        Raises:
            ValueError: If neither api_token nor username is set.

        Returns:
            The values dictionary.
        """
        # Check if the values dictionary contains either an api_token or a
        # username as non-empty strings.
        if values.get("api_token") or values.get("username"):
            return values
        else:
            raise ValueError(
                "Neither api_token nor username is set in the store config."
            )

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

        # When running inside a container, if the URL uses localhost, the
        # target service will not be available. We try to replace localhost
        # with one of the special Docker or K3D internal hostnames.
        url = replace_localhost_with_internal_hostname(url)

        return url

    @validator("verify_ssl")
    def validate_verify_ssl(
        cls, verify_ssl: Union[bool, str]
    ) -> Union[bool, str]:
        """Validates that the verify_ssl either points to a file or is a bool.

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

    @classmethod
    def supports_url_scheme(cls, url: str) -> bool:
        """Check if a URL scheme is supported by this store.

        Args:
            url: The URL to check.

        Returns:
            True if the URL scheme is supported, False otherwise.
        """
        return urlparse(url).scheme in ("http", "https")

    def expand_certificates(self) -> None:
        """Expands the certificates in the verify_ssl field."""
        # Load the certificate values back into the configuration
        if isinstance(self.verify_ssl, str) and os.path.isfile(
            self.verify_ssl
        ):
            with open(self.verify_ssl, "r") as f:
                self.verify_ssl = f.read()

    @classmethod
    def copy_configuration(
        cls,
        config: "StoreConfiguration",
        config_path: str,
        load_config_path: Optional[PurePath] = None,
    ) -> "StoreConfiguration":
        """Create a copy of the store config using a different path.

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
        assert config.api_token is not None
        config = config.copy(exclude={"username", "password"}, deep=True)
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
        client_version = zenml.__version__
        server_version = self.get_store_info().version

        if not DISABLE_CLIENT_SERVER_MISMATCH_WARNING and (
            server_version != client_version
        ):
            logger.warning(
                "Your ZenML client version (%s) does not match the server "
                "version (%s). This version mismatch might lead to errors or "
                "unexpected behavior. \nTo disable this warning message, set "
                "the environment variable `%s=True`",
                client_version,
                server_version,
                ENV_ZENML_DISABLE_CLIENT_SERVER_MISMATCH_WARNING,
            )

    def get_store_info(self) -> ServerModel:
        """Get information about the server.

        Returns:
            Information about the server.
        """
        body = self.get(INFO)
        return ServerModel.parse_obj(body)

    # ------
    # Stacks
    # ------

    def create_stack(self, stack: StackRequestModel) -> StackResponseModel:
        """Register a new stack.

        Args:
            stack: The stack to register.

        Returns:
            The registered stack.
        """
        return self._create_workspace_scoped_resource(
            resource=stack,
            route=STACKS,
            response_model=StackResponseModel,
        )

    def get_stack(self, stack_id: UUID) -> StackResponseModel:
        """Get a stack by its unique ID.

        Args:
            stack_id: The ID of the stack to get.

        Returns:
            The stack with the given ID.
        """
        return self._get_resource(
            resource_id=stack_id,
            route=STACKS,
            response_model=StackResponseModel,
        )

    def list_stacks(
        self, stack_filter_model: StackFilterModel
    ) -> Page[StackResponseModel]:
        """List all stacks matching the given filter criteria.

        Args:
            stack_filter_model: All filter parameters including pagination
                params.

        Returns:
            A list of all stacks matching the filter criteria.
        """
        return self._list_paginated_resources(
            route=STACKS,
            response_model=StackResponseModel,
            filter_model=stack_filter_model,
        )

    def update_stack(
        self, stack_id: UUID, stack_update: StackUpdateModel
    ) -> StackResponseModel:
        """Update a stack.

        Args:
            stack_id: The ID of the stack update.
            stack_update: The update request on the stack.

        Returns:
            The updated stack.
        """
        return self._update_resource(
            resource_id=stack_id,
            resource_update=stack_update,
            route=STACKS,
            response_model=StackResponseModel,
        )

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

    def create_stack_component(
        self,
        component: ComponentRequestModel,
    ) -> ComponentResponseModel:
        """Create a stack component.

        Args:
            component: The stack component to create.

        Returns:
            The created stack component.
        """
        return self._create_workspace_scoped_resource(
            resource=component,
            route=STACK_COMPONENTS,
            response_model=ComponentResponseModel,
        )

    def get_stack_component(
        self, component_id: UUID
    ) -> ComponentResponseModel:
        """Get a stack component by ID.

        Args:
            component_id: The ID of the stack component to get.

        Returns:
            The stack component.
        """
        return self._get_resource(
            resource_id=component_id,
            route=STACK_COMPONENTS,
            response_model=ComponentResponseModel,
        )

    def list_stack_components(
        self, component_filter_model: ComponentFilterModel
    ) -> Page[ComponentResponseModel]:
        """List all stack components matching the given filter criteria.

        Args:
            component_filter_model: All filter parameters including pagination
                params.

        Returns:
            A list of all stack components matching the filter criteria.
        """
        return self._list_paginated_resources(
            route=STACK_COMPONENTS,
            response_model=ComponentResponseModel,
            filter_model=component_filter_model,
        )

    def update_stack_component(
        self,
        component_id: UUID,
        component_update: ComponentUpdateModel,
    ) -> ComponentResponseModel:
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
            response_model=ComponentResponseModel,
        )

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

    def create_flavor(self, flavor: FlavorRequestModel) -> FlavorResponseModel:
        """Creates a new stack component flavor.

        Args:
            flavor: The stack component flavor to create.

        Returns:
            The newly created flavor.
        """
        return self._create_resource(
            resource=flavor,
            route=FLAVORS,
            response_model=FlavorResponseModel,
        )

    def update_flavor(
        self, flavor_id: UUID, flavor_update: FlavorUpdateModel
    ) -> FlavorResponseModel:
        """Updates an existing user.

        Args:
            flavor_id: The id of the flavor to update.
            flavor_update: The update to be applied to the flavor.

        Returns:
            The updated flavor.
        """
        return self._update_resource(
            resource_id=flavor_id,
            resource_update=flavor_update,
            route=FLAVORS,
            response_model=FlavorResponseModel,
        )

    def get_flavor(self, flavor_id: UUID) -> FlavorResponseModel:
        """Get a stack component flavor by ID.

        Args:
            flavor_id: The ID of the stack component flavor to get.

        Returns:
            The stack component flavor.
        """
        return self._get_resource(
            resource_id=flavor_id,
            route=FLAVORS,
            response_model=FlavorResponseModel,
        )

    def list_flavors(
        self, flavor_filter_model: FlavorFilterModel
    ) -> Page[FlavorResponseModel]:
        """List all stack component flavors matching the given filter criteria.

        Args:
            flavor_filter_model: All filter parameters including pagination
                params

        Returns:
            List of all the stack component flavors matching the given criteria.
        """
        return self._list_paginated_resources(
            route=FLAVORS,
            response_model=FlavorResponseModel,
            filter_model=flavor_filter_model,
        )

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

    def create_user(self, user: UserRequestModel) -> UserResponseModel:
        """Creates a new user.

        Args:
            user: User to be created.

        Returns:
            The newly created user.
        """
        return self._create_resource(
            resource=user,
            route=USERS + "?assign_default_role=False",
            response_model=UserResponseModel,
        )

    def get_user(
        self,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        include_private: bool = False,
    ) -> UserResponseModel:
        """Gets a specific user, when no id is specified the active user is returned.

        The `include_private` parameter is ignored here as it is handled
        implicitly by the /current-user endpoint that is queried when no
        user_name_or_id is set. Raises a KeyError in case a user with that id
        does not exist.

        Args:
            user_name_or_id: The name or ID of the user to get.
            include_private: Whether to include private user information

        Returns:
            The requested user, if it was found.
        """
        if user_name_or_id:
            return self._get_resource(
                resource_id=user_name_or_id,
                route=USERS,
                response_model=UserResponseModel,
            )
        else:
            body = self.get(CURRENT_USER)
            return UserResponseModel.parse_obj(body)

    def list_users(
        self, user_filter_model: UserFilterModel
    ) -> Page[UserResponseModel]:
        """List all users.

        Args:
            user_filter_model: All filter parameters including pagination
                params.

        Returns:
            A list of all users.
        """
        return self._list_paginated_resources(
            route=USERS,
            response_model=UserResponseModel,
            filter_model=user_filter_model,
        )

    def update_user(
        self, user_id: UUID, user_update: UserUpdateModel
    ) -> UserResponseModel:
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
            response_model=UserResponseModel,
        )

    def delete_user(self, user_name_or_id: Union[str, UUID]) -> None:
        """Deletes a user.

        Args:
            user_name_or_id: The name or ID of the user to delete.
        """
        self._delete_resource(
            resource_id=user_name_or_id,
            route=USERS,
        )

    # -----
    # Teams
    # -----

    def create_team(self, team: TeamRequestModel) -> TeamResponseModel:
        """Creates a new team.

        Args:
            team: The team model to create.

        Returns:
            The newly created team.
        """
        return self._create_resource(
            resource=team,
            route=TEAMS,
            response_model=TeamResponseModel,
        )

    def get_team(self, team_name_or_id: Union[str, UUID]) -> TeamResponseModel:
        """Gets a specific team.

        Args:
            team_name_or_id: Name or ID of the team to get.

        Returns:
            The requested team.
        """
        return self._get_resource(
            resource_id=team_name_or_id,
            route=TEAMS,
            response_model=TeamResponseModel,
        )

    def list_teams(
        self, team_filter_model: TeamFilterModel
    ) -> Page[TeamResponseModel]:
        """List all teams matching the given filter criteria.

        Args:
            team_filter_model: All filter parameters including pagination
                params.

        Returns:
            A list of all teams matching the filter criteria.
        """
        return self._list_paginated_resources(
            route=TEAMS,
            response_model=TeamResponseModel,
            filter_model=team_filter_model,
        )

    def update_team(
        self, team_id: UUID, team_update: TeamUpdateModel
    ) -> TeamResponseModel:
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
            response_model=TeamResponseModel,
        )

    def delete_team(self, team_name_or_id: Union[str, UUID]) -> None:
        """Deletes a team.

        Args:
            team_name_or_id: Name or ID of the team to delete.
        """
        self._delete_resource(
            resource_id=team_name_or_id,
            route=TEAMS,
        )

    # -----
    # Roles
    # -----

    def create_role(self, role: RoleRequestModel) -> RoleResponseModel:
        """Creates a new role.

        Args:
            role: The role model to create.

        Returns:
            The newly created role.
        """
        return self._create_resource(
            resource=role,
            route=ROLES,
            response_model=RoleResponseModel,
        )

    def get_role(self, role_name_or_id: Union[str, UUID]) -> RoleResponseModel:
        """Gets a specific role.

        Args:
            role_name_or_id: Name or ID of the role to get.

        Returns:
            The requested role.
        """
        return self._get_resource(
            resource_id=role_name_or_id,
            route=ROLES,
            response_model=RoleResponseModel,
        )

    def list_roles(
        self, role_filter_model: RoleFilterModel
    ) -> Page[RoleResponseModel]:
        """List all roles matching the given filter criteria.

        Args:
            role_filter_model: All filter parameters including pagination
                params.

        Returns:
            A list of all roles matching the filter criteria.
        """
        return self._list_paginated_resources(
            route=ROLES,
            response_model=RoleResponseModel,
            filter_model=role_filter_model,
        )

    def update_role(
        self, role_id: UUID, role_update: RoleUpdateModel
    ) -> RoleResponseModel:
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
            response_model=RoleResponseModel,
        )

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

    def list_user_role_assignments(
        self, user_role_assignment_filter_model: UserRoleAssignmentFilterModel
    ) -> Page[UserRoleAssignmentResponseModel]:
        """List all roles assignments matching the given filter criteria.

        Args:
            user_role_assignment_filter_model: All filter parameters including
                pagination params.

        Returns:
            A list of all roles assignments matching the filter criteria.
        """
        return self._list_paginated_resources(
            route=USER_ROLE_ASSIGNMENTS,
            response_model=UserRoleAssignmentResponseModel,
            filter_model=user_role_assignment_filter_model,
        )

    def get_user_role_assignment(
        self, user_role_assignment_id: UUID
    ) -> UserRoleAssignmentResponseModel:
        """Get an existing role assignment by name or ID.

        Args:
            user_role_assignment_id: Name or ID of the role assignment to get.

        Returns:
            The requested workspace.
        """
        return self._get_resource(
            resource_id=user_role_assignment_id,
            route=USER_ROLE_ASSIGNMENTS,
            response_model=UserRoleAssignmentResponseModel,
        )

    def delete_user_role_assignment(
        self, user_role_assignment_id: UUID
    ) -> None:
        """Delete a specific role assignment.

        Args:
            user_role_assignment_id: The ID of the specific role assignment
        """
        self._delete_resource(
            resource_id=user_role_assignment_id,
            route=USER_ROLE_ASSIGNMENTS,
        )

    def create_user_role_assignment(
        self, user_role_assignment: UserRoleAssignmentRequestModel
    ) -> UserRoleAssignmentResponseModel:
        """Creates a new role assignment.

        Args:
            user_role_assignment: The role assignment to create.

        Returns:
            The newly created workspace.
        """
        return self._create_resource(
            resource=user_role_assignment,
            route=USER_ROLE_ASSIGNMENTS,
            response_model=UserRoleAssignmentResponseModel,
        )

    # ---------------------
    # Team Role assignments
    # ---------------------

    def create_team_role_assignment(
        self, team_role_assignment: TeamRoleAssignmentRequestModel
    ) -> TeamRoleAssignmentResponseModel:
        """Creates a new team role assignment.

        Args:
            team_role_assignment: The role assignment model to create.

        Returns:
            The newly created role assignment.
        """
        return self._create_resource(
            resource=team_role_assignment,
            route=TEAM_ROLE_ASSIGNMENTS,
            response_model=TeamRoleAssignmentResponseModel,
        )

    def get_team_role_assignment(
        self, team_role_assignment_id: UUID
    ) -> TeamRoleAssignmentResponseModel:
        """Gets a specific role assignment.

        Args:
            team_role_assignment_id: ID of the role assignment to get.

        Returns:
            The requested role assignment.
        """
        return self._get_resource(
            resource_id=team_role_assignment_id,
            route=TEAM_ROLE_ASSIGNMENTS,
            response_model=TeamRoleAssignmentResponseModel,
        )

    def delete_team_role_assignment(
        self, team_role_assignment_id: UUID
    ) -> None:
        """Delete a specific role assignment.

        Args:
            team_role_assignment_id: The ID of the specific role assignment
        """
        self._delete_resource(
            resource_id=team_role_assignment_id,
            route=TEAM_ROLE_ASSIGNMENTS,
        )

    def list_team_role_assignments(
        self, team_role_assignment_filter_model: TeamRoleAssignmentFilterModel
    ) -> Page[TeamRoleAssignmentResponseModel]:
        """List all roles assignments matching the given filter criteria.

        Args:
            team_role_assignment_filter_model: All filter parameters including
                pagination params.

        Returns:
            A list of all roles assignments matching the filter criteria.
        """
        return self._list_paginated_resources(
            route=TEAM_ROLE_ASSIGNMENTS,
            response_model=TeamRoleAssignmentResponseModel,
            filter_model=team_role_assignment_filter_model,
        )

    # --------
    # Workspaces
    # --------

    def create_workspace(
        self, workspace: WorkspaceRequestModel
    ) -> WorkspaceResponseModel:
        """Creates a new workspace.

        Args:
            workspace: The workspace to create.

        Returns:
            The newly created workspace.
        """
        return self._create_resource(
            resource=workspace,
            route=WORKSPACES,
            response_model=WorkspaceResponseModel,
        )

    def get_workspace(
        self, workspace_name_or_id: Union[UUID, str]
    ) -> WorkspaceResponseModel:
        """Get an existing workspace by name or ID.

        Args:
            workspace_name_or_id: Name or ID of the workspace to get.

        Returns:
            The requested workspace.
        """
        return self._get_resource(
            resource_id=workspace_name_or_id,
            route=WORKSPACES,
            response_model=WorkspaceResponseModel,
        )

    def list_workspaces(
        self, workspace_filter_model: WorkspaceFilterModel
    ) -> Page[WorkspaceResponseModel]:
        """List all workspace matching the given filter criteria.

        Args:
            workspace_filter_model: All filter parameters including pagination
                params.

        Returns:
            A list of all workspace matching the filter criteria.
        """
        return self._list_paginated_resources(
            route=WORKSPACES,
            response_model=WorkspaceResponseModel,
            filter_model=workspace_filter_model,
        )

    def update_workspace(
        self, workspace_id: UUID, workspace_update: WorkspaceUpdateModel
    ) -> WorkspaceResponseModel:
        """Update an existing workspace.

        Args:
            workspace_id: The ID of the workspace to be updated.
            workspace_update: The update to be applied to the workspace.

        Returns:
            The updated workspace.
        """
        return self._update_resource(
            resource_id=workspace_id,
            resource_update=workspace_update,
            route=WORKSPACES,
            response_model=WorkspaceResponseModel,
        )

    def delete_workspace(self, workspace_name_or_id: Union[str, UUID]) -> None:
        """Deletes a workspace.

        Args:
            workspace_name_or_id: Name or ID of the workspace to delete.
        """
        self._delete_resource(
            resource_id=workspace_name_or_id,
            route=WORKSPACES,
        )

    # ---------
    # Pipelines
    # ---------

    def create_pipeline(
        self, pipeline: PipelineRequestModel
    ) -> PipelineResponseModel:
        """Creates a new pipeline in a workspace.

        Args:
            pipeline: The pipeline to create.

        Returns:
            The newly created pipeline.
        """
        return self._create_workspace_scoped_resource(
            resource=pipeline,
            route=PIPELINES,
            response_model=PipelineResponseModel,
        )

    def get_pipeline(self, pipeline_id: UUID) -> PipelineResponseModel:
        """Get a pipeline with a given ID.

        Args:
            pipeline_id: ID of the pipeline.

        Returns:
            The pipeline.
        """
        return self._get_resource(
            resource_id=pipeline_id,
            route=PIPELINES,
            response_model=PipelineResponseModel,
        )

    def list_pipelines(
        self, pipeline_filter_model: PipelineFilterModel
    ) -> Page[PipelineResponseModel]:
        """List all pipelines matching the given filter criteria.

        Args:
            pipeline_filter_model: All filter parameters including pagination
                params.

        Returns:
            A list of all pipelines matching the filter criteria.
        """
        return self._list_paginated_resources(
            route=PIPELINES,
            response_model=PipelineResponseModel,
            filter_model=pipeline_filter_model,
        )

    def update_pipeline(
        self, pipeline_id: UUID, pipeline_update: PipelineUpdateModel
    ) -> PipelineResponseModel:
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
            response_model=PipelineResponseModel,
        )

    def delete_pipeline(self, pipeline_id: UUID) -> None:
        """Deletes a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to delete.
        """
        self._delete_resource(
            resource_id=pipeline_id,
            route=PIPELINES,
        )

    # ---------
    # Builds
    # ---------

    def create_build(
        self,
        build: PipelineBuildRequestModel,
    ) -> PipelineBuildResponseModel:
        """Creates a new build in a workspace.

        Args:
            build: The build to create.

        Returns:
            The newly created build.
        """
        return self._create_workspace_scoped_resource(
            resource=build,
            route=PIPELINE_BUILDS,
            response_model=PipelineBuildResponseModel,
        )

    def get_build(self, build_id: UUID) -> PipelineBuildResponseModel:
        """Get a build with a given ID.

        Args:
            build_id: ID of the build.

        Returns:
            The build.
        """
        return self._get_resource(
            resource_id=build_id,
            route=PIPELINE_BUILDS,
            response_model=PipelineBuildResponseModel,
        )

    def list_builds(
        self, build_filter_model: PipelineBuildFilterModel
    ) -> Page[PipelineBuildResponseModel]:
        """List all builds matching the given filter criteria.

        Args:
            build_filter_model: All filter parameters including pagination
                params.

        Returns:
            A page of all builds matching the filter criteria.
        """
        return self._list_paginated_resources(
            route=PIPELINE_BUILDS,
            response_model=PipelineBuildResponseModel,
            filter_model=build_filter_model,
        )

    def delete_build(self, build_id: UUID) -> None:
        """Deletes a build.

        Args:
            build_id: The ID of the build to delete.
        """
        self._delete_resource(
            resource_id=build_id,
            route=PIPELINE_BUILDS,
        )

    # ----------------------
    # Pipeline Deployments
    # ----------------------

    def create_deployment(
        self,
        deployment: PipelineDeploymentRequestModel,
    ) -> PipelineDeploymentResponseModel:
        """Creates a new deployment in a workspace.

        Args:
            deployment: The deployment to create.

        Returns:
            The newly created deployment.
        """
        return self._create_workspace_scoped_resource(
            resource=deployment,
            route=PIPELINE_DEPLOYMENTS,
            response_model=PipelineDeploymentResponseModel,
        )

    def get_deployment(
        self, deployment_id: UUID
    ) -> PipelineDeploymentResponseModel:
        """Get a deployment with a given ID.

        Args:
            deployment_id: ID of the deployment.

        Returns:
            The deployment.
        """
        return self._get_resource(
            resource_id=deployment_id,
            route=PIPELINE_DEPLOYMENTS,
            response_model=PipelineDeploymentResponseModel,
        )

    def list_deployments(
        self, deployment_filter_model: PipelineDeploymentFilterModel
    ) -> Page[PipelineDeploymentResponseModel]:
        """List all deployments matching the given filter criteria.

        Args:
            deployment_filter_model: All filter parameters including pagination
                params.

        Returns:
            A page of all deployments matching the filter criteria.
        """
        return self._list_paginated_resources(
            route=PIPELINE_DEPLOYMENTS,
            response_model=PipelineDeploymentResponseModel,
            filter_model=deployment_filter_model,
        )

    def delete_deployment(self, deployment_id: UUID) -> None:
        """Deletes a deployment.

        Args:
            deployment_id: The ID of the deployment to delete.
        """
        self._delete_resource(
            resource_id=deployment_id,
            route=PIPELINE_DEPLOYMENTS,
        )

    # ---------
    # Schedules
    # ---------

    def create_schedule(
        self, schedule: ScheduleRequestModel
    ) -> ScheduleResponseModel:
        """Creates a new schedule.

        Args:
            schedule: The schedule to create.

        Returns:
            The newly created schedule.
        """
        return self._create_workspace_scoped_resource(
            resource=schedule,
            route=SCHEDULES,
            response_model=ScheduleResponseModel,
        )

    def get_schedule(self, schedule_id: UUID) -> ScheduleResponseModel:
        """Get a schedule with a given ID.

        Args:
            schedule_id: ID of the schedule.

        Returns:
            The schedule.
        """
        return self._get_resource(
            resource_id=schedule_id,
            route=SCHEDULES,
            response_model=ScheduleResponseModel,
        )

    def list_schedules(
        self, schedule_filter_model: ScheduleFilterModel
    ) -> Page[ScheduleResponseModel]:
        """List all schedules in the workspace.

        Args:
            schedule_filter_model: All filter parameters including pagination
                params

        Returns:
            A list of schedules.
        """
        return self._list_paginated_resources(
            route=SCHEDULES,
            response_model=ScheduleResponseModel,
            filter_model=schedule_filter_model,
        )

    def update_schedule(
        self,
        schedule_id: UUID,
        schedule_update: ScheduleUpdateModel,
    ) -> ScheduleResponseModel:
        """Updates a schedule.

        Args:
            schedule_id: The ID of the schedule to be updated.
            schedule_update: The update to be applied.

        Returns:
            The updated schedule.
        """
        return self._update_resource(
            resource_id=schedule_id,
            resource_update=schedule_update,
            route=SCHEDULES,
            response_model=ScheduleResponseModel,
        )

    def delete_schedule(self, schedule_id: UUID) -> None:
        """Deletes a schedule.

        Args:
            schedule_id: The ID of the schedule to delete.
        """
        self._delete_resource(
            resource_id=schedule_id,
            route=SCHEDULES,
        )

    # --------------
    # Pipeline runs
    # --------------

    def create_run(
        self, pipeline_run: PipelineRunRequestModel
    ) -> PipelineRunResponseModel:
        """Creates a pipeline run.

        Args:
            pipeline_run: The pipeline run to create.

        Returns:
            The created pipeline run.
        """
        return self._create_workspace_scoped_resource(
            resource=pipeline_run,
            response_model=PipelineRunResponseModel,
            route=RUNS,
        )

    def get_run(
        self, run_name_or_id: Union[UUID, str]
    ) -> PipelineRunResponseModel:
        """Gets a pipeline run.

        Args:
            run_name_or_id: The name or ID of the pipeline run to get.

        Returns:
            The pipeline run.
        """
        return self._get_resource(
            resource_id=run_name_or_id,
            route=RUNS,
            response_model=PipelineRunResponseModel,
        )

    def get_or_create_run(
        self, pipeline_run: PipelineRunRequestModel
    ) -> Tuple[PipelineRunResponseModel, bool]:
        """Gets or creates a pipeline run.

        If a run with the same ID or name already exists, it is returned.
        Otherwise, a new run is created.

        Args:
            pipeline_run: The pipeline run to get or create.

        Returns:
            The pipeline run, and a boolean indicating whether the run was
            created or not.
        """
        return self._get_or_create_workspace_scoped_resource(
            resource=pipeline_run,
            route=RUNS,
            response_model=PipelineRunResponseModel,
        )

    def list_runs(
        self, runs_filter_model: PipelineRunFilterModel
    ) -> Page[PipelineRunResponseModel]:
        """List all pipeline runs matching the given filter criteria.

        Args:
            runs_filter_model: All filter parameters including pagination
                params.

        Returns:
            A list of all pipeline runs matching the filter criteria.
        """
        return self._list_paginated_resources(
            route=RUNS,
            response_model=PipelineRunResponseModel,
            filter_model=runs_filter_model,
        )

    def update_run(
        self, run_id: UUID, run_update: PipelineRunUpdateModel
    ) -> PipelineRunResponseModel:
        """Updates a pipeline run.

        Args:
            run_id: The ID of the pipeline run to update.
            run_update: The update to be applied to the pipeline run.


        Returns:
            The updated pipeline run.
        """
        return self._update_resource(
            resource_id=run_id,
            resource_update=run_update,
            response_model=PipelineRunResponseModel,
            route=RUNS,
        )

    def delete_run(self, run_id: UUID) -> None:
        """Deletes a pipeline run.

        Args:
            run_id: The ID of the pipeline run to delete.
        """
        self._delete_resource(
            resource_id=run_id,
            route=RUNS,
        )

    # ------------------
    # Pipeline run steps
    # ------------------

    def create_run_step(
        self, step_run: StepRunRequestModel
    ) -> StepRunResponseModel:
        """Creates a step run.

        Args:
            step_run: The step run to create.

        Returns:
            The created step run.
        """
        return self._create_resource(
            resource=step_run,
            response_model=StepRunResponseModel,
            route=STEPS,
        )

    def get_run_step(self, step_run_id: UUID) -> StepRunResponseModel:
        """Get a step run by ID.

        Args:
            step_run_id: The ID of the step run to get.

        Returns:
            The step run.
        """
        return self._get_resource(
            resource_id=step_run_id,
            route=STEPS,
            response_model=StepRunResponseModel,
        )

    def list_run_steps(
        self, step_run_filter_model: StepRunFilterModel
    ) -> Page[StepRunResponseModel]:
        """List all step runs matching the given filter criteria.

        Args:
            step_run_filter_model: All filter parameters including pagination
                params.

        Returns:
            A list of all step runs matching the filter criteria.
        """
        return self._list_paginated_resources(
            route=STEPS,
            response_model=StepRunResponseModel,
            filter_model=step_run_filter_model,
        )

    def update_run_step(
        self,
        step_run_id: UUID,
        step_run_update: StepRunUpdateModel,
    ) -> StepRunResponseModel:
        """Updates a step run.

        Args:
            step_run_id: The ID of the step to update.
            step_run_update: The update to be applied to the step.

        Returns:
            The updated step run.
        """
        return self._update_resource(
            resource_id=step_run_id,
            resource_update=step_run_update,
            response_model=StepRunResponseModel,
            route=STEPS,
        )

    # ---------
    # Artifacts
    # ---------

    def create_artifact(
        self, artifact: ArtifactRequestModel
    ) -> ArtifactResponseModel:
        """Creates an artifact.

        Args:
            artifact: The artifact to create.

        Returns:
            The created artifact.
        """
        return self._create_resource(
            resource=artifact,
            response_model=ArtifactResponseModel,
            route=ARTIFACTS,
        )

    def get_artifact(self, artifact_id: UUID) -> ArtifactResponseModel:
        """Gets an artifact.

        Args:
            artifact_id: The ID of the artifact to get.

        Returns:
            The artifact.
        """
        return self._get_resource(
            resource_id=artifact_id,
            route=ARTIFACTS,
            response_model=ArtifactResponseModel,
        )

    def list_artifacts(
        self, artifact_filter_model: ArtifactFilterModel
    ) -> Page[ArtifactResponseModel]:
        """List all artifacts matching the given filter criteria.

        Args:
            artifact_filter_model: All filter parameters including pagination
                params.

        Returns:
            A list of all artifacts matching the filter criteria.
        """
        return self._list_paginated_resources(
            route=ARTIFACTS,
            response_model=ArtifactResponseModel,
            filter_model=artifact_filter_model,
        )

    def delete_artifact(self, artifact_id: UUID) -> None:
        """Deletes an artifact.

        Args:
            artifact_id: The ID of the artifact to delete.
        """
        self._delete_resource(resource_id=artifact_id, route=ARTIFACTS)

    # ------------
    # Run Metadata
    # ------------

    def create_run_metadata(
        self, run_metadata: RunMetadataRequestModel
    ) -> RunMetadataResponseModel:
        """Creates run metadata.

        Args:
            run_metadata: The run metadata to create.

        Returns:
            The created run metadata.
        """
        return self._create_workspace_scoped_resource(
            resource=run_metadata,
            response_model=RunMetadataResponseModel,
            route=RUN_METADATA,
        )

    def list_run_metadata(
        self,
        run_metadata_filter_model: RunMetadataFilterModel,
    ) -> Page[RunMetadataResponseModel]:
        """List run metadata.

        Args:
            run_metadata_filter_model: All filter parameters including
                pagination params.

        Returns:
            The run metadata.
        """
        return self._list_paginated_resources(
            route=RUN_METADATA,
            response_model=RunMetadataResponseModel,
            filter_model=run_metadata_filter_model,
        )

    # -----------------
    # Code Repositories
    # -----------------

    def create_code_repository(
        self, code_repository: CodeRepositoryRequestModel
    ) -> CodeRepositoryResponseModel:
        """Creates a new code repository.

        Args:
            code_repository: Code repository to be created.

        Returns:
            The newly created code repository.
        """
        return self._create_workspace_scoped_resource(
            resource=code_repository,
            response_model=CodeRepositoryResponseModel,
            route=CODE_REPOSITORIES,
        )

    def get_code_repository(
        self, code_repository_id: UUID
    ) -> CodeRepositoryResponseModel:
        """Gets a specific code repository.

        Args:
            code_repository_id: The ID of the code repository to get.

        Returns:
            The requested code repository, if it was found.
        """
        return self._get_resource(
            resource_id=code_repository_id,
            route=CODE_REPOSITORIES,
            response_model=CodeRepositoryResponseModel,
        )

    def list_code_repositories(
        self, filter_model: CodeRepositoryFilterModel
    ) -> Page[CodeRepositoryResponseModel]:
        """List all code repositories.

        Args:
            filter_model: All filter parameters including pagination
                params.

        Returns:
            A page of all code repositories.
        """
        return self._list_paginated_resources(
            route=CODE_REPOSITORIES,
            response_model=CodeRepositoryResponseModel,
            filter_model=filter_model,
        )

    def update_code_repository(
        self, code_repository_id: UUID, update: CodeRepositoryUpdateModel
    ) -> CodeRepositoryResponseModel:
        """Updates an existing code repository.

        Args:
            code_repository_id: The ID of the code repository to update.
            update: The update to be applied to the code repository.

        Returns:
            The updated code repository.
        """
        return self._update_resource(
            resource_id=code_repository_id,
            resource_update=update,
            response_model=CodeRepositoryResponseModel,
            route=CODE_REPOSITORIES,
        )

    def delete_code_repository(self, code_repository_id: UUID) -> None:
        """Deletes a code repository.

        Args:
            code_repository_id: The ID of the code repository to delete.
        """
        self._delete_resource(
            resource_id=code_repository_id, route=CODE_REPOSITORIES
        )

    # ------------------
    # Service Connectors
    # ------------------

    def _populate_connector_type(
        self,
        *connector_models: Union[
            ServiceConnectorResponseModel, ServiceConnectorResourcesModel
        ],
    ) -> None:
        """Populates or updates the connector type of the given connector or resource models.

        If the connector type is not locally available, the connector type
        field is left as is. The local and remote flags of the connector type
        are updated accordingly.

        Args:
            connector_models: The service connector or resource models to
                populate.
        """
        for service_connector in connector_models:
            # Mark the remote connector type as being only remotely available
            if not isinstance(service_connector.connector_type, str):
                service_connector.connector_type.local = False
                service_connector.connector_type.remote = True

            if not service_connector_registry.is_registered(
                service_connector.type
            ):
                continue

            connector_type = (
                service_connector_registry.get_service_connector_type(
                    service_connector.type
                )
            )
            connector_type.local = True
            if not isinstance(service_connector.connector_type, str):
                connector_type.remote = True
            service_connector.connector_type = connector_type

    def create_service_connector(
        self, service_connector: ServiceConnectorRequestModel
    ) -> ServiceConnectorResponseModel:
        """Creates a new service connector.

        Args:
            service_connector: Service connector to be created.

        Returns:
            The newly created service connector.
        """
        connector_model = self._create_workspace_scoped_resource(
            resource=service_connector,
            route=SERVICE_CONNECTORS,
            response_model=ServiceConnectorResponseModel,
        )
        self._populate_connector_type(connector_model)
        return connector_model

    def get_service_connector(
        self, service_connector_id: UUID
    ) -> ServiceConnectorResponseModel:
        """Gets a specific service connector.

        Args:
            service_connector_id: The ID of the service connector to get.

        Returns:
            The requested service connector, if it was found.
        """
        connector_model = self._get_resource(
            resource_id=service_connector_id,
            route=SERVICE_CONNECTORS,
            response_model=ServiceConnectorResponseModel,
            params={"expand_secrets": False},
        )
        self._populate_connector_type(connector_model)
        return connector_model

    def list_service_connectors(
        self, filter_model: ServiceConnectorFilterModel
    ) -> Page[ServiceConnectorResponseModel]:
        """List all service connectors.

        Args:
            filter_model: All filter parameters including pagination
                params.

        Returns:
            A page of all service connectors.
        """
        connector_models = self._list_paginated_resources(
            route=SERVICE_CONNECTORS,
            response_model=ServiceConnectorResponseModel,
            filter_model=filter_model,
            params={"expand_secrets": False},
        )
        self._populate_connector_type(*connector_models.items)
        return connector_models

    def update_service_connector(
        self, service_connector_id: UUID, update: ServiceConnectorUpdateModel
    ) -> ServiceConnectorResponseModel:
        """Updates an existing service connector.

        The update model contains the fields to be updated. If a field value is
        set to None in the model, the field is not updated, but there are
        special rules concerning some fields:

        * the `configuration` and `secrets` fields together represent a full
        valid configuration update, not just a partial update. If either is
        set (i.e. not None) in the update, their values are merged together and
        will replace the existing configuration and secrets values.
        * the `resource_id` field value is also a full replacement value: if set
        to `None`, the resource ID is removed from the service connector.
        * the `expiration_seconds` field value is also a full replacement value:
        if set to `None`, the expiration is removed from the service connector.
        * the `secret_id` field value in the update is ignored, given that
        secrets are managed internally by the ZenML store.
        * the `labels` field is also a full labels update: if set (i.e. not
        `None`), all existing labels are removed and replaced by the new labels
        in the update.

        Args:
            service_connector_id: The ID of the service connector to update.
            update: The update to be applied to the service connector.

        Returns:
            The updated service connector.
        """
        connector_model = self._update_resource(
            resource_id=service_connector_id,
            resource_update=update,
            response_model=ServiceConnectorResponseModel,
            route=SERVICE_CONNECTORS,
        )
        self._populate_connector_type(connector_model)
        return connector_model

    def delete_service_connector(self, service_connector_id: UUID) -> None:
        """Deletes a service connector.

        Args:
            service_connector_id: The ID of the service connector to delete.
        """
        self._delete_resource(
            resource_id=service_connector_id, route=SERVICE_CONNECTORS
        )

    def verify_service_connector_config(
        self,
        service_connector: ServiceConnectorRequestModel,
        list_resources: bool = True,
    ) -> ServiceConnectorResourcesModel:
        """Verifies if a service connector configuration has access to resources.

        Args:
            service_connector: The service connector configuration to verify.
            list_resources: If True, the list of all resources accessible
                through the service connector and matching the supplied resource
                type and ID are returned.

        Returns:
            The list of resources that the service connector configuration has
            access to.
        """
        response_body = self.post(
            f"{SERVICE_CONNECTORS}{SERVICE_CONNECTOR_VERIFY}",
            body=service_connector,
            params={"list_resources": list_resources},
        )

        resources = ServiceConnectorResourcesModel.parse_obj(response_body)
        self._populate_connector_type(resources)
        return resources

    def verify_service_connector(
        self,
        service_connector_id: UUID,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        list_resources: bool = True,
    ) -> ServiceConnectorResourcesModel:
        """Verifies if a service connector instance has access to one or more resources.

        Args:
            service_connector_id: The ID of the service connector to verify.
            resource_type: The type of resource to verify access to.
            resource_id: The ID of the resource to verify access to.
            list_resources: If True, the list of all resources accessible
                through the service connector and matching the supplied resource
                type and ID are returned.

        Returns:
            The list of resources that the service connector has access to,
            scoped to the supplied resource type and ID, if provided.
        """
        params: Dict[str, Any] = {"list_resources": list_resources}
        if resource_type:
            params["resource_type"] = resource_type
        if resource_id:
            params["resource_id"] = resource_id
        response_body = self.put(
            f"{SERVICE_CONNECTORS}/{str(service_connector_id)}{SERVICE_CONNECTOR_VERIFY}",
            params=params,
        )

        resources = ServiceConnectorResourcesModel.parse_obj(response_body)
        self._populate_connector_type(resources)
        return resources

    def get_service_connector_client(
        self,
        service_connector_id: UUID,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> ServiceConnectorResponseModel:
        """Get a service connector client for a service connector and given resource.

        Args:
            service_connector_id: The ID of the base service connector to use.
            resource_type: The type of resource to get a client for.
            resource_id: The ID of the resource to get a client for.

        Returns:
            A service connector client that can be used to access the given
            resource.
        """
        params = {}
        if resource_type:
            params["resource_type"] = resource_type
        if resource_id:
            params["resource_id"] = resource_id
        response_body = self.get(
            f"{SERVICE_CONNECTORS}/{str(service_connector_id)}{SERVICE_CONNECTOR_CLIENT}",
            params=params,
        )

        connector = ServiceConnectorResponseModel.parse_obj(response_body)
        self._populate_connector_type(connector)
        return connector

    def list_service_connector_resources(
        self,
        user_name_or_id: Union[str, UUID],
        workspace_name_or_id: Union[str, UUID],
        connector_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> List[ServiceConnectorResourcesModel]:
        """List resources that can be accessed by service connectors.

        Args:
            user_name_or_id: The name or ID of the user to scope to.
            workspace_name_or_id: The name or ID of the workspace to scope to.
            connector_type: The type of service connector to scope to.
            resource_type: The type of resource to scope to.
            resource_id: The ID of the resource to scope to.

        Returns:
            The matching list of resources that available service
            connectors have access to.
        """
        params = {}
        if connector_type:
            params["connector_type"] = connector_type
        if resource_type:
            params["resource_type"] = resource_type
        if resource_id:
            params["resource_id"] = resource_id
        response_body = self.get(
            f"{WORKSPACES}/{workspace_name_or_id}{SERVICE_CONNECTORS}{SERVICE_CONNECTOR_RESOURCES}",
            params=params,
        )

        assert isinstance(response_body, list)
        resource_list = [
            ServiceConnectorResourcesModel.parse_obj(item)
            for item in response_body
        ]

        self._populate_connector_type(*resource_list)

        # For service connectors with types that are only locally available,
        # we need to retrieve the resource list locally
        for idx, resources in enumerate(resource_list):
            if isinstance(resources.connector_type, str):
                # Skip connector types that are neither locally nor remotely
                # available
                continue
            if resources.connector_type.remote:
                # Skip connector types that are remotely available
                continue

            # Retrieve the resource list locally
            assert resources.id is not None
            connector = self.get_service_connector(resources.id)
            connector_instance = (
                service_connector_registry.instantiate_connector(
                    model=connector
                )
            )

            try:
                local_resources = connector_instance.verify(
                    resource_type=resource_type,
                    resource_id=resource_id,
                )
            except (ValueError, AuthorizationException) as e:
                logger.error(
                    f'Failed to fetch {resource_type or "available"} '
                    f"resources from service connector {connector.name}/"
                    f"{connector.id}: {e}"
                )
                continue

            resource_list[idx] = local_resources

        return resource_list

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
        params = {}
        if connector_type:
            params["connector_type"] = connector_type
        if resource_type:
            params["resource_type"] = resource_type
        if auth_method:
            params["auth_method"] = auth_method
        response_body = self.get(
            SERVICE_CONNECTOR_TYPES,
            params=params,
        )

        assert isinstance(response_body, list)
        remote_connector_types = [
            ServiceConnectorTypeModel.parse_obj(item) for item in response_body
        ]

        # Mark the remote connector types as being only remotely available
        for c in remote_connector_types:
            c.local = False
            c.remote = True

        local_connector_types = (
            service_connector_registry.list_service_connector_types(
                connector_type=connector_type,
                resource_type=resource_type,
                auth_method=auth_method,
            )
        )

        # Add the connector types in the local registry to the list of
        # connector types available remotely. Overwrite those that have
        # the same connector type but mark them as being remotely available.
        connector_types_map = {
            connector_type.connector_type: connector_type
            for connector_type in remote_connector_types
        }

        for connector in local_connector_types:
            if connector.connector_type in connector_types_map:
                connector.remote = True
            connector_types_map[connector.connector_type] = connector

        return list(connector_types_map.values())

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
        # Use the local registry to get the service connector type, if it
        # exists.
        local_connector_type: Optional[ServiceConnectorTypeModel] = None
        if service_connector_registry.is_registered(connector_type):
            local_connector_type = (
                service_connector_registry.get_service_connector_type(
                    connector_type
                )
            )
        try:
            response_body = self.get(
                f"{SERVICE_CONNECTOR_TYPES}/{connector_type}",
            )
            remote_connector_type = ServiceConnectorTypeModel.parse_obj(
                response_body
            )
            if local_connector_type:
                # If locally available, return the local connector type but
                # mark it as being remotely available.
                local_connector_type.remote = True
                return local_connector_type

            # Mark the remote connector type as being only remotely available
            remote_connector_type.local = False
            remote_connector_type.remote = True

            return remote_connector_type
        except KeyError:
            # If the service connector type is not found, check the local
            # registry.
            return service_connector_registry.get_service_connector_type(
                connector_type
            )

    # =======================
    # Internal helper methods
    # =======================

    def _get_auth_token(self) -> str:
        """Get the authentication token for the REST store.

        Returns:
            The authentication token.

        Raises:
            ValueError: if the response from the server isn't in the right
                format.
        """
        if self._api_token is None:
            # Check if the API token is already stored in the config
            if self.config.api_token:
                self._api_token = self.config.api_token
            # Check if the username and password are provided in the config
            elif (
                self.config.username is not None
                and self.config.password is not None
            ):
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
                if (
                    not isinstance(response, dict)
                    or "access_token" not in response
                ):
                    raise ValueError(
                        f"Bad API Response. Expected access token dict, got "
                        f"{type(response)}"
                    )
                self._api_token = response["access_token"]
                self.config.api_token = self._api_token
            else:
                raise ValueError(
                    "No API token or username/password provided. Please "
                    "provide either a token or a username and password in "
                    "the ZenStore config."
                )
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
            ValueError: if the response is not in the right format.
            RuntimeError: if an error response is received from the server
                and a more specific exception cannot be determined.
            exc: the exception converted from an error response, if one
                is returned from the server.
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
        elif response.status_code >= 400:
            exc = exception_from_response(response)
            if exc is not None:
                raise exc
            else:
                raise RuntimeError(
                    f"{response.status_code} HTTP Error received from server: "
                    f"{response.text}"
                )
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

        self.session.headers.update(
            {source_context.name: source_context.get().value}
        )

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
            "DELETE",
            self.url + API + VERSION_1 + path,
            params=params,
            **kwargs,
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
        body: Optional[BaseModel] = None,
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
        data = body.json(exclude_unset=True) if body else None
        return self._request(
            "PUT",
            self.url + API + VERSION_1 + path,
            data=data,
            params=params,
            **kwargs,
        )

    def _create_resource(
        self,
        resource: BaseRequestModel,
        response_model: Type[AnyResponseModel],
        route: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> AnyResponseModel:
        """Create a new resource.

        Args:
            resource: The resource to create.
            route: The resource REST API route to use.
            response_model: Optional model to use to deserialize the response
                body. If not provided, the resource class itself will be used.
            params: Optional query parameters to pass to the endpoint.

        Returns:
            The created resource.
        """
        response_body = self.post(f"{route}", body=resource, params=params)
        return response_model.parse_obj(response_body)

    def _create_workspace_scoped_resource(
        self,
        resource: WorkspaceScopedRequestModel,
        response_model: Type[AnyResponseModel],
        route: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> AnyResponseModel:
        """Create a new workspace scoped resource.

        Args:
            resource: The resource to create.
            route: The resource REST API route to use.
            response_model: Optional model to use to deserialize the response
                body. If not provided, the resource class itself will be used.
            params: Optional query parameters to pass to the endpoint.

        Returns:
            The created resource.
        """
        return self._create_resource(
            resource=resource,
            response_model=response_model,
            route=f"{WORKSPACES}/{str(resource.workspace)}{route}",
            params=params,
        )

    def _get_or_create_resource(
        self,
        resource: BaseRequestModel,
        response_model: Type[AnyResponseModel],
        route: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[AnyResponseModel, bool]:
        """Get or create a resource.

        Args:
            resource: The resource to get or create.
            route: The resource REST API route to use.
            response_model: Optional model to use to deserialize the response
                body. If not provided, the resource class itself will be used.
            params: Optional query parameters to pass to the endpoint.

        Returns:
            The created resource, and a boolean indicating whether the resource
            was created or not.

        Raises:
            ValueError: If the response body is not a list with 2 elements
                where the first element is the resource and the second element
                a boolean indicating whether the resource was created or not.
        """
        response_body = self.post(
            f"{route}{GET_OR_CREATE}",
            body=resource,
            params=params,
        )
        if not isinstance(response_body, list):
            raise ValueError(
                f"Expected a list response from the {route}{GET_OR_CREATE} "
                f"endpoint but got {type(response_body)} instead."
            )
        if len(response_body) != 2:
            raise ValueError(
                f"Expected a list response with 2 elements from the "
                f"{route}{GET_OR_CREATE} endpoint but got {len(response_body)} "
                f"elements instead."
            )
        model_json, was_created = response_body
        if not isinstance(was_created, bool):
            raise ValueError(
                f"Expected a boolean as the second element of the list "
                f"response from the {route}{GET_OR_CREATE} endpoint but got "
                f"{type(was_created)} instead."
            )
        return response_model.parse_obj(model_json), was_created

    def _get_or_create_workspace_scoped_resource(
        self,
        resource: WorkspaceScopedRequestModel,
        response_model: Type[AnyResponseModel],
        route: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[AnyResponseModel, bool]:
        """Get or create a workspace scoped resource.

        Args:
            resource: The resource to get or create.
            route: The resource REST API route to use.
            response_model: Optional model to use to deserialize the response
                body. If not provided, the resource class itself will be used.
            params: Optional query parameters to pass to the endpoint.

        Returns:
            The created resource, and a boolean indicating whether the resource
            was created or not.
        """
        return self._get_or_create_resource(
            resource=resource,
            response_model=response_model,
            route=f"{WORKSPACES}/{str(resource.workspace)}{route}",
            params=params,
        )

    def _get_resource(
        self,
        resource_id: Union[str, UUID],
        route: str,
        response_model: Type[AnyResponseModel],
        params: Optional[Dict[str, Any]] = None,
    ) -> AnyResponseModel:
        """Retrieve a single resource.

        Args:
            resource_id: The ID of the resource to retrieve.
            route: The resource REST API route to use.
            response_model: Model to use to serialize the response body.
            params: Optional query parameters to pass to the endpoint.

        Returns:
            The retrieved resource.
        """
        body = self.get(f"{route}/{str(resource_id)}", params=params)
        return response_model.parse_obj(body)

    def _list_paginated_resources(
        self,
        route: str,
        response_model: Type[AnyResponseModel],
        filter_model: BaseFilterModel,
        params: Optional[Dict[str, Any]] = None,
    ) -> Page[AnyResponseModel]:
        """Retrieve a list of resources filtered by some criteria.

        Args:
            route: The resource REST API route to use.
            response_model: Model to use to serialize the response body.
            filter_model: The filter model to use for the list query.
            params: Optional query parameters to pass to the endpoint.

        Returns:
            List of retrieved resources matching the filter criteria.

        Raises:
            ValueError: If the value returned by the server is not a list.
        """
        # leave out filter params that are not supplied
        params = params or {}
        params.update(filter_model.dict(exclude_none=True))
        body = self.get(f"{route}", params=params)
        if not isinstance(body, dict):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        # The initial page of items will be of type BaseResponseModel
        page_of_items: Page[AnyResponseModel] = Page.parse_obj(body)
        # So these items will be parsed into their correct types like here
        page_of_items.items = [
            response_model.parse_obj(generic_item)
            for generic_item in page_of_items.items
        ]
        return page_of_items

    def _list_resources(
        self,
        route: str,
        response_model: Type[AnyResponseModel],
        **filters: Any,
    ) -> List[AnyResponseModel]:
        """Retrieve a list of resources filtered by some criteria.

        Args:
            route: The resource REST API route to use.
            response_model: Model to use to serialize the response body.
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
        resource_update: BaseModel,
        response_model: Type[AnyResponseModel],
        route: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> AnyResponseModel:
        """Update an existing resource.

        Args:
            resource_id: The id of the resource to update.
            resource_update: The resource update.
            response_model: Optional model to use to deserialize the response
                body. If not provided, the resource class itself will be used.
            route: The resource REST API route to use.
            params: Optional query parameters to pass to the endpoint.

        Returns:
            The updated resource.
        """
        response_body = self.put(
            f"{route}/{str(resource_id)}", body=resource_update, params=params
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
