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

from zenml.models.artifact_models import (
    ArtifactFilterModel,
    ArtifactRequestModel,
    ArtifactResponseModel,
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
from zenml.models.base_models import BaseRequestModel, BaseResponseModel
from zenml.models.code_repository_models import (
    CodeReferenceRequestModel,
    CodeReferenceResponseModel,
    CodeRepositoryFilterModel,
    CodeRepositoryRequestModel,
    CodeRepositoryResponseModel,
    CodeRepositoryUpdateModel,
)
from zenml.models.component_models import (
    ComponentFilterModel,
    ComponentRequestModel,
    ComponentResponseModel,
    ComponentUpdateModel,
)
from zenml.models.device_models import (
    OAuthDeviceFilterModel,
    OAuthDeviceInternalRequestModel,
    OAuthDeviceInternalResponseModel,
    OAuthDeviceInternalUpdateModel,
    OAuthDeviceResponseModel,
    OAuthDeviceUpdateModel,
)
from zenml.models.filter_models import Filter, BaseFilterModel
from zenml.models.flavor_models import (
    FlavorFilterModel,
    FlavorRequestModel,
    FlavorResponseModel,
    FlavorUpdateModel,
)
from zenml.models.logs_models import (
    LogsBaseModel,
    LogsRequestModel,
    LogsResponseModel,
)
from zenml.models.page_model import Page
from zenml.models.pipeline_build_models import (
    PipelineBuildFilterModel,
    PipelineBuildRequestModel,
    PipelineBuildResponseModel,
)
from zenml.models.pipeline_deployment_models import (
    PipelineDeploymentFilterModel,
    PipelineDeploymentRequestModel,
    PipelineDeploymentResponseModel,
)
from zenml.models.pipeline_models import (
    PipelineFilterModel,
    PipelineRequestModel,
    PipelineResponseModel,
    PipelineUpdateModel,
)
from zenml.models.pipeline_run_models import (
    PipelineRunFilterModel,
    PipelineRunRequestModel,
    PipelineRunResponseModel,
    PipelineRunUpdateModel,
)
from zenml.models.role_models import (
    RoleFilterModel,
    RoleRequestModel,
    RoleResponseModel,
    RoleUpdateModel,
)
from zenml.models.run_metadata_models import (
    RunMetadataFilterModel,
    RunMetadataRequestModel,
    RunMetadataResponseModel,
)
from zenml.models.schedule_model import (
    ScheduleFilterModel,
    ScheduleRequestModel,
    ScheduleResponseModel,
    ScheduleUpdateModel,
)
from zenml.models.secret_models import (
    SecretBaseModel,
    SecretFilterModel,
    SecretRequestModel,
    SecretResponseModel,
    SecretUpdateModel,
)
from zenml.models.server_models import ServerDatabaseType, ServerModel
from zenml.models.service_connector_models import (
    AuthenticationMethodModel,
    ResourceTypeModel,
    ServiceConnectorBaseModel,
    ServiceConnectorFilterModel,
    ServiceConnectorRequestModel,
    ServiceConnectorRequirements,
    ServiceConnectorResourcesModel,
    ServiceConnectorResponseModel,
    ServiceConnectorTypeModel,
    ServiceConnectorUpdateModel,
)
from zenml.models.stack_models import (
    StackFilterModel,
    StackRequestModel,
    StackResponseModel,
    StackUpdateModel,
)
from zenml.models.step_run_models import (
    StepRunFilterModel,
    StepRunRequestModel,
    StepRunResponseModel,
    StepRunUpdateModel,
)
from zenml.models.team_models import (
    TeamFilterModel,
    TeamRequestModel,
    TeamResponseModel,
    TeamUpdateModel,
)
from zenml.models.team_role_assignment_models import (
    TeamRoleAssignmentFilterModel,
    TeamRoleAssignmentRequestModel,
    TeamRoleAssignmentResponseModel,
)
from zenml.models.user_models import (
    ExternalUserModel,
    UserAuthModel,
    UserFilterModel,
    UserRequestModel,
    UserResponseModel,
    UserUpdateModel,
)
from zenml.models.user_role_assignment_models import (
    UserRoleAssignmentFilterModel,
    UserRoleAssignmentRequestModel,
    UserRoleAssignmentResponseModel,
)
from zenml.models.workspace_models import (
    WorkspaceFilterModel,
    WorkspaceRequestModel,
    WorkspaceResponseModel,
    WorkspaceUpdateModel,
)
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


ComponentResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)

StackResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)

FlavorResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)

UserResponseModel.update_forward_refs(TeamResponseModel=TeamResponseModel)

TeamResponseModel.update_forward_refs(UserResponseModel=UserResponseModel)

UserRoleAssignmentResponseModel.update_forward_refs(
    RoleResponseModel=RoleResponseModel,
    TeamResponseModel=TeamResponseModel,
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)

TeamRoleAssignmentResponseModel.update_forward_refs(
    RoleResponseModel=RoleResponseModel,
    TeamResponseModel=TeamResponseModel,
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)

PipelineResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)

RunMetadataResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)
ScheduleResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)
PipelineBuildResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
    PipelineResponseModel=PipelineResponseModel,
    StackResponseModel=StackResponseModel,
)

PipelineDeploymentResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
    PipelineResponseModel=PipelineResponseModel,
    StackResponseModel=StackResponseModel,
    PipelineBuildResponseModel=PipelineBuildResponseModel,
    ScheduleResponseModel=ScheduleResponseModel,
    CodeReferenceResponseModel=CodeReferenceResponseModel,
)

PipelineDeploymentRequestModel.update_forward_refs(
    CodeReferenceRequestModel=CodeReferenceRequestModel,
)

PipelineRunResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
    PipelineResponseModel=PipelineResponseModel,
    StackResponseModel=StackResponseModel,
    RunMetadataResponseModel=RunMetadataResponseModel,
    PipelineBuildResponseModel=PipelineBuildResponseModel,
    StepRunResponseModel=StepRunResponseModel,
    ScheduleResponseModel=ScheduleResponseModel,
    CodeReferenceResponseModel=CodeReferenceResponseModel,
)

StepRunResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
    ArtifactResponseModel=ArtifactResponseModel,
    RunMetadataResponseModel=RunMetadataResponseModel,
)

ArtifactResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
    RunMetadataResponseModel=RunMetadataResponseModel,
)

SecretResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)
CodeRepositoryResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)
ServiceConnectorResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)
ServiceConnectorResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)

ModelRequestModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)

ModelResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)

ModelVersionRequestModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)

ModelVersionResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)

ModelVersionArtifactRequestModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)
ModelVersionArtifactResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)
ModelVersionPipelineRunRequestModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)
ModelVersionPipelineRunResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
)

OAuthDeviceResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
)
OAuthDeviceInternalResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
)

__all__ = [
    "ArtifactFilterModel",
    "ArtifactRequestModel",
    "ArtifactResponseModel",
    "AuthenticationMethodModel",
    "BaseFilterModel",
    "BaseRequestModel",
    "BaseResponseModel",
    "CodeReferenceRequestModel",
    "CodeReferenceResponseModel",
    "CodeRepositoryFilterModel",
    "CodeRepositoryRequestModel",
    "CodeRepositoryResponseModel",
    "CodeRepositoryUpdateModel",
    "ComponentFilterModel",
    "ComponentRequestModel",
    "ComponentResponseModel",
    "ComponentUpdateModel",
    "ExternalUserModel",
    "Filter",
    "FlavorFilterModel",
    "FlavorRequestModel",
    "FlavorResponseModel",
    "FlavorUpdateModel",
    "LogsBaseModel",
    "LogsRequestModel",
    "LogsResponseModel",
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
    "PipelineBuildFilterModel",
    "PipelineBuildRequestModel",
    "PipelineBuildResponseModel",
    "PipelineDeploymentFilterModel",
    "PipelineDeploymentRequestModel",
    "PipelineDeploymentResponseModel",
    "PipelineFilterModel",
    "PipelineRequestModel",
    "PipelineResponseModel",
    "PipelineRunFilterModel",
    "PipelineRunRequestModel",
    "PipelineRunResponseModel",
    "PipelineRunUpdateModel",
    "PipelineUpdateModel",
    "ResourceTypeModel",
    "RoleFilterModel",
    "RoleRequestModel",
    "RoleResponseModel",
    "RoleUpdateModel",
    "RunMetadataFilterModel",
    "RunMetadataRequestModel",
    "RunMetadataResponseModel",
    "ScheduleFilterModel",
    "ScheduleRequestModel",
    "ScheduleResponseModel",
    "ScheduleUpdateModel",
    "SecretBaseModel",
    "SecretFilterModel",
    "SecretRequestModel",
    "SecretResponseModel",
    "SecretUpdateModel",
    "ServerDatabaseType",
    "ServerModel",
    "ServiceConnectorBaseModel",
    "ServiceConnectorFilterModel",
    "ServiceConnectorRequirements",
    "ServiceConnectorRequestModel",
    "ServiceConnectorResourcesModel",
    "ServiceConnectorResponseModel",
    "ServiceConnectorTypeModel",
    "ServiceConnectorUpdateModel",
    "StackFilterModel",
    "StackRequestModel",
    "StackResponseModel",
    "StackUpdateModel",
    "StepRunFilterModel",
    "StepRunRequestModel",
    "StepRunResponseModel",
    "StepRunUpdateModel",
    "TeamFilterModel",
    "TeamRequestModel",
    "TeamResponseModel",
    "TeamRoleAssignmentFilterModel",
    "TeamRoleAssignmentRequestModel",
    "TeamRoleAssignmentResponseModel",
    "TeamUpdateModel",
    "UserRoleAssignmentFilterModel",
    "UserRoleAssignmentRequestModel",
    "UserRoleAssignmentResponseModel",
    "UserAuthModel",
    "UserFilterModel",
    "UserRequestModel",
    "UserResponseModel",
    "UserUpdateModel",
    "WorkspaceFilterModel",
    "WorkspaceRequestModel",
    "WorkspaceResponseModel",
    "WorkspaceUpdateModel",
]
