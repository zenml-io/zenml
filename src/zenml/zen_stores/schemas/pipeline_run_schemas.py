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
from typing import TYPE_CHECKING, Any, List, Optional
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import TEXT, Column, Field, Relationship

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.enums import (
    ExecutionStatus,
    MetadataResourceTypes,
    TaggableResourceTypes,
)
from zenml.models import (
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineRunResponseBody,
    PipelineRunResponseMetadata,
    PipelineRunUpdate,
)
from zenml.models.v2.core.pipeline_run import PipelineRunResponseResources
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.constants import MODEL_VERSION_TABLENAME
from zenml.zen_stores.schemas.pipeline_build_schemas import PipelineBuildSchema
from zenml.zen_stores.schemas.pipeline_deployment_schemas import (
    PipelineDeploymentSchema,
)
from zenml.zen_stores.schemas.pipeline_schemas import PipelineSchema
from zenml.zen_stores.schemas.schedule_schema import ScheduleSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.stack_schemas import StackSchema
from zenml.zen_stores.schemas.trigger_schemas import TriggerExecutionSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.logs_schemas import LogsSchema
    from zenml.zen_stores.schemas.model_schemas import (
        ModelVersionPipelineRunSchema,
        ModelVersionSchema,
    )
    from zenml.zen_stores.schemas.run_metadata_schemas import RunMetadataSchema
    from zenml.zen_stores.schemas.service_schemas import ServiceSchema
    from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema
    from zenml.zen_stores.schemas.tag_schemas import TagResourceSchema


class PipelineRunSchema(NamedSchema, table=True):
    """SQL Model for pipeline runs."""

    __tablename__ = "pipeline_run"
    __table_args__ = (
        UniqueConstraint(
            "deployment_id",
            "orchestrator_run_id",
            name="unique_orchestrator_run_id_for_deployment_id",
        ),
    )

    # Fields
    orchestrator_run_id: Optional[str] = Field(nullable=True)
    start_time: Optional[datetime] = Field(nullable=True)
    end_time: Optional[datetime] = Field(nullable=True, default=None)
    status: str = Field(nullable=False)
    orchestrator_environment: Optional[str] = Field(
        sa_column=Column(TEXT, nullable=True)
    )

    # Foreign keys
    deployment_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineDeploymentSchema.__tablename__,
        source_column="deployment_id",
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
    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
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
    deployment: Optional["PipelineDeploymentSchema"] = Relationship(
        back_populates="pipeline_runs"
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="runs")
    user: Optional["UserSchema"] = Relationship(back_populates="runs")
    run_metadata: List["RunMetadataSchema"] = Relationship(
        back_populates="pipeline_run",
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(RunMetadataSchema.resource_type=='{MetadataResourceTypes.PIPELINE_RUN.value}', foreign(RunMetadataSchema.resource_id)==PipelineRunSchema.id)",
            cascade="delete",
            overlaps="run_metadata",
        ),
    )
    logs: Optional["LogsSchema"] = Relationship(
        back_populates="pipeline_run",
        sa_relationship_kwargs={"cascade": "delete", "uselist": False},
    )
    model_versions_pipeline_runs_links: List[
        "ModelVersionPipelineRunSchema"
    ] = Relationship(
        back_populates="pipeline_run",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    step_runs: List["StepRunSchema"] = Relationship(
        sa_relationship_kwargs={"cascade": "delete"},
    )
    configured_model_version: "ModelVersionSchema" = Relationship(
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
    pipeline: Optional["PipelineSchema"] = Relationship(back_populates="runs")
    trigger_execution: Optional["TriggerExecutionSchema"] = Relationship()

    services: List["ServiceSchema"] = Relationship(
        back_populates="pipeline_run",
    )
    tags: List["TagResourceSchema"] = Relationship(
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(TagResourceSchema.resource_type=='{TaggableResourceTypes.PIPELINE_RUN.value}', foreign(TagResourceSchema.resource_id)==PipelineRunSchema.id)",
            cascade="delete",
            overlaps="tags",
        ),
    )

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

        return cls(
            workspace_id=request.workspace,
            user_id=request.user,
            name=request.name,
            orchestrator_run_id=request.orchestrator_run_id,
            orchestrator_environment=orchestrator_environment,
            start_time=request.start_time,
            status=request.status.value,
            pipeline_id=request.pipeline,
            deployment_id=request.deployment,
            trigger_execution_id=request.trigger_execution_id,
            model_version_id=request.model_version_id,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> "PipelineRunResponse":
        """Convert a `PipelineRunSchema` to a `PipelineRunResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The created `PipelineRunResponse`.

        Raises:
            RuntimeError: if the model creation fails.
        """
        orchestrator_environment = (
            json.loads(self.orchestrator_environment)
            if self.orchestrator_environment
            else {}
        )

        run_metadata = {
            metadata_schema.key: metadata_schema.to_model()
            for metadata_schema in self.run_metadata
        }

        if self.deployment is not None:
            deployment = self.deployment.to_model()

            config = deployment.pipeline_configuration
            client_environment = deployment.client_environment

            stack = deployment.stack
            pipeline = deployment.pipeline
            build = deployment.build
            schedule = deployment.schedule
            code_reference = deployment.code_reference

        elif self.pipeline_configuration is not None:
            config = PipelineConfiguration.model_validate_json(
                self.pipeline_configuration
            )
            client_environment = (
                json.loads(self.client_environment)
                if self.client_environment
                else {}
            )

            stack = self.stack.to_model() if self.stack else None
            pipeline = self.pipeline.to_model() if self.pipeline else None
            build = self.build.to_model() if self.build else None
            schedule = self.schedule.to_model() if self.schedule else None
            code_reference = None

        else:
            raise RuntimeError(
                "Pipeline run model creation has failed. Each pipeline run "
                "entry should either have a deployment_id or "
                "pipeline_configuration."
            )

        body = PipelineRunResponseBody(
            user=self.user.to_model() if self.user else None,
            status=ExecutionStatus(self.status),
            stack=stack,
            pipeline=pipeline,
            build=build,
            schedule=schedule,
            code_reference=code_reference,
            trigger_execution=self.trigger_execution.to_model()
            if self.trigger_execution
            else None,
            created=self.created,
            updated=self.updated,
            deployment_id=self.deployment_id,
            model_version_id=self.model_version_id,
        )
        metadata = None
        if include_metadata:
            steps = {step.name: step.to_model() for step in self.step_runs}

            metadata = PipelineRunResponseMetadata(
                workspace=self.workspace.to_model(),
                run_metadata=run_metadata,
                config=config,
                steps=steps,
                start_time=self.start_time,
                end_time=self.end_time,
                client_environment=client_environment,
                orchestrator_environment=orchestrator_environment,
                orchestrator_run_id=self.orchestrator_run_id,
                code_path=self.deployment.code_path
                if self.deployment
                else None,
                template_id=self.deployment.template_id
                if self.deployment
                else None,
            )

        resources = None
        if include_resources:
            model_version = None
            if self.configured_model_version:
                model_version = self.configured_model_version.to_model()

            resources = PipelineRunResponseResources(
                model_version=model_version,
                tags=[t.tag.to_model() for t in self.tags],
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

        Returns:
            The updated `PipelineRunSchema`.
        """
        if run_update.status:
            self.status = run_update.status.value
            self.end_time = run_update.end_time
        if run_update.model_version_id and self.model_version_id is None:
            self.model_version_id = run_update.model_version_id

        self.updated = datetime.utcnow()
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
            ValueError: If the run request does not match the deployment or
                pipeline ID of the placeholder run.

        Returns:
            The updated `PipelineRunSchema`.
        """
        if (
            self.orchestrator_run_id
            or self.status != ExecutionStatus.INITIALIZING
        ):
            raise RuntimeError(
                f"Unable to replace pipeline run {self.id} which is not a "
                "placeholder run."
            )

        if (
            self.deployment_id != request.deployment
            or self.pipeline_id != request.pipeline
        ):
            raise ValueError(
                "Deployment or orchestrator run ID of placeholder run do not "
                "match the IDs of the run request."
            )

        orchestrator_environment = json.dumps(request.orchestrator_environment)

        self.orchestrator_run_id = request.orchestrator_run_id
        self.orchestrator_environment = orchestrator_environment
        self.status = request.status.value

        self.updated = datetime.utcnow()

        return self
