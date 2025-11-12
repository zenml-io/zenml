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
"""Models representing steps runs."""

from datetime import datetime
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.enums import (
    ArtifactSaveType,
    ExecutionStatus,
    StepRunInputArtifactType,
)
from zenml.metadata.metadata_types import MetadataType
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
    RunMetadataFilterMixin,
)
from zenml.models.v2.core.artifact_version import ArtifactVersionResponse
from zenml.models.v2.core.model_version import ModelVersionResponse
from zenml.models.v2.misc.exception_info import ExceptionInfo
from zenml.utils.time_utils import utc_now

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.models.v2.core.logs import (
        LogsRequest,
        LogsResponse,
    )
    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)


class StepRunInputResponse(ArtifactVersionResponse):
    """Response model for step run inputs."""

    input_type: StepRunInputArtifactType

    def get_hydrated_version(self) -> "StepRunInputResponse":
        """Get the hydrated version of this step run input.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return StepRunInputResponse(
            input_type=self.input_type,
            **Client().zen_store.get_artifact_version(self.id).model_dump(),
        )


# ------------------ Request Model ------------------


class StepRunRequest(ProjectScopedRequest):
    """Request model for step runs."""

    name: str = Field(
        title="The name of the pipeline run step.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    start_time: datetime = Field(
        title="The start time of the step run.",
    )
    end_time: datetime | None = Field(
        title="The end time of the step run.",
        default=None,
    )
    status: ExecutionStatus = Field(title="The status of the step.")
    cache_key: str | None = Field(
        title="The cache key of the step run.",
        default=None,
        max_length=STR_FIELD_MAX_LENGTH,
    )
    cache_expires_at: datetime | None = Field(
        title="The time at which this step run should not be used for cached "
        "results anymore. If not set, the result will never expire.",
        default=None,
    )
    code_hash: str | None = Field(
        title="The code hash of the step run.",
        default=None,
        max_length=STR_FIELD_MAX_LENGTH,
    )
    docstring: str | None = Field(
        title="The docstring of the step function or class.",
        default=None,
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    source_code: str | None = Field(
        title="The source code of the step function or class.",
        default=None,
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    pipeline_run_id: UUID = Field(
        title="The ID of the pipeline run that this step run belongs to.",
    )
    original_step_run_id: UUID | None = Field(
        title="The ID of the original step run if this step was cached.",
        default=None,
    )
    parent_step_ids: list[UUID] = Field(
        title="The IDs of the parent steps of this step run.",
        default_factory=list,
        deprecated=True,
    )
    inputs: dict[str, list[UUID]] = Field(
        title="The IDs of the input artifact versions of the step run.",
        default_factory=dict,
    )
    outputs: dict[str, list[UUID]] = Field(
        title="The IDs of the output artifact versions of the step run.",
        default_factory=dict,
    )
    logs: Optional["LogsRequest"] = Field(
        title="Logs associated with this step run.",
        default=None,
    )
    exception_info: ExceptionInfo | None = Field(
        default=None,
        title="The exception information of the step run.",
    )
    dynamic_config: Optional["Step"] = Field(
        title="The dynamic configuration of the step run.",
        default=None,
    )

    model_config = ConfigDict(protected_namespaces=())


# ------------------ Update Model ------------------


class StepRunUpdate(BaseUpdate):
    """Update model for step runs."""

    outputs: dict[str, list[UUID]] = Field(
        title="The IDs of the output artifact versions of the step run.",
        default={},
    )
    loaded_artifact_versions: dict[str, UUID] = Field(
        title="The IDs of artifact versions that were loaded by this step run.",
        default={},
    )
    status: ExecutionStatus | None = Field(
        title="The status of the step.",
        default=None,
    )
    end_time: datetime | None = Field(
        title="The end time of the step run.",
        default=None,
    )
    exception_info: ExceptionInfo | None = Field(
        default=None,
        title="The exception information of the step run.",
    )
    cache_expires_at: datetime | None = Field(
        title="The time at which this step run should not be used for cached "
        "results anymore.",
        default=None,
    )
    model_config = ConfigDict(protected_namespaces=())


# ------------------ Response Model ------------------
class StepRunResponseBody(ProjectScopedResponseBody):
    """Response body for step runs."""

    status: ExecutionStatus = Field(title="The status of the step.")
    version: int = Field(
        title="The version of the step run.",
    )
    is_retriable: bool = Field(
        title="Whether the step run is retriable.",
    )
    start_time: datetime | None = Field(
        title="The start time of the step run.",
        default=None,
    )
    end_time: datetime | None = Field(
        title="The end time of the step run.",
        default=None,
    )
    latest_heartbeat: datetime | None = Field(
        title="The latest heartbeat of the step run.",
        default=None,
    )
    model_version_id: UUID | None = Field(
        title="The ID of the model version that was "
        "configured by this step run explicitly.",
        default=None,
    )
    substitutions: dict[str, str] = Field(
        title="The substitutions of the step run.",
        default={},
    )
    model_config = ConfigDict(protected_namespaces=())


class StepRunResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for step runs."""

    __zenml_skip_dehydration__: ClassVar[list[str]] = [
        "config",
        "spec",
        "metadata",
    ]

    # Configuration
    config: "StepConfiguration" = Field(title="The configuration of the step.")
    spec: "StepSpec" = Field(title="The spec of the step.")

    # Code related fields
    cache_key: str | None = Field(
        title="The cache key of the step run.",
        default=None,
        max_length=STR_FIELD_MAX_LENGTH,
    )
    cache_expires_at: datetime | None = Field(
        title="The time at which this step run should not be used for cached "
        "results anymore. If not set, the result will never expire.",
        default=None,
    )
    code_hash: str | None = Field(
        title="The code hash of the step run.",
        default=None,
        max_length=STR_FIELD_MAX_LENGTH,
    )
    docstring: str | None = Field(
        title="The docstring of the step function or class.",
        default=None,
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    source_code: str | None = Field(
        title="The source code of the step function or class.",
        default=None,
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    exception_info: ExceptionInfo | None = Field(
        default=None,
        title="The exception information of the step run.",
    )

    # References
    logs: Optional["LogsResponse"] = Field(
        title="Logs associated with this step run.",
        default=None,
    )
    snapshot_id: UUID = Field(
        title="The snapshot associated with the step run."
    )
    pipeline_run_id: UUID = Field(
        title="The ID of the pipeline run that this step run belongs to.",
    )
    original_step_run_id: UUID | None = Field(
        title="The ID of the original step run if this step was cached.",
        default=None,
    )
    parent_step_ids: list[UUID] = Field(
        title="The IDs of the parent steps of this step run.",
        default_factory=list,
    )
    run_metadata: dict[str, MetadataType] = Field(
        title="Metadata associated with this step run.",
        default={},
    )


class StepRunResponseResources(ProjectScopedResponseResources):
    """Class for all resource models associated with the step run entity."""

    model_version: ModelVersionResponse | None = None
    inputs: dict[str, list[StepRunInputResponse]] = Field(
        title="The input artifact versions of the step run.",
        default_factory=dict,
    )
    outputs: dict[str, list[ArtifactVersionResponse]] = Field(
        title="The output artifact versions of the step run.",
        default_factory=dict,
    )

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())


class StepRunResponse(
    ProjectScopedResponse[
        StepRunResponseBody, StepRunResponseMetadata, StepRunResponseResources
    ]
):
    """Response model for step runs."""

    name: str = Field(
        title="The name of the pipeline run step.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "StepRunResponse":
        """Get the hydrated version of this step run.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_run_step(self.id)

    # Helper properties
    @property
    def input(self) -> StepRunInputResponse:
        """Returns the input artifact that was used to run this step.

        Returns:
            The input artifact.

        Raises:
            ValueError: If there were zero or multiple inputs to this step.
        """
        if not self.inputs:
            raise ValueError(f"Step {self.name} has no inputs.")
        if len(self.inputs) > 1 or (
            len(self.inputs) == 1 and len(next(iter(self.inputs.values()))) > 1
        ):
            raise ValueError(
                f"Step {self.name} has multiple inputs, so `Step.input` is "
                "ambiguous. Please use `Step.inputs` instead."
            )
        return next(iter(self.inputs.values()))[0]

    @property
    def output(self) -> ArtifactVersionResponse:
        """Returns the output artifact that was written by this step.

        Returns:
            The output artifact.

        Raises:
            ValueError: If there were zero or multiple step outputs.
        """
        if not self.outputs:
            raise ValueError(f"Step {self.name} has no outputs.")
        if len(self.outputs) > 1 or (
            len(self.outputs) == 1
            and len(next(iter(self.outputs.values()))) > 1
        ):
            raise ValueError(
                f"Step {self.name} has multiple outputs, so `Step.output` is "
                "ambiguous. Please use `Step.outputs` instead."
            )
        return next(iter(self.outputs.values()))[0]

    @property
    def regular_inputs(self) -> dict[str, StepRunInputResponse]:
        """Returns the regular step inputs of the step run.

        Regular step inputs are the inputs that are defined in the step function
        signature, and are not manually loaded during the step execution.

        Raises:
            ValueError: If there were multiple regular input artifacts for the
                same input name.

        Returns:
            The regular step inputs.
        """
        result = {}

        for input_name, input_artifacts in self.inputs.items():
            filtered = [
                input_artifact
                for input_artifact in input_artifacts
                if input_artifact.input_type != StepRunInputArtifactType.MANUAL
            ]
            if len(filtered) > 1:
                raise ValueError(
                    f"Expected 1 regular input artifact for {input_name}, got "
                    f"{len(filtered)}."
                )
            if filtered:
                result[input_name] = filtered[0]

        return result

    @property
    def regular_outputs(self) -> dict[str, ArtifactVersionResponse]:
        """Returns the regular step outputs of the step run.

        Regular step outputs are the outputs that are defined in the step
        function signature, and are not manually saved during the step
        execution.

        Raises:
            ValueError: If there were multiple regular output artifacts for the
                same output name.

        Returns:
            The regular step outputs.
        """
        result = {}

        for output_name, output_artifacts in self.outputs.items():
            filtered = [
                output_artifact
                for output_artifact in output_artifacts
                if output_artifact.save_type == ArtifactSaveType.STEP_OUTPUT
            ]
            if len(filtered) > 1:
                raise ValueError(
                    f"Expected 1 regular output artifact for {output_name}, "
                    f"got {len(filtered)}."
                )
            if filtered:
                result[output_name] = filtered[0]

        return result

    # Body and metadata properties
    @property
    def status(self) -> ExecutionStatus:
        """The `status` property.

        Returns:
            the value of the property.
        """
        return self.get_body().status

    @property
    def version(self) -> int:
        """The `version` property.

        Returns:
            the value of the property.
        """
        return self.get_body().version

    @property
    def is_retriable(self) -> bool:
        """The `is_retriable` property.

        Returns:
            the value of the property.
        """
        return self.get_body().is_retriable

    @property
    def inputs(self) -> dict[str, list[StepRunInputResponse]]:
        """The `inputs` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().inputs

    @property
    def outputs(self) -> dict[str, list[ArtifactVersionResponse]]:
        """The `outputs` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().outputs

    @property
    def model_version_id(self) -> UUID | None:
        """The `model_version_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().model_version_id

    @property
    def substitutions(self) -> dict[str, str]:
        """The `substitutions` property.

        Returns:
            the value of the property.
        """
        return self.get_body().substitutions

    @property
    def config(self) -> "StepConfiguration":
        """The `config` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().config

    @property
    def spec(self) -> "StepSpec":
        """The `spec` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().spec

    @property
    def cache_key(self) -> str | None:
        """The `cache_key` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().cache_key

    @property
    def cache_expires_at(self) -> datetime | None:
        """The `cache_expires_at` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().cache_expires_at

    @property
    def code_hash(self) -> str | None:
        """The `code_hash` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().code_hash

    @property
    def docstring(self) -> str | None:
        """The `docstring` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().docstring

    @property
    def source_code(self) -> str | None:
        """The `source_code` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().source_code

    @property
    def start_time(self) -> datetime | None:
        """The `start_time` property.

        Returns:
            the value of the property.
        """
        return self.get_body().start_time

    @property
    def end_time(self) -> datetime | None:
        """The `end_time` property.

        Returns:
            the value of the property.
        """
        return self.get_body().end_time

    @property
    def latest_heartbeat(self) -> datetime | None:
        """The `latest_heartbeat` property.

        Returns:
            the value of the property.
        """
        return self.get_body().latest_heartbeat

    @property
    def logs(self) -> Optional["LogsResponse"]:
        """The `logs` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().logs

    @property
    def snapshot_id(self) -> UUID:
        """The `snapshot_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().snapshot_id

    @property
    def pipeline_run_id(self) -> UUID:
        """The `pipeline_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().pipeline_run_id

    @property
    def original_step_run_id(self) -> UUID | None:
        """The `original_step_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().original_step_run_id

    @property
    def parent_step_ids(self) -> list[UUID]:
        """The `parent_step_ids` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().parent_step_ids

    @property
    def run_metadata(self) -> dict[str, MetadataType]:
        """The `run_metadata` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().run_metadata

    @property
    def model_version(self) -> ModelVersionResponse | None:
        """The `model_version` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().model_version


# ------------------ Filter Model ------------------


class StepRunFilter(ProjectScopedFilter, RunMetadataFilterMixin):
    """Model to enable advanced filtering of step runs."""

    FILTER_EXCLUDE_FIELDS: ClassVar[list[str]] = [
        *ProjectScopedFilter.FILTER_EXCLUDE_FIELDS,
        *RunMetadataFilterMixin.FILTER_EXCLUDE_FIELDS,
        "model",
        "exclude_retried",
        "cache_expired",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[list[str]] = [
        *ProjectScopedFilter.CLI_EXCLUDE_FIELDS,
        *RunMetadataFilterMixin.CLI_EXCLUDE_FIELDS,
    ]
    CUSTOM_SORTING_OPTIONS: ClassVar[list[str]] = [
        *ProjectScopedFilter.CUSTOM_SORTING_OPTIONS,
        *RunMetadataFilterMixin.CUSTOM_SORTING_OPTIONS,
    ]
    API_MULTI_INPUT_PARAMS: ClassVar[list[str]] = [
        *ProjectScopedFilter.API_MULTI_INPUT_PARAMS,
        *RunMetadataFilterMixin.API_MULTI_INPUT_PARAMS,
    ]

    name: str | None = Field(
        default=None,
        description="Name of the step run",
    )
    code_hash: str | None = Field(
        default=None,
        description="Code hash for this step run",
    )
    cache_key: str | None = Field(
        default=None,
        description="Cache key for this step run",
    )
    status: str | None = Field(
        default=None,
        description="Status of the Step Run",
    )
    start_time: datetime | str | None = Field(
        default=None,
        description="Start time for this run",
        union_mode="left_to_right",
    )
    end_time: datetime | str | None = Field(
        default=None,
        description="End time for this run",
        union_mode="left_to_right",
    )
    pipeline_run_id: UUID | str | None = Field(
        default=None,
        description="Pipeline run of this step run",
        union_mode="left_to_right",
    )
    snapshot_id: UUID | str | None = Field(
        default=None,
        description="Snapshot of this step run",
        union_mode="left_to_right",
    )
    original_step_run_id: UUID | str | None = Field(
        default=None,
        description="Original id for this step run",
        union_mode="left_to_right",
    )
    model_version_id: UUID | str | None = Field(
        default=None,
        description="Model version associated with the step run.",
        union_mode="left_to_right",
    )
    model: UUID | str | None = Field(
        default=None,
        description="Name/ID of the model associated with the step run.",
    )
    exclude_retried: bool | None = Field(
        default=None,
        description="Whether to exclude retried step runs.",
    )
    cache_expires_at: datetime | str | None = Field(
        default=None,
        description="Cache expiration time of the step run.",
        union_mode="left_to_right",
    )
    cache_expired: bool | None = Field(
        default=None,
        description="Whether the cache expiration time of the step run has "
        "passed.",
    )
    model_config = ConfigDict(protected_namespaces=())

    def get_custom_filters(
        self, table: type["AnySchema"]
    ) -> list["ColumnElement[bool]"]:
        """Get custom filters.

        Args:
            table: The query table.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters(table)

        from sqlmodel import and_, col, or_

        from zenml.zen_stores.schemas import (
            ModelSchema,
            ModelVersionSchema,
            StepRunSchema,
        )

        if self.model:
            model_filter = and_(
                StepRunSchema.model_version_id == ModelVersionSchema.id,
                ModelVersionSchema.model_id == ModelSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.model, table=ModelSchema
                ),
            )
            custom_filters.append(model_filter)

        if self.exclude_retried:
            custom_filters.append(
                col(StepRunSchema.status) != ExecutionStatus.RETRIED.value
            )

        if self.cache_expired is True:
            cache_expiration_filter = and_(
                col(StepRunSchema.cache_expires_at).is_not(None),
                col(StepRunSchema.cache_expires_at) < utc_now(),
            )
            custom_filters.append(cache_expiration_filter)
        elif self.cache_expired is False:
            cache_expiration_filter = or_(
                col(StepRunSchema.cache_expires_at) > utc_now(),
                col(StepRunSchema.cache_expires_at).is_(None),
            )
            custom_filters.append(cache_expiration_filter)

        return custom_filters


# ------------------ Heartbeat Model ---------------


class StepHeartbeatResponse(BaseModel, use_enum_values=True):
    """Light-weight model for Step Heartbeat responses."""

    id: UUID
    status: ExecutionStatus
    latest_heartbeat: datetime
