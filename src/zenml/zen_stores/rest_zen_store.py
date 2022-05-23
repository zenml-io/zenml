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
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import requests
from pydantic import BaseModel

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
from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import (
    DoesNotExistException,
    EntityExistsError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.logger import get_logger
from zenml.zen_stores import BaseZenStore
from zenml.zen_stores.models import (
    ComponentWrapper,
    FlavorWrapper,
    Project,
    Role,
    RoleAssignment,
    StackWrapper,
    Team,
    User,
)
from zenml.zen_stores.models.pipeline_models import PipelineRunWrapper

logger = get_logger(__name__)

# type alias for possible json payloads (the Anys are recursive Json instances)
Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


class RestZenStore(BaseZenStore):
    """ZenStore implementation for accessing data from a REST api."""

    def initialize(
        self,
        url: str,
        *args: Any,
        **kwargs: Any,
    ) -> "RestZenStore":
        """Initializes a rest zen store instance.

        Args:
            url: Endpoint URL of the service for zen storage.
            args: additional positional arguments (ignored).
            kwargs: additional keyword arguments (ignored).

        Returns:
            The initialized zen store instance.
        """
        if not self.is_valid_url(url.strip("/")):
            raise ValueError("Invalid URL for REST store: {url}")
        self._url = url.strip("/")
        super().initialize(url, *args, **kwargs)
        return self

    def _migrate_store(self) -> None:
        """Migrates the store to the latest version."""
        # Don't do anything here in the rest store, as the migration has to be
        # done server-side.

    # Static methods:

    @staticmethod
    def get_path_from_url(url: str) -> Optional[Path]:
        """Get the path from a URL, if it points or is backed by a local file.

        Args:
            url: The URL to get the path from.

        Returns:
            None, because there are no local paths from REST urls.
        """
        return None

    @staticmethod
    def get_local_url(path: str) -> str:
        """Get a local URL for a given local path.

        Args:
             path: the path string to build a URL out of.

        Returns:
            Url pointing to the path for the store type.

        Raises:
            NotImplementedError: always
        """
        raise NotImplementedError("Cannot build a REST url from a path.")

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if the given url is a valid local path."""
        scheme = re.search("^([a-z0-9]+://)", url)
        return (
            scheme is not None
            and scheme.group() in ("https://", "http://")
            and url[-1] != "/"
        )

    # Public Interface:

    @property
    def type(self) -> StoreType:
        """The type of stack store."""
        return StoreType.REST

    @property
    def url(self) -> str:
        """Get the stack store URL."""
        return self._url

    @property
    def stacks_empty(self) -> bool:
        """Check if the store is empty (no stacks are configured).

        The implementation of this method should check if the store is empty
        without having to load all the stacks from the persistent storage.
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

        Raises:
            KeyError: If no stack exists for the given name.
        """
        return self._parse_stack_configuration(
            self.get(f"{STACK_CONFIGURATIONS}/{name}")
        )

    @property
    def stack_configurations(self) -> Dict[str, Dict[StackComponentType, str]]:
        """Configurations for all stacks registered in this stack store.

        Returns:
            Dictionary mapping stack names to Dict[StackComponentType, str]'s
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

    def _register_stack_component(
        self,
        component: ComponentWrapper,
    ) -> None:
        """Register a stack component.

        Args:
            component: The component to register.

        Raises:
            KeyError: If a stack component with the same type
                and name already exists.
        """
        self.post(STACK_COMPONENTS, body=component)

    def _update_stack_component(
        self,
        name: str,
        component_type: StackComponentType,
        component: ComponentWrapper,
    ) -> Dict[str, str]:
        """Update a stack component.

        Args:
            name: The original name of the stack component.
            component_type: The type of the stack component to update.
            component: The new component to update with.

        Raises:
            KeyError: If no stack component exists with the given name.
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

        Raises:
            KeyError: If no stack exists for the given name.
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
        """
        raise NotImplementedError

    # Custom implementations:

    @property
    def stacks(self) -> List[StackWrapper]:
        """All stacks registered in this repository."""
        body = self.get(STACKS)
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [StackWrapper.parse_obj(s) for s in body]

    def get_stack(self, name: str) -> StackWrapper:
        """Fetch a stack by name.

        Args:
            name: The name of the stack to retrieve.

        Returns:
            StackWrapper instance if the stack exists.

        Raises:
            KeyError: If no stack exists for the given name.
        """
        return StackWrapper.parse_obj(self.get(f"{STACKS}/{name}"))

    def _register_stack(self, stack: StackWrapper) -> None:
        """Register a stack and its components.

        If any of the stacks' components aren't registered in the stack store
        yet, this method will try to register them as well.

        Args:
            stack: The stack to register.

        Raises:
            StackExistsError: If a stack with the same name already exists.
            StackComponentExistsError: If a component of the stack wasn't
                registered and a different component with the same name
                already exists.
        """
        self.post(STACKS, stack)

    def _update_stack(self, name: str, stack: StackWrapper) -> None:
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
    ) -> ComponentWrapper:
        """Get a registered stack component.

        Raises:
            KeyError: If no component with the requested type and name exists.
        """
        return ComponentWrapper.parse_obj(
            self.get(f"{STACK_COMPONENTS}/{component_type}/{name}")
        )

    def get_stack_components(
        self, component_type: StackComponentType
    ) -> List[ComponentWrapper]:
        """Fetches all registered stack components of the given type.

        Args:
            component_type: StackComponentType to list members of

        Returns:
            A list of StackComponentConfiguration instances.
        """
        body = self.get(f"{STACK_COMPONENTS}/{component_type}")
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [ComponentWrapper.parse_obj(c) for c in body]

    def deregister_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> None:
        """Deregisters a stack component.

        Args:
            component_type: The type of the component to deregister.
            name: The name of the component to deregister.

        Raises:
            ValueError: if trying to deregister a component that's part
                of a stack.
        """
        self.delete(f"{STACK_COMPONENTS}/{component_type}/{name}")

    # User, project and role management

    @property
    def users(self) -> List[User]:
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
        return [User.parse_obj(user_dict) for user_dict in body]

    def _get_user(self, user_name: str) -> User:
        """Get a specific user by name.

        Args:
            user_name: Name of the user to get.

        Returns:
            The requested user, if it was found.

        Raises:
            KeyError: If no user with the given name exists.
        """
        return User.parse_obj(self.get(f"{USERS}/{user_name}"))

    def _create_user(self, user_name: str) -> User:
        """Creates a new user.

        Args:
            user_name: Unique username.

        Returns:
             The newly created user.

        Raises:
            EntityExistsError: If a user with the given name already exists.
        """
        user = User(name=user_name)
        return User.parse_obj(self.post(USERS, body=user))

    def _delete_user(self, user_name: str) -> None:
        """Deletes a user.

        Args:
            user_name: Name of the user to delete.

        Raises:
            KeyError: If no user with the given name exists.
        """
        self.delete(f"{USERS}/{user_name}")

    @property
    def teams(self) -> List[Team]:
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
        return [Team.parse_obj(team_dict) for team_dict in body]

    def _get_team(self, team_name: str) -> Team:
        """Gets a specific team.

        Args:
            team_name: Name of the team to get.

        Returns:
            The requested team.

        Raises:
            KeyError: If no team with the given name exists.
        """
        return Team.parse_obj(self.get(f"{TEAMS}/{team_name}"))

    def _create_team(self, team_name: str) -> Team:
        """Creates a new team.

        Args:
            team_name: Unique team name.

        Returns:
             The newly created team.

        Raises:
            EntityExistsError: If a team with the given name already exists.
        """
        team = Team(name=team_name)
        return Team.parse_obj(self.post(TEAMS, body=team))

    def _delete_team(self, team_name: str) -> None:
        """Deletes a team.

        Args:
            team_name: Name of the team to delete.

        Raises:
            KeyError: If no team with the given name exists.
        """
        self.delete(f"{TEAMS}/{team_name}")

    def add_user_to_team(self, team_name: str, user_name: str) -> None:
        """Adds a user to a team.

        Args:
            team_name: Name of the team.
            user_name: Name of the user.

        Raises:
            KeyError: If no user and team with the given names exists.
        """
        user = User(name=user_name)
        self.post(f"{TEAMS}/{team_name}/users", user)

    def remove_user_from_team(self, team_name: str, user_name: str) -> None:
        """Removes a user from a team.

        Args:
            team_name: Name of the team.
            user_name: Name of the user.

        Raises:
            KeyError: If no user and team with the given names exists.
        """
        self.delete(f"{TEAMS}/{team_name}/users/{user_name}")

    @property
    def projects(self) -> List[Project]:
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
        return [Project.parse_obj(project_dict) for project_dict in body]

    def _get_project(self, project_name: str) -> Project:
        """Get an existing project by name.

        Args:
            project_name: Name of the project to get.

        Returns:
            The requested project if one was found.

        Raises:
            KeyError: If there is no such project.
        """
        return Project.parse_obj(self.get(f"{PROJECTS}/{project_name}"))

    def _create_project(
        self, project_name: str, description: Optional[str] = None
    ) -> Project:
        """Creates a new project.

        Args:
            project_name: Unique project name.
            description: Optional project description.

        Returns:
             The newly created project.

        Raises:
            EntityExistsError: If a project with the given name already exists.
        """
        project = Project(name=project_name, description=description)
        return Project.parse_obj(self.post(PROJECTS, body=project))

    def _delete_project(self, project_name: str) -> None:
        """Deletes a project.

        Args:
            project_name: Name of the project to delete.

        Raises:
            KeyError: If no project with the given name exists.
        """
        self.delete(f"{PROJECTS}/{project_name}")

    @property
    def roles(self) -> List[Role]:
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
        return [Role.parse_obj(role_dict) for role_dict in body]

    @property
    def role_assignments(self) -> List[RoleAssignment]:
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
            RoleAssignment.parse_obj(assignment_dict)
            for assignment_dict in body
        ]

    def _get_role(self, role_name: str) -> Role:
        """Gets a specific role.

        Args:
            role_name: Name of the role to get.

        Returns:
            The requested role.

        Raises:
            KeyError: If no role with the given name exists.
        """
        return Role.parse_obj(self.get(f"{ROLES}/{role_name}"))

    def _create_role(self, role_name: str) -> Role:
        """Creates a new role.

        Args:
            role_name: Unique role name.

        Returns:
             The newly created role.

        Raises:
            EntityExistsError: If a role with the given name already exists.
        """
        role = Role(name=role_name)
        return Role.parse_obj(self.post(ROLES, body=role))

    def _delete_role(self, role_name: str) -> None:
        """Deletes a role.

        Args:
            role_name: Name of the role to delete.

        Raises:
            KeyError: If no role with the given name exists.
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

        Raises:
            KeyError: If no role, entity or project with the given names exists.
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

        Raises:
            KeyError: If no role, entity or project with the given names exists.
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

    def get_users_for_team(self, team_name: str) -> List[User]:
        """Fetches all users of a team.

        Args:
            team_name: Name of the team.

        Returns:
            List of users that are part of the team.

        Raises:
            KeyError: If no team with the given name exists.
            ValueError: In case of a bad API response.
        """
        body = self.get(f"{TEAMS}/{team_name}/users")
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [User.parse_obj(user_dict) for user_dict in body]

    def get_teams_for_user(self, user_name: str) -> List[Team]:
        """Fetches all teams for a user.

        Args:
            user_name: Name of the user.

        Returns:
            List of teams that the user is part of.

        Raises:
            KeyError: If no user with the given name exists.
            ValueError: In case of a bad API response.
        """
        body = self.get(f"{USERS}/{user_name}/teams")
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [Team.parse_obj(team_dict) for team_dict in body]

    def get_role_assignments_for_user(
        self,
        user_name: str,
        project_name: Optional[str] = None,
        include_team_roles: bool = True,
    ) -> List[RoleAssignment]:
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
            KeyError: If no user or project with the given names exists.
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
            RoleAssignment.parse_obj(assignment_dict)
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
    ) -> List[RoleAssignment]:
        """Fetches all role assignments for a team.

        Args:
            team_name: Name of the user.
            project_name: Optional filter to only return roles assigned for
                this project.

        Returns:
            List of role assignments for this team.

        Raises:
            KeyError: If no user or project with the given names exists.
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
            RoleAssignment.parse_obj(assignment_dict)
            for assignment_dict in body
        ]

    # Pipelines and pipeline runs

    def get_pipeline_run(
        self,
        pipeline_name: str,
        run_name: str,
        project_name: Optional[str] = None,
    ) -> PipelineRunWrapper:
        """Gets a pipeline run.

        Args:
            pipeline_name: Name of the pipeline for which to get the run.
            run_name: Name of the pipeline run to get.
            project_name: Optional name of the project from which to get the
                pipeline run.

        Raises:
            KeyError: If no pipeline run (or project) with the given name
                exists.
        """
        path = f"{PIPELINE_RUNS}/{pipeline_name}/{run_name}"
        if project_name:
            path += f"?project_name={project_name}"

        body = self.get(path)
        return PipelineRunWrapper.parse_obj(body)

    def get_pipeline_runs(
        self, pipeline_name: str, project_name: Optional[str] = None
    ) -> List[PipelineRunWrapper]:
        """Gets pipeline runs.

        Args:
            pipeline_name: Name of the pipeline for which to get runs.
            project_name: Optional name of the project from which to get the
                pipeline runs.
        """
        path = f"{PIPELINE_RUNS}/{pipeline_name}"
        if project_name:
            path += f"?project_name={project_name}"

        body = self.get(path)
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [PipelineRunWrapper.parse_obj(dict_) for dict_ in body]

    def register_pipeline_run(
        self,
        pipeline_run: PipelineRunWrapper,
    ) -> None:
        """Registers a pipeline run.

        Args:
            pipeline_run: The pipeline run to register.

        Raises:
            EntityExistsError: If a pipeline run with the same name already
                exists.
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
        """Add a stack to storage"""
        raise NotImplementedError("Not to be accessed directly in client!")

    def _get_component_flavor_and_config(
        self, component_type: StackComponentType, name: str
    ) -> Tuple[str, bytes]:
        """Fetch the flavor and configuration for a stack component."""
        raise NotImplementedError("Not to be accessed directly in client!")

    def _get_stack_component_names(
        self, component_type: StackComponentType
    ) -> List[str]:
        """Get names of all registered stack components of a given type."""
        raise NotImplementedError("Not to be accessed directly in client!")

    def _delete_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> None:
        """Remove a StackComponent from storage."""
        raise NotImplementedError("Not to be accessed directly in client!")

    # Handling stack component flavors

    @property
    def flavors(self) -> List[FlavorWrapper]:
        """All registered flavors.

        Returns:
            A list of all registered flavors.
        """
        body = self.get(FLAVORS)
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [FlavorWrapper.parse_obj(flavor_dict) for flavor_dict in body]

    def _create_flavor(
        self,
        source: str,
        name: str,
        stack_component_type: StackComponentType,
    ) -> FlavorWrapper:
        """Creates a new flavor.

        Args:
            source: the source path to the implemented flavor.
            name: the name of the flavor.
            stack_component_type: the corresponding StackComponentType.

        Returns:
             The newly created flavor.

        Raises:
            EntityExistsError: If a flavor with the given name and type
                already exists.
        """
        flavor = FlavorWrapper(
            name=name,
            source=source,
            type=stack_component_type,
        )
        return FlavorWrapper.parse_obj(self.post(FLAVORS, body=flavor))

    def get_flavors_by_type(
        self, component_type: StackComponentType
    ) -> List[FlavorWrapper]:
        """Fetch all flavor defined for a specific stack component type.

        Args:
            component_type: The type of the stack component.

        Returns:
            List of all the flavors for the given stack component type.
        """
        body = self.get(f"{FLAVORS}/{component_type}")
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [FlavorWrapper.parse_obj(flavor_dict) for flavor_dict in body]

    def get_flavor_by_name_and_type(
        self,
        flavor_name: str,
        component_type: StackComponentType,
    ) -> FlavorWrapper:
        """Fetch a flavor by a given name and type.

        Args:
            flavor_name: The name of the flavor.
            component_type: Optional, the type of the component.

        Returns:
            Flavor instance if it exists

        Raises:
            KeyError: If no flavor exists with the given name and type
                or there are more than one instances
        """
        return FlavorWrapper.parse_obj(
            self.get(f"{FLAVORS}/{component_type}/{flavor_name}")
        )

    # Implementation specific methods:

    def _parse_stack_configuration(
        self, to_parse: Json
    ) -> Dict[StackComponentType, str]:
        """Parse an API response into `Dict[StackComponentType, str]`."""
        if not isinstance(to_parse, dict):
            raise ValueError(
                f"Bad API Response. Expected dict, got {type(to_parse)}."
            )
        return {
            StackComponentType(typ): component_name
            for typ, component_name in to_parse.items()
        }

    def _handle_response(self, response: requests.Response) -> Json:
        """Handle API response, translating http status codes to Exception."""
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

    @staticmethod
    def _get_authentication() -> Tuple[str, str]:
        """Gets HTTP basic auth credentials."""
        from zenml.repository import Repository

        return Repository().active_user_name, ""

    def get(self, path: str) -> Json:
        """Make a GET request to the given endpoint path."""
        return self._handle_response(
            requests.get(self.url + path, auth=self._get_authentication())
        )

    def delete(self, path: str) -> Json:
        """Make a DELETE request to the given endpoint path."""
        return self._handle_response(
            requests.delete(self.url + path, auth=self._get_authentication())
        )

    def post(self, path: str, body: BaseModel) -> Json:
        """Make a POST request to the given endpoint path."""
        endpoint = self.url + path
        return self._handle_response(
            requests.post(
                endpoint, data=body.json(), auth=self._get_authentication()
            )
        )

    def put(self, path: str, body: BaseModel) -> Json:
        """Make a PUT request to the given endpoint path."""
        endpoint = self.url + path
        return self._handle_response(
            requests.put(
                endpoint, data=body.json(), auth=self._get_authentication()
            )
        )
