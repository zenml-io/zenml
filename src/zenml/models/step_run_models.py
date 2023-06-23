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
"""Models representing steps of pipeline runs."""

from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.config.step_configurations import StepConfiguration, StepSpec
from zenml.enums import ExecutionStatus
from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.models.filter_models import WorkspaceScopedFilterModel
from zenml.models.logs_models import LogsRequestModel, LogsResponseModel

if TYPE_CHECKING:
    from zenml.models import (
        ArtifactResponseModel,
        PipelineRunResponseModel,
        RunMetadataResponseModel,
    )


# ---- #
# BASE #
# ---- #


class StepRunBaseModel(BaseModel):
    """Base model for step runs."""

    name: str = Field(
        title="The name of the pipeline run step.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    config: StepConfiguration = Field(title="The configuration of the step.")
    spec: StepSpec = Field(title="The spec of the step.")
    pipeline_run_id: UUID = Field(
        title="The ID of the pipeline run that this step run belongs to.",
    )
    original_step_run_id: Optional[UUID] = Field(
        title="The ID of the original step run if this step was cached.",
        default=None,
    )
    status: ExecutionStatus = Field(title="The status of the step.")
    parent_step_ids: List[UUID] = Field(
        title="The IDs of the parent steps of this step run.",
        default_factory=list,
    )
    cache_key: Optional[str] = Field(
        title="The cache key of the step run.",
        default=None,
        max_length=STR_FIELD_MAX_LENGTH,
    )
    docstring: Optional[str] = Field(
        title="The docstring of the step function or class.",
        default=None,
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    source_code: Optional[str] = Field(
        title="The source code of the step function or class.",
        default=None,
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    start_time: Optional[datetime] = Field(
        title="The start time of the step run.",
        default=None,
    )
    end_time: Optional[datetime] = Field(
        title="The end time of the step run.",
        default=None,
    )


# -------- #
# RESPONSE #
# -------- #


class StepRunResponseModel(StepRunBaseModel, WorkspaceScopedResponseModel):
    """Response model for step runs."""

    inputs: Dict[str, "ArtifactResponseModel"] = Field(
        title="The input artifacts of the step run.",
        default={},
    )
    outputs: Dict[str, "ArtifactResponseModel"] = Field(
        title="The output artifacts of the step run.",
        default={},
    )
    metadata: Dict[str, "RunMetadataResponseModel"] = Field(
        title="Metadata associated with this step run.",
        default={},
    )
    logs: Optional["LogsResponseModel"] = Field(
        title="Logs associated with this step run.",
        default=None,
    )

    @property
    def run(self) -> "PipelineRunResponseModel":
        """Returns the pipeline run that this step run belongs to.

        Returns:
            The pipeline run.
        """
        from zenml.client import Client

        return Client().get_pipeline_run(self.pipeline_run_id)

    @property
    def parent_steps(self) -> List["StepRunResponseModel"]:
        """Returns the parent (upstream) steps of this step run.

        Returns:
            The parent steps.
        """
        from zenml.client import Client

        return [
            Client().get_run_step(step_id) for step_id in self.parent_step_ids
        ]

    @property
    def input(self) -> "ArtifactResponseModel":
        """Returns the input artifact that was used to run this step.

        Returns:
            The input artifact.

        Raises:
            ValueError: If there were zero or multiple inputs to this step.
        """
        if not self.inputs:
            raise ValueError(f"Step {self.name} has no inputs.")
        if len(self.inputs) > 1:
            raise ValueError(
                f"Step {self.name} has multiple inputs, so `Step.input` is "
                "ambiguous. Please use `Step.inputs` instead."
            )
        return next(iter(self.inputs.values()))

    @property
    def output(self) -> "ArtifactResponseModel":
        """Returns the output artifact that was written by this step.

        Returns:
            The output artifact.

        Raises:
            ValueError: If there were zero or multiple step outputs.
        """
        if not self.outputs:
            raise ValueError(f"Step {self.name} has no outputs.")
        if len(self.outputs) > 1:
            raise ValueError(
                f"Step {self.name} has multiple outputs, so `Step.output` is "
                "ambiguous. Please use `Step.outputs` instead."
            )
        return next(iter(self.outputs.values()))


# ------ #
# FILTER #
# ------ #


class StepRunFilterModel(WorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all Artifacts."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the step run",
    )
    entrypoint_name: Optional[str] = Field(
        default=None,
        description="Entrypoint name of the step run",
    )
    code_hash: Optional[str] = Field(
        default=None,
        description="Code hash for this step run",
    )
    cache_key: Optional[str] = Field(
        default=None,
        description="Cache key for this step run",
    )
    status: Optional[str] = Field(
        default=None,
        description="Status of the Step Run",
    )
    start_time: Optional[Union[datetime, str]] = Field(
        default=None, description="Start time for this run"
    )
    end_time: Optional[Union[datetime, str]] = Field(
        default=None, description="End time for this run"
    )
    pipeline_run_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Pipeline run of this step run"
    )
    original_step_run_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Original id for this step run"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="User that produced this step run"
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Workspace of this step run"
    )
    num_outputs: Optional[int] = Field(
        default=None,
        description="Amount of outputs for this Step Run",
    )


# ------- #
# REQUEST #
# ------- #


class StepRunRequestModel(StepRunBaseModel, WorkspaceScopedRequestModel):
    """Request model for step runs."""

    inputs: Dict[str, UUID] = Field(
        title="The IDs of the input artifacts of the step run.",
        default={},
    )
    outputs: Dict[str, UUID] = Field(
        title="The IDs of the output artifacts of the step run.",
        default={},
    )
    logs: Optional["LogsRequestModel"] = Field(
        title="Logs associated with this step run.",
        default=None,
    )


# ------ #
# UPDATE #
# ------ #


class StepRunUpdateModel(BaseModel):
    """Update model for step runs."""

    outputs: Dict[str, UUID] = Field(
        title="The IDs of the output artifacts of the step run.",
        default={},
    )
    status: Optional[ExecutionStatus] = Field(
        title="The status of the step.",
        default=None,
    )
    end_time: Optional[datetime] = Field(
        title="The end time of the step run.",
        default=None,
    )
