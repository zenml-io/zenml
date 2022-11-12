import json
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Column, ForeignKey, TEXT
from sqlmodel import Field, Relationship

from zenml.enums import ExecutionStatus
from zenml.new_models import PipelineRunResponseModel
from zenml.zen_stores.schemas.base_schemas import NamedSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import (
        PipelineSchema,
        ProjectSchema,
        StackSchema,
        UserSchema,
    )


class PipelineRunSchema(NamedSchema, table=True):
    """SQL Model for pipeline runs."""

    pipeline_configuration: str = Field(sa_column=Column(TEXT, nullable=False))
    num_steps: int
    zenml_version: str
    git_sha: Optional[str] = Field(nullable=True)
    mlmd_id: Optional[int] = Field(default=None, nullable=True)
    stack_id: Optional[UUID] = Field(
        nullable=True,
        sa_column=Column(ForeignKey("stackschema.id", ondelete="SET NULL")),
    )
    pipeline_id: Optional[UUID] = Field(
        nullable=True,
        sa_column=Column(ForeignKey("pipelineschema.id", ondelete="SET NULL")),
    )
    user_id: UUID = Field(
        sa_column=Column(ForeignKey("userschema.id", ondelete="SET NULL"))
    )
    project_id: UUID = Field(
        sa_column=Column(ForeignKey("projectschema.id", ondelete="CASCADE"))
    )
    project: "ProjectSchema" = Relationship(back_populates="runs")
    user: "UserSchema" = Relationship(back_populates="runs")
    stack: "StackSchema" = Relationship(back_populates="runs")
    pipeline: "PipelineSchema" = Relationship(back_populates="runs")
    orchestrator_run_id: Optional[str] = Field(nullable=True)

    status: ExecutionStatus

    def to_model(
        self, _block_recursion: bool = False
    ) -> PipelineRunResponseModel:
        """Convert a `PipelineRunSchema` to a `PipelineRunResponseModel`.

        Returns:
            The created `PipelineRunResponseModel`.
        """
        if _block_recursion:
            return PipelineRunResponseModel(
                id=self.id,
                name=self.name,
                stack_id=self.stack.to_model(),
                project=self.project.to_model(),
                user=self.user.to_model(),
                orchestrator_run_id=self.orchestrator_run_id,
                status=self.status,
                pipeline_configuration=json.loads(self.pipeline_configuration),
                num_steps=self.num_steps,
                git_sha=self.git_sha,
                zenml_version=self.zenml_version,
                mlmd_id=self.mlmd_id,
                created=self.created,
                updated=self.updated,
            )
        else:
            return PipelineRunResponseModel(
                id=self.id,
                name=self.name,
                stack_id=self.stack.to_model(),
                project=self.project.to_model(),
                user=self.user.to_model(),
                orchestrator_run_id=self.orchestrator_run_id,
                status=self.status,
                pipeline=self.pipeline.to_model(not _block_recursion),
                pipeline_configuration=json.loads(self.pipeline_configuration),
                num_steps=self.num_steps,
                git_sha=self.git_sha,
                zenml_version=self.zenml_version,
                mlmd_id=self.mlmd_id,
                created=self.created,
                updated=self.updated,
            )
