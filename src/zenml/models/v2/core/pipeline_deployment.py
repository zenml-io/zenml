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

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

from pydantic import Field

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.step_configurations import Step
from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import BaseUpdate, BaseZenModel
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
    TaggableFilter,
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
from zenml.models.v2.core.tag import TagResponse

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.zen_stores.schemas.base_schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)


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
    client_environment: Dict[str, Any] = Field(
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


class PipelineDeploymentRequest(PipelineDeploymentBase, ProjectScopedRequest):
    """Request model for pipeline deployments."""

    name: Optional[str] = Field(
        default=None,
        title="The name of the deployment.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: Optional[str] = Field(
        default=None,
        title="The description of the deployment.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    tags: Optional[List[str]] = Field(
        default=None,
        title="Tags of the deployment.",
    )

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
    source_deployment: Optional[UUID] = Field(
        default=None,
        description="Deployment that is the source of this deployment.",
    )


# ------------------ Update Model ------------------


class PipelineDeploymentUpdate(BaseUpdate):
    """Pipeline deployment update model."""

    name: Optional[str] = Field(
        default=None,
        title="The name of the deployment.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: Optional[str] = Field(
        default=None,
        title="The description of the deployment.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    add_tags: Optional[List[str]] = Field(
        default=None, title="New tags to add to the deployment."
    )
    remove_tags: Optional[List[str]] = Field(
        default=None, title="Tags to remove from the deployment."
    )


# ------------------ Response Model ------------------


class PipelineDeploymentResponseBody(ProjectScopedResponseBody):
    """Response body for pipeline deployments."""

    runnable: bool = Field(
        title="If a run can be started from the deployment.",
    )


class PipelineDeploymentResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for pipeline deployments."""

    __zenml_skip_dehydration__: ClassVar[List[str]] = [
        "pipeline_configuration",
        "step_configurations",
        "client_environment",
        "pipeline_spec",
    ]

    description: Optional[str] = Field(
        default=None,
        title="The description of the deployment.",
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
    client_environment: Dict[str, Any] = Field(
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
    source_deployment_id: Optional[UUID] = Field(
        default=None,
        description="Deployment that is the source of this deployment.",
    )
    config_template: Optional[Dict[str, Any]] = Field(
        default=None, title="Run configuration template."
    )
    config_schema: Optional[Dict[str, Any]] = Field(
        default=None, title="Run configuration schema."
    )


class PipelineDeploymentResponseResources(ProjectScopedResponseResources):
    """Class for all resource models associated with the pipeline deployment entity."""

    tags: List[TagResponse] = Field(
        title="Tags associated with the run template.",
    )


class PipelineDeploymentResponse(
    ProjectScopedResponse[
        PipelineDeploymentResponseBody,
        PipelineDeploymentResponseMetadata,
        PipelineDeploymentResponseResources,
    ]
):
    """Response model for pipeline deployments."""

    name: Optional[str] = Field(
        default=None,
        title="The name of the deployment.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "PipelineDeploymentResponse":
        """Return the hydrated version of this pipeline deployment.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_deployment(self.id)

    # Body and metadata properties
    @property
    def runnable(self) -> bool:
        """The `runnable` property.

        Returns:
            the value of the property.
        """
        return self.get_body().runnable

    @property
    def description(self) -> Optional[str]:
        """The `description` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().description

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
    def client_environment(self) -> Dict[str, Any]:
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
    def source_deployment_id(self) -> Optional[UUID]:
        """The `source_deployment_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().source_deployment_id

    @property
    def config_schema(self) -> Optional[Dict[str, Any]]:
        """The `config_schema` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().config_schema

    @property
    def config_template(self) -> Optional[Dict[str, Any]]:
        """The `config_template` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().config_template


# ------------------ Filter Model ------------------


class PipelineDeploymentFilter(ProjectScopedFilter, TaggableFilter):
    """Model for filtering pipeline deployments."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ProjectScopedFilter.FILTER_EXCLUDE_FIELDS,
        *TaggableFilter.FILTER_EXCLUDE_FIELDS,
        "named_only",
    ]
    CUSTOM_SORTING_OPTIONS = [
        *ProjectScopedFilter.CUSTOM_SORTING_OPTIONS,
        *TaggableFilter.CUSTOM_SORTING_OPTIONS,
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ProjectScopedFilter.CLI_EXCLUDE_FIELDS,
        *TaggableFilter.CLI_EXCLUDE_FIELDS,
    ]

    name: Optional[str] = Field(
        default=None,
        description="Name of the deployment.",
    )
    named_only: Optional[bool] = Field(
        default=None,
        description="Whether to only return deployments with a name.",
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

    def get_custom_filters(
        self, table: Type["AnySchema"]
    ) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        Args:
            table: The query table.

        Returns:
            A list of custom filters.
        """
        from sqlmodel import col

        from zenml.zen_stores.schemas import (
            PipelineDeploymentSchema,
        )

        custom_filters = super().get_custom_filters(table)

        if self.named_only:
            custom_filters.append(
                col(PipelineDeploymentSchema.name).is_not(None)
            )

        return custom_filters
