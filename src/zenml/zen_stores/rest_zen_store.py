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

import re
from pathlib import Path, PurePath
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)
from uuid import UUID

import requests
from pydantic import BaseModel

from zenml.config.store_config import StoreConfiguration
from zenml.constants import (
    LOGIN,
    PIPELINES,
    PROJECTS,
    STACK_COMPONENTS,
    STACKS,
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
from zenml.logger import get_logger
from zenml.models import (
    ArtifactModel,
    ComponentModel,
    FlavorModel,
    PipelineModel,
    PipelineRunModel,
    ProjectModel,
    RoleAssignmentModel,
    RoleModel,
    StackModel,
    StepRunModel,
    TeamModel,
    UserModel,
)
from zenml.zen_server.models.pipeline_models import (
    CreatePipelineRequest,
    UpdatePipelineRequest,
)
from zenml.zen_server.models.projects_models import (
    CreateProjectRequest,
    UpdateProjectRequest,
)
from zenml.zen_server.models.stack_models import (
    CreateStackRequest,
    UpdateStackRequest,
)
from zenml.zen_server.models.user_management_models import (
    CreateUserRequest,
    CreateUserResponse,
    UpdateUserRequest,
)
from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)

# type alias for possible json payloads (the Anys are recursive Json instances)
Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

AnyModel = TypeVar("AnyModel", bound=BaseModel)


class RestZenStoreConfiguration(StoreConfiguration):
    """REST ZenML store configuration.

    Attributes:
        username: The username to use to connect to the Zen server.
        password: The password to use to connect to the Zen server.
    """

    type: StoreType = StoreType.REST
    username: str
    password: str = ""

    class Config:
        """Pydantic configuration class."""

        # Validate attributes when assigning them. We need to set this in order
        # to have a mix of mutable and immutable attributes
        validate_assignment = True
        # Ignore extra attributes set in the class.
        extra = "ignore"


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

    @staticmethod
    def get_path_from_url(url: str) -> Optional[Path]:
        """Get the path from a URL, if it points or is backed by a local file.

        Args:
            url: The URL to get the path from.

        Returns:
            None, because there are no local paths from REST URLs.
        """
        return None

    @staticmethod
    def get_local_url(path: str) -> str:
        """Get a local URL for a given local path.

        Args:
            path: the path string to build a URL out of.

        Raises:
            NotImplementedError: always
        """
        raise NotImplementedError("Cannot build a REST url from a path.")

    @staticmethod
    def validate_url(url: str) -> str:
        """Check if the given url is a valid REST URL.

        Args:
            url: The url to check.

        Returns:
            The validated url.

        Raises:
            ValueError: If the url is not valid.
        """
        url = url.rstrip("/")
        scheme = re.search("^([a-z0-9]+://)", url)
        if scheme is None or scheme.group() not in ("https://", "http://"):
            raise ValueError(
                "Invalid URL for REST store: {url}. Should be in the form "
                "https://hostname[:port] or http://hostname[:port]."
            )

        return url

    @classmethod
    def copy_local_store(
        cls,
        config: StoreConfiguration,
        path: str,
        load_config_path: Optional[PurePath] = None,
    ) -> StoreConfiguration:
        """Copy a local store to a new location.

        Use this method to create a copy of a store database to a new location
        and return a new store configuration pointing to the database copy. This
        only applies to stores that use the local filesystem to store their
        data. Calling this method for remote stores simply returns the input
        store configuration unaltered.

        Args:
            config: The configuration of the store to copy.
            path: The new local path where the store DB will be copied.
            load_config_path: path that will be used to load the copied store
                database. This can be set to a value different from `path`
                if the local database copy will be loaded from a different
                environment, e.g. when the database is copied to a container
                image and loaded using a different absolute path. This will be
                reflected in the paths and URLs encoded in the copied store
                configuration.

        Returns:
            The store configuration of the copied store.
        """
        # REST zen stores are not backed by local files
        return config

    # ------------
    # TFX Metadata
    # ------------

    def get_metadata_config(self) -> str:
        """Get the TFX metadata config of this ZenStore.

        Returns:
            The TFX metadata config of this ZenStore.
        """

    # ------
    # Stacks
    # ------

    def register_stack(
        self,
        stack: StackModel,
    ) -> StackModel:
        """Register a new stack.

        Args:
            user_name_or_id: The stack owner.
            project_name_or_id: The project that the stack belongs to.
            stack: The stack to register.

        Returns:
            The registered stack.

        Raises:
            StackExistsError: If a stack with the same name is already owned
                by this user in this project.
        """
        return self._create_project_scoped_resource(
            resource=stack,
            route=STACKS,
            request_model=CreateStackRequest,
        )

    def get_stack(self, stack_id: UUID) -> StackModel:
        """Get a stack by its unique ID.

        Args:
            stack_id: The ID of the stack to get.

        Returns:
            The stack with the given ID.

        Raises:
            KeyError: if the stack doesn't exist.
        """
        return self._get_resource(
            resource_id=stack_id,
            route=STACKS,
            resource_model=StackModel,
        )

    def list_stacks(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[StackModel]:
        """List all stacks matching the given filter criteria.

        Args:
            project_name_or_id: Id or name of the Project containing the stack
            user_name_or_id: Optionally filter stacks by their owner
            name: Optionally filter stacks by their name
            is_shared: Optionally filter out stacks by whether they are shared
                or not

        Returns:
            A list of all stacks matching the filter criteria.

        Raises:
            KeyError: if the project doesn't exist.
        """
        filters = locals()
        filters.pop("self")
        return self._list_resources(
            route=STACKS,
            resource_model=StackModel,
            **filters,
        )

    def update_stack(
        self,
        stack: StackModel,
    ) -> StackModel:
        """Update a stack.

        Args:
            stack: The stack to use for the update.

        Returns:
            The updated stack.

        Raises:
            KeyError: if the stack doesn't exist.
        """
        return self._update_resource(
            resource=stack,
            route=STACKS,
            request_model=UpdateStackRequest,
        )

    def delete_stack(self, stack_id: UUID) -> None:
        """Delete a stack.

        Args:
            stack_id: The ID of the stack to delete.

        Raises:
            KeyError: if the stack doesn't exist.
        """
        self._delete_resource(
            resource_id=stack_id,
            route=STACKS,
        )

    # ----------------
    # Stack components
    # ----------------

    def register_stack_component(
        self,
        component: ComponentModel,
    ) -> ComponentModel:
        """Create a stack component.

        Args:
            component: The stack component to create.

        Returns:
            The created stack component.

        Raises:
            StackComponentExistsError: If a stack component with the same name
                and type is already owned by this user in this project.
        """
        return self._create_project_scoped_resource(
            resource=component,
            route=STACK_COMPONENTS,
            # TODO[Stefan]: for when the request model is ready
            # request_model=CreateStackComponentRequest,
        )

    def get_stack_component(self, component_id: UUID) -> ComponentModel:
        """Get a stack component by ID.

        Args:
            component_id: The ID of the stack component to get.

        Returns:
            The stack component.

        Raises:
            KeyError: if the stack component doesn't exist.
        """
        return self._get_resource(
            resource_id=component_id,
            route=STACK_COMPONENTS,
            resource_model=ComponentModel,
        )

    def list_stack_components(
        self,
        project_name_or_id: Union[str, UUID],
        type: Optional[str] = None,
        flavor_name: Optional[str] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
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

        Raises:
            KeyError: if the project doesn't exist.
        """
        filters = locals()
        filters.pop("self")
        return self._list_resources(
            route=STACK_COMPONENTS,
            resource_model=ComponentModel,
            **filters,
        )

    def update_stack_component(
        self,
        component: ComponentModel,
    ) -> ComponentModel:
        """Update an existing stack component.

        Args:
            component: The stack component to use for the update.

        Returns:
            The updated stack component.

        Raises:
            KeyError: if the stack component doesn't exist.
        """
        return self._update_resource(
            resource=component,
            route=STACK_COMPONENTS,
            # TODO[Stefan]: for when the request model is ready
            # request_model=UpdateComponentRequest,
        )

    def delete_stack_component(self, component_id: UUID) -> None:
        """Delete a stack component.

        Args:
            component_id: The ID of the stack component to delete.

        Raises:
            KeyError: if the stack component doesn't exist.
        """
        self._delete_resource(
            resource_id=component_id,
            route=STACK_COMPONENTS,
        )

    def get_stack_component_side_effects(
        self,
        component_id: UUID,
        run_id: UUID,
        pipeline_id: UUID,
        stack_id: UUID,
    ) -> Dict[Any, Any]:
        """Get the side effects of a stack component.

        Args:
            component_id: The ID of the stack component to get side effects for.
            run_id: The ID of the run to get side effects for.
            pipeline_id: The ID of the pipeline to get side effects for.
            stack_id: The ID of the stack to get side effects for.
        """

    # -----------------------
    # Stack component flavors
    # -----------------------

    def create_flavor(
        self,
        user_name_or_id: Union[str, UUID],
        project_name_or_id: Union[str, UUID],
        flavor: FlavorModel,
    ) -> FlavorModel:
        """Creates a new stack component flavor.

        Args:
            user_name_or_id: The stack component flavor owner.
            project_name_or_id: The project in which the stack component flavor
                is created.
            flavor: The stack component flavor to create.

        Returns:
            The newly created flavor.

        Raises:
            EntityExistsError: If a flavor with the same name and type
                is already owned by this user in this project.
        """

    def get_flavor(self, flavor_id: UUID) -> FlavorModel:
        """Get a stack component flavor by ID.

        Args:
            component_id: The ID of the stack component flavor to get.

        Returns:
            The stack component flavor.

        Raises:
            KeyError: if the stack component flavor doesn't exist.
        """

    def list_flavors(
        self,
        project_name_or_id: Union[str, UUID],
        component_type: Optional[StackComponentType] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[FlavorModel]:
        """List all stack component flavors matching the given filter criteria.

        Args:
            project_name_or_id: The ID or name of the Project to which the
                component flavors belong
            component_type: Optionally filter by type of stack component
            flavor_name: Optionally filter by flavor name
            user_name_or_id: Optionally filter by the owner
            name: Optionally filter flavors by name
            is_shared: Optionally filter out flavors by whether they are
                shared or not

        Returns:
            List of all the stack component flavors matching the given criteria.

        Raises:
            KeyError: if the project doesn't exist.
        """

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

    def create_user(self, user: UserModel) -> UserModel:
        """Creates a new user.

        Args:
            user: User to be created.

        Returns:
            The newly created user.

        Raises:
            EntityExistsError: If a user with the given name already exists.
        """
        return self._create_resource(
            resource=user,
            route=USERS,
            request_model=CreateUserRequest,
            response_model=CreateUserResponse,
        )

    def get_user(self, user_name_or_id: Union[str, UUID]) -> UserModel:
        """Gets a specific user.

        Args:
            user_name_or_id: The name or ID of the user to get.

        Returns:
            The requested user, if it was found.

        Raises:
            KeyError: If no user with the given name or ID exists.
        """
        return self._get_resource(
            resource_id=user_name_or_id,
            route=USERS,
            resource_model=UserModel,
        )
        return UserModel.parse_obj(self.get(f"{USERS}/{str(user_name_or_id)}"))

    # TODO: [ALEX] add filtering param(s)
    def list_users(self) -> List[UserModel]:
        """List all users.

        Returns:
            A list of all users.
        """
        filters = locals()
        filters.pop("self")
        return self._list_resources(
            route=USERS,
            resource_model=UserModel,
            **filters,
        )

    def update_user(self, user: UserModel) -> UserModel:
        """Updates an existing user.

        Args:
            user: The user model to use for the update.

        Returns:
            The updated user.

        Raises:
            KeyError: If no user with the given name exists.
        """
        return self._update_resource(
            resource=user,
            route=USERS,
            request_model=UpdateUserRequest,
        )

    def delete_user(self, user_name_or_id: Union[str, UUID]) -> None:
        """Deletes a user.

        Args:
            user_name_or_id: The name or ID of the user to delete.

        Raises:
            KeyError: If no user with the given ID exists.
        """
        self._delete_resource(
            resource_id=user_name_or_id,
            route=USERS,
        )

    # -----
    # Teams
    # -----

    def create_team(self, team: TeamModel) -> TeamModel:
        """Creates a new team.

        Args:
            team: The team model to create.

        Returns:
            The newly created team.
        """

    def get_team(self, team_name_or_id: Union[str, UUID]) -> TeamModel:
        """Gets a specific team.

        Args:
            team_name_or_id: Name or ID of the team to get.

        Returns:
            The requested team.

        Raises:
            KeyError: If no team with the given name or ID exists.
        """

    def list_teams(self) -> List[TeamModel]:
        """List all teams.

        Returns:
            A list of all teams.
        """

    def delete_team(self, team_name_or_id: Union[str, UUID]) -> None:
        """Deletes a team.

        Args:
            team_name_or_id: Name or ID of the team to delete.

        Raises:
            KeyError: If no team with the given ID exists.
        """

    # ---------------
    # Team membership
    # ---------------

    def get_users_for_team(
        self, team_name_or_id: Union[str, UUID]
    ) -> List[UserModel]:
        """Fetches all users of a team.

        Args:
            team_name_or_id: The name or ID of the team for which to get users.

        Returns:
            A list of all users that are part of the team.

        Raises:
            KeyError: If no team with the given ID exists.
        """

    def get_teams_for_user(
        self, user_name_or_id: Union[str, UUID]
    ) -> List[TeamModel]:
        """Fetches all teams for a user.

        Args:
            user_name_or_id: The name or ID of the user for which to get all
                teams.

        Returns:
            A list of all teams that the user is part of.

        Raises:
            KeyError: If no user with the given ID exists.
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

        Raises:
            KeyError: If the team or user does not exist.
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

        Raises:
            KeyError: If the team or user does not exist.
        """

    # -----
    # Roles
    # -----

    # TODO: consider using team_id instead
    def create_role(self, role: RoleModel) -> RoleModel:
        """Creates a new role.

        Args:
            role: The role model to create.

        Returns:
            The newly created role.

        Raises:
            EntityExistsError: If a role with the given name already exists.
        """

    # TODO: consider using team_id instead
    def get_role(self, role_name_or_id: Union[str, UUID]) -> RoleModel:
        """Gets a specific role.

        Args:
            role_name_or_id: Name or ID of the role to get.

        Returns:
            The requested role.

        Raises:
            KeyError: If no role with the given name exists.
        """

    # TODO: [ALEX] add filtering param(s)
    def list_roles(self) -> List[RoleModel]:
        """List all roles.

        Returns:
            A list of all roles.
        """

    def delete_role(self, role_name_or_id: Union[str, UUID]) -> None:
        """Deletes a role.

        Args:
            role_name_or_id: Name or ID of the role to delete.

        Raises:
            KeyError: If no role with the given ID exists.
        """

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

        Raises:
            EntityExistsError: If the role assignment already exists.
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

        Raises:
            KeyError: If the role, user, team, or project does not exists.
        """

    # --------
    # Projects
    # --------

    def create_project(self, project: ProjectModel) -> ProjectModel:
        """Creates a new project.

        Args:
            project: The project to create.

        Returns:
            The newly created project.

        Raises:
            EntityExistsError: If a project with the given name already exists.
        """
        return self._create_resource(
            resource=project,
            route=PROJECTS,
            request_model=CreateProjectRequest,
        )

    def get_project(self, project_name_or_id: Union[UUID, str]) -> ProjectModel:
        """Get an existing project by name or ID.

        Args:
            project_name_or_id: Name or ID of the project to get.

        Returns:
            The requested project.

        Raises:
            KeyError: If there is no such project.
        """
        return self._get_resource(
            resource_id=project_name_or_id,
            route=PROJECTS,
            resource_model=ProjectModel,
        )

    # TODO: [ALEX] add filtering param(s)
    def list_projects(self) -> List[ProjectModel]:
        """List all projects.

        Returns:
            A list of all projects.
        """
        filters = locals()
        filters.pop("self")
        return self._list_resources(
            route=PROJECTS,
            resource_model=ProjectModel,
            **filters,
        )

    def update_project(self, project: ProjectModel) -> ProjectModel:
        """Update an existing project.

        Args:
            project: The project to use for the update.

        Returns:
            The updated project.

        Raises:
            KeyError: if the project does not exist.
        """
        return self._update_resource(
            resource=project,
            route=PROJECTS,
            request_model=UpdateProjectRequest,
        )

    def delete_project(self, project_name_or_id: Union[str, UUID]) -> None:
        """Deletes a project.

        Args:
            project_name_or_id: Name or ID of the project to delete.

        Raises:
            KeyError: If no project with the given name exists.
        """
        self._delete_resource(
            resource_id=project_name_or_id,
            route=PROJECTS,
        )

    # ---------
    # Pipelines
    # ---------

    def create_pipeline(self, pipeline: PipelineModel) -> PipelineModel:
        """Creates a new pipeline in a project.

        Args:
            pipeline: The pipeline to create.

        Returns:
            The newly created pipeline.

        Raises:
            KeyError: if the project does not exist.
            EntityExistsError: If an identical pipeline already exists.
        """
        return self._create_project_scoped_resource(
            resource=pipeline,
            route=PIPELINES,
            request_model=CreatePipelineRequest,
        )

    def get_pipeline(self, pipeline_id: UUID) -> PipelineModel:
        """Get a pipeline with a given ID.

        Args:
            pipeline_id: ID of the pipeline.

        Returns:
            The pipeline.

        Raises:
            KeyError: if the pipeline does not exist.
        """
        return self._get_resource(
            resource_id=pipeline_id,
            route=PIPELINES,
            resource_model=PipelineModel,
        )

    def list_pipelines(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        name: Optional[str] = None,
    ) -> List[PipelineModel]:
        """List all pipelines in the project.

        Args:
            project_name_or_id: If provided, only list pipelines in this project.
            user_name_or_id: If provided, only list pipelines from this user.
            name: If provided, only list pipelines with this name.

        Returns:
            A list of pipelines.

        Raises:
            KeyError: if the project does not exist.
        """
        filters = locals()
        filters.pop("self")
        return self._list_resources(
            route=PIPELINES,
            resource_model=PipelineModel,
            **filters,
        )

    def update_pipeline(self, pipeline: PipelineModel) -> PipelineModel:
        """Updates a pipeline.

        Args:
            pipeline: The pipeline to use for the update.

        Returns:
            The updated pipeline.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """
        return self._update_resource(
            resource=pipeline,
            route=PIPELINES,
            request_model=UpdatePipelineRequest,
        )

    def delete_pipeline(self, pipeline_id: UUID) -> None:
        """Deletes a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to delete.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """
        self._delete_resource(
            resource_id=pipeline_id,
            route=PIPELINES,
        )

    # --------------
    # Pipeline steps
    # --------------

    # TODO: Note that this doesn't have a corresponding API endpoint (consider adding?)
    # TODO: Discuss whether we even need this, given that the endpoint is on
    # pipeline runs
    # TODO: [ALEX] add filtering param(s)
    def list_steps(self, pipeline_id: UUID) -> List[StepRunModel]:
        """List all steps.

        Args:
            pipeline_id: The ID of the pipeline to list steps for.

        Returns:
            A list of all steps.
        """

    # --------------
    # Pipeline runs
    # --------------

    def create_run(self, pipeline_run: PipelineRunModel) -> PipelineRunModel:
        """Creates a pipeline run.

        Args:
            pipeline_run: The pipeline run to create.

        Returns:
            The created pipeline run.

        Raises:
            EntityExistsError: If an identical pipeline run already exists.
        """

    def get_run(self, run_id: UUID) -> PipelineRunModel:
        """Gets a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            The pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """

    def get_run_dag(self, run_id: UUID) -> str:
        """Gets the DAG for a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            The DAG for the pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """

    # TODO: Figure out what exactly gets returned from this
    def get_run_component_side_effects(
        self,
        run_id: UUID,
        component_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Gets the side effects for a component in a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.
            component_id: The ID of the component to get.

        Returns:
            The side effects for the component in the pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """

    def list_runs(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        stack_id: Optional[UUID] = None,
        run_name: Optional[str] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        pipeline_id: Optional[UUID] = None,
        unlisted: bool = False,
    ) -> List[PipelineRunModel]:
        """Gets all pipeline runs.

        Args:
            project_name_or_id: If provided, only return runs for this project.
            stack_id: If provided, only return runs for this stack.
            run_name: Run name if provided
            user_name_or_id: If provided, only return runs for this user.
            pipeline_id: If provided, only return runs for this pipeline.
            unlisted: If True, only return unlisted runs that are not
                associated with any pipeline (filter by `pipeline_id==None`).

        Returns:
            A list of all pipeline runs.
        """

    def update_run(self, run: PipelineRunModel) -> PipelineRunModel:
        """Updates a pipeline run.

        Args:
            run: The pipeline run to use for the update.

        Returns:
            The updated pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """

    def delete_run(self, run_id: UUID) -> None:
        """Deletes a pipeline run.

        Args:
            run_id: The ID of the pipeline run to delete.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """

    # ------------------
    # Pipeline run steps
    # ------------------

    def get_run_step(self, step_id: UUID) -> StepRunModel:
        """Get a step by ID.

        Args:
            step_id: The ID of the step to get.

        Returns:
            The step.

        Raises:
            KeyError: if the step doesn't exist.
        """

    def get_run_step_outputs(self, step_id: UUID) -> Dict[str, ArtifactModel]:
        """Get a list of outputs for a specific step.

        Args:
            step_id: The id of the step to get outputs for.

        Returns:
            A dict mapping artifact names to the output artifacts for the step.
        """

    def get_run_step_inputs(self, step_id: UUID) -> Dict[str, ArtifactModel]:
        """Get a list of inputs for a specific step.

        Args:
            step_id: The id of the step to get inputs for.

        Returns:
            A dict mapping artifact names to the input artifacts for the step.
        """

    def get_run_step_status(self, step_id: UUID) -> ExecutionStatus:
        """Gets the execution status of a single step.

        Args:
            step_id: The ID of the step to get the status for.

        Returns:
            ExecutionStatus: The status of the step.
        """

    def list_run_steps(self, run_id: UUID) -> List[StepRunModel]:
        """Gets all steps in a pipeline run.

        Args:
            run_id: The ID of the pipeline run for which to list runs.

        Returns:
            A mapping from step names to step models for all steps in the run.
        """

    # =======================
    # Internal helper methods
    # =======================

    def _get_auth_token(self) -> str:
        """Get the authentication token for the REST store.

        Returns:
            The authentication token.
        """
        if self._api_token is None:
            self._api_token = self._handle_response(
                requests.post(
                    self.url + VERSION_1 + LOGIN,
                    data={
                        "username": self.config.username,
                        "password": self.config.password,
                    },
                )
            )["access_token"]
        return self._api_token

    @property
    def session(self) -> requests.Session:
        """Authenticate to the ZenML server."""
        if self._session is None:
            self._session = requests.Session()
            token = self._get_auth_token()
            self._session.headers.update({"Authorization": "Bearer " + token})
            logger.debug("Authenticated to ZenML server.")
        return self._session

    def _handle_response(self, response: requests.Response) -> Json:
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
        if response.status_code >= 200 and response.status_code < 300:
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
                f"{response.status_code} Client Error: Unauthorized request to URL {response.url}: {response.json().get('detail')}"
            )
        elif response.status_code == 404:
            if "DoesNotExistException" not in response.text:
                raise KeyError(*response.json().get("detail", (response.text,)))
            message = ": ".join(response.json().get("detail", (response.text,)))
            raise DoesNotExistException(message)
        elif response.status_code == 409:
            if "StackComponentExistsError" in response.text:
                raise StackComponentExistsError(
                    *response.json().get("detail", (response.text,))
                )
            elif "StackExistsError" in response.text:
                raise StackExistsError(
                    *response.json().get("detail", (response.text,))
                )
            elif "EntityExistsError" in response.text:
                raise EntityExistsError(
                    *response.json().get("detail", (response.text,))
                )
            else:
                raise ValueError(
                    *response.json().get("detail", (response.text,))
                )
        elif response.status_code == 422:
            raise RuntimeError(*response.json().get("detail", (response.text,)))
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
        """
        params = {k: str(v) for k, v in params.items()} if params else {}
        try:
            return self._handle_response(
                self.session.request(method, url, params=params, **kwargs)
            )
        except AuthorizationException:
            # The authentication token could have expired; refresh it and try
            # again
            self._session = None
            return self._handle_response(
                self.session.request(method, url, **kwargs)
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
        return self._request(
            "GET", self.url + VERSION_1 + path, params=params, **kwargs
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
        return self._request(
            "DELETE", self.url + VERSION_1 + path, params=params, **kwargs
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
        return self._request(
            "POST",
            self.url + VERSION_1 + path,
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
        return self._request(
            "PUT",
            self.url + VERSION_1 + path,
            data=body.json(),
            params=params,
            **kwargs,
        )

    def _create_resource(
        self,
        resource: AnyModel,
        route: str,
        request_model: Optional[Type[BaseModel]] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> AnyModel:
        """Create a new resource.

        Args:
            resource: The resource to create.
            route: The resource REST API route to use.
            request_model: Optional model to use to serialize the request body.
                If not provided, the resource object itself will be used.
            response_model: Optional model to use to deserialize the response
                body. If not provided, the resource class itself will be used.

        Returns:
            The created resource.
        """
        request = resource
        if request_model is not None:
            request = request_model.from_model(resource)
        response_body = self.post(f"{route}/", body=request)
        if response_model is not None:
            response = response_model.parse_obj(response_body)
            created_resource = cast(AnyModel, response.to_model())
        else:
            created_resource = resource.parse_obj(response_body)
        return created_resource

    def _create_project_scoped_resource(
        self,
        resource: AnyModel,
        route: str,
        request_model: Optional[Type[BaseModel]] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> AnyModel:
        """Create a new project scoped resource.

        Args:
            resource: The resource to create.
            route: The resource REST API route to use.
            request_model: Optional model to use to serialize the request body.
                If not provided, the resource object itself will be used.
            response_model: Optional model to use to deserialize the response
                body. If not provided, the resource class itself will be used.

        Returns:
            The created resource.
        """
        project = getattr(resource, "project", None)

        # TODO: this should be guaranteed through inheritance
        assert project is not None and isinstance(project, UUID), (
            f"Project scoped resource '{type(resource)}' must have a UUID "
            f"'project' attribute"
        )
        return self._create_resource(
            resource=resource,
            route=f"{PROJECTS}/{str(project)}{route}",
            request_model=request_model,
            response_model=response_model,
        )

    def _get_resource(
        self,
        resource_id: Union[str, UUID],
        route: str,
        resource_model: Type[AnyModel],
    ) -> AnyModel:
        """Retrieve a single resource.

        Args:
            resource_id: The ID of the resource to retrieve.
            route: The resource REST API route to use.
            resource_model: Model to use to serialize the response body.

        Returns:
            The retrieved resource.
        """
        body = self.get(f"{route}/{str(resource_id)}")
        return resource_model.parse_obj(body)

    def _list_resources(
        self,
        route: str,
        resource_model: Type[AnyModel],
        **filters: Any,
    ) -> List[AnyModel]:
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
        body = self.get(f"{route}/", params=params)
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [resource_model.parse_obj(entry) for entry in body]

    def _update_resource(
        self,
        resource: AnyModel,
        route: str,
        request_model: Optional[Type[BaseModel]] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> AnyModel:
        """Update an existing resource.

        Args:
            resource: The resource to update.
            route: The resource REST API route to use.
            request_model: Optional model to use to serialize the request body.
                If not provided, the resource object itself will be used.
            response_model: Optional model to use to deserialize the response
                body. If not provided, the resource class itself will be used.

        Returns:
            The updated resource.
        """
        resource_id = getattr(resource, "id", None)

        # TODO: this should be guaranteed through inheritance
        assert resource_id is not None and isinstance(
            resource_id, UUID
        ), f"Resource '{type(resource)}' must have a UUID 'id' attribute"
        request = resource
        if request_model is not None:
            request = request_model.from_model(resource)
        response_body = self.put(f"{route}/{str(resource_id)}", body=request)
        if response_model is not None:
            response = response_model.parse_obj(response_body)
            updated_resource = cast(AnyModel, response.to_model())
        else:
            updated_resource = resource.parse_obj(response_body)

        return updated_resource

    def _delete_resource(
        self, resource_id: Union[str, UUID], route: str
    ) -> None:
        """Delete a resource.

        Args:
            resource_id: The ID of the resource to delete.
            route: The resource REST API route to use.
        """
        self.delete(f"{route}/{str(resource_id)}")
