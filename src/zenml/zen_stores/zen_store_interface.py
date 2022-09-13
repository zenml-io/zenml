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
"""ZenML Store interface."""
from abc import ABC, abstractmethod
from pathlib import Path, PurePath
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from zenml.config.store_config import StoreConfiguration
from zenml.enums import ExecutionStatus, StackComponentType
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


class ZenStoreInterface(ABC):
    """ZenML store interface.

    All ZenML stores must implement the methods in this interface.

    The methods in this interface are organized in the following way:

     * they are grouped into categories based on the type of resource
       that they operate on (e.g. stacks, stack components, etc.)

     * each category has a set of CRUD methods (create, read, update, delete)
       that operate on the resources in that category. The order of the methods
       in each category should be:

       * create/register methods - store a new resource. These methods
         should fill in generated fields (e.g. UUIDs, creation timestamps) in
         the resource and return the updated resource.
       * get methods - retrieve a single existing resource identified by a
         unique key or identifier from the store. These methods should always
         return a resource and raise an exception if the resource does not exist.
       * list methods - retrieve a list of resources from the store. These
         methods should accept a set of filter parameters that can be used to
         filter the list of resources retrieved from the store.
       * update methods - update an existing resource in the store. These
         methods should expect the updated resource to be correctly identified
         by its unique key or identifier and raise an exception if the resource
         does not exist.
       * delete methods - delete an existing resource from the store. These
         methods should expect the resource to be correctly identified by its
         unique key or identifier. If the resource does not exist,
         an exception should be raised.

    Best practices for implementing and keeping this interface clean and easy to
    maintain and extend:

      * keep methods organized by resource type and ordered by CRUD operation
      * for resources with multiple keys, don't implement multiple get or list
      methods here if the same functionality can be achieved by a single get or
      list method. Instead, implement them in the BaseZenStore class and have
      them call the generic get or list method in this interface.
      * keep the logic required to convert between ZenML domain Model classes
      and internal store representations outside the ZenML domain Model classes
      * methods for resources that have two or more unique keys (e.g. a Project
      is uniquely identified by its name as well as its UUID) should reflect
      that in the method variants and/or method arguments:
        * methods that take in a resource identifier as argument should accept
        all variants of the identifier (e.g. `project_name_or_uuid` for methods
        that get/list/update/delete Projects)
        * if a compound key is involved, separate get methods should be
        implemented (e.g. `get_pipeline` to get a pipeline by ID and
        `get_pipeline_in_project` to get a pipeline by its name and the ID of
        the project it belongs to)
      * methods for resources that are scoped as children of other resources
      (e.g. a Stack is always owned by a Project) should reflect the
      key(s) of the parent resource in the provided methods and method
      arguments:
        * create methods should take the parent resource UUID(s) as an argument
        (e.g. `create_stack` takes in the project ID)
        * get methods should be provided to retrieve a resource by the compound
        key that includes the parent resource key(s)
        * list methods should feature optional filter arguments that reflect
        the parent resource key(s)
    """

    # ---------------------------------
    # Initialization and configuration
    # ---------------------------------

    @abstractmethod
    def _initialize(self) -> None:
        """Initialize the store.

        This method is called immediately after the store is created. It should
        be used to set up the backend (database, connection etc.).
        """

    @staticmethod
    @abstractmethod
    def get_path_from_url(url: str) -> Optional[Path]:
        """Get the path from a URL, if it points or is backed by a local file.

        Args:
            url: The URL to get the path from.

        Returns:
            The local path backed by the URL, or None if the URL is not backed
            by a local file or directory
        """

    @staticmethod
    @abstractmethod
    def get_local_url(path: str) -> str:
        """Get a local URL for a given local path.

        Args:
            path: the path string to build a URL out of.

        Returns:
            Url pointing to the path for the store type.
        """

    @staticmethod
    @abstractmethod
    def validate_url(url: str) -> str:
        """Check if the given url is valid.

        The implementation should raise a ValueError if the url is invalid.

        Args:
            url: The url to check.

        Returns:
            The modified url, if it is valid.
        """

    @classmethod
    @abstractmethod
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

    # ------------
    # TFX Metadata
    # ------------

    @abstractmethod
    def get_metadata_config(self) -> str:
        """Get the TFX metadata config of this ZenStore.

        Returns:
            The TFX metadata config of this ZenStore.
        """

    # ------
    # Stacks
    # ------

    @abstractmethod
    def register_stack(
        self,
        user_name_or_id: Union[str, UUID],
        project_name_or_id: Union[str, UUID],
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

    @abstractmethod
    def get_stack(self, stack_id: UUID) -> StackModel:
        """Get a stack by its unique ID.

        Args:
            stack_id: The ID of the stack to get.

        Returns:
            The stack with the given ID.

        Raises:
            KeyError: if the stack doesn't exist.
        """

    @abstractmethod
    def list_stacks(
        self,
        project_name_or_id: Union[str, UUID],
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

    @abstractmethod
    def update_stack(
        self,
        stack_id: UUID,
        stack: StackModel,
    ) -> StackModel:
        """Update a stack.

        Args:
            stack_id: The id of the stack that is to be updated.
            stack: The stack to use for the update.

        Returns:
            The updated stack.

        Raises:
            KeyError: if the stack doesn't exist.
        """

    @abstractmethod
    def delete_stack(self, stack_id: UUID) -> None:
        """Delete a stack.

        Args:
            stack_id: The ID of the stack to delete.

        Raises:
            KeyError: if the stack doesn't exist.
        """

    # ----------------
    # Stack components
    # ----------------

    @abstractmethod
    def register_stack_component(
        self,
        user_name_or_id: Union[str, UUID],
        project_name_or_id: Union[str, UUID],
        component: ComponentModel,
    ) -> ComponentModel:
        """Create a stack component.

        Args:
            user_name_or_id: The stack component owner.
            project_name_or_id: The project the stack component is created in.
            component: The stack component to create.

        Returns:
            The created stack component.

        Raises:
            StackComponentExistsError: If a stack component with the same name
                and type is already owned by this user in this project.
        """

    @abstractmethod
    def get_stack_component(self, component_id: UUID) -> ComponentModel:
        """Get a stack component by ID.

        Args:
            component_id: The ID of the stack component to get.

        Returns:
            The stack component.

        Raises:
            KeyError: if the stack component doesn't exist.
        """

    @abstractmethod
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

    @abstractmethod
    def update_stack_component(
        self,
        component_id: UUID,
        component: ComponentModel,
    ) -> ComponentModel:
        """Update an existing stack component.

        Args:
            component_id: The ID of the stack component to update.
            component: The stack component to use for the update.

        Returns:
            The updated stack component.

        Raises:
            KeyError: if the stack component doesn't exist.
        """

    @abstractmethod
    def delete_stack_component(self, component_id: UUID) -> None:
        """Delete a stack component.

        Args:
            component_id: The ID of the stack component to delete.

        Raises:
            KeyError: if the stack component doesn't exist.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def get_flavor(self, flavor_id: UUID) -> FlavorModel:
        """Get a stack component flavor by ID.

        Args:
            component_id: The ID of the stack component flavor to get.

        Returns:
            The stack component flavor.

        Raises:
            KeyError: if the stack component flavor doesn't exist.
        """

    @abstractmethod
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
    @abstractmethod
    def active_user_name(self) -> str:
        """Gets the active username.

        Returns:
            The active username.
        """

    @abstractmethod
    def create_user(self, user: UserModel) -> UserModel:
        """Creates a new user.

        Args:
            user: User to be created.

        Returns:
            The newly created user.

        Raises:
            EntityExistsError: If a user with the given name already exists.
        """

    @abstractmethod
    def get_user(self, user_name_or_id: Union[str, UUID]) -> UserModel:
        """Gets a specific user.

        Args:
            user_name_or_id: The name or ID of the user to get.

        Returns:
            The requested user, if it was found.

        Raises:
            KeyError: If no user with the given name or ID exists.
        """

    # TODO: [ALEX] add filtering param(s)
    @abstractmethod
    def list_users(self) -> List[UserModel]:
        """List all users.

        Returns:
            A list of all users.
        """

    @abstractmethod
    def update_user(
        self, user_name_or_id: Union[str, UUID], user: UserModel
    ) -> UserModel:
        """Updates an existing user.

        Args:
            user_name_or_id: The name or ID of the user to update.
            user: The user model to use for the update.

        Returns:
            The updated user.

        Raises:
            KeyError: If no user with the given name exists.
        """

    @abstractmethod
    def delete_user(self, user_name_or_id: Union[str, UUID]) -> None:
        """Deletes a user.

        Args:
            user_name_or_id: The name or ID of the user to delete.

        Raises:
            KeyError: If no user with the given ID exists.
        """

    # -----
    # Teams
    # -----

    @abstractmethod
    def create_team(self, team: TeamModel) -> TeamModel:
        """Creates a new team.

        Args:
            team: The team model to create.

        Returns:
            The newly created team.
        """

    @abstractmethod
    def get_team(self, team_name_or_id: Union[str, UUID]) -> TeamModel:
        """Gets a specific team.

        Args:
            team_name_or_id: Name or ID of the team to get.

        Returns:
            The requested team.

        Raises:
            KeyError: If no team with the given name or ID exists.
        """

    @abstractmethod
    def list_teams(self) -> List[TeamModel]:
        """List all teams.

        Returns:
            A list of all teams.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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
    @abstractmethod
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
    @abstractmethod
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
    @abstractmethod
    def list_roles(self) -> List[RoleModel]:
        """List all roles.

        Returns:
            A list of all roles.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def create_project(self, project: ProjectModel) -> ProjectModel:
        """Creates a new project.

        Args:
            project: The project to create.

        Returns:
            The newly created project.

        Raises:
            EntityExistsError: If a project with the given name already exists.
        """

    @abstractmethod
    def get_project(self, project_name_or_id: Union[UUID, str]) -> ProjectModel:
        """Get an existing project by name or ID.

        Args:
            project_name_or_id: Name or ID of the project to get.

        Returns:
            The requested project.

        Raises:
            KeyError: If there is no such project.
        """

    # TODO: [ALEX] add filtering param(s)
    @abstractmethod
    def list_projects(self) -> List[ProjectModel]:
        """List all projects.

        Returns:
            A list of all projects.
        """

    @abstractmethod
    def update_project(
        self, project_name_or_id: Union[str, UUID], project: ProjectModel
    ) -> ProjectModel:
        """Update an existing project.

        Args:
            project_name_or_id: Name or ID of the project to update.
            project: The project to use for the update.

        Returns:
            The updated project.

        Raises:
            KeyError: if the project does not exist.
        """

    @abstractmethod
    def delete_project(self, project_name_or_id: Union[str, UUID]) -> None:
        """Deletes a project.

        Args:
            project_name_or_id: Name or ID of the project to delete.

        Raises:
            KeyError: If no project with the given name exists.
        """

    # ------------
    # Repositories
    # ------------

    # ---------
    # Pipelines
    # ---------

    @abstractmethod
    def create_pipeline(
        self, project_name_or_id: Union[str, UUID], pipeline: PipelineModel
    ) -> PipelineModel:
        """Creates a new pipeline in a project.

        Args:
            project_name_or_id: ID of the project to create the pipeline in.
            pipeline: The pipeline to create.

        Returns:
            The newly created pipeline.

        Raises:
            KeyError: if the project does not exist.
            EntityExistsError: If an identical pipeline already exists.
        """

    @abstractmethod
    def get_pipeline(self, pipeline_id: UUID) -> PipelineModel:
        """Get a pipeline with a given ID.

        Args:
            pipeline_id: ID of the pipeline.

        Returns:
            The pipeline.

        Raises:
            KeyError: if the pipeline does not exist.
        """

    @abstractmethod
    def get_pipeline_in_project(
        self, pipeline_name: str, project_name_or_id: Union[str, UUID]
    ) -> PipelineModel:
        """Get a pipeline with a given name in a project.

        Args:
            pipeline_name: Name of the pipeline.
            project_name_or_id: ID of the project.

        Returns:
            The pipeline.

        Raises:
            KeyError: if the pipeline does not exist.
        """

    @abstractmethod
    def list_pipelines(
        self,
        project_name_or_id: Optional[Union[str, UUID]],
    ) -> List[PipelineModel]:
        """List all pipelines in the project.

        Args:
            project_name_or_id: If provided, only list pipelines in this project.

        Returns:
            A list of pipelines.

        Raises:
            KeyError: if the project does not exist.
        """

    @abstractmethod
    def update_pipeline(
        self, pipeline_id: UUID, pipeline: PipelineModel
    ) -> PipelineModel:
        """Updates a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to update.
            pipeline: The pipeline to use for the update.

        Returns:
            The updated pipeline.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """

    @abstractmethod
    def delete_pipeline(self, pipeline_id: UUID) -> None:
        """Deletes a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to delete.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """

    # --------------
    # Pipeline steps
    # --------------

    # TODO: change into an abstract method
    # TODO: Note that this doesn't have a corresponding API endpoint (consider adding?)
    # TODO: Discuss whether we even need this, given that the endpoint is on
    # pipeline runs
    # TODO: [ALEX] add filtering param(s)
    @abstractmethod
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

    @abstractmethod
    def create_run(self, pipeline_run: PipelineRunModel) -> PipelineRunModel:
        """Creates a pipeline run.

        Args:
            pipeline_run: The pipeline run to create.

        Returns:
            The created pipeline run.

        Raises:
            EntityExistsError: If an identical pipeline run already exists.
        """

    @abstractmethod
    def get_run(self, run_id: UUID) -> PipelineRunModel:
        """Gets a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            The pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """

    @abstractmethod
    def get_run_in_project(
        self, run_name: str, project_name_or_id: Union[str, UUID]
    ) -> PipelineRunModel:
        """Get a pipeline run with a given name in a project.

        Args:
            run_name: Name of the pipeline run.
            project_name_or_id: ID or name of the project.

        Returns:
            The pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """

    # TODO: figure out args and output for this
    @abstractmethod
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
    @abstractmethod
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

    @abstractmethod
    def list_runs(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        stack_id: Optional[UUID] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        pipeline_id: Optional[UUID] = None,
        unlisted: bool = False,
    ) -> List[PipelineRunModel]:
        """Gets all pipeline runs.

        Args:
            project_name_or_id: If provided, only return runs for this project.
            stack_id: If provided, only return runs for this stack.
            user_name_or_id: If provided, only return runs for this user.
            pipeline_id: If provided, only return runs for this pipeline.
            unlisted: If True, only return unlisted runs that are not
                associated with any pipeline (filter by `pipeline_id==None`).

        Returns:
            A list of all pipeline runs.
        """

    @abstractmethod
    def update_run(
        self, run_id: UUID, run: PipelineRunModel
    ) -> PipelineRunModel:
        """Updates a pipeline run.

        Args:
            run_id: The ID of the pipeline run to update.
            run: The pipeline run to use for the update.

        Returns:
            The updated pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """

    @abstractmethod
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

    @abstractmethod
    def get_run_step(self, step_id: UUID) -> StepRunModel:
        """Get a step by ID.

        Args:
            step_id: The ID of the step to get.

        Returns:
            The step.

        Raises:
            KeyError: if the step doesn't exist.
        """

    @abstractmethod
    def get_run_step_outputs(self, step_id: UUID) -> Dict[str, ArtifactModel]:
        """Get a list of outputs for a specific step.

        Args:
            step_id: The id of the step to get outputs for.

        Returns:
            A dict mapping artifact names to the output artifacts for the step.
        """

    @abstractmethod
    def get_run_step_inputs(self, step_id: UUID) -> Dict[str, ArtifactModel]:
        """Get a list of inputs for a specific step.

        Args:
            step_id: The id of the step to get inputs for.

        Returns:
            A dict mapping artifact names to the input artifacts for the step.
        """

    @abstractmethod
    def get_run_step_status(self, step_id: UUID) -> ExecutionStatus:
        """Gets the execution status of a single step.

        Args:
            step_id: The ID of the step to get the status for.

        Returns:
            ExecutionStatus: The status of the step.
        """

    @abstractmethod
    def list_run_steps(self, run_id: UUID) -> List[StepRunModel]:
        """Gets all steps in a pipeline run.

        Args:
            run_id: The ID of the pipeline run for which to list runs.

        Returns:
            A mapping from step names to step models for all steps in the run.
        """
