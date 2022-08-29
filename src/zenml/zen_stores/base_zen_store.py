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

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ml_metadata.proto import metadata_store_pb2

from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import StackComponentExistsError, StackExistsError
from zenml.logger import get_logger
from zenml.models import ComponentModel, FlavorModel, StackModel
from zenml.models.code_models import CodeRepositoryModel
from zenml.models.pipeline_models import (
    PipelineModel,
    PipelineRunModel,
    StepModel,
)
from zenml.models.user_management_models import Project, Role, User
from zenml.utils.analytics_utils import AnalyticsEvent

logger = get_logger(__name__)

DEFAULT_USERNAME = "default"
DEFAULT_PROJECT_NAME = "default"


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
            self.create_default_project()

        if not skip_migration:
            self._migrate_store()

        return self

    def _migrate_store(self) -> None:
        """Migrates the store to the latest version."""
        # Older versions of ZenML didn't have users or projects in the zen
        # store, so we create the default user if it doesn't exists
        self.create_default_user()
        self.create_default_project()

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
        """Check if the given url is valid.

        Args:
            url: The url to check.

        Returns:
            True if the url is valid, False otherwise.
        """

    # Public Interface:

    @property
    @abstractmethod
    def type(self) -> StoreType:
        """The type of zen store.

        Returns:
            The type of zen store.
        """

    @property
    @abstractmethod
    def url(self) -> str:
        """Get the repository URL.

        Returns:
            The repository URL.
        """

    @property
    @abstractmethod
    def stacks_empty(self) -> bool:
        """Check if the store is empty (no stacks are configured).

        The implementation of this method should check if the store is empty
        without having to load all the stacks from the persistent storage.

        Returns:
            True if the store is empty, False otherwise.
        """

    #  .--------.
    # | STACKS |
    # '--------'

    # TODO: [ALEX] add filtering param(s)
    def list_stacks(self) -> List[StackModel]:
        """List all stacks.

        Returns:
            A list of all stacks.
        """
        return self._list_stacks()

    def register_stack(self, stack: StackModel) -> StackModel:
        """Register a new stack.

        Args:
            stack: The stack to register.

        Returns:
            The registered stack.
        """
        return self._register_stack(stack)

    def get_stack(self, stack_id: str) -> StackModel:
        """Get a stack by id.

        Args:
            stack_id: The id of the stack to get.

        Returns:
            The stack with the given id.

        Raises:
            KeyError: if the stack doesn't exist.
        """
        return self._get_stack(stack_id)

    def update_stack(self, stack_id: str, stack: StackModel) -> StackModel:
        """Update an existing stack.

        Args:
            stack_id: The id of the stack to update.
            stack: The stack to update.

        Returns:
            The updated stack.
        """
        return self._update_stack(stack_id, stack)

    def delete_stack(self, stack_id: str) -> None:
        """Delete a stack.

        Args:
            stack_id: The id of the stack to delete.
        """
        self._delete_stack(stack_id)

    #  .-----------------.
    # | STACK COMPONENTS |
    # '------------------'

    # TODO: [ALEX] add filtering param(s)
    def list_stack_component_types(self) -> List[StackComponentType]:
        """List all stack component types.

        Returns:
            A list of all stack component types.
        """
        return self._list_stack_component_types()

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

    # TODO: [ALEX] add filtering param(s)
    def list_stack_components(self) -> List[ComponentModel]:
        """List all stack components.

        Returns:
            All stack components currently registered.
        """
        return self._list_stack_components()

    def get_stack_component(self, component_id: str) -> ComponentModel:
        """Get a stack component by id.

        Args:
            component_id: The id of the stack component to get.

        Returns:
            The stack component with the given id.
        """
        return self._get_stack_component(component_id)

    def update_stack_component(
        self, component_id: str, component: ComponentModel
    ) -> ComponentModel:
        """Update an existing stack component.

        Args:
            component_id: The id of the stack component to update.
            component: The stack component to use for the update.

        Returns:
            The updated stack component.
        """
        return self._update_stack_component(component_id, component)

    def delete_stack_component(self, component_id: str) -> None:
        """Delete a stack component.

        Args:
            component_id: The id of the stack component to delete.

        Raises:
            KeyError: if the stack component doesn't exist.
        """
        self._delete_stack_component(component_id)

    def get_stack_component_side_effects(
        self, component_id: str, run_id: str, pipeline_id: str, stack_id: str
    ) -> Dict[Any]:
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

    #  .------.
    # | STEPS |
    # '-------'

    # TODO: change into an abstract method
    def get_step(self, step_id: str) -> StepModel:
        """Get a step by id.

        Args:
            step_id: The id of the step to get.

        Returns:
            The step with the given id.
        """
        return self._get_step(step_id)

    # TODO: change into an abstract method
    # TODO: use the correct return value + also amend the endpoint as well
    def get_step_outputs(self, step_id: str) -> Dict[str, ArtifactView]:
        """Get a list of outputs for a specific step.

        Args:
            step_id: The id of the step to get outputs for.

        Returns:
            A list of Dicts mapping artifact names to the output artifacts for the step.
        """
        return self._get_step_outputs(step_id)

    # TODO: change into an abstract method
    # TODO: Note that this doesn't have a corresponding API endpoint (consider adding?)
    def get_step_inputs(self, step_id: str) -> Dict[str, ArtifactView]:
        """Get a list of inputs for a specific step.

        Args:
            step_id: The id of the step to get inputs for.

        Returns:
            A list of Dicts mapping artifact names to the input artifacts for the step.
        """
        return self._get_step_inputs(step_id)

    # TODO: change into an abstract method
    # TODO: Note that this doesn't have a corresponding API endpoint (consider adding?)
    # TODO: Discuss whether we even need this, given that the endpoint is on
    # pipeline RUNs
    # TODO: [ALEX] add filtering param(s)
    def list_steps(self, pipeline_id: str) -> List[StepModel]:
        """List all steps for a specific pipeline.

        Args:
            pipeline_id: The id of the pipeline to get steps for.

        Returns:
            A list of all steps for the pipeline.
        """
        return self._list_steps(pipeline_id)

    #  .------.
    # | USERS |
    # '-------'

    # TODO: make the invite_token optional
    # TODO: [ALEX] add filtering param(s)
    def list_users(self, invite_token: str = None) -> List[User]:
        """List all users.

        Args:
            invite_token: Token to use for the invitation.

        Returns:
            A list of all users.
        """
        return self._list_users(invite_token=invite_token)

    def create_user(self, user: User) -> User:
        """Creates a new user.

        Args:
            user: User to be created.

        Returns:
            The newly created user.
        """
        self._track_event(AnalyticsEvent.CREATED_USER)
        return self._create_user(user)

    def get_user(self, user_id: str, invite_token: str = None) -> User:
        """Gets a specific user.

        Args:
            user_name: Name of the user to get.
            invite_token: Token to use for the invitation.

        Returns:
            The requested user.
        """
        # No tracking events, here for consistency
        return self._get_user(user_id, invite_token=invite_token)

    def update_user(self, user_id: str, user: User) -> User:
        """Updates an existing user.

        Args:
            user_id: The id of the user to update.
            user: The user to use for the update.

        Returns:
            The updated user.
        """
        # No tracking events, here for consistency
        return self._update_user(user_id, user)

    def delete_user(self, user_id: str) -> None:
        """Deletes a user.

        Args:
            user_id: ID of the user to delete.
        """
        self._track_event(AnalyticsEvent.DELETED_USER)
        return self._delete_user(user_id)

    def get_role_assignments_for_user(
        self,
        user_id: str,
        # include_team_roles: bool = True, # TODO: Remove these from the
        # SQLStore implementation
    ) -> List[Role]:
        """Fetches all role assignments for a user.

        Args:
            user_id: ID of the user.

        Returns:
            List of role assignments for this user.

        Raises:
            KeyError: If no user or project with the given names exists.
        """
        return self._get_role_assignments_for_user(user_id)

    def assign_role(
        self,
        user_id: str,
        role: Role,
    ) -> None:
        """Assigns a role to a user or team.

        Args:
            user_id: ID of the user.
            role: Role to assign to the user.

        Raises:
            KeyError: If no user with the given ID exists.
        """
        return self._assign_role(user_id, role)

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

    def delete_role(self, user_id: str, role_id: str) -> None:
        """Deletes a role.

        Args:
            user_id: ID of the user.
            role_id: ID of the role.
        """
        self._track_event(AnalyticsEvent.DELETED_ROLE)
        return self._delete_role(user_id, role_id)

    #  .------.
    # | ROLES |
    # '-------'

    # TODO: [ALEX] add filtering param(s)
    @abstractmethod
    def list_roles(self) -> List[Role]:
        """List all roles.

        Returns:
            A list of all roles.
        """

    #  .----------------.
    # | METADATA_CONFIG |
    # '-----------------'

    @abstractmethod
    def get_metadata_config(
        self,
    ) -> Union[
        metadata_store_pb2.ConnectionConfig,
        metadata_store_pb2.MetadataStoreClientConfig,
    ]:
        """Get the TFX metadata config of this ZenStore.

        Returns:
            The TFX metadata config of this ZenStore.
        """

    #  .---------.
    # | PROJECTS |
    # '----------'

    # TODO: [ALEX] add filtering param(s)
    @abstractmethod
    def list_projects(self) -> List[Project]:
        """List all projects.

        Returns:
            A list of all projects.
        """

    def create_project(self, project: Project) -> Project:
        """Creates a new project.

        Args:
            project: The project to create.

        Returns:
            The newly created project.

        Raises:
            EntityExistsError: If an identical project already exists.
        """
        self._track_event(AnalyticsEvent.CREATED_PROJECT)
        return self._create_project(project)

    def get_project(self, project_name: str) -> Project:
        """Gets a specific project.

        Args:
            project_name: Name of the project to get.

        Returns:
            The requested project.

        Raises:
            KeyError: If there is no such project.
        """
        # No tracking events, here for consistency
        return self._get_project(project_name)

    def update_project(self, project_name: str, project: Project) -> Project:
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

    def delete_project(self, project_name: str) -> None:
        """Deletes a project.

        Args:
            project_name: Name of the project to delete.

        Raises:
            KeyError: If the project does not exist.
        """
        self._track_event(AnalyticsEvent.DELETED_PROJECT)
        return self._delete_project(project_name)

    def get_project_stacks(self, project_name: str) -> List[StackModel]:
        """Gets all stacks in a project.

        Args:
            project_name: Name of the project to get.

        Returns:
            A list of all stacks in the project.

        Raises:
            KeyError: if the project doesn't exist.
        """
        return self._get_project_stacks(project_name)

    def create_stack(self, project_name: str, stack: StackModel) -> StackModel:
        """Creates a new stack in a project.

        Args:
            project_name: Name of the project to create the stack in.
            stack: The stack to create.

        Returns:
            The newly created stack.

        Raises:
            EntityExistsError: If an identical stack already exists.
        """
        self._track_event(AnalyticsEvent.CREATED_STACK)
        return self._create_stack(project_name, stack)

    # TODO: [ALEX] add filtering param(s)
    def list_project_stack_components(
        self, project_name: str
    ) -> List[ComponentModel]:
        """Gets all components in a project.

        Args:
            project_name: Name of the project for which to get the components.

        Returns:
            A list of all components in the project.

        Raises:
            KeyError: if the project doesn't exist.
        """
        return self._list_project_stack_components(project_name)

    def get_project_stack_components_by_type(
        self, project_name: str, component_type: ComponentModel
    ) -> List[ComponentModel]:
        """Gets all components in a project of a specific type.

        Args:
            project_name: Name of the project for which to get the components.
            component_type: Type of the components to get.

        Returns:
            A list of all components in the project of the specified type.

        Raises:
            KeyError: if the project doesn't exist.
        """
        return self._get_project_stack_components_by_type(
            project_name, component_type
        )

    def create_stack_component(
        self,
        project_name: str,
        component_type: ComponentModel,
        component: ComponentModel,
    ) -> ComponentModel:
        """Creates a new component in a project.

        Args:
            project_name: Name of the project to create the component in.
            component_type: The component to create.
            component: The component to create.

        Returns:
            The newly created component.

        Raises:
            StackComponentExistsError: If an identical component already exists.
        """
        analytics_metadata = {
            "type": component.type.value,
            "flavor": component.flavor,
        }
        self._track_event(
            AnalyticsEvent.REGISTERED_STACK_COMPONENT,
            metadata=analytics_metadata,
        )
        return self._create_stack_component(
            project_name, component_type, component
        )

    # TODO: [ALEX] add filtering param(s)
    @abstractmethod
    def list_pipelines(self, project_name: str) -> List[PipelineModel]:
        """Gets all pipelines in a project.

        Args:
            project_name: Name of the project to get.

        Returns:
            A list of all pipelines in the project.

        Raises:
            KeyError: if the project doesn't exist.
        """
        return self._list_pipelines(project_name)

    @abstractmethod
    def create_pipeline(
        self, project_name: str, pipeline: PipelineModel
    ) -> PipelineModel:
        """Creates a new pipeline in a project.

        Args:
            project_name: Name of the project to create the pipeline in.
            pipeline: The pipeline to create.

        Returns:
            The newly created pipeline.

        Raises:
            PipelineExistsError: If an identical pipeline already exists.
        """
        self._track_event(AnalyticsEvent.CREATE_PIPELINE)
        return self._create_pipeline(project_name, pipeline)

    @abstractmethod
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
    def set_default_stack(self, project_name: str, stack_id: str) -> StackModel:
        """Sets the default stack in a project.

        Args:
            project_name: Name of the project to set.
            stack_id: The ID of the stack to set as the default.

        Raises:
            KeyError: if the project or stack doesn't exist.
        """
        return self._set_default_stack(project_name, stack_id)

    # TODO: [ALEX] add filtering param(s)
    @abstractmethod
    def list_project_repositories(
        self, project_name: str
    ) -> List[CodeRepositoryModel]:
        """Gets all repositories in a project.

        Args:
            project_name: Name of the project to get.

        Returns:
            A list of all repositories in the project.

        Raises:
            KeyError: if the project doesn't exist.
        """
        return self._list_project_repositories(project_name)

    @abstractmethod
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

    #  .-------------.
    # | REPOSITORIES |
    # '--------------'

    @abstractmethod
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
    def delete_repository(self, repository_id: str):
        """Deletes a repository.

        Args:
            repository_id: The ID of the repository to delete.

        Raises:
            KeyError: if the repository doesn't exist.
        """
        self._track_event(AnalyticsEvent.DELETE_REPOSITORY)
        return self._delete_repository(repository_id)

    #  .-----.
    # | AUTH |
    # '------'

    def login(self) -> None:
        """Logs in to the server."""
        self._track_event(AnalyticsEvent.LOGIN)
        self._login()

    def logout(self) -> None:
        """Logs out of the server."""
        self._track_event(AnalyticsEvent.LOGOUT)
        self._logout()

    #  .----------.
    # | PIPELINES |
    # '-----------'

    # TODO: [ALEX] add filtering param(s)
    def list_pipelines(self, project_name: str) -> List[PipelineModel]:
        """Gets all pipelines in a project.

        Args:
            project_name: Name of the project to get.

        Returns:
            A list of all pipelines in the project.

        Raises:
            KeyError: if the project doesn't exist.
        """
        return self._list_pipelines(project_name)

    @abstractmethod
    def get_pipeline(self, pipeline_id: str) -> Optional[PipelineModel]:
        """Returns a pipeline for the given name.

        Args:
            pipeline_id: ID of the pipeline.

        Returns:
            PipelineModel if found, None otherwise.
        """

    @abstractmethod
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
    def delete_pipeline(self, pipeline_id: str) -> None:
        """Deletes a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to delete.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """
        self._track_event(AnalyticsEvent.DELETE_PIPELINE)
        return self._delete_pipeline(pipeline_id)

    def get_pipeline_runs(self, pipeline_id: str) -> List[PipelineRunModel]:
        """Gets all pipeline runs in a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to get.

        Returns:
            A list of all pipeline runs in the pipeline.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """
        return self._get_pipeline_runs(pipeline_id)

    def create_pipeline_run(
        self, pipeline_id: str, pipeline_run: PipelineRunModel
    ) -> PipelineRunModel:
        """Creates a pipeline run.

        Args:
            pipeline_id: The ID of the pipeline to create the run in.
            pipeline_run: The pipeline run to create.

        Returns:
            The created pipeline run.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """
        return self._create_pipeline_run(pipeline_id, pipeline_run)

    def get_pipeline_configuration(self, pipeline_id: str) -> Dict[Any, Any]:
        """Gets the pipeline configuration.

        Args:
            pipeline_id: The ID of the pipeline to get.

        Returns:
            The pipeline configuration.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """
        return self._get_pipeline_configuration(pipeline_id)

    # @abstractmethod
    # def get_stack_configuration(
    #     self, name: str
    # ) -> Dict[StackComponentType, str]:
    #     """Fetches a stack configuration by name.

    #     Args:
    #         name: The name of the stack to fetch.

    #     Returns:
    #         Dict[StackComponentType, str] for the requested stack name.

    #     Raises:
    #         KeyError: If no stack exists for the given name.
    #     """

    # @property
    # @abstractmethod
    # def stack_configurations(self) -> Dict[str, Dict[StackComponentType, str]]:
    #     """Configurations for all stacks registered in this zen store.

    #     Returns:
    #         Dictionary mapping stack names to Dict[StackComponentType, str]'s
    #     """

    # # Private interface (must be implemented, not to be called by user):

    # @abstractmethod
    # def _update_stack_component(
    #     self,
    #     name: str,
    #     component_type: StackComponentType,
    #     component: ComponentModel,
    # ) -> Dict[str, str]:
    #     """Update a stack component.

    #     Args:
    #         name: The original name of the stack component.
    #         component_type: The type of the stack component to update.
    #         component: The new component to update with.

    #     Raises:
    #         KeyError: If no stack component exists with the given name.
    #     """

    # @abstractmethod
    # def _deregister_stack(self, name: str) -> None:
    #     """Delete a stack from storage.

    #     Args:
    #         name: The name of the stack to be deleted.

    #     Raises:
    #         KeyError: If no stack exists for the given name.
    #     """

    # @abstractmethod
    # def _save_stack(
    #     self,
    #     name: str,
    #     stack_configuration: Dict[StackComponentType, str],
    # ) -> None:
    #     """Add a stack to storage.

    #     Args:
    #         name: The name to save the stack as.
    #         stack_configuration: Dict[StackComponentType, str] to persist.
    #     """

    # @abstractmethod
    # def _get_component_flavor_and_config(
    #     self, component_type: StackComponentType, name: str
    # ) -> Tuple[str, bytes]:
    #     """Fetch the flavor and configuration for a stack component.

    #     Args:
    #         component_type: The type of the component to fetch.
    #         name: The name of the component to fetch.

    #     Returns:
    #         Pair of (flavor, configuration) for stack component, as string and
    #         base64-encoded yaml document, respectively

    #     Raises:
    #         KeyError: If no stack component exists for the given type and name.
    #     """

    # @abstractmethod
    # def _get_stack_component_names(
    #     self, component_type: StackComponentType
    # ) -> List[str]:
    #     """Get names of all registered stack components of a given type.

    #     Args:
    #         component_type: The type of the component to list names for.

    #     Returns:
    #         A list of names as strings.
    #     """

    # @abstractmethod
    # def _delete_stack_component(
    #     self, component_type: StackComponentType, name: str
    # ) -> None:
    #     """Remove a StackComponent from storage.

    #     Args:
    #         component_type: The type of component to delete.
    #         name: Then name of the component to delete.

    #     Raises:
    #         KeyError: If no component exists for given type and name.
    #     """

    # # User, project and role management

    # @property
    # @abstractmethod
    # def teams(self) -> List[Team]:
    #     """All registered teams.

    #     Returns:
    #         A list of all registered teams.
    #     """

    # @abstractmethod
    # def _create_team(self, team_name: str) -> Team:
    #     """Creates a new team.

    #     Args:
    #         team_name: Unique team name.

    #     Returns:
    #         The newly created team.

    #     Raises:
    #         EntityExistsError: If a team with the given name already exists.
    #     """

    # @abstractmethod
    # def _get_team(self, team_name: str) -> Team:
    #     """Gets a specific team.

    #     Args:
    #         team_name: Name of the team to get.

    #     Returns:
    #         The requested team.

    #     Raises:
    #         KeyError: If no team with the given name exists.
    #     """

    # @abstractmethod
    # def _delete_team(self, team_name: str) -> None:
    #     """Deletes a team.

    #     Args:
    #         team_name: Name of the team to delete.

    #     Raises:
    #         KeyError: If no team with the given name exists.
    #     """

    # @abstractmethod
    # def add_user_to_team(self, team_name: str, user_name: str) -> None:
    #     """Adds a user to a team.

    #     Args:
    #         team_name: Name of the team.
    #         user_name: Name of the user.

    #     Raises:
    #         KeyError: If no user and team with the given names exists.
    #     """

    # @abstractmethod
    # def remove_user_from_team(self, team_name: str, user_name: str) -> None:
    #     """Removes a user from a team.

    #     Args:
    #         team_name: Name of the team.
    #         user_name: Name of the user.

    #     Raises:
    #         KeyError: If no user and team with the given names exists.
    #     """

    # @property
    # @abstractmethod
    # def role_assignments(self) -> List[RoleAssignment]:
    #     """All registered role assignments.

    #     Returns:
    #         A list of all registered role assignments.
    #     """

    # @abstractmethod
    # def _get_role(self, role_name: str) -> Role:
    #     """Gets a specific role.

    #     Args:
    #         role_name: Name of the role to get.

    #     Returns:
    #         The requested role.

    #     Raises:
    #         KeyError: If no role with the given name exists.
    #     """

    # @abstractmethod
    # def _create_role(self, role_name: str) -> Role:
    #     """Creates a new role.

    #     Args:
    #         role_name: Unique role name.

    #     Returns:
    #         The newly created role.

    #     Raises:
    #         EntityExistsError: If a role with the given name already exists.
    #     """

    # @abstractmethod
    # def revoke_role(
    #     self,
    #     role_name: str,
    #     entity_name: str,
    #     project_name: Optional[str] = None,
    #     is_user: bool = True,
    # ) -> None:
    #     """Revokes a role from a user or team.

    #     Args:
    #         role_name: Name of the role to revoke.
    #         entity_name: User or team name.
    #         project_name: Optional project name.
    #         is_user: Boolean indicating whether the given `entity_name` refers
    #             to a user.

    #     Raises:
    #         KeyError: If no role, entity or project with the given names exists.
    #     """

    # @abstractmethod
    # def get_users_for_team(self, team_name: str) -> List[User]:
    #     """Fetches all users of a team.

    #     Args:
    #         team_name: Name of the team.

    #     Returns:
    #         List of users that are part of the team.

    #     Raises:
    #         KeyError: If no team with the given name exists.
    #     """

    # @abstractmethod
    # def get_teams_for_user(self, user_name: str) -> List[Team]:
    #     """Fetches all teams for a user.

    #     Args:
    #         user_name: Name of the user.

    #     Returns:
    #         List of teams that the user is part of.

    #     Raises:
    #         KeyError: If no user with the given name exists.
    #     """

    # @abstractmethod
    # def get_role_assignments_for_team(
    #     self,
    #     team_name: str,
    #     project_name: Optional[str] = None,
    # ) -> List[RoleAssignment]:
    #     """Fetches all role assignments for a team.

    #     Args:
    #         team_name: Name of the user.
    #         project_name: Optional filter to only return roles assigned for
    #             this project.

    #     Returns:
    #         List of role assignments for this team.

    #     Raises:
    #         KeyError: If no team or project with the given names exists.
    #     """

    # # Pipelines and pipeline runs

    # @abstractmethod
    # def get_pipeline_run(
    #     self, pipeline: PipelineView, run_name: str
    # ) -> Optional[PipelineRunView]:
    #     """Gets a specific run for the given pipeline.

    #     Args:
    #         pipeline: The pipeline for which to get the run.
    #         run_name: The name of the run to get.

    #     Returns:
    #         The pipeline run with the given name.
    #     """

    # @abstractmethod
    # def get_pipeline_runs(
    #     self, pipeline: PipelineView
    # ) -> Dict[str, PipelineRunView]:
    #     """Gets all runs for the given pipeline.

    #     Args:
    #         pipeline: a Pipeline object for which you want the runs.

    #     Returns:
    #         A dictionary of pipeline run names to PipelineRunView.
    #     """

    # @abstractmethod
    # def get_pipeline_run_wrapper(
    #     self,
    #     pipeline_name: str,
    #     run_name: str,
    #     project_name: Optional[str] = None,
    # ) -> PipelineRunModel:
    #     """Gets a pipeline run.

    #     Args:
    #         pipeline_name: Name of the pipeline for which to get the run.
    #         run_name: Name of the pipeline run to get.
    #         project_name: Optional name of the project from which to get the
    #             pipeline run.

    #     Raises:
    #         KeyError: If no pipeline run (or project) with the given name
    #             exists.
    #     """

    # @abstractmethod
    # def get_pipeline_run_wrappers(
    #     self, pipeline_name: str, project_name: Optional[str] = None
    # ) -> List[PipelineRunModel]:
    #     """Gets pipeline runs.

    #     Args:
    #         pipeline_name: Name of the pipeline for which to get runs.
    #         project_name: Optional name of the project from which to get the
    #             pipeline runs.
    #     """

    # @abstractmethod
    # def get_pipeline_run_steps(
    #     self, pipeline_run: PipelineRunView
    # ) -> Dict[str, StepView]:
    #     """Gets all steps for the given pipeline run.

    #     Args:
    #         pipeline_run: The pipeline run to get the steps for.

    #     Returns:
    #         A dictionary of step names to step views.
    #     """

    # @abstractmethod
    # def get_step_status(self, step: StepView) -> ExecutionStatus:
    #     """Gets the execution status of a single step.

    #     Args:
    #         step (StepView): The step to get the status for.

    #     Returns:
    #         ExecutionStatus: The status of the step.
    #     """

    # @abstractmethod
    # def get_producer_step_from_artifact(self, artifact_id: int) -> StepView:
    #     """Returns original StepView from an ArtifactView.

    #     Args:
    #         artifact_id: ID of the ArtifactView to be queried.

    #     Returns:
    #         Original StepView that produced the artifact.
    #     """

    # @abstractmethod
    # def register_pipeline_run(
    #     self,
    #     pipeline_run: PipelineRunModel,
    # ) -> None:
    #     """Registers a pipeline run.

    #     Args:
    #         pipeline_run: The pipeline run to register.

    #     Raises:
    #         EntityExistsError: If a pipeline run with the same name already
    #             exists.
    #     """

    # # Stack component flavors

    # @property
    # @abstractmethod
    # def flavors(self) -> List[FlavorModel]:
    #     """All registered flavors.

    #     Returns:
    #         A list of all registered flavors.
    #     """

    # @abstractmethod
    # def _create_flavor(
    #     self,
    #     source: str,
    #     name: str,
    #     stack_component_type: StackComponentType,
    # ) -> FlavorModel:
    #     """Creates a new flavor.

    #     Args:
    #         source: the source path to the implemented flavor.
    #         name: the name of the flavor.
    #         stack_component_type: the corresponding StackComponentType.

    #     Returns:
    #         The newly created flavor.

    #     Raises:
    #         EntityExistsError: If a flavor with the given name and type
    #             already exists.
    #     """

    # @abstractmethod
    # def get_flavors_by_type(
    #     self, component_type: StackComponentType
    # ) -> List[FlavorModel]:
    #     """Fetch all flavor defined for a specific stack component type.

    #     Args:
    #         component_type: The type of the stack component.

    #     Returns:
    #         List of all the flavors for the given stack component type.
    #     """

    # @abstractmethod
    # def get_flavor_by_name_and_type(
    #     self,
    #     flavor_name: str,
    #     component_type: StackComponentType,
    # ) -> FlavorModel:
    #     """Fetch a flavor by a given name and type.

    #     Args:
    #         flavor_name: The name of the flavor.
    #         component_type: Optional, the type of the component.

    #     Returns:
    #         Flavor instance if it exists

    #     Raises:
    #         KeyError: If no flavor exists with the given name and type
    #             or there are more than one instances
    #     """

    # # Common code (user facing):

    # @property
    # def stacks(self) -> List[StackModel]:
    #     """All stacks registered in this zen store.

    #     Returns:
    #         A list of all stacks registered in this zen store.
    #     """
    #     return [
    #         self._stack_from_dict(name, conf)
    #         for name, conf in self.stack_configurations.items()
    #     ]

    # def get_stack(self, name: str) -> StackModel:
    #     """Fetch a stack by name.

    #     Args:
    #         name: The name of the stack to retrieve.

    #     Returns:
    #         StackWrapper instance if the stack exists.
    #     """
    #     return self._stack_from_dict(name, self.get_stack_configuration(name))

    # def _update_stack(self, name: str, stack: StackModel) -> None:
    #     """Update a stack and its components.

    #     If any of the stack's components aren't registered in the stack store
    #     yet, this method will try to register them as well.

    #     Args:
    #         name: The original name of the stack.
    #         stack: The new stack to use in the update.

    #     Raises:
    #         KeyError: If no stack exists with the given name.
    #         StackExistsError: If a stack with the same name already exists.
    #     """
    #     try:
    #         self.get_stack(name)
    #     except KeyError:
    #         raise KeyError(
    #             f"Unable to update stack with name '{stack.name}': No existing "
    #             f"stack found with this name."
    #         )

    #     try:
    #         renamed_stack = self.get_stack(stack.name)
    #         if (name != stack.name) and renamed_stack:
    #             raise StackExistsError(
    #                 f"Unable to update stack with name '{stack.name}': Found "
    #                 f"existing stack with this name."
    #             )
    #     except KeyError:
    #         pass

    #     def __check_component(
    #         component: ComponentModel,
    #     ) -> Tuple[StackComponentType, str]:
    #         """Try to register a stack component, if it doesn't exist.

    #         Args:
    #             component: StackComponentWrapper to register.

    #         Returns:
    #             The type and name of the component.
    #         """
    #         try:
    #             _ = self.get_stack_component(
    #                 component_type=component.type, name=component.name
    #             )
    #         except KeyError:
    #             self._register_stack_component(component)
    #         return component.type, component.name

    #     stack_configuration = {
    #         typ: name for typ, name in map(__check_component, stack.components)
    #     }
    #     self._save_stack(stack.name, stack_configuration)

    #     logger.info("Updated stack with name '%s'.", name)
    #     if name != stack.name:
    #         self.deregister_stack(name)

    # def get_stack_component(
    #     self, component_type: StackComponentType, name: str
    # ) -> ComponentModel:
    #     """Get a registered stack component.

    #     Args:
    #         component_type: The type of the component.
    #         name: The name of the component.

    #     Returns:
    #         The component.
    #     """
    #     flavor, config = self._get_component_flavor_and_config(
    #         component_type, name=name
    #     )
    #     uuid = yaml.safe_load(base64.b64decode(config).decode())["uuid"]
    #     return ComponentModel(
    #         type=component_type,
    #         flavor=flavor,
    #         name=name,
    #         uuid=uuid,
    #         config=config,
    #     )

    # def get_stack_components(
    #     self, component_type: StackComponentType
    # ) -> List[ComponentModel]:
    #     """Fetches all registered stack components of the given type.

    #     Args:
    #         component_type: StackComponentType to list members of

    #     Returns:
    #         A list of StackComponentConfiguration instances.
    #     """
    #     return [
    #         self.get_stack_component(component_type=component_type, name=name)
    #         for name in self._get_stack_component_names(component_type)
    #     ]

    # def deregister_stack_component(
    #     self, component_type: StackComponentType, name: str
    # ) -> None:
    #     """Deregisters a stack component.

    #     Args:
    #         component_type: The type of the component to deregister.
    #         name: The name of the component to deregister.

    #     Raises:
    #         ValueError: if trying to deregister a component that's part
    #             of a stack.
    #     """
    #     for stack_name, stack_config in self.stack_configurations.items():
    #         if stack_config.get(component_type) == name:
    #             raise ValueError(
    #                 f"Unable to deregister stack component (type: "
    #                 f"{component_type}, name: {name}) that is part of a "
    #                 f"registered stack (stack name: '{stack_name}')."
    #             )
    #     self._delete_stack_component(component_type, name=name)

    # def register_default_stack(self) -> None:
    #     """Populates the store with the default Stack.

    #     The default stack contains a local orchestrator and a local artifact
    #     store.
    #     """
    #     stack = Stack.default_local_stack()
    #     sw = StackModel.from_stack(stack)
    #     self._register_stack(sw)
    #     metadata = {c.type.value: c.flavor for c in sw.components}
    #     metadata["store_type"] = self.type.value
    #     self._track_event(
    #         AnalyticsEvent.REGISTERED_DEFAULT_STACK, metadata=metadata
    #     )

    # def create_default_user(self) -> None:
    #     """Creates a default user."""
    #     try:
    #         self.get_user(user_name=DEFAULT_USERNAME)
    #     except KeyError:
    #         # Use private interface and send custom tracking event
    #         self._track_event(AnalyticsEvent.CREATED_DEFAULT_USER)
    #         self._create_user(user_name=DEFAULT_USERNAME)

    # def create_default_project(self) -> None:
    #     """Creates a default project."""
    #     try:
    #         self.get_project(project_name=DEFAULT_PROJECT_NAME)
    #     except KeyError:
    #         # Use private interface and send custom tracking event
    #         self._track_event(AnalyticsEvent.CREATED_DEFAULT_PROJECT)
    #         self._create_project(project_name=DEFAULT_PROJECT_NAME)

    # # Common code (internal implementations, private):

    # def _track_event(
    #     self,
    #     event: Union[str, AnalyticsEvent],
    #     metadata: Optional[Dict[str, Any]] = None,
    # ) -> bool:
    #     """Track an analytics event.

    #     Args:
    #         event: The event to track.
    #         metadata: Additional metadata to track with the event.

    #     Returns:
    #         True if the event was successfully tracked, False otherwise.
    #     """
    #     if self._track_analytics:
    #         return track_event(event, metadata)
    #     return False

    # def _stack_from_dict(
    #     self, name: str, stack_configuration: Dict[StackComponentType, str]
    # ) -> StackModel:
    #     """Build a StackWrapper from stored configurations.

    #     Args:
    #         name: The name of the stack.
    #         stack_configuration: The configuration of the stack.

    #     Returns:
    #         A StackWrapper instance.
    #     """
    #     stack_components = [
    #         self.get_stack_component(
    #             component_type=component_type, name=component_name
    #         )
    #         for component_type, component_name in stack_configuration.items()
    #     ]
    #     return StackModel(name=name, components=stack_components)

    # # Public facing APIs
    # # TODO [ENG-894]: Refactor these with the proxy pattern, as noted in
    # #  the [review comment](https://github.com/zenml-io/zenml/pull/589#discussion_r875003334)

    # def update_stack_component(
    #     self,
    #     name: str,
    #     component_type: StackComponentType,
    #     component: ComponentModel,
    # ) -> Dict[str, str]:
    #     """Update a stack component.

    #     Args:
    #         name: The original name of the stack component.
    #         component_type: The type of the stack component to update.
    #         component: The new component to update with.

    #     Returns:
    #         The updated stack configuration.
    #     """
    #     analytics_metadata = {
    #         "type": component.type.value,
    #         "flavor": component.flavor,
    #     }
    #     self._track_event(
    #         AnalyticsEvent.UPDATED_STACK_COMPONENT,
    #         metadata=analytics_metadata,
    #     )
    #     return self._update_stack_component(name, component_type, component)

    # def deregister_stack(self, name: str) -> None:
    #     """Delete a stack from storage.

    #     Args:
    #         name: The name of the stack to be deleted.

    #     Returns:
    #         None.
    #     """
    #     # No tracking events, here for consistency
    #     return self._deregister_stack(name)

    # def create_team(self, team_name: str) -> Team:
    #     """Creates a new team.

    #     Args:
    #         team_name: Unique team name.

    #     Returns:
    #         The newly created team.
    #     """
    #     self._track_event(AnalyticsEvent.CREATED_TEAM)
    #     return self._create_team(team_name)

    # def get_team(self, team_name: str) -> Team:
    #     """Gets a specific team.

    #     Args:
    #         team_name: Name of the team to get.

    #     Returns:
    #         The requested team.
    #     """
    #     # No tracking events, here for consistency
    #     return self._get_team(team_name)

    # def delete_team(self, team_name: str) -> None:
    #     """Deletes a team.

    #     Args:
    #         team_name: Name of the team to delete.

    #     Returns:
    #         None
    #     """
    #     self._track_event(AnalyticsEvent.DELETED_TEAM)
    #     return self._delete_team(team_name)

    # def get_role(self, role_name: str) -> Role:
    #     """Gets a specific role.

    #     Args:
    #         role_name: Name of the role to get.

    #     Returns:
    #         The requested role.
    #     """
    #     # No tracking events, here for consistency
    #     return self._get_role(role_name)

    # def create_role(self, role_name: str) -> Role:
    #     """Creates a new role.

    #     Args:
    #         role_name: Unique role name.

    #     Returns:
    #         The newly created role.
    #     """
    #     self._track_event(AnalyticsEvent.CREATED_ROLE)
    #     return self._create_role(role_name)

    # def create_flavor(
    #     self,
    #     source: str,
    #     name: str,
    #     stack_component_type: StackComponentType,
    # ) -> FlavorModel:
    #     """Creates a new flavor.

    #     Args:
    #         source: the source path to the implemented flavor.
    #         name: the name of the flavor.
    #         stack_component_type: the corresponding StackComponentType.

    #     Returns:
    #         The newly created flavor.
    #     """
    #     analytics_metadata = {
    #         "type": stack_component_type.value,
    #     }
    #     track_event(
    #         AnalyticsEvent.CREATED_FLAVOR,
    #         metadata=analytics_metadata,
    #     )
    #     return self._create_flavor(source, name, stack_component_type)

    # def register_stack(self, stack: StackModel) -> None:
    #     """Register a stack and its components.

    #     If any of the stack's components aren't registered in the zen store
    #     yet, this method will try to register them as well.

    #     Args:
    #         stack: The stack to register.

    #     Returns:
    #         None
    #     """
    #     metadata = {c.type.value: c.flavor for c in stack.components}
    #     metadata["store_type"] = self.type.value
    #     track_event(AnalyticsEvent.REGISTERED_STACK, metadata=metadata)
    #     return self._register_stack(stack)

    # def update_stack(self, name: str, stack: StackModel) -> None:
    #     """Update a stack and its components.

    #     If any of the stack's components aren't registered in the stack store
    #     yet, this method will try to register them as well.

    #     Args:
    #         name: The original name of the stack.
    #         stack: The new stack to use in the update.

    #     Returns:
    #         None.
    #     """
    #     metadata = {c.type.value: c.flavor for c in stack.components}
    #     metadata["store_type"] = self.type.value
    #     track_event(AnalyticsEvent.UPDATED_STACK, metadata=metadata)
    #     return self._update_stack(name, stack)

    ## PRIVATE PAIRED METHODS

    @abstractmethod
    def _create_user(self, user: User) -> User:
        """Creates a new user.

        Args:
            user_name: Unique username.

        Returns:
                The newly created user.

        Raises:
            EntityExistsError: If a user with the given name already exists.
        """

    @abstractmethod
    def _get_user(self, user_id: str, invite_token: str = None) -> User:
        """Get a specific user by name.

        Args:
            user_name: Name of the user to get.

        Returns:
            The requested user, if it was found.

        Raises:
            KeyError: If no user with the given name exists.
        """

    @abstractmethod
    def _update_user(self, user_id: str, user: User) -> User:
        """Update the user.

        Args:
            user_id: ID of the user.
            user: The User model to use for the update.

        Returns:
            The updated user.
        """

    @abstractmethod
    def _delete_user(self, user_id: str) -> None:
        """Deletes a user.

        Args:
            user_id: The ID of the user to delete.

        Raises:
            KeyError: If no user with the given name exists.
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
    def _create_project(self, project: Project) -> Project:
        """Creates a new project.

        Args:
            project: The project to create.

        Returns:
            The newly created project.

        Raises:
            EntityExistsError: If a project with the given name already exists.
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
    def _update_project(self, project_name: str, project: Project) -> Project:
        """Update an existing project.

        Args:
            project_name: Name of the project to update.
            project: The project to use for the update.

        Returns:
            The updated project.

        Raises:
            KeyError: if the project does not exist.
        """

    @abstractmethod
    def _delete_project(self, project_name: str) -> None:
        """Deletes a project.

        Args:
            project_name: Name of the project to delete.

        Raises:
            KeyError: If no project with the given name exists.
        """

    @abstractmethod
    def _get_project_stacks(self, project_name: str) -> List[StackModel]:
        """Get all stacks in the project.

        Args:
            project_name: the name of the project.

        Returns:
            A list of all stacks in the project.

        Raises:
            KeyError: if the project doesn't exist.
        """

    # TODO: rework to use the project_name
    def _create_stack(self, project_name: str, stack: StackModel) -> None:
        """Create a stack and its components for a particular project.

        If any of the stack's components aren't registered in the ZenStore
        yet, this method will try to register them as well.

        Args:
            project_name: Name of the project.
            stack: The stack to create.

        Raises:
            StackExistsError: If a stack with the same name already exists.
        """
        try:
            self.get_stack(stack.name)
        except KeyError:
            pass
        else:
            raise StackExistsError(
                f"Unable to create stack with name '{stack.name}': Found "
                f"existing stack with this name."
            )

        def __check_component(
            component: ComponentModel,
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
                if existing_component.id != component.id:
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
        logger.info("Created stack with name '%s'.", stack.name)

    @abstractmethod
    def _list_project_stack_components(
        self, project_name: str
    ) -> List[ComponentModel]:
        """List all stack components in the project.

        Args:
            project_name: Name of the project.

        Returns:
            A list of stack components.

        Raises:
            KeyError: if the project does not exist.
        """

    @abstractmethod
    def _list_pipelines(self, project_name: str) -> List[PipelineModel]:
        """List all pipelines in the project.

        Args:
            project_name: Name of the project.

        Returns:
            A list of pipelines.

        Raises:
            KeyError: if the project does not exist.
        """

    @abstractmethod
    def _create_pipeline(
        self, project_name: str, pipeline: PipelineModel
    ) -> PipelineModel:
        """Creates a new pipeline in a project.

        Args:
            project_name: Name of the project to create the pipeline in.
            pipeline: The pipeline to create.

        Returns:
            The newly created pipeline.

        Raises:
            PipelineExistsError: If an identical pipeline already exists.
        """

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

    @abstractmethod
    def _list_project_repositories(
        self, project_name: str
    ) -> List[CodeRepositoryModel]:
        """Get all repositories in the project.

        Args:
            project_name: the name of the project.

        Returns:
            A list of all repositories in the project.

        Raises:
            KeyError: if the project doesn't exist.
        """

    @abstractmethod
    def _connect_project_repository(
        self, project_name: str, repository: CodeRepositoryModel
    ) -> CodeRepositoryModel:
        """Connect a repository to a project.

        Args:
            project_name: the name of the project.
            repository: the repository to connect.

        Returns:
            The connected repository.

        Raises:
            KeyError: if the project or repository doesn't exist.
        """

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

    @abstractmethod
    def _delete_repository(self, repository_id: str) -> None:
        """Delete a repository.

        Args:
            repository_id: The ID of the repository to delete.

        Raises:
            KeyError: if the repository doesn't exist.
        """

    @abstractmethod
    def _list_stacks(self) -> List[StackModel]:
        """List all stacks.

        Returns:
            A list of all stacks.
        """

    @abstractmethod
    def _register_stack(self, stack: StackModel) -> StackModel:
        """Register a new stack.

        Args:
            stack: The stack to register.

        Returns:
            The registered stack.
        """

    @abstractmethod
    def _get_stack(self, stack_id: str) -> StackModel:
        """Get a stack by ID.

        Args:
            stack_id: The ID of the stack to get.

        Returns:
            The stack.

        Raises:
            KeyError: if the stack doesn't exist.
        """

    @abstractmethod
    def _update_stack(self, stack_id: str, stack: StackModel) -> StackModel:
        """Update a stack.

        Args:
            stack_id: The ID of the stack to update.
            stack: The stack to use for the update.

        Returns:
            The updated stack.

        Raises:
            KeyError: if the stack doesn't exist.
        """

    @abstractmethod
    def _delete_stack(self, stack_id: str) -> None:
        """Delete a stack.

        Args:
            stack_id: The ID of the stack to delete.

        Raises:
            KeyError: if the stack doesn't exist.
        """

    @abstractmethod
    def _list_stack_component_types(self) -> List[StackComponentType]:
        """List all stack component types.

        Returns:
            A list of all stack component types.
        """

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

    @abstractmethod
    def _list_stack_components(self) -> List[ComponentModel]:
        """List all stack components.

        Returns:
            A list of all stack components.
        """

    @abstractmethod
    def _get_stack_component(self, component_id: str) -> ComponentModel:
        """Get a stack component by ID.

        Args:
            component_id: The ID of the stack component to get.

        Returns:
            The stack component.

        Raises:
            KeyError: if the stack component doesn't exist.
        """

    @abstractmethod
    def _update_stack_component(
        self, component_id: str, component: ComponentModel
    ):
        """Update a stack component.

        Args:
            component_id: The ID of the stack component to update.
            component: The stack component to use for the update.

        Returns:
            The updated stack component.

        Raises:
            KeyError: if the stack component doesn't exist.
        """

    @abstractmethod
    def _delete_stack_component(self, component_id: str) -> None:
        """Delete a stack component.

        Args:
            component_id: The ID of the stack component to delete.

        Raises:
            KeyError: if the stack component doesn't exist.
        """

    @abstractmethod
    def _get_stack_component_side_effects(
        self, component_id: str, run_id: str, pipeline_id: str, stack_id: str
    ) -> Dict[Any]:
        """Get the side effects of a stack component.

        Args:
            component_id: The ID of the stack component to get side effects for.
            run_id: The ID of the run to get side effects for.
            pipeline_id: The ID of the pipeline to get side effects for.
            stack_id: The ID of the stack to get side effects for.
        """

    @abstractmethod
    def _get_step(self, step_id: str) -> StepModel:
        """Get a step by ID.

        Args:
            step_id: The ID of the step to get.

        Returns:
            The step.

        Raises:
            KeyError: if the step doesn't exist.
        """

    @abstractmethod
    def _get_step_outputs(self, step_id: str) -> Dict[str, ArtifactView]:
        """Get the outputs of a step.

        Args:
            step_id: The ID of the step to get outputs for.

        Returns:
            The outputs of the step.
        """

    @abstractmethod
    def _get_step_inputs(self, step_id: str) -> Dict[str, ArtifactView]:
        """Get the inputs of a step.

        Args:
            step_id: The ID of the step to get inputs for.

        Returns:
            The inputs of the step.
        """

    @abstractmethod
    def _list_steps(self, pipeline_id: str) -> List[StepModel]:
        """List all steps.

        Args:
            pipeline_id: The ID of the pipeline to list steps for.

        Returns:
            A list of all steps.
        """

    @abstractmethod
    def _list_users(self, invite_token: str = None) -> List[User]:
        """List all users.

        Args:
            invite_token: The invite token to filter by.

        Returns:
            A list of all users.
        """

    @abstractmethod
    def _get_role_assignments_for_user(self, user_id: str) -> List[Role]:
        """Get the role assignments for a user.

        Args:
            user_id: The ID of the user to get role assignments for.

        Returns:
            The role assignments for the user.
        """

    @abstractmethod
    def _assign_role(self, user_id: str, role: Role) -> None:
        """Assign a role to a user.

        Args:
            user_id: The ID of the user to assign the role to.
            role: The role to assign.
        """

    def _login(self) -> None:
        """Logs in to the server."""

    def _logout(self) -> None:
        """Logs out of the server."""

    @abstractmethod
    def _list_pipelines(self, project_name: str) -> List[PipelineModel]:
        """Gets all pipelines in a project.

        Args:
            project_name: Name of the project to get.

        Returns:
            A list of all pipelines in the project.

        Raises:
            KeyError: if the project doesn't exist.
        """

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

    @abstractmethod
    def _delete_pipeline(self, pipeline_id: str) -> None:
        """Deletes a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to delete.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """

    @abstractmethod
    def _get_pipeline_runs(self, pipeline_id: str) -> List[PipelineRunModel]:
        """Gets all pipeline runs in a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to get.

        Returns:
            A list of all pipeline runs in the pipeline.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """

    @abstractmethod
    def _create_pipeline_run(
        self, pipeline_id: str, pipeline_run: PipelineRunModel
    ) -> PipelineRunModel:
        """Creates a pipeline run.

        Args:
            pipeline_id: The ID of the pipeline to create the run in.
            pipeline_run: The pipeline run to create.

        Returns:
            The created pipeline run.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """

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

    # PROPERTIES

    @property
    @abstractmethod
    def users(self) -> List[User]:
        """All registered users.

        Returns:
            A list of all registered users.
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
    def projects(self) -> List[Project]:
        """All registered projects.

        Returns:
            A list of all registered projects.
        """


# Generalised TODOs
# - fix the exceptions
# - be consistent about which raise KeyErrors
