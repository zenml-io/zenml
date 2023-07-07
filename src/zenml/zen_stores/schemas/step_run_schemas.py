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
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from pydantic.json import pydantic_encoder
from sqlalchemy import TEXT, Column, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlmodel import Field, Relationship, SQLModel

from zenml.config.step_configurations import Step
from zenml.constants import STEP_SOURCE_PARAMETER_NAME
from zenml.enums import ExecutionStatus
from zenml.models.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.models.step_run_models import (
    StepRunRequestModel,
    StepRunResponseModel,
    StepRunUpdateModel,
)
from zenml.zen_stores.schemas.artifact_schemas import ArtifactSchema
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.models import ArtifactResponseModel
    from zenml.zen_stores.schemas.logs_schemas import LogsSchema
    from zenml.zen_stores.schemas.run_metadata_schemas import RunMetadataSchema


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
    pipeline_run: "PipelineRunSchema" = Relationship(
        back_populates="step_runs"
    )
    original_step_run_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=__tablename__,
        source_column="original_step_run_id",
        target_column="id",
        ondelete="SET NULL",
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
    user: Optional["UserSchema"] = Relationship(back_populates="step_runs")

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="step_runs")

    enable_cache: Optional[bool] = Field(nullable=True)
    enable_artifact_metadata: Optional[bool] = Field(nullable=True)
    code_hash: Optional[str] = Field(nullable=True)
    cache_key: Optional[str] = Field(nullable=True)
    start_time: Optional[datetime] = Field(nullable=True)
    end_time: Optional[datetime] = Field(nullable=True)
    status: ExecutionStatus
    entrypoint_name: str
    parameters: str = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=False,
        )
    )
    step_configuration: str = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=False,
        )
    )
    caching_parameters: Optional[str] = Field(
        sa_column=Column(TEXT, nullable=True)
    )
    docstring: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    source_code: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    num_outputs: Optional[int]

    run_metadata: List["RunMetadataSchema"] = Relationship(
        back_populates="step_run", sa_relationship_kwargs={"cascade": "delete"}
    )
    input_artifacts: List["StepRunInputArtifactSchema"] = Relationship(
        back_populates="step_run", sa_relationship_kwargs={"cascade": "delete"}
    )
    output_artifacts: List["StepRunOutputArtifactSchema"] = Relationship(
        back_populates="step_run", sa_relationship_kwargs={"cascade": "delete"}
    )
    logs: Optional["LogsSchema"] = Relationship(
        back_populates="step_run",
        sa_relationship_kwargs={"cascade": "delete", "uselist": False},
    )
    parents: List["StepRunParentsSchema"] = Relationship(
        back_populates="child",
        sa_relationship_kwargs={
            "cascade": "delete",
            "primaryjoin": "StepRunParentsSchema.child_id == StepRunSchema.id",
        },
    )
    children: List["StepRunParentsSchema"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={
            "cascade": "delete",
            "primaryjoin": "StepRunParentsSchema.parent_id == StepRunSchema.id",
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
        step_config = request.config
        full_step_config = Step(spec=request.spec, config=request.config)
        return cls(
            name=request.name,
            pipeline_run_id=request.pipeline_run_id,
            original_step_run_id=request.original_step_run_id,
            workspace_id=request.workspace,
            user_id=request.user,
            enable_cache=step_config.enable_cache,
            enable_artifact_metadata=step_config.enable_artifact_metadata,
            code_hash=step_config.caching_parameters.get(
                STEP_SOURCE_PARAMETER_NAME
            ),
            cache_key=request.cache_key,
            start_time=request.start_time,
            end_time=request.end_time,
            entrypoint_name=step_config.name,
            parameters=json.dumps(
                step_config.parameters,
                default=pydantic_encoder,
                sort_keys=True,
            ),
            step_configuration=full_step_config.json(sort_keys=True),
            caching_parameters=json.dumps(
                step_config.caching_parameters,
                default=pydantic_encoder,
                sort_keys=True,
            ),
            docstring=request.docstring,
            source_code=request.source_code,
            num_outputs=len(step_config.outputs),
            status=request.status,
        )

    def to_model(
        self,
        parent_step_ids: List[UUID],
        input_artifacts: Dict[str, "ArtifactResponseModel"],
        output_artifacts: Dict[str, "ArtifactResponseModel"],
    ) -> StepRunResponseModel:
        """Convert a `StepRunSchema` to a `StepRunModel`.

        Args:
            parent_step_ids: The parent step ids to link to the step.
            input_artifacts: The input artifacts to link to the step.
            output_artifacts: The output artifacts to link to the step.

        Returns:
            The created StepRunModel.
        """
        metadata = {
            metadata_schema.key: metadata_schema.to_model()
            for metadata_schema in self.run_metadata
        }
        full_step_config = Step.parse_raw(self.step_configuration)
        return StepRunResponseModel(
            id=self.id,
            name=self.name,
            pipeline_run_id=self.pipeline_run_id,
            original_step_run_id=self.original_step_run_id,
            workspace=self.workspace.to_model(),
            user=self.user.to_model() if self.user else None,
            parent_step_ids=parent_step_ids,
            cache_key=self.cache_key,
            start_time=self.start_time,
            end_time=self.end_time,
            config=full_step_config.config,
            spec=full_step_config.spec,
            status=self.status,
            docstring=self.docstring,
            source_code=self.source_code,
            created=self.created,
            updated=self.updated,
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

    parent_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="parent_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )
    parent: StepRunSchema = Relationship(
        back_populates="children",
        sa_relationship_kwargs={
            "primaryjoin": "StepRunParentsSchema.parent_id == StepRunSchema.id"
        },
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
    child: StepRunSchema = Relationship(
        back_populates="parents",
        sa_relationship_kwargs={
            "primaryjoin": "StepRunParentsSchema.child_id == StepRunSchema.id"
        },
    )


class StepRunInputArtifactSchema(SQLModel, table=True):
    """SQL Model that defines which artifacts are inputs to which step."""

    __tablename__ = "step_run_input_artifact"

    step_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="step_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )
    step_run: StepRunSchema = Relationship(back_populates="input_artifacts")
    artifact_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ArtifactSchema.__tablename__,
        source_column="artifact_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )
    artifact: ArtifactSchema = Relationship(
        back_populates="input_to_step_runs"
    )
    name: str = Field(nullable=False, primary_key=True)


class StepRunOutputArtifactSchema(SQLModel, table=True):
    """SQL Model that defines which artifacts are outputs of which step."""

    __tablename__ = "step_run_output_artifact"

    step_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="step_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )
    step_run: StepRunSchema = Relationship(back_populates="output_artifacts")
    artifact_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ArtifactSchema.__tablename__,
        source_column="artifact_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )
    artifact: ArtifactSchema = Relationship(
        back_populates="output_of_step_runs"
    )
    name: str
