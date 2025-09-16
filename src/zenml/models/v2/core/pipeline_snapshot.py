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
"""Pipeline snapshot models."""

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

from pydantic import Field, field_validator

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.step_configurations import Step
from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.enums import ExecutionStatus
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


class PipelineSnapshotBase(BaseZenModel):
    """Base model for pipeline snapshots."""

    run_name_template: str = Field(
        title="The run name template for runs created using this snapshot.",
    )
    pipeline_configuration: PipelineConfiguration = Field(
        title="The pipeline configuration for this snapshot."
    )
    step_configurations: Dict[str, Step] = Field(
        default={}, title="The step configurations for this snapshot."
    )
    client_environment: Dict[str, Any] = Field(
        default={}, title="The client environment for this snapshot."
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
        title="The pipeline version hash of the snapshot.",
    )
    pipeline_spec: Optional[PipelineSpec] = Field(
        default=None,
        title="The pipeline spec of the snapshot.",
    )

    @property
    def should_prevent_build_reuse(self) -> bool:
        """Whether the snapshot prevents a build reuse.

        Returns:
            Whether the snapshot prevents a build reuse.
        """
        return any(
            step.config.docker_settings.prevent_build_reuse
            for step in self.step_configurations.values()
        )


class PipelineSnapshotRequest(PipelineSnapshotBase, ProjectScopedRequest):
    """Request model for pipeline snapshots."""

    name: Optional[Union[str, bool]] = Field(
        default=None,
        title="The name of the snapshot.",
    )
    description: Optional[str] = Field(
        default=None,
        title="The description of the snapshot.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    replace: Optional[bool] = Field(
        default=None,
        title="Whether to replace the existing snapshot with the same name.",
    )
    tags: Optional[List[str]] = Field(
        default=None,
        title="Tags of the snapshot.",
    )

    stack: UUID = Field(title="The stack associated with the snapshot.")
    pipeline: UUID = Field(title="The pipeline associated with the snapshot.")
    build: Optional[UUID] = Field(
        default=None, title="The build associated with the snapshot."
    )
    schedule: Optional[UUID] = Field(
        default=None, title="The schedule associated with the snapshot."
    )
    code_reference: Optional["CodeReferenceRequest"] = Field(
        default=None,
        title="The code reference associated with the snapshot.",
    )
    code_path: Optional[str] = Field(
        default=None,
        title="Optional path where the code is stored in the artifact store.",
    )
    template: Optional[UUID] = Field(
        default=None,
        description="DEPRECATED: Template used for the snapshot.",
        deprecated=True,
    )
    source_snapshot: Optional[UUID] = Field(
        default=None,
        description="Snapshot that is the source of this snapshot.",
    )

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            if not v:
                raise ValueError("Snapshot name cannot be empty.")
            if len(v) > STR_FIELD_MAX_LENGTH:
                raise ValueError(
                    f"Snapshot name `{v}` is too long. The maximum length "
                    f"is {STR_FIELD_MAX_LENGTH} characters."
                )
        elif v is True:
            raise ValueError("Snapshot name cannot be `True`.")

        return v


# ------------------ Update Model ------------------


class PipelineSnapshotUpdate(BaseUpdate):
    """Pipeline snapshot update model."""

    name: Optional[Union[str, bool]] = Field(
        default=None,
        title="The name of the snapshot. If set to "
        "False, the name will be removed.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: Optional[str] = Field(
        default=None,
        title="The description of the snapshot.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    replace: Optional[bool] = Field(
        default=None,
        title="Whether to replace the existing snapshot with the same name.",
    )
    add_tags: Optional[List[str]] = Field(
        default=None, title="New tags to add to the snapshot."
    )
    remove_tags: Optional[List[str]] = Field(
        default=None, title="Tags to remove from the snapshot."
    )

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            if not v:
                raise ValueError("Snapshot name cannot be empty.")
            if len(v) > STR_FIELD_MAX_LENGTH:
                raise ValueError(
                    f"Snapshot name `{v}` is too long. The maximum length "
                    f"is {STR_FIELD_MAX_LENGTH} characters."
                )
        elif v is True:
            raise ValueError("Snapshot name cannot be `True`.")

        return v


# ------------------ Response Model ------------------


class PipelineSnapshotResponseBody(ProjectScopedResponseBody):
    """Response body for pipeline snapshots."""

    runnable: bool = Field(
        title="If a run can be started from the snapshot.",
    )


class PipelineSnapshotResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for pipeline snapshots."""

    __zenml_skip_dehydration__: ClassVar[List[str]] = [
        "pipeline_configuration",
        "step_configurations",
        "client_environment",
        "pipeline_spec",
    ]

    description: Optional[str] = Field(
        default=None,
        title="The description of the snapshot.",
    )
    run_name_template: str = Field(
        title="The run name template for runs created using this snapshot.",
    )
    pipeline_configuration: PipelineConfiguration = Field(
        title="The pipeline configuration for this snapshot."
    )
    step_configurations: Dict[str, Step] = Field(
        default={}, title="The step configurations for this snapshot."
    )
    client_environment: Dict[str, Any] = Field(
        default={}, title="The client environment for this snapshot."
    )
    client_version: Optional[str] = Field(
        title="The version of the ZenML installation on the client side."
    )
    server_version: Optional[str] = Field(
        title="The version of the ZenML installation on the server side."
    )
    pipeline_version_hash: Optional[str] = Field(
        default=None, title="The pipeline version hash of the snapshot."
    )
    pipeline_spec: Optional[PipelineSpec] = Field(
        default=None, title="The pipeline spec of the snapshot."
    )
    code_path: Optional[str] = Field(
        default=None,
        title="Optional path where the code is stored in the artifact store.",
    )
    pipeline: PipelineResponse = Field(
        title="The pipeline associated with the snapshot."
    )
    stack: Optional[StackResponse] = Field(
        default=None, title="The stack associated with the snapshot."
    )
    build: Optional[PipelineBuildResponse] = Field(
        default=None,
        title="The pipeline build associated with the snapshot.",
    )
    schedule: Optional[ScheduleResponse] = Field(
        default=None, title="The schedule associated with the snapshot."
    )
    code_reference: Optional[CodeReferenceResponse] = Field(
        default=None,
        title="The code reference associated with the snapshot.",
    )
    template_id: Optional[UUID] = Field(
        default=None,
        description="Template from which this snapshot was created.",
        deprecated=True,
    )
    source_snapshot_id: Optional[UUID] = Field(
        default=None,
        description="Snapshot that is the source of this snapshot.",
    )
    config_template: Optional[Dict[str, Any]] = Field(
        default=None, title="Run configuration template."
    )
    config_schema: Optional[Dict[str, Any]] = Field(
        default=None, title="Run configuration schema."
    )


class PipelineSnapshotResponseResources(ProjectScopedResponseResources):
    """Run snapshot resources."""

    tags: List[TagResponse] = Field(
        default=[],
        title="Tags associated with the snapshot.",
    )
    latest_run_id: Optional[UUID] = Field(
        default=None,
        title="The ID of the latest run of the snapshot.",
    )
    latest_run_status: Optional[ExecutionStatus] = Field(
        default=None,
        title="The status of the latest run of the snapshot.",
    )


class PipelineSnapshotResponse(
    ProjectScopedResponse[
        PipelineSnapshotResponseBody,
        PipelineSnapshotResponseMetadata,
        PipelineSnapshotResponseResources,
    ]
):
    """Response model for pipeline snapshots."""

    name: Optional[str] = Field(
        default=None,
        title="The name of the snapshot.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "PipelineSnapshotResponse":
        """Return the hydrated version of this pipeline snapshot.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_snapshot(self.id)

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
    def pipeline(self) -> PipelineResponse:
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

    @property
    def source_snapshot_id(self) -> Optional[UUID]:
        """The `source_snapshot_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().source_snapshot_id

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

    @property
    def tags(self) -> List[TagResponse]:
        """The `tags` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().tags

    @property
    def latest_run_id(self) -> Optional[UUID]:
        """The `latest_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().latest_run_id

    @property
    def latest_run_status(self) -> Optional[ExecutionStatus]:
        """The `latest_run_status` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().latest_run_status


# ------------------ Filter Model ------------------


class PipelineSnapshotFilter(ProjectScopedFilter, TaggableFilter):
    """Model for filtering pipeline snapshots."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ProjectScopedFilter.FILTER_EXCLUDE_FIELDS,
        *TaggableFilter.FILTER_EXCLUDE_FIELDS,
        "named_only",
        "pipeline",
        "stack",
        "runnable",
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
        description="Name of the snapshot.",
    )
    named_only: Optional[bool] = Field(
        default=None,
        description="Whether to only return snapshots with a name.",
    )
    pipeline: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Pipeline associated with the snapshot.",
        union_mode="left_to_right",
    )
    stack: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Stack associated with the snapshot.",
        union_mode="left_to_right",
    )
    build_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Build associated with the snapshot.",
        union_mode="left_to_right",
    )
    schedule_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Schedule associated with the snapshot.",
        union_mode="left_to_right",
    )
    source_snapshot_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Source snapshot used for the snapshot.",
        union_mode="left_to_right",
    )
    runnable: Optional[bool] = Field(
        default=None,
        description="Whether the snapshot is runnable.",
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
        from sqlmodel import and_, col

        from zenml.zen_stores.schemas import (
            PipelineBuildSchema,
            PipelineSchema,
            PipelineSnapshotSchema,
            StackSchema,
        )

        custom_filters = super().get_custom_filters(table)

        if self.named_only:
            custom_filters.append(
                col(PipelineSnapshotSchema.name).is_not(None)
            )

        if self.pipeline:
            pipeline_filter = and_(
                PipelineSnapshotSchema.pipeline_id == PipelineSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.pipeline, table=PipelineSchema
                ),
            )
            custom_filters.append(pipeline_filter)

        if self.stack:
            stack_filter = and_(
                PipelineSnapshotSchema.stack_id == StackSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.stack,
                    table=StackSchema,
                ),
            )
            custom_filters.append(stack_filter)

        if self.runnable is True:
            runnable_filter = and_(
                # The following condition is not perfect as it does not
                # consider stacks with custom flavor components or local
                # components, but the best we can do currently with our
                # table columns.
                PipelineSnapshotSchema.build_id == PipelineBuildSchema.id,
                col(PipelineBuildSchema.is_local).is_(False),
                col(PipelineBuildSchema.stack_id).is_not(None),
            )

            custom_filters.append(runnable_filter)

        return custom_filters


# ------------------ Trigger Model ------------------


class PipelineSnapshotRunRequest(BaseZenModel):
    """Request model for running a pipeline snapshot."""

    run_configuration: Optional[PipelineRunConfiguration] = Field(
        default=None,
        title="The run configuration for the snapshot.",
    )
    step_run: Optional[UUID] = Field(
        default=None,
        title="The ID of the step run that ran the snapshot.",
    )
