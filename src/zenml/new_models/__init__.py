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

from zenml.new_models.artifact_models import (
    ArtifactRequestModel,
    ArtifactResponseModel,
ArtifactUpdateModel,
)
from zenml.new_models.component_models import (
    ComponentRequestModel,
    ComponentResponseModel,
    ComponentUpdateModel,
)
from zenml.new_models.flavor_models import (
    FlavorRequestModel,
    FlavorResponseModel,
)
from zenml.new_models.pipeline_models import (
    PipelineRequestModel,
    PipelineResponseModel,
    PipelineUpdateModel,
)
from zenml.new_models.pipeline_run_models import (
    PipelineRunRequestModel,
    PipelineRunResponseModel,
    PipelineRunUpdateModel,
)
from zenml.new_models.project_models import (
    ProjectRequestModel,
    ProjectResponseModel,
    ProjectUpdateModel,
)
from zenml.new_models.role_assignment_models import (
    RoleAssignmentRequestModel,
    RoleAssignmentResponseModel,
)
from zenml.new_models.role_models import (
    RoleRequestModel,
    RoleResponseModel,
    RoleUpdateModel,
)
from zenml.new_models.stack_models import (
    StackRequestModel,
    StackResponseModel,
    StackUpdateModel,
)
from zenml.new_models.step_run_models import (
    StepRunRequestModel,
    StepRunResponseModel,
    StepRunUpdateModel,
)
from zenml.new_models.team_models import TeamRequestModel, TeamResponseModel
from zenml.new_models.user_models import (
    EmailOptInModel,
    UserAuthModel,
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

__all__ = [
    "ArtifactRequestModel",
    "ArtifactResponseModel",
    "ArtifactUpdateModel",
    "ComponentRequestModel",
    "ComponentResponseModel",
    "ComponentUpdateModel",
    "FlavorRequestModel",
    "FlavorResponseModel",
    "PipelineRequestModel",
    "PipelineResponseModel",
    "PipelineUpdateModel",
    "PipelineRunRequestModel",
    "PipelineRunResponseModel",
    "PipelineRunUpdateModel",
    "ProjectRequestModel",
    "ProjectResponseModel",
    "ProjectUpdateModel",
    "RoleAssignmentRequestModel",
    "RoleAssignmentResponseModel",
    "RoleRequestModel",
    "RoleResponseModel",
    "RoleUpdateModel",
    "StackRequestModel",
    "StackResponseModel",
    "StackUpdateModel",
    "StepRunRequestModel",
    "StepRunResponseModel",
    "StepRunUpdateModel",
    "TeamRequestModel",
    "TeamResponseModel",
    "EmailOptInModel",
    "UserRequestModel",
    "UserResponseModel",
    "UserUpdateModel",
    "UserAuthModel",
]
