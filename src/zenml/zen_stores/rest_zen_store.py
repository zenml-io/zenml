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
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, Union, cast
from uuid import UUID

import requests
from ml_metadata.proto import metadata_store_pb2
from pydantic import BaseModel

from zenml.config.store_config import StoreConfiguration
from zenml.constants import (
    FLAVORS,
    PIPELINE_RUNS,
    PROJECTS,
    ROLE_ASSIGNMENTS,
    ROLES,
    STACK_COMPONENTS,
    STACK_CONFIGURATIONS,
    STACKS,
    STACKS_EMPTY,
    TEAMS,
    USERS,
)
from zenml.enums import ExecutionStatus, StackComponentType, StoreType
from zenml.exceptions import (
    DoesNotExistException,
    EntityExistsError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.logger import get_logger
from zenml.models import (
    ComponentModel,
    FlavorModel,
    PipelineRunModel,
    ProjectModel,
    RoleModel,
    RoleAssignmentModel,
    StackModel,
    TeamModel,
    UserModel,
)
from zenml.post_execution.artifact import ArtifactView
from zenml.post_execution.pipeline import PipelineView
from zenml.post_execution.pipeline_run import PipelineRunView
from zenml.post_execution.step import StepView
from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)

# type alias for possible json payloads (the Anys are recursive Json instances)
Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


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

    def _initialize(self) -> None:
        """Initialize the REST store."""
        # try to connect to the server to validate the configuration
        self._handle_response(
            requests.get(self.url + "/", auth=self._get_authentication())
        )

    def _initialize_database(self) -> None:
        """Initialize the database."""
        # don't do anything for a REST store

    # Static methods:

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

    # Public Interface:

    @property
    def stacks_empty(self) -> bool:
        """Check if the store is empty (no stacks are configured).

        The implementation of this method should check if the store is empty
        without having to load all the stacks from the persistent storage.

        Returns:
            True, if the store is empty, False otherwise.

        Raises:
            ValueError: if the response is not a boolean.
        """
        empty = self.get(STACKS_EMPTY)
        if not isinstance(empty, bool):
            raise ValueError(
                f"Bad API Response. Expected boolean, got:\n{empty}"
            )
        return empty

    def get_stack_configuration(
        self, name: str
    ) -> Dict[StackComponentType, str]:
        """Fetches a stack configuration by name.

        Args:
            name: The name of the stack to fetch.

        Returns:
            Dict[StackComponentType, str] for the requested stack name.
        """
        return self._parse_stack_configuration(
            self.get(f"{STACK_CONFIGURATIONS}/{name}")
        )

    @property
    def stack_configurations(self) -> Dict[str, Dict[StackComponentType, str]]:
        """Configurations for all stacks registered in this stack store.

        Returns:
            Dictionary mapping stack names to Dict[StackComponentType, str]'s

        Raises:
            ValueError: If the API response is not a dict.
        """
        body = self.get(STACK_CONFIGURATIONS)
        if not isinstance(body, dict):
            raise ValueError(
                f"Bad API Response. Expected dict, got {type(body)}"
            )
        return {
            key: self._parse_stack_configuration(value)
            for key, value in body.items()
        }

    def get_stack_component_types(self) -> List[str]:
        """Fetches all available stack component types.

        Returns:
            List of available stack component types.
        """
        return NotImplementedError

    @property
    def stack_component_types(self) -> List[str]:
        """List of stack component types.

        Returns:
            List of stack component types.
        """
        return NotImplementedError

    # Private interface implementations:

    def _get_tfx_metadata_config(
        self,
    ) -> Union[
        metadata_store_pb2.ConnectionConfig,
        metadata_store_pb2.MetadataStoreClientConfig,
    ]:
        """Get the TFX metadata config of this ZenStore.

        Returns:
            The TFX metadata config of this ZenStore.
        """
        pass  # TODO

    def _register_stack_component(
        self,
        component: ComponentModel,
    ) -> None:
        """Register a stack component.

        Args:
            component: The component to register.
        """
        self.post(STACK_COMPONENTS, body=component)

    def _update_stack_component(
        self,
        name: str,
        component_type: StackComponentType,
        component: ComponentModel,
    ) -> Dict[str, str]:
        """Update a stack component.

        Args:
            name: The original name of the stack component.
            component_type: The type of the stack component to update.
            component: The new component to update with.

        Returns:
            The updated component.

        Raises:
            ValueError: in cases of a bad API response.
        """
        body = self.put(
            f"{STACK_COMPONENTS}/{component_type}/{name}", body=component
        )
        if isinstance(body, dict):
            return cast(Dict[str, str], body)
        else:
            raise ValueError(
                f"Bad API Response. Expected dict, got {type(body)}"
            )

    def _deregister_stack(self, name: str) -> None:
        """Delete a stack from storage.

        Args:
            name: The name of the stack to be deleted.
        """
        self.delete(f"{STACKS}/{name}")

    def _save_stack(
        self,
        name: str,
        stack_configuration: Dict[StackComponentType, str],
    ) -> None:
        """Add a stack to storage.

        Args:
            name: The name to save the stack as.
            stack_configuration: Dict[StackComponentType, str] to persist.

        Raises:
            NotImplementedError: always.
        """
        raise NotImplementedError

    # Custom implementations:

    @property
    def stacks(self) -> List[StackModel]:
        """All stacks registered in this repository.

        Returns:
            List[StackModel] of all stacks registered in this repository.

        Raises:
            ValueError: If the API response is not a list of stacks.
        """
        body = self.get(STACKS)
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [StackModel.parse_obj(s) for s in body]

    def get_stack(self, name: str) -> StackModel:
        """Fetch a stack by name.

        Args:
            name: The name of the stack to retrieve.

        Returns:
            StackModel instance if the stack exists.
        """
        return StackModel.parse_obj(self.get(f"{STACKS}/{name}"))

    def _register_stack(self, stack: StackModel) -> None:
        """Register a stack and its components.

        If any of the stacks' components aren't registered in the stack store
        yet, this method will try to register them as well.

        Args:
            stack: The stack to register.
        """
        self.post(STACKS, stack)

    def _update_stack(self, name: str, stack: StackModel) -> None:
        """Update a stack and its components.

        If any of the stack's components aren't registered in the stack store
        yet, this method will try to register them as well.

        Args:
            name: The original name of the stack.
            stack: The new stack to use in the update.
        """
        self.put(f"{STACKS}/{name}", body=stack)
        if name != stack.name:
            self.deregister_stack(name)

    def get_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> ComponentModel:
        """Get a registered stack component.

        Args:
            component_type: The type of the component to retrieve.
            name: The name of the component to retrieve.

        Returns:
            ComponentWrapper instance if the component exists.
        """
        return ComponentModel.parse_obj(
            self.get(f"{STACK_COMPONENTS}/{component_type}/{name}")
        )

    def get_stack_components(
        self, component_type: StackComponentType
    ) -> List[ComponentModel]:
        """Fetches all registered stack components of the given type.

        Args:
            component_type: StackComponentType to list members of

        Returns:
            A list of StackComponentConfiguration instances.

        Raises:
            ValueError: If the API response is not a list of components.
        """
        body = self.get(f"{STACK_COMPONENTS}/{component_type}")
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [ComponentModel.parse_obj(c) for c in body]

    def deregister_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> None:
        """Deregisters a stack component.

        Args:
            component_type: The type of the component to deregister.
            name: The name of the component to deregister.
        """
        self.delete(f"{STACK_COMPONENTS}/{component_type}/{name}")

    # User, project and role management

    @property
    def active_user_name(self) -> str:
        """Gets the active username.

        Returns:
            The active username.
        """
        return self.config.username

    @property
    def users(self) -> List[UserModel]:
        """All registered users.

        Returns:
            A list of all registered users.

        Raises:
            ValueError: In case of a bad API response.
        """
        body = self.get(USERS)
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [UserModel.parse_obj(user_dict) for user_dict in body]

    def _get_user(self, user_name: str) -> UserModel:
        """Get a specific user by name.

        Args:
            user_name: Name of the user to get.

        Returns:
            The requested user, if it was found.
        """
        return UserModel.parse_obj(self.get(f"{USERS}/{user_name}"))

    def _create_user(self, user_name: str) -> UserModel:
        """Creates a new user.

        Args:
            user_name: Unique username.

        Returns:
            The newly created user.
        """
        user = UserModel(name=user_name)
        return UserModel.parse_obj(self.post(USERS, body=user))

    def _delete_user(self, user_name: str) -> None:
        """Deletes a user.

        Args:
            user_name: Name of the user to delete.
        """
        self.delete(f"{USERS}/{user_name}")

    @property
    def teams(self) -> List[TeamModel]:
        """All registered teams.

        Returns:
            A list of all registered teams.

        Raises:
            ValueError: In case of a bad API response.
        """
        body = self.get(TEAMS)
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [TeamModel.parse_obj(team_dict) for team_dict in body]

    def _get_team(self, team_name: str) -> TeamModel:
        """Gets a specific team.

        Args:
            team_name: Name of the team to get.

        Returns:
            The requested team.
        """
        return TeamModel.parse_obj(self.get(f"{TEAMS}/{team_name}"))

    def _create_team(self, team_name: str) -> TeamModel:
        """Creates a new team.

        Args:
            team_name: Unique team name.

        Returns:
            The newly created team.
        """
        team = TeamModel(name=team_name)
        return TeamModel.parse_obj(self.post(TEAMS, body=team))

    def _delete_team(self, team_name: str) -> None:
        """Deletes a team.

        Args:
            team_name: Name of the team to delete.
        """
        self.delete(f"{TEAMS}/{team_name}")

    def add_user_to_team(self, team_name: str, user_name: str) -> None:
        """Adds a user to a team.

        Args:
            team_name: Name of the team.
            user_name: Name of the user.
        """
        user = UserModel(name=user_name)
        self.post(f"{TEAMS}/{team_name}/users", user)

    def remove_user_from_team(self, team_name: str, user_name: str) -> None:
        """Removes a user from a team.

        Args:
            team_name: Name of the team.
            user_name: Name of the user.
        """
        self.delete(f"{TEAMS}/{team_name}/users/{user_name}")

    @property
    def projects(self) -> List[ProjectModel]:
        """All registered projects.

        Returns:
            A list of all registered projects.

        Raises:
            ValueError: In case of a bad API response.
        """
        body = self.get(PROJECTS)
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [ProjectModel.parse_obj(project_dict) for project_dict in body]

    def _get_project(self, project_name: str) -> ProjectModel:
        """Get an existing project by name.

        Args:
            project_name: Name of the project to get.

        Returns:
            The requested project if one was found.
        """
        return ProjectModel.parse_obj(self.get(f"{PROJECTS}/{project_name}"))

    def _create_project(
        self, project_name: str, description: Optional[str] = None
    ) -> ProjectModel:
        """Creates a new project.

        Args:
            project_name: Unique project name.
            description: Optional project description.

        Returns:
            The newly created project.
        """
        project = ProjectModel(name=project_name, description=description)
        return ProjectModel.parse_obj(self.post(PROJECTS, body=project))

    def _delete_project(self, project_name: str) -> None:
        """Deletes a project.

        Args:
            project_name: Name of the project to delete.
        """
        self.delete(f"{PROJECTS}/{project_name}")

    @property
    def roles(self) -> List[RoleModel]:
        """All registered roles.

        Returns:
            A list of all registered roles.

        Raises:
            ValueError: In case of a bad API response.
        """
        body = self.get(ROLES)
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [RoleModel.parse_obj(role_dict) for role_dict in body]

    @property
    def role_assignments(self) -> List[RoleAssignmentModel]:
        """All registered role assignments.

        Returns:
            A list of all registered role assignments.

        Raises:
            ValueError: In case of a bad API response.
        """
        body = self.get(ROLE_ASSIGNMENTS)
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [
            RoleAssignmentModel.parse_obj(assignment_dict)
            for assignment_dict in body
        ]

    def _get_role(self, role_name: str) -> RoleModel:
        """Gets a specific role.

        Args:
            role_name: Name of the role to get.

        Returns:
            The requested role.
        """
        return RoleModel.parse_obj(self.get(f"{ROLES}/{role_name}"))

    def _create_role(self, role_name: str) -> RoleModel:
        """Creates a new role.

        Args:
            role_name: Unique role name.

        Returns:
            The newly created role.
        """
        role = RoleModel(name=role_name)
        return RoleModel.parse_obj(self.post(ROLES, body=role))

    def _delete_role(self, role_name: str) -> None:
        """Deletes a role.

        Args:
            role_name: Name of the role to delete.
        """
        self.delete(f"{ROLES}/{role_name}")

    def assign_role(
        self,
        role_name: str,
        entity_name: str,
        project_name: Optional[str] = None,
        is_user: bool = True,
    ) -> None:
        """Assigns a role to a user or team.

        Args:
            role_name: Name of the role to assign.
            entity_name: User or team name.
            project_name: Optional project name.
            is_user: Boolean indicating whether the given `entity_name` refers
                to a user.
        """
        data = {
            "role_name": role_name,
            "entity_name": entity_name,
            "project_name": project_name,
            "is_user": is_user,
        }
        self._handle_response(
            requests.post(
                self.url + ROLE_ASSIGNMENTS,
                json=data,
                auth=self._get_authentication(),
            )
        )

    def revoke_role(
        self,
        role_name: str,
        entity_name: str,
        project_name: Optional[str] = None,
        is_user: bool = True,
    ) -> None:
        """Revokes a role from a user or team.

        Args:
            role_name: Name of the role to revoke.
            entity_name: User or team name.
            project_name: Optional project name.
            is_user: Boolean indicating whether the given `entity_name` refers
                to a user.
        """
        data = {
            "role_name": role_name,
            "entity_name": entity_name,
            "project_name": project_name,
            "is_user": is_user,
        }
        self._handle_response(
            requests.delete(
                self.url + ROLE_ASSIGNMENTS,
                json=data,
                auth=self._get_authentication(),
            )
        )

    def get_users_for_team(self, team_name: str) -> List[UserModel]:
        """Fetches all users of a team.

        Args:
            team_name: Name of the team.

        Returns:
            List of users that are part of the team.

        Raises:
            ValueError: In case of a bad API response.
        """
        body = self.get(f"{TEAMS}/{team_name}/users")
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [UserModel.parse_obj(user_dict) for user_dict in body]

    def get_teams_for_user(self, user_name: str) -> List[TeamModel]:
        """Fetches all teams for a user.

        Args:
            user_name: Name of the user.

        Returns:
            List of teams that the user is part of.

        Raises:
            ValueError: In case of a bad API response.
        """
        body = self.get(f"{USERS}/{user_name}/teams")
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [TeamModel.parse_obj(team_dict) for team_dict in body]

    def get_role_assignments_for_user(
        self,
        user_name: str,
        project_name: Optional[str] = None,
        include_team_roles: bool = True,
    ) -> List[RoleAssignmentModel]:
        """Fetches all role assignments for a user.

        Args:
            user_name: Name of the user.
            project_name: Optional filter to only return roles assigned for
                this project.
            include_team_roles: If `True`, includes roles for all teams that
                the user is part of.

        Returns:
            List of role assignments for this user.

        Raises:
            ValueError: In case of a bad API response.
        """
        path = f"{USERS}/{user_name}/role_assignments"
        if project_name:
            path += f"?project_name={project_name}"

        body = self.get(path)
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        assignments = [
            RoleAssignmentModel.parse_obj(assignment_dict)
            for assignment_dict in body
        ]
        if include_team_roles:
            for team in self.get_teams_for_user(user_name):
                assignments += self.get_role_assignments_for_team(
                    team.name, project_name=project_name
                )
        return assignments

    def get_role_assignments_for_team(
        self,
        team_name: str,
        project_name: Optional[str] = None,
    ) -> List[RoleAssignmentModel]:
        """Fetches all role assignments for a team.

        Args:
            team_name: Name of the user.
            project_name: Optional filter to only return roles assigned for
                this project.

        Returns:
            List of role assignments for this team.

        Raises:
            ValueError: In case of a bad API response.
        """
        path = f"{TEAMS}/{team_name}/role_assignments"
        if project_name:
            path += f"?project_name={project_name}"

        body = self.get(path)
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [
            RoleAssignmentModel.parse_obj(assignment_dict)
            for assignment_dict in body
        ]

    # Pipelines and pipeline runs

    def get_pipeline(self, pipeline_name: str) -> Optional[PipelineView]:
        """Returns a pipeline for the given name.

        Args:
            pipeline_name: Name of the pipeline.

        Returns:
            PipelineView if found, None otherwise.
        """
        pass  # TODO

    def get_pipelines(self) -> List[PipelineView]:
        """Returns a list of all pipelines stored in this ZenStore.

        Returns:
            A list of all pipelines stored in this ZenStore.
        """
        pass  # TODO

    def get_pipeline_run(
        self, pipeline: PipelineView, run_name: str
    ) -> Optional[PipelineRunView]:
        """Gets a specific run for the given pipeline.

        Args:
            pipeline: The pipeline for which to get the run.
            run_name: The name of the run to get.

        Returns:
            The pipeline run with the given name.
        """
        pass  # TODO

    def get_pipeline_runs(
        self, pipeline: PipelineView
    ) -> Dict[str, PipelineRunView]:
        """Gets all runs for the given pipeline.

        Args:
            pipeline: a Pipeline object for which you want the runs.

        Returns:
            A dictionary of pipeline run names to PipelineRunView.
        """
        pass  # TODO

    def get_pipeline_run_wrapper(
        self,
        pipeline_name: str,
        run_name: str,
        project_name: Optional[str] = None,
    ) -> PipelineRunModel:
        """Gets a pipeline run.

        Args:
            pipeline_name: Name of the pipeline for which to get the run.
            run_name: Name of the pipeline run to get.
            project_name: Optional name of the project from which to get the
                pipeline run.

        Returns:
            A pipeline run object.
        """
        path = f"{PIPELINE_RUNS}/{pipeline_name}/{run_name}"
        if project_name:
            path += f"?project_name={project_name}"

        body = self.get(path)
        return PipelineRunModel.parse_obj(body)

    def get_pipeline_run_wrappers(
        self, pipeline_name: str, project_name: Optional[str] = None
    ) -> List[PipelineRunModel]:
        """Gets pipeline runs.

        Args:
            pipeline_name: Name of the pipeline for which to get runs.
            project_name: Optional name of the project from which to get the
                pipeline runs.

        Returns:
            List of pipeline runs.

        Raises:
            ValueError: In case of a bad API response.
        """
        path = f"{PIPELINE_RUNS}/{pipeline_name}"
        if project_name:
            path += f"?project_name={project_name}"

        body = self.get(path)
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [PipelineRunModel.parse_obj(dict_) for dict_ in body]

    def get_pipeline_run_steps(
        self, pipeline_run: PipelineRunView
    ) -> Dict[str, StepView]:
        """Gets all steps for the given pipeline run.

        Args:
            pipeline_run: The pipeline run to get the steps for.

        Returns:
            A dictionary of step names to step views.
        """
        pass  # TODO

    def get_step_by_id(self, step_id: int) -> StepView:
        """Gets a `StepView` by its ID.

        Args:
            step_id (int): The ID of the step to get.

        Returns:
            StepView: The `StepView` with the given ID.
        """
        pass  # TODO

    def get_step_status(self, step: StepView) -> ExecutionStatus:
        """Gets the execution status of a single step.

        Args:
            step (StepView): The step to get the status for.

        Returns:
            ExecutionStatus: The status of the step.
        """
        pass  # TODO

    def get_step_artifacts(
        self, step: StepView
    ) -> Tuple[Dict[str, ArtifactView], Dict[str, ArtifactView]]:
        """Returns input and output artifacts for the given step.

        Args:
            step: The step for which to get the artifacts.

        Returns:
            A tuple (inputs, outputs) where inputs and outputs
            are both Dicts mapping artifact names
            to the input and output artifacts respectively.
        """
        pass  # TODO

    def get_producer_step_from_artifact(self, artifact_id: int) -> StepView:
        """Returns original StepView from an ArtifactView.

        Args:
            artifact_id: ID of the ArtifactView to be queried.

        Returns:
            Original StepView that produced the artifact.
        """
        pass  # TODO

    def register_pipeline_run(
        self,
        pipeline_run: PipelineRunModel,
    ) -> None:
        """Registers a pipeline run.

        Args:
            pipeline_run: The pipeline run to register.
        """
        self.post(PIPELINE_RUNS, body=pipeline_run)

    # Private interface shall not be implemented for REST store, instead the
    # API only provides all public methods, including the ones that would
    # otherwise be inherited from the BaseZenStore in other implementations.
    # Don't call these! ABC complains that they aren't implemented, but they
    # aren't needed with the custom implementations of base methods.

    def _create_stack(
        self, name: str, stack_configuration: Dict[StackComponentType, str]
    ) -> None:
        """Add a stack to storage.

        Args:
            name: Name of the stack.
            stack_configuration: Configuration of the stack.

        Raises:
            NotImplementedError: If this method is called.
        """
        raise NotImplementedError("Not to be accessed directly in client!")

    def _get_component_flavor_and_config(
        self, component_type: StackComponentType, name: str
    ) -> Tuple[str, bytes]:
        """Fetch the flavor and configuration for a stack component.

        Args:
            component_type: Type of the component.
            name: Name of the component.

        Raises:
            NotImplementedError: If the component type is not supported.
        """
        raise NotImplementedError("Not to be accessed directly in client!")

    def _get_stack_component_names(
        self, component_type: StackComponentType
    ) -> List[str]:
        """Get names of all registered stack components of a given type.

        Args:
            component_type: Type of the components.

        Raises:
            NotImplementedError: always
        """
        raise NotImplementedError("Not to be accessed directly in client!")

    def _delete_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> None:
        """Remove a StackComponent from storage.

        Args:
            component_type: Type of the component.
            name: Name of the component.

        Raises:
            NotImplementedError: always.
        """
        raise NotImplementedError("Not to be accessed directly in client!")

    # Handling stack component flavors

    @property
    def flavors(self) -> List[FlavorModel]:
        """All registered flavors.

        Returns:
            A list of all registered flavors.

        Raises:
            ValueError: If the API response is not a list.
        """
        body = self.get(FLAVORS)
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [FlavorModel.parse_obj(flavor_dict) for flavor_dict in body]

    def _create_flavor(
        self,
        source: str,
        name: str,
        stack_component_type: StackComponentType,
    ) -> FlavorModel:
        """Creates a new flavor.

        Args:
            source: the source path to the implemented flavor.
            name: the name of the flavor.
            stack_component_type: the corresponding StackComponentType.

        Returns:
            The newly created flavor.
        """
        flavor = FlavorModel(
            name=name,
            source=source,
            type=stack_component_type,
        )
        return FlavorModel.parse_obj(self.post(FLAVORS, body=flavor))

    def get_flavors_by_type(
        self, component_type: StackComponentType
    ) -> List[FlavorModel]:
        """Fetch all flavor defined for a specific stack component type.

        Args:
            component_type: The type of the stack component.

        Returns:
            List of all the flavors for the given stack component type.

        Raises:
            ValueError: If a list of flavors is not returned.
        """
        body = self.get(f"{FLAVORS}/{component_type}")
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [FlavorModel.parse_obj(flavor_dict) for flavor_dict in body]

    def get_flavor_by_name_and_type(
        self,
        flavor_name: str,
        component_type: StackComponentType,
    ) -> FlavorModel:
        """Fetch a flavor by a given name and type.

        Args:
            flavor_name: The name of the flavor.
            component_type: Optional, the type of the component.

        Returns:
            Flavor instance if it exists
        """
        return FlavorModel.parse_obj(
            self.get(f"{FLAVORS}/{component_type}/{flavor_name}")
        )

    # Implementation specific methods:

    def _parse_stack_configuration(
        self, to_parse: Json
    ) -> Dict[StackComponentType, str]:
        """Parse an API response into `Dict[StackComponentType, str]`.

        Args:
            to_parse: The response to parse.

        Returns:
            A dictionary mapping the component type to the path to the
            configuration.

        Raises:
            ValueError: If the response is not a dictionary.
        """
        if not isinstance(to_parse, dict):
            raise ValueError(
                f"Bad API Response. Expected dict, got {type(to_parse)}."
            )
        return {
            StackComponentType(typ): component_name
            for typ, component_name in to_parse.items()
        }

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
            HTTPError: If the response indicates that the requested entity
                does not exist.
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
            raise requests.HTTPError(
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
            raise KeyError(response.text)
        else:
            raise RuntimeError(
                "Error retrieving from API. Got response "
                f"{response.status_code} with body:\n{response.text}"
            )

    def _get_authentication(self) -> Tuple[str, str]:
        """Gets HTTP basic auth credentials.

        Returns:
            A tuple of the username and password.
        """
        return self.config.username, self.config.password

    def get(self, path: str) -> Json:
        """Make a GET request to the given endpoint path.

        Args:
            path: The path to the endpoint.

        Returns:
            The response body.
        """
        return self._handle_response(
            requests.get(self.url + path, auth=self._get_authentication())
        )

    def delete(self, path: str) -> Json:
        """Make a DELETE request to the given endpoint path.

        Args:
            path: The path to the endpoint.

        Returns:
            The response body.
        """
        return self._handle_response(
            requests.delete(self.url + path, auth=self._get_authentication())
        )

    def post(self, path: str, body: BaseModel) -> Json:
        """Make a POST request to the given endpoint path.

        Args:
            path: The path to the endpoint.
            body: The body to send.

        Returns:
            The response body.
        """
        endpoint = self.url + path
        return self._handle_response(
            requests.post(
                endpoint, data=body.json(), auth=self._get_authentication()
            )
        )

    def put(self, path: str, body: BaseModel) -> Json:
        """Make a PUT request to the given endpoint path.

        Args:
            path: The path to the endpoint.
            body: The body to send.

        Returns:
            The response body.
        """
        endpoint = self.url + path
        return self._handle_response(
            requests.put(
                endpoint, data=body.json(), auth=self._get_authentication()
            )
        )
