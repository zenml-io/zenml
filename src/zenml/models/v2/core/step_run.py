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

from zenml.config.step_configurations import StepConfiguration, StepSpec
from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.enums import ExecutionStatus, StepRunInputArtifactType
from zenml.metadata.metadata_types import MetadataType
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
)
from zenml.models.v2.core.artifact_version import ArtifactVersionResponse
from zenml.models.v2.core.model_version import ModelVersionResponse

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


class StepRunRequest(WorkspaceScopedRequest):
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
        title="The IDs of the input artifact versions of the step run.",
        default_factory=dict,
    )
    outputs: Dict[str, List[UUID]] = Field(
        title="The IDs of the output artifact versions of the step run.",
        default_factory=dict,
    )
    logs: Optional["LogsRequest"] = Field(
        title="Logs associated with this step run.",
        default=None,
    )
    deployment: UUID = Field(
        title="The deployment associated with the step run."
    )
    model_version_id: Optional[UUID] = Field(
        title="The ID of the model version that was "
        "configured by this step run explicitly.",
        default=None,
    )

    model_config = ConfigDict(protected_namespaces=())


# ------------------ Update Model ------------------


class StepRunUpdate(BaseModel):
    """Update model for step runs."""

    outputs: Dict[str, List[UUID]] = Field(
        title="The IDs of the output artifact versions of the step run.",
        default={},
    )
    loaded_artifact_versions: Dict[str, UUID] = Field(
        title="The IDs of artifact versions that were loaded by this step run.",
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
    model_version_id: Optional[UUID] = Field(
        title="The ID of the model version that was "
        "configured by this step run explicitly.",
        default=None,
    )
    model_config = ConfigDict(protected_namespaces=())


# ------------------ Response Model ------------------
class StepRunResponseBody(WorkspaceScopedResponseBody):
    """Response body for step runs."""

    status: ExecutionStatus = Field(title="The status of the step.")
    start_time: Optional[datetime] = Field(
        title="The start time of the step run.",
        default=None,
    )
    end_time: Optional[datetime] = Field(
        title="The end time of the step run.",
        default=None,
    )
    inputs: Dict[str, StepRunInputResponse] = Field(
        title="The input artifact versions of the step run.",
        default_factory=dict,
    )
    outputs: Dict[str, List[ArtifactVersionResponse]] = Field(
        title="The output artifact versions of the step run.",
        default_factory=dict,
    )
    model_version_id: Optional[UUID] = Field(
        title="The ID of the model version that was "
        "configured by this step run explicitly.",
        default=None,
    )
    model_config = ConfigDict(protected_namespaces=())


class StepRunResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for step runs."""

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
    run_metadata: Dict[str, MetadataType] = Field(
        title="Metadata associated with this step run.",
        default={},
    )


class StepRunResponseResources(WorkspaceScopedResponseResources):
    """Class for all resource models associated with the step run entity."""

    model_version: Optional[ModelVersionResponse] = None

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())


class StepRunResponse(
    WorkspaceScopedResponse[
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
    def input(self) -> ArtifactVersionResponse:
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

    # Body and metadata properties
    @property
    def status(self) -> ExecutionStatus:
        """The `status` property.

        Returns:
            the value of the property.
        """
        return self.get_body().status

    @property
    def inputs(self) -> Dict[str, StepRunInputResponse]:
        """The `inputs` property.

        Returns:
            the value of the property.
        """
        return self.get_body().inputs

    @property
    def outputs(self) -> Dict[str, List[ArtifactVersionResponse]]:
        """The `outputs` property.

        Returns:
            the value of the property.
        """
        return self.get_body().outputs

    @property
    def model_version_id(self) -> Optional[UUID]:
        """The `model_version_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().model_version_id

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
    def cache_key(self) -> Optional[str]:
        """The `cache_key` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().cache_key

    @property
    def code_hash(self) -> Optional[str]:
        """The `code_hash` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().code_hash

    @property
    def docstring(self) -> Optional[str]:
        """The `docstring` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().docstring

    @property
    def source_code(self) -> Optional[str]:
        """The `source_code` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().source_code

    @property
    def start_time(self) -> Optional[datetime]:
        """The `start_time` property.

        Returns:
            the value of the property.
        """
        return self.get_body().start_time

    @property
    def end_time(self) -> Optional[datetime]:
        """The `end_time` property.

        Returns:
            the value of the property.
        """
        return self.get_body().end_time

    @property
    def logs(self) -> Optional["LogsResponse"]:
        """The `logs` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().logs

    @property
    def deployment_id(self) -> UUID:
        """The `deployment_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().deployment_id

    @property
    def pipeline_run_id(self) -> UUID:
        """The `pipeline_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().pipeline_run_id

    @property
    def original_step_run_id(self) -> Optional[UUID]:
        """The `original_step_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().original_step_run_id

    @property
    def parent_step_ids(self) -> List[UUID]:
        """The `parent_step_ids` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().parent_step_ids

    @property
    def run_metadata(self) -> Dict[str, MetadataType]:
        """The `run_metadata` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().run_metadata

    @property
    def model_version(self) -> Optional[ModelVersionResponse]:
        """The `model_version` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().model_version


# ------------------ Filter Model ------------------


class StepRunFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of step runs."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "model",
        "run_metadata",
    ]

    name: Optional[str] = Field(
        default=None,
        description="Name of the step run",
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
        default=None,
        description="Start time for this run",
        union_mode="left_to_right",
    )
    end_time: Optional[Union[datetime, str]] = Field(
        default=None,
        description="End time for this run",
        union_mode="left_to_right",
    )
    pipeline_run_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Pipeline run of this step run",
        union_mode="left_to_right",
    )
    deployment_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Deployment of this step run",
        union_mode="left_to_right",
    )
    original_step_run_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Original id for this step run",
        union_mode="left_to_right",
    )
    model_version_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Model version associated with the step run.",
        union_mode="left_to_right",
    )
    model: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of the model associated with the step run.",
    )
    run_metadata: Optional[Dict[str, str]] = Field(
        default=None,
        description="The run_metadata to filter the step runs by.",
    )
    model_config = ConfigDict(protected_namespaces=())

    def get_custom_filters(
        self, table: Type["AnySchema"]
    ) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        Args:
            table: The query table.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters(table)

        from sqlmodel import and_

        from zenml.zen_stores.schemas import (
            ModelSchema,
            ModelVersionSchema,
            RunMetadataResourceSchema,
            RunMetadataSchema,
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
        if self.run_metadata is not None:
            from zenml.enums import MetadataResourceTypes

            for key, value in self.run_metadata.items():
                additional_filter = and_(
                    RunMetadataResourceSchema.resource_id == StepRunSchema.id,
                    RunMetadataResourceSchema.resource_type
                    == MetadataResourceTypes.STEP_RUN,
                    RunMetadataResourceSchema.run_metadata_id
                    == RunMetadataSchema.id,
                    self.generate_custom_query_conditions_for_column(
                        value=value,
                        table=RunMetadataSchema,
                        column="value",
                    ),
                )
                custom_filters.append(additional_filter)

        return custom_filters
