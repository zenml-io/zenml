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
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, Union
from uuid import UUID

from pydantic import BaseModel

import zenml
from zenml.config.global_config import GlobalConfiguration
from zenml.config.store_config import StoreConfiguration
from zenml.constants import (
    ENV_ZENML_DEFAULT_PROJECT_NAME,
    ENV_ZENML_DEFAULT_USER_NAME,
    ENV_ZENML_DEFAULT_USER_PASSWORD,
    ENV_ZENML_SERVER_DEPLOYMENT_TYPE,
)
from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import StackExistsError
from zenml.logger import get_logger
from zenml.models import (
    ComponentModel,
    ProjectModel,
    RoleAssignmentModel,
    RoleModel,
    StackModel,
    TeamModel,
    UserModel,
)
from zenml.models.pipeline_models import PipelineModel
from zenml.models.server_models import (
    ServerDatabaseType,
    ServerDeploymentType,
    ServerModel,
)
from zenml.utils.analytics_utils import (
    AnalyticsEvent,
    AnalyticsTrackerMixin,
    track,
    track_event,
)
from zenml.zen_stores.zen_store_interface import ZenStoreInterface

logger = get_logger(__name__)

DEFAULT_USERNAME = "default"
DEFAULT_PASSWORD = ""
DEFAULT_PROJECT_NAME = "default"
DEFAULT_STACK_NAME = "default"


class BaseZenStore(BaseModel, ZenStoreInterface, AnalyticsTrackerMixin):
    """Base class for accessing and persisting ZenML core objects.

    Attributes:
        config: The configuration of the store.
        track_analytics: Only send analytics if set to `True`.
    """

    config: StoreConfiguration
    track_analytics: bool = True
    _active_user: Optional[UserModel] = None

    TYPE: ClassVar[StoreType]
    CONFIG_TYPE: ClassVar[Type[StoreConfiguration]]

    # ---------------------------------
    # Initialization and configuration
    # ---------------------------------

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
            logger.debug("Initializing database")
            self._initialize_database()
        else:
            logger.debug("Skipping database initialization")

    @staticmethod
    def get_store_class(store_type: StoreType) -> Type["BaseZenStore"]:
        """Returns the class of the given store type.

        Args:
            store_type: The type of the store to get the class for.

        Returns:
            The class of the given store type or None if the type is unknown.

        Raises:
            TypeError: If the store type is unsupported.
        """
        if store_type == StoreType.SQL:
            from zenml.zen_stores.sql_zen_store import SqlZenStore

            return SqlZenStore
        elif store_type == StoreType.REST:
            from zenml.zen_stores.rest_zen_store import RestZenStore

            return RestZenStore
        else:
            raise TypeError(
                f"No store implementation found for store type "
                f"`{store_type.value}`."
            )

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
        from zenml.zen_stores.sql_zen_store import SqlZenStoreConfiguration

        config = SqlZenStoreConfiguration(
            type=StoreType.SQL, url=SqlZenStoreConfiguration.get_local_url(path)
        )
        return config

    def _initialize_database(self) -> None:
        """Initialize the database on first use."""
        try:
            default_project = self._default_project
        except KeyError:
            default_project = self._create_default_project()
        try:
            default_user = self._default_user
        except KeyError:
            default_user = self._create_default_user()
        try:
            self._get_default_stack(
                project_name_or_id=default_project.id,
                user_name_or_id=default_user.id,
            )
        except KeyError:
            self._create_default_stack(
                project_name_or_id=default_project.id,
                user_name_or_id=default_user.id,
            )

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

    def validate_active_config(
        self,
        active_project_name_or_id: Optional[Union[str, UUID]] = None,
        active_stack_id: Optional[UUID] = None,
        config_name: str = "",
    ) -> Tuple[ProjectModel, StackModel]:
        """Validate the active configuration.

        Call this method to validate the supplied active project and active
        stack values.

        This method is guaranteed to return valid project ID and stack ID
        values. If the supplied project and stack are not set or are not valid
        (e.g. they do not exist or are not accessible), the default project and
        default project stack will be returned in their stead.

        Args:
            active_project_name_or_id: The name or ID of the active project.
            active_stack_id: The ID of the active stack.
            config_name: The name of the configuration to validate (used in the
                displayed logs/messages).

        Returns:
            A tuple containing the active project and active stack.
        """
        active_project: ProjectModel

        # Figure out a project to use if one isn't configured or
        # available:
        #   1. If the default project is configured, use that.
        #   2. If the default project is not configured, use the first
        #      project in the store.
        #   3. If there are no projects in the store, create the default
        #      project and use that
        try:
            default_project = self._default_project
        except KeyError:
            projects = self.list_projects()
            if len(projects) == 0:
                self._create_default_project()
                default_project = self._default_project
            else:
                default_project = projects[0]

        # Ensure that the current active project is still valid
        if active_project_name_or_id:
            try:
                active_project = self.get_project(active_project_name_or_id)
            except KeyError:
                logger.warning(
                    "The current %s active project is no longer available. "
                    "Resetting the active project to '%s'.",
                    config_name,
                    default_project.name,
                )
                active_project = default_project
        else:
            logger.info(
                "Setting the %s active project to '%s'.",
                config_name,
                default_project.name,
            )
            active_project = default_project

        active_stack: StackModel

        # Create a default stack in the active project for the active user if
        # one is not yet created.
        try:
            default_stack = self._get_default_stack(
                project_name_or_id=active_project.id,
                user_name_or_id=self.active_user.id,
            )
        except KeyError:
            default_stack = self._create_default_stack(
                project_name_or_id=active_project.id,
                user_name_or_id=self.active_user.id,
            )

        # Sanitize the active stack
        if active_stack_id:
            # Ensure that the active stack is still valid
            try:
                active_stack = self.get_stack(stack_id=active_stack_id)
            except KeyError:
                logger.warning(
                    "The current %s active stack is no longer available. "
                    "Resetting the active stack to default.",
                    config_name,
                )
                active_stack = default_stack
            else:
                if active_stack.project != active_project.id:
                    logger.warning(
                        "The current %s active stack is not part of the active "
                        "project. Resetting the active stack to default.",
                        config_name,
                    )
                    active_stack = default_stack
                elif (
                    not active_stack.is_shared
                    and active_stack.user != self.active_user.id
                ):
                    logger.warning(
                        "The current %s active stack is not shared and not "
                        "owned by the active user. "
                        "Resetting the active stack to default.",
                        config_name,
                    )
                    active_stack = default_stack
        else:
            logger.warning(
                "Setting the %s active stack to default.",
                config_name,
            )
            active_stack = default_stack

        return active_project, active_stack

    def get_store_info(self) -> ServerModel:
        """Get information about the store.

        Returns:
            Information about the store.
        """
        return ServerModel(
            id=GlobalConfiguration().user_id,
            version=zenml.__version__,
            deployment_type=os.environ.get(
                ENV_ZENML_SERVER_DEPLOYMENT_TYPE, ServerDeploymentType.OTHER
            ),
            database_type=ServerDatabaseType.OTHER,
        )

    def is_local_store(self) -> bool:
        """Check if the store is a local store or connected to a locally deployed ZenML server.

        Returns:
            True if the store is local, False otherwise.
        """
        return self.get_store_info().is_local()

    # ------
    # Stacks
    # ------

    @track(AnalyticsEvent.REGISTERED_DEFAULT_STACK)
    def _create_default_stack(
        self,
        project_name_or_id: Union[str, UUID],
        user_name_or_id: Union[str, UUID],
    ) -> StackModel:
        """Create the default stack components and stack.

        The default stack contains a local orchestrator and a local artifact
        store.

        Args:
            project_name_or_id: Name or ID of the project to which the stack
                belongs.
            user_name_or_id: The name or ID of the user that owns the stack.

        Returns:
            The model of the created default stack.

        Raises:
            StackExistsError: If a default stack already exists for the
                user in the supplied project.
        """
        project = self.get_project(project_name_or_id=project_name_or_id)
        user = self.get_user(user_name_or_id=user_name_or_id)
        try:
            self._get_default_stack(
                project_name_or_id=project_name_or_id,
                user_name_or_id=user_name_or_id,
            )
        except KeyError:
            pass
        else:
            raise StackExistsError(
                f"Default stack already exists for user "
                f"{user.name} in project {project.name}"
            )

        logger.info(
            f"Creating default stack for user '{user.name}' in project "
            f"{project.name}..."
        )

        # Register the default orchestrator
        orchestrator = self.create_stack_component(
            component=ComponentModel(
                user=user.id,
                project=project.id,
                name="default",
                type=StackComponentType.ORCHESTRATOR,
                flavor="local",
                configuration={},
            ),
        )

        # Register the default artifact store
        artifact_store = self.create_stack_component(
            component=ComponentModel(
                user=user.id,
                project=project.id,
                name="default",
                type=StackComponentType.ARTIFACT_STORE,
                flavor="local",
                configuration={},
            ),
        )

        components = {c.type: [c.id] for c in [orchestrator, artifact_store]}
        # Register the default stack
        stack = StackModel(
            name="default",
            components=components,
            is_shared=False,
            project=project.id,
            user=user.id,
        )
        return self.create_stack(stack=stack)

    def _get_default_stack(
        self,
        project_name_or_id: Union[str, UUID],
        user_name_or_id: Union[str, UUID],
    ) -> StackModel:
        """Get the default stack for a user in a project.

        Args:
            project_name_or_id: Name or ID of the project.
            user_name_or_id: Name or ID of the user.

        Returns:
            The default stack in the project owned by the supplied user.

        Raises:
            KeyError: if the project or default stack doesn't exist.
        """
        default_stacks = self.list_stacks(
            project_name_or_id=project_name_or_id,
            user_name_or_id=user_name_or_id,
            name=DEFAULT_STACK_NAME,
        )
        if len(default_stacks) == 0:
            raise KeyError(
                f"No default stack found for user {str(user_name_or_id)} in "
                f"project {str(project_name_or_id)}"
            )
        return default_stacks[0]

    # -----
    # Users
    # -----

    @property
    def active_user(self) -> UserModel:
        """The active user.

        Returns:
            The active user.
        """
        if self._active_user is None:
            self._active_user = self.get_user(self.active_user_name)
        return self._active_user

    @property
    def users(self) -> List[UserModel]:
        """All existing users.

        Returns:
            A list of all existing users.
        """
        return self.list_users()

    @property
    def _default_user_name(self) -> str:
        """Get the default user name.

        Returns:
            The default user name.
        """
        return os.getenv(ENV_ZENML_DEFAULT_USER_NAME, DEFAULT_USERNAME)

    @property
    def _default_user(self) -> UserModel:
        """Get the default user.

        Returns:
            The default user.

        Raises:
            KeyError: If the default user doesn't exist.
        """
        user_name = self._default_user_name
        try:
            return self.get_user(user_name)
        except KeyError:
            raise KeyError(f"The default user '{user_name}' is not configured")

    @track(AnalyticsEvent.CREATED_DEFAULT_USER)
    def _create_default_user(self) -> UserModel:
        """Creates a default user.

        Returns:
            The default user.
        """
        user_name = os.getenv(ENV_ZENML_DEFAULT_USER_NAME, DEFAULT_USERNAME)
        user_password = os.getenv(
            ENV_ZENML_DEFAULT_USER_PASSWORD, DEFAULT_PASSWORD
        )

        logger.info(f"Creating default user '{user_name}' ...")
        return self.create_user(
            UserModel(
                name=user_name,
                active=True,
                password=user_password,
            )
        )

    # -----
    # Teams
    # -----

    @property
    def teams(self) -> List[TeamModel]:
        """List all teams.

        Returns:
            A list of all teams.
        """
        return self.list_teams()

    # -----
    # Roles
    # -----

    @property
    def roles(self) -> List[RoleModel]:
        """All existing roles.

        Returns:
            A list of all existing roles.
        """
        return self.list_roles()

    @property
    def role_assignments(self) -> List[RoleAssignmentModel]:
        """All role assignments.

        Returns:
            A list of all role assignments.
        """
        return self.list_role_assignments(user_name_or_id=self.active_user_name)

    # --------
    # Projects
    # --------

    @property
    def _default_project(self) -> ProjectModel:
        """Get the default project.

        Returns:
            The default project.

        Raises:
            KeyError: if the default project doesn't exist.
        """
        project_name = os.getenv(
            ENV_ZENML_DEFAULT_PROJECT_NAME, DEFAULT_PROJECT_NAME
        )
        try:
            return self.get_project(project_name)
        except KeyError:
            raise KeyError(
                f"The default project '{project_name}' is not configured"
            )

    @track(AnalyticsEvent.CREATED_DEFAULT_PROJECT)
    def _create_default_project(self) -> ProjectModel:
        """Creates a default project.

        Returns:
            The default project.
        """
        project_name = os.getenv(
            ENV_ZENML_DEFAULT_PROJECT_NAME, DEFAULT_PROJECT_NAME
        )
        logger.info(f"Creating default project '{project_name}' ...")
        return self.create_project(ProjectModel(name=project_name))

    # ------------
    # Repositories
    # ------------

    # ---------
    # Pipelines
    # ---------

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
        pipelines = self.list_pipelines(
            project_name_or_id=project_name_or_id, name=pipeline_name
        )
        if len(pipelines) == 0:
            raise KeyError(
                f"No pipeline found with name {pipeline_name} in project "
                f"{project_name_or_id}"
            )
        return pipelines[0]

    # -------------
    # Pipeline runs
    # -------------

    # ------------------
    # Pipeline run steps
    # ------------------

    # ---------
    # Analytics
    # ---------

    def track_event(
        self,
        event: Union[str, AnalyticsEvent],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track an analytics event.

        Args:
            event: The event to track.
            metadata: Additional metadata to track with the event.
        """
        if self.track_analytics:
            # Server information is always tracked, if available.
            track_event(event, metadata)

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
