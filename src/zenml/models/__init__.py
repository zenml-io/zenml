#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Pydantic models for the various concepts in ZenML."""

# ------------------------------------- V2 -------------------------------------

# V2 Base
from zenml.models.v2.base.base import (
    BaseZenModel,
    BaseRequest,
    BaseResponse,
    BaseUpdate,
    BaseIdentifiedResponse,
    BaseResponseBody,
    BaseResponseMetadata,
    BaseResponseResources,
    BaseDatedResponseBody,
)
from zenml.models.v2.base.scoped import (
    UserScopedRequest,
    UserScopedFilter,
    UserScopedResponse,
    UserScopedResponseBody,
    UserScopedResponseMetadata,
    WorkspaceScopedRequest,
    WorkspaceScopedFilter,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
    WorkspaceScopedTaggableFilter,
)
from zenml.models.v2.base.filter import (
    BaseFilter,
    StrFilter,
    BoolFilter,
    NumericFilter,
    UUIDFilter,
)
from zenml.models.v2.base.page import Page

# V2 Core
from zenml.models.v2.core.action import (
    ActionFilter,
    ActionRequest,
    ActionResponse,
    ActionResponseBody,
    ActionResponseMetadata,
    ActionResponseResources,
    ActionUpdate,
)
from zenml.models.v2.core.action_flavor import (
    ActionFlavorResponse,
    ActionFlavorResponseBody,
    ActionFlavorResponseMetadata,
    ActionFlavorResponseResources,
)
from zenml.models.v2.core.api_key import (
    APIKey,
    APIKeyRequest,
    APIKeyUpdate,
    APIKeyFilter,
    APIKeyResponse,
    APIKeyResponseBody,
    APIKeyResponseMetadata,
    APIKeyInternalResponse,
    APIKeyInternalUpdate,
    APIKeyRotateRequest,
)
from zenml.models.v2.core.artifact import (
    ArtifactFilter,
    ArtifactRequest,
    ArtifactResponse,
    ArtifactResponseBody,
    ArtifactResponseMetadata,
    ArtifactUpdate,
)
from zenml.models.v2.core.artifact_version import (
    ArtifactVersionRequest,
    ArtifactVersionFilter,
    ArtifactVersionResponse,
    ArtifactVersionResponseBody,
    ArtifactVersionResponseMetadata,
    ArtifactVersionUpdate,
    LazyArtifactVersionResponse
)
from zenml.models.v2.core.artifact_visualization import (
    ArtifactVisualizationRequest,
    ArtifactVisualizationResponse,
    ArtifactVisualizationResponseBody,
    ArtifactVisualizationResponseMetadata,
)
from zenml.models.v2.core.service import (
    ServiceResponse,
    ServiceResponseBody,
    ServiceResponseMetadata,
    ServiceUpdate,
    ServiceFilter,
    ServiceRequest,
    ServiceResponseResources,
)
from zenml.models.v2.core.code_reference import (
    CodeReferenceRequest,
    CodeReferenceResponse,
    CodeReferenceResponseBody,
    CodeReferenceResponseMetadata,
)
from zenml.models.v2.core.code_repository import (
    CodeRepositoryRequest,
    CodeRepositoryUpdate,
    CodeRepositoryFilter,
    CodeRepositoryResponse,
    CodeRepositoryResponseBody,
    CodeRepositoryResponseMetadata,
)
from zenml.models.v2.core.component import (
    ComponentBase,
    ComponentRequest,
    ComponentUpdate,
    ComponentFilter,
    ComponentResponse,
    ComponentResponseBody,
    ComponentResponseMetadata,
)
from zenml.models.v2.core.event_source_flavor import (
    EventSourceFlavorResponse,
    EventSourceFlavorResponseBody,
    EventSourceFlavorResponseMetadata,
    EventSourceFlavorResponseResources,
)
from zenml.models.v2.core.device import (
    OAuthDeviceUpdate,
    OAuthDeviceFilter,
    OAuthDeviceResponse,
    OAuthDeviceResponseBody,
    OAuthDeviceResponseMetadata,
    OAuthDeviceInternalRequest,
    OAuthDeviceInternalUpdate,
    OAuthDeviceInternalResponse,
)
from zenml.models.v2.core.flavor import (
    FlavorRequest,
    FlavorUpdate,
    FlavorFilter,
    FlavorResponse,
    FlavorResponseBody,
    FlavorResponseMetadata,
)
from zenml.models.v2.core.logs import (
    LogsRequest,
    LogsResponse,
    LogsResponseBody,
    LogsResponseMetadata,
)
from zenml.models.v2.core.model import (
    ModelFilter,
    ModelResponse,
    ModelResponseBody,
    ModelResponseMetadata,
    ModelRequest,
    ModelUpdate,
)
from zenml.models.v2.core.model_version import (
    ModelVersionResponse,
    ModelVersionRequest,
    ModelVersionResponseBody,
    ModelVersionResponseMetadata,
    ModelVersionFilter,
    ModelVersionUpdate,
    ModelVersionResponseResources,
)
from zenml.models.v2.core.model_version_artifact import (
    ModelVersionArtifactFilter,
    ModelVersionArtifactRequest,
    ModelVersionArtifactResponse,
    ModelVersionArtifactResponseBody,
)
from zenml.models.v2.core.model_version_pipeline_run import (
    ModelVersionPipelineRunFilter,
    ModelVersionPipelineRunRequest,
    ModelVersionPipelineRunResponse,
    ModelVersionPipelineRunResponseBody,
)
from zenml.models.v2.core.pipeline import (
    PipelineRequest,
    PipelineUpdate,
    PipelineFilter,
    PipelineResponse,
    PipelineResponseBody,
    PipelineResponseMetadata,
)
from zenml.models.v2.core.pipeline_build import (
    PipelineBuildBase,
    PipelineBuildRequest,
    PipelineBuildFilter,
    PipelineBuildResponse,
    PipelineBuildResponseBody,
    PipelineBuildResponseMetadata,
)
from zenml.models.v2.core.pipeline_deployment import (
    PipelineDeploymentBase,
    PipelineDeploymentRequest,
    PipelineDeploymentFilter,
    PipelineDeploymentResponse,
    PipelineDeploymentResponseBody,
    PipelineDeploymentResponseMetadata,
    PipelineDeploymentResponseResources,
)
from zenml.models.v2.core.pipeline_run import (
    PipelineRunRequest,
    PipelineRunUpdate,
    PipelineRunFilter,
    PipelineRunResponse,
    PipelineRunResponseBody,
    PipelineRunResponseMetadata,
)
from zenml.models.v2.base.base_plugin_flavor import BasePluginFlavorResponse
from zenml.models.v2.core.run_metadata import (
    LazyRunMetadataResponse,
    RunMetadataRequest,
    RunMetadataFilter,
    RunMetadataResponse,
    RunMetadataResponseBody,
    RunMetadataResponseMetadata,
)
from zenml.models.v2.core.schedule import (
    ScheduleRequest,
    ScheduleUpdate,
    ScheduleFilter,
    ScheduleResponse,
    ScheduleResponseBody,
    ScheduleResponseMetadata,
)
from zenml.models.v2.core.secret import (
    SecretFilter,
    SecretRequest,
    SecretResponse,
    SecretResponseBody,
    SecretResponseMetadata,
    SecretUpdate,
)
from zenml.models.v2.core.service_account import (
    ServiceAccountFilter,
    ServiceAccountResponseBody,
    ServiceAccountResponseMetadata,
    ServiceAccountUpdate,
    ServiceAccountRequest,
    ServiceAccountResponse,
)
from zenml.models.v2.core.service_connector import (
    ServiceConnectorRequest,
    ServiceConnectorUpdate,
    ServiceConnectorFilter,
    ServiceConnectorResponse,
    ServiceConnectorResponseBody,
    ServiceConnectorResponseMetadata,
)
from zenml.models.v2.core.stack import (
    StackRequest,
    StackUpdate,
    StackFilter,
    StackResponse,
    StackResponseBody,
    StackResponseMetadata,
)
from zenml.models.v2.core.step_run import (
    StepRunRequest,
    StepRunUpdate,
    StepRunFilter,
    StepRunResponse,
    StepRunResponseBody,
    StepRunResponseMetadata,
)
from zenml.models.v2.core.tag import (
    TagFilter,
    TagResponse,
    TagResponseBody,
    TagRequest,
    TagUpdate,
)
from zenml.models.v2.core.tag_resource import (
    TagResourceResponse,
    TagResourceResponseBody,
    TagResourceRequest,
)
from zenml.models.v2.core.user import (
    UserRequest,
    UserUpdate,
    UserFilter,
    UserResponse,
    UserResponseBody,
    UserResponseMetadata,
)
from zenml.models.v2.core.workspace import (
    WorkspaceRequest,
    WorkspaceUpdate,
    WorkspaceFilter,
    WorkspaceResponse,
    WorkspaceResponseBody,
    WorkspaceResponseMetadata,
)

# V2 Misc
from zenml.models.v2.misc.service_connector_type import (
    AuthenticationMethodModel,
    ServiceConnectorResourcesModel,
    ServiceConnectorRequirements,
    ServiceConnectorTypeModel,
    ServiceConnectorTypedResourcesModel,
    ResourceTypeModel,
)
from zenml.models.v2.misc.server_models import ServerDatabaseType, ServerModel
from zenml.models.v2.core.trigger import (
    TriggerRequest,
    TriggerFilter,
    TriggerUpdate,
    TriggerResponse,
    TriggerResponseBody,
    TriggerResponseMetadata,
    TriggerResponseResources,
)
from zenml.models.v2.core.trigger_execution import (
    TriggerExecutionRequest,
    TriggerExecutionFilter,
    TriggerExecutionResponse,
    TriggerExecutionResponseBody,
    TriggerExecutionResponseMetadata,
    TriggerExecutionResponseResources,
)
from zenml.models.v2.core.event_source import (
    EventSourceRequest,
    EventSourceFilter,
    EventSourceUpdate,
    EventSourceResponse,
    EventSourceResponseBody,
    EventSourceResponseMetadata,
    EventSourceResponseResources,
)
from zenml.models.v2.misc.user_auth import UserAuthModel
from zenml.models.v2.misc.build_item import BuildItem
from zenml.models.v2.misc.loaded_visualization import LoadedVisualization
from zenml.models.v2.misc.hub_plugin_models import (
    HubPluginRequestModel,
    HubPluginResponseModel,
    HubUserResponseModel,
    HubPluginBaseModel,
    PluginStatus,
)
from zenml.models.v2.misc.external_user import ExternalUserModel
from zenml.models.v2.misc.auth_models import (
    OAuthDeviceAuthorizationRequest,
    OAuthDeviceAuthorizationResponse,
    OAuthDeviceTokenRequest,
    OAuthDeviceUserAgentHeader,
    OAuthDeviceVerificationRequest,
    OAuthRedirectResponse,
    OAuthTokenResponse,
)
from zenml.models.v2.misc.server_models import (
    ServerModel,
    ServerDatabaseType,
    ServerDeploymentType,
)
from zenml.models.v2.core.server_settings import (
    ServerActivationRequest,
    ServerSettingsResponse,
    ServerSettingsResponseResources,
    ServerSettingsResponseBody,
    ServerSettingsResponseMetadata,
    ServerSettingsUpdate,
)

# ----------------------------- Forward References -----------------------------

# V2
ActionResponseResources.model_rebuild()
APIKeyResponseBody.model_rebuild()
ArtifactVersionRequest.model_rebuild()
ArtifactVersionResponseBody.model_rebuild()
ArtifactVersionResponseMetadata.model_rebuild()
CodeReferenceResponseBody.model_rebuild()
CodeRepositoryResponseBody.model_rebuild()
CodeRepositoryResponseMetadata.model_rebuild()
ComponentResponseBody.model_rebuild()
ComponentResponseMetadata.model_rebuild()
EventSourceResponseBody.model_rebuild()
EventSourceResponseMetadata.model_rebuild()
EventSourceResponseResources.model_rebuild()
FlavorResponseBody.model_rebuild()
FlavorResponseMetadata.model_rebuild()
LazyArtifactVersionResponse.model_rebuild()
LazyRunMetadataResponse.model_rebuild()
ModelResponseBody.model_rebuild()
ModelResponseMetadata.model_rebuild()
ModelVersionResponseBody.model_rebuild()
ModelVersionResponseMetadata.model_rebuild()
ModelVersionResponseResources.model_rebuild()
ModelVersionArtifactResponseBody.model_rebuild()
ModelVersionPipelineRunResponseBody.model_rebuild()
OAuthDeviceResponseBody.model_rebuild()
PipelineResponseBody.model_rebuild()
PipelineResponseMetadata.model_rebuild()
PipelineBuildBase.model_rebuild()
PipelineBuildResponseBody.model_rebuild()
PipelineBuildResponseMetadata.model_rebuild()
PipelineDeploymentRequest.model_rebuild()
PipelineDeploymentResponseBody.model_rebuild()
PipelineDeploymentResponseMetadata.model_rebuild()
PipelineDeploymentResponseResources.model_rebuild()
PipelineRunResponseBody.model_rebuild()
PipelineRunResponseMetadata.model_rebuild()
RunMetadataResponseBody.model_rebuild()
RunMetadataResponseMetadata.model_rebuild()
ScheduleResponseBody.model_rebuild()
ScheduleResponseMetadata.model_rebuild()
SecretResponseBody.model_rebuild()
SecretResponseMetadata.model_rebuild()
ServiceResponseBody.model_rebuild()
ServiceResponseMetadata.model_rebuild()
ServiceResponseResources.model_rebuild()
ServiceConnectorResponseBody.model_rebuild()
ServiceConnectorResponseMetadata.model_rebuild()
StackResponseBody.model_rebuild()
StackResponseMetadata.model_rebuild()
StepRunRequest.model_rebuild()
StepRunResponseBody.model_rebuild()
StepRunResponseMetadata.model_rebuild()
TriggerExecutionResponseResources.model_rebuild()
TriggerResponseBody.model_rebuild()
TriggerResponseMetadata.model_rebuild()
TriggerResponseResources.model_rebuild()
TriggerResponseResources.model_rebuild()


__all__ = [
    # V2 Base
    "BaseRequest",
    "BaseResponse",
    "BaseUpdate",
    "BaseIdentifiedResponse",
    "BaseResponseBody",
    "BaseResponseMetadata",
    "BaseResponseResources",
    "BaseDatedResponseBody",
    "BaseZenModel",
    "BasePluginFlavorResponse",
    "UserScopedRequest",
    "UserScopedFilter",
    "UserScopedResponse",
    "UserScopedResponseBody",
    "UserScopedResponseMetadata",
    "WorkspaceScopedRequest",
    "WorkspaceScopedFilter",
    "WorkspaceScopedResponse",
    "WorkspaceScopedResponseBody",
    "WorkspaceScopedResponseMetadata",
    "WorkspaceScopedResponseResources",
    "WorkspaceScopedTaggableFilter",
    "BaseFilter",
    "StrFilter",
    "BoolFilter",
    "NumericFilter",
    "UUIDFilter",
    "Page",
    # V2 Core
    "ActionFilter",
    "ActionRequest",
    "ActionResponse",
    "ActionResponseBody",
    "ActionResponseMetadata",
    "ActionResponseResources",
    "ActionUpdate",
    "ActionFlavorResponse",
    "ActionFlavorResponseBody",
    "ActionFlavorResponseMetadata",
    "ActionFlavorResponseResources",
    "APIKey",
    "APIKeyRequest",
    "APIKeyUpdate",
    "APIKeyFilter",
    "APIKeyResponse",
    "APIKeyResponseBody",
    "APIKeyResponseMetadata",
    "APIKeyInternalResponse",
    "APIKeyInternalUpdate",
    "APIKeyRotateRequest",
    "ArtifactFilter",
    "ArtifactRequest",
    "ArtifactResponse",
    "ArtifactResponseBody",
    "ArtifactResponseMetadata",
    "ArtifactUpdate",
    "ArtifactVersionRequest",
    "ArtifactVersionFilter",
    "ArtifactVersionResponse",
    "ArtifactVersionResponseBody",
    "ArtifactVersionResponseMetadata",
    "ArtifactVersionUpdate",
    "ArtifactVisualizationRequest",
    "ArtifactVisualizationResponse",
    "ArtifactVisualizationResponseBody",
    "ArtifactVisualizationResponseMetadata",
    "CodeReferenceRequest",
    "CodeReferenceResponse",
    "CodeReferenceResponseBody",
    "CodeReferenceResponseMetadata",
    "CodeRepositoryUpdate",
    "CodeRepositoryFilter",
    "CodeRepositoryRequest",
    "CodeRepositoryResponse",
    "CodeRepositoryResponseBody",
    "CodeRepositoryResponseMetadata",
    "ComponentBase",
    "ComponentRequest",
    "ComponentUpdate",
    "ComponentFilter",
    "ComponentResponse",
    "ComponentResponseBody",
    "ComponentResponseMetadata",
    "EventSourceFlavorResponse",
    "EventSourceFlavorResponseBody",
    "EventSourceFlavorResponseMetadata",
    "EventSourceFlavorResponseResources",
    "FlavorRequest",
    "FlavorUpdate",
    "FlavorFilter",
    "FlavorResponse",
    "FlavorResponseBody",
    "FlavorResponseMetadata",
    "LogsRequest",
    "LogsResponse",
    "LogsResponseBody",
    "LogsResponseMetadata",
    "ModelFilter",
    "ModelRequest",
    "ModelResponse",
    "ModelResponseBody",
    "ModelResponseMetadata",
    "ModelUpdate",
    "ModelVersionFilter",
    "ModelVersionRequest",
    "ModelVersionResponse",
    "ModelVersionResponseBody",
    "ModelVersionResponseMetadata",
    "ModelVersionResponseResources",
    "ModelVersionUpdate",
    "ModelVersionArtifactFilter",
    "ModelVersionArtifactRequest",
    "ModelVersionArtifactResponse",
    "ModelVersionArtifactResponseBody",
    "ModelVersionPipelineRunFilter",
    "ModelVersionPipelineRunRequest",
    "ModelVersionPipelineRunResponse",
    "ModelVersionPipelineRunResponseBody",
    "OAuthDeviceUpdate",
    "OAuthDeviceFilter",
    "OAuthDeviceResponse",
    "OAuthDeviceResponseBody",
    "OAuthDeviceResponseMetadata",
    "OAuthDeviceInternalRequest",
    "OAuthDeviceInternalUpdate",
    "OAuthDeviceInternalResponse",
    "PipelineRequest",
    "PipelineUpdate",
    "PipelineFilter",
    "PipelineResponse",
    "PipelineResponseBody",
    "PipelineResponseMetadata",
    "PipelineBuildBase",
    "PipelineBuildRequest",
    "PipelineBuildFilter",
    "PipelineBuildResponse",
    "PipelineBuildResponseBody",
    "PipelineBuildResponseMetadata",
    "PipelineDeploymentBase",
    "PipelineDeploymentRequest",
    "PipelineDeploymentFilter",
    "PipelineDeploymentResponse",
    "PipelineDeploymentResponseBody",
    "PipelineDeploymentResponseMetadata",
    "PipelineRunRequest",
    "PipelineRunUpdate",
    "PipelineRunFilter",
    "PipelineRunResponse",
    "PipelineRunResponseBody",
    "PipelineRunResponseMetadata",
    "RunMetadataRequest",
    "RunMetadataFilter",
    "RunMetadataResponse",
    "RunMetadataResponseBody",
    "RunMetadataResponseMetadata",
    "ScheduleRequest",
    "ScheduleUpdate",
    "ScheduleFilter",
    "ScheduleResponse",
    "ScheduleResponseBody",
    "ScheduleResponseMetadata",
    "SecretFilter",
    "SecretRequest",
    "SecretResponse",
    "SecretResponseBody",
    "SecretResponseMetadata",
    "SecretUpdate",
    "ServiceResponse",
    "ServiceResponseBody",
    "ServiceResponseMetadata",
    "ServiceUpdate",
    "ServiceFilter",
    "ServiceRequest",
    "ServiceResponseResources",
    "ServerActivationRequest",
    "ServerSettingsResponse",
    "ServerSettingsResponseResources",
    "ServerSettingsResponseBody",
    "ServerSettingsResponseMetadata",
    "ServerSettingsUpdate",
    "ServiceAccountFilter",
    "ServiceAccountResponseBody",
    "ServiceAccountResponseMetadata",
    "ServiceAccountUpdate",
    "ServiceAccountRequest",
    "ServiceAccountResponse",
    "ServiceConnectorRequest",
    "ServiceConnectorUpdate",
    "ServiceConnectorFilter",
    "ServiceConnectorResponse",
    "ServiceConnectorResponseBody",
    "ServiceConnectorResponseMetadata",
    "StackRequest",
    "StackUpdate",
    "StackFilter",
    "StackResponse",
    "StackResponseBody",
    "StackResponseMetadata",
    "StepRunRequest",
    "StepRunUpdate",
    "StepRunFilter",
    "StepRunResponse",
    "StepRunResponseBody",
    "StepRunResponseMetadata",
    "TagFilter",
    "TagResourceResponse",
    "TagResourceResponseBody",
    "TagResourceRequest",
    "TagResponse",
    "TagResponseBody",
    "TagRequest",
    "TagUpdate",
    "TriggerResponse",
    "TriggerRequest",
    "TriggerFilter",
    "TriggerUpdate",
    "TriggerResponseBody",
    "TriggerResponseMetadata",
    "TriggerResponseResources",
    "TriggerExecutionRequest",
    "TriggerExecutionFilter",
    "TriggerExecutionResponse",
    "TriggerExecutionResponseBody",
    "TriggerExecutionResponseMetadata",
    "TriggerExecutionResponseResources",
    "EventSourceResponse",
    "EventSourceRequest",
    "EventSourceFilter",
    "EventSourceUpdate",
    "EventSourceResponseBody",
    "EventSourceResponseMetadata",
    "EventSourceResponseResources",
    "UserRequest",
    "UserUpdate",
    "UserFilter",
    "UserResponse",
    "UserResponseBody",
    "UserResponseMetadata",
    "WorkspaceRequest",
    "WorkspaceUpdate",
    "WorkspaceFilter",
    "WorkspaceResponse",
    "WorkspaceResponseBody",
    "WorkspaceResponseMetadata",
    # V2 Misc
    "AuthenticationMethodModel",
    "ServiceConnectorResourcesModel",
    "ServiceConnectorTypeModel",
    "ServiceConnectorTypedResourcesModel",
    "ServiceConnectorRequirements",
    "ResourceTypeModel",
    "UserAuthModel",
    "ExternalUserModel",
    "BuildItem",
    "LoadedVisualization",
    "HubPluginRequestModel",
    "HubPluginResponseModel",
    "HubUserResponseModel",
    "HubPluginBaseModel",
    "PluginStatus",
    "ServerModel",
    "ServerDatabaseType",
    "ServerDeploymentType",
    "OAuthDeviceAuthorizationRequest",
    "OAuthDeviceAuthorizationResponse",
    "OAuthDeviceTokenRequest",
    "OAuthDeviceUserAgentHeader",
    "OAuthDeviceVerificationRequest",
    "OAuthRedirectResponse",
    "OAuthTokenResponse",
]
