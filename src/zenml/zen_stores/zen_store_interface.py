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

import datetime
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Union
from uuid import UUID

from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.enums import StackDeploymentProvider
from zenml.models import (
    ActionFilter,
    ActionRequest,
    ActionResponse,
    ActionUpdate,
    APIKeyFilter,
    APIKeyRequest,
    APIKeyResponse,
    APIKeyRotateRequest,
    APIKeyUpdate,
    ArtifactFilter,
    ArtifactRequest,
    ArtifactResponse,
    ArtifactUpdate,
    ArtifactVersionFilter,
    ArtifactVersionRequest,
    ArtifactVersionResponse,
    ArtifactVersionUpdate,
    ArtifactVisualizationResponse,
    CodeReferenceResponse,
    CodeRepositoryFilter,
    CodeRepositoryRequest,
    CodeRepositoryResponse,
    CodeRepositoryUpdate,
    ComponentFilter,
    ComponentRequest,
    ComponentResponse,
    ComponentUpdate,
    DeployedStack,
    EventSourceFilter,
    EventSourceRequest,
    EventSourceResponse,
    EventSourceUpdate,
    FlavorFilter,
    FlavorRequest,
    FlavorResponse,
    FlavorUpdate,
    LogsResponse,
    ModelFilter,
    ModelRequest,
    ModelResponse,
    ModelUpdate,
    ModelVersionArtifactFilter,
    ModelVersionArtifactRequest,
    ModelVersionArtifactResponse,
    ModelVersionFilter,
    ModelVersionPipelineRunFilter,
    ModelVersionPipelineRunRequest,
    ModelVersionPipelineRunResponse,
    ModelVersionRequest,
    ModelVersionResponse,
    ModelVersionUpdate,
    OAuthDeviceFilter,
    OAuthDeviceResponse,
    OAuthDeviceUpdate,
    Page,
    PipelineBuildFilter,
    PipelineBuildRequest,
    PipelineBuildResponse,
    PipelineDeploymentFilter,
    PipelineDeploymentRequest,
    PipelineDeploymentResponse,
    PipelineFilter,
    PipelineRequest,
    PipelineResponse,
    PipelineRunFilter,
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineRunUpdate,
    PipelineUpdate,
    ProjectFilter,
    ProjectRequest,
    ProjectResponse,
    ProjectUpdate,
    RunMetadataRequest,
    RunTemplateFilter,
    RunTemplateRequest,
    RunTemplateResponse,
    RunTemplateUpdate,
    ScheduleFilter,
    ScheduleRequest,
    ScheduleResponse,
    ScheduleUpdate,
    SecretFilter,
    SecretRequest,
    SecretResponse,
    SecretUpdate,
    ServerModel,
    ServerSettingsResponse,
    ServerSettingsUpdate,
    ServiceAccountFilter,
    ServiceAccountRequest,
    ServiceAccountResponse,
    ServiceAccountUpdate,
    ServiceConnectorFilter,
    ServiceConnectorRequest,
    ServiceConnectorResourcesModel,
    ServiceConnectorResponse,
    ServiceConnectorTypeModel,
    ServiceConnectorUpdate,
    ServiceFilter,
    ServiceRequest,
    ServiceResponse,
    ServiceUpdate,
    StackDeploymentConfig,
    StackDeploymentInfo,
    StackFilter,
    StackRequest,
    StackResponse,
    StackUpdate,
    StepRunFilter,
    StepRunRequest,
    StepRunResponse,
    StepRunUpdate,
    TagFilter,
    TagRequest,
    TagResourceRequest,
    TagResourceResponse,
    TagResponse,
    TagUpdate,
    TriggerExecutionFilter,
    TriggerExecutionResponse,
    TriggerFilter,
    TriggerRequest,
    TriggerResponse,
    TriggerUpdate,
    UserFilter,
    UserRequest,
    UserResponse,
    UserUpdate,
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

       * create methods - store a new resource. These methods
         should fill in generated fields (e.g. UUIDs, creation timestamps) in
         the resource and return the updated resource.
       * get methods - retrieve a single existing resource identified by a
         unique key or identifier from the store. These methods should always
         return a resource and raise an exception if the resource does not
         exist.
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
      * methods for resources that have two or more unique keys (e.g. a project
      is uniquely identified by its name as well as its UUID) should reflect
      that in the method variants and/or method arguments:
        * methods that take in a resource identifier as argument should accept
        all variants of the identifier (e.g. `project_name_or_uuid` for methods
        that get/list/update/delete projects)
        * if a compound key is involved, separate get methods should be
        implemented (e.g. `get_pipeline` to get a pipeline by ID and
        `get_pipeline_in_project` to get a pipeline by its name and the ID of
        the project it belongs to)
      * methods for resources that are scoped as children of other resources
      (e.g. a pipeline is always owned by a project) should reflect the
      key(s) of the parent resource in the provided method arguments:
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

    @abstractmethod
    def get_store_info(self) -> ServerModel:
        """Get information about the store.

        Returns:
            Information about the store.
        """

    @abstractmethod
    def get_deployment_id(self) -> UUID:
        """Get the ID of the deployment.

        Returns:
            The ID of the deployment.
        """

    # -------------------- Server Settings --------------------

    @abstractmethod
    def get_server_settings(
        self, hydrate: bool = True
    ) -> ServerSettingsResponse:
        """Get the server settings.

        Args:
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The server settings.
        """

    @abstractmethod
    def update_server_settings(
        self, settings_update: ServerSettingsUpdate
    ) -> ServerSettingsResponse:
        """Update the server settings.

        Args:
            settings_update: The server settings update.

        Returns:
            The updated server settings.
        """

    # -------------------- Actions  --------------------

    @abstractmethod
    def create_action(self, action: ActionRequest) -> ActionResponse:
        """Create an action.

        Args:
            action: The action to create.

        Returns:
            The created action.
        """

    @abstractmethod
    def get_action(
        self,
        action_id: UUID,
        hydrate: bool = True,
    ) -> ActionResponse:
        """Get an action by ID.

        Args:
            action_id: The ID of the action to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The action.

        Raises:
            KeyError: If the action doesn't exist.
        """

    @abstractmethod
    def list_actions(
        self,
        action_filter_model: ActionFilter,
        hydrate: bool = False,
    ) -> Page[ActionResponse]:
        """List all actions matching the given filter criteria.

        Args:
            action_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all actions matching the filter criteria.
        """

    @abstractmethod
    def update_action(
        self,
        action_id: UUID,
        action_update: ActionUpdate,
    ) -> ActionResponse:
        """Update an existing action.

        Args:
            action_id: The ID of the action to update.
            action_update: The update to be applied to the action.

        Returns:
            The updated action.

        Raises:
            KeyError: If the action doesn't exist.
        """

    @abstractmethod
    def delete_action(self, action_id: UUID) -> None:
        """Delete an action.

        Args:
            action_id: The ID of the action to delete.

        Raises:
            KeyError: If the action doesn't exist.
        """

    # -------------------- API Keys --------------------

    @abstractmethod
    def create_api_key(
        self, service_account_id: UUID, api_key: APIKeyRequest
    ) -> APIKeyResponse:
        """Create a new API key for a service account.

        Args:
            service_account_id: The ID of the service account for which to
                create the API key.
            api_key: The API key to create.

        Returns:
            The created API key.

        Raises:
            KeyError: If the service account doesn't exist.
            EntityExistsError: If an API key with the same name is already
                configured for the same service account.
        """

    @abstractmethod
    def get_api_key(
        self,
        service_account_id: UUID,
        api_key_name_or_id: Union[str, UUID],
        hydrate: bool = True,
    ) -> APIKeyResponse:
        """Get an API key for a service account.

        Args:
            service_account_id: The ID of the service account for which to fetch
                the API key.
            api_key_name_or_id: The name or ID of the API key to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The API key with the given ID.

        Raises:
            KeyError: if an API key with the given name or ID is not configured
                for the given service account.
        """

    @abstractmethod
    def list_api_keys(
        self,
        service_account_id: UUID,
        filter_model: APIKeyFilter,
        hydrate: bool = False,
    ) -> Page[APIKeyResponse]:
        """List all API keys for a service account matching the given filter criteria.

        Args:
            service_account_id: The ID of the service account for which to list
                the API keys.
            filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all API keys matching the filter criteria.
        """

    @abstractmethod
    def update_api_key(
        self,
        service_account_id: UUID,
        api_key_name_or_id: Union[str, UUID],
        api_key_update: APIKeyUpdate,
    ) -> APIKeyResponse:
        """Update an API key for a service account.

        Args:
            service_account_id: The ID of the service account for which to update
                the API key.
            api_key_name_or_id: The name or ID of the API key to update.
            api_key_update: The update request on the API key.

        Returns:
            The updated API key.

        Raises:
            KeyError: if an API key with the given name or ID is not configured
                for the given service account.
            EntityExistsError: if the API key update would result in a name
                conflict with an existing API key for the same service account.
        """

    @abstractmethod
    def rotate_api_key(
        self,
        service_account_id: UUID,
        api_key_name_or_id: Union[str, UUID],
        rotate_request: APIKeyRotateRequest,
    ) -> APIKeyResponse:
        """Rotate an API key for a service account.

        Args:
            service_account_id: The ID of the service account for which to
                rotate the API key.
            api_key_name_or_id: The name or ID of the API key to rotate.
            rotate_request: The rotate request on the API key.

        Returns:
            The updated API key.

        Raises:
            KeyError: if an API key with the given name or ID is not configured
                for the given service account.
        """

    @abstractmethod
    def delete_api_key(
        self,
        service_account_id: UUID,
        api_key_name_or_id: Union[str, UUID],
    ) -> None:
        """Delete an API key for a service account.

        Args:
            service_account_id: The ID of the service account for which to
                delete the API key.
            api_key_name_or_id: The name or ID of the API key to delete.

        Raises:
            KeyError: if an API key with the given name or ID is not configured
                for the given service account.
        """

    # -------------------- Services --------------------

    @abstractmethod
    def create_service(
        self,
        service: ServiceRequest,
    ) -> ServiceResponse:
        """Create a new service.

        Args:
            service: The service to create.

        Returns:
            The newly created service.

        Raises:
            EntityExistsError: If a service with the same name already exists.
        """

    @abstractmethod
    def get_service(
        self, service_id: UUID, hydrate: bool = True
    ) -> ServiceResponse:
        """Get a service by ID.

        Args:
            service_id: The ID of the service to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The service.

        Raises:
            KeyError: if the service doesn't exist.
        """

    @abstractmethod
    def list_services(
        self, filter_model: ServiceFilter, hydrate: bool = False
    ) -> Page[ServiceResponse]:
        """List all services matching the given filter criteria.

        Args:
            filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all services matching the filter criteria.
        """

    @abstractmethod
    def update_service(
        self, service_id: UUID, update: ServiceUpdate
    ) -> ServiceResponse:
        """Update an existing service.

        Args:
            service_id: The ID of the service to update.
            update: The update to be applied to the service.

        Returns:
            The updated service.

        Raises:
            KeyError: if the service doesn't exist.
        """

    @abstractmethod
    def delete_service(self, service_id: UUID) -> None:
        """Delete a service.

        Args:
            service_id: The ID of the service to delete.

        Raises:
            KeyError: if the service doesn't exist.
        """

    # -------------------- Artifacts --------------------

    @abstractmethod
    def create_artifact(self, artifact: ArtifactRequest) -> ArtifactResponse:
        """Creates a new artifact.

        Args:
            artifact: The artifact to create.

        Returns:
            The newly created artifact.

        Raises:
            EntityExistsError: If an artifact with the same name already exists.
        """

    @abstractmethod
    def get_artifact(
        self, artifact_id: UUID, hydrate: bool = True
    ) -> ArtifactResponse:
        """Gets an artifact.

        Args:
            artifact_id: The ID of the artifact to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The artifact.

        Raises:
            KeyError: if the artifact doesn't exist.
        """

    @abstractmethod
    def list_artifacts(
        self, filter_model: ArtifactFilter, hydrate: bool = False
    ) -> Page[ArtifactResponse]:
        """List all artifacts matching the given filter criteria.

        Args:
            filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all artifacts matching the filter criteria.
        """

    @abstractmethod
    def update_artifact(
        self, artifact_id: UUID, artifact_update: ArtifactUpdate
    ) -> ArtifactResponse:
        """Updates an artifact.

        Args:
            artifact_id: The ID of the artifact to update.
            artifact_update: The update to be applied to the artifact.

        Returns:
            The updated artifact.

        Raises:
            KeyError: if the artifact doesn't exist.
        """

    @abstractmethod
    def delete_artifact(self, artifact_id: UUID) -> None:
        """Deletes an artifact.

        Args:
            artifact_id: The ID of the artifact to delete.

        Raises:
            KeyError: if the artifact doesn't exist.
        """

    # -------------------- Artifact Versions --------------------

    @abstractmethod
    def create_artifact_version(
        self, artifact_version: ArtifactVersionRequest
    ) -> ArtifactVersionResponse:
        """Creates an artifact version.

        Args:
            artifact_version: The artifact version to create.

        Returns:
            The created artifact version.
        """

    @abstractmethod
    def batch_create_artifact_versions(
        self, artifact_versions: List[ArtifactVersionRequest]
    ) -> List[ArtifactVersionResponse]:
        """Creates a batch of artifact versions.

        Args:
            artifact_versions: The artifact versions to create.

        Returns:
            The created artifact versions.
        """

    @abstractmethod
    def get_artifact_version(
        self, artifact_version_id: UUID, hydrate: bool = True
    ) -> ArtifactVersionResponse:
        """Gets an artifact version.

        Args:
            artifact_version_id: The ID of the artifact version to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The artifact version.

        Raises:
            KeyError: if the artifact version doesn't exist.
        """

    @abstractmethod
    def list_artifact_versions(
        self,
        artifact_version_filter_model: ArtifactVersionFilter,
        hydrate: bool = False,
    ) -> Page[ArtifactVersionResponse]:
        """List all artifact versions matching the given filter criteria.

        Args:
            artifact_version_filter_model: All filter parameters including
                pagination params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all artifact versions matching the filter criteria.
        """

    @abstractmethod
    def update_artifact_version(
        self,
        artifact_version_id: UUID,
        artifact_version_update: ArtifactVersionUpdate,
    ) -> ArtifactVersionResponse:
        """Updates an artifact version.

        Args:
            artifact_version_id: The ID of the artifact version to update.
            artifact_version_update: The update to be applied to the artifact
                version.

        Returns:
            The updated artifact version.

        Raises:
            KeyError: if the artifact version doesn't exist.
        """

    @abstractmethod
    def delete_artifact_version(self, artifact_version_id: UUID) -> None:
        """Deletes an artifact version.

        Args:
            artifact_version_id: The ID of the artifact version to delete.

        Raises:
            KeyError: if the artifact version doesn't exist.
        """

    @abstractmethod
    def prune_artifact_versions(
        self,
        project_name_or_id: Union[str, UUID],
        only_versions: bool = True,
    ) -> None:
        """Prunes unused artifact versions and their artifacts.

        Args:
            project_name_or_id: The project name or ID to prune artifact
                versions for.
            only_versions: Only delete artifact versions, keeping artifacts
        """

    # -------------------- Artifact Visualization --------------------

    @abstractmethod
    def get_artifact_visualization(
        self, artifact_visualization_id: UUID, hydrate: bool = True
    ) -> ArtifactVisualizationResponse:
        """Gets an artifact visualization.

        Args:
            artifact_visualization_id: The ID of the artifact visualization
                to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The artifact visualization.

        Raises:
            KeyError: if the artifact visualization doesn't exist.
        """

    # -------------------- Code References --------------------

    @abstractmethod
    def get_code_reference(
        self, code_reference_id: UUID, hydrate: bool = True
    ) -> CodeReferenceResponse:
        """Gets a specific code reference.

        Args:
            code_reference_id: The ID of the code reference to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The requested code reference, if it was found.

        Raises:
            KeyError: If no code reference with the given ID exists.
        """

    # -------------------- Code repositories --------------------

    @abstractmethod
    def create_code_repository(
        self, code_repository: CodeRepositoryRequest
    ) -> CodeRepositoryResponse:
        """Creates a new code repository.

        Args:
            code_repository: Code repository to be created.

        Returns:
            The newly created code repository.

        Raises:
            EntityExistsError: If a code repository with the given name already
                exists.
        """

    @abstractmethod
    def get_code_repository(
        self, code_repository_id: UUID, hydrate: bool = True
    ) -> CodeRepositoryResponse:
        """Gets a specific code repository.

        Args:
            code_repository_id: The ID of the code repository to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The requested code repository, if it was found.

        Raises:
            KeyError: If no code repository with the given ID exists.
        """

    @abstractmethod
    def list_code_repositories(
        self, filter_model: CodeRepositoryFilter, hydrate: bool = False
    ) -> Page[CodeRepositoryResponse]:
        """List all code repositories.

        Args:
            filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all code repositories.
        """

    @abstractmethod
    def update_code_repository(
        self, code_repository_id: UUID, update: CodeRepositoryUpdate
    ) -> CodeRepositoryResponse:
        """Updates an existing code repository.

        Args:
            code_repository_id: The ID of the code repository to update.
            update: The update to be applied to the code repository.

        Returns:
            The updated code repository.

        Raises:
            KeyError: If no code repository with the given name exists.
        """

    @abstractmethod
    def delete_code_repository(self, code_repository_id: UUID) -> None:
        """Deletes a code repository.

        Args:
            code_repository_id: The ID of the code repository to delete.

        Raises:
            KeyError: If no code repository with the given ID exists.
        """

    # -------------------- Components --------------------

    @abstractmethod
    def create_stack_component(
        self, component: ComponentRequest
    ) -> ComponentResponse:
        """Create a stack component.

        Args:
            component: The stack component to create.

        Returns:
            The created stack component.

        Raises:
            EntityExistsError: If a stack component with the same name
                and type already exists.
        """

    @abstractmethod
    def get_stack_component(
        self,
        component_id: UUID,
        hydrate: bool = True,
    ) -> ComponentResponse:
        """Get a stack component by ID.

        Args:
            component_id: The ID of the stack component to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The stack component.

        Raises:
            KeyError: if the stack component doesn't exist.
        """

    @abstractmethod
    def list_stack_components(
        self,
        component_filter_model: ComponentFilter,
        hydrate: bool = False,
    ) -> Page[ComponentResponse]:
        """List all stack components matching the given filter criteria.

        Args:
            component_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all stack components matching the filter criteria.
        """

    @abstractmethod
    def update_stack_component(
        self,
        component_id: UUID,
        component_update: ComponentUpdate,
    ) -> ComponentResponse:
        """Update an existing stack component.

        Args:
            component_id: The ID of the stack component to update.
            component_update: The update to be applied to the stack component.

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
            ValueError: if the stack component is part of one or more stacks.
        """

    # -------------------- Devices --------------------

    @abstractmethod
    def get_authorized_device(
        self, device_id: UUID, hydrate: bool = True
    ) -> OAuthDeviceResponse:
        """Gets a specific OAuth 2.0 authorized device.

        Args:
            device_id: The ID of the device to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The requested device, if it was found.

        Raises:
            KeyError: If no device with the given ID exists.
        """

    @abstractmethod
    def list_authorized_devices(
        self, filter_model: OAuthDeviceFilter, hydrate: bool = False
    ) -> Page[OAuthDeviceResponse]:
        """List all OAuth 2.0 authorized devices for a user.

        Args:
            filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all matching OAuth 2.0 authorized devices.
        """

    @abstractmethod
    def update_authorized_device(
        self, device_id: UUID, update: OAuthDeviceUpdate
    ) -> OAuthDeviceResponse:
        """Updates an existing OAuth 2.0 authorized device for internal use.

        Args:
            device_id: The ID of the device to update.
            update: The update to be applied to the device.

        Returns:
            The updated OAuth 2.0 authorized device.

        Raises:
            KeyError: If no device with the given ID exists.
        """

    @abstractmethod
    def delete_authorized_device(self, device_id: UUID) -> None:
        """Deletes an OAuth 2.0 authorized device.

        Args:
            device_id: The ID of the device to delete.

        Raises:
            KeyError: If no device with the given ID exists.
        """

    # -------------------- Flavors --------------------

    @abstractmethod
    def create_flavor(
        self,
        flavor: FlavorRequest,
    ) -> FlavorResponse:
        """Creates a new stack component flavor.

        Args:
            flavor: The stack component flavor to create.

        Returns:
            The newly created flavor.

        Raises:
            EntityExistsError: If a flavor with the same name and type
                already exists.
        """

    @abstractmethod
    def get_flavor(
        self, flavor_id: UUID, hydrate: bool = True
    ) -> FlavorResponse:
        """Get a stack component flavor by ID.

        Args:
            flavor_id: The ID of the flavor to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The stack component flavor.

        Raises:
            KeyError: if the stack component flavor doesn't exist.
        """

    @abstractmethod
    def update_flavor(
        self, flavor_id: UUID, flavor_update: FlavorUpdate
    ) -> FlavorResponse:
        """Updates an existing user.

        Args:
            flavor_id: The id of the flavor to update.
            flavor_update: The update to be applied to the flavor.

        Returns:
            The updated flavor.
        """

    @abstractmethod
    def list_flavors(
        self,
        flavor_filter_model: FlavorFilter,
        hydrate: bool = False,
    ) -> Page[FlavorResponse]:
        """List all stack component flavors matching the given filter criteria.

        Args:
            flavor_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            List of all the stack component flavors matching the given criteria.
        """

    @abstractmethod
    def delete_flavor(self, flavor_id: UUID) -> None:
        """Delete a stack component flavor.

        Args:
            flavor_id: The ID of the stack component flavor to delete.

        Raises:
            KeyError: if the stack component flavor doesn't exist.
        """

    # -------------------- Logs --------------------
    @abstractmethod
    def get_logs(self, logs_id: UUID, hydrate: bool = True) -> LogsResponse:
        """Get logs by its unique ID.

        Args:
            logs_id: The ID of the logs to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The logs with the given ID.

        Raises:
            KeyError: if the logs doesn't exist.
        """

    # -------------------- Pipelines --------------------

    @abstractmethod
    def create_pipeline(
        self,
        pipeline: PipelineRequest,
    ) -> PipelineResponse:
        """Creates a new pipeline.

        Args:
            pipeline: The pipeline to create.

        Returns:
            The newly created pipeline.

        Raises:
            EntityExistsError: If an identical pipeline already exists.
        """

    @abstractmethod
    def get_pipeline(
        self, pipeline_id: UUID, hydrate: bool = True
    ) -> PipelineResponse:
        """Get a pipeline with a given ID.

        Args:
            pipeline_id: ID of the pipeline.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The pipeline.

        Raises:
            KeyError: if the pipeline does not exist.
        """

    @abstractmethod
    def list_pipelines(
        self,
        pipeline_filter_model: PipelineFilter,
        hydrate: bool = False,
    ) -> Page[PipelineResponse]:
        """List all pipelines matching the given filter criteria.

        Args:
            pipeline_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all pipelines matching the filter criteria.
        """

    @abstractmethod
    def update_pipeline(
        self,
        pipeline_id: UUID,
        pipeline_update: PipelineUpdate,
    ) -> PipelineResponse:
        """Updates a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to be updated.
            pipeline_update: The update to be applied.

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

    # -------------------- Pipeline builds --------------------

    @abstractmethod
    def create_build(
        self,
        build: PipelineBuildRequest,
    ) -> PipelineBuildResponse:
        """Creates a new build.

        Args:
            build: The build to create.

        Returns:
            The newly created build.

        Raises:
            EntityExistsError: If an identical build already exists.
        """

    @abstractmethod
    def get_build(
        self, build_id: UUID, hydrate: bool = True
    ) -> PipelineBuildResponse:
        """Get a build with a given ID.

        Args:
            build_id: ID of the build.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The build.

        Raises:
            KeyError: If the build does not exist.
        """

    @abstractmethod
    def list_builds(
        self,
        build_filter_model: PipelineBuildFilter,
        hydrate: bool = False,
    ) -> Page[PipelineBuildResponse]:
        """List all builds matching the given filter criteria.

        Args:
            build_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all builds matching the filter criteria.
        """

    @abstractmethod
    def delete_build(self, build_id: UUID) -> None:
        """Deletes a build.

        Args:
            build_id: The ID of the build to delete.

        Raises:
            KeyError: if the build doesn't exist.
        """

    # -------------------- Pipeline deployments --------------------

    @abstractmethod
    def create_deployment(
        self,
        deployment: PipelineDeploymentRequest,
    ) -> PipelineDeploymentResponse:
        """Creates a new deployment.

        Args:
            deployment: The deployment to create.

        Returns:
            The newly created deployment.

        Raises:
            EntityExistsError: If an identical deployment already exists.
        """

    @abstractmethod
    def get_deployment(
        self, deployment_id: UUID, hydrate: bool = True
    ) -> PipelineDeploymentResponse:
        """Get a deployment with a given ID.

        Args:
            deployment_id: ID of the deployment.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The deployment.

        Raises:
            KeyError: If the deployment does not exist.
        """

    @abstractmethod
    def list_deployments(
        self,
        deployment_filter_model: PipelineDeploymentFilter,
        hydrate: bool = False,
    ) -> Page[PipelineDeploymentResponse]:
        """List all deployments matching the given filter criteria.

        Args:
            deployment_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all deployments matching the filter criteria.
        """

    @abstractmethod
    def delete_deployment(self, deployment_id: UUID) -> None:
        """Deletes a deployment.

        Args:
            deployment_id: The ID of the deployment to delete.

        Raises:
            KeyError: If the deployment doesn't exist.
        """

    # -------------------- Run templates --------------------

    @abstractmethod
    def create_run_template(
        self,
        template: RunTemplateRequest,
    ) -> RunTemplateResponse:
        """Create a new run template.

        Args:
            template: The template to create.

        Returns:
            The newly created template.

        Raises:
            EntityExistsError: If a template with the same name already exists.
        """

    @abstractmethod
    def get_run_template(
        self, template_id: UUID, hydrate: bool = True
    ) -> RunTemplateResponse:
        """Get a run template with a given ID.

        Args:
            template_id: ID of the template.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The template.

        Raises:
            KeyError: If the template does not exist.
        """

    @abstractmethod
    def list_run_templates(
        self,
        template_filter_model: RunTemplateFilter,
        hydrate: bool = False,
    ) -> Page[RunTemplateResponse]:
        """List all run templates matching the given filter criteria.

        Args:
            template_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all templates matching the filter criteria.
        """

    @abstractmethod
    def update_run_template(
        self,
        template_id: UUID,
        template_update: RunTemplateUpdate,
    ) -> RunTemplateResponse:
        """Updates a run template.

        Args:
            template_id: The ID of the template to update.
            template_update: The update to apply.

        Returns:
            The updated template.

        Raises:
            KeyError: If the template does not exist.
        """

    @abstractmethod
    def delete_run_template(self, template_id: UUID) -> None:
        """Delete a run template.

        Args:
            template_id: The ID of the template to delete.

        Raises:
            KeyError: If the template does not exist.
        """

    @abstractmethod
    def run_template(
        self,
        template_id: UUID,
        run_configuration: Optional[PipelineRunConfiguration] = None,
    ) -> PipelineRunResponse:
        """Run a template.

        Args:
            template_id: The ID of the template to run.
            run_configuration: Configuration for the run.

        Returns:
            Model of the pipeline run.
        """

    # -------------------- Event Sources  --------------------

    @abstractmethod
    def create_event_source(
        self, event_source: EventSourceRequest
    ) -> EventSourceResponse:
        """Create an event_source.

        Args:
            event_source: The event_source to create.

        Returns:
            The created event_source.
        """

    @abstractmethod
    def get_event_source(
        self,
        event_source_id: UUID,
        hydrate: bool = True,
    ) -> EventSourceResponse:
        """Get an event_source by ID.

        Args:
            event_source_id: The ID of the event_source to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The event_source.

        Raises:
            KeyError: if the stack event_source doesn't exist.
        """

    @abstractmethod
    def list_event_sources(
        self,
        event_source_filter_model: EventSourceFilter,
        hydrate: bool = False,
    ) -> Page[EventSourceResponse]:
        """List all event_sources matching the given filter criteria.

        Args:
            event_source_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all event_sources matching the filter criteria.
        """

    @abstractmethod
    def update_event_source(
        self,
        event_source_id: UUID,
        event_source_update: EventSourceUpdate,
    ) -> EventSourceResponse:
        """Update an existing event_source.

        Args:
            event_source_id: The ID of the event_source to update.
            event_source_update: The update to be applied to the event_source.

        Returns:
            The updated event_source.

        Raises:
            KeyError: if the event_source doesn't exist.
        """

    @abstractmethod
    def delete_event_source(self, event_source_id: UUID) -> None:
        """Delete an event_source.

        Args:
            event_source_id: The ID of the event_source to delete.

        Raises:
            KeyError: if the event_source doesn't exist.
        """

    # -------------------- Pipeline runs --------------------

    @abstractmethod
    def get_or_create_run(
        self, pipeline_run: PipelineRunRequest
    ) -> Tuple[PipelineRunResponse, bool]:
        """Gets or creates a pipeline run.

        If a run with the same ID or name already exists, it is returned.
        Otherwise, a new run is created.

        Args:
            pipeline_run: The pipeline run to get or create.

        Returns:
            The pipeline run, and a boolean indicating whether the run was
            created or not.
        """

    @abstractmethod
    def get_run(
        self, run_id: UUID, hydrate: bool = True
    ) -> PipelineRunResponse:
        """Gets a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """

    @abstractmethod
    def list_runs(
        self,
        runs_filter_model: PipelineRunFilter,
        hydrate: bool = False,
    ) -> Page[PipelineRunResponse]:
        """List all pipeline runs matching the given filter criteria.

        Args:
            runs_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all pipeline runs matching the filter criteria.
        """

    @abstractmethod
    def update_run(
        self, run_id: UUID, run_update: PipelineRunUpdate
    ) -> PipelineRunResponse:
        """Updates a pipeline run.

        Args:
            run_id: The ID of the pipeline run to update.
            run_update: The update to be applied to the pipeline run.

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

    # -------------------- Run metadata --------------------

    @abstractmethod
    def create_run_metadata(self, run_metadata: RunMetadataRequest) -> None:
        """Creates run metadata.

        Args:
            run_metadata: The run metadata to create.

        Returns:
            None
        """

    # -------------------- Schedules --------------------

    @abstractmethod
    def create_schedule(self, schedule: ScheduleRequest) -> ScheduleResponse:
        """Creates a new schedule.

        Args:
            schedule: The schedule to create.

        Returns:
            The newly created schedule.
        """

    @abstractmethod
    def get_schedule(
        self, schedule_id: UUID, hydrate: bool = True
    ) -> ScheduleResponse:
        """Get a schedule with a given ID.

        Args:
            schedule_id: ID of the schedule.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The schedule.

        Raises:
            KeyError: if the schedule does not exist.
        """

    @abstractmethod
    def list_schedules(
        self,
        schedule_filter_model: ScheduleFilter,
        hydrate: bool = False,
    ) -> Page[ScheduleResponse]:
        """List all schedules.

        Args:
            schedule_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of schedules.
        """

    @abstractmethod
    def update_schedule(
        self,
        schedule_id: UUID,
        schedule_update: ScheduleUpdate,
    ) -> ScheduleResponse:
        """Updates a schedule.

        Args:
            schedule_id: The ID of the schedule to be updated.
            schedule_update: The update to be applied.

        Returns:
            The updated schedule.

        Raises:
            KeyError: if the schedule doesn't exist.
        """

    @abstractmethod
    def delete_schedule(self, schedule_id: UUID) -> None:
        """Deletes a schedule.

        Args:
            schedule_id: The ID of the schedule to delete.

        Raises:
            KeyError: if the schedule doesn't exist.
        """

    # --------------------  Secrets --------------------

    @abstractmethod
    def create_secret(
        self,
        secret: SecretRequest,
    ) -> SecretResponse:
        """Creates a new secret.

        The new secret is also validated against the scoping rules enforced in
        the secrets store:

          - only one private secret with the given name can exist.
          - only one public secret with the given name can exist.

        Args:
            secret: The secret to create.

        Returns:
            The newly created secret.

        Raises:
            KeyError: if the user does not exist.
            EntityExistsError: If a secret with the same name already exists in
                the same scope.
        """

    @abstractmethod
    def get_secret(
        self, secret_id: UUID, hydrate: bool = True
    ) -> SecretResponse:
        """Get a secret with a given name.

        Args:
            secret_id: ID of the secret.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The secret.

        Raises:
            KeyError: if the secret does not exist.
        """

    @abstractmethod
    def list_secrets(
        self, secret_filter_model: SecretFilter, hydrate: bool = False
    ) -> Page[SecretResponse]:
        """List all secrets matching the given filter criteria.

        Note that returned secrets do not include any secret values. To fetch
        the secret values, use `get_secret`.

        Args:
            secret_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all secrets matching the filter criteria, with pagination
            information and sorted according to the filter criteria. The
            returned secrets do not include any secret values, only metadata. To
            fetch the secret values, use `get_secret` individually with each
            secret.
        """

    @abstractmethod
    def update_secret(
        self,
        secret_id: UUID,
        secret_update: SecretUpdate,
    ) -> SecretResponse:
        """Updates a secret.

        Secret values that are specified as `None` in the update that are
        present in the existing secret are removed from the existing secret.
        Values that are present in both secrets are overwritten. All other
        values in both the existing secret and the update are kept (merged).

        If the update includes a change of name or scope, the scoping rules
        enforced in the secrets store are used to validate the update:

          - only one private secret with the given name can exist.
          - only one public secret with the given name can exist.

        Args:
            secret_id: The ID of the secret to be updated.
            secret_update: The update to be applied.

        Returns:
            The updated secret.

        Raises:
            KeyError: if the secret doesn't exist.
            EntityExistsError: If a secret with the same name already exists in
                the same scope.
        """

    @abstractmethod
    def delete_secret(self, secret_id: UUID) -> None:
        """Deletes a secret.

        Args:
            secret_id: The ID of the secret to delete.

        Raises:
            KeyError: if the secret doesn't exist.
        """

    @abstractmethod
    def backup_secrets(
        self, ignore_errors: bool = True, delete_secrets: bool = False
    ) -> None:
        """Backs up all secrets to the configured backup secrets store.

        Args:
            ignore_errors: Whether to ignore individual errors during the backup
                process and attempt to backup all secrets.
            delete_secrets: Whether to delete the secrets that have been
                successfully backed up from the primary secrets store. Setting
                this flag effectively moves all secrets from the primary secrets
                store to the backup secrets store.

        Raises:
            BackupSecretsStoreNotConfiguredError: if no backup secrets store is
                configured.
        """

    @abstractmethod
    def restore_secrets(
        self, ignore_errors: bool = False, delete_secrets: bool = False
    ) -> None:
        """Restore all secrets from the configured backup secrets store.

        Args:
            ignore_errors: Whether to ignore individual errors during the
                restore process and attempt to restore all secrets.
            delete_secrets: Whether to delete the secrets that have been
                successfully restored from the backup secrets store. Setting
                this flag effectively moves all secrets from the backup secrets
                store to the primary secrets store.

        Raises:
            BackupSecretsStoreNotConfiguredError: if no backup secrets store is
                configured.
        """

    # --------------------  Service Accounts --------------------

    @abstractmethod
    def create_service_account(
        self, service_account: ServiceAccountRequest
    ) -> ServiceAccountResponse:
        """Creates a new service account.

        Args:
            service_account: Service account to be created.

        Returns:
            The newly created service account.

        Raises:
            EntityExistsError: If a user or service account with the given name
                already exists.
        """

    @abstractmethod
    def get_service_account(
        self,
        service_account_name_or_id: Union[str, UUID],
        hydrate: bool = True,
    ) -> ServiceAccountResponse:
        """Gets a specific service account.

        Args:
            service_account_name_or_id: The name or ID of the service account to
                get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The requested service account, if it was found.

        Raises:
            KeyError: If no service account with the given name or ID exists.
        """

    @abstractmethod
    def list_service_accounts(
        self,
        filter_model: ServiceAccountFilter,
        hydrate: bool = False,
    ) -> Page[ServiceAccountResponse]:
        """List all service accounts.

        Args:
            filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of filtered service accounts.
        """

    @abstractmethod
    def update_service_account(
        self,
        service_account_name_or_id: Union[str, UUID],
        service_account_update: ServiceAccountUpdate,
    ) -> ServiceAccountResponse:
        """Updates an existing service account.

        Args:
            service_account_name_or_id: The name or the ID of the service
                account to update.
            service_account_update: The update to be applied to the service
                account.

        Returns:
            The updated service account.

        Raises:
            KeyError: If no service account with the given name exists.
        """

    @abstractmethod
    def delete_service_account(
        self,
        service_account_name_or_id: Union[str, UUID],
    ) -> None:
        """Delete a service account.

        Args:
            service_account_name_or_id: The name or the ID of the service
                account to delete.

        Raises:
            IllegalOperationError: if the service account has already been used
                to create other resources.
        """

    # -------------------- Service Connectors --------------------

    @abstractmethod
    def create_service_connector(
        self,
        service_connector: ServiceConnectorRequest,
    ) -> ServiceConnectorResponse:
        """Creates a new service connector.

        Args:
            service_connector: Service connector to be created.

        Returns:
            The newly created service connector.

        Raises:
            EntityExistsError: If a service connector with the given name
                already exists.
        """

    @abstractmethod
    def get_service_connector(
        self, service_connector_id: UUID, hydrate: bool = True
    ) -> ServiceConnectorResponse:
        """Gets a specific service connector.

        Args:
            service_connector_id: The ID of the service connector to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The requested service connector, if it was found.

        Raises:
            KeyError: If no service connector with the given ID exists.
        """

    @abstractmethod
    def list_service_connectors(
        self,
        filter_model: ServiceConnectorFilter,
        hydrate: bool = False,
    ) -> Page[ServiceConnectorResponse]:
        """List all service connectors.

        Args:
            filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all service connectors.
        """

    @abstractmethod
    def update_service_connector(
        self, service_connector_id: UUID, update: ServiceConnectorUpdate
    ) -> ServiceConnectorResponse:
        """Updates an existing service connector.

        The update model contains the fields to be updated. If a field value is
        set to None in the model, the field is not updated, but there are
        special rules concerning some fields:

        * the `configuration` and `secrets` fields together represent a full
        valid configuration update, not just a partial update. If either is
        set (i.e. not None) in the update, their values are merged together and
        will replace the existing configuration and secrets values.
        * the `resource_id` field value is also a full replacement value: if set
        to `None`, the resource ID is removed from the service connector.
        * the `expiration_seconds` field value is also a full replacement value:
        if set to `None`, the expiration is removed from the service connector.
        * the `secret_id` field value in the update is ignored, given that
        secrets are managed internally by the ZenML store.
        * the `labels` field is also a full labels update: if set (i.e. not
        `None`), all existing labels are removed and replaced by the new labels
        in the update.

        Args:
            service_connector_id: The ID of the service connector to update.
            update: The update to be applied to the service connector.

        Returns:
            The updated service connector.

        Raises:
            KeyError: If no service connector with the given name exists.
        """

    @abstractmethod
    def delete_service_connector(self, service_connector_id: UUID) -> None:
        """Deletes a service connector.

        Args:
            service_connector_id: The ID of the service connector to delete.

        Raises:
            KeyError: If no service connector with the given ID exists.
        """

    @abstractmethod
    def verify_service_connector_config(
        self,
        service_connector: ServiceConnectorRequest,
        list_resources: bool = True,
    ) -> ServiceConnectorResourcesModel:
        """Verifies if a service connector configuration has access to resources.

        Args:
            service_connector: The service connector configuration to verify.
            list_resources: If True, the list of all resources accessible
                through the service connector is returned.

        Returns:
            The list of resources that the service connector configuration has
            access to.

        Raises:
            NotImplementError: If the service connector cannot be verified
                on the store e.g. due to missing package dependencies.
        """

    @abstractmethod
    def verify_service_connector(
        self,
        service_connector_id: UUID,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        list_resources: bool = True,
    ) -> ServiceConnectorResourcesModel:
        """Verifies if a service connector instance has access to one or more resources.

        Args:
            service_connector_id: The ID of the service connector to verify.
            resource_type: The type of resource to verify access to.
            resource_id: The ID of the resource to verify access to.
            list_resources: If True, the list of all resources accessible
                through the service connector and matching the supplied resource
                type and ID are returned.

        Returns:
            The list of resources that the service connector has access to,
            scoped to the supplied resource type and ID, if provided.

        Raises:
            KeyError: If no service connector with the given name exists.
            NotImplementError: If the service connector cannot be verified
                e.g. due to missing package dependencies.
        """

    @abstractmethod
    def get_service_connector_client(
        self,
        service_connector_id: UUID,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> ServiceConnectorResponse:
        """Get a service connector client for a service connector and given resource.

        Args:
            service_connector_id: The ID of the base service connector to use.
            resource_type: The type of resource to get a client for.
            resource_id: The ID of the resource to get a client for.

        Returns:
            A service connector client that can be used to access the given
            resource.

        Raises:
            KeyError: If no service connector with the given name exists.
            NotImplementError: If the service connector cannot be instantiated
                on the store e.g. due to missing package dependencies.
        """

    @abstractmethod
    def list_service_connector_resources(
        self,
        filter_model: ServiceConnectorFilter,
    ) -> List[ServiceConnectorResourcesModel]:
        """List resources that can be accessed by service connectors.

        Args:
            filter_model: The filter model to use when fetching service
                connectors.

        Returns:
            The matching list of resources that available service
            connectors have access to.
        """

    @abstractmethod
    def list_service_connector_types(
        self,
        connector_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        auth_method: Optional[str] = None,
    ) -> List[ServiceConnectorTypeModel]:
        """Get a list of service connector types.

        Args:
            connector_type: Filter by connector type.
            resource_type: Filter by resource type.
            auth_method: Filter by authentication method.

        Returns:
            List of service connector types.
        """

    @abstractmethod
    def get_service_connector_type(
        self,
        connector_type: str,
    ) -> ServiceConnectorTypeModel:
        """Returns the requested service connector type.

        Args:
            connector_type: the service connector type identifier.

        Returns:
            The requested service connector type.

        Raises:
            KeyError: If no service connector type with the given ID exists.
        """

    # -------------------- Stacks --------------------

    @abstractmethod
    def create_stack(self, stack: StackRequest) -> StackResponse:
        """Create a new stack.

        Args:
            stack: The stack to create.

        Returns:
            The created stack.

        Raises:
            EntityExistsError: If a stack, stack component or service connector
                with the same name already exists.
        """

    @abstractmethod
    def get_stack(self, stack_id: UUID, hydrate: bool = True) -> StackResponse:
        """Get a stack by its unique ID.

        Args:
            stack_id: The ID of the stack to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The stack with the given ID.

        Raises:
            KeyError: if the stack doesn't exist.
        """

    @abstractmethod
    def list_stacks(
        self,
        stack_filter_model: StackFilter,
        hydrate: bool = False,
    ) -> Page[StackResponse]:
        """List all stacks matching the given filter criteria.

        Args:
            stack_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all stacks matching the filter criteria.
        """

    @abstractmethod
    def update_stack(
        self, stack_id: UUID, stack_update: StackUpdate
    ) -> StackResponse:
        """Update a stack.

        Args:
            stack_id: The ID of the stack update.
            stack_update: The update request on the stack.

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

    # ---------------- Stack deployments-----------------

    @abstractmethod
    def get_stack_deployment_info(
        self,
        provider: StackDeploymentProvider,
    ) -> StackDeploymentInfo:
        """Get information about a stack deployment provider.

        Args:
            provider: The stack deployment provider.

        Returns:
            Information about the stack deployment provider.
        """

    @abstractmethod
    def get_stack_deployment_config(
        self,
        provider: StackDeploymentProvider,
        stack_name: str,
        location: Optional[str] = None,
    ) -> StackDeploymentConfig:
        """Return the cloud provider console URL and configuration needed to deploy the ZenML stack.

        Args:
            provider: The stack deployment provider.
            stack_name: The name of the stack.
            location: The location where the stack should be deployed.

        Returns:
            The cloud provider console URL and configuration needed to deploy
            the ZenML stack to the specified cloud provider.
        """

    @abstractmethod
    def get_stack_deployment_stack(
        self,
        provider: StackDeploymentProvider,
        stack_name: str,
        location: Optional[str] = None,
        date_start: Optional[datetime.datetime] = None,
    ) -> Optional[DeployedStack]:
        """Return a matching ZenML stack that was deployed and registered.

        Args:
            provider: The stack deployment provider.
            stack_name: The name of the stack.
            location: The location where the stack should be deployed.
            date_start: The date when the deployment started.

        Returns:
            The ZenML stack that was deployed and registered or None if the
            stack was not found.
        """

    # -------------------- Step runs --------------------

    @abstractmethod
    def create_run_step(self, step_run: StepRunRequest) -> StepRunResponse:
        """Creates a step run.

        Args:
            step_run: The step run to create.

        Returns:
            The created step run.

        Raises:
            EntityExistsError: if the step run already exists.
            KeyError: if the pipeline run doesn't exist.
        """

    @abstractmethod
    def get_run_step(
        self, step_run_id: UUID, hydrate: bool = True
    ) -> StepRunResponse:
        """Get a step run by ID.

        Args:
            step_run_id: The ID of the step run to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The step run.

        Raises:
            KeyError: if the step run doesn't exist.
        """

    @abstractmethod
    def list_run_steps(
        self,
        step_run_filter_model: StepRunFilter,
        hydrate: bool = False,
    ) -> Page[StepRunResponse]:
        """List all step runs matching the given filter criteria.

        Args:
            step_run_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all step runs matching the filter criteria.
        """

    @abstractmethod
    def update_run_step(
        self,
        step_run_id: UUID,
        step_run_update: StepRunUpdate,
    ) -> StepRunResponse:
        """Updates a step run.

        Args:
            step_run_id: The ID of the step to update.
            step_run_update: The update to be applied to the step.

        Returns:
            The updated step run.

        Raises:
            KeyError: if the step run doesn't exist.
        """

    # -------------------- Triggers  --------------------

    @abstractmethod
    def create_trigger(self, trigger: TriggerRequest) -> TriggerResponse:
        """Create an trigger.

        Args:
            trigger: The trigger to create.

        Returns:
            The created trigger.
        """

    @abstractmethod
    def get_trigger(
        self,
        trigger_id: UUID,
        hydrate: bool = True,
    ) -> TriggerResponse:
        """Get an trigger by ID.

        Args:
            trigger_id: The ID of the trigger to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The trigger.

        Raises:
            KeyError: if the stack trigger doesn't exist.
        """

    @abstractmethod
    def list_triggers(
        self,
        trigger_filter_model: TriggerFilter,
        hydrate: bool = False,
    ) -> Page[TriggerResponse]:
        """List all triggers matching the given filter criteria.

        Args:
            trigger_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all triggers matching the filter criteria.
        """

    @abstractmethod
    def update_trigger(
        self,
        trigger_id: UUID,
        trigger_update: TriggerUpdate,
    ) -> TriggerResponse:
        """Update an existing trigger.

        Args:
            trigger_id: The ID of the trigger to update.
            trigger_update: The update to be applied to the trigger.

        Returns:
            The updated trigger.

        Raises:
            KeyError: if the trigger doesn't exist.
        """

    @abstractmethod
    def delete_trigger(self, trigger_id: UUID) -> None:
        """Delete an trigger.

        Args:
            trigger_id: The ID of the trigger to delete.

        Raises:
            KeyError: if the trigger doesn't exist.
        """

    # -------------------- Trigger Executions --------------------

    @abstractmethod
    def get_trigger_execution(
        self,
        trigger_execution_id: UUID,
        hydrate: bool = True,
    ) -> TriggerExecutionResponse:
        """Get a trigger execution by ID.

        Args:
            trigger_execution_id: The ID of the trigger execution to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The trigger execution.

        Raises:
            KeyError: If the trigger execution doesn't exist.
        """

    @abstractmethod
    def list_trigger_executions(
        self,
        trigger_execution_filter_model: TriggerExecutionFilter,
        hydrate: bool = False,
    ) -> Page[TriggerExecutionResponse]:
        """List all trigger executions matching the given filter criteria.

        Args:
            trigger_execution_filter_model: All filter parameters including
                pagination params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all trigger executions matching the filter criteria.
        """

    @abstractmethod
    def delete_trigger_execution(self, trigger_execution_id: UUID) -> None:
        """Delete a trigger execution.

        Args:
            trigger_execution_id: The ID of the trigger execution to delete.

        Raises:
            KeyError: If the trigger execution doesn't exist.
        """

    # -------------------- Users --------------------

    @abstractmethod
    def create_user(self, user: UserRequest) -> UserResponse:
        """Creates a new user.

        Args:
            user: User to be created.

        Returns:
            The newly created user.

        Raises:
            EntityExistsError: If a user with the given name already exists.
        """

    @abstractmethod
    def get_user(
        self,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        include_private: bool = False,
        hydrate: bool = True,
    ) -> UserResponse:
        """Gets a specific user, when no id is specified the active user is returned.

        Args:
            user_name_or_id: The name or ID of the user to get.
            include_private: Whether to include private user information.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The requested user, if it was found.

        Raises:
            KeyError: If no user with the given name or ID exists.
        """

    @abstractmethod
    def list_users(
        self,
        user_filter_model: UserFilter,
        hydrate: bool = False,
    ) -> Page[UserResponse]:
        """List all users.

        Args:
            user_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all users.
        """

    @abstractmethod
    def update_user(
        self, user_id: UUID, user_update: UserUpdate
    ) -> UserResponse:
        """Updates an existing user.

        Args:
            user_id: The id of the user to update.
            user_update: The update to be applied to the user.

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

    # -------------------- Projects --------------------

    @abstractmethod
    def create_project(self, project: ProjectRequest) -> ProjectResponse:
        """Creates a new project.

        Args:
            project: The project to create.

        Returns:
            The newly created project.

        Raises:
            EntityExistsError: If a project with the given name already exists.
        """

    @abstractmethod
    def get_project(
        self, project_name_or_id: Union[UUID, str], hydrate: bool = True
    ) -> ProjectResponse:
        """Get an existing project by name or ID.

        Args:
            project_name_or_id: Name or ID of the project to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The requested project.

        Raises:
            KeyError: If there is no such project.
        """

    @abstractmethod
    def list_projects(
        self,
        project_filter_model: ProjectFilter,
        hydrate: bool = False,
    ) -> Page[ProjectResponse]:
        """List all projects matching the given filter criteria.

        Args:
            project_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all projects matching the filter criteria.
        """

    @abstractmethod
    def update_project(
        self, project_id: UUID, project_update: ProjectUpdate
    ) -> ProjectResponse:
        """Update an existing project.

        Args:
            project_id: The ID of the project to be updated.
            project_update: The update to be applied to the project.

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

    # -------------------- Models --------------------

    @abstractmethod
    def create_model(self, model: ModelRequest) -> ModelResponse:
        """Creates a new model.

        Args:
            model: the Model to be created.

        Returns:
            The newly created model.

        Raises:
            EntityExistsError: If a model with the given name already exists.
        """

    @abstractmethod
    def delete_model(self, model_id: UUID) -> None:
        """Deletes a model.

        Args:
            model_id: id of the model to be deleted.

        Raises:
            KeyError: model with specified ID not found.
        """

    @abstractmethod
    def update_model(
        self,
        model_id: UUID,
        model_update: ModelUpdate,
    ) -> ModelResponse:
        """Updates an existing model.

        Args:
            model_id: UUID of the model to be updated.
            model_update: the Model to be updated.

        Returns:
            The updated model.
        """

    @abstractmethod
    def get_model(self, model_id: UUID, hydrate: bool = True) -> ModelResponse:
        """Get an existing model.

        Args:
            model_id: id of the model to be retrieved.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The model of interest.

        Raises:
            KeyError: model with specified ID not found.
        """

    @abstractmethod
    def list_models(
        self,
        model_filter_model: ModelFilter,
        hydrate: bool = False,
    ) -> Page[ModelResponse]:
        """Get all models by filter.

        Args:
            model_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all models.
        """

    # -------------------- Model versions --------------------

    @abstractmethod
    def create_model_version(
        self, model_version: ModelVersionRequest
    ) -> ModelVersionResponse:
        """Creates a new model version.

        Args:
            model_version: the Model Version to be created.

        Returns:
            The newly created model version.

        Raises:
            ValueError: If `number` is not None during model version creation.
            EntityExistsError: If a model version with the given name already
                exists.
        """

    @abstractmethod
    def delete_model_version(
        self,
        model_version_id: UUID,
    ) -> None:
        """Deletes a model version.

        Args:
            model_version_id: id of the model version to be deleted.

        Raises:
            KeyError: specified ID or name not found.
        """

    @abstractmethod
    def get_model_version(
        self, model_version_id: UUID, hydrate: bool = True
    ) -> ModelVersionResponse:
        """Get an existing model version.

        Args:
            model_version_id: name, id, stage or number of the model version to
                be retrieved. If skipped - latest is retrieved.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.


        Returns:
            The model version of interest.

        Raises:
            KeyError: specified ID or name not found.
        """

    @abstractmethod
    def list_model_versions(
        self,
        model_version_filter_model: ModelVersionFilter,
        hydrate: bool = False,
    ) -> Page[ModelVersionResponse]:
        """Get all model versions by filter.

        Args:
            model_version_filter_model: All filter parameters including
                pagination params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all model versions.
        """

    @abstractmethod
    def update_model_version(
        self,
        model_version_id: UUID,
        model_version_update_model: ModelVersionUpdate,
    ) -> ModelVersionResponse:
        """Get all model versions by filter.

        Args:
            model_version_id: The ID of model version to be updated.
            model_version_update_model: The model version to be updated.

        Returns:
            An updated model version.

        Raises:
            KeyError: If the model version not found
            RuntimeError: If there is a model version with target stage,
                but `force` flag is off
        """

    # -------------------- Model Versions Artifacts --------------------

    @abstractmethod
    def create_model_version_artifact_link(
        self, model_version_artifact_link: ModelVersionArtifactRequest
    ) -> ModelVersionArtifactResponse:
        """Creates a new model version link.

        Args:
            model_version_artifact_link: the Model Version to Artifact Link
                to be created.

        Returns:
            The newly created model version to artifact link.

        Raises:
            EntityExistsError: If a link with the given name already exists.
        """

    @abstractmethod
    def list_model_version_artifact_links(
        self,
        model_version_artifact_link_filter_model: ModelVersionArtifactFilter,
        hydrate: bool = False,
    ) -> Page[ModelVersionArtifactResponse]:
        """Get all model version to artifact links by filter.

        Args:
            model_version_artifact_link_filter_model: All filter parameters
                including pagination params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all model version to artifact links.
        """

    @abstractmethod
    def delete_model_version_artifact_link(
        self,
        model_version_id: UUID,
        model_version_artifact_link_name_or_id: Union[str, UUID],
    ) -> None:
        """Deletes a model version to artifact link.

        Args:
            model_version_id: ID of the model version containing the link.
            model_version_artifact_link_name_or_id: name or ID of the model
                version to artifact link to be deleted.

        Raises:
            KeyError: specified ID or name not found.
        """

    @abstractmethod
    def delete_all_model_version_artifact_links(
        self,
        model_version_id: UUID,
        only_links: bool = True,
    ) -> None:
        """Deletes all model version to artifact links.

        Args:
            model_version_id: ID of the model version containing the link.
            only_links: Flag deciding whether to delete only links or all.
        """

    # -------------------- Model Versions Pipeline Runs --------------------

    @abstractmethod
    def create_model_version_pipeline_run_link(
        self,
        model_version_pipeline_run_link: ModelVersionPipelineRunRequest,
    ) -> ModelVersionPipelineRunResponse:
        """Creates a new model version to pipeline run link.

        Args:
            model_version_pipeline_run_link: the Model Version to Pipeline Run
                Link to be created.

        Returns:
            - If Model Version to Pipeline Run Link already exists - returns
                the existing link.
            - Otherwise, returns the newly created model version to pipeline
                run link.
        """

    @abstractmethod
    def list_model_version_pipeline_run_links(
        self,
        model_version_pipeline_run_link_filter_model: ModelVersionPipelineRunFilter,
        hydrate: bool = False,
    ) -> Page[ModelVersionPipelineRunResponse]:
        """Get all model version to pipeline run links by filter.

        Args:
            model_version_pipeline_run_link_filter_model: All filter parameters
                including pagination params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all model version to pipeline run links.
        """

    @abstractmethod
    def delete_model_version_pipeline_run_link(
        self,
        model_version_id: UUID,
        model_version_pipeline_run_link_name_or_id: Union[str, UUID],
    ) -> None:
        """Deletes a model version to pipeline run link.

        Args:
            model_version_id: ID of the model version containing the link.
            model_version_pipeline_run_link_name_or_id: name or ID of the model
                version to pipeline run link to be deleted.

        Raises:
            KeyError: specified ID not found.
        """

    # -------------------- Tags --------------------

    @abstractmethod
    def create_tag(self, tag: TagRequest) -> TagResponse:
        """Creates a new tag.

        Args:
            tag: the tag to be created.

        Returns:
            The newly created tag.

        Raises:
            EntityExistsError: If a tag with the given name already exists.
        """

    @abstractmethod
    def delete_tag(
        self,
        tag_name_or_id: Union[str, UUID],
    ) -> None:
        """Deletes a tag.

        Args:
            tag_name_or_id: name or id of the tag to delete.

        Raises:
            KeyError: specified ID or name not found.
        """

    @abstractmethod
    def get_tag(
        self,
        tag_name_or_id: Union[str, UUID],
        hydrate: bool = True,
    ) -> TagResponse:
        """Get an existing tag.

        Args:
            tag_name_or_id: name or id of the tag to be retrieved.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The tag of interest.

        Raises:
            KeyError: specified ID or name not found.
        """

    @abstractmethod
    def list_tags(
        self,
        tag_filter_model: TagFilter,
        hydrate: bool = False,
    ) -> Page[TagResponse]:
        """Get all tags by filter.

        Args:
            tag_filter_model: All filter parameters including pagination params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all tags.
        """

    @abstractmethod
    def update_tag(
        self,
        tag_name_or_id: Union[str, UUID],
        tag_update_model: TagUpdate,
    ) -> TagResponse:
        """Update tag.

        Args:
            tag_name_or_id: name or id of the tag to be updated.
            tag_update_model: Tag to use for the update.

        Returns:
            An updated tag.

        Raises:
            KeyError: If the tag is not found
        """

    # -------------------- Tag Resources --------------------

    @abstractmethod
    def create_tag_resource(
        self, tag_resource: TagResourceRequest
    ) -> TagResourceResponse:
        """Create a new tag resource relationship.

        Args:
            tag_resource: The tag resource relationship to be created.

        Returns:
            The newly created tag resource relationship.
        """

    @abstractmethod
    def batch_create_tag_resource(
        self, tag_resources: List[TagResourceRequest]
    ) -> List[TagResourceResponse]:
        """Create a new tag resource relationship.

        Args:
            tag_resources: The tag resource relationships to be created.

        Returns:
            The newly created tag resource relationships.
        """

    @abstractmethod
    def delete_tag_resource(
        self,
        tag_resource: TagResourceRequest,
    ) -> None:
        """Delete a tag resource relationship.

        Args:
            tag_resource: The tag resource relationship to delete.
        """

    @abstractmethod
    def batch_delete_tag_resource(
        self, tag_resources: List[TagResourceRequest]
    ) -> None:
        """Delete a batch of tag resource relationships.

        Args:
            tag_resources: The tag resource relationships to be deleted.
        """
