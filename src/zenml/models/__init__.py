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

# ------------------------------------- V1 -------------------------------------

from zenml.models.base_models import (
    BaseRequestModel,
    BaseResponseModel,
    WorkspaceScopedRequestModel,
)
from zenml.models.secret_models import (
    SecretBaseModel,
    SecretFilterModel,
    SecretRequestModel,
    SecretResponseModel,
    SecretUpdateModel,
)
from zenml.models.tag_models import (
    TagFilterModel,
    TagResourceResponseModel,
    TagResourceRequestModel,
    TagResponseModel,
    TagRequestModel,
    TagUpdateModel,
)

# ------------------------------------- V2 -------------------------------------

# V2 Base
from zenml.models.v2.base.base import (
    BaseRequest,
    BaseResponse,
    BaseResponseBody,
    BaseResponseMetadata,
    BaseZenModel,
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
)
from zenml.models.v2.core.artifact_visualization import (
    ArtifactVisualizationRequest,
    ArtifactVisualizationResponse,
    ArtifactVisualizationResponseBody,
    ArtifactVisualizationResponseMetadata,
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
)
from zenml.models.v2.core.pipeline_run import (
    PipelineRunRequest,
    PipelineRunUpdate,
    PipelineRunFilter,
    PipelineRunResponse,
    PipelineRunResponseBody,
    PipelineRunResponseMetadata,
)
from zenml.models.v2.core.run_metadata import (
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

# ----------------------------- Forward References -----------------------------

# V1
SecretResponseModel.update_forward_refs(
    UserResponse=UserResponse,
    WorkspaceResponse=WorkspaceResponse,
)

# V2
APIKeyResponseBody.update_forward_refs(
    ServiceAccountResponse=ServiceAccountResponse,
)
ArtifactVersionRequest.update_forward_refs(
    ArtifactVisualizationRequest=ArtifactVisualizationRequest,
)
ArtifactVersionResponseBody.update_forward_refs(
    UserResponse=UserResponse,
)
ArtifactVersionResponseMetadata.update_forward_refs(
    WorkspaceResponse=WorkspaceResponse,
    ArtifactVisualizationResponse=ArtifactVisualizationResponse,
    RunMetadataResponse=RunMetadataResponse,
)
CodeReferenceResponseBody.update_forward_refs(
    CodeRepositoryResponse=CodeRepositoryResponse,
)
CodeRepositoryResponseBody.update_forward_refs(
    UserResponse=UserResponse,
)
CodeRepositoryResponseMetadata.update_forward_refs(
    WorkspaceResponse=WorkspaceResponse,
)
ComponentResponseBody.update_forward_refs(
    UserResponse=UserResponse,
)
ComponentResponseMetadata.update_forward_refs(
    WorkspaceResponse=WorkspaceResponse,
    ServiceConnectorResponse=ServiceConnectorResponse,
)
FlavorResponseBody.update_forward_refs(
    UserResponse=UserResponse,
)
FlavorResponseMetadata.update_forward_refs(
    WorkspaceResponse=WorkspaceResponse,
)
ModelResponseBody.update_forward_refs(
    UserResponse=UserResponse,
    TagResponseModel=TagResponseModel,
)
ModelResponseMetadata.update_forward_refs(
    WorkspaceResponse=WorkspaceResponse,
)
ModelVersionResponseBody.update_forward_refs(
    UserResponse=UserResponse,
    ModelResponse=ModelResponse,
    RunMetadataResponse=RunMetadataResponse,
)
ModelVersionResponseMetadata.update_forward_refs(
    WorkspaceResponse=WorkspaceResponse,
    RunMetadataResponse=RunMetadataResponse,
)
ModelVersionArtifactResponseBody.update_forward_refs(
    ArtifactVersionResponse=ArtifactVersionResponse,
)
ModelVersionPipelineRunResponseBody.update_forward_refs(
    PipelineRunResponse=PipelineRunResponse
)
OAuthDeviceResponseBody.update_forward_refs(
    UserResponse=UserResponse,
)
PipelineResponseBody.update_forward_refs(
    UserResponse=UserResponse,
)
PipelineResponseMetadata.update_forward_refs(
    WorkspaceResponse=WorkspaceResponse,
)
PipelineBuildBase.update_forward_refs(
    BuildItem=BuildItem,
)
PipelineBuildResponseBody.update_forward_refs(
    UserResponse=UserResponse,
)
PipelineBuildResponseMetadata.update_forward_refs(
    WorkspaceResponse=WorkspaceResponse,
    PipelineResponse=PipelineResponse,
    StackResponse=StackResponse,
    BuildItem=BuildItem,
)
PipelineDeploymentRequest.update_forward_refs(
    CodeReferenceRequest=CodeReferenceRequest,
)
PipelineDeploymentResponseBody.update_forward_refs(
    UserResponse=UserResponse,
)
PipelineDeploymentResponseMetadata.update_forward_refs(
    WorkspaceResponse=WorkspaceResponse,
    PipelineResponse=PipelineResponse,
    StackResponse=StackResponse,
    PipelineBuildResponse=PipelineBuildResponse,
    ScheduleResponse=ScheduleResponse,
    CodeReferenceResponse=CodeReferenceResponse,
)
PipelineRunResponseBody.update_forward_refs(
    UserResponse=UserResponse,
    PipelineResponse=PipelineResponse,
    StackResponse=StackResponse,
    PipelineBuildResponse=PipelineBuildResponse,
    ScheduleResponse=ScheduleResponse,
    CodeReferenceResponse=CodeReferenceResponse,
)
PipelineRunResponseMetadata.update_forward_refs(
    WorkspaceResponse=WorkspaceResponse,
    RunMetadataResponse=RunMetadataResponse,
    StepRunResponse=StepRunResponse,
)
RunMetadataResponseBody.update_forward_refs(
    UserResponse=UserResponse,
)
RunMetadataResponseMetadata.update_forward_refs(
    WorkspaceResponse=WorkspaceResponse,
)
ScheduleResponseBody.update_forward_refs(
    UserResponse=UserResponse,
)
ScheduleResponseMetadata.update_forward_refs(
    WorkspaceResponse=WorkspaceResponse,
)
ServiceConnectorResponseBody.update_forward_refs(
    UserResponse=UserResponse,
)
ServiceConnectorResponseMetadata.update_forward_refs(
    ServiceConnectorTypeModel=ServiceConnectorTypeModel,
    WorkspaceResponse=WorkspaceResponse,
    ComponentResponse=ComponentResponse,
)
StackResponseBody.update_forward_refs(
    UserResponse=UserResponse,
)
StackResponseMetadata.update_forward_refs(
    ComponentResponse=ComponentResponse,
    WorkspaceResponse=WorkspaceResponse,
)
StepRunRequest.update_forward_refs(
    LogsRequest=LogsRequest,
)
StepRunResponseBody.update_forward_refs(
    UserResponse=UserResponse,
    ArtifactVersionResponse=ArtifactVersionResponse,
)
StepRunResponseMetadata.update_forward_refs(
    WorkspaceResponse=WorkspaceResponse,
    LogsResponse=LogsResponse,
    RunMetadataResponse=RunMetadataResponse,
)

__all__ = [
    # V1
    "BaseRequestModel",
    "BaseResponseModel",
    "SecretBaseModel",
    "SecretFilterModel",
    "SecretRequestModel",
    "SecretResponseModel",
    "SecretUpdateModel",
    "TagFilterModel",
    "TagResourceResponseModel",
    "TagResourceRequestModel",
    "TagResponseModel",
    "TagRequestModel",
    "TagUpdateModel",
    "WorkspaceScopedRequestModel",
    # V2 Base
    "BaseRequest",
    "BaseResponse",
    "BaseResponseBody",
    "BaseResponseMetadata",
    "BaseZenModel",
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
    "BaseFilter",
    "StrFilter",
    "BoolFilter",
    "NumericFilter",
    "UUIDFilter",
    "Page",
    # V2 Core
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
