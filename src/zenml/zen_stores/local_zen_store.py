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
import base64
import itertools
import os
import re
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    overload,
)
from uuid import UUID

from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import EntityExistsError, StackComponentExistsError
from zenml.io import fileio, utils
from zenml.logger import get_logger
from zenml.zen_stores import BaseZenStore
from zenml.zen_stores.models import (
    ComponentWrapper,
    FlavorWrapper,
    Project,
    Role,
    RoleAssignment,
    Team,
    User,
    ZenStoreModel,
    ZenStorePipelineModel,
)
from zenml.zen_stores.models.pipeline_models import PipelineRunWrapper

logger = get_logger(__name__)

E = TypeVar(
    "E",
    bound=Union[User, Team, Project, Role, FlavorWrapper, PipelineRunWrapper],
)


@overload
def _get_unique_entity(
    entity_name: str, collection: Sequence[E], ensure_exists: bool = True
) -> E:
    """Type annotations in case of `ensure_exists=True`."""
    ...


@overload
def _get_unique_entity(
    entity_name: str, collection: Sequence[E], ensure_exists: bool = False
) -> Optional[E]:
    """Type annotations in case of `ensure_exists=False`."""
    ...


def _get_unique_entity(
    entity_name: str, collection: Sequence[E], ensure_exists: bool = True
) -> Optional[E]:
    """Gets an entity with a specific name from a collection.

    Args:
        entity_name: Name of the entity to get.
        collection: List of entities.
        ensure_exists: If `True`, raises an error if the entity doesn't exist.

    Returns:
        The entity for the name or `None` if it wasn't found.

    Raises:
        RuntimeError: If more than one entity with the name exists.
        KeyError: If `ensure_exists` is `True` and no entity for the name was
            found.
    """
    matches = [entity for entity in collection if entity.name == entity_name]
    if len(matches) > 1:
        # Two entities with the same name, this should never happen
        raise RuntimeError(
            f"Found two or more entities with name '{entity_name}' of type "
            f"`{type(matches[0])}`."
        )

    if ensure_exists:
        if not matches:
            raise KeyError(f"No entity found with name '{entity_name}'.")
        return matches[0]
    else:
        return matches[0] if matches else None


class LocalZenStore(BaseZenStore):
    def initialize(
        self,
        url: str,
        *args: Any,
        store_data: Optional[ZenStoreModel] = None,
        **kwargs: Any,
    ) -> "LocalZenStore":
        """Initializes a local ZenStore instance.

        Args:
            url: URL of local directory of the repository to use for
                storage.
            store_data: optional store data object to pre-populate the
                zen store with.
            args: additional positional arguments (ignored).
            kwargs: additional keyword arguments (ignored).

        Returns:
            The initialized ZenStore instance.
        """
        if not self.is_valid_url(url):
            raise ValueError(f"Invalid URL for local store: {url}")

        self._root = self.get_path_from_url(url)
        self._url = f"file://{self._root}"
        utils.create_dir_recursive_if_not_exists(str(self._root))

        if store_data is not None:
            self.__store = store_data
        else:
            self.__store = ZenStoreModel(str(self.root / "stacks.yaml"))

        self.__pipeline_store = ZenStorePipelineModel(
            str(self.root / "pipeline_runs.yaml")
        )

        super().initialize(url, *args, **kwargs)
        return self

    # Public interface implementations:

    @property
    def type(self) -> StoreType:
        """The type of zen store."""
        return StoreType.LOCAL

    @property
    def url(self) -> str:
        """URL of the repository."""
        return self._url

    # Static methods:

    @staticmethod
    def get_path_from_url(url: str) -> Optional[Path]:
        """Get the path from a URL.

        Args:
            url: The URL to get the path from.

        Returns:
            The path from the URL.
        """
        if not LocalZenStore.is_valid_url(url):
            raise ValueError(f"Invalid URL for local store: {url}")
        url = url.replace("file://", "")
        return Path(url)

    @staticmethod
    def get_local_url(path: str) -> str:
        """Get a local URL for a given local path."""
        return f"file://{path}"

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if the given url is a valid local path."""
        scheme = re.search("^([a-z0-9]+://)", url)
        return not scheme or scheme.group() == "file://"

    @property
    def stacks_empty(self) -> bool:
        """Check if the zen store is empty."""
        return len(self.__store.stacks) == 0

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
        logger.debug("Fetching stack with name '%s'.", name)
        if name not in self.__store.stacks:
            raise KeyError(
                f"Unable to find stack with name '{name}'. Available names: "
                f"{set(self.__store.stacks)}."
            )

        return self.__store.stacks[name]

    @property
    def stack_configurations(self) -> Dict[str, Dict[StackComponentType, str]]:
        """Configuration for all stacks registered in this zen store.

        Returns:
            Dictionary mapping stack names to Dict[StackComponentType, str]
        """
        return self.__store.stacks.copy()

    def _register_stack_component(
        self,
        component: ComponentWrapper,
    ) -> None:
        """Register a stack component.

        Args:
            component: The component to register.

        Raises:
            StackComponentExistsError: If a stack component with the same type
                and name already exists.
        """
        components = self.__store.stack_components[component.type]
        if component.name in components:
            raise StackComponentExistsError(
                f"Unable to register stack component (type: {component.type}) "
                f"with name '{component.name}': Found existing stack component "
                f"with this name."
            )

        # write the component configuration file
        component_config_path = self._get_stack_component_config_path(
            component_type=component.type, name=component.name
        )
        utils.create_dir_recursive_if_not_exists(
            os.path.dirname(component_config_path)
        )
        utils.write_file_contents_as_string(
            component_config_path,
            base64.b64decode(component.config).decode(),
        )

        # add the component to the zen store dict and write it to disk
        components[component.name] = component.flavor
        self.__store.write_config()
        logger.info(
            "Registered stack component with type '%s' and name '%s'.",
            component.type,
            component.name,
        )

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
        components = self.__store.stack_components[component_type]
        if name not in components:
            raise KeyError(
                f"Unable to update stack component (type: {component_type}) "
                f"with name '{name}': No existing stack component "
                f"found with this name."
            )
        elif name != component.name and component.name in components:
            raise StackComponentExistsError(
                f"Unable to update stack component (type: {component_type}) "
                f"with name '{component.name}': a stack component already "
                f"is registered with this name."
            )
        component_config_path = self._get_stack_component_config_path(
            component_type=component.type, name=component.name
        )
        utils.create_dir_recursive_if_not_exists(
            os.path.dirname(component_config_path)
        )
        utils.write_file_contents_as_string(
            component_config_path,
            base64.b64decode(component.config).decode(),
        )
        if name != component.name:
            self._delete_stack_component(component_type, name)

        # add the component to the stack store dict and write it to disk
        components[component.name] = component.flavor

        for _, conf in self.stack_configurations.items():
            for component_type, component_name in conf.items():
                if component_name == name and component_type == component.type:
                    conf[component_type] = component.name
        self.__store.write_config()

        logger.info(
            "Updated stack component with type '%s' and name '%s'.",
            component_type,
            component.name,
        )
        return {component.type.value: component.flavor}

    def _deregister_stack(self, name: str) -> None:
        """Remove a stack from storage.

        Args:
            name: The name of the stack to be deleted.

        Raises:
            KeyError: If no stack exists for the given name.
        """
        del self.__store.stacks[name]
        self.__store.write_config()

    # Private interface implementations:

    def _save_stack(
        self,
        name: str,
        stack_configuration: Dict[StackComponentType, str],
    ) -> None:
        """Save a stack.

        Args:
            name: The name to save the stack as.
            stack_configuration: Dict[StackComponentType, str] to persist.
        """
        self.__store.stacks[name] = stack_configuration
        self.__store.write_config()

    def _get_component_flavor_and_config(
        self, component_type: StackComponentType, name: str
    ) -> Tuple[str, bytes]:
        """Fetch the flavor and configuration for a stack component.

        Args:
            component_type: The type of the component to fetch.
            name: The name of the component to fetch.

        Returns:
            Pair of (flavor, configuration) for stack component, as string and
            base64-encoded yaml document, respectively

        Raises:
            KeyError: If no stack component exists for the given type and name.
        """
        components: Dict[str, str] = self.__store.stack_components[
            component_type
        ]
        if name not in components:
            raise KeyError(
                f"Unable to find stack component (type: {component_type}) "
                f"with name '{name}'. Available names: {set(components)}."
            )

        component_config_path = self._get_stack_component_config_path(
            component_type=component_type, name=name
        )
        flavor = components[name]
        config = base64.b64encode(
            utils.read_file_contents_as_string(component_config_path).encode()
        )
        return flavor, config

    def _get_stack_component_names(
        self, component_type: StackComponentType
    ) -> List[str]:
        """Get names of all registered stack components of a given type."""
        return list(self.__store.stack_components[component_type])

    def _delete_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> None:
        """Remove a StackComponent from storage.

        Args:
            component_type: The type of component to delete.
            name: Then name of the component to delete.

        Raises:
            KeyError: If no component exists for given type and name.
        """
        component_config_path = self._get_stack_component_config_path(
            component_type=component_type, name=name
        )

        if fileio.exists(component_config_path):
            fileio.remove(component_config_path)

        components = self.__store.stack_components[component_type]
        del components[name]
        self.__store.write_config()

    # User, project and role management

    @property
    def users(self) -> List[User]:
        """All registered users.

        Returns:
            A list of all registered users.
        """
        return self.__store.users

    def _get_user(self, user_name: str) -> User:
        """Get a specific user by name.

        Args:
            user_name: Name of the user to get.

        Returns:
            The requested user, if it was found.

        Raises:
            KeyError: If no user with the given name exists.
        """
        return _get_unique_entity(user_name, collection=self.__store.users)

    def _create_user(self, user_name: str) -> User:
        """Creates a new user.

        Args:
            user_name: Unique username.

        Returns:
             The newly created user.

        Raises:
            EntityExistsError: If a user with the given name already exists.
        """
        if _get_unique_entity(
            user_name, collection=self.__store.users, ensure_exists=False
        ):
            raise EntityExistsError(
                f"User with name '{user_name}' already exists."
            )

        user = User(name=user_name)
        self.__store.users.append(user)
        self.__store.write_config()
        return user

    def _delete_user(self, user_name: str) -> None:
        """Deletes a user.

        Args:
            user_name: Name of the user to delete.

        Raises:
            KeyError: If no user with the given name exists.
        """
        user = _get_unique_entity(user_name, collection=self.__store.users)
        self.__store.users.remove(user)
        for user_names in self.__store.team_assignments.values():
            user_names.discard(user.name)

        self.__store.role_assignments = [
            assignment
            for assignment in self.__store.role_assignments
            if assignment.user_id != user.id
        ]
        self.__store.write_config()
        logger.info("Deleted user %s.", user)

    @property
    def teams(self) -> List[Team]:
        """All registered teams.

        Returns:
            A list of all registered teams.
        """
        return self.__store.teams

    def _get_team(self, team_name: str) -> Team:
        """Gets a specific team.

        Args:
            team_name: Name of the team to get.

        Returns:
            The requested team.

        Raises:
            KeyError: If no team with the given name exists.
        """
        return _get_unique_entity(team_name, collection=self.__store.teams)

    def _create_team(self, team_name: str) -> Team:
        """Creates a new team.

        Args:
            team_name: Unique team name.

        Returns:
             The newly created team.

        Raises:
            EntityExistsError: If a team with the given name already exists.
        """
        if _get_unique_entity(
            team_name, collection=self.__store.teams, ensure_exists=False
        ):
            raise EntityExistsError(
                f"Team with name '{team_name}' already exists."
            )

        team = Team(name=team_name)
        self.__store.teams.append(team)
        self.__store.write_config()
        return team

    def _delete_team(self, team_name: str) -> None:
        """Deletes a team.

        Args:
            team_name: Name of the team to delete.

        Raises:
            KeyError: If no team with the given name exists.
        """
        team = _get_unique_entity(team_name, collection=self.__store.teams)
        self.__store.teams.remove(team)
        self.__store.team_assignments.pop(team.name, None)
        self.__store.role_assignments = [
            assignment
            for assignment in self.__store.role_assignments
            if assignment.team_id != team.id
        ]
        self.__store.write_config()
        logger.info("Deleted team %s.", team)

    def add_user_to_team(self, team_name: str, user_name: str) -> None:
        """Adds a user to a team.

        Args:
            team_name: Name of the team.
            user_name: Name of the user.

        Raises:
            KeyError: If no user and team with the given names exists.
        """
        team = _get_unique_entity(team_name, self.__store.teams)
        user = _get_unique_entity(user_name, self.__store.users)
        self.__store.team_assignments[team.name].add(user.name)
        self.__store.write_config()

    def remove_user_from_team(self, team_name: str, user_name: str) -> None:
        """Removes a user from a team.

        Args:
            team_name: Name of the team.
            user_name: Name of the user.

        Raises:
            KeyError: If no user and team with the given names exists.
        """
        team = _get_unique_entity(team_name, self.__store.teams)
        user = _get_unique_entity(user_name, self.__store.users)
        self.__store.team_assignments[team.name].remove(user.name)
        self.__store.write_config()

    @property
    def projects(self) -> List[Project]:
        """All registered projects.

        Returns:
            A list of all registered projects.
        """
        return self.__store.projects

    def _get_project(self, project_name: str) -> Project:
        """Get an existing project by name.

        Args:
            project_name: Name of the project to get.

        Returns:
            The requested project if one was found.

        Raises:
            KeyError: If there is no such project.
        """
        return _get_unique_entity(
            project_name, collection=self.__store.projects
        )

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
        if _get_unique_entity(
            project_name, collection=self.__store.projects, ensure_exists=False
        ):
            raise EntityExistsError(
                f"Project with name '{project_name}' already exists."
            )

        project = Project(name=project_name, description=description)
        self.__store.projects.append(project)
        self.__store.write_config()
        return project

    def _delete_project(self, project_name: str) -> None:
        """Deletes a project.

        Args:
            project_name: Name of the project to delete.

        Raises:
            KeyError: If no project with the given name exists.
        """
        project = _get_unique_entity(
            project_name, collection=self.__store.projects
        )
        self.__store.projects.remove(project)
        self.__store.role_assignments = [
            assignment
            for assignment in self.__store.role_assignments
            if assignment.project_id != project.id
        ]

        self.__store.write_config()
        logger.info("Deleted project %s.", project)

    @property
    def roles(self) -> List[Role]:
        """All registered roles.

        Returns:
            A list of all registered roles.
        """
        return self.__store.roles

    @property
    def role_assignments(self) -> List[RoleAssignment]:
        """All registered role assignments.

        Returns:
            A list of all registered role assignments.
        """
        return self.__store.role_assignments

    def _get_role(self, role_name: str) -> Role:
        """Gets a specific role.

        Args:
            role_name: Name of the role to get.

        Returns:
            The requested role.

        Raises:
            KeyError: If no role with the given name exists.
        """
        return _get_unique_entity(role_name, collection=self.__store.roles)

    def _create_role(self, role_name: str) -> Role:
        """Creates a new role.

        Args:
            role_name: Unique role name.

        Returns:
             The newly created role.

        Raises:
            EntityExistsError: If a role with the given name already exists.
        """
        if _get_unique_entity(
            role_name, collection=self.__store.roles, ensure_exists=False
        ):
            raise EntityExistsError(
                f"Role with name '{role_name}' already exists."
            )

        role = Role(name=role_name)
        self.__store.roles.append(role)
        self.__store.write_config()
        return role

    def _delete_role(self, role_name: str) -> None:
        """Deletes a role.

        Args:
            role_name: Name of the role to delete.

        Raises:
            KeyError: If no role with the given name exists.
        """
        role = _get_unique_entity(role_name, collection=self.__store.roles)
        self.__store.roles.remove(role)
        self.__store.role_assignments = [
            assignment
            for assignment in self.__store.role_assignments
            if assignment.role_id != role.id
        ]

        self.__store.write_config()
        logger.info("Deleted role %s.", role)

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
        role = _get_unique_entity(role_name, collection=self.__store.roles)
        project_id: Optional[UUID] = None
        if project_name:
            project_id = _get_unique_entity(
                project_name, collection=self.__store.projects
            ).id

        if is_user:
            user = _get_unique_entity(entity_name, self.__store.users)
            assignment = RoleAssignment(
                role_id=role.id, project_id=project_id, user_id=user.id
            )
        else:
            team = _get_unique_entity(entity_name, self.__store.teams)
            assignment = RoleAssignment(
                role_id=role.id, project_id=project_id, team_id=team.id
            )

        self.__store.role_assignments.append(assignment)
        self.__store.write_config()

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
        role = _get_unique_entity(role_name, collection=self.__store.roles)

        user_id: Optional[UUID] = None
        team_id: Optional[UUID] = None
        project_id: Optional[UUID] = None

        if is_user:
            user_id = _get_unique_entity(entity_name, self.__store.users).id
        else:
            team_id = _get_unique_entity(entity_name, self.__store.teams).id

        if project_name:
            project_id = _get_unique_entity(
                project_name, collection=self.__store.projects
            ).id

        assignments = self._get_role_assignments(
            role_id=role.id,
            user_id=user_id,
            team_id=team_id,
            project_id=project_id,
        )
        if assignments:
            self.__store.role_assignments.remove(
                assignments[0]
            )  # there should only be one
            self.__store.write_config()

    def get_users_for_team(self, team_name: str) -> List[User]:
        """Fetches all users of a team.

        Args:
            team_name: Name of the team.

        Returns:
            List of users that are part of the team.

        Raises:
            KeyError: If no team with the given name exists.
        """
        team = _get_unique_entity(team_name, collection=self.__store.teams)
        user_names = self.__store.team_assignments[team.name]
        return [user for user in self.users if user.name in user_names]

    def get_teams_for_user(self, user_name: str) -> List[Team]:
        """Fetches all teams for a user.

        Args:
            user_name: Name of the user.

        Returns:
            List of teams that the user is part of.

        Raises:
            KeyError: If no user with the given name exists.
        """
        user = _get_unique_entity(user_name, collection=self.__store.users)
        team_names = [
            team_name
            for team_name, user_names in self.__store.team_assignments.items()
            if user.name in user_names
        ]
        return [team for team in self.teams if team.name in team_names]

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
        """
        user = _get_unique_entity(user_name, collection=self.__store.users)
        project_id = (
            _get_unique_entity(
                project_name, collection=self.__store.projects
            ).id
            if project_name
            else None
        )
        assignments = self._get_role_assignments(
            user_id=user.id, project_id=project_id
        )

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
            KeyError: If no team or project with the given names exists.
        """
        team = _get_unique_entity(team_name, collection=self.__store.teams)
        project_id = (
            _get_unique_entity(
                project_name, collection=self.__store.projects
            ).id
            if project_name
            else None
        )
        return self._get_role_assignments(
            team_id=team.id, project_id=project_id
        )

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
        runs = self.__pipeline_store.pipeline_runs[pipeline_name]

        for run in runs:
            if run.name != run_name:
                continue
            if project_name and run.project_name != project_name:
                continue

            return run

        project_message = (
            f" in project {project_name}." if project_name else "."
        )
        raise KeyError(
            f"No pipeline run '{run_name}' found for pipeline "
            f"'{pipeline_name}'{project_message}"
        )

    def get_pipeline_runs(
        self, pipeline_name: str, project_name: Optional[str] = None
    ) -> List[PipelineRunWrapper]:
        """Gets pipeline runs.

        Args:
            pipeline_name: Name of the pipeline for which to get runs.
            project_name: Optional name of the project from which to get the
                pipeline runs.
        """
        runs = self.__pipeline_store.pipeline_runs[pipeline_name]
        if project_name:
            runs = [run for run in runs if run.project_name == project_name]

        return runs

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
        all_runs = list(
            itertools.chain.from_iterable(
                self.__pipeline_store.pipeline_runs.values()
            )
        )
        if _get_unique_entity(
            entity_name=pipeline_run.name,
            collection=all_runs,
            ensure_exists=False,
        ):
            raise EntityExistsError(
                f"Pipeline run with name '{pipeline_run.name}' already exists. "
                "Please make sure your pipeline run names are unique."
            )

        self.__pipeline_store.pipeline_runs[pipeline_run.pipeline.name].append(
            pipeline_run
        )
        self.__pipeline_store.write_config()

    # Handling stack component flavors

    @property
    def flavors(self) -> List[FlavorWrapper]:
        """All registered flavors.

        Returns:
            A list of all registered flavors.
        """
        return self.__store.stack_component_flavors

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

        if _get_unique_entity(
            name,
            collection=self.get_flavors_by_type(stack_component_type),
            ensure_exists=False,
        ):
            raise EntityExistsError(
                f"The flavor '{name}' for the stack component type "
                f"'{stack_component_type.plural}' already exists."
            )

        flavor = FlavorWrapper(
            name=name,
            source=source,
            type=stack_component_type,
        )

        self.__store.stack_component_flavors.append(flavor)
        self.__store.write_config()

        return flavor

    def get_flavors_by_type(
        self, component_type: StackComponentType
    ) -> List[FlavorWrapper]:
        """Fetch all flavor defined for a specific stack component type.

        Args:
            component_type: The type of the stack component.

        Returns:
            List of all the flavors for the given stack component type.
        """
        return [
            f
            for f in self.__store.stack_component_flavors
            if f.type == component_type
        ]

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
        matches = self.get_flavors_by_type(component_type)
        return _get_unique_entity(
            entity_name=flavor_name,
            collection=matches,
            ensure_exists=True,
        )

    # Implementation-specific internal methods:

    @property
    def root(self) -> Path:
        """The root directory of the zen store."""
        if not self._root:
            raise RuntimeError(
                "Local zen store has not been initialized. Call `initialize` "
                "before using the store."
            )
        return self._root

    def _get_stack_component_config_path(
        self, component_type: StackComponentType, name: str
    ) -> str:
        """Path to the configuration file of a stack component."""
        path = self.root / component_type.plural / f"{name}.yaml"
        return str(path)

    def _get_role_assignments(
        self,
        role_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        team_id: Optional[UUID] = None,
    ) -> List[RoleAssignment]:
        """Gets all role assignments that match the criteria.

        Args:
            role_id: Only include role assignments associated with this role id.
            project_id: Only include role assignments associated with this
                project id.
            user_id: Only include role assignments associated with this user id.
            team_id: Only include role assignments associated with this team id.

        Returns:
            List of role assignments.
        """
        return [
            assignment
            for assignment in self.__store.role_assignments
            if not (
                (role_id and assignment.role_id != role_id)
                or (project_id and project_id != assignment.project_id)
                or (user_id and user_id != assignment.user_id)
                or (team_id and team_id != assignment.team_id)
            )
        ]
