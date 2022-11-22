import json
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, SQLModel

from zenml.enums import ExecutionStatus
from zenml.models.step_run_models import (
    StepRunRequestModel,
    StepRunResponseModel,
    StepRunUpdateModel,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field


class StepRunSchema(NamedSchema, table=True):
    """SQL Model for steps of pipeline runs."""

    __tablename__ = "step_run"

    pipeline_run_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=PipelineRunSchema.__tablename__,
        source_column="pipeline_run_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    status: ExecutionStatus
    entrypoint_name: str

    parameters: str = Field(sa_column=Column(TEXT, nullable=False))
    step_configuration: str = Field(sa_column=Column(TEXT, nullable=False))
    docstring: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    num_outputs: Optional[int]

    mlmd_id: Optional[int] = Field(default=None, nullable=True)

    @classmethod
    def from_request(cls, request: StepRunRequestModel) -> "StepRunSchema":
        return cls(
            name=request.name,
            pipeline_run_id=request.pipeline_run_id,
            entrypoint_name=request.entrypoint_name,
            parameters=json.dumps(request.parameters),
            step_configuration=json.dumps(request.step_configuration),
            docstring=request.docstring,
            mlmd_id=request.mlmd_id,
            num_outputs=request.num_outputs,
            status=request.status,
        )

    def to_model(
        self,
        parent_step_ids: List[UUID],
        mlmd_parent_step_ids: List[int],
        input_artifacts: Dict[str, UUID],
    ) -> StepRunResponseModel:
        """Convert a `StepRunSchema` to a `StepRunModel`.

        Args:
            parent_step_ids: The parent step ids to link to the step.
            mlmd_parent_step_ids: The parent step ids in MLMD.
            input_artifacts:

        Returns:
            The created StepRunModel.
        """
        return StepRunResponseModel(
            id=self.id,
            name=self.name,
            pipeline_run_id=self.pipeline_run_id,
            parent_step_ids=parent_step_ids,
            entrypoint_name=self.entrypoint_name,
            parameters=json.loads(self.parameters),
            step_configuration=json.loads(self.step_configuration),
            docstring=self.docstring,
            status=self.status,
            mlmd_id=self.mlmd_id,
            mlmd_parent_step_ids=mlmd_parent_step_ids,
            created=self.created,
            updated=self.updated,
            input_artifacts=input_artifacts,
            num_outputs=self.num_outputs,
        )

    def update(self, step_update: StepRunUpdateModel) -> "StepRunSchema":
        """For steps only the execution status is mutable"""
        if "status" in step_update.__fields_set__ and step_update.status:
            self.status = step_update.status

        self.updated = datetime.now()

        return self


class StepRunParentsSchema(SQLModel, table=True):
    """SQL Model that defines the order of steps."""

    __tablename__ = "step_run_parents"

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


class StepRunArtifactSchema(SQLModel, table=True):
    """SQL Model that defines which artifacts are inputs to which step."""

    __tablename__ = "step_run_artifact"

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
        target="artifacts",  # ArtifactSchema.__tablename__,
        source_column="artifact_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )
    name: str  # Name of the input in the step
