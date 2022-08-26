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
"""Base Zen Store implementation."""

import base64
from abc import abstractmethod
from pathlib import Path, PurePath
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, Union
from uuid import UUID

import yaml
from pydantic import BaseModel

from zenml.config.store_config import StoreConfiguration
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
    StoreAssociation,
    Team,
    User,
)
from zenml.zen_stores.models.pipeline_models import PipelineRunWrapper

logger = get_logger(__name__)

DEFAULT_USERNAME = "default"


class BaseZenStore(BaseModel):
    """Base class for accessing and persisting ZenML core objects.

    Attributes:
        config: The configuration of the store.
        track_analytics: Only send analytics if set to `True`.
    """

    config: StoreConfiguration
    track_analytics: bool = True

    TYPE: ClassVar[StoreType]
    CONFIG_TYPE: ClassVar[Type[StoreConfiguration]]

    def __init__(
        self,
        skip_default_registrations: bool = False,
        **kwargs: Any,
    ) -> None:
        """Create and initialize a store.

        Args:
            skip_default_registrations: If `True`, the creation of the default
                stack and user in the store will be skipped.
            **kwargs: Additional keyword arguments to pass to the Pydantic
                constructor.

        Raises:
            RuntimeError: If the store cannot be initialized.
        """
        super().__init__(**kwargs)

        try:
            self._initialize()
        except Exception as e:
            raise RuntimeError(
                f"Error initializing {self.type.value} store with URL "
                f"'{self.url}': {str(e)}"
            ) from e

        if not skip_default_registrations:
            self._initialize_database()

    @staticmethod
    def get_store_class(type: StoreType) -> Type["BaseZenStore"]:
        """Returns the class of the given store type.

        Args:
            type: The type of the store to get the class for.

        Returns:
            The class of the given store type or None if the type is unknown.

        Raises:
            TypeError: If the store type is unsupported.
        """
        from zenml.zen_stores import RestZenStore, SqlZenStore

        store_class = {
            StoreType.SQL: SqlZenStore,
            StoreType.REST: RestZenStore,
        }.get(type)

        if store_class is None:
            raise TypeError(
                f"No store implementation found for store type "
                f"`{type.value}`."
            )

        return store_class

    @staticmethod
    def create_store(
        config: StoreConfiguration,
        skip_default_registrations: bool = False,
        **kwargs: Any,
    ) -> "BaseZenStore":
        """Create and initialize a store from a store configuration.

        Args:
            config: The store configuration to use.
            skip_default_registrations: If `True`, the creation of the default
                stack and user in the store will be skipped.
            **kwargs: Additional keyword arguments to pass to the store class

        Returns:
            The initialized store.
        """
        logger.debug(f"Creating store with config '{config}'...")
        store_class = BaseZenStore.get_store_class(config.type)
        store = store_class(
            config=config,
            skip_default_registrations=skip_default_registrations,
        )
        return store

    @staticmethod
    def get_default_store_config(path: str) -> StoreConfiguration:
        """Get the default store configuration.

        The default store is a SQLite store that saves the DB contents on the
        local filesystem.

        Args:
            path: The local path where the store DB will be stored.

        Returns:
            The default store configuration.
        """
        from zenml.zen_stores.sql_zen_store import (
            SqlZenStore,
            SqlZenStoreConfiguration,
        )

        config = SqlZenStoreConfiguration(
            type=StoreType.SQL, url=SqlZenStore.get_local_url(path)
        )
        return config

    def _initialize_database(self) -> None:
        """Initialize the database on first use."""
        if self.stacks_empty:
            logger.info("Initializing database...")
            self.register_default_stack()
        self.create_default_user()

    @property
    def url(self) -> str:
        """The URL of the store.

        Returns:
            The URL of the store.
        """
        return self.config.url

    @property
    def type(self) -> StoreType:
        """The type of the store.

        Returns:
            The type of the store.
        """
        return self.TYPE

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

    # Public Interface:

    @property
    @abstractmethod
    def stacks_empty(self) -> bool:
        """Check if the store is empty (no stacks are configured).

        The implementation of this method should check if the store is empty
        without having to load all the stacks from the persistent storage.

        Returns:
            True if the store is empty, False otherwise.
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
    def _initialize(self) -> None:
        """Initialize the store.

        This method is called immediately after the store is created. It should
        be used to set up the backend (database, connection etc.).
        """

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
    def active_user_name(self) -> str:
        """Gets the active username.

        Returns:
            The active username.
        """

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

    @property
    @abstractmethod
    def store_associations(self) -> List[StoreAssociation]:
        """Fetches all artifact/metadata store associations.

        Returns:
            A list of all artifact/metadata store associations.
        """

    @abstractmethod
    def create_store_association(
        self,
        artifact_store_uuid: UUID,
        metadata_store_uuid: UUID,
    ) -> StoreAssociation:
        """Creates an association between an artifact- and a metadata store.

        Args:
            artifact_store_uuid: The UUID of the artifact store.
            metadata_store_uuid: The UUID of the metadata store.

        Returns:
            The newly created store association.
        """

    @abstractmethod
    def get_store_associations_for_artifact_store(
        self,
        artifact_store_uuid: UUID,
    ) -> List[StoreAssociation]:
        """Fetches all associations for a given artifact store.

        Args:
            artifact_store_uuid: The UUID of the selected artifact store.

        Returns:
            A list of store associations for the given artifact store.
        """

    @abstractmethod
    def get_store_associations_for_metadata_store(
        self,
        metadata_store_uuid: UUID,
    ) -> List[StoreAssociation]:
        """Fetches all associations for a given metadata store.

        Args:
            metadata_store_uuid: The UUID of the selected metadata store.

        Returns:
            A list of store associations for the given metadata store.
        """

    @abstractmethod
    def get_store_associations_for_artifact_and_metadata_store(
        self,
        artifact_store_uuid: UUID,
        metadata_store_uuid: UUID,
    ) -> List[StoreAssociation]:
        """Fetches all associations for a given artifact/metadata store pair.

        Args:
            artifact_store_uuid: The UUID of the selected artifact store.
            metadata_store_uuid: The UUID of the selected metadata store.

        Returns:
            A list of store associations for the given combination.
        """

    @abstractmethod
    def delete_store_association_for_artifact_and_metadata_store(
        self,
        artifact_store_uuid: UUID,
        metadata_store_uuid: UUID,
    ) -> None:
        """Deletes associations between a given artifact/metadata store pair.

        Args:
            artifact_store_uuid: The UUID of the selected artifact store.
            metadata_store_uuid: The UUID of the selected metadata store.
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
        """All stacks registered in this zen store.

        Returns:
            A list of all stacks registered in this zen store.
        """
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

            Returns:
                The type and name of the component.

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
            KeyError: If no stack exists with the given name.
            StackExistsError: If a stack with the same name already exists.
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
            """Try to register a stack component, if it doesn't exist.

            Args:
                component: StackComponentWrapper to register.

            Returns:
                The type and name of the component.
            """
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

        Args:
            component_type: The type of the component.
            name: The name of the component.

        Returns:
            The component.
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
        # For the default stack, we have to set up the association manually.
        # As we can not use the repo/store yet to check the previously defined
        # associations.
        self.create_store_association(
            artifact_store_uuid=stack.artifact_store.uuid,
            metadata_store_uuid=stack.metadata_store.uuid,
        )
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
        """Track an analytics event.

        Args:
            event: The event to track.
            metadata: Additional metadata to track with the event.

        Returns:
            True if the event was successfully tracked, False otherwise.
        """
        if self.track_analytics:
            return track_event(event, metadata)
        return False

    def _stack_from_dict(
        self, name: str, stack_configuration: Dict[StackComponentType, str]
    ) -> StackWrapper:
        """Build a StackWrapper from stored configurations.

        Args:
            name: The name of the stack.
            stack_configuration: The configuration of the stack.

        Returns:
            A StackWrapper instance.
        """
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

        Returns:
            None
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

        Returns:
            The updated stack configuration.
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

    @property
    def active_user(self) -> "User":
        """The active user.

        Returns:
            The active user.
        """
        return self.get_user(self.active_user_name)

    def create_user(self, user_name: str) -> User:
        """Creates a new user.

        Args:
            user_name: Unique username.

        Returns:
            The newly created user.
        """
        self._track_event(AnalyticsEvent.CREATED_USER)
        return self._create_user(user_name)

    def delete_user(self, user_name: str) -> None:
        """Deletes a user.

        Args:
            user_name: Name of the user to delete.

        Returns:
            None.
        """
        self._track_event(AnalyticsEvent.DELETED_USER)
        return self._delete_user(user_name)

    def get_user(self, user_name: str) -> User:
        """Gets a specific user.

        Args:
            user_name: Name of the user to get.

        Returns:
            The requested user.
        """
        # No tracking events, here for consistency
        return self._get_user(user_name)

    def create_team(self, team_name: str) -> Team:
        """Creates a new team.

        Args:
            team_name: Unique team name.

        Returns:
            The newly created team.
        """
        self._track_event(AnalyticsEvent.CREATED_TEAM)
        return self._create_team(team_name)

    def get_team(self, team_name: str) -> Team:
        """Gets a specific team.

        Args:
            team_name: Name of the team to get.

        Returns:
            The requested team.
        """
        # No tracking events, here for consistency
        return self._get_team(team_name)

    def delete_team(self, team_name: str) -> None:
        """Deletes a team.

        Args:
            team_name: Name of the team to delete.

        Returns:
            None
        """
        self._track_event(AnalyticsEvent.DELETED_TEAM)
        return self._delete_team(team_name)

    def get_project(self, project_name: str) -> Project:
        """Gets a specific project.

        Args:
            project_name: Name of the project to get.

        Returns:
            The requested project.
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
        """
        self._track_event(AnalyticsEvent.CREATED_PROJECT)
        return self._create_project(project_name, description)

    def delete_project(self, project_name: str) -> None:
        """Deletes a project.

        Args:
            project_name: Name of the project to delete.

        Returns:
            None.
        """
        self._track_event(AnalyticsEvent.DELETED_PROJECT)
        return self._delete_project(project_name)

    def get_role(self, role_name: str) -> Role:
        """Gets a specific role.

        Args:
            role_name: Name of the role to get.

        Returns:
            The requested role.
        """
        # No tracking events, here for consistency
        return self._get_role(role_name)

    def create_role(self, role_name: str) -> Role:
        """Creates a new role.

        Args:
            role_name: Unique role name.

        Returns:
            The newly created role.
        """
        self._track_event(AnalyticsEvent.CREATED_ROLE)
        return self._create_role(role_name)

    def delete_role(self, role_name: str) -> None:
        """Deletes a role.

        Args:
            role_name: Name of the role to delete

        Returns:
            None.
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

        Returns:
            None
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

        Returns:
            None.
        """
        metadata = {c.type.value: c.flavor for c in stack.components}
        metadata["store_type"] = self.type.value
        track_event(AnalyticsEvent.UPDATED_STACK, metadata=metadata)
        return self._update_stack(name, stack)

    def deregister_stack(self, name: str) -> None:
        """Delete a stack from storage.

        Args:
            name: The name of the stack to be deleted.

        Returns:
            None.
        """
        # No tracking events, here for consistency
        return self._deregister_stack(name)

    class Config:
        """Pydantic configuration class."""

        # Validate attributes when assigning them. We need to set this in order
        # to have a mix of mutable and immutable attributes
        validate_assignment = True
        # Ignore extra attributes from configs of previous ZenML versions
        extra = "ignore"
        # all attributes with leading underscore are private and therefore
        # are mutable and not included in serialization
        underscore_attrs_are_private = True
