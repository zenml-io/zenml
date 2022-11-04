import json
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, Relationship

from zenml.new_models import RunModel
from zenml.zen_stores.schemas.base_schemas import ProjectScopedSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import (
        PipelineSchema,
        ProjectSchema,
        StackSchema,
        UserSchema,
    )


class PipelineRunSchema(ProjectScopedSchema, table=True):
    """SQL Model for pipeline runs."""

    name: str
    pipeline_configuration: str = Field(max_length=4096)
    num_steps: int
    zenml_version: str
    git_sha: Optional[str] = Field(nullable=True)
    mlmd_id: int = Field(default=None, nullable=True)
    stack_id: Optional[UUID] = Field(
        nullable=True,
        sa_column=Column(ForeignKey("stackschema.id", ondelete="SET NULL")),
    )
    pipeline_id: Optional[UUID] = Field(
        nullable=True,
        sa_column=Column(ForeignKey("pipelineschema.id", ondelete="SET NULL")),
    )

    project: "ProjectSchema" = Relationship(back_populates="runs")
    user: "UserSchema" = Relationship(back_populates="runs")
    stack: "StackSchema" = Relationship(back_populates="runs")
    pipeline: "PipelineSchema" = Relationship(back_populates="runs")

    def to_model(self, _block_recursion: bool = False) -> RunModel:
        """Convert a `PipelineRunSchema` to a `PipelineRunModel`.

        Returns:
            The created `PipelineRunModel`.
        """
        if _block_recursion:
            return RunModel(
                id=self.id,
                name=self.name,
                stack_id=self.stack.to_model(),
                project=self.project.to_model(),
                user=self.user.to_model(),
                pipeline_configuration=json.loads(self.pipeline_configuration),
                num_steps=self.num_steps,
                git_sha=self.git_sha,
                zenml_version=self.zenml_version,
                mlmd_id=self.mlmd_id,
                created=self.created,
                updated=self.updated,
            )
        else:
            return RunModel(
                id=self.id,
                name=self.name,
                stack_id=self.stack.to_model(),
                project=self.project.to_model(),
                user=self.user.to_model(),
                pipeline=self.pipeline.to_model(not _block_recursion),
                pipeline_configuration=json.loads(self.pipeline_configuration),
                num_steps=self.num_steps,
                git_sha=self.git_sha,
                zenml_version=self.zenml_version,
                mlmd_id=self.mlmd_id,
                created=self.created,
                updated=self.updated,
            )
