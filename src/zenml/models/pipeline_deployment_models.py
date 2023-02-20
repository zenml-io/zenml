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
"""Models representing pipeline deployments."""

from typing import TYPE_CHECKING, Dict, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step
from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
)
from zenml.models.filter_models import WorkspaceScopedFilterModel

if TYPE_CHECKING:
    from zenml.models import (
        PipelineBuildResponseModel,
        PipelineResponseModel,
        ScheduleResponseModel,
        StackResponseModel,
    )

# ---- #
# BASE #
# ---- #


class PipelineDeploymentBaseModel(BaseModel):
    """Base model for pipeline deployments."""

    run_name_template: str = Field(
        title="The run name template for runs created using this deployment.",
    )
    pipeline_configuration: PipelineConfiguration = Field(
        title="The pipeline configuration for this deployment."
    )
    step_configurations: Dict[str, Step] = Field(
        default={}, title="The step configurations for this deployment."
    )
    client_environment: Dict[str, str] = Field(
        default={}, title="The client environment for this deployment."
    )


# -------- #
# RESPONSE #
# -------- #


class PipelineDeploymentResponseModel(
    PipelineDeploymentBaseModel, WorkspaceScopedResponseModel
):
    """Response model for pipeline deployments."""

    pipeline: Optional["PipelineResponseModel"] = Field(
        title="The pipeline associated with the deployment."
    )
    stack: Optional["StackResponseModel"] = Field(
        title="The stack associated with the deployment."
    )
    build: Optional["PipelineBuildResponseModel"] = Field(
        title="The pipeline build associated with the deployment."
    )
    schedule: Optional["ScheduleResponseModel"] = Field(
        title="The schedule associated with the deployment."
    )


# ------ #
# FILTER #
# ------ #


class PipelineDeploymentFilterModel(WorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all pipeline deployments."""

    workspace_id: Union[UUID, str, None] = Field(
        description="Workspace for this deployment."
    )
    user_id: Union[UUID, str, None] = Field(
        description="User that created this deployment."
    )
    pipeline_id: Union[UUID, str, None] = Field(
        description="Pipeline associated with the deployment."
    )
    stack_id: Union[UUID, str, None] = Field(
        description="Stack associated with the deployment."
    )
    build_id: Union[UUID, str, None] = Field(
        description="Build associated with the deployment."
    )
    schedule_id: Union[UUID, str, None] = Field(
        description="Schedule associated with the deployment."
    )


# ------- #
# REQUEST #
# ------- #


class PipelineDeploymentRequestModel(
    PipelineDeploymentBaseModel, WorkspaceScopedRequestModel
):
    """Request model for pipeline deployments."""

    stack: UUID = Field(title="The stack associated with the deployment.")
    pipeline: Optional[UUID] = Field(
        title="The pipeline associated with the deployment."
    )
    build: Optional[UUID] = Field(
        title="The build associated with the deployment."
    )
    schedule: Optional[UUID] = Field(
        title="The schedule associated with the deployment."
    )
