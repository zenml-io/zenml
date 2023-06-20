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
"""Pydantic models for the various concepts in ZenML."""

from zenml.models.artifact_models import (
    ArtifactFilterModel,
    ArtifactRequestModel,
    ArtifactResponseModel,
)
from zenml.models.pipeline_build_models import (
    PipelineBuildFilterModel,
    PipelineBuildRequestModel,
    PipelineBuildResponseModel,
)
from zenml.models.component_models import (
    ComponentFilterModel,
    ComponentRequestModel,
    ComponentResponseModel,
    ComponentUpdateModel,
)
from zenml.models.base_models import BaseRequestModel, BaseResponseModel
from zenml.models.filter_models import Filter, BaseFilterModel
from zenml.models.flavor_models import (
    FlavorFilterModel,
    FlavorRequestModel,
    FlavorResponseModel,
    FlavorUpdateModel,
)
from zenml.models.pipeline_models import (
    PipelineFilterModel,
    PipelineRequestModel,
    PipelineResponseModel,
    PipelineUpdateModel,
)
from zenml.models.page_model import Page
from zenml.models.pipeline_deployment_models import (
    PipelineDeploymentFilterModel,
    PipelineDeploymentRequestModel,
    PipelineDeploymentResponseModel,
)
from zenml.models.pipeline_run_models import (
    PipelineRunFilterModel,
    PipelineRunRequestModel,
    PipelineRunResponseModel,
    PipelineRunUpdateModel,
)
from zenml.models.workspace_models import (
    WorkspaceFilterModel,
    WorkspaceRequestModel,
    WorkspaceResponseModel,
    WorkspaceUpdateModel,
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
    ScheduleRequestModel,
    ScheduleResponseModel,
    ScheduleUpdateModel,
    ScheduleFilterModel,
)
from zenml.models.secret_models import (
    SecretBaseModel,
    SecretRequestModel,
    SecretFilterModel,
    SecretResponseModel,
    SecretUpdateModel,
)
from zenml.models.stack_models import (
    StackFilterModel,
    StackRequestModel,
    StackResponseModel,
    StackUpdateModel,
)
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
from zenml.models.code_repository_models import (
    CodeRepositoryFilterModel,
    CodeRepositoryRequestModel,
    CodeRepositoryResponseModel,
    CodeRepositoryUpdateModel,
    CodeReferenceRequestModel,
    CodeReferenceResponseModel,
)
from zenml.models.logs_models import (
    LogsBaseModel,
    LogsRequestModel,
    LogsResponseModel,
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
    CodeReferenceRequestModel=CodeReferenceRequestModel
)

PipelineRunResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    WorkspaceResponseModel=WorkspaceResponseModel,
    PipelineResponseModel=PipelineResponseModel,
    StackResponseModel=StackResponseModel,
    RunMetadataResponseModel=RunMetadataResponseModel,
    PipelineBuildResponseModel=PipelineBuildResponseModel,
    PipelineDeploymentResponseModel=PipelineDeploymentResponseModel,
    StepRunResponseModel=StepRunResponseModel,
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

__all__ = [
    "ArtifactRequestModel",
    "ArtifactResponseModel",
    "ArtifactFilterModel",
    "BaseRequestModel",
    "BaseResponseModel",
    "PipelineBuildFilterModel",
    "PipelineBuildRequestModel",
    "PipelineBuildResponseModel",
    "CodeRepositoryFilterModel",
    "CodeRepositoryRequestModel",
    "CodeRepositoryResponseModel",
    "CodeRepositoryUpdateModel",
    "CodeReferenceRequestModel",
    "CodeReferenceResponseModel",
    "ComponentRequestModel",
    "ComponentResponseModel",
    "ComponentUpdateModel",
    "ComponentFilterModel",
    "FlavorRequestModel",
    "FlavorResponseModel",
    "FlavorFilterModel",
    "FlavorUpdateModel",
    "BaseFilterModel",
    "Page",
    "PipelineRequestModel",
    "PipelineResponseModel",
    "PipelineUpdateModel",
    "PipelineFilterModel",
    "PipelineDeploymentRequestModel",
    "PipelineDeploymentResponseModel",
    "PipelineDeploymentFilterModel",
    "PipelineRunRequestModel",
    "PipelineRunResponseModel",
    "PipelineRunUpdateModel",
    "PipelineRunFilterModel",
    "WorkspaceRequestModel",
    "WorkspaceResponseModel",
    "WorkspaceUpdateModel",
    "WorkspaceFilterModel",
    "UserRoleAssignmentRequestModel",
    "UserRoleAssignmentResponseModel",
    "UserRoleAssignmentFilterModel",
    "TeamRoleAssignmentRequestModel",
    "TeamRoleAssignmentResponseModel",
    "TeamRoleAssignmentFilterModel",
    "RoleRequestModel",
    "RoleResponseModel",
    "RoleUpdateModel",
    "RoleFilterModel",
    "RunMetadataFilterModel",
    "RunMetadataRequestModel",
    "RunMetadataResponseModel",
    "ScheduleRequestModel",
    "ScheduleResponseModel",
    "ScheduleUpdateModel",
    "ScheduleFilterModel",
    "SecretBaseModel",
    "SecretRequestModel",
    "SecretFilterModel",
    "SecretResponseModel",
    "SecretUpdateModel",
    "AuthenticationMethodModel",
    "ResourceTypeModel",
    "ServiceConnectorTypeModel",
    "ServiceConnectorBaseModel",
    "ServiceConnectorFilterModel",
    "ServiceConnectorRequestModel",
    "ServiceConnectorRequirements",
    "ServiceConnectorResourcesModel",
    "ServiceConnectorResponseModel",
    "ServiceConnectorUpdateModel",
    "StackRequestModel",
    "StackResponseModel",
    "StackUpdateModel",
    "StackFilterModel",
    "StepRunRequestModel",
    "StepRunResponseModel",
    "StepRunUpdateModel",
    "StepRunFilterModel",
    "TeamRequestModel",
    "TeamResponseModel",
    "TeamUpdateModel",
    "TeamFilterModel",
    "UserRequestModel",
    "UserResponseModel",
    "UserUpdateModel",
    "UserFilterModel",
    "UserAuthModel",
    "LogsBaseModel",
    "LogsRequestModel",
    "LogsResponseModel",
]
