import json
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from zenml.new_models.step_run_models import (
    StepRunRequestModel,
    StepRunResponseModel,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema

if TYPE_CHECKING:
    pass


class StepRunOrderSchema(SQLModel, table=True):
    """SQL Model that defines the order of steps."""

    parent_id: UUID = Field(foreign_key="steprunschema.id", primary_key=True)
    child_id: UUID = Field(foreign_key="steprunschema.id", primary_key=True)


class StepInputArtifactSchema(SQLModel, table=True):
    """SQL Model that defines which artifacts are inputs to which step."""

    step_id: UUID = Field(foreign_key="steprunschema.id", primary_key=True)
    artifact_id: UUID = Field(foreign_key="artifactschema.id", primary_key=True)
    name: str  # Name of the input in the step


class StepRunSchema(BaseSchema, table=True):
    """SQL Model for steps of pipeline runs."""

    name: str

    pipeline_run_id: UUID = Field(foreign_key="pipelinerunschema.id")

    entrypoint_name: str
    parameters: str = Field(max_length=4096)
    step_configuration: str = Field(max_length=4096)
    docstring: Optional[str] = Field(max_length=4096, nullable=True)

    mlmd_id: int = Field(default=None, nullable=True)

    @classmethod
    def from_request(cls, request: StepRunRequestModel):
        return cls(
            name=request.name,
            pipeline_run_id=request.pipeline_run_id,
            entrypoint_name=request.entrypoint_name,
            parameters=json.dumps(request.parameters),
            step_configuration=json.dumps(request.step_configuration),
            docstring=request.docstring,
            mlmd_id=request.mlmd_id,
        )

    def to_model(
        self, parent_step_ids: List[UUID], mlmd_parent_step_ids: List[int]
    ) -> StepRunResponseModel:
        """Convert a `StepRunSchema` to a `StepRunModel`.

        Args:
            parent_step_ids: The parent step ids to link to the step.
            mlmd_parent_step_ids: The parent step ids in MLMD.

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
            mlmd_id=self.mlmd_id,
            mlmd_parent_step_ids=mlmd_parent_step_ids,
            created=self.created,
            updated=self.updated,
        )
