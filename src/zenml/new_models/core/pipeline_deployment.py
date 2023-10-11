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
"""Models representing pipeline deployments."""
from typing import TYPE_CHECKING, Dict, Optional
from uuid import UUID

from pydantic import Field

from zenml.config.docker_settings import SourceFileMode
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step
from zenml.new_models.base import (
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseMetadata,
    hydrated_property,
)

if TYPE_CHECKING:
    from zenml.new_models.core.code_reference import (
        CodeReferenceRequest,
        CodeReferenceResponse,
    )
    from zenml.new_models.core.pipeline import PipelineResponse
    from zenml.new_models.core.pipeline_build import (
        PipelineBuildResponse,
    )
    from zenml.new_models.core.schedule import ScheduleResponse
    from zenml.new_models.core.stack import StackResponse

# ------------------ Request Model ------------------


class PipelineDeploymentRequest(WorkspaceScopedRequest):
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
    code_reference: Optional["CodeReferenceRequest"] = Field(
        title="The code reference associated with the deployment."
    )

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
    client_version: str = Field(
        title="The version of the ZenML installation on the client side."
    )
    server_version: str = Field(
        title="The version of the ZenML installation on the server side."
    )

    @property
    def requires_included_files(self) -> bool:
        """Whether the deployment requires included files.

        Returns:
            Whether the deployment requires included files.
        """
        return any(
            step.config.docker_settings.source_files == SourceFileMode.INCLUDE
            for step in self.step_configurations.values()
        )

    @property
    def requires_code_download(self) -> bool:
        """Whether the deployment requires downloading some code files.

        Returns:
            Whether the deployment requires downloading some code files.
        """
        return any(
            step.config.docker_settings.source_files == SourceFileMode.DOWNLOAD
            for step in self.step_configurations.values()
        )


# ------------------ Update Model ------------------

# There is no update model for pipeline deployments.

# ------------------ Response Model ------------------


class PipelineDeploymentResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response model metadata for pipeline deployments."""

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
    client_version: str = Field(
        title="The version of the ZenML installation on the client side."
    )
    server_version: str = Field(
        title="The version of the ZenML installation on the server side."
    )
    pipeline: Optional["PipelineResponse"] = Field(
        title="The pipeline associated with the deployment."
    )
    stack: Optional["StackResponse"] = Field(
        title="The stack associated with the deployment."
    )
    build: Optional["PipelineBuildResponse"] = Field(
        title="The pipeline build associated with the deployment."
    )
    schedule: Optional["ScheduleResponse"] = Field(
        title="The schedule associated with the deployment."
    )
    code_reference: Optional["CodeReferenceResponse"] = Field(
        title="The code reference associated with the deployment."
    )


class PipelineDeploymentResponse(WorkspaceScopedResponse):
    """Response model for pipeline deployments."""

    # Metadata related field, method and properties
    metadata: Optional["PipelineDeploymentResponseMetadata"]

    def get_hydrated_version(self) -> "PipelineDeploymentResponse":
        # TODO: Implement it with the parameterized calls
        from zenml.client import Client

        return Client().get_deployment(self.id, hydrate=True)

    @hydrated_property
    def run_name_template(self):
        """The run_name_template property."""
        return self.metadata.run_name_template

    @hydrated_property
    def pipeline_configuration(self):
        """The pipeline_configuration property."""
        return self.metadata.pipeline_configuration

    @hydrated_property
    def step_configurations(self):
        """The step_configurations property."""
        return self.metadata.step_configurations

    @hydrated_property
    def client_environment(self):
        """The client_environment property."""
        return self.metadata.client_environment

    @hydrated_property
    def client_version(self):
        """The client_version property."""
        return self.metadata.client_version

    @hydrated_property
    def server_version(self):
        """The server_version property."""
        return self.metadata.server_version

    @hydrated_property
    def pipeline(self):
        """The pipeline property."""
        return self.metadata.pipeline

    @hydrated_property
    def stack(self):
        """The stack property."""
        return self.metadata.stack

    @hydrated_property
    def build(self):
        """The build property."""
        return self.metadata.build

    @hydrated_property
    def schedule(self):
        """The schedule property."""
        return self.metadata.schedule

    @hydrated_property
    def code_reference(self):
        """The code_reference property."""
        return self.metadata.code_reference
