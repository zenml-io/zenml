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

from zenml.models.auth_models import (
    OAuthDeviceAuthorizationRequest,
    OAuthDeviceAuthorizationResponse,
    OAuthDeviceTokenRequest,
    OAuthDeviceUserAgentHeader,
    OAuthDeviceVerificationRequest,
    OAuthRedirectResponse,
    OAuthTokenResponse,
)
from zenml.models.base_models import BaseRequestModel, BaseResponseModel
from zenml.models.device_models import (
    OAuthDeviceFilterModel,
    OAuthDeviceInternalRequestModel,
    OAuthDeviceInternalResponseModel,
    OAuthDeviceInternalUpdateModel,
    OAuthDeviceResponseModel,
    OAuthDeviceUpdateModel,
)
from zenml.models.page_model import Page
from zenml.models.secret_models import (
    SecretBaseModel,
    SecretFilterModel,
    SecretRequestModel,
    SecretResponseModel,
    SecretUpdateModel,
)
from zenml.models.server_models import ServerDatabaseType, ServerModel
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
    SharableResponseBody,
    SharableResponseMetadata,
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
    ServiceConnectorTypeModel,
    ServiceConnectorTypedResourcesModel,
    ResourceTypeModel,
)
from zenml.models.v2.user_auth import UserAuthModel
from zenml.models.v2.build_item import BuildItem
from zenml.models.v2.loaded_visualization import LoadedVisualization


# ----------------------------- Forward References -----------------------------

SecretResponseModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
ModelRequestModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
ModelResponseModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
ModelVersionRequestModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
ModelVersionResponseModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
ModelVersionArtifactRequestModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
ModelVersionArtifactResponseModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
ModelVersionPipelineRunRequestModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
ModelVersionPipelineRunResponseModel.update_forward_refs(
    UserResponseModel=UserResponse,
    WorkspaceResponseModel=WorkspaceResponse,
)
OAuthDeviceResponseModel.update_forward_refs(
    UserResponseModel=UserResponse,
)
OAuthDeviceInternalResponseModel.update_forward_refs(
    UserResponseModel=UserResponse,
)

__all__ = [
    # V1
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
    "ServerDatabaseType",
    "ServerModel",
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
    "SharableResponseBody",
    "SharableResponseMetadata",
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
    "ResourceTypeModel",
    "UserAuthModel",
    "BuildItem",
    "LoadedVisualization",
]
