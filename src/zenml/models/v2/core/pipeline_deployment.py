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

from typing import Dict, Optional, TypeVar, Union
from uuid import UUID

from pydantic import Field

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.step_configurations import Step
from zenml.models.v2.base.base import BaseZenModel
from zenml.models.v2.base.page import Page
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
)
from zenml.models.v2.core.code_reference import (
    CodeReferenceRequest,
    CodeReferenceResponse,
)
from zenml.models.v2.core.pipeline import PipelineResponse
from zenml.models.v2.core.pipeline_build import (
    PipelineBuildResponse,
)
from zenml.models.v2.core.schedule import ScheduleResponse
from zenml.models.v2.core.stack import StackResponse
from zenml.models.v2.core.trigger import TriggerResponse

TriggerPage = TypeVar("TriggerPage", bound=Page[TriggerResponse])

# ------------------ Request Model ------------------


class PipelineDeploymentBase(BaseZenModel):
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
    client_version: Optional[str] = Field(
        default=None,
        title="The version of the ZenML installation on the client side.",
    )
    server_version: Optional[str] = Field(
        default=None,
        title="The version of the ZenML installation on the server side.",
    )
    pipeline_version_hash: Optional[str] = Field(
        default=None,
        title="The pipeline version hash of the deployment.",
    )
    pipeline_spec: Optional[PipelineSpec] = Field(
        default=None,
        title="The pipeline spec of the deployment.",
    )

    @property
    def should_prevent_build_reuse(self) -> bool:
        """Whether the deployment prevents a build reuse.

        Returns:
            Whether the deployment prevents a build reuse.
        """
        return any(
            step.config.docker_settings.prevent_build_reuse
            for step in self.step_configurations.values()
        )


class PipelineDeploymentRequest(
    PipelineDeploymentBase, WorkspaceScopedRequest
):
    """Request model for pipeline deployments."""

    stack: UUID = Field(title="The stack associated with the deployment.")
    pipeline: Optional[UUID] = Field(
        default=None, title="The pipeline associated with the deployment."
    )
    build: Optional[UUID] = Field(
        default=None, title="The build associated with the deployment."
    )
    schedule: Optional[UUID] = Field(
        default=None, title="The schedule associated with the deployment."
    )
    code_reference: Optional["CodeReferenceRequest"] = Field(
        default=None,
        title="The code reference associated with the deployment.",
    )
    code_path: Optional[str] = Field(
        default=None,
        title="Optional path where the code is stored in the artifact store.",
    )
    template: Optional[UUID] = Field(
        default=None,
        description="Template used for the deployment.",
    )


# ------------------ Update Model ------------------

# There is no update model for pipeline deployments.

# ------------------ Response Model ------------------


class PipelineDeploymentResponseBody(WorkspaceScopedResponseBody):
    """Response body for pipeline deployments."""


class PipelineDeploymentResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for pipeline deployments."""

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
    client_version: Optional[str] = Field(
        title="The version of the ZenML installation on the client side."
    )
    server_version: Optional[str] = Field(
        title="The version of the ZenML installation on the server side."
    )
    pipeline_version_hash: Optional[str] = Field(
        default=None, title="The pipeline version hash of the deployment."
    )
    pipeline_spec: Optional[PipelineSpec] = Field(
        default=None, title="The pipeline spec of the deployment."
    )
    code_path: Optional[str] = Field(
        default=None,
        title="Optional path where the code is stored in the artifact store.",
    )

    pipeline: Optional[PipelineResponse] = Field(
        default=None, title="The pipeline associated with the deployment."
    )
    stack: Optional[StackResponse] = Field(
        default=None, title="The stack associated with the deployment."
    )
    build: Optional[PipelineBuildResponse] = Field(
        default=None,
        title="The pipeline build associated with the deployment.",
    )
    schedule: Optional[ScheduleResponse] = Field(
        default=None, title="The schedule associated with the deployment."
    )
    code_reference: Optional[CodeReferenceResponse] = Field(
        default=None,
        title="The code reference associated with the deployment.",
    )
    template_id: Optional[UUID] = Field(
        default=None,
        description="Template used for the pipeline run.",
    )


class PipelineDeploymentResponseResources(WorkspaceScopedResponseResources):
    """Class for all resource models associated with the pipeline deployment entity."""

    triggers: TriggerPage = Field(  # type: ignore[valid-type]
        title="The triggers configured with this event source.",
    )


class PipelineDeploymentResponse(
    WorkspaceScopedResponse[
        PipelineDeploymentResponseBody,
        PipelineDeploymentResponseMetadata,
        PipelineDeploymentResponseResources,
    ]
):
    """Response model for pipeline deployments."""

    def get_hydrated_version(self) -> "PipelineDeploymentResponse":
        """Return the hydrated version of this pipeline deployment.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_deployment(self.id)

    # Body and metadata properties
    @property
    def run_name_template(self) -> str:
        """The `run_name_template` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().run_name_template

    @property
    def pipeline_configuration(self) -> PipelineConfiguration:
        """The `pipeline_configuration` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().pipeline_configuration

    @property
    def step_configurations(self) -> Dict[str, Step]:
        """The `step_configurations` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().step_configurations

    @property
    def client_environment(self) -> Dict[str, str]:
        """The `client_environment` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().client_environment

    @property
    def client_version(self) -> Optional[str]:
        """The `client_version` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().client_version

    @property
    def server_version(self) -> Optional[str]:
        """The `server_version` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().server_version

    @property
    def pipeline_version_hash(self) -> Optional[str]:
        """The `pipeline_version_hash` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().pipeline_version_hash

    @property
    def pipeline_spec(self) -> Optional[PipelineSpec]:
        """The `pipeline_spec` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().pipeline_spec

    @property
    def code_path(self) -> Optional[str]:
        """The `code_path` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().code_path

    @property
    def pipeline(self) -> Optional[PipelineResponse]:
        """The `pipeline` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().pipeline

    @property
    def stack(self) -> Optional[StackResponse]:
        """The `stack` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().stack

    @property
    def build(self) -> Optional[PipelineBuildResponse]:
        """The `build` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().build

    @property
    def schedule(self) -> Optional[ScheduleResponse]:
        """The `schedule` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().schedule

    @property
    def code_reference(self) -> Optional[CodeReferenceResponse]:
        """The `code_reference` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().code_reference

    @property
    def template_id(self) -> Optional[UUID]:
        """The `template_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().template_id


# ------------------ Filter Model ------------------


class PipelineDeploymentFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all pipeline deployments."""

    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Workspace for this deployment.",
        union_mode="left_to_right",
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="User that created this deployment.",
        union_mode="left_to_right",
    )
    pipeline_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Pipeline associated with the deployment.",
        union_mode="left_to_right",
    )
    stack_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Stack associated with the deployment.",
        union_mode="left_to_right",
    )
    build_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Build associated with the deployment.",
        union_mode="left_to_right",
    )
    schedule_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Schedule associated with the deployment.",
        union_mode="left_to_right",
    )
    template_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Template used as base for the deployment.",
        union_mode="left_to_right",
    )
