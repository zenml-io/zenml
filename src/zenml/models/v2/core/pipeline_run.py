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

from pydantic import ConfigDict, Field, model_validator

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import ExecutionStatus, PipelineRunTriggeredByType
from zenml.metadata.metadata_types import MetadataType
from zenml.models.v2.base.base import BaseUpdate, BaseZenModel
from zenml.models.v2.base.filter import (
    DatetimeFilterOption,
    IntegerFilterOption,
    StringFilterOption,
    UUIDFilterOption,
)
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
    RunMetadataFilterMixin,
    TaggableFilter,
)
from zenml.models.v2.core.logs import LogsRequest
from zenml.models.v2.core.model_version import ModelVersionResponse
from zenml.models.v2.core.tag import TagResponse
from zenml.models.v2.misc.exception_info import ExceptionInfo
from zenml.utils import pagination_utils
from zenml.utils.tag_utils import Tag

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.models.v2.core.artifact_version import ArtifactVersionResponse
    from zenml.models.v2.core.code_reference import CodeReferenceResponse
    from zenml.models.v2.core.curated_visualization import (
        CuratedVisualizationResponse,
    )
    from zenml.models.v2.core.logs import LogsResponse
    from zenml.models.v2.core.pipeline import PipelineResponse
    from zenml.models.v2.core.pipeline_build import (
        PipelineBuildResponse,
    )
    from zenml.models.v2.core.pipeline_snapshot import PipelineSnapshotResponse
    from zenml.models.v2.core.run_wait_condition import (
        RunWaitConditionResponse,
    )
    from zenml.models.v2.core.schedule import ScheduleResponse
    from zenml.models.v2.core.stack import StackResponse
    from zenml.models.v2.core.step_run import StepRunResponse
    from zenml.models.v2.core.triggers import (
        TRIGGER_RETURN_TYPE_UNION,
        TriggerExecutionInfo,
    )
    from zenml.zen_stores.schemas.base_schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)

AnyQuery = TypeVar("AnyQuery", bound=Any)


# ------------------ Request Model ------------------


class PipelineRunTriggerInfo(BaseZenModel):
    """Trigger information model."""

    step_run_id: Optional[UUID] = Field(
        default=None,
        title="The ID of the step run that triggered the pipeline run.",
    )
    deployment_id: Optional[UUID] = Field(
        default=None,
        title="The ID of the deployment that triggered the pipeline run.",
    )


class PipelineRunRequest(ProjectScopedRequest):
    """Request model for pipeline runs."""

    name: str = Field(
        title="The name of the pipeline run.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    snapshot: UUID = Field(
        title="The snapshot associated with the pipeline run."
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
    status_reason: Optional[str] = Field(
        title="The reason for the status of the pipeline run.",
        default=None,
        max_length=STR_FIELD_MAX_LENGTH,
    )
    orchestrator_environment: Dict[str, Any] = Field(
        default={},
        title=(
            "Environment of the orchestrator that executed this pipeline run "
            "(OS, Python version, etc.)."
        ),
    )
    trigger_info: Optional[PipelineRunTriggerInfo] = Field(
        default=None,
        title="Trigger information for the pipeline run.",
    )
    tags: Optional[List[Union[str, Tag]]] = Field(
        default=None,
        title="Tags of the pipeline run.",
    )
    logs: Optional[Union[UUID, LogsRequest]] = Field(
        default=None,
        title="Logs of the pipeline run.",
    )
    exception_info: Optional[ExceptionInfo] = Field(
        default=None,
        title="The exception information of the pipeline run.",
    )
    original_run_id: Optional[UUID] = Field(
        default=None,
        title="The original run ID for a replayed run.",
    )
    parent_run_id: Optional[UUID] = Field(
        default=None,
        title="The parent run ID for a nested child pipeline run.",
    )
    child_key: Optional[str] = Field(
        default=None,
        title="Stable per-parent identifier of the child pipeline call that "
        "produced this child run.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    @property
    def is_placeholder_request(self) -> bool:
        """Whether the request is a placeholder request.

        Returns:
            Whether the request is a placeholder request.
        """
        return self.status in {
            ExecutionStatus.INITIALIZING,
            ExecutionStatus.PROVISIONING,
        }

    @model_validator(mode="after")
    def _validate_status(self) -> "PipelineRunRequest":
        """Validate the status of the pipeline run request.

        Raises:
            ValueError: If the status is not valid.

        Returns:
            The pipeline run request.
        """
        if self.status not in {
            ExecutionStatus.INITIALIZING,
            ExecutionStatus.RUNNING,
        }:
            raise ValueError(
                "Run must be started in the initializing or running state."
            )

        return self

    @model_validator(mode="after")
    def _validate_parent_child_pair(self) -> "PipelineRunRequest":
        """Ensure `parent_run_id` and `child_key` are set together.

        The unique constraint on `(parent_run_id, child_key)` does not catch
        cases where one is set and the other is `NULL` (NULLs compare unequal
        in SQL), so resume idempotency would silently break.

        Raises:
            ValueError: If only one of the two fields is set.

        Returns:
            The pipeline run request.
        """
        if self.parent_run_id is not None and self.child_key is None:
            raise ValueError(
                "`parent_run_id` is set but `child_key` is None; both "
                "must be set together."
            )
        if self.child_key is not None and self.parent_run_id is None:
            raise ValueError(
                "`child_key` is set but `parent_run_id` is None; both "
                "must be set together."
            )
        return self

    model_config = ConfigDict(protected_namespaces=())


# ------------------ Update Model ------------------


class PipelineRunUpdate(BaseUpdate):
    """Pipeline run update model."""

    status: Optional[ExecutionStatus] = None
    status_reason: Optional[str] = Field(
        default=None,
        title="The reason for the status of the pipeline run.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    orchestrator_run_id: Optional[str] = None
    exception_info: Optional[ExceptionInfo] = Field(
        default=None,
        title="The exception information of the pipeline run.",
    )
    outputs: Optional[Dict[str, UUID]] = Field(
        default=None,
        title="Pipeline output artifact version IDs keyed by output name.",
    )
    # TODO: we should maybe have a different update model here, the upper
    #  attributes should only be for internal use
    add_tags: Optional[List[str]] = Field(
        default=None, title="New tags to add to the pipeline run."
    )
    remove_tags: Optional[List[str]] = Field(
        default=None, title="Tags to remove from the pipeline run."
    )
    add_logs: Optional[List[LogsRequest]] = Field(
        default=None, title="New logs to add to the pipeline run."
    )

    model_config = ConfigDict(protected_namespaces=())


# ------------------ Response Model ------------------


class PipelineRunResponseBody(ProjectScopedResponseBody):
    """Response body for pipeline runs."""

    status: ExecutionStatus = Field(
        title="The status of the pipeline run.",
    )
    in_progress: bool = Field(
        title="Whether the pipeline run is in progress.",
    )
    status_reason: Optional[str] = Field(
        default=None,
        title="The reason for the status of the pipeline run.",
    )
    index: int = Field(
        title="The unique index of the run within the pipeline."
    )
    pipeline_id: UUID | None = Field(
        default=None,
        title="The ID of the pipeline this run is associated with.",
    )
    child_key: Optional[str] = Field(
        default=None,
        title="Stable per-parent identifier of the child pipeline call that "
        "produced this child run.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    root_run_id: Optional[UUID] = Field(
        default=None,
        title="The ID of the top-level parent run of this run's nesting tree.",
    )

    model_config = ConfigDict(protected_namespaces=())


class PipelineRunResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for pipeline runs."""

    __zenml_skip_dehydration__: ClassVar[List[str]] = [
        "run_metadata",
        "config",
        "client_environment",
        "orchestrator_environment",
    ]

    run_metadata: Dict[str, MetadataType] = Field(
        default={},
        title="Metadata associated with this pipeline run.",
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
    client_environment: Dict[str, Any] = Field(
        default={},
        title=(
            "Environment of the client that initiated this pipeline run "
            "(OS, Python version, etc.)."
        ),
    )
    orchestrator_environment: Dict[str, Any] = Field(
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
    code_path: Optional[str] = Field(
        default=None,
        title="Optional path where the code is stored in the artifact store.",
    )
    template_id: Optional[UUID] = Field(
        default=None,
        description="DEPRECATED: Template used for the pipeline run.",
        deprecated=True,
    )
    is_templatable: bool = Field(
        default=False,
        description="Whether a template can be created from this run.",
    )
    trigger_info: Optional[PipelineRunTriggerInfo] = Field(
        default=None,
        title="Trigger information for the pipeline run.",
    )
    enable_heartbeat: bool = Field(
        title="Enable heartbeat flag for run.",
    )
    exception_info: Optional[ExceptionInfo] = Field(
        default=None,
        title="The exception information of the pipeline run.",
    )
    trigger_execution_info: Optional["TriggerExecutionInfo"] = Field(
        default=None,
        title="Extra information for trigger execution like upstream_run_id etc.",
    )


class PipelineRunResponseResources(ProjectScopedResponseResources):
    """Class for all resource models associated with the pipeline run entity."""

    snapshot: Optional["PipelineSnapshotResponse"] = None
    source_snapshot: Optional["PipelineSnapshotResponse"] = None
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
    code_reference: Optional["CodeReferenceResponse"] = Field(
        default=None, title="The code reference that was used for this run."
    )
    model_version: Optional[ModelVersionResponse] = None
    tags: List[TagResponse] = Field(
        title="Tags associated with the pipeline run.",
    )
    log_collection: Optional[List["LogsResponse"]] = Field(
        title="Logs associated with this pipeline run.",
        default=None,
    )
    visualizations: List["CuratedVisualizationResponse"] = Field(
        default=[],
        title="Curated visualizations associated with the pipeline run.",
    )
    trigger: Optional["TRIGGER_RETURN_TYPE_UNION"] = Field(
        default=None,
        title="The trigger that generated this pipeline run.",
    )
    original_run: Optional["PipelineRunResponse"] = Field(
        default=None,
        title="The original run that was replayed to create this run.",
    )
    parent_run: Optional["PipelineRunResponse"] = Field(
        default=None,
        title="The parent run that launched this run as a child pipeline.",
    )
    active_wait_condition: Optional["RunWaitConditionResponse"] = Field(
        default=None,
        title="The active pending wait condition associated with this run.",
    )
    outputs: Dict[str, "ArtifactVersionResponse"] = Field(
        default_factory=dict,
        title="Pipeline output artifact versions keyed by output name.",
    )

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())


class PipelineRunResponse(
    ProjectScopedResponse[
        PipelineRunResponseBody,
        PipelineRunResponseMetadata,
        PipelineRunResponseResources,
    ]
):
    """Response model for pipeline runs."""

    name: str = Field(
        title="The name of the pipeline run.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "PipelineRunResponse":
        """Get the hydrated version of this pipeline run.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_run(self.id)

    # Helper methods
    @property
    def artifact_versions(self) -> List["ArtifactVersionResponse"]:
        """Get all artifact versions that are outputs of steps of this run.

        Returns:
            All output artifact versions of this run (including cached ones).
        """
        from zenml.artifacts.utils import (
            get_artifacts_versions_of_pipeline_run,
        )

        return get_artifacts_versions_of_pipeline_run(self)

    @property
    def produced_artifact_versions(self) -> List["ArtifactVersionResponse"]:
        """Get all artifact versions produced during this pipeline run.

        Returns:
            A list of all artifact versions produced during this pipeline run.
        """
        from zenml.artifacts.utils import (
            get_artifacts_versions_of_pipeline_run,
        )

        return get_artifacts_versions_of_pipeline_run(self, only_produced=True)

    # Body and metadata properties
    @property
    def status(self) -> ExecutionStatus:
        """The `status` property.

        Returns:
            the value of the property.
        """
        return self.get_body().status

    @property
    def index(self) -> int:
        """The `index` property.

        Returns:
            the value of the property.
        """
        return self.get_body().index

    @property
    def run_metadata(self) -> Dict[str, MetadataType]:
        """The `run_metadata` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().run_metadata

    @property
    def steps(self) -> Dict[str, "StepRunResponse"]:
        """The `steps` property.

        Returns:
            the value of the property.
        """
        from zenml.client import Client

        return {
            step.name: step
            for step in pagination_utils.depaginate(
                Client().list_run_steps,
                pipeline_run_id=self.id,
                project=self.project_id,
                exclude_retried=True,
            )
        }

    @property
    def config(self) -> PipelineConfiguration:
        """The `config` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().config

    @property
    def start_time(self) -> Optional[datetime]:
        """The `start_time` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().start_time

    @property
    def end_time(self) -> Optional[datetime]:
        """The `end_time` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().end_time

    @property
    def in_progress(self) -> bool:
        """The `in_progress` property.

        Returns:
            the value of the property.
        """
        return self.get_body().in_progress

    @property
    def client_environment(self) -> Dict[str, Any]:
        """The `client_environment` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().client_environment

    @property
    def orchestrator_environment(self) -> Dict[str, Any]:
        """The `orchestrator_environment` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().orchestrator_environment

    @property
    def orchestrator_run_id(self) -> Optional[str]:
        """The `orchestrator_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().orchestrator_run_id

    @property
    def code_path(self) -> Optional[str]:
        """The `code_path` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().code_path

    @property
    def template_id(self) -> Optional[UUID]:
        """The `template_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().template_id

    @property
    def is_templatable(self) -> bool:
        """The `is_templatable` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().is_templatable

    @property
    def trigger_info(self) -> Optional[PipelineRunTriggerInfo]:
        """The `trigger_info` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().trigger_info

    @property
    def enable_heartbeat(self) -> bool:
        """The `enable_heartbeat` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().enable_heartbeat

    @property
    def exception_info(self) -> Optional[ExceptionInfo]:
        """The `exception_info` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().exception_info

    @property
    def triggered_by_deployment(self) -> bool:
        """The `triggered_by_deployment` property.

        Returns:
            the value of the property.
        """
        return (
            self.trigger_info is not None
            and self.trigger_info.deployment_id is not None
        )

    @property
    def snapshot(self) -> Optional["PipelineSnapshotResponse"]:
        """The `snapshot` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().snapshot

    @property
    def source_snapshot(self) -> Optional["PipelineSnapshotResponse"]:
        """The `source_snapshot` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().source_snapshot

    @property
    def stack(self) -> Optional["StackResponse"]:
        """The `stack` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().stack

    @property
    def pipeline(self) -> Optional["PipelineResponse"]:
        """The `pipeline` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().pipeline

    @property
    def build(self) -> Optional["PipelineBuildResponse"]:
        """The `build` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().build

    @property
    def schedule(self) -> Optional["ScheduleResponse"]:
        """The `schedule` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().schedule

    @property
    def code_reference(self) -> Optional["CodeReferenceResponse"]:
        """The `schedule` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().code_reference

    @property
    def model_version(self) -> Optional[ModelVersionResponse]:
        """The `model_version` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().model_version

    @property
    def tags(self) -> List[TagResponse]:
        """The `tags` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().tags

    @property
    def log_collection(self) -> Optional[List["LogsResponse"]]:
        """The `log_collection` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().log_collection

    @property
    def trigger(self) -> Optional["TRIGGER_RETURN_TYPE_UNION"]:
        """The `trigger` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().trigger

    @property
    def trigger_execution_info(self) -> Optional["TriggerExecutionInfo"]:
        """The `trigger_execution_info` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().trigger_execution_info

    @property
    def outputs(self) -> Dict[str, "ArtifactVersionResponse"]:
        """The `outputs` property.

        Returns:
            The output artifact versions keyed by output name.
        """
        return self.get_resources().outputs

    @property
    def original_run(self) -> Optional["PipelineRunResponse"]:
        """The `original_run` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().original_run

    @property
    def parent_run(self) -> Optional["PipelineRunResponse"]:
        """The `parent_run` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().parent_run

    @property
    def active_wait_condition(self) -> Optional["RunWaitConditionResponse"]:
        """The `active_wait_condition` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().active_wait_condition

    @property
    def pipeline_id(self) -> UUID | None:
        """The `pipeline_id` property.

        Returns:
            The ID of the pipeline this run is associated with.
        """
        return self.get_body().pipeline_id

    @property
    def child_key(self) -> Optional[str]:
        """The `child_key` property.

        Returns:
            the value of the property.
        """
        return self.get_body().child_key

    @property
    def root_run_id(self) -> Optional[UUID]:
        """The `root_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().root_run_id


# ------------------ Filter Model ------------------


class PipelineRunFilter(
    ProjectScopedFilter, TaggableFilter, RunMetadataFilterMixin
):
    """Model to enable advanced filtering of all pipeline runs."""

    CUSTOM_SORTING_OPTIONS: ClassVar[List[str]] = [
        *ProjectScopedFilter.CUSTOM_SORTING_OPTIONS,
        *TaggableFilter.CUSTOM_SORTING_OPTIONS,
        *RunMetadataFilterMixin.CUSTOM_SORTING_OPTIONS,
        "stack",
        "pipeline",
        "model",
        "model_version",
    ]
    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ProjectScopedFilter.FILTER_EXCLUDE_FIELDS,
        *TaggableFilter.FILTER_EXCLUDE_FIELDS,
        *RunMetadataFilterMixin.FILTER_EXCLUDE_FIELDS,
        "code_repository_id",
        "build_id",
        "schedule_id",
        "stack_id",
        "template_id",
        "source_snapshot_id",
        "pipeline",
        "stack",
        "code_repository",
        "model",
        "stack_component",
        "pipeline_name",
        "templatable",
        "triggered_by_step_run_id",
        "triggered_by_deployment_id",
        "linked_to_model_version_id",
        "trigger_id",
        "root_runs_only",
    ]
    CLI_EXCLUDE_FIELDS = [
        *ProjectScopedFilter.CLI_EXCLUDE_FIELDS,
        *TaggableFilter.CLI_EXCLUDE_FIELDS,
        *RunMetadataFilterMixin.CLI_EXCLUDE_FIELDS,
    ]
    API_SINGLE_INPUT_PARAMS: ClassVar[List[str]] = [
        *ProjectScopedFilter.API_SINGLE_INPUT_PARAMS,
        *TaggableFilter.API_SINGLE_INPUT_PARAMS,
        *RunMetadataFilterMixin.API_SINGLE_INPUT_PARAMS,
        "in_progress",
        "templatable",
        "root_runs_only",
    ]

    name: StringFilterOption = Field(
        default=None,
        description="Name of the Pipeline Run",
    )
    index: IntegerFilterOption = Field(
        default=None,
        description="The unique index of the run within the pipeline.",
    )
    orchestrator_run_id: StringFilterOption = Field(
        default=None,
        description="Name of the Pipeline Run within the orchestrator",
    )
    pipeline_id: UUIDFilterOption = Field(
        default=None,
        description="Pipeline associated with the Pipeline Run",
        union_mode="left_to_right",
    )
    stack_id: UUIDFilterOption = Field(
        default=None,
        description="Stack used for the Pipeline Run",
        union_mode="left_to_right",
    )
    schedule_id: UUIDFilterOption = Field(
        default=None,
        description="Schedule that triggered the Pipeline Run",
        union_mode="left_to_right",
    )
    build_id: UUIDFilterOption = Field(
        default=None,
        description="Build used for the Pipeline Run",
        union_mode="left_to_right",
    )
    snapshot_id: UUIDFilterOption = Field(
        default=None,
        description="Snapshot used for the Pipeline Run",
        union_mode="left_to_right",
    )
    code_repository_id: UUIDFilterOption = Field(
        default=None,
        description="Code repository used for the Pipeline Run",
        union_mode="left_to_right",
    )
    template_id: UUIDFilterOption = Field(
        default=None,
        description="DEPRECATED: Template used for the pipeline run.",
        deprecated=True,
        union_mode="left_to_right",
    )
    source_snapshot_id: UUIDFilterOption = Field(
        default=None,
        description="Source snapshot used for the pipeline run.",
        union_mode="left_to_right",
    )
    model_version_id: UUIDFilterOption = Field(
        default=None,
        description="Model version associated with the pipeline run.",
        union_mode="left_to_right",
    )
    linked_to_model_version_id: UUIDFilterOption = Field(
        default=None,
        description="Filter by model version linked to the pipeline run. "
        "The difference to `model_version_id` is that this filter will "
        "not only include pipeline runs which are directly linked to the model "
        "version, but also if any step run is linked to the model version.",
        union_mode="left_to_right",
    )
    status: StringFilterOption = Field(
        default=None,
        description="Status of the Pipeline Run",
    )
    in_progress: Optional[bool] = Field(
        default=None,
        description="Whether the pipeline run is in progress.",
    )
    start_time: DatetimeFilterOption = Field(
        default=None,
        description="Start time for this run",
        union_mode="left_to_right",
    )
    end_time: DatetimeFilterOption = Field(
        default=None,
        description="End time for this run",
        union_mode="left_to_right",
    )
    # TODO: Remove once frontend is ready for it. This is replaced by the more
    #   generic `pipeline` filter below.
    pipeline_name: StringFilterOption = Field(
        default=None,
        description="Name of the pipeline associated with the run",
    )
    pipeline: UUIDFilterOption = Field(
        default=None,
        description="Name/ID of the pipeline associated with the run.",
    )
    stack: UUIDFilterOption = Field(
        default=None,
        description="Name/ID of the stack associated with the run.",
    )
    code_repository: UUIDFilterOption = Field(
        default=None,
        description="Name/ID of the code repository associated with the run.",
    )
    model: UUIDFilterOption = Field(
        default=None,
        description="Name/ID of the model associated with the run.",
    )
    stack_component: UUIDFilterOption = Field(
        default=None,
        description="Name/ID of the stack component associated with the run.",
    )
    templatable: Optional[bool] = Field(
        default=None, description="Whether the run is templatable."
    )
    triggered_by_step_run_id: UUIDFilterOption = Field(
        default=None,
        description="The ID of the step run that triggered this pipeline run.",
        union_mode="left_to_right",
    )
    triggered_by_deployment_id: UUIDFilterOption = Field(
        default=None,
        description="The ID of the deployment that triggered this pipeline run.",
        union_mode="left_to_right",
    )
    trigger_id: UUIDFilterOption = Field(
        default=None,
        description="The ID of the trigger that generated this pipeline run.",
        union_mode="left_to_right",
    )
    parent_run_id: UUIDFilterOption = Field(
        default=None,
        description="The parent run ID for nested child pipeline runs.",
        union_mode="left_to_right",
    )
    # TODO: Remove this once we support filtering for `parent_run_id is NULL`
    root_runs_only: Optional[bool] = Field(
        default=None,
        description="Whether to include only root runs. Ignored if False.",
    )
    model_config = ConfigDict(protected_namespaces=())

    def get_custom_filters(
        self,
        table: Type["AnySchema"],
    ) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        Args:
            table: The query table.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters(table)

        from sqlmodel import and_, col, or_

        from zenml.zen_stores.schemas import (
            CodeReferenceSchema,
            CodeRepositorySchema,
            DeploymentSchema,
            ModelSchema,
            ModelVersionPipelineRunSchema,
            ModelVersionSchema,
            PipelineBuildSchema,
            PipelineRunSchema,
            PipelineSchema,
            PipelineSnapshotSchema,
            ScheduleSchema,
            StackComponentSchema,
            StackCompositionSchema,
            StackSchema,
            StepRunSchema,
            TriggerExecutionSchema,
        )

        if self.code_repository_id:
            code_repo_filters = (
                self.code_repository_id
                if isinstance(self.code_repository_id, list)
                else [self.code_repository_id]
            )
            for code_repo_filter in code_repo_filters:
                custom_filters.append(
                    and_(
                        PipelineRunSchema.snapshot_id
                        == PipelineSnapshotSchema.id,
                        PipelineSnapshotSchema.code_reference_id
                        == CodeReferenceSchema.id,
                        self.generate_custom_query_conditions_for_column(
                            value=code_repo_filter,
                            table=CodeReferenceSchema,
                            column="code_repository_id",
                        ),
                    )
                )

        if self.stack_id:
            stack_filters = (
                self.stack_id
                if isinstance(self.stack_id, list)
                else [self.stack_id]
            )
            for stack_filter in stack_filters:
                custom_filters.append(
                    and_(
                        PipelineRunSchema.snapshot_id
                        == PipelineSnapshotSchema.id,
                        PipelineSnapshotSchema.stack_id == StackSchema.id,
                        self.generate_custom_query_conditions_for_column(
                            value=stack_filter,
                            table=StackSchema,
                            column="id",
                        ),
                    )
                )

        if self.schedule_id:
            schedule_filters = (
                self.schedule_id
                if isinstance(self.schedule_id, list)
                else [self.schedule_id]
            )
            for schedule_filter in schedule_filters:
                custom_filters.append(
                    and_(
                        PipelineRunSchema.snapshot_id
                        == PipelineSnapshotSchema.id,
                        PipelineSnapshotSchema.schedule_id
                        == ScheduleSchema.id,
                        self.generate_custom_query_conditions_for_column(
                            value=schedule_filter,
                            table=ScheduleSchema,
                            column="id",
                        ),
                    )
                )

        if self.build_id:
            build_filters = (
                self.build_id
                if isinstance(self.build_id, list)
                else [self.build_id]
            )
            for build_filter in build_filters:
                custom_filters.append(
                    and_(
                        PipelineRunSchema.snapshot_id
                        == PipelineSnapshotSchema.id,
                        PipelineSnapshotSchema.build_id
                        == PipelineBuildSchema.id,
                        self.generate_custom_query_conditions_for_column(
                            value=build_filter,
                            table=PipelineBuildSchema,
                            column="id",
                        ),
                    )
                )

        if self.template_id:
            run_template_filters = (
                self.template_id
                if isinstance(self.template_id, list)
                else [self.template_id]
            )
            for run_template_filter in run_template_filters:
                custom_filters.append(
                    and_(
                        PipelineRunSchema.snapshot_id
                        == PipelineSnapshotSchema.id,
                        self.generate_custom_query_conditions_for_column(
                            value=run_template_filter,
                            table=PipelineSnapshotSchema,
                            column="template_id",
                        ),
                    )
                )

        if self.source_snapshot_id:
            source_snapshot_filters = (
                self.source_snapshot_id
                if isinstance(self.source_snapshot_id, list)
                else [self.source_snapshot_id]
            )
            for source_snapshot_filter in source_snapshot_filters:
                custom_filters.append(
                    and_(
                        PipelineRunSchema.snapshot_id
                        == PipelineSnapshotSchema.id,
                        self.generate_custom_query_conditions_for_column(
                            value=source_snapshot_filter,
                            table=PipelineSnapshotSchema,
                            column="source_snapshot_id",
                        ),
                    )
                )

        if self.pipeline:
            pipeline_filters = (
                self.pipeline
                if isinstance(self.pipeline, list)
                else [self.pipeline]
            )
            for pipeline_filter in pipeline_filters:
                custom_filters.append(
                    and_(
                        PipelineRunSchema.pipeline_id == PipelineSchema.id,
                        self.generate_name_or_id_query_conditions(
                            value=pipeline_filter, table=PipelineSchema
                        ),
                    )
                )

        if self.stack:
            stack_filters = (
                self.stack if isinstance(self.stack, list) else [self.stack]
            )
            for stack_filter in stack_filters:
                custom_filters.append(
                    and_(
                        PipelineRunSchema.snapshot_id
                        == PipelineSnapshotSchema.id,
                        PipelineSnapshotSchema.stack_id == StackSchema.id,
                        self.generate_name_or_id_query_conditions(
                            value=stack_filter,
                            table=StackSchema,
                        ),
                    )
                )

        if self.code_repository:
            code_repo_filters = (
                self.code_repository
                if isinstance(self.code_repository, list)
                else [self.code_repository]
            )
            for code_repo_filter in code_repo_filters:
                custom_filters.append(
                    and_(
                        PipelineRunSchema.snapshot_id
                        == PipelineSnapshotSchema.id,
                        PipelineSnapshotSchema.code_reference_id
                        == CodeReferenceSchema.id,
                        CodeReferenceSchema.code_repository_id
                        == CodeRepositorySchema.id,
                        self.generate_name_or_id_query_conditions(
                            value=code_repo_filter,
                            table=CodeRepositorySchema,
                        ),
                    )
                )

        if self.model:
            model_filters = (
                self.model if isinstance(self.model, list) else [self.model]
            )
            for model_filter in model_filters:
                custom_filters.append(
                    and_(
                        PipelineRunSchema.model_version_id
                        == ModelVersionSchema.id,
                        ModelVersionSchema.model_id == ModelSchema.id,
                        self.generate_name_or_id_query_conditions(
                            value=model_filter, table=ModelSchema
                        ),
                    )
                )

        if self.stack_component:
            component_filters = (
                self.stack_component
                if isinstance(self.stack_component, list)
                else [self.stack_component]
            )
            for component_filter in component_filters:
                custom_filters.append(
                    and_(
                        PipelineRunSchema.snapshot_id
                        == PipelineSnapshotSchema.id,
                        PipelineSnapshotSchema.stack_id == StackSchema.id,
                        StackSchema.id == StackCompositionSchema.stack_id,
                        StackCompositionSchema.component_id
                        == StackComponentSchema.id,
                        self.generate_name_or_id_query_conditions(
                            value=component_filter,
                            table=StackComponentSchema,
                        ),
                    )
                )

        if self.pipeline_name:
            pipeline_name_filters = (
                self.pipeline_name
                if isinstance(self.pipeline_name, list)
                else [self.pipeline_name]
            )
            for pipeline_name_filter in pipeline_name_filters:
                custom_filters.append(
                    and_(
                        PipelineRunSchema.pipeline_id == PipelineSchema.id,
                        self.generate_custom_query_conditions_for_column(
                            value=pipeline_name_filter,
                            table=PipelineSchema,
                            column="name",
                        ),
                    )
                )

        if self.templatable is not None:
            if self.templatable is True:
                templatable_filter = and_(
                    # The following condition is not perfect as it does not
                    # consider stacks with custom flavor components or local
                    # components, but the best we can do currently with our
                    # table columns.
                    PipelineRunSchema.snapshot_id == PipelineSnapshotSchema.id,
                    PipelineSnapshotSchema.build_id == PipelineBuildSchema.id,
                    col(PipelineBuildSchema.is_local).is_(False),
                    col(PipelineBuildSchema.stack_id).is_not(None),
                )
            else:
                templatable_filter = or_(
                    col(PipelineRunSchema.snapshot_id).is_(None),
                    and_(
                        PipelineRunSchema.snapshot_id
                        == PipelineSnapshotSchema.id,
                        col(PipelineSnapshotSchema.build_id).is_(None),
                    ),
                    and_(
                        PipelineRunSchema.snapshot_id
                        == PipelineSnapshotSchema.id,
                        PipelineSnapshotSchema.build_id
                        == PipelineBuildSchema.id,
                        or_(
                            col(PipelineBuildSchema.is_local).is_(True),
                            col(PipelineBuildSchema.stack_id).is_(None),
                        ),
                    ),
                )

            custom_filters.append(templatable_filter)

        if self.triggered_by_step_run_id:
            triggered_by_step_run_id_filters = (
                self.triggered_by_step_run_id
                if isinstance(self.triggered_by_step_run_id, list)
                else [self.triggered_by_step_run_id]
            )
            for (
                triggered_by_step_run_id_filter
            ) in triggered_by_step_run_id_filters:
                custom_filters.append(
                    and_(
                        PipelineRunSchema.triggered_by == StepRunSchema.id,
                        PipelineRunSchema.triggered_by_type
                        == PipelineRunTriggeredByType.STEP_RUN.value,
                        self.generate_custom_query_conditions_for_column(
                            value=triggered_by_step_run_id_filter,
                            table=StepRunSchema,
                            column="id",
                        ),
                    )
                )

        if self.triggered_by_deployment_id:
            triggered_by_deployment_id_filters = (
                self.triggered_by_deployment_id
                if isinstance(self.triggered_by_deployment_id, list)
                else [self.triggered_by_deployment_id]
            )
            for (
                triggered_by_deployment_id_filter
            ) in triggered_by_deployment_id_filters:
                custom_filters.append(
                    and_(
                        PipelineRunSchema.triggered_by == DeploymentSchema.id,
                        PipelineRunSchema.triggered_by_type
                        == PipelineRunTriggeredByType.DEPLOYMENT.value,
                        self.generate_custom_query_conditions_for_column(
                            value=triggered_by_deployment_id_filter,
                            table=DeploymentSchema,
                            column="id",
                        ),
                    )
                )

        if self.linked_to_model_version_id:
            linked_to_model_version_filters = (
                self.linked_to_model_version_id
                if isinstance(self.linked_to_model_version_id, list)
                else [self.linked_to_model_version_id]
            )
            for (
                linked_to_model_version_filter
            ) in linked_to_model_version_filters:
                custom_filters.append(
                    and_(
                        PipelineRunSchema.id
                        == ModelVersionPipelineRunSchema.pipeline_run_id,
                        ModelVersionPipelineRunSchema.model_version_id
                        == ModelVersionSchema.id,
                        self.generate_custom_query_conditions_for_column(
                            value=linked_to_model_version_filter,
                            table=ModelVersionSchema,
                            column="id",
                        ),
                    )
                )

        if self.trigger_id:
            trigger_id_filters = (
                self.trigger_id
                if isinstance(self.trigger_id, list)
                else [self.trigger_id]
            )
            for trigger_id_filter in trigger_id_filters:
                custom_filters.append(
                    and_(
                        and_(
                            PipelineRunSchema.id
                            == TriggerExecutionSchema.pipeline_run_id,
                            self.generate_custom_query_conditions_for_column(
                                value=trigger_id_filter,
                                table=TriggerExecutionSchema,
                                column="trigger_id",
                            ),
                        )
                    )
                )

        if self.root_runs_only is True:
            custom_filters.append(
                col(PipelineRunSchema.parent_run_id).is_(None)
            )

        return custom_filters

    def apply_sorting(
        self,
        query: AnyQuery,
        table: Type["AnySchema"],
    ) -> AnyQuery:
        """Apply sorting to the query.

        Args:
            query: The query to which to apply the sorting.
            table: The query table.

        Returns:
            The query with sorting applied.
        """
        from sqlmodel import asc, desc

        from zenml.enums import SorterOps
        from zenml.zen_stores.schemas import (
            ModelSchema,
            ModelVersionSchema,
            PipelineRunSchema,
            PipelineSchema,
            PipelineSnapshotSchema,
            StackSchema,
        )

        sort_by, operand = self.sorting_params

        if sort_by == "pipeline":
            query = query.outerjoin(
                PipelineSchema,
                PipelineRunSchema.pipeline_id == PipelineSchema.id,
            )
            column = PipelineSchema.name
        elif sort_by == "stack":
            query = query.outerjoin(
                PipelineSnapshotSchema,
                PipelineRunSchema.snapshot_id == PipelineSnapshotSchema.id,
            ).outerjoin(
                StackSchema,
                PipelineSnapshotSchema.stack_id == StackSchema.id,
            )
            column = StackSchema.name
        elif sort_by == "model":
            query = query.outerjoin(
                ModelVersionSchema,
                PipelineRunSchema.model_version_id == ModelVersionSchema.id,
            ).outerjoin(
                ModelSchema,
                ModelVersionSchema.model_id == ModelSchema.id,
            )
            column = ModelSchema.name
        elif sort_by == "model_version":
            query = query.outerjoin(
                ModelVersionSchema,
                PipelineRunSchema.model_version_id == ModelVersionSchema.id,
            )
            column = ModelVersionSchema.name
        else:
            return super().apply_sorting(query=query, table=table)

        query = query.add_columns(column)

        if operand == SorterOps.ASCENDING:
            query = query.order_by(asc(column))
        else:
            query = query.order_by(desc(column))

        return query
