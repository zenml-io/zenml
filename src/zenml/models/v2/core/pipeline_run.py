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
    cast,
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import ExecutionStatus
from zenml.metadata.metadata_types import MetadataType
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
    WorkspaceScopedTaggableFilter,
)
from zenml.models.v2.core.model_version import ModelVersionResponse
from zenml.models.v2.core.tag import TagResponse

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.models import TriggerExecutionResponse
    from zenml.models.v2.core.artifact_version import ArtifactVersionResponse
    from zenml.models.v2.core.code_reference import CodeReferenceResponse
    from zenml.models.v2.core.pipeline import PipelineResponse
    from zenml.models.v2.core.pipeline_build import (
        PipelineBuildResponse,
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
    tags: Optional[List[str]] = Field(
        default=None,
        title="Tags of the pipeline run.",
    )
    model_version_id: Optional[UUID] = Field(
        title="The ID of the model version that was "
        "configured by this pipeline run explicitly.",
        default=None,
    )

    model_config = ConfigDict(protected_namespaces=())


# ------------------ Update Model ------------------


class PipelineRunUpdate(BaseModel):
    """Pipeline run update model."""

    status: Optional[ExecutionStatus] = None
    end_time: Optional[datetime] = None
    model_version_id: Optional[UUID] = Field(
        title="The ID of the model version that was "
        "configured by this pipeline run explicitly.",
        default=None,
    )
    # TODO: we should maybe have a different update model here, the upper
    #  three attributes should only be for internal use
    add_tags: Optional[List[str]] = Field(
        default=None, title="New tags to add to the pipeline run."
    )
    remove_tags: Optional[List[str]] = Field(
        default=None, title="Tags to remove from the pipeline run."
    )

    model_config = ConfigDict(protected_namespaces=())


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
    model_version_id: Optional[UUID] = Field(
        title="The ID of the model version that was "
        "configured by this pipeline run explicitly.",
        default=None,
    )

    model_config = ConfigDict(protected_namespaces=())


class PipelineRunResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for pipeline runs."""

    run_metadata: Dict[str, MetadataType] = Field(
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
    code_path: Optional[str] = Field(
        default=None,
        title="Optional path where the code is stored in the artifact store.",
    )
    template_id: Optional[UUID] = Field(
        default=None,
        description="Template used for the pipeline run.",
    )
    is_templatable: bool = Field(
        default=False,
        description="Whether a template can be created from this run.",
    )


class PipelineRunResponseResources(WorkspaceScopedResponseResources):
    """Class for all resource models associated with the pipeline run entity."""

    model_version: Optional[ModelVersionResponse] = None
    tags: List[TagResponse] = Field(
        title="Tags associated with the pipeline run.",
    )

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

    def refresh_run_status(self) -> "PipelineRunResponse":
        """Method to refresh the status of a run if it is initializing/running.

        Returns:
            The updated pipeline.

        Raises:
            ValueError: If the stack of the run response is None.
        """
        if self.status in [
            ExecutionStatus.INITIALIZING,
            ExecutionStatus.RUNNING,
        ]:
            # Check if the stack still accessible
            if self.stack is None:
                raise ValueError(
                    "The stack that this pipeline run response was executed on"
                    "has been deleted."
                )

            # Create the orchestrator instance
            from zenml.enums import StackComponentType
            from zenml.orchestrators.base_orchestrator import BaseOrchestrator
            from zenml.stack.stack_component import StackComponent

            # Check if the stack still accessible
            orchestrator_list = self.stack.components.get(
                StackComponentType.ORCHESTRATOR, []
            )
            if len(orchestrator_list) == 0:
                raise ValueError(
                    "The orchestrator that this pipeline run response was "
                    "executed with has been deleted."
                )

            orchestrator = cast(
                BaseOrchestrator,
                StackComponent.from_model(
                    component_model=orchestrator_list[0]
                ),
            )

            # Fetch the status
            status = orchestrator.fetch_status(run=self)

            # If it is different from the current status, update it
            if status != self.status:
                from zenml.client import Client
                from zenml.models import PipelineRunUpdate

                client = Client()
                return client.zen_store.update_run(
                    run_id=self.id,
                    run_update=PipelineRunUpdate(status=status),
                )

        return self

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
    def model_version_id(self) -> Optional[UUID]:
        """The `model_version_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().model_version_id

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


# ------------------ Filter Model ------------------


class PipelineRunFilter(WorkspaceScopedTaggableFilter):
    """Model to enable advanced filtering of all Workspaces."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "unlisted",
        "code_repository_id",
        "build_id",
        "schedule_id",
        "stack_id",
        "template_id",
        "user",
        "pipeline",
        "stack",
        "code_repository",
        "model",
        "pipeline_name",
        "templatable",
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
    template_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Template used for the pipeline run.",
        union_mode="left_to_right",
    )
    model_version_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Model version associated with the pipeline run.",
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
    user: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of the user that created the run.",
    )
    # TODO: Remove once frontend is ready for it. This is replaced by the more
    # generic `pipeline` filter below.
    pipeline_name: Optional[str] = Field(
        default=None,
        description="Name of the pipeline associated with the run",
    )
    pipeline: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of the pipeline associated with the run.",
    )
    stack: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of the stack associated with the run.",
    )
    code_repository: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of the code repository associated with the run.",
    )
    model: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of the model associated with the run.",
    )
    templatable: Optional[bool] = Field(
        default=None, description="Whether the run is templatable."
    )

    model_config = ConfigDict(protected_namespaces=())

    def get_custom_filters(
        self,
    ) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters()

        from sqlmodel import and_, col, or_

        from zenml.zen_stores.schemas import (
            CodeReferenceSchema,
            CodeRepositorySchema,
            ModelSchema,
            ModelVersionSchema,
            PipelineBuildSchema,
            PipelineDeploymentSchema,
            PipelineRunSchema,
            PipelineSchema,
            ScheduleSchema,
            StackSchema,
            UserSchema,
        )

        if self.unlisted is not None:
            if self.unlisted is True:
                unlisted_filter = PipelineRunSchema.pipeline_id.is_(None)  # type: ignore[union-attr]
            else:
                unlisted_filter = PipelineRunSchema.pipeline_id.is_not(None)  # type: ignore[union-attr]
            custom_filters.append(unlisted_filter)

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

        if self.template_id:
            run_template_filter = and_(
                PipelineRunSchema.deployment_id == PipelineDeploymentSchema.id,
                PipelineDeploymentSchema.template_id == self.template_id,
            )
            custom_filters.append(run_template_filter)

        if self.user:
            user_filter = and_(
                PipelineRunSchema.user_id == UserSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.user, table=UserSchema
                ),
            )
            custom_filters.append(user_filter)

        if self.pipeline:
            pipeline_filter = and_(
                PipelineRunSchema.pipeline_id == PipelineSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.pipeline, table=PipelineSchema
                ),
            )
            custom_filters.append(pipeline_filter)

        if self.stack:
            stack_filter = and_(
                PipelineRunSchema.deployment_id == PipelineDeploymentSchema.id,
                PipelineDeploymentSchema.stack_id == StackSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.stack,
                    table=StackSchema,
                ),
            )
            custom_filters.append(stack_filter)

        if self.code_repository:
            code_repo_filter = and_(
                PipelineRunSchema.deployment_id == PipelineDeploymentSchema.id,
                PipelineDeploymentSchema.code_reference_id
                == CodeReferenceSchema.id,
                CodeReferenceSchema.code_repository_id
                == CodeRepositorySchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.code_repository,
                    table=CodeRepositorySchema,
                ),
            )
            custom_filters.append(code_repo_filter)

        if self.model:
            model_filter = and_(
                PipelineRunSchema.model_version_id == ModelVersionSchema.id,
                ModelVersionSchema.model_id == ModelSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.model, table=ModelSchema
                ),
            )
            custom_filters.append(model_filter)

        if self.pipeline_name:
            pipeline_name_filter = and_(
                PipelineRunSchema.pipeline_id == PipelineSchema.id,
                self.generate_custom_query_conditions_for_column(
                    value=self.pipeline_name,
                    table=PipelineSchema,
                    column="name",
                ),
            )
            custom_filters.append(pipeline_name_filter)

        if self.templatable is not None:
            if self.templatable is True:
                templatable_filter = and_(
                    # The following condition is not perfect as it does not
                    # consider stacks with custom flavor components or local
                    # components, but the best we can do currently with our
                    # table columns.
                    PipelineRunSchema.deployment_id
                    == PipelineDeploymentSchema.id,
                    PipelineDeploymentSchema.build_id
                    == PipelineBuildSchema.id,
                    col(PipelineBuildSchema.is_local).is_(False),
                    col(PipelineBuildSchema.stack_id).is_not(None),
                )
            else:
                templatable_filter = or_(
                    col(PipelineRunSchema.deployment_id).is_(None),
                    and_(
                        PipelineRunSchema.deployment_id
                        == PipelineDeploymentSchema.id,
                        col(PipelineDeploymentSchema.build_id).is_(None),
                    ),
                    and_(
                        PipelineRunSchema.deployment_id
                        == PipelineDeploymentSchema.id,
                        PipelineDeploymentSchema.build_id
                        == PipelineBuildSchema.id,
                        or_(
                            col(PipelineBuildSchema.is_local).is_(True),
                            col(PipelineBuildSchema.stack_id).is_(None),
                        ),
                    ),
                )

            custom_filters.append(templatable_filter)

        return custom_filters
