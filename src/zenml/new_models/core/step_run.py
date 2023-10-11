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
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.config.step_configurations import StepConfiguration, StepSpec
from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.enums import ExecutionStatus
from zenml.new_models.base import (
    BaseRequest,
    BaseResponse,
    BaseResponseMetadata,
    hydrated_property,
)

if TYPE_CHECKING:
    from zenml.new_models.core.artifact import ArtifactResponse
    from zenml.new_models.core.logs import (
        LogsRequest,
        LogsResponse,
    )
    from zenml.new_models.core.run_metadata import (
        RunMetadataResponse,
    )


# ------------------ Request Model ------------------


class StepRunRequest(BaseRequest):
    """Request model for step runs."""

    name: str = Field(
        title="The name of the pipeline run step.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    start_time: Optional[datetime] = Field(
        title="The start time of the step run.",
        default=None,
    )
    end_time: Optional[datetime] = Field(
        title="The end time of the step run.",
        default=None,
    )
    status: ExecutionStatus = Field(title="The status of the step.")
    cache_key: Optional[str] = Field(
        title="The cache key of the step run.",
        default=None,
        max_length=STR_FIELD_MAX_LENGTH,
    )
    code_hash: Optional[str] = Field(
        title="The code hash of the step run.",
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
    pipeline_run_id: UUID = Field(
        title="The ID of the pipeline run that this step run belongs to.",
    )

    original_step_run_id: Optional[UUID] = Field(
        title="The ID of the original step run if this step was cached.",
        default=None,
    )
    parent_step_ids: List[UUID] = Field(
        title="The IDs of the parent steps of this step run.",
        default_factory=list,
    )

    inputs: Dict[str, UUID] = Field(
        title="The IDs of the input artifacts of the step run.",
        default={},
    )
    outputs: Dict[str, UUID] = Field(
        title="The IDs of the output artifacts of the step run.",
        default={},
    )
    logs: Optional["LogsRequest"] = Field(
        title="Logs associated with this step run.",
        default=None,
    )
    deployment: UUID = Field(
        title="The deployment associated with the step run."
    )
    code_hash: Optional[str]


# ------------------ Update Model ------------------


class StepRunUpdate(BaseModel):
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


# ------------------ Response Model ------------------


class StepRunResponseMetadata(BaseResponseMetadata):
    """Response metadata model for step runs/"""

    # Configuration
    config: "StepConfiguration" = Field(title="The configuration of the step.")
    spec: "StepSpec" = Field(title="The spec of the step.")

    # Code related fields
    cache_key: Optional[str] = Field(
        title="The cache key of the step run.",
        default=None,
        max_length=STR_FIELD_MAX_LENGTH,
    )
    code_hash: Optional[str] = Field(
        title="The code hash of the step run.",
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

    # Timestamps
    start_time: Optional[datetime] = Field(
        title="The start time of the step run.",
        default=None,
    )
    end_time: Optional[datetime] = Field(
        title="The end time of the step run.",
        default=None,
    )

    # References
    logs: Optional["LogsResponse"] = Field(
        title="Logs associated with this step run.",
        default=None,
    )
    deployment_id: UUID = Field(
        title="The deployment associated with the step run."
    )
    pipeline_run_id: UUID = Field(
        title="The ID of the pipeline run that this step run belongs to.",
    )
    original_step_run_id: Optional[UUID] = Field(
        title="The ID of the original step run if this step was cached.",
        default=None,
    )
    parent_step_ids: List[UUID] = Field(
        title="The IDs of the parent steps of this step run.",
        default_factory=list,
    )
    run_metadata: Dict[str, "RunMetadataResponse"] = Field(
        title="Metadata associated with this step run.",
        default={},
    )


class StepRunResponse(BaseResponse):
    """Response model for step runs."""

    # Entity fields
    name: str = Field(
        title="The name of the pipeline run step.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    status: ExecutionStatus = Field(title="The status of the step.")

    inputs: Dict[str, "ArtifactResponse"] = Field(
        title="The input artifacts of the step run.",
        default={},
    )
    outputs: Dict[str, "ArtifactResponse"] = Field(
        title="The output artifacts of the step run.",
        default={},
    )

    # Metadata related field, method and properties
    metadata: Optional["StepRunResponseMetadata"]

    def get_hydrated_version(self) -> "StepRunResponse":
        # TODO: Implement it with the parameterized calls
        from zenml.client import Client

        return Client().get_run_step(self.id, hydrate=True)

    @hydrated_property
    def config(self):
        """The config property of the instance."""
        return self.metadata.config

    @hydrated_property
    def spec(self):
        """The spec property of the instance."""
        return self.metadata.spec

    @hydrated_property
    def cache_key(self):
        """The cache_key property of the instance."""
        return self.metadata.cache_key

    @hydrated_property
    def code_hash(self):
        """The code_hash property of the instance."""
        return self.metadata.code_hash

    @hydrated_property
    def docstring(self):
        """The docstring property of the instance."""
        return self.metadata.docstring

    @hydrated_property
    def source_code(self):
        """The source_code property of the instance."""
        return self.metadata.source_code

    @hydrated_property
    def start_time(self):
        """The start_time property of the instance."""
        return self.metadata.start_time

    @hydrated_property
    def end_time(self):
        """The end_time property of the instance."""
        return self.metadata.end_time

    @hydrated_property
    def logs(self):
        """The logs property of the instance."""
        return self.metadata.logs

    @hydrated_property
    def deployment_id(self):
        """The deployment_id property of the instance."""
        return self.metadata.deployment_id

    @hydrated_property
    def pipeline_run_id(self):
        """The pipeline_run_id property of the instance."""
        return self.metadata.pipeline_run_id

    @hydrated_property
    def original_step_run_id(self):
        """The original_step_run_id property of the instance."""
        return self.metadata.original_step_run_id

    @hydrated_property
    def parent_step_ids(self):
        """The parent_step_ids property of the instance."""
        return self.metadata.parent_step_ids

    @hydrated_property
    def run_metadata(self):
        """The metadata property of the instance."""
        return self.metadata.run_metadata

    # Helper properties

    @property
    def input(self) -> "ArtifactResponse":
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
    def output(self) -> "ArtifactResponse":
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
