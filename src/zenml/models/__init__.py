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
    ArtifactRequestModel,
    ArtifactResponseModel,
    ArtifactUpdateModel,
)
from zenml.models.component_models import (
    ComponentRequestModel,
    ComponentResponseModel,
    ComponentFilterModel,
    ComponentUpdateModel,
)
from zenml.models.filter_models import Filter, FilterBaseModel
from zenml.models.flavor_models import (
    FlavorRequestModel,
    FlavorResponseModel,
    FlavorFilterModel
)
from zenml.models.pipeline_models import (
    PipelineRequestModel,
    PipelineResponseModel,
    PipelineUpdateModel,
    PipelineFilterModel,
)
from zenml.models.pipeline_run_models import (
    PipelineRunRequestModel,
    PipelineRunResponseModel,
    PipelineRunUpdateModel,
)
from zenml.models.project_models import (
    ProjectRequestModel,
    ProjectResponseModel,
    ProjectUpdateModel,
    ProjectFilterModel,
)
from zenml.models.role_assignment_models import (
    RoleAssignmentRequestModel,
    RoleAssignmentResponseModel,
    RoleAssignmentFilterModel,
)
from zenml.models.role_models import (
    RoleRequestModel,
    RoleResponseModel,
    RoleUpdateModel,
    RoleFilterModel,
)
from zenml.models.stack_models import (
    StackFilterModel,
    StackRequestModel,
    StackResponseModel,
    StackUpdateModel,
)
from zenml.models.step_run_models import (
    StepRunRequestModel,
    StepRunResponseModel,
    StepRunUpdateModel,
)
from zenml.models.team_models import (
    TeamRequestModel,
    TeamResponseModel,
    TeamUpdateModel,
    TeamFilterModel,
)
from zenml.models.user_models import (
    UserAuthModel,
    UserFilterModel,
    UserRequestModel,
    UserResponseModel,
    UserUpdateModel,
)

ComponentResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    ProjectResponseModel=ProjectResponseModel,
)

StackResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    ProjectResponseModel=ProjectResponseModel,
)

FlavorResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    ProjectResponseModel=ProjectResponseModel,
)

UserResponseModel.update_forward_refs(TeamResponseModel=TeamResponseModel)

TeamResponseModel.update_forward_refs(UserResponseModel=UserResponseModel)

RoleAssignmentResponseModel.update_forward_refs(
    RoleResponseModel=RoleResponseModel,
    TeamResponseModel=TeamResponseModel,
    UserResponseModel=UserResponseModel,
    ProjectResponseModel=ProjectResponseModel,
)

PipelineResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    ProjectResponseModel=ProjectResponseModel,
)

PipelineRunResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    ProjectResponseModel=ProjectResponseModel,
    PipelineResponseModel=PipelineResponseModel,
    StackResponseModel=StackResponseModel,
)

StepRunResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    ProjectResponseModel=ProjectResponseModel,
    ArtifactResponseModel=ArtifactResponseModel,
)

ArtifactResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    ProjectResponseModel=ProjectResponseModel,
)

__all__ = [
    "ArtifactRequestModel",
    "ArtifactResponseModel",
    "ArtifactUpdateModel",
    "ComponentRequestModel",
    "ComponentResponseModel",
    "ComponentUpdateModel",
    "ComponentFilterModel",
    "FlavorRequestModel",
    "FlavorResponseModel",
    "FlavorFilterModel",
    "FilterBaseModel",
    "PipelineRequestModel",
    "PipelineResponseModel",
    "PipelineUpdateModel",
    "PipelineFilterModel",
    "PipelineRunRequestModel",
    "PipelineRunResponseModel",
    "PipelineRunUpdateModel",
    "ProjectRequestModel",
    "ProjectResponseModel",
    "ProjectUpdateModel",
    "ProjectFilterModel",
    "RoleAssignmentRequestModel",
    "RoleAssignmentResponseModel",
    "RoleAssignmentFilterModel",
    "RoleRequestModel",
    "RoleResponseModel",
    "RoleUpdateModel",
    "RoleFilterModel",
    "StackRequestModel",
    "StackResponseModel",
    "StackUpdateModel",
    "StackFilterModel",
    "StepRunRequestModel",
    "StepRunResponseModel",
    "StepRunUpdateModel",
    "TeamRequestModel",
    "TeamResponseModel",
    "TeamUpdateModel",
    "TeamFilterModel",
    "UserRequestModel",
    "UserResponseModel",
    "UserUpdateModel",
    "UserFilterModel",
    "UserAuthModel",
]
