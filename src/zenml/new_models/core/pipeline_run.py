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
"""Models representing pipeline runs."""

from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import ExecutionStatus
from zenml.new_models.base import (
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    hydrated_property,
)

if TYPE_CHECKING:
    from zenml.new_models.core.artifact import ArtifactResponse
    from zenml.new_models.core.pipeline import PipelineResponse
    from zenml.new_models.core.pipeline_build import (
        PipelineBuildResponse,
    )
    from zenml.new_models.core.run_metadata import (
        RunMetadataResponse,
    )
    from zenml.new_models.core.schedule import ScheduleResponse
    from zenml.new_models.core.stack import StackResponse
    from zenml.new_models.core.step_run import StepRunResponse

# ------------------ Request Model ------------------


class PipelineRunRequest(WorkspaceScopedRequest):
    """Request model for pipeline runs."""

    id: UUID
    name: str = Field(
        title="The name of the pipeline run.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    deployment: UUID = Field(
        title="The deployment associated with the pipeline run."
    )
    pipeline: Optional[UUID] = Field(
        title="The pipeline associated with the pipeline run."
    )
    orchestrator_run_id: Optional[str] = Field(
        title="The orchestrator run ID.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    start_time: Optional[datetime] = Field(
        title="The start time of the pipeline run.",
        default=None,
    )
    end_time: Optional[datetime] = Field(
        title="The end time of the pipeline run.",
        default=None,
    )
    status: ExecutionStatus = Field(
        title="The status of the pipeline run.",
    )
    client_environment: Dict[str, str] = Field(
        default={},
        title=(
            "Environment of the client that initiated this pipeline run "
            "(OS, Python version, etc.)."
        ),
    )
    orchestrator_environment: Dict[str, str] = Field(
        default={},
        title=(
            "Environment of the orchestrator that executed this pipeline run "
            "(OS, Python version, etc.)."
        ),
    )


# ------------------ Update Model ------------------


class PipelineRunUpdate(BaseModel):
    """Pipeline run update model."""

    status: Optional[ExecutionStatus] = None
    end_time: Optional[datetime] = None


# ------------------ Response Model ------------------


class PipelineRunResponseBody(WorkspaceScopedResponseBody):
    """Response body for pipeline runs."""

    status: ExecutionStatus = Field(
        title="The status of the pipeline run.",
    )
    stack: Optional["StackResponse"] = Field(
        default=None, title="The stack that was used for this run."
    )
    pipeline: Optional["PipelineResponse"] = Field(
        default=None, title="The pipeline this run belongs to."
    )
    build: Optional["PipelineBuildResponse"] = Field(
        default=None, title="The pipeline build that was used for this run."
    )
    schedule: Optional["ScheduleResponse"] = Field(
        default=None, title="The schedule that was used for this run."
    )


class PipelineRunResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for pipeline runs."""

    run_metadata: Dict[str, "RunMetadataResponse"] = Field(
        default={},
        title="Metadata associated with this pipeline run.",
    )
    steps: Dict[str, "StepRunResponse"] = Field(
        default={}, title="The steps of this run."
    )
    config: PipelineConfiguration = Field(
        title="The pipeline configuration used for this pipeline run.",
    )
    start_time: Optional[datetime] = Field(
        title="The start time of the pipeline run.",
        default=None,
    )
    end_time: Optional[datetime] = Field(
        title="The end time of the pipeline run.",
        default=None,
    )
    client_environment: Dict[str, str] = Field(
        default={},
        title=(
            "Environment of the client that initiated this pipeline run "
            "(OS, Python version, etc.)."
        ),
    )
    orchestrator_environment: Dict[str, str] = Field(
        default={},
        title=(
            "Environment of the orchestrator that executed this pipeline run "
            "(OS, Python version, etc.)."
        ),
    )
    orchestrator_run_id: Optional[str] = Field(
        title="The orchestrator run ID.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )


class PipelineRunResponse(WorkspaceScopedResponse):
    """Response model for pipeline runs."""

    name: str = Field(
        title="The name of the pipeline run.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    # Body and metadata pair
    body: "PipelineRunResponseBody"
    metadata: Optional["PipelineRunResponseMetadata"]

    def get_hydrated_version(self) -> "PipelineRunResponse":
        """Get the hydrated version of this pipeline run."""
        from zenml.client import Client

        return Client().get_pipeline_run(self.id)

    # Helper methods
    @property
    def artifacts(self) -> List["ArtifactResponse"]:
        """Get all artifacts that are outputs of steps of this pipeline run.

        Returns:
            All output artifacts of this pipeline run (including cached ones).
        """
        from zenml.utils.artifact_utils import get_artifacts_of_pipeline_run

        return get_artifacts_of_pipeline_run(self)

    @property
    def produced_artifacts(self) -> List["ArtifactResponse"]:
        """Get all artifacts produced during this pipeline run.

        Returns:
            A list of all artifacts produced during this pipeline run.
        """
        from zenml.utils.artifact_utils import get_artifacts_of_pipeline_run

        return get_artifacts_of_pipeline_run(self, only_produced=True)

    # Body and metadata properties
    @property
    def status(self):
        """The `status` property."""
        return self.body.status

    @property
    def stack(self):
        """The `stack` property."""
        return self.body.stack

    @property
    def pipeline(self):
        """The `pipeline` property."""
        return self.body.pipeline

    @property
    def build(self):
        """The `build` property."""
        return self.body.build

    @property
    def schedule(self):
        """The `schedule` property."""
        return self.body.schedule

    @hydrated_property
    def run_metadata(self):
        """The `run_metadata` property"""
        return self.metadata.run_metadata

    @hydrated_property
    def steps(self):
        """The `steps` property"""
        return self.metadata.steps

    @hydrated_property
    def config(self):
        """The `config` property"""
        return self.metadata.config

    @hydrated_property
    def start_time(self):
        """The `start_time` property"""
        return self.metadata.start_time

    @hydrated_property
    def end_time(self):
        """The `end_time` property"""
        return self.metadata.end_time

    @hydrated_property
    def client_environment(self):
        """The `client_environment` property"""
        return self.metadata.client_environment

    @hydrated_property
    def orchestrator_environment(self):
        """The `orchestrator_environment` property"""
        return self.metadata.orchestrator_environment

    @hydrated_property
    def orchestrator_run_id(self):
        """The `orchestrator_run_id` property"""
        return self.metadata.orchestrator_run_id
