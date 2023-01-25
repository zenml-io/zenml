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
    ArtifactUpdateModel,
)
from zenml.models.component_models import (
    ComponentFilterModel,
    ComponentRequestModel,
    ComponentResponseModel,
    ComponentUpdateModel,
)
from zenml.models.filter_models import Filter, BaseFilterModel
from zenml.models.flavor_models import (
    FlavorFilterModel,
    FlavorRequestModel,
    FlavorResponseModel,
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
from zenml.models.project_models import (
    ProjectFilterModel,
    ProjectRequestModel,
    ProjectResponseModel,
    ProjectUpdateModel,
)
from zenml.models.role_models import (
    RoleFilterModel,
    RoleRequestModel,
    RoleResponseModel,
    RoleUpdateModel,
)
from zenml.models.schedule_model import (
    ScheduleRequestModel,
    ScheduleResponseModel,
    ScheduleUpdateModel,
    ScheduleFilterModel,
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

UserRoleAssignmentResponseModel.update_forward_refs(
    RoleResponseModel=RoleResponseModel,
    TeamResponseModel=TeamResponseModel,
    UserResponseModel=UserResponseModel,
    ProjectResponseModel=ProjectResponseModel,
)

TeamRoleAssignmentResponseModel.update_forward_refs(
    RoleResponseModel=RoleResponseModel,
    TeamResponseModel=TeamResponseModel,
    UserResponseModel=UserResponseModel,
    ProjectResponseModel=ProjectResponseModel,
)

PipelineResponseModel.update_forward_refs(
    UserResponseModel=UserResponseModel,
    ProjectResponseModel=ProjectResponseModel,
)

ScheduleResponseModel.update_forward_refs(
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
    "ArtifactFilterModel",
    "ComponentRequestModel",
    "ComponentResponseModel",
    "ComponentUpdateModel",
    "ComponentFilterModel",
    "FlavorRequestModel",
    "FlavorResponseModel",
    "FlavorFilterModel",
    "BaseFilterModel",
    "PipelineRequestModel",
    "PipelineResponseModel",
    "PipelineUpdateModel",
    "PipelineFilterModel",
    "PipelineRunRequestModel",
    "PipelineRunResponseModel",
    "PipelineRunUpdateModel",
    "PipelineRunFilterModel",
    "ProjectRequestModel",
    "ProjectResponseModel",
    "ProjectUpdateModel",
    "ProjectFilterModel",
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
    "ScheduleRequestModel",
    "ScheduleResponseModel",
    "ScheduleUpdateModel",
    "ScheduleFilterModel",
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
]
