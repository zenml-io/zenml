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
from pathlib import Path, PurePath
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, Union
from uuid import UUID

from pydantic import BaseModel

from zenml.config.store_config import StoreConfiguration
from zenml.enums import ExecutionStatus, StackComponentType, StoreType
from zenml.exceptions import StackExistsError
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
from zenml.stack.flavor_registry import flavor_registry
from zenml.utils import io_utils
from zenml.utils.analytics_utils import (
    AnalyticsEvent,
    AnalyticsTrackerMixin,
    track,
    track_event,
)
from zenml.zen_stores.zen_store_interface import ZenStoreInterface

logger = get_logger(__name__)

DEFAULT_USERNAME = "default"
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
        from zenml.zen_stores.rest_zen_store import RestZenStore

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
            self._register_default_stack(
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

        Returns:
            A tuple containing the active project and active stack.
        """

        active_project: ProjectModel

        # Ensure that the current active project is still valid
        if active_project_name_or_id:
            try:
                active_project = self.get_project(active_project_name_or_id)
            except KeyError:
                logger.warning(
                    "Project '%s' not found. Resetting the active project to "
                    "the default.",
                    active_project_name_or_id,
                )
                active_project = self._default_project
        else:
            logger.warning("Active project not set. Setting it to the default.")
            active_project = self._default_project

        active_stack: Optional[StackModel] = None

        # Sanitize the active stack
        if active_stack_id:
            # Ensure that the active stack is still valid
            try:
                active_stack = self.get_stack(stack_id=active_stack_id)
            except KeyError:
                logger.warning(
                    "Stack with id '%s' not found. Setting the active "
                    "stack to the default project stack.",
                    active_stack_id,
                )
            else:
                if active_stack.project_id != active_project.id:
                    logger.warning(
                        "The stack with id '%s' is not in the active project. "
                        "Resetting the active stack to the default "
                        "project stack.",
                        active_stack_id,
                    )
                    active_stack = None
        else:
            logger.warning(
                "The active stack is not set. Setting the "
                "active stack to the default project stack."
            )

        if active_stack is None:
            # If no active stack is set, use the default stack in the project
            # (create one if one is not yet created).
            try:
                active_stack = self._get_default_stack(
                    project_name_or_id=active_project.id,
                    user_name_or_id=self.active_user.id,
                )
            except KeyError:
                active_stack = self._register_default_stack(
                    project_name_or_id=active_project.id,
                    user_name_or_id=self.active_user.id,
                )

        return active_project, active_stack

    # ------
    # Stacks
    # ------

    @track(AnalyticsEvent.REGISTERED_DEFAULT_STACK)
    def _register_default_stack(
        self,
        project_name_or_id: Union[str, UUID],
        user_name_or_id: Union[str, UUID],
    ) -> StackModel:
        """Construct and register the default stack components and the stack
        for a user in a project.

        The default stack contains a local orchestrator and a local artifact
        store.

        Args:
            project_name_or_id: Name or ID of the project to which the stack
                belongs.
            user_name_or_id: The name or ID of the user that owns the stack.

        Raises:
            StackExistsError: If a default stack is already registered for the
                user in the supplied project.
        """
        from zenml.config.global_config import GlobalConfiguration

        project_name = self.get_project(
            project_name_or_id=project_name_or_id
        ).name
        user_name = self.get_user(user_name_or_id=user_name_or_id).name
        try:
            self._get_default_stack(
                project_name_or_id=project_name_or_id,
                user_name_or_id=user_name_or_id,
            )
        except KeyError:
            pass
        else:
            raise StackExistsError(
                f"Default stack already registered for user "
                f"{user_name} in project {project_name}"
            )

        logger.info(
            f"Creating default stack for user {user_name} in project "
            f"{project_name}..."
        )

        # Register the default orchestrator
        orchestrator = self.register_stack_component(
            user_name_or_id=user_name_or_id,
            project_name_or_id=project_name_or_id,
            component=ComponentModel(
                name="default",
                type=StackComponentType.ORCHESTRATOR,
                flavor_name="local",
                configuration={},
            ),
        )

        # Register the default artifact store
        artifact_store_path = os.path.join(
            GlobalConfiguration().config_directory,
            "local_stores",
            "default_local_store",
        )
        io_utils.create_dir_recursive_if_not_exists(artifact_store_path)

        artifact_store = self.register_stack_component(
            user_name_or_id=user_name_or_id,
            project_name_or_id=project_name_or_id,
            component=ComponentModel(
                name="default",
                type=StackComponentType.ARTIFACT_STORE,
                flavor_name="local",
                configuration={"path": artifact_store_path},
            ),
        )

        components = {c.type: c for c in [orchestrator, artifact_store]}
        # Register the default stack
        stack = StackModel(
            name="default", components=components, is_shared=False
        )
        return self.register_stack(
            user_name_or_id=user_name_or_id,
            project_name_or_id=project_name_or_id,
            stack=stack,
        )

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

    # ----------------
    # Stack components
    # ----------------

    # -----------------------
    # Stack component flavors
    # -----------------------

    @property
    def flavors(self) -> List[FlavorModel]:
        """All registered flavors.

        Returns:
            A list of all registered flavors.
        """
        return self.list_flavors()

    # TODO [Baris]: clarify how core and integration flavors are shared and/or
    #   mixed with custom flavors. Shouldn't this be a Repository() method ?
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

        # List all the flavors of the component type
        zenml_flavors = [
            f
            for f in flavor_registry.get_flavors_by_type(
                component_type=component_type
            ).values()
        ]

        # TODO: call this with the right arguments
        custom_flavors = self.list_flavors(component_type=component_type)

        return zenml_flavors + custom_flavors

    # -----
    # Users
    # -----

    @property
    def active_user(self) -> UserModel:
        """The active user.

        Returns:
            The active user.
        """
        return self.get_user(self.active_user_name)

    @property
    def users(self) -> List[UserModel]:
        """All registered users.

        Returns:
            A list of all registered users.
        """
        return self.list_users()

    @property
    def _default_user(self) -> UserModel:
        """Get the default user.

        Returns:
            The default user.

        Raises:
            KeyError: If the default user doesn't exist.
        """
        try:
            return self.get_user(DEFAULT_USERNAME)
        except KeyError:
            raise KeyError("The default user is not configured")

    @track(AnalyticsEvent.CREATED_DEFAULT_USER)
    def _create_default_user(self) -> UserModel:
        """Creates a default user.

        Returns:
            The default user.
        """
        logger.info("Creating default user...")
        return self.create_user(UserModel(name=DEFAULT_USERNAME))

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
        """All registered roles.

        Returns:
            A list of all registered roles.
        """
        return self.list_roles()

    @property
    def role_assignments(self) -> List[RoleAssignmentModel]:
        """All role assignments.

        Returns:
            A list of all role assignments.
        """
        return self.list_role_assignments()

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
        try:
            return self.get_project(DEFAULT_PROJECT_NAME)
        except KeyError:
            raise KeyError("The default project is not configured")

    @track(AnalyticsEvent.CREATED_DEFAULT_PROJECT)
    def _create_default_project(self) -> ProjectModel:
        """Creates a default project.

        Returns:
            The default project.
        """
        logger.info("Creating default project...")
        return self.create_project(ProjectModel(name=DEFAULT_PROJECT_NAME))

    # ------------
    # Repositories
    # ------------

    # ---------
    # Pipelines
    # ---------

    # TODO: is this really needed ?
    def get_pipeline_configuration(self, pipeline_id: UUID) -> Dict[str, str]:
        """Gets the pipeline configuration.

        Args:
            pipeline_id: The ID of the pipeline to get.

        Returns:
            The pipeline configuration.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """
        return self.get_pipeline(pipeline_id).configuration

    # -------------
    # Pipeline runs
    # -------------

    # TODO: is this really needed ?
    def get_run_runtime_configuration(
        self, run_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Gets the runtime configuration for a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            The runtime configuration for the pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """
        run = self.get_run(run_id)
        return run.runtime_configuration

    # ------------------
    # Pipeline run steps
    # ------------------

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
