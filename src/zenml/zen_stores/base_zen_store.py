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
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import StackComponentExistsError, StackExistsError
from zenml.logger import get_logger
from zenml.stack import Stack
from zenml.utils.analytics_utils import AnalyticsEvent, track_event
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

DEFAULT_USERNAME = "default"


class BaseZenStore(ABC):
    """Base class for accessing data in ZenML Repository and new Service."""

    def initialize(
        self,
        url: str,
        skip_default_registrations: bool = False,
        track_analytics: bool = True,
        skip_migration: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> "BaseZenStore":
        """Initialize the store.

        Args:
            url: The URL of the store.
            skip_default_registrations: If `True`, the creation of the default
                stack and user will be skipped.
            track_analytics: Only send analytics if set to `True`.
            skip_migration: If `True`, no migration will be performed.
            *args: Additional arguments to pass to the concrete store
                implementation.
            **kwargs: Additional keyword arguments to pass to the concrete
                store implementation.

        Returns:
            The initialized concrete store instance.
        """
        self._track_analytics = track_analytics
        if not skip_default_registrations:
            if self.stacks_empty:
                logger.info("Registering default stack...")
                self.register_default_stack()
            self.create_default_user()

        if not skip_migration:
            self._migrate_store()

        return self

    def _migrate_store(self) -> None:
        """Migrates the store to the latest version."""
        # Older versions of ZenML didn't have users in the zen store, so we
        # create the default user if it doesn't exists
        self.create_default_user()

    # Static methods:

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
    def is_valid_url(url: str) -> bool:
        """Check if the given url is valid."""

    # Public Interface:

    @property
    @abstractmethod
    def type(self) -> StoreType:
        """The type of zen store."""

    @property
    @abstractmethod
    def url(self) -> str:
        """Get the repository URL."""

    @property
    @abstractmethod
    def stacks_empty(self) -> bool:
        """Check if the store is empty (no stacks are configured).

        The implementation of this method should check if the store is empty
        without having to load all the stacks from the persistent storage.
        """

    @abstractmethod
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

    @property
    @abstractmethod
    def stack_configurations(self) -> Dict[str, Dict[StackComponentType, str]]:
        """Configurations for all stacks registered in this zen store.

        Returns:
            Dictionary mapping stack names to Dict[StackComponentType, str]'s
        """

    # Private interface (must be implemented, not to be called by user):

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def _deregister_stack(self, name: str) -> None:
        """Delete a stack from storage.

        Args:
            name: The name of the stack to be deleted.

        Raises:
            KeyError: If no stack exists for the given name.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def _get_stack_component_names(
        self, component_type: StackComponentType
    ) -> List[str]:
        """Get names of all registered stack components of a given type.

        Args:
            component_type: The type of the component to list names for.

        Returns:
            A list of names as strings.
        """

    @abstractmethod
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

    # User, project and role management

    @property
    @abstractmethod
    def users(self) -> List[User]:
        """All registered users.

        Returns:
            A list of all registered users.
        """

    @abstractmethod
    def _get_user(self, user_name: str) -> User:
        """Get a specific user by name.

        Args:
            user_name: Name of the user to get.

        Returns:
            The requested user, if it was found.

        Raises:
            KeyError: If no user with the given name exists.
        """

    @abstractmethod
    def _create_user(self, user_name: str) -> User:
        """Creates a new user.

        Args:
            user_name: Unique username.

        Returns:
             The newly created user.

        Raises:
            EntityExistsError: If a user with the given name already exists.
        """

    @abstractmethod
    def _delete_user(self, user_name: str) -> None:
        """Deletes a user.

        Args:
            user_name: Name of the user to delete.

        Raises:
            KeyError: If no user with the given name exists.
        """

    @property
    @abstractmethod
    def teams(self) -> List[Team]:
        """All registered teams.

        Returns:
            A list of all registered teams.
        """

    @abstractmethod
    def _create_team(self, team_name: str) -> Team:
        """Creates a new team.

        Args:
            team_name: Unique team name.

        Returns:
             The newly created team.

        Raises:
            EntityExistsError: If a team with the given name already exists.
        """

    @abstractmethod
    def _get_team(self, team_name: str) -> Team:
        """Gets a specific team.

        Args:
            team_name: Name of the team to get.

        Returns:
            The requested team.

        Raises:
            KeyError: If no team with the given name exists.
        """

    @abstractmethod
    def _delete_team(self, team_name: str) -> None:
        """Deletes a team.

        Args:
            team_name: Name of the team to delete.

        Raises:
            KeyError: If no team with the given name exists.
        """

    @abstractmethod
    def add_user_to_team(self, team_name: str, user_name: str) -> None:
        """Adds a user to a team.

        Args:
            team_name: Name of the team.
            user_name: Name of the user.

        Raises:
            KeyError: If no user and team with the given names exists.
        """

    @abstractmethod
    def remove_user_from_team(self, team_name: str, user_name: str) -> None:
        """Removes a user from a team.

        Args:
            team_name: Name of the team.
            user_name: Name of the user.

        Raises:
            KeyError: If no user and team with the given names exists.
        """

    @property
    @abstractmethod
    def projects(self) -> List[Project]:
        """All registered projects.

        Returns:
            A list of all registered projects.
        """

    @abstractmethod
    def _get_project(self, project_name: str) -> Project:
        """Get an existing project by name.

        Args:
            project_name: Name of the project to get.

        Returns:
            The requested project if one was found.

        Raises:
            KeyError: If there is no such project.
        """

    @abstractmethod
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

    @abstractmethod
    def _delete_project(self, project_name: str) -> None:
        """Deletes a project.

        Args:
            project_name: Name of the project to delete.

        Raises:
            KeyError: If no project with the given name exists.
        """

    @property
    @abstractmethod
    def roles(self) -> List[Role]:
        """All registered roles.

        Returns:
            A list of all registered roles.
        """

    @property
    @abstractmethod
    def role_assignments(self) -> List[RoleAssignment]:
        """All registered role assignments.

        Returns:
            A list of all registered role assignments.
        """

    @abstractmethod
    def _get_role(self, role_name: str) -> Role:
        """Gets a specific role.

        Args:
            role_name: Name of the role to get.

        Returns:
            The requested role.

        Raises:
            KeyError: If no role with the given name exists.
        """

    @abstractmethod
    def _create_role(self, role_name: str) -> Role:
        """Creates a new role.

        Args:
            role_name: Unique role name.

        Returns:
             The newly created role.

        Raises:
            EntityExistsError: If a role with the given name already exists.
        """

    @abstractmethod
    def _delete_role(self, role_name: str) -> None:
        """Deletes a role.

        Args:
            role_name: Name of the role to delete.

        Raises:
            KeyError: If no role with the given name exists.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def get_users_for_team(self, team_name: str) -> List[User]:
        """Fetches all users of a team.

        Args:
            team_name: Name of the team.

        Returns:
            List of users that are part of the team.

        Raises:
            KeyError: If no team with the given name exists.
        """

    @abstractmethod
    def get_teams_for_user(self, user_name: str) -> List[Team]:
        """Fetches all teams for a user.

        Args:
            user_name: Name of the user.

        Returns:
            List of teams that the user is part of.

        Raises:
            KeyError: If no user with the given name exists.
        """

    @abstractmethod
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

    @abstractmethod
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

    # Pipelines and pipeline runs

    @abstractmethod
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

    @abstractmethod
    def get_pipeline_runs(
        self, pipeline_name: str, project_name: Optional[str] = None
    ) -> List[PipelineRunWrapper]:
        """Gets pipeline runs.

        Args:
            pipeline_name: Name of the pipeline for which to get runs.
            project_name: Optional name of the project from which to get the
                pipeline runs.
        """

    @abstractmethod
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

    # Stack component flavors

    @property
    @abstractmethod
    def flavors(self) -> List[FlavorWrapper]:
        """All registered flavors.

        Returns:
            A list of all registered flavors.
        """

    @abstractmethod
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

    @abstractmethod
    def get_flavors_by_type(
        self, component_type: StackComponentType
    ) -> List[FlavorWrapper]:
        """Fetch all flavor defined for a specific stack component type.

        Args:
            component_type: The type of the stack component.

        Returns:
            List of all the flavors for the given stack component type.
        """

    @abstractmethod
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

    # Common code (user facing):

    @property
    def stacks(self) -> List[StackWrapper]:
        """All stacks registered in this zen store."""
        return [
            self._stack_from_dict(name, conf)
            for name, conf in self.stack_configurations.items()
        ]

    def get_stack(self, name: str) -> StackWrapper:
        """Fetch a stack by name.

        Args:
            name: The name of the stack to retrieve.

        Returns:
            StackWrapper instance if the stack exists.

        Raises:
            KeyError: If no stack exists for the given name.
        """
        return self._stack_from_dict(name, self.get_stack_configuration(name))

    def _register_stack(self, stack: StackWrapper) -> None:
        """Register a stack and its components.

        If any of the stack's components aren't registered in the zen store
        yet, this method will try to register them as well.

        Args:
            stack: The stack to register.

        Raises:
            StackExistsError: If a stack with the same name already exists.
            StackComponentExistsError: If a component of the stack wasn't
                registered and a different component with the same name
                already exists.
        """
        try:
            self.get_stack(stack.name)
        except KeyError:
            pass
        else:
            raise StackExistsError(
                f"Unable to register stack with name '{stack.name}': Found "
                f"existing stack with this name."
            )

        def __check_component(
            component: ComponentWrapper,
        ) -> Tuple[StackComponentType, str]:
            """Try to register a stack component, if it doesn't exist.

            Args:
                component: StackComponentWrapper to register.

            Raises:
                StackComponentExistsError: If a component with same name exists.
            """
            try:
                existing_component = self.get_stack_component(
                    component_type=component.type, name=component.name
                )
                if existing_component.uuid != component.uuid:
                    raise StackComponentExistsError(
                        f"Unable to register one of the stacks components: "
                        f"A component of type '{component.type}' and name "
                        f"'{component.name}' already exists."
                    )
            except KeyError:
                self._register_stack_component(component)
            return component.type, component.name

        stack_configuration = {
            typ: name for typ, name in map(__check_component, stack.components)
        }
        self._save_stack(stack.name, stack_configuration)
        logger.info("Registered stack with name '%s'.", stack.name)

    def _update_stack(self, name: str, stack: StackWrapper) -> None:
        """Update a stack and its components.

        If any of the stack's components aren't registered in the stack store
        yet, this method will try to register them as well.

        Args:
            name: The original name of the stack.
            stack: The new stack to use in the update.

        Raises:
            DoesNotExistException: If no stack exists with the given name.
        """
        try:
            self.get_stack(name)
        except KeyError:
            raise KeyError(
                f"Unable to update stack with name '{stack.name}': No existing "
                f"stack found with this name."
            )

        try:
            renamed_stack = self.get_stack(stack.name)
            if (name != stack.name) and renamed_stack:
                raise StackExistsError(
                    f"Unable to update stack with name '{stack.name}': Found "
                    f"existing stack with this name."
                )
        except KeyError:
            pass

        def __check_component(
            component: ComponentWrapper,
        ) -> Tuple[StackComponentType, str]:
            try:
                _ = self.get_stack_component(
                    component_type=component.type, name=component.name
                )
            except KeyError:
                self._register_stack_component(component)
            return component.type, component.name

        stack_configuration = {
            typ: name for typ, name in map(__check_component, stack.components)
        }
        self._save_stack(stack.name, stack_configuration)

        logger.info("Updated stack with name '%s'.", name)
        if name != stack.name:
            self.deregister_stack(name)

    def get_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> ComponentWrapper:
        """Get a registered stack component.

        Raises:
            KeyError: If no component with the requested type and name exists.
        """
        flavor, config = self._get_component_flavor_and_config(
            component_type, name=name
        )
        uuid = yaml.safe_load(base64.b64decode(config).decode())["uuid"]
        return ComponentWrapper(
            type=component_type,
            flavor=flavor,
            name=name,
            uuid=uuid,
            config=config,
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
        return [
            self.get_stack_component(component_type=component_type, name=name)
            for name in self._get_stack_component_names(component_type)
        ]

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
        for stack_name, stack_config in self.stack_configurations.items():
            if stack_config.get(component_type) == name:
                raise ValueError(
                    f"Unable to deregister stack component (type: "
                    f"{component_type}, name: {name}) that is part of a "
                    f"registered stack (stack name: '{stack_name}')."
                )
        self._delete_stack_component(component_type, name=name)

    def register_default_stack(self) -> None:
        """Populates the store with the default Stack.

        The default stack contains a local orchestrator,
        a local artifact store and a local SQLite metadata store.
        """
        stack = Stack.default_local_stack()
        sw = StackWrapper.from_stack(stack)
        self._register_stack(sw)
        metadata = {c.type.value: c.flavor for c in sw.components}
        metadata["store_type"] = self.type.value
        self._track_event(
            AnalyticsEvent.REGISTERED_DEFAULT_STACK, metadata=metadata
        )

    def create_default_user(self) -> None:
        """Creates a default user."""
        try:
            self.get_user(user_name=DEFAULT_USERNAME)
        except KeyError:
            # Use private interface and send custom tracking event
            self._track_event(AnalyticsEvent.CREATED_DEFAULT_USER)
            self._create_user(user_name=DEFAULT_USERNAME)

    # Common code (internal implementations, private):

    def _track_event(
        self,
        event: Union[str, AnalyticsEvent],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if self._track_analytics:
            return track_event(event, metadata)
        return False

    def _stack_from_dict(
        self, name: str, stack_configuration: Dict[StackComponentType, str]
    ) -> StackWrapper:
        """Build a StackWrapper from stored configurations"""
        stack_components = [
            self.get_stack_component(
                component_type=component_type, name=component_name
            )
            for component_type, component_name in stack_configuration.items()
        ]
        return StackWrapper(name=name, components=stack_components)

    # Public facing APIs
    # TODO [ENG-894]: Refactor these with the proxy pattern, as noted in
    #  the [review comment](https://github.com/zenml-io/zenml/pull/589#discussion_r875003334)

    def register_stack_component(
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
        analytics_metadata = {
            "type": component.type.value,
            "flavor": component.flavor,
        }
        self._track_event(
            AnalyticsEvent.REGISTERED_STACK_COMPONENT,
            metadata=analytics_metadata,
        )
        return self._register_stack_component(component)

    def update_stack_component(
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
        analytics_metadata = {
            "type": component.type.value,
            "flavor": component.flavor,
        }
        self._track_event(
            AnalyticsEvent.UPDATED_STACK_COMPONENT,
            metadata=analytics_metadata,
        )
        return self._update_stack_component(name, component_type, component)

    def deregister_stack(self, name: str) -> None:
        """Delete a stack from storage.

        Args:
            name: The name of the stack to be deleted.

        Raises:
            KeyError: If no stack exists for the given name.
        """
        # No tracking events, here for consistency
        return self._deregister_stack(name)

    def create_user(self, user_name: str) -> User:
        """Creates a new user.

        Args:
            user_name: Unique username.

        Returns:
             The newly created user.

        Raises:
            EntityExistsError: If a user with the given name already exists.
        """
        self._track_event(AnalyticsEvent.CREATED_USER)
        return self._create_user(user_name)

    def delete_user(self, user_name: str) -> None:
        """Deletes a user.

        Args:
            user_name: Name of the user to delete.

        Raises:
            KeyError: If no user with the given name exists.
        """
        self._track_event(AnalyticsEvent.DELETED_USER)
        return self._delete_user(user_name)

    def get_user(self, user_name: str) -> User:
        """Gets a specific user.

        Args:
            user_name: Name of the user to get.

        Returns:
            The requested user.

        Raises:
            KeyError: If no user with the given name exists.
        """
        # No tracking events, here for consistency
        return self._get_user(user_name)

    def create_team(self, team_name: str) -> Team:
        """Creates a new team.

        Args:
            team_name: Unique team name.

        Returns:
             The newly created team.

        Raises:
            EntityExistsError: If a team with the given name already exists.
        """
        self._track_event(AnalyticsEvent.CREATED_TEAM)
        return self._create_team(team_name)

    def get_team(self, team_name: str) -> Team:
        """Gets a specific team.

        Args:
            team_name: Name of the team to get.

        Returns:
            The requested team.

        Raises:
            KeyError: If no team with the given name exists.
        """
        # No tracking events, here for consistency
        return self._get_team(team_name)

    def delete_team(self, team_name: str) -> None:
        """Deletes a team.

        Args:
            team_name: Name of the team to delete.

        Raises:
            KeyError: If no team with the given name exists.
        """
        self._track_event(AnalyticsEvent.DELETED_TEAM)
        return self._delete_team(team_name)

    def get_project(self, project_name: str) -> Project:
        """Gets a specific project.

        Args:
            project_name: Name of the project to get.

        Returns:
            The requested project.

        Raises:
            KeyError: If no project with the given name exists.
        """
        # No tracking events, here for consistency
        return self._get_project(project_name)

    def create_project(
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
        self._track_event(AnalyticsEvent.CREATED_PROJECT)
        return self._create_project(project_name, description)

    def delete_project(self, project_name: str) -> None:
        """Deletes a project.

        Args:
            project_name: Name of the project to delete.

        Raises:
            KeyError: If no project with the given name exists.
        """
        self._track_event(AnalyticsEvent.DELETED_PROJECT)
        return self._delete_project(project_name)

    def get_role(self, role_name: str) -> Role:
        """Gets a specific role.

        Args:
            role_name: Name of the role to get.

        Returns:
            The requested role.

        Raises:
            KeyError: If no role with the given name exists.
        """
        # No tracking events, here for consistency
        return self._get_role(role_name)

    def create_role(self, role_name: str) -> Role:
        """Creates a new role.

        Args:
            role_name: Unique role name.

        Returns:
             The newly created role.

        Raises:
            EntityExistsError: If a role with the given name already exists.
        """
        self._track_event(AnalyticsEvent.CREATED_ROLE)
        return self._create_role(role_name)

    def delete_role(self, role_name: str) -> None:
        """Deletes a role.

        Args:
            role_name: Name of the role to delete.

        Raises:
            KeyError: If no role with the given name exists.
        """
        self._track_event(AnalyticsEvent.DELETED_ROLE)
        return self._delete_role(role_name)

    def create_flavor(
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

        analytics_metadata = {
            "type": stack_component_type.value,
        }
        track_event(
            AnalyticsEvent.CREATED_FLAVOR,
            metadata=analytics_metadata,
        )
        return self._create_flavor(source, name, stack_component_type)

    def register_stack(self, stack: StackWrapper) -> None:
        """Register a stack and its components.

        If any of the stack's components aren't registered in the zen store
        yet, this method will try to register them as well.

        Args:
            stack: The stack to register.

        Raises:
            StackExistsError: If a stack with the same name already exists.
            StackComponentExistsError: If a component of the stack wasn't
                registered and a different component with the same name
                already exists.
        """
        metadata = {c.type.value: c.flavor for c in stack.components}
        metadata["store_type"] = self.type.value
        track_event(AnalyticsEvent.REGISTERED_STACK, metadata=metadata)
        return self._register_stack(stack)

    def update_stack(self, name: str, stack: StackWrapper) -> None:
        """Update a stack and its components.

        If any of the stack's components aren't registered in the stack store
        yet, this method will try to register them as well.

        Args:
            name: The original name of the stack.
            stack: The new stack to use in the update.

        Raises:
            DoesNotExistException: If no stack exists with the given name.
        """
        metadata = {c.type.value: c.flavor for c in stack.components}
        metadata["store_type"] = self.type.value
        track_event(AnalyticsEvent.UPDATED_STACK, metadata=metadata)
        return self._update_stack(name, stack)
