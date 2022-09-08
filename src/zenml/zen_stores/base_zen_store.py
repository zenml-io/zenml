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
import os
from abc import abstractmethod
from pathlib import Path, PurePath
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, Union
from uuid import UUID

from pydantic import BaseModel

from zenml.config.store_config import StoreConfiguration
from zenml.enums import ExecutionStatus, StackComponentType, StoreType
from zenml.logger import get_logger
from zenml.models import (
    ArtifactModel,
    CodeRepositoryModel,
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
from zenml.utils import io_utils
from zenml.utils.analytics_utils import AnalyticsEvent, track_event

logger = get_logger(__name__)

DEFAULT_USERNAME = "default"
DEFAULT_PROJECT_NAME = "default"
DEFAULT_STACK_NAME = "default"


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
        from zenml.zen_stores.sql_zen_store import SqlZenStore

        # from zenml.zen_stores.rest_zen_store import RestZenStore

        store_class = {
            StoreType.SQL: SqlZenStore,
            # StoreType.REST: RestZenStore,
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
        self.create_default_user()
        self.create_default_project()
        if len(self.list_stacks(self.default_project_id)) == 0:
            logger.info("Initializing database...")
            self.register_default_stack()

    @property
    def default_user_id(self) -> UUID:
        """Get the ID of the default user, or None if it doesn't exist."""
        try:
            return self.get_user(DEFAULT_USERNAME).id
        except KeyError:
            return None

    @property
    def default_project_id(self) -> UUID:
        """Get the ID of the default project, or None if it doesn't exist."""
        try:
            return self.get_project(DEFAULT_PROJECT_NAME).id
        except KeyError:
            return None

    def create_default_user(self) -> None:
        """Creates a default user."""
        if not self.default_user_id:
            self._track_event(AnalyticsEvent.CREATED_DEFAULT_USER)
            self._create_user(UserModel(name=DEFAULT_USERNAME))

    def create_default_project(self) -> None:
        """Creates a default project."""
        if not self.default_project_id:
            self._track_event(AnalyticsEvent.CREATED_DEFAULT_PROJECT)
            self._create_project(ProjectModel(name=DEFAULT_PROJECT_NAME))

    def register_default_stack(self) -> None:
        """Populates the store with the default Stack.

        The default stack contains a local orchestrator and a local artifact
        store.
        """
        from zenml.config.global_config import GlobalConfiguration

        # Register the default orchestrator
        # try:
        orchestrator = self.register_stack_component(
            user_id=self.default_user_id,
            project_name_or_id=self.default_project_id,
            component=ComponentModel(
                name="default",
                type=StackComponentType.ORCHESTRATOR,
                flavor_name="local",
                configuration={},
            ),
        )
        # except StackComponentExistsError:
        #     logger.warning("Default Orchestrator exists already, "
        #                    "skipping creation ...")

        # Register the default artifact store
        artifact_store_path = os.path.join(
            GlobalConfiguration().config_directory,
            "local_stores",
            "default_local_store",
        )
        io_utils.create_dir_recursive_if_not_exists(artifact_store_path)

        # try:
        artifact_store = self.register_stack_component(
            user_id=self.default_user_id,
            project_name_or_id=self.default_project_id,
            component=ComponentModel(
                name="default",
                type=StackComponentType.ARTIFACT_STORE,
                flavor_name="local",
                configuration={"path": artifact_store_path},
            ),
        )
        # except StackComponentExistsError:
        #     logger.warning("Default Artifact Store exists already, "
        #                    "skipping creation ...")

        components = {c.type: c for c in [orchestrator, artifact_store]}
        # Register the default stack
        stack = StackModel(
            name="default", components=components, is_shared=True
        )
        self._register_stack(
            user_id=self.default_user_id,
            project_name_or_id=self.default_project_id,
            stack=stack,
        )
        self._track_event(
            AnalyticsEvent.REGISTERED_DEFAULT_STACK,
        )

    @property
    def stacks(self) -> List[StackModel]:
        """All stacks registered in this zen store.

        Returns:
            A list of all stacks registered in this zen store.
        """
        return self.list_stacks(project_name_or_id=self.default_project_id)

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

    # .--------.
    # | STACKS |
    # '--------'

    # TODO: [ALEX] add filtering param(s)
    def list_stacks(
        self,
        project_name_or_id: Union[str, UUID],
        user_id: Optional[UUID] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[StackModel]:
        """List all stacks within the filter.

        Args:
            project_name_or_id: Id or name of the Project containing the stack
            user_id: Optionally filter stack components by the owner
            name: Optionally filter stack component by name
            is_shared: Optionally filter out stack component by the `is_shared`
                       flag
        Returns:
            A list of all stacks.

        Raises:
            KeyError: if the project doesn't exist.
        """
        return self._list_stacks(project_name_or_id, user_id, name, is_shared)

    @abstractmethod
    def _list_stacks(
        self,
        project_name_or_id: Union[str, UUID],
        owner: Optional[UUID] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[StackModel]:
        """List all stacks within the filter.

        Args:
            project_name_or_id: Id or name of the Project containing the stack
            user_id: Optionally filter stack components by the owner
            name: Optionally filter stack component by name
            is_shared: Optionally filter out stack component by the `is_shared`
                       flag
        Returns:
            A list of all stacks.
        """

    @abstractmethod
    def _initialize(self) -> None:
        """Initialize the store.

        This method is called immediately after the store is created. It should
        be used to set up the backend (database, connection etc.).
        """

    def get_stack(self, stack_id: UUID) -> StackModel:
        """Get a stack by id.

        Args:
            stack_id: The id of the stack to get.

        Returns:
            The stack with the given id.

        Raises:
            KeyError: if the stack doesn't exist.
        """
        return self._get_stack(stack_id)

    @abstractmethod
    def _get_stack(self, stack_id: UUID) -> StackModel:
        """Get a stack by ID.

        Args:
            stack_id: The ID of the stack to get.

        Returns:
            The stack.

        Raises:
            KeyError: if the stack doesn't exist.
        """

    def register_stack(
        self,
        user_id: UUID,
        project_name_or_id: Union[str, UUID],
        stack: StackModel,
    ) -> StackModel:
        """Register a new stack.

        Args:
            stack: The stack to register.
            user_id: The user that is registering this stack
            project_name_or_id: The project within which that stack is
                                registered

        Returns:
            The registered stack.

        Raises:
            StackExistsError: In case a stack with that name is already owned
                by this user on this project.
        """
        metadata = {ct: c.flavor_name for ct, c in stack.components.items()}
        metadata["store_type"] = self.type.value
        self._track_event(AnalyticsEvent.REGISTERED_STACK, metadata=metadata)
        return self._register_stack(
            stack=stack, user_id=user_id, project_name_or_id=project_name_or_id
        )

    @abstractmethod
    def _register_stack(
        self,
        user_id: UUID,
        project_name_or_id: Union[str, UUID],
        stack: StackModel,
    ) -> StackModel:
        """Register a new stack.

        Args:
            stack: The stack to register.
            user_id: The user that is registering this stack
            project_name_or_id: The project within which that stack is
                                registered

        Returns:
            The registered stack.

        Raises:
            StackExistsError: In case a stack with that name is already owned
                by this user on this project.
        """

    def update_stack(
        self,
        stack: StackModel,
    ) -> StackModel:
        """Update an existing stack.

        Args:
            stack: The stack to update.

        Returns:
            The updated stack.
        """
        metadata = {c.type: c.flavor_name for c in stack.components.values()}
        metadata["store_type"] = self.type.value
        track_event(AnalyticsEvent.UPDATED_STACK, metadata=metadata)
        return self._update_stack(stack=stack)

    @abstractmethod
    def _update_stack(
        self,
        stack: StackModel,
    ) -> StackModel:
        """Update a stack.

        Args:
            stack_id: The ID of the stack to update.
            stack: The stack to use for the update.

        Returns:
            The updated stack.

        Raises:
            KeyError: if the stack doesn't exist.
        """

    def delete_stack(self, stack_id: UUID) -> None:
        """Delete a stack.

        Args:
            stack_id: The id of the stack to delete.
        """
        # No tracking events, here for consistency
        self._delete_stack(stack_id)

    @abstractmethod
    def _delete_stack(self, stack_id: UUID) -> None:
        """Delete a stack.

        Args:
            stack_id: The ID of the stack to delete.

        Raises:
            KeyError: if the stack doesn't exist.
        """

    #  .-----------------.
    # | STACK COMPONENTS |
    # '------------------'

    # TODO: [ALEX] add filtering param(s)
    def list_stack_components(
        self,
        project_name_or_id: Union[str, UUID],
        type: Optional[str] = None,
        flavor_name: Optional[str] = None,
        user_id: Optional[UUID] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[ComponentModel]:
        """List all stack components within the filter.

        Args:
            project_name_or_id: Id or name of the Project containing the stack
                                component
            type: Optionally filter by type of stack component
            flavor_name: Optionally filter by flavor
            user_id: Optionally filter stack components by the owner
            name: Optionally filter stack component by name
            is_shared: Optionally filter out stack component by the `is_shared`
                       flag

        Returns:
            All stack components currently registered.
        """
        return self._list_stack_components(
            project_name_or_id=project_name_or_id,
            type=type,
            flavor_name=flavor_name,
            user_id=user_id,
            name=name,
            is_shared=is_shared,
        )

    @abstractmethod
    def _list_stack_components(
        self,
        project_name_or_id: Union[str, UUID],
        type: Optional[str] = None,
        flavor_name: Optional[str] = None,
        user_id: Optional[UUID] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[ComponentModel]:
        """List all stack components within the filter.

        Args:
            project_name_or_id: Union[str, UUID],
            type: Optionally filter by type of stack component
            flavor_name: Optionally filter by flavor
            owner: Optionally filter stack components by the owner
            name: Optionally filter stack component by name
            is_shared: Optionally filter out stack component by the `is_shared`
                       flag

        Returns:
            A list of all stack components.
        """

    def get_stack_component(self, component_id: UUID) -> ComponentModel:
        """Get a stack component by id.

        Args:
            component_id: The id of the stack component to get.

        Returns:
            The stack component with the given id.
        """
        return self._get_stack_component(component_id)

    @abstractmethod
    def _get_stack_component(self, component_id: UUID) -> ComponentModel:
        """Get a stack component by ID.

        Args:
            component_id: The ID of the stack component to get.

        Returns:
            The stack component.

        Raises:
            KeyError: if the stack component doesn't exist.
        """

    def register_stack_component(
        self,
        user_id: UUID,
        project_name_or_id: Union[str, UUID],
        component: ComponentModel,
    ) -> ComponentModel:
        """Create a stack component.

        Args:
            user_id: The user that created the stack component.
            project_name_or_id: The project the stack component is created in.
            component: The stack component to create.

        Returns:
            The created stack component.
        """
        return self._register_stack_component(
            user_id=user_id,
            project_name_or_id=project_name_or_id,
            component=component,
        )

    @abstractmethod
    def _register_stack_component(
        self,
        user_id: UUID,
        project_name_or_id: Union[str, UUID],
        component: ComponentModel,
    ) -> ComponentModel:
        """Create a stack component.

        Args:
            user_id: The user that created the stack component.
            project_name_or_id: The project the stack component is created in.
            component: The stack component to create.

        Returns:
            The created stack component.
        """

    def update_stack_component(
        self,
        component_id: UUID,
        component: ComponentModel,
    ) -> ComponentModel:
        """Update an existing stack component.

        Args:
            component: The stack component to use for the update.

        Returns:
            The updated stack component.
        """
        analytics_metadata = {
            "type": component.type.value,
            "flavor": component.flavor_name,
        }
        self._track_event(
            AnalyticsEvent.UPDATED_STACK_COMPONENT,
            metadata=analytics_metadata,
        )
        return self._update_stack_component(component_id=component_id,
                                            component=component)

    @abstractmethod
    def _update_stack_component(
        self,
        component_id: UUID,
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

    def delete_stack_component(self, component_id: UUID) -> None:
        """Delete a stack component.

        Args:
            component_id: The id of the stack component to delete.

        Raises:
            KeyError: if the stack component doesn't exist.
        """
        self._delete_stack_component(component_id)

    @abstractmethod
    def _delete_stack_component(self, component_id: UUID) -> None:
        """Delete a stack component.

        Args:
            component_id: The ID of the stack component to delete.

        Raises:
            KeyError: if the stack component doesn't exist.
        """

    def get_stack_component_side_effects(
        self, component_id: str, run_id: str, pipeline_id: str, stack_id: str
    ) -> Dict[Any, Any]:
        """Get the side effects of a stack component.

        Args:
            component_id: The id of the stack component to get side effects for.
            run_id: The id of the run to get side effects for.
            pipeline_id: The id of the pipeline to get side effects for.
            stack_id: The id of the stack to get side effects for.
        """
        return self._get_stack_component_side_effects(
            component_id, run_id, pipeline_id, stack_id
        )

    @abstractmethod
    def _get_stack_component_side_effects(
        self, component_id: str, run_id: str, pipeline_id: str, stack_id: str
    ) -> Dict[Any, Any]:
        """Get the side effects of a stack component.

        Args:
            component_id: The ID of the stack component to get side effects for.
            run_id: The ID of the run to get side effects for.
            pipeline_id: The ID of the pipeline to get side effects for.
            stack_id: The ID of the stack to get side effects for.
        """

    def list_stack_component_types(self) -> List[StackComponentType]:
        """List all stack component types.

        Returns:
            A list of all stack component types.
        """
        return self._list_stack_component_types()

    @abstractmethod
    def _list_stack_component_types(self) -> List[StackComponentType]:
        """List all stack component types.

        Returns:
            A list of all stack component types.
        """

    def list_stack_component_flavors_by_type(
        self,
        component_type: StackComponentType,
    ) -> List[FlavorModel]:
        """List all stack component flavors by type.

        Args:
            component_type: The stack component for which to get flavors.

        Returns:
            List of stack component flavors.
        """
        return self._list_stack_component_flavors_by_type(component_type)

    @abstractmethod
    def _list_stack_component_flavors_by_type(
        self, component_type: StackComponentType
    ) -> List[FlavorModel]:
        """List all stack component flavors by type.

        Args:
            component_type: The stack component for which to get flavors.

        Returns:
            List of stack component flavors.
        """

    #  .------.
    # | USERS |
    # '-------'

    @property
    def active_user(self) -> UserModel:
        """The active user.

        Returns:
            The active user.
        """
        return self.get_user(self.active_user_name)

    @property
    @abstractmethod
    def active_user_name(self) -> str:
        """Gets the active username.

        Returns:
            The active username.
        """

    @property
    def users(self) -> List[UserModel]:
        """All registered users.

        Returns:
            A list of all registered users.
        """
        return self.list_users()

    # TODO: make the invite_token optional
    # TODO: [ALEX] add filtering param(s)
    def list_users(self) -> List[UserModel]:
        """List all users.

        Returns:
            A list of all users.
        """
        return self._list_users()

    @abstractmethod
    def _list_users(self) -> List[UserModel]:
        """List all users.

        Returns:
            A list of all users.
        """

    def create_user(self, user: UserModel) -> UserModel:
        """Creates a new user.

        Args:
            user: The user model to create.

        Returns:
            The newly created user.

        Raises:
            EntityExistsError: If a user with the given name already exists.
        """
        self._track_event(AnalyticsEvent.CREATED_USER)
        return self._create_user(user)

    @abstractmethod
    def _create_user(self, user: UserModel) -> UserModel:
        """Creates a new user.

        Args:
            user: The user model to create.

        Returns:
            The newly created user.

        Raises:
            EntityExistsError: If a user with the given name already exists.
        """

    def get_user(self, user_name_or_id: str) -> UserModel:
        """Gets a specific user.

        Args:
            user_name_or_id: The name or ID of the user to get.

        Returns:
            The requested user, if it was found.

        Raises:
            KeyError: If no user with the given name or ID exists.
        """
        # No tracking events, here for consistency
        return self._get_user(user_name_or_id=user_name_or_id)

    @abstractmethod
    def _get_user(self, user_name_or_id: str) -> UserModel:
        """Gets a specific user.

        Args:
            user_name_or_id: The name or ID of the user to get.

        Returns:
            The requested user, if it was found.

        Raises:
            KeyError: If no user with the given name or ID exists.
        """

    def update_user(self, user_id: str, user: UserModel) -> UserModel:
        """Updates an existing user.

        Args:
            user_id: The ID of the user to update.
            user: The user model to use for the update.

        Returns:
            The updated user.

        Raises:
            KeyError: If no user with the given name exists.
        """
        # No tracking events, here for consistency
        return self._update_user(user_id, user)

    @abstractmethod
    def _update_user(self, user_id: str, user: UserModel) -> UserModel:
        """Update the user.

        Args:
            user_id: The ID of the user to update.
            user: The user model to use for the update.

        Returns:
            The updated user.

        Raises:
            KeyError: If no user with the given name exists.
        """

    def delete_user(self, user_id: str) -> None:
        """Deletes a user.

        Args:
            user_id: The ID of the user to delete.

        Raises:
            KeyError: If no user with the given ID exists.
        """
        self._track_event(AnalyticsEvent.DELETED_USER)
        return self._delete_user(user_id)

    @abstractmethod
    def _delete_user(self, user_id: str) -> None:
        """Deletes a user.

        Args:
            user_id: The ID of the user to delete.

        Raises:
            KeyError: If no user with the given ID exists.
        """

    # TODO: Check whether this needs to be an abstract method or not (probably?)
    @abstractmethod
    def get_invite_token(self, user_id: str) -> str:
        """Gets an invite token for a user.

        Args:
            user_id: ID of the user.

        Returns:
            The invite token for the specific user.
        """

    @abstractmethod
    def invalidate_invite_token(self, user_id: str) -> None:
        """Invalidates an invite token for a user.

        Args:
            user_id: ID of the user.
        """

    #  .------.
    # | TEAMS |
    # '-------'

    @property
    def teams(self) -> List[TeamModel]:
        """List all teams.

        Returns:
            A list of all teams.
        """
        return self._list_teams()

    @abstractmethod
    def _list_teams(self) -> List[TeamModel]:
        """List all teams.

        Returns:
            A list of all teams.
        """

    def create_team(self, team: TeamModel) -> TeamModel:
        """Creates a new team.

        Args:
            team: The team model to create.

        Returns:
            The newly created team.
        """
        self._track_event(AnalyticsEvent.CREATED_TEAM)
        return self._create_team(team)

    @abstractmethod
    def _create_team(self, team: TeamModel) -> TeamModel:
        """Creates a new team.

        Args:
            team: The team model to create.

        Returns:
            The newly created team.

        Raises:
            EntityExistsError: If a team with the given name already exists.
        """

    def get_team(self, team_name_or_id: str) -> TeamModel:
        """Gets a specific team.

        Args:
            team_name_or_id: Name or ID of the team to get.

        Returns:
            The requested team.

        Raises:
            KeyError: If no team with the given name or ID exists.
        """
        # No tracking events, here for consistency
        return self._get_team(team_name_or_id)

    @abstractmethod
    def _get_team(self, team_name_or_id: str) -> TeamModel:
        """Gets a specific team.

        Args:
            team_name_or_id: Name or ID of the team to get.

        Returns:
            The requested team.

        Raises:
            KeyError: If no team with the given name or ID exists.
        """

    def delete_team(self, team_id: str) -> None:
        """Deletes a team.

        Args:
            team_id: ID of the team to delete.

        Raises:
            KeyError: If no team with the given ID exists.
        """
        self._track_event(AnalyticsEvent.DELETED_TEAM)
        return self._delete_team(team_id)

    @abstractmethod
    def _delete_team(self, team_id: str) -> None:
        """Deletes a team.

        Args:
            team_id: ID of the team to delete.

        Raises:
            KeyError: If no team with the given ID exists.
        """

    @abstractmethod
    def add_user_to_team(self, user_id: str, team_id: str) -> None:
        """Adds a user to a team.

        Args:
            user_id: ID of the user to add to the team.
            team_id: ID of the team to which to add the user to.

        Raises:
            KeyError: If the team or user does not exist.
        """

    @abstractmethod
    def remove_user_from_team(self, user_id: str, team_id: str) -> None:
        """Removes a user from a team.

        Args:
            user_id: ID of the user to remove from the team.
            team_id: ID of the team from which to remove the user.

        Raises:
            KeyError: If the team or user does not exist.
        """

    @abstractmethod
    def get_users_for_team(self, team_id: str) -> List[UserModel]:
        """Fetches all users of a team.

        Args:
            team_id: The ID of the team for which to get users.

        Returns:
            A list of all users that are part of the team.

        Raises:
            KeyError: If no team with the given ID exists.
        """

    @abstractmethod
    def get_teams_for_user(self, user_id: str) -> List[TeamModel]:
        """Fetches all teams for a user.

        Args:
            user_id: The ID of the user for which to get all teams.

        Returns:
            A list of all teams that the user is part of.

        Raises:
            KeyError: If no user with the given ID exists.
        """

    #  .------.
    # | ROLES |
    # '-------'

    # TODO: create & delete roles?

    @property
    def roles(self) -> List[RoleModel]:
        """All registered roles.

        Returns:
            A list of all registered roles.
        """
        return self._list_roles()

    # TODO: [ALEX] add filtering param(s)
    @abstractmethod
    def _list_roles(self) -> List[RoleModel]:
        """List all roles.

        Returns:
            A list of all roles.
        """

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
        self._track_event(AnalyticsEvent.CREATED_ROLE)
        return self._create_role(role)

    @abstractmethod
    def _create_role(self, role: RoleModel) -> RoleModel:
        """Creates a new role.

        Args:
            role: The role model to create.

        Returns:
            The newly created role.

        Raises:
            EntityExistsError: If a role with the given name already exists.
        """

    # TODO: consider using team_id instead
    def get_role(self, role_name_or_id: str) -> RoleModel:
        """Gets a specific role.

        Args:
            role_name_or_id: Name or ID of the role to get.

        Returns:
            The requested role.

        Raises:
            KeyError: If no role with the given name exists.
        """
        # No tracking events, here for consistency
        return self._get_role(role_name_or_id)

    @abstractmethod
    def _get_role(self, role_name_or_id: str) -> RoleModel:
        """Gets a specific role.

        Args:
            role_name_or_id: Name or ID of the role to get.

        Returns:
            The requested role.

        Raises:
            KeyError: If no role with the given name exists.
        """

    def delete_role(self, role_id: str) -> None:
        """Deletes a role.

        Args:
            role_id: ID of the role to delete.

        Raises:
            KeyError: If no role with the given ID exists.
        """
        self._track_event(AnalyticsEvent.DELETED_ROLE)
        return self._delete_role(role_id)

    @abstractmethod
    def _delete_role(self, role_id: str) -> None:
        """Deletes a role.

        Args:
            role_id: ID of the role to delete.

        Raises:
            KeyError: If no role with the given ID exists.
        """

    @property
    def role_assignments(self) -> List[RoleAssignmentModel]:
        """All role assignments.

        Returns:
            A list of all role assignments.
        """
        return self.list_role_assignments()

    @abstractmethod
    def list_role_assignments(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        team_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[RoleAssignmentModel]:
        """List all role assignments.

        Args:
            project_name_or_id: If provided, only list assignments for the given
                                project
            team_id: If provided, only list assignments for the given team
            user_id: If provided, only list assignments for the given user

        Returns:
            A list of all role assignments.
        """

    def assign_role(
        self,
        role_id: str,
        user_or_team_id: str,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        is_user: bool = True,
    ) -> None:
        """Assigns a role to a user or team, scoped to a specific project.

        Args:
            role_id: ID of the role to assign to the user.
            user_or_team_id: ID of the user or team to which to assign the role.
            is_user: Whether `user_or_team_id` refers to a user or a team.
            project_name_or_id: Optional Name or ID of a project in which to
                                assign the role. If this is not provided, the
                                role will be assigned globally.

        Raises:
            EntityExistsError: If the role assignment already exists.
        """
        return self._assign_role(
            role_id=role_id,
            user_or_team_id=user_or_team_id,
            is_user=is_user,
            project_name_or_id=project_name_or_id,
        )

    @abstractmethod
    def _assign_role(
        self,
        role_id: str,
        user_or_team_id: str,
        project_name_or_id: Optional[Union[str, UUID]],
        is_user: bool = True,
    ) -> None:
        """Assigns a role to a user or team, scoped to a specific project.

        Args:
            role_id: ID of the role to assign.
            user_or_team_id: ID of the user or team to which to assign the role.
            is_user: Whether `user_or_team_id` refers to a user or a team.
            project_name_or_id: Optional Name or ID of a project in which to
                                assign the role. If this is not provided, the
                                role will be assigned globally.

        Raises:
            EntityExistsError: If the role assignment already exists.
        """

    def revoke_role(
        self,
        role_id: str,
        user_or_team_id: str,
        is_user: bool = True,
        project_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> None:
        """Revokes a role from a user or team for a given project.

        Args:
            role_id: ID of the role to revoke.
            user_or_team_id: ID of the user or team from which to revoke the
                role.
            is_user: Whether `user_or_team_id` refers to a user or a team.
            project_name_or_id: Optional ID of a project in which to revoke
                                the role. If this is not provided, the role will
                                be revoked globally.

        Raises:
            KeyError: If the role, user, team, or project does not exists.
        """
        self._track_event(AnalyticsEvent.DELETED_ROLE)
        return self._revoke_role(
            role_id=role_id,
            user_or_team_id=user_or_team_id,
            is_user=is_user,
            project_name_or_id=project_name_or_id,
        )

    @abstractmethod
    def _revoke_role(
        self,
        role_id: str,
        user_or_team_id: str,
        is_user: bool = True,
        project_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> None:
        """Revokes a role from a user or team for a given project.

        Args:
            role_id: ID of the role to revoke.
            user_or_team_id: ID of the user or team from which to revoke the
                role.
            is_user: Whether `user_or_team_id` refers to a user or a team.
            project_name_or_id: Optional ID of a project in which to revoke
                                the role. If this is not provided, the role will
                                be revoked globally.

        Raises:
            KeyError: If the role, user, team, or project does not exists.
        """

    #  .---------.
    # | PROJECTS |
    # '----------'

    # TODO: [ALEX] add filtering param(s)
    def list_projects(self) -> List[ProjectModel]:
        """List all projects.

        Returns:
            A list of all projects.
        """
        return self._list_projects()

    @abstractmethod
    def _list_projects(self) -> List[ProjectModel]:
        """List all projects.

        Returns:
            A list of all projects.
        """

    def create_project(self, project: ProjectModel) -> ProjectModel:
        """Creates a new project.

        Args:
            project: The project to create.

        Returns:
            The newly created project.

        Raises:
            EntityExistsError: If a project with the given name already exists.
        """
        self._track_event(AnalyticsEvent.CREATED_PROJECT)
        return self._create_project(project)

    @abstractmethod
    def _create_project(self, project: ProjectModel) -> ProjectModel:
        """Creates a new project.

        Args:
            project: The project to create.

        Returns:
            The newly created project.

        Raises:
            EntityExistsError: If a project with the given name already exists.
        """

    def get_project(self, project_name_or_id: str) -> ProjectModel:
        """Get an existing project by name or ID.

        Args:
            project_name_or_id: Name or ID of the project to get.

        Returns:
            The requested project if one was found.

        Raises:
            KeyError: If there is no such project.
        """
        # No tracking events, here for consistency
        return self._get_project(project_name_or_id)

    @abstractmethod
    def _get_project(self, project_name_or_id: str) -> ProjectModel:
        """Get an existing project by name or ID.

        Args:
            project_name_or_id: Name or ID of the project to get.

        Returns:
            The requested project if one was found.

        Raises:
            KeyError: If there is no such project.
        """

    def update_project(
        self, project_name: str, project: ProjectModel
    ) -> ProjectModel:
        """Updates an existing project.

        Args:
            project_name: Name of the project to update.
            project: The project to use for the update.

        Returns:
            The updated project.

        Raises:
            KeyError: if the project does not exist.
        """
        # No tracking events, here for consistency
        return self._update_project(project_name, project)

    @abstractmethod
    def _update_project(
        self, project_name: str, project: ProjectModel
    ) -> ProjectModel:
        """Update an existing project.

        Args:
            project_name: Name of the project to update.
            project: The project to use for the update.

        Returns:
            The updated project.

        Raises:
            KeyError: if the project does not exist.
        """

    def delete_project(self, project_name: str) -> None:
        """Deletes a project.

        Args:
            project_name: Name of the project to delete.

        Raises:
            KeyError: If the project does not exist.
        """
        self._track_event(AnalyticsEvent.DELETED_PROJECT)
        return self._delete_project(project_name)

    @abstractmethod
    def _delete_project(self, project_name: str) -> None:
        """Deletes a project.

        Args:
            project_name: Name of the project to delete.

        Raises:
            KeyError: If no project with the given name exists.
        """

    def get_default_stack(self, project_name: str) -> StackModel:
        """Gets the default stack in a project.

        Args:
            project_name: Name of the project to get.

        Returns:
            The default stack in the project.

        Raises:
            KeyError: if the project doesn't exist.
        """
        return self._get_default_stack(project_name)

    @abstractmethod
    def _get_default_stack(self, project_name: str) -> StackModel:
        """Gets the default stack in a project.

        Args:
            project_name: Name of the project to get.

        Returns:
            The default stack in the project.

        Raises:
            KeyError: if the project doesn't exist.
        """

    def set_default_stack(self, project_name: str, stack_id: str) -> StackModel:
        """Sets the default stack in a project.

        Args:
            project_name: Name of the project to set.
            stack_id: The ID of the stack to set as the default.

        Raises:
            KeyError: if the project or stack doesn't exist.
        """
        return self._set_default_stack(project_name, stack_id)

    @abstractmethod
    def _set_default_stack(
        self, project_name: str, stack_id: str
    ) -> StackModel:
        """Sets the default stack in a project.

        Args:
            project_name: Name of the project to set.
            stack_id: The ID of the stack to set as the default.

        Raises:
            KeyError: if the project or stack doesn't exist.
        """

    #  .-------------.
    # | REPOSITORIES |
    # '--------------'

    # TODO: create repository?

    # TODO: [ALEX] add filtering param(s)
    def list_project_repositories(
        self, project_name: str
    ) -> List[CodeRepositoryModel]:
        """Gets all repositories in a project.

        Args:
            project_name: The name of the project.

        Returns:
            A list of all repositories in the project.

        Raises:
            KeyError: if the project doesn't exist.
        """
        return self._list_project_repositories(project_name)

    @abstractmethod
    def _list_project_repositories(
        self, project_name: str
    ) -> List[CodeRepositoryModel]:
        """Get all repositories in the project.

        Args:
            project_name: The name of the project.

        Returns:
            A list of all repositories in the project.

        Raises:
            KeyError: if the project doesn't exist.
        """

    def connect_project_repository(
        self, project_name: str, repository: CodeRepositoryModel
    ) -> CodeRepositoryModel:
        """Connects a repository to a project.

        Args:
            project_name: Name of the project to connect the repository to.
            repository: The repository to connect.

        Returns:
            The connected repository.

        Raises:
            KeyError: if the project or repository doesn't exist.
        """
        self._track_event(AnalyticsEvent.CONNECT_REPOSITORY)
        return self._connect_project_repository(project_name, repository)

    @abstractmethod
    def _connect_project_repository(
        self, project_name: str, repository: CodeRepositoryModel
    ) -> CodeRepositoryModel:
        """Connects a repository to a project.

        Args:
            project_name: Name of the project to connect the repository to.
            repository: The repository to connect.

        Returns:
            The connected repository.

        Raises:
            KeyError: if the project or repository doesn't exist.
        """

    def get_repository(self, repository_id: str) -> CodeRepositoryModel:
        """Gets a repository.

        Args:
            repository_id: The ID of the repository to get.

        Returns:
            The repository.

        Raises:
            KeyError: if the repository doesn't exist.
        """
        return self._get_repository(repository_id)

    @abstractmethod
    def _get_repository(self, repository_id: str) -> CodeRepositoryModel:
        """Get a repository by ID.

        Args:
            repository_id: The ID of the repository to get.

        Returns:
            The repository.

        Raises:
            KeyError: if the repository doesn't exist.
        """

    def update_repository(
        self, repository_id: str, repository: CodeRepositoryModel
    ):
        """Updates a repository.

        Args:
            repository_id: The ID of the repository to update.
            repository: The repository to use for the update.

        Returns:
            The updated repository.

        Raises:
            KeyError: if the repository doesn't exist.
        """
        self._track_event(AnalyticsEvent.UPDATE_REPOSITORY)
        return self._update_repository(repository_id, repository)

    @abstractmethod
    def _update_repository(
        self, repository_id: str, repository: CodeRepositoryModel
    ) -> CodeRepositoryModel:
        """Update a repository.

        Args:
            repository_id: The ID of the repository to update.
            repository: The repository to use for the update.

        Returns:
            The updated repository.

        Raises:
            KeyError: if the repository doesn't exist.
        """

    def delete_repository(self, repository_id: str):
        """Deletes a repository.

        Args:
            repository_id: The ID of the repository to delete.

        Raises:
            KeyError: if the repository doesn't exist.
        """
        self._track_event(AnalyticsEvent.DELETE_REPOSITORY)
        return self._delete_repository(repository_id)

    @abstractmethod
    def _delete_repository(self, repository_id: str) -> None:
        """Delete a repository.

        Args:
            repository_id: The ID of the repository to delete.

        Raises:
            KeyError: if the repository doesn't exist.
        """

    #  .-----.
    # | AUTH |
    # '------'

    def login(self) -> None:
        """Logs in to the server."""
        self._track_event(AnalyticsEvent.LOGIN)
        self._login()

    def _login(self) -> None:
        """Logs in to the server."""

    def logout(self) -> None:
        """Logs out of the server."""
        self._track_event(AnalyticsEvent.LOGOUT)
        self._logout()

    def _logout(self) -> None:
        """Logs out of the server."""

    #  .----------.
    # | PIPELINES |
    # '-----------'

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
        return self._list_pipelines(project_name_or_id)

    @abstractmethod
    def _list_pipelines(
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

    def create_pipeline(
        self, project_name_or_id: Union[str, UUID], pipeline: PipelineModel
    ) -> PipelineModel:
        """Creates a new pipeline in a project.

        Args:
            project_name_or_id: ID or name of the project to create the pipeline
                                in.
            pipeline: The pipeline to create.

        Returns:
            The newly created pipeline.

        Raises:
            KeyError: if the project does not exist.
            EntityExistsError: If an identical pipeline already exists.
        """
        self._track_event(AnalyticsEvent.CREATE_PIPELINE)
        return self._create_pipeline(project_name_or_id, pipeline)

    @abstractmethod
    def _create_pipeline(
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
    def get_pipeline(self, pipeline_id: str) -> Optional[PipelineModel]:
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
    ) -> Optional[PipelineModel]:
        """Get a pipeline with a given name in a project.

        Args:
            pipeline_name: Name of the pipeline.
            project_name_or_id: ID of the project.

        Returns:
            The pipeline.

        Raises:
            KeyError: if the pipeline does not exist.
        """

    def update_pipeline(
        self, pipeline_id: str, pipeline: PipelineModel
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
        self._track_event(AnalyticsEvent.UPDATE_PIPELINE)
        return self._update_pipeline(pipeline_id, pipeline)

    @abstractmethod
    def _update_pipeline(
        self, pipeline_id: str, pipeline: PipelineModel
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

    def delete_pipeline(self, pipeline_id: str) -> None:
        """Deletes a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to delete.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """
        self._track_event(AnalyticsEvent.DELETE_PIPELINE)
        return self._delete_pipeline(pipeline_id)

    @abstractmethod
    def _delete_pipeline(self, pipeline_id: str) -> None:
        """Deletes a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to delete.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """

    def get_pipeline_configuration(self, pipeline_id: str) -> Dict[str, str]:
        """Gets the pipeline configuration.

        Args:
            pipeline_id: The ID of the pipeline to get.

        Returns:
            The pipeline configuration.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """
        return self._get_pipeline_configuration(pipeline_id)

    @abstractmethod
    def _get_pipeline_configuration(self, pipeline_id: str) -> Dict[Any, Any]:
        """Gets the pipeline configuration.

        Args:
            pipeline_id: The ID of the pipeline to get.

        Returns:
            The pipeline configuration.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """

    # TODO: change into an abstract method
    # TODO: Note that this doesn't have a corresponding API endpoint (consider adding?)
    # TODO: Discuss whether we even need this, given that the endpoint is on
    # pipeline runs
    # TODO: [ALEX] add filtering param(s)
    def list_steps(self, pipeline_id: str) -> List[StepRunModel]:
        """List all steps for a specific pipeline.

        Args:
            pipeline_id: The id of the pipeline to get steps for.

        Returns:
            A list of all steps for the pipeline.
        """
        return self._list_steps(pipeline_id)

    @abstractmethod
    def _list_steps(self, pipeline_id: str) -> List[StepRunModel]:
        """List all steps.

        Args:
            pipeline_id: The ID of the pipeline to list steps for.

        Returns:
            A list of all steps.
        """

    #  .-----.
    # | RUNS |
    # '------'

    def list_runs(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        stack_id: Optional[str] = None,
        user_id: Optional[str] = None,
        pipeline_id: Optional[str] = None,
        unlisted: bool = False,
    ) -> List[PipelineRunModel]:
        """Gets all pipeline runs.

        Args:
            project_name_or_id: If provided, only return runs for this project.
            stack_id: If provided, only return runs for this stack.
            user_id: If provided, only return runs for this user.
            pipeline_id: If provided, only return runs for this pipeline.
            unlisted: If True, only return unlisted runs that are not
                associated with any pipeline (filter by `pipeline_id==None`).

        Returns:
            A list of all pipeline runs.
        """
        return self._list_runs(
            project_name_or_id=project_name_or_id,
            stack_id=stack_id,
            user_id=user_id,
            pipeline_id=pipeline_id,
            unlisted=unlisted,
        )

    @abstractmethod
    def _list_runs(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        stack_id: Optional[str] = None,
        user_id: Optional[str] = None,
        pipeline_id: Optional[str] = None,
        unlisted: bool = False,
    ) -> List[PipelineRunModel]:
        """Gets all pipeline runs.

        Args:
            project_name_or_id: If provided, only return runs for this project.
            stack_id: If provided, only return runs for this stack.
            user_id: If provided, only return runs for this user.
            pipeline_id: If provided, only return runs for this pipeline.
            unlisted: If True, only return unlisted runs that are not
                associated with any pipeline (filter by pipeline_id==None).

        Returns:
            A list of all pipeline runs.
        """

    def create_run(self, pipeline_run: PipelineRunModel) -> PipelineRunModel:
        """Creates a pipeline run.

        Args:
            pipeline_run: The pipeline run to create.

        Returns:
            The created pipeline run.

        Raises:
            EntityExistsError: If an identical pipeline run already exists.
        """
        return self._create_run(pipeline_run)

    @abstractmethod
    def _create_run(self, pipeline_run: PipelineRunModel) -> PipelineRunModel:
        """Creates a pipeline run.

        Args:
            pipeline_run: The pipeline run to create.

        Returns:
            The created pipeline run.

        Raises:
            EntityExistsError: If an identical pipeline run already exists.
        """

    def get_run(self, run_id: str) -> PipelineRunModel:
        """Gets a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            The pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """
        return self._get_run(run_id)

    @abstractmethod
    def _get_run(self, run_id: str) -> PipelineRunModel:
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
    ) -> Optional[PipelineModel]:
        """Get a pipeline run with a given name in a project.

        Args:
            run_name: Name of the pipeline run.
            project_name_or_id: ID or name of the project.

        Returns:
            The pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """

    def update_run(
        self, run_id: str, run: PipelineRunModel
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
        return self._update_run(run_id, run)

    @abstractmethod
    def _update_run(
        self, run_id: str, run: PipelineRunModel
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

    def delete_run(self, run_id: str) -> None:
        """Deletes a pipeline run.

        Args:
            run_id: The ID of the pipeline run to delete.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """
        return self._delete_run(run_id)

    @abstractmethod
    def _delete_run(self, run_id: str) -> None:
        """Deletes a pipeline run.

        Args:
            run_id: The ID of the pipeline run to delete.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """

    # TODO: figure out args and output for this
    def get_run_dag(self, run_id: str) -> str:
        """Gets the DAG for a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            The DAG for the pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """
        return self._get_run_dag(run_id)

    # TODO: figure out args and output for this
    @abstractmethod
    def _get_run_dag(self, run_id: str) -> str:
        """Gets the DAG for a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            The DAG for the pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """

    def get_run_runtime_configuration(self, run_id: str) -> Dict:
        """Gets the runtime configuration for a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            The runtime configuration for the pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """
        return self._get_run_runtime_configuration(run_id)

    @abstractmethod
    def _get_run_runtime_configuration(self, run_id: str) -> Dict:
        """Gets the runtime configuration for a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            The runtime configuration for the pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """

    # TODO: Figure out what exactly gets returned from this
    def get_run_component_side_effects(
        self,
        run_id: str,
        component_id: Optional[str] = None,
        component_type: Optional[StackComponentType] = None,
    ) -> Dict:
        """Gets the side effects for a component in a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.
            component_id: The ID of the component to get.

        Returns:
            The side effects for the component in the pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """
        return self._get_run_component_side_effects(
            run_id, component_id=component_id, component_type=component_type
        )

    @abstractmethod
    def _get_run_component_side_effects(
        self,
        run_id: str,
        component_id: Optional[str] = None,
        component_type: Optional[StackComponentType] = None,
    ) -> Dict:
        """Gets the side effects for a component in a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.
            component_id: The ID of the component to get.

        Returns:
            The side effects for the component in the pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """

    #  .------.
    # | STEPS |
    # '-------'

    @abstractmethod
    def list_run_steps(self, run_id: int) -> List[StepRunModel]:
        """Gets all steps in a pipeline run.

        Args:
            run_id: The ID of the pipeline run for which to list runs.

        Returns:
            A list of all steps in the pipeline run.
        """

    @abstractmethod
    def get_run_step(self, step_id: str) -> StepRunModel:
        """Get a step by ID.

        Args:
            step_id: The ID of the step to get.

        Returns:
            The step.
        """

    def get_run_step_outputs(
        self, step: StepRunModel
    ) -> Dict[str, ArtifactModel]:
        """Get a list of outputs for a specific step.

        Args:
            step_id: The id of the step to get outputs for.

        Returns:
            A dict mapping artifact names to the output artifacts for the step.
        """
        return self.get_run_step_artifacts(step)[1]

    # TODO: Note that this doesn't have a corresponding API endpoint (consider adding?)
    def get_run_step_inputs(
        self, step: StepRunModel
    ) -> Dict[str, ArtifactModel]:
        """Get a list of inputs for a specific step.

        Args:
            step_id: The id of the step to get inputs for.

        Returns:
            A dict mapping artifact names to the input artifacts for the step.
        """
        return self.get_run_step_artifacts(step)[0]

    @abstractmethod
    def get_run_step_artifacts(
        self, step: StepRunModel
    ) -> Tuple[Dict[str, ArtifactModel], Dict[str, ArtifactModel]]:
        """Returns input and output artifacts for the given step.

        Args:
            step: The step for which to get the artifacts.

        Returns:
            A tuple (inputs, outputs) where inputs and outputs
            are both Dicts mapping artifact names
            to the input and output artifacts respectively.
        """

    @abstractmethod
    def get_run_step_status(self, step_id: int) -> ExecutionStatus:
        """Gets the execution status of a single step.

        Args:
            step_id: The ID of the step to get the status for.

        Returns:
            ExecutionStatus: The status of the step.
        """

    #  .---------.
    # | METADATA |
    # '----------'

    @abstractmethod
    def get_metadata_config(self) -> str:
        """Get the TFX metadata config of this ZenStore.

        Returns:
            The TFX metadata config of this ZenStore.
        """

    # # Public facing APIs
    # # TODO [ENG-894]: Refactor these with the proxy pattern, as noted in
    # #  the [review comment](https://github.com/zenml-io/zenml/pull/589#discussion_r875003334)

    def create_flavor(
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
        analytics_metadata = {
            "type": stack_component_type.value,
        }
        self._track_event(
            AnalyticsEvent.CREATED_FLAVOR,
            metadata=analytics_metadata,
        )
        return self._create_flavor(source, name, stack_component_type)

    # LEGACY CODE FROM THE PREVIOUS VERSION OF BASEZENSTORE

    # Stack component flavors
    @property
    @abstractmethod
    def flavors(self) -> List[FlavorModel]:
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
    ) -> FlavorModel:
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
    ) -> List[FlavorModel]:
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
    ) -> FlavorModel:
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
