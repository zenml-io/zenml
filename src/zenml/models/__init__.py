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

from zenml.models.api_key_models import (
    APIKey,
    APIKeyFilterModel,
    APIKeyInternalResponseModel,
    APIKeyInternalUpdateModel,
    APIKeyRequestModel,
    APIKeyResponseModel,
    APIKeyRotateRequestModel,
    APIKeyUpdateModel,
)
from zenml.models.auth_models import (
    OAuthDeviceAuthorizationRequest,
    OAuthDeviceAuthorizationResponse,
    OAuthDeviceTokenRequest,
    OAuthDeviceUserAgentHeader,
    OAuthDeviceVerificationRequest,
    OAuthRedirectResponse,
    OAuthTokenResponse,
)
from zenml.models.base_models import (
    BaseRequestModel,
    BaseResponseModel,
    WorkspaceScopedRequestModel,
)
from zenml.models.device_models import (
    OAuthDeviceFilterModel,
    OAuthDeviceInternalRequestModel,
    OAuthDeviceInternalResponseModel,
    OAuthDeviceInternalUpdateModel,
    OAuthDeviceResponseModel,
    OAuthDeviceUpdateModel,
)
from zenml.models.secret_models import (
    SecretBaseModel,
    SecretFilterModel,
    SecretRequestModel,
    SecretResponseModel,
    SecretUpdateModel,
)
from zenml.models.server_models import ServerDatabaseType, ServerModel
from zenml.models.service_account_models import (
    ServiceAccountFilterModel,
    ServiceAccountRequestModel,
    ServiceAccountResponseModel,
    ServiceAccountUpdateModel,
)
from zenml.models.user_models import ExternalUserModel
from zenml.models.model_models import (
    ModelFilterModel,
    ModelResponseModel,
    ModelRequestModel,
    ModelUpdateModel,
    ModelVersionBaseModel,
    ModelVersionResponseModel,
    ModelVersionRequestModel,
    ModelVersionArtifactBaseModel,
    ModelVersionArtifactFilterModel,
    ModelVersionArtifactRequestModel,
    ModelVersionArtifactResponseModel,
    ModelVersionPipelineRunBaseModel,
    ModelVersionPipelineRunFilterModel,
    ModelVersionPipelineRunRequestModel,
    ModelVersionPipelineRunResponseModel,
    ModelVersionFilterModel,
    ModelVersionUpdateModel,
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
    ShareableRequest,
    ShareableFilter,
    ShareableResponse,
    ShareableResponseBody,
    ShareableResponseMetadata,
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
from zenml.models.v2.core.artifact import (
    ArtifactRequest,
    ArtifactFilter,
    ArtifactResponse,
    ArtifactResponseBody,
    ArtifactResponseMetadata,
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
from zenml.models.v2.core.role import (
    RoleRequest,
    RoleUpdate,
    RoleFilter,
    RoleResponse,
    RoleResponseBody,
    RoleResponseMetadata,
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
from zenml.models.v2.core.team import (
    TeamRequest,
    TeamUpdate,
    TeamFilter,
    TeamResponse,
    TeamResponseBody,
    TeamResponseMetadata,
)
from zenml.models.v2.core.team_role import (
    TeamRoleAssignmentRequest,
    TeamRoleAssignmentFilter,
    TeamRoleAssignmentResponse,
    TeamRoleAssignmentResponseBody,
    TeamRoleAssignmentResponseMetadata,
)
from zenml.models.v2.core.user import (
    UserRequest,
    UserUpdate,
    UserFilter,
    UserResponse,
    UserResponseBody,
    UserResponseMetadata,
)
from zenml.models.v2.core.user_role import (
    UserRoleAssignmentRequest,
    UserRoleAssignmentFilter,
    UserRoleAssignmentResponse,
    UserRoleAssignmentResponseBody,
    UserRoleAssignmentResponseMetadata,
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
from zenml.models.v2.service_connector_type import (
    AuthenticationMethodModel,
    ServiceConnectorResourcesModel,
    ServiceConnectorRequirements,
    ServiceConnectorTypeModel,
    ServiceConnectorTypedResourcesModel,
    ResourceTypeModel,
)
from zenml.models.v2.misc.user_auth import UserAuthModel
from zenml.models.v2.misc.build_item import BuildItem
from zenml.models.v2.loaded_visualization import LoadedVisualization
from zenml.models.v2.misc.hub_plugin_models import (
    HubPluginRequestModel,
    HubPluginResponseModel,
    HubUserResponseModel,
    HubPluginBaseModel,
    PluginStatus,
)

# ----------------------------- Forward References -----------------------------

# V1
APIKeyResponseModel.update_forward_refs(
    ServiceAccountResponseModel=ServiceAccountResponseModel,
)
APIKeyInternalResponseModel.update_forward_refs(
    ServiceAccountResponseModel=ServiceAccountResponseModel,
)
ServiceAccountResponseModel.update_forward_refs(TeamResponse=TeamResponse)
SecretResponseModel.update_forward_refs(
    UserResponse=UserResponse,
    WorkspaceResponse=WorkspaceResponse,
)
ModelRequestModel.update_forward_refs(
    UserResponse=UserResponse,
    WorkspaceResponse=WorkspaceResponse,
)
ModelResponseModel.update_forward_refs(
    UserResponse=UserResponse,
    WorkspaceResponse=WorkspaceResponse,
)
ModelVersionRequestModel.update_forward_refs(
    UserResponse=UserResponse,
    WorkspaceResponse=WorkspaceResponse,
)
ModelVersionResponseModel.update_forward_refs(
    UserResponse=UserResponse,
    WorkspaceResponse=WorkspaceResponse,
)
ModelVersionArtifactRequestModel.update_forward_refs(
    UserResponse=UserResponse,
    WorkspaceResponse=WorkspaceResponse,
)
ModelVersionArtifactResponseModel.update_forward_refs(
    UserResponse=UserResponse,
    WorkspaceResponse=WorkspaceResponse,
)
ModelVersionPipelineRunRequestModel.update_forward_refs(
    UserResponse=UserResponse,
    WorkspaceResponse=WorkspaceResponse,
)
ModelVersionPipelineRunResponseModel.update_forward_refs(
    UserResponse=UserResponse,
    WorkspaceResponse=WorkspaceResponse,
)
OAuthDeviceResponseModel.update_forward_refs(
    UserResponse=UserResponse,
)
OAuthDeviceInternalResponseModel.update_forward_refs(
    UserResponse=UserResponse,
)

# V2
ArtifactRequest.update_forward_refs(
    ArtifactVisualizationRequest=ArtifactVisualizationRequest,
)
ArtifactResponseBody.update_forward_refs(
    UserResponse=UserResponse,
)
ArtifactResponseMetadata.update_forward_refs(
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
    ArtifactResponse=ArtifactResponse,
)
StepRunResponseMetadata.update_forward_refs(
    WorkspaceResponse=WorkspaceResponse,
    LogsResponse=LogsResponse,
    RunMetadataResponse=RunMetadataResponse,
)
TeamResponseBody.update_forward_refs(
    UserResponse=UserResponse,
)
TeamRoleAssignmentResponseMetadata.update_forward_refs(
    WorkspaceResponse=WorkspaceResponse,
    TeamResponse=TeamResponse,
    RoleResponse=RoleResponse,
)
UserRoleAssignmentResponseMetadata.update_forward_refs(
    WorkspaceResponse=WorkspaceResponse,
    UserResponse=UserResponse,
    RoleResponse=RoleResponse,
)
UserResponseMetadata.update_forward_refs(
    RoleResponse=RoleResponse,
    TeamResponse=TeamResponse,
)
__all__ = [
    # V1
    "APIKey",
    "APIKeyFilterModel",
    "APIKeyInternalResponseModel",
    "APIKeyInternalUpdateModel",
    "APIKeyRequestModel",
    "APIKeyResponseModel",
    "APIKeyRotateRequestModel",
    "APIKeyUpdateModel",
    "BaseRequestModel",
    "BaseResponseModel",
    "ExternalUserModel",
    "ModelFilterModel",
    "ModelRequestModel",
    "ModelResponseModel",
    "ModelUpdateModel",
    "ModelVersionBaseModel",
    "ModelVersionFilterModel",
    "ModelVersionRequestModel",
    "ModelVersionResponseModel",
    "ModelVersionUpdateModel",
    "ModelVersionArtifactBaseModel",
    "ModelVersionArtifactFilterModel",
    "ModelVersionArtifactRequestModel",
    "ModelVersionArtifactResponseModel",
    "ModelVersionPipelineRunBaseModel",
    "ModelVersionPipelineRunFilterModel",
    "ModelVersionPipelineRunRequestModel",
    "ModelVersionPipelineRunResponseModel",
    "OAuthDeviceAuthorizationRequest",
    "OAuthDeviceAuthorizationResponse",
    "OAuthDeviceFilterModel",
    "OAuthDeviceInternalRequestModel",
    "OAuthDeviceInternalResponseModel",
    "OAuthDeviceInternalUpdateModel",
    "OAuthDeviceResponseModel",
    "OAuthDeviceTokenRequest",
    "OAuthDeviceUpdateModel",
    "OAuthDeviceUserAgentHeader",
    "OAuthDeviceVerificationRequest",
    "OAuthRedirectResponse",
    "OAuthTokenResponse",
    "Page",
    "SecretBaseModel",
    "SecretFilterModel",
    "SecretRequestModel",
    "SecretResponseModel",
    "SecretUpdateModel",
    "ServiceAccountFilterModel",
    "ServiceAccountRequestModel",
    "ServiceAccountResponseModel",
    "ServiceAccountUpdateModel",
    "ServerDatabaseType",
    "ServerModel",
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
    "ShareableRequest",
    "ShareableFilter",
    "ShareableResponse",
    "ShareableResponseBody",
    "ShareableResponseMetadata",
    "BaseFilter",
    "StrFilter",
    "BoolFilter",
    "NumericFilter",
    "UUIDFilter",
    "Page",
    # V2 Core
    "ArtifactRequest",
    "ArtifactFilter",
    "ArtifactResponse",
    "ArtifactResponseBody",
    "ArtifactResponseMetadata",
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
    "RoleRequest",
    "RoleUpdate",
    "RoleFilter",
    "RoleResponse",
    "RoleResponseBody",
    "RoleResponseMetadata",
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
    "TeamRequest",
    "TeamUpdate",
    "TeamFilter",
    "TeamResponse",
    "TeamResponseBody",
    "TeamResponseMetadata",
    "TeamRoleAssignmentRequest",
    "TeamRoleAssignmentFilter",
    "TeamRoleAssignmentResponse",
    "TeamRoleAssignmentResponseBody",
    "TeamRoleAssignmentResponseMetadata",
    "UserRequest",
    "UserUpdate",
    "UserFilter",
    "UserResponse",
    "UserResponseBody",
    "UserResponseMetadata",
    "UserRoleAssignmentRequest",
    "UserRoleAssignmentFilter",
    "UserRoleAssignmentResponse",
    "UserRoleAssignmentResponseBody",
    "UserRoleAssignmentResponseMetadata",
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
    "BuildItem",
    "LoadedVisualization",
    "HubPluginRequestModel",
    "HubPluginResponseModel",
    "HubUserResponseModel",
    "HubPluginBaseModel",
    "PluginStatus",
]
