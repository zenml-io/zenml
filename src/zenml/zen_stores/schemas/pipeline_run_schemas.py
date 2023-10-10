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
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import TEXT, Column, Field, Relationship

from zenml.enums import ExecutionStatus
from zenml.models import (
    PipelineRunRequestModel,
    PipelineRunResponseModel,
    PipelineRunUpdateModel,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.pipeline_deployment_schemas import (
    PipelineDeploymentSchema,
)
from zenml.zen_stores.schemas.pipeline_schemas import PipelineSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.logs_schemas import LogsSchema
    from zenml.zen_stores.schemas.model_schemas import (
        ModelVersionPipelineRunSchema,
    )
    from zenml.zen_stores.schemas.run_metadata_schemas import RunMetadataSchema
    from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema


class PipelineRunSchema(NamedSchema, table=True):
    """SQL Model for pipeline runs."""

    __tablename__ = "pipeline_run"

    # Fields
    orchestrator_run_id: Optional[str] = Field(nullable=True)
    start_time: Optional[datetime] = Field(nullable=True)
    end_time: Optional[datetime] = Field(nullable=True, default=None)
    status: ExecutionStatus = Field(nullable=False)
    orchestrator_environment: Optional[str] = Field(
        sa_column=Column(TEXT, nullable=True)
    )

    # Foreign keys
    deployment_id: UUID = build_foreign_key_field(
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

    # Relationships
    deployment: "PipelineDeploymentSchema" = Relationship(
        back_populates="pipeline_runs"
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="runs")
    user: Optional["UserSchema"] = Relationship(back_populates="runs")
    run_metadata: List["RunMetadataSchema"] = Relationship(
        back_populates="pipeline_run",
        sa_relationship_kwargs={"cascade": "delete"},
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
        orchestrator_environment = json.dumps(request.orchestrator_environment)

        return cls(
            id=request.id,
            workspace_id=request.workspace,
            user_id=request.user,
            name=request.name,
            orchestrator_run_id=request.orchestrator_run_id,
            orchestrator_environment=orchestrator_environment,
            start_time=request.start_time,
            status=request.status,
            pipeline_id=request.pipeline,
            deployment_id=request.deployment,
        )

    def to_model(self) -> PipelineRunResponseModel:
        """Convert a `PipelineRunSchema` to a `PipelineRunResponseModel`.

        Returns:
            The created `PipelineRunResponseModel`.
        """
        orchestrator_environment = (
            json.loads(self.orchestrator_environment)
            if self.orchestrator_environment
            else {}
        )

        metadata = {
            metadata_schema.key: metadata_schema.to_model()
            for metadata_schema in self.run_metadata
        }

        steps = {s.name: s.to_model() for s in self.deployment.step_runs}

        deployment = self.deployment.to_model()

        return PipelineRunResponseModel(
            id=self.id,
            user=deployment.user,
            workspace=deployment.workspace,
            # Attributes of the PipelineRunBaseModel
            name=self.name,
            start_time=self.start_time,
            end_time=self.end_time,
            status=self.status,
            config=deployment.pipeline_configuration,
            orchestrator_run_id=self.orchestrator_run_id,
            client_version=deployment.client_version,
            server_version=deployment.server_version,
            client_environment=deployment.client_environment,
            orchestrator_environment=orchestrator_environment,
            # Attributes of the WorkspaceScopedResponseModel
            created=self.created,
            updated=self.updated,
            # Attributes of the PipelineRunResponseModel
            stack=deployment.stack,
            pipeline=deployment.pipeline,
            build=deployment.build,
            schedule=deployment.schedule,
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
