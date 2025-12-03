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
"""SQLModel implementation of pipeline run tables."""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence
from uuid import UUID

from pydantic import ConfigDict
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import object_session, selectinload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import TEXT, Column, Field, Relationship, select

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.step_configurations import Step
from zenml.constants import TEXT_FIELD_MAX_LENGTH
from zenml.enums import (
    ExecutionMode,
    ExecutionStatus,
    MetadataResourceTypes,
    PipelineRunTriggeredByType,
    TaggableResourceTypes,
    VisualizationResourceTypes,
)
from zenml.logger import get_logger
from zenml.models import (
    PipelineResponse,
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineRunResponseBody,
    PipelineRunResponseMetadata,
    PipelineRunTriggerInfo,
    PipelineRunUpdate,
    RunMetadataEntry,
)
from zenml.models.v2.core.pipeline_run import PipelineRunResponseResources
from zenml.utils.run_utils import (
    build_dag,
    find_all_downstream_steps,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.constants import MODEL_VERSION_TABLENAME
from zenml.zen_stores.schemas.pipeline_build_schemas import PipelineBuildSchema
from zenml.zen_stores.schemas.pipeline_schemas import PipelineSchema
from zenml.zen_stores.schemas.pipeline_snapshot_schemas import (
    PipelineSnapshotSchema,
)
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schedule_schema import ScheduleSchema
from zenml.zen_stores.schemas.schema_utils import (
    build_foreign_key_field,
)
from zenml.zen_stores.schemas.stack_schemas import StackSchema
from zenml.zen_stores.schemas.trigger_schemas import TriggerExecutionSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import (
    RunMetadataInterface,
    jl_arg,
)

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.curated_visualization_schemas import (
        CuratedVisualizationSchema,
    )
    from zenml.zen_stores.schemas.logs_schemas import LogsSchema
    from zenml.zen_stores.schemas.model_schemas import (
        ModelVersionPipelineRunSchema,
        ModelVersionSchema,
    )
    from zenml.zen_stores.schemas.run_metadata_schemas import RunMetadataSchema
    from zenml.zen_stores.schemas.service_schemas import ServiceSchema
    from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema
    from zenml.zen_stores.schemas.tag_schemas import TagSchema

logger = get_logger(__name__)


class PipelineRunSchema(NamedSchema, RunMetadataInterface, table=True):
    """SQL Model for pipeline runs."""

    __tablename__ = "pipeline_run"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "orchestrator_run_id",
            name="unique_orchestrator_run_id_for_snapshot_id",
        ),
        UniqueConstraint(
            "name",
            "project_id",
            name="unique_run_name_in_project",
        ),
    )

    # Fields
    orchestrator_run_id: Optional[str] = Field(nullable=True)
    start_time: Optional[datetime] = Field(nullable=True)
    end_time: Optional[datetime] = Field(nullable=True, default=None)
    in_progress: bool = Field(nullable=False)
    status: str = Field(nullable=False)
    status_reason: Optional[str] = Field(nullable=True)
    orchestrator_environment: Optional[str] = Field(
        sa_column=Column(TEXT, nullable=True)
    )

    # Foreign keys
    snapshot_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineSnapshotSchema.__tablename__,
        source_column="snapshot_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    pipeline_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineSchema.__tablename__,
        source_column="pipeline_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    model_version_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=MODEL_VERSION_TABLENAME,
        source_column="model_version_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )

    # Relationships
    snapshot: Optional["PipelineSnapshotSchema"] = Relationship(
        back_populates="pipeline_runs"
    )
    project: "ProjectSchema" = Relationship(back_populates="runs")
    user: Optional["UserSchema"] = Relationship(back_populates="runs")
    run_metadata: List["RunMetadataSchema"] = Relationship(
        sa_relationship_kwargs=dict(
            secondary="run_metadata_resource",
            primaryjoin=f"and_(foreign(RunMetadataResourceSchema.resource_type)=='{MetadataResourceTypes.PIPELINE_RUN.value}', foreign(RunMetadataResourceSchema.resource_id)==PipelineRunSchema.id)",
            secondaryjoin="RunMetadataSchema.id==foreign(RunMetadataResourceSchema.run_metadata_id)",
            overlaps="run_metadata",
        ),
    )
    logs: List["LogsSchema"] = Relationship(
        back_populates="pipeline_run",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    step_runs: List["StepRunSchema"] = Relationship(
        sa_relationship_kwargs={
            "cascade": "delete",
            "order_by": "asc(StepRunSchema.start_time)",
        },
    )
    model_version: "ModelVersionSchema" = Relationship(
        back_populates="pipeline_runs",
    )

    # Temporary fields and foreign keys to be deprecated
    pipeline_configuration: Optional[str] = Field(
        sa_column=Column(TEXT, nullable=True)
    )
    client_environment: Optional[str] = Field(
        sa_column=Column(TEXT, nullable=True)
    )

    stack_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackSchema.__tablename__,
        source_column="stack_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    build_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineBuildSchema.__tablename__,
        source_column="build_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    schedule_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=ScheduleSchema.__tablename__,
        source_column="schedule_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    trigger_execution_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=TriggerExecutionSchema.__tablename__,
        source_column="trigger_execution_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )

    stack: Optional["StackSchema"] = Relationship()
    build: Optional["PipelineBuildSchema"] = Relationship()
    schedule: Optional["ScheduleSchema"] = Relationship()
    pipeline: Optional["PipelineSchema"] = Relationship()
    trigger_execution: Optional["TriggerExecutionSchema"] = Relationship()
    triggered_by: Optional[UUID] = None
    triggered_by_type: Optional[str] = None

    services: List["ServiceSchema"] = Relationship(
        back_populates="pipeline_run",
    )
    tags: List["TagSchema"] = Relationship(
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(foreign(TagResourceSchema.resource_type)=='{TaggableResourceTypes.PIPELINE_RUN.value}', foreign(TagResourceSchema.resource_id)==PipelineRunSchema.id)",
            secondary="tag_resource",
            secondaryjoin="TagSchema.id == foreign(TagResourceSchema.tag_id)",
            order_by="TagSchema.name",
            overlaps="tags",
        ),
    )
    visualizations: List["CuratedVisualizationSchema"] = Relationship(
        sa_relationship_kwargs=dict(
            primaryjoin=(
                "and_(CuratedVisualizationSchema.resource_type"
                f"=='{VisualizationResourceTypes.PIPELINE_RUN.value}', "
                "foreign(CuratedVisualizationSchema.resource_id)==PipelineRunSchema.id)"
            ),
            overlaps="visualizations",
            cascade="delete",
            order_by="CuratedVisualizationSchema.display_order",
        ),
    )

    # Needed for cascade deletion
    model_versions_pipeline_runs_links: List[
        "ModelVersionPipelineRunSchema"
    ] = Relationship(
        back_populates="pipeline_run",
        sa_relationship_kwargs={"cascade": "delete"},
    )

    model_config = ConfigDict(protected_namespaces=())  # type: ignore[assignment]

    @classmethod
    def get_query_options(
        cls,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> Sequence[ExecutableOption]:
        """Get the query options for the schema.

        Args:
            include_metadata: Whether metadata will be included when converting
                the schema to a model.
            include_resources: Whether resources will be included when
                converting the schema to a model.
            **kwargs: Keyword arguments to allow schema specific logic

        Returns:
            A list of query options.
        """
        from zenml.zen_stores.schemas import ModelVersionSchema

        options = []

        # if include_metadata:
        #     options.extend(
        #         [
        #             joinedload(jl_arg(PipelineRunSchema.run_metadata)),
        #         ]
        #     )

        if include_resources:
            options.extend(
                [
                    selectinload(
                        jl_arg(PipelineRunSchema.model_version)
                    ).joinedload(
                        jl_arg(ModelVersionSchema.model), innerjoin=True
                    ),
                    selectinload(
                        jl_arg(PipelineRunSchema.snapshot)
                    ).joinedload(
                        jl_arg(PipelineSnapshotSchema.source_snapshot)
                    ),
                    selectinload(
                        jl_arg(PipelineRunSchema.snapshot)
                    ).joinedload(jl_arg(PipelineSnapshotSchema.pipeline)),
                    selectinload(
                        jl_arg(PipelineRunSchema.snapshot)
                    ).joinedload(jl_arg(PipelineSnapshotSchema.stack)),
                    selectinload(
                        jl_arg(PipelineRunSchema.snapshot)
                    ).joinedload(jl_arg(PipelineSnapshotSchema.build)),
                    selectinload(
                        jl_arg(PipelineRunSchema.snapshot)
                    ).joinedload(jl_arg(PipelineSnapshotSchema.schedule)),
                    selectinload(
                        jl_arg(PipelineRunSchema.snapshot)
                    ).joinedload(
                        jl_arg(PipelineSnapshotSchema.code_reference)
                    ),
                    selectinload(jl_arg(PipelineRunSchema.logs)),
                    selectinload(jl_arg(PipelineRunSchema.user)),
                    selectinload(jl_arg(PipelineRunSchema.tags)),
                    selectinload(jl_arg(PipelineRunSchema.visualizations)),
                ]
            )

        return options

    @classmethod
    def from_request(
        cls, request: "PipelineRunRequest"
    ) -> "PipelineRunSchema":
        """Convert a `PipelineRunRequest` to a `PipelineRunSchema`.

        Args:
            request: The request to convert.

        Returns:
            The created `PipelineRunSchema`.
        """
        orchestrator_environment = json.dumps(request.orchestrator_environment)
        if len(orchestrator_environment) > TEXT_FIELD_MAX_LENGTH:
            logger.warning(
                "Orchestrator environment is too large to be stored in the "
                "database. Skipping."
            )
            orchestrator_environment = "{}"

        triggered_by = None
        triggered_by_type = None
        if request.trigger_info:
            if request.trigger_info.step_run_id:
                triggered_by = request.trigger_info.step_run_id
                triggered_by_type = PipelineRunTriggeredByType.STEP_RUN.value
            elif request.trigger_info.deployment_id:
                triggered_by = request.trigger_info.deployment_id
                triggered_by_type = PipelineRunTriggeredByType.DEPLOYMENT.value

        return cls(
            project_id=request.project,
            user_id=request.user,
            name=request.name,
            orchestrator_run_id=request.orchestrator_run_id,
            orchestrator_environment=orchestrator_environment,
            start_time=request.start_time,
            status=request.status.value,
            in_progress=not request.status.is_finished,
            status_reason=request.status_reason,
            pipeline_id=request.pipeline,
            snapshot_id=request.snapshot,
            trigger_execution_id=request.trigger_execution_id,
            triggered_by=triggered_by,
            triggered_by_type=triggered_by_type,
        )

    def get_pipeline_configuration(self) -> PipelineConfiguration:
        """Get the pipeline configuration for the pipeline run.

        Raises:
            RuntimeError: if the pipeline run has no snapshot and no pipeline
                configuration.

        Returns:
            The pipeline configuration.
        """
        if self.snapshot:
            pipeline_config = PipelineConfiguration.model_validate_json(
                self.snapshot.pipeline_configuration
            )
        elif self.pipeline_configuration:
            pipeline_config = PipelineConfiguration.model_validate_json(
                self.pipeline_configuration
            )
        else:
            raise RuntimeError(
                "Pipeline run has no snapshot and no pipeline configuration."
            )

        pipeline_config.finalize_substitutions(
            start_time=self.start_time, inplace=True
        )
        return pipeline_config

    def get_step_configuration(self, step_name: str) -> Step:
        """Get the step configuration for the pipeline run.

        Args:
            step_name: The name of the step to get the configuration for.

        Raises:
            RuntimeError: If the pipeline run has no snapshot.

        Returns:
            The step configuration.
        """
        if self.snapshot:
            pipeline_configuration = self.get_pipeline_configuration()
            return Step.from_dict(
                data=json.loads(
                    self.snapshot.get_step_configuration(step_name).config
                ),
                pipeline_configuration=pipeline_configuration,
            )
        else:
            raise RuntimeError("Pipeline run has no snapshot.")

    def get_upstream_steps(self) -> Dict[str, List[str]]:
        """Get the list of all the upstream steps for each step.

        Returns:
            The list of upstream steps for each step.

        Raises:
            RuntimeError: If the pipeline run has no snapshot or
                the snapshot has no pipeline spec.
        """
        if self.snapshot and self.snapshot.pipeline_spec:
            pipeline_spec = PipelineSpec.model_validate_json(
                self.snapshot.pipeline_spec
            )
            steps = {}
            for step_spec in pipeline_spec.steps:
                steps[step_spec.invocation_id] = step_spec.upstream_steps
            return steps
        else:
            raise RuntimeError("Pipeline run has no snapshot.")

    def fetch_metadata_collection(
        self, include_full_metadata: bool = False, **kwargs: Any
    ) -> Dict[str, List[RunMetadataEntry]]:
        """Fetches all the metadata entries related to the pipeline run.

        Args:
            include_full_metadata: Whether the full metadata will be included.
            **kwargs: Keyword arguments.

        Returns:
            a dictionary, where the key is the key of the metadata entry
                and the values represent the list of entries with this key.
        """
        # Fetch the metadata related to this run
        metadata_collection = super().fetch_metadata_collection(**kwargs)

        if include_full_metadata:
            # Fetch the metadata related to the steps of this run
            for s in self.step_runs:
                step_metadata = s.fetch_metadata_collection()
                for k, v in step_metadata.items():
                    metadata_collection[f"{s.name}::{k}"] = v

            # Fetch the metadata related to the schedule of this run
            if self.snapshot is not None:
                if schedule := self.snapshot.schedule:
                    schedule_metadata = schedule.fetch_metadata_collection()
                    for k, v in schedule_metadata.items():
                        metadata_collection[f"schedule:{k}"] = v

        return metadata_collection

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        include_python_packages: bool = False,
        include_full_metadata: bool = False,
        **kwargs: Any,
    ) -> "PipelineRunResponse":
        """Convert a `PipelineRunSchema` to a `PipelineRunResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            include_python_packages: Whether the python packages will be filled.
            include_full_metadata: Whether the full metadata will be included.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The created `PipelineRunResponse`.

        Raises:
            RuntimeError: if the model creation fails.
        """
        if self.snapshot is not None:
            config = PipelineConfiguration.model_validate_json(
                self.snapshot.pipeline_configuration
            )
            client_environment = json.loads(self.snapshot.client_environment)
        elif self.pipeline_configuration is not None:
            config = PipelineConfiguration.model_validate_json(
                self.pipeline_configuration
            )
            client_environment = (
                json.loads(self.client_environment)
                if self.client_environment
                else {}
            )
        else:
            raise RuntimeError(
                "Pipeline run model creation has failed. Each pipeline run "
                "entry should either have a snapshot_id or "
                "pipeline_configuration."
            )

        config.finalize_substitutions(start_time=self.start_time, inplace=True)

        body = PipelineRunResponseBody(
            user_id=self.user_id,
            project_id=self.project_id,
            status=ExecutionStatus(self.status),
            status_reason=self.status_reason,
            created=self.created,
            updated=self.updated,
            in_progress=self.in_progress,
        )
        metadata = None
        if include_metadata:
            is_templatable = False
            if (
                self.snapshot
                and self.snapshot.build
                and not self.snapshot.build.is_local
                and self.snapshot.build.stack_id
            ):
                is_templatable = True

            orchestrator_environment = (
                json.loads(self.orchestrator_environment)
                if self.orchestrator_environment
                else {}
            )

            if not include_python_packages:
                client_environment.pop("python_packages", None)
                orchestrator_environment.pop("python_packages", None)

            trigger_info: Optional[PipelineRunTriggerInfo] = None
            if self.triggered_by and self.triggered_by_type:
                if (
                    self.triggered_by_type
                    == PipelineRunTriggeredByType.STEP_RUN.value
                ):
                    trigger_info = PipelineRunTriggerInfo(
                        step_run_id=self.triggered_by,
                    )
                elif (
                    self.triggered_by_type
                    == PipelineRunTriggeredByType.DEPLOYMENT.value
                ):
                    trigger_info = PipelineRunTriggerInfo(
                        deployment_id=self.triggered_by,
                    )

            metadata = PipelineRunResponseMetadata(
                run_metadata=self.fetch_metadata(
                    include_full_metadata=include_full_metadata
                ),
                config=config,
                start_time=self.start_time,
                end_time=self.end_time,
                client_environment=client_environment,
                orchestrator_environment=orchestrator_environment,
                orchestrator_run_id=self.orchestrator_run_id,
                code_path=self.snapshot.code_path if self.snapshot else None,
                template_id=self.snapshot.template_id
                if self.snapshot
                else None,
                is_templatable=is_templatable,
                trigger_info=trigger_info,
            )

        resources = None
        if include_resources:
            # Add the client logs as "logs" if they exist, for backwards compatibility
            # TODO: This will be safe to remove in future releases (>0.84.0).
            client_logs = [
                log_entry
                for log_entry in self.logs
                if log_entry.source == "client"
            ]

            if self.snapshot:
                source_snapshot = (
                    self.snapshot.source_snapshot.to_model()
                    if self.snapshot.source_snapshot
                    else None
                )
                stack = (
                    self.snapshot.stack.to_model()
                    if self.snapshot.stack
                    else None
                )
                pipeline: Optional["PipelineResponse"] = (
                    self.snapshot.pipeline.to_model()
                )
                build = (
                    self.snapshot.build.to_model()
                    if self.snapshot.build
                    else None
                )
                schedule = (
                    self.snapshot.schedule.to_model()
                    if self.snapshot.schedule
                    else None
                )
                code_reference = (
                    self.snapshot.code_reference.to_model()
                    if self.snapshot.code_reference
                    else None
                )
            else:
                source_snapshot = None
                stack = self.stack.to_model() if self.stack else None
                pipeline = self.pipeline.to_model() if self.pipeline else None
                build = self.build.to_model() if self.build else None
                schedule = self.schedule.to_model() if self.schedule else None
                code_reference = None

            resources = PipelineRunResponseResources(
                user=self.user.to_model() if self.user else None,
                snapshot=self.snapshot.to_model() if self.snapshot else None,
                source_snapshot=source_snapshot,
                stack=stack,
                pipeline=pipeline,
                build=build,
                schedule=schedule,
                code_reference=code_reference,
                trigger_execution=(
                    self.trigger_execution.to_model()
                    if self.trigger_execution
                    else None
                ),
                model_version=self.model_version.to_model()
                if self.model_version
                else None,
                tags=[tag.to_model() for tag in self.tags],
                logs=client_logs[0].to_model() if client_logs else None,
                log_collection=[log.to_model() for log in self.logs],
                visualizations=[
                    visualization.to_model(
                        include_metadata=False,
                        include_resources=False,
                    )
                    for visualization in self.visualizations
                ],
            )

        return PipelineRunResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )

    def update(self, run_update: "PipelineRunUpdate") -> "PipelineRunSchema":
        """Update a `PipelineRunSchema` with a `PipelineRunUpdate`.

        Args:
            run_update: The `PipelineRunUpdate` to update with.

        Raises:
            ValueError: When trying to update the orchestrator run ID of a
                run that already has a different one.

        Returns:
            The updated `PipelineRunSchema`.
        """
        if run_update.status:
            if (
                run_update.status == ExecutionStatus.PROVISIONING
                and self.status != ExecutionStatus.INITIALIZING.value
            ):
                # This run is already past the provisioning status, so we ignore
                # the update.
                pass
            else:
                self.status = run_update.status.value
                self.end_time = run_update.end_time

                if run_update.status_reason:
                    self.status_reason = run_update.status_reason

            if run_update.is_finished:
                self.in_progress = False
            elif self.snapshot and self.snapshot.is_dynamic:
                # In dynamic pipelines, we can't actually check if the run is
                # in progress by inspecting the DAG. Only once the orchestration
                # container finishes we know for sure.
                pass
            else:
                self.in_progress = self._check_if_run_in_progress()

        if run_update.orchestrator_run_id:
            if (
                self.orchestrator_run_id
                and self.orchestrator_run_id != run_update.orchestrator_run_id
            ):
                raise ValueError(
                    "Updating the orchestrator run ID of a run with an "
                    "existing orchestrator run ID "
                    f"({self.orchestrator_run_id}) is not allowed."
                )
            self.orchestrator_run_id = run_update.orchestrator_run_id

        self.updated = utc_now()
        return self

    def update_placeholder(
        self, request: "PipelineRunRequest"
    ) -> "PipelineRunSchema":
        """Update a placeholder run.

        Args:
            request: The pipeline run request which should replace the
                placeholder.

        Raises:
            RuntimeError: If the DB entry does not represent a placeholder run.
            ValueError: If the run request is not a valid request to replace the
                placeholder run.

        Returns:
            The updated `PipelineRunSchema`.
        """
        if not self.is_placeholder_run():
            raise RuntimeError(
                f"Unable to replace pipeline run {self.id} which is not a "
                "placeholder run."
            )

        if request.is_placeholder_request:
            raise ValueError(
                "Cannot replace a placeholder run with another placeholder run."
            )

        if (
            self.snapshot_id != request.snapshot
            or self.pipeline_id != request.pipeline
            or self.project_id != request.project
        ):
            raise ValueError(
                "Snapshot, project or pipeline ID of placeholder run "
                "do not match the IDs of the run request."
            )

        if not request.orchestrator_run_id:
            raise ValueError(
                "Orchestrator run ID is required to replace a placeholder run."
            )

        if (
            self.orchestrator_run_id
            and self.orchestrator_run_id != request.orchestrator_run_id
        ):
            raise ValueError(
                "Orchestrator run ID of placeholder run does not match the "
                "ID of the run request."
            )

        orchestrator_environment = json.dumps(request.orchestrator_environment)

        self.orchestrator_run_id = request.orchestrator_run_id
        self.orchestrator_environment = orchestrator_environment
        self.status = request.status.value
        self.in_progress = not request.status.is_finished

        self.updated = utc_now()

        return self

    def is_placeholder_run(self) -> bool:
        """Whether the pipeline run is a placeholder run.

        Returns:
            Whether the pipeline run is a placeholder run.
        """
        return self.status in {
            ExecutionStatus.INITIALIZING.value,
            ExecutionStatus.PROVISIONING.value,
        }

    def _check_if_run_in_progress(self) -> bool:
        """Checks whether the run is in progress.

        Raises:
            RuntimeError: If the DB session is missing.

        Returns:
            A flag to indicate whether the run is in progress.
        """
        run_status = ExecutionStatus(self.status)

        if not run_status.is_finished:
            return True

        if run_status == ExecutionStatus.FAILED:
            execution_mode = self.get_pipeline_configuration().execution_mode

            if execution_mode in [
                ExecutionMode.FAIL_FAST,
                ExecutionMode.STOP_ON_FAILURE,
            ]:
                return False

            elif execution_mode == ExecutionMode.CONTINUE_ON_FAILURE:
                from zenml.zen_stores.schemas import StepRunSchema

                if session := object_session(self):
                    step_run_statuses = session.execute(
                        select(StepRunSchema.name, StepRunSchema.status).where(
                            StepRunSchema.pipeline_run_id == self.id
                        )
                    ).all()

                    if self.snapshot and self.snapshot.pipeline_spec:
                        step_dict = self.get_upstream_steps()

                        dag = build_dag(step_dict)

                        failed_steps = {
                            name
                            for name, status in step_run_statuses
                            if ExecutionStatus(status).is_failed
                        }

                        steps_to_skip = set()
                        for failed_step in failed_steps:
                            steps_to_skip.update(
                                find_all_downstream_steps(failed_step, dag)
                            )

                        steps_to_skip.update(failed_steps)

                        steps_statuses = {
                            name: ExecutionStatus(status)
                            for name, status in step_run_statuses
                        }

                        for step_name, _ in step_dict.items():
                            if step_name in steps_to_skip:
                                continue

                            if step_name not in steps_statuses:
                                return True

                            elif not steps_statuses[step_name].is_finished:
                                return True

                        return False
                    else:
                        in_progress = any(
                            not ExecutionStatus(status).is_finished
                            for _, status in step_run_statuses
                        )
                        return in_progress
                else:
                    raise RuntimeError(
                        "Missing DB session to check the in progress "
                        "status of the run."
                    )

        return False
