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
    ClassVar,
    Dict,
    List,
    Optional,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import ExecutionStatus, GenericFilterOps
from zenml.models.v2.base.filter import StrFilter
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
)
from zenml.models.v2.core.model_version import ModelVersionResponse

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.models import TriggerExecutionResponse
    from zenml.models.v2.core.artifact_version import ArtifactVersionResponse
    from zenml.models.v2.core.code_reference import CodeReferenceResponse
    from zenml.models.v2.core.pipeline import PipelineResponse
    from zenml.models.v2.core.pipeline_build import (
        PipelineBuildResponse,
    )
    from zenml.models.v2.core.run_metadata import (
        RunMetadataResponse,
    )
    from zenml.models.v2.core.schedule import ScheduleResponse
    from zenml.models.v2.core.stack import StackResponse
    from zenml.models.v2.core.step_run import StepRunResponse


# ------------------ Request Model ------------------


class PipelineRunRequest(WorkspaceScopedRequest):
    """Request model for pipeline runs."""

    name: str = Field(
        title="The name of the pipeline run.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    deployment: UUID = Field(
        title="The deployment associated with the pipeline run."
    )
    pipeline: Optional[UUID] = Field(
        title="The pipeline associated with the pipeline run.",
        default=None,
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
    trigger_execution_id: Optional[UUID] = Field(
        default=None,
        title="ID of the trigger execution that triggered this run.",
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
    code_reference: Optional["CodeReferenceResponse"] = Field(
        default=None, title="The code reference that was used for this run."
    )
    deployment_id: Optional[UUID] = Field(
        default=None, title="The deployment that was used for this run."
    )
    trigger_execution: Optional["TriggerExecutionResponse"] = Field(
        default=None, title="The trigger execution that triggered this run."
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


class PipelineRunResponseResources(WorkspaceScopedResponseResources):
    """Class for all resource models associated with the pipeline run entity."""

    model_version: Optional[ModelVersionResponse] = None

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())


class PipelineRunResponse(
    WorkspaceScopedResponse[
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
    def stack(self) -> Optional["StackResponse"]:
        """The `stack` property.

        Returns:
            the value of the property.
        """
        return self.get_body().stack

    @property
    def pipeline(self) -> Optional["PipelineResponse"]:
        """The `pipeline` property.

        Returns:
            the value of the property.
        """
        return self.get_body().pipeline

    @property
    def build(self) -> Optional["PipelineBuildResponse"]:
        """The `build` property.

        Returns:
            the value of the property.
        """
        return self.get_body().build

    @property
    def schedule(self) -> Optional["ScheduleResponse"]:
        """The `schedule` property.

        Returns:
            the value of the property.
        """
        return self.get_body().schedule

    @property
    def trigger_execution(self) -> Optional["TriggerExecutionResponse"]:
        """The `trigger_execution` property.

        Returns:
            the value of the property.
        """
        return self.get_body().trigger_execution

    @property
    def code_reference(self) -> Optional["CodeReferenceResponse"]:
        """The `schedule` property.

        Returns:
            the value of the property.
        """
        return self.get_body().code_reference

    @property
    def deployment_id(self) -> Optional["UUID"]:
        """The `deployment_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().deployment_id

    @property
    def run_metadata(self) -> Dict[str, "RunMetadataResponse"]:
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
        return self.get_metadata().steps

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
    def client_environment(self) -> Dict[str, str]:
        """The `client_environment` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().client_environment

    @property
    def orchestrator_environment(self) -> Dict[str, str]:
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
    def model_version(self) -> Optional[ModelVersionResponse]:
        """The `model_version` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().model_version


# ------------------ Filter Model ------------------


class PipelineRunFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all Workspaces."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "unlisted",
        "code_repository_id",
        "build_id",
        "schedule_id",
        "stack_id",
        "pipeline_name",
    ]
    name: Optional[str] = Field(
        default=None,
        description="Name of the Pipeline Run",
    )
    orchestrator_run_id: Optional[str] = Field(
        default=None,
        description="Name of the Pipeline Run within the orchestrator",
    )
    pipeline_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Pipeline associated with the Pipeline Run",
        union_mode="left_to_right",
    )
    pipeline_name: Optional[str] = Field(
        default=None,
        description="Name of the pipeline associated with the run",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Workspace of the Pipeline Run",
        union_mode="left_to_right",
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="User that created the Pipeline Run",
        union_mode="left_to_right",
    )
    stack_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Stack used for the Pipeline Run",
        union_mode="left_to_right",
    )
    schedule_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Schedule that triggered the Pipeline Run",
        union_mode="left_to_right",
    )
    build_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Build used for the Pipeline Run",
        union_mode="left_to_right",
    )
    deployment_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Deployment used for the Pipeline Run",
        union_mode="left_to_right",
    )
    code_repository_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Code repository used for the Pipeline Run",
        union_mode="left_to_right",
    )
    status: Optional[str] = Field(
        default=None,
        description="Name of the Pipeline Run",
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
    unlisted: Optional[bool] = None

    def get_custom_filters(
        self,
    ) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters()

        from sqlmodel import and_

        from zenml.zen_stores.schemas import (
            CodeReferenceSchema,
            PipelineBuildSchema,
            PipelineDeploymentSchema,
            PipelineRunSchema,
            PipelineSchema,
            ScheduleSchema,
            StackSchema,
        )

        if self.unlisted is not None:
            if self.unlisted is True:
                unlisted_filter = PipelineRunSchema.pipeline_id.is_(None)  # type: ignore[union-attr]
            else:
                unlisted_filter = PipelineRunSchema.pipeline_id.is_not(None)  # type: ignore[union-attr]
            custom_filters.append(unlisted_filter)

        if self.pipeline_name is not None:
            value, filter_operator = self._resolve_operator(self.pipeline_name)
            filter_ = StrFilter(
                operation=GenericFilterOps(filter_operator),
                column="name",
                value=value,
            )
            pipeline_name_filter = and_(
                PipelineRunSchema.pipeline_id == PipelineSchema.id,
                filter_.generate_query_conditions(PipelineSchema),
            )
            custom_filters.append(pipeline_name_filter)

        if self.code_repository_id:
            code_repo_filter = and_(
                PipelineRunSchema.deployment_id == PipelineDeploymentSchema.id,
                PipelineDeploymentSchema.code_reference_id
                == CodeReferenceSchema.id,
                CodeReferenceSchema.code_repository_id
                == self.code_repository_id,
            )
            custom_filters.append(code_repo_filter)

        if self.stack_id:
            stack_filter = and_(
                PipelineRunSchema.deployment_id == PipelineDeploymentSchema.id,
                PipelineDeploymentSchema.stack_id == StackSchema.id,
                StackSchema.id == self.stack_id,
            )
            custom_filters.append(stack_filter)

        if self.schedule_id:
            schedule_filter = and_(
                PipelineRunSchema.deployment_id == PipelineDeploymentSchema.id,
                PipelineDeploymentSchema.schedule_id == ScheduleSchema.id,
                ScheduleSchema.id == self.schedule_id,
            )
            custom_filters.append(schedule_filter)

        if self.build_id:
            pipeline_build_filter = and_(
                PipelineRunSchema.deployment_id == PipelineDeploymentSchema.id,
                PipelineDeploymentSchema.build_id == PipelineBuildSchema.id,
                PipelineBuildSchema.id == self.build_id,
            )
            custom_filters.append(pipeline_build_filter)

        return custom_filters
