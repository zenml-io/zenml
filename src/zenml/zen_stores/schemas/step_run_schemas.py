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
"""SQLModel implementation of step run tables."""
import json
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship, SQLModel

from zenml.config.step_configurations import Step
from zenml.enums import ExecutionStatus
from zenml.models.step_run_models import (
    StepRunRequestModel,
    StepRunResponseModel,
    StepRunUpdateModel,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.pipeline_deployment_schemas import (
    PipelineDeploymentSchema,
)
from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.artifact_schemas import ArtifactSchema
    from zenml.zen_stores.schemas.logs_schemas import LogsSchema
    from zenml.zen_stores.schemas.run_metadata_schemas import RunMetadataSchema


class StepRunSchema(NamedSchema, table=True):
    """SQL Model for steps of pipeline runs."""

    __tablename__ = "step_run"

    # Fields
    start_time: Optional[datetime] = Field(nullable=True)
    end_time: Optional[datetime] = Field(nullable=True)
    status: ExecutionStatus = Field(nullable=False)

    docstring: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    cache_key: Optional[str] = Field(nullable=True)
    source_code: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    code_hash: Optional[str] = Field(nullable=True)

    # Foreign keys
    original_step_run_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=__tablename__,
        source_column="original_step_run_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    deployment_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=PipelineDeploymentSchema.__tablename__,
        source_column="deployment_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    pipeline_run_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=PipelineRunSchema.__tablename__,
        source_column="pipeline_run_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
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

    # Relationships
    workspace: "WorkspaceSchema" = Relationship(back_populates="step_runs")
    user: Optional["UserSchema"] = Relationship(back_populates="step_runs")
    deployment: "PipelineDeploymentSchema" = Relationship(
        back_populates="step_runs"
    )
    run_metadata: List["RunMetadataSchema"] = Relationship(
        back_populates="step_run", sa_relationship_kwargs={"cascade": "delete"}
    )
    input_artifacts: List["StepRunInputArtifactSchema"] = Relationship(
        sa_relationship_kwargs={"cascade": "delete"}
    )
    output_artifacts: List["StepRunOutputArtifactSchema"] = Relationship(
        sa_relationship_kwargs={"cascade": "delete"}
    )
    logs: Optional["LogsSchema"] = Relationship(
        back_populates="step_run",
        sa_relationship_kwargs={"cascade": "delete", "uselist": False},
    )
    parents: List["StepRunParentsSchema"] = Relationship(
        sa_relationship_kwargs={
            "cascade": "delete",
            "primaryjoin": "StepRunParentsSchema.child_id == StepRunSchema.id",
        },
    )

    @classmethod
    def from_request(cls, request: StepRunRequestModel) -> "StepRunSchema":
        """Create a step run schema from a step run request model.

        Args:
            request: The step run request model.

        Returns:
            The step run schema.
        """
        return cls(
            name=request.name,
            workspace_id=request.workspace,
            user_id=request.user,
            start_time=request.start_time,
            end_time=request.end_time,
            status=request.status,
            original_step_run_id=request.original_step_run_id,
            pipeline_run_id=request.pipeline_run_id,
            deployment_id=request.deployment,
            docstring=request.docstring,
            cache_key=request.cache_key,
            code_hash=request.code_hash,
            source_code=request.source_code,
        )

    def to_model(self) -> StepRunResponseModel:
        """Convert a `StepRunSchema` to a `StepRunModel`.

        Returns:
            The created StepRunModel.
        """
        metadata = {
            metadata_schema.key: metadata_schema.to_model()
            for metadata_schema in self.run_metadata
        }

        input_artifacts = {
            artifact.name: artifact.artifact.to_model()
            for artifact in self.input_artifacts
        }

        output_artifacts = {
            artifact.name: artifact.artifact.to_model()
            for artifact in self.output_artifacts
        }

        full_step_config = Step.parse_obj(
            json.loads(self.deployment.step_configurations)[self.name]
        )

        return StepRunResponseModel(
            id=self.id,
            # Attributes from the StepRunBaseModel
            name=self.name,
            start_time=self.start_time,
            end_time=self.end_time,
            status=self.status,
            cache_key=self.cache_key,
            code_hash=self.code_hash,
            docstring=self.docstring,
            source_code=self.source_code,
            config=full_step_config.config,
            spec=full_step_config.spec,
            deployment_id=self.deployment_id,
            pipeline_run_id=self.pipeline_run_id,
            original_step_run_id=self.original_step_run_id,
            parent_step_ids=[p.parent_id for p in self.parents],
            # Attributes from the WorkspaceScopedResponseModel
            user=self.deployment.user.to_model(_block_recursion=True)
            if self.deployment.user
            else None,
            workspace=self.deployment.workspace.to_model(),
            created=self.created,
            updated=self.updated,
            # Attributes from the StepRunResponseModel
            inputs=input_artifacts,
            outputs=output_artifacts,
            metadata=metadata,
            logs=self.logs.to_model() if self.logs else None,
        )

    def update(self, step_update: StepRunUpdateModel) -> "StepRunSchema":
        """Update a step run schema with a step run update model.

        Args:
            step_update: The step run update model.

        Returns:
            The updated step run schema.
        """
        for key, value in step_update.dict(
            exclude_unset=True, exclude_none=True
        ).items():
            if key == "status":
                self.status = value
            if key == "end_time":
                self.end_time = value

        self.updated = datetime.utcnow()

        return self


class StepRunParentsSchema(SQLModel, table=True):
    """SQL Model that defines the order of steps."""

    __tablename__ = "step_run_parents"

    # Foreign Keys
    parent_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="parent_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )
    child_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="child_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )


class StepRunInputArtifactSchema(SQLModel, table=True):
    """SQL Model that defines which artifacts are inputs to which step."""

    __tablename__ = "step_run_input_artifact"

    # Fields
    name: str = Field(nullable=False, primary_key=True)

    # Foreign keys
    step_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="step_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )
    artifact_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="artifact",  # TODO: Find a way for ArtifactSchema.__tablename__
        source_column="artifact_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )

    # Relationships
    step_run: "StepRunSchema" = Relationship(back_populates="input_artifacts")
    artifact: "ArtifactSchema" = Relationship()


class StepRunOutputArtifactSchema(SQLModel, table=True):
    """SQL Model that defines which artifacts are outputs of which step."""

    __tablename__ = "step_run_output_artifact"

    # Fields
    name: str

    # Foreign keys
    step_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="step_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )

    artifact_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="artifact",  # TODO: Find a way for ArtifactSchema.__tablename__
        source_column="artifact_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )

    # Relationship
    step_run: "StepRunSchema" = Relationship(back_populates="output_artifacts")
    artifact: "ArtifactSchema" = Relationship(
        back_populates="output_of_step_runs"
    )
