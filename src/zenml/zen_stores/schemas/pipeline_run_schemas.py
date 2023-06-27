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
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.enums import ExecutionStatus
from zenml.models import (
    PipelineRunRequestModel,
    PipelineRunResponseModel,
    PipelineRunUpdateModel,
    StepRunResponseModel,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.pipeline_build_schemas import PipelineBuildSchema
from zenml.zen_stores.schemas.pipeline_deployment_schemas import (
    PipelineDeploymentSchema,
)
from zenml.zen_stores.schemas.pipeline_schemas import PipelineSchema
from zenml.zen_stores.schemas.schedule_schema import ScheduleSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.stack_schemas import StackSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.logs_schemas import LogsSchema
    from zenml.zen_stores.schemas.run_metadata_schemas import RunMetadataSchema
    from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema


class PipelineRunSchema(NamedSchema, table=True):
    """SQL Model for pipeline runs."""

    __tablename__ = "pipeline_run"

    stack_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackSchema.__tablename__,
        source_column="stack_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    stack: Optional["StackSchema"] = Relationship(back_populates="runs")

    pipeline_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineSchema.__tablename__,
        source_column="pipeline_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    pipeline: Optional["PipelineSchema"] = Relationship(back_populates="runs")

    build_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineBuildSchema.__tablename__,
        source_column="build_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    build: Optional["PipelineBuildSchema"] = Relationship(
        back_populates="runs"
    )

    deployment_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=PipelineDeploymentSchema.__tablename__,
        source_column="deployment_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    deployment: Optional["PipelineDeploymentSchema"] = Relationship(
        back_populates="runs"
    )

    schedule_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=ScheduleSchema.__tablename__,
        source_column="schedule_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    schedule: Optional[ScheduleSchema] = Relationship(back_populates="runs")

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="runs")

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="runs")

    orchestrator_run_id: Optional[str] = Field(nullable=True)

    enable_cache: Optional[bool] = Field(nullable=True)
    enable_artifact_metadata: Optional[bool] = Field(nullable=True)
    start_time: Optional[datetime] = Field(nullable=True)
    end_time: Optional[datetime] = Field(nullable=True, default=None)
    status: ExecutionStatus
    pipeline_configuration: str = Field(sa_column=Column(TEXT, nullable=False))
    num_steps: Optional[int]
    client_version: str
    server_version: Optional[str] = Field(nullable=True)
    client_environment: Optional[str] = Field(
        sa_column=Column(TEXT, nullable=True)
    )
    orchestrator_environment: Optional[str] = Field(
        sa_column=Column(TEXT, nullable=True)
    )
    git_sha: Optional[str] = Field(nullable=True, default=None)  # DEPRECATED

    run_metadata: List["RunMetadataSchema"] = Relationship(
        back_populates="pipeline_run",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    step_runs: List["StepRunSchema"] = Relationship(
        back_populates="pipeline_run",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    logs: Optional["LogsSchema"] = Relationship(
        back_populates="pipeline_run",
        sa_relationship_kwargs={"cascade": "delete", "uselist": False},
    )

    @classmethod
    def from_request(
        cls, request: PipelineRunRequestModel
    ) -> "PipelineRunSchema":
        """Convert a `PipelineRunRequestModel` to a `PipelineRunSchema`.

        Args:
            request: The request to convert.

        Returns:
            The created `PipelineRunSchema`.
        """
        config = request.config
        client_environment = json.dumps(request.client_environment)
        orchestrator_environment = json.dumps(request.orchestrator_environment)

        return cls(
            id=request.id,
            name=request.name,
            orchestrator_run_id=request.orchestrator_run_id,
            stack_id=request.stack,
            workspace_id=request.workspace,
            user_id=request.user,
            pipeline_id=request.pipeline,
            build_id=request.build,
            deployment_id=request.deployment,
            schedule_id=request.schedule_id,
            enable_cache=config.enable_cache,
            enable_artifact_metadata=config.enable_artifact_metadata,
            start_time=request.start_time,
            status=request.status,
            pipeline_configuration=config.json(sort_keys=True),
            num_steps=request.num_steps,
            client_version=request.client_version,
            server_version=request.server_version,
            client_environment=client_environment,
            orchestrator_environment=orchestrator_environment,
        )

    def to_model(
        self,
        steps: Optional[Dict[str, "StepRunResponseModel"]] = None,
    ) -> PipelineRunResponseModel:
        """Convert a `PipelineRunSchema` to a `PipelineRunResponseModel`.

        Args:
            steps: The steps to include in the response.

        Returns:
            The created `PipelineRunResponseModel`.
        """
        client_environment = (
            json.loads(self.client_environment)
            if self.client_environment
            else {}
        )
        orchestrator_environment = (
            json.loads(self.orchestrator_environment)
            if self.orchestrator_environment
            else {}
        )
        metadata = {
            metadata_schema.key: metadata_schema.to_model()
            for metadata_schema in self.run_metadata
        }
        config = PipelineConfiguration.parse_raw(self.pipeline_configuration)

        pipeline = self.pipeline.to_model() if self.pipeline else None
        build = self.build.to_model() if self.build else None
        deployment = self.deployment.to_model() if self.deployment else None
        steps = steps or {}

        return PipelineRunResponseModel(
            id=self.id,
            name=self.name,
            stack=self.stack.to_model() if self.stack else None,
            workspace=self.workspace.to_model(),
            user=self.user.to_model(True) if self.user else None,
            orchestrator_run_id=self.orchestrator_run_id,
            start_time=self.start_time,
            end_time=self.end_time,
            status=self.status,
            pipeline=pipeline,
            build=build,
            deployment=deployment,
            schedule_id=self.schedule_id,
            config=config,
            num_steps=self.num_steps,
            client_version=self.client_version,
            server_version=self.server_version,
            client_environment=client_environment,
            orchestrator_environment=orchestrator_environment,
            created=self.created,
            updated=self.updated,
            metadata=metadata,
            steps=steps,
        )

    def update(
        self, run_update: "PipelineRunUpdateModel"
    ) -> "PipelineRunSchema":
        """Update a `PipelineRunSchema` with a `PipelineRunUpdateModel`.

        Args:
            run_update: The `PipelineRunUpdateModel` to update with.

        Returns:
            The updated `PipelineRunSchema`.
        """
        if run_update.status:
            self.status = run_update.status
            self.end_time = run_update.end_time

        self.updated = datetime.utcnow()
        return self
