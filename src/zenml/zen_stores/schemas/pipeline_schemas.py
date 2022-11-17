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
"""SQL Model Implementations for Pipelines and Pipeline Runs."""

import json
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship, SQLModel

from zenml.config.pipeline_configurations import PipelineSpec
from zenml.enums import ArtifactType, ExecutionStatus
from zenml.models import PipelineModel, PipelineRunModel
from zenml.models.pipeline_models import ArtifactModel, StepRunModel
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.stack_schemas import StackSchema
from zenml.zen_stores.schemas.user_management_schemas import UserSchema


class PipelineSchema(SQLModel, table=True):
    """SQL Model for pipelines."""

    __tablename__ = "pipeline"

    id: UUID = Field(primary_key=True)

    name: str

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    project: "ProjectSchema" = Relationship(back_populates="pipelines")

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: "UserSchema" = Relationship(back_populates="pipelines")

    docstring: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    spec: str = Field(sa_column=Column(TEXT, nullable=False))

    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    runs: List["PipelineRunSchema"] = Relationship(
        back_populates="pipeline",
    )

    @classmethod
    def from_create_model(cls, pipeline: PipelineModel) -> "PipelineSchema":
        """Create a `PipelineSchema` from a `PipelineModel`.

        Args:
            pipeline: The `PipelineModel` to create the schema from.

        Returns:
            The created `PipelineSchema`.
        """
        return cls(
            id=pipeline.id,
            name=pipeline.name,
            project_id=pipeline.project,
            user_id=pipeline.user,
            docstring=pipeline.docstring,
            spec=pipeline.spec.json(sort_keys=True),
        )

    def from_update_model(self, model: PipelineModel) -> "PipelineSchema":
        """Update a `PipelineSchema` from a PipelineModel.

        Args:
            model: The `PipelineModel` to update the schema from.

        Returns:
            The updated `PipelineSchema`.
        """
        self.name = model.name
        self.updated = datetime.now()
        self.docstring = model.docstring
        self.spec = model.spec.json(sort_keys=True)
        return self

    def to_model(self) -> "PipelineModel":
        """Convert a `PipelineSchema` to a `PipelineModel`.

        Returns:
            The created PipelineModel.
        """
        return PipelineModel(
            id=self.id,
            name=self.name,
            project=self.project_id,
            user=self.user_id,
            docstring=self.docstring,
            spec=PipelineSpec.parse_raw(self.spec),
            created=self.created,
            updated=self.updated,
        )


class PipelineRunSchema(SQLModel, table=True):
    """SQL Model for pipeline runs."""

    __tablename__ = "pipeline_run"

    id: UUID = Field(primary_key=True)
    name: str

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    project: "ProjectSchema" = Relationship(back_populates="runs")

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: "UserSchema" = Relationship(back_populates="runs")

    stack_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackSchema.__tablename__,
        source_column="stack_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    stack: "StackSchema" = Relationship(back_populates="runs")

    pipeline_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineSchema.__tablename__,
        source_column="pipeline_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    pipeline: PipelineSchema = Relationship(back_populates="runs")

    orchestrator_run_id: Optional[str] = Field(nullable=True)

    status: ExecutionStatus
    pipeline_configuration: str = Field(sa_column=Column(TEXT, nullable=False))
    num_steps: Optional[int]
    zenml_version: str
    git_sha: Optional[str] = Field(nullable=True)

    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    mlmd_id: Optional[int] = Field(default=None, nullable=True)

    @classmethod
    def from_create_model(
        cls,
        run: PipelineRunModel,
        pipeline: Optional[PipelineSchema] = None,
    ) -> "PipelineRunSchema":
        """Create a `PipelineRunSchema` from a `PipelineRunModel`.

        Args:
            run: The `PipelineRunModel` to create the schema from.
            pipeline: The `PipelineSchema` to link to the run.

        Returns:
            The created `PipelineRunSchema`.
        """
        return cls(
            id=run.id,
            name=run.name,
            orchestrator_run_id=run.orchestrator_run_id,
            stack_id=run.stack_id,
            project_id=run.project,
            user_id=run.user,
            pipeline_id=run.pipeline_id,
            status=run.status,
            pipeline_configuration=json.dumps(run.pipeline_configuration),
            num_steps=run.num_steps,
            git_sha=run.git_sha,
            zenml_version=run.zenml_version,
            pipeline=pipeline,
            mlmd_id=run.mlmd_id,
        )

    def from_update_model(self, model: PipelineRunModel) -> "PipelineRunSchema":
        """Update a `PipelineRunSchema` from a `PipelineRunModel`.

        Args:
            model: The `PipelineRunModel` to update the schema from.

        Returns:
            The updated `PipelineRunSchema`.
        """
        self.mlmd_id = model.mlmd_id
        self.status = model.status
        self.updated = datetime.now()
        return self

    def to_model(self) -> PipelineRunModel:
        """Convert a `PipelineRunSchema` to a `PipelineRunModel`.

        Returns:
            The created `PipelineRunModel`.
        """
        return PipelineRunModel(
            id=self.id,
            name=self.name,
            orchestrator_run_id=self.orchestrator_run_id,
            stack_id=self.stack_id,
            project=self.project_id,
            user=self.user_id,
            pipeline_id=self.pipeline_id,
            status=self.status,
            pipeline_configuration=json.loads(self.pipeline_configuration),
            num_steps=self.num_steps,
            git_sha=self.git_sha,
            zenml_version=self.zenml_version,
            mlmd_id=self.mlmd_id,
            created=self.created,
            updated=self.updated,
        )


class StepRunSchema(SQLModel, table=True):
    """SQL Model for steps of pipeline runs."""

    __tablename__ = "step_run"

    id: UUID = Field(primary_key=True)
    name: str

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

    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    @classmethod
    def from_create_model(cls, model: StepRunModel) -> "StepRunSchema":
        """Create a `StepRunSchema` from a `StepRunModel`.

        Args:
            model: The `StepRunModel` to create the schema from.

        Returns:
            The created `StepRunSchema`.

        """
        return cls(
            id=model.id,
            name=model.name,
            pipeline_run_id=model.pipeline_run_id,
            status=model.status,
            entrypoint_name=model.entrypoint_name,
            parameters=json.dumps(model.parameters),
            step_configuration=json.dumps(model.step_configuration),
            docstring=model.docstring,
            num_outputs=model.num_outputs,
            mlmd_id=model.mlmd_id,
        )

    def from_update_model(self, model: StepRunModel) -> "StepRunSchema":
        """Update a `StepRunSchema` from a `StepRunModel`.

        Args:
            model: The `StepRunModel` to update the schema from.

        Returns:
            The updated `StepRunSchema`.
        """
        self.status = model.status
        self.updated = datetime.now()
        return self

    def to_model(
        self,
        parent_step_ids: List[UUID],
        mlmd_parent_step_ids: List[int],
        input_artifacts: Dict[str, UUID],
    ) -> StepRunModel:
        """Convert a `StepRunSchema` to a `StepRunModel`.

        Args:
            parent_step_ids: The parent step ids to link to the step.
            mlmd_parent_step_ids: The parent step ids in MLMD.
            input_artifacts: The input artifacts to link to the step.

        Returns:
            The created StepRunModel.
        """
        return StepRunModel(
            id=self.id,
            name=self.name,
            pipeline_run_id=self.pipeline_run_id,
            parent_step_ids=parent_step_ids,
            input_artifacts=input_artifacts,
            status=self.status,
            entrypoint_name=self.entrypoint_name,
            parameters=json.loads(self.parameters),
            step_configuration=json.loads(self.step_configuration),
            docstring=self.docstring,
            num_outputs=self.num_outputs,
            mlmd_id=self.mlmd_id,
            mlmd_parent_step_ids=mlmd_parent_step_ids,
            created=self.created,
            updated=self.updated,
        )


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


class ArtifactSchema(SQLModel, table=True):
    """SQL Model for artifacts of steps."""

    __tablename__ = "artifacts"

    id: UUID = Field(primary_key=True)
    name: str  # Name of the output in the parent step

    parent_step_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="parent_step_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    producer_step_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="producer_step_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )

    type: ArtifactType
    uri: str
    materializer: str
    data_type: str
    is_cached: bool

    mlmd_id: Optional[int] = Field(default=None, nullable=True)
    mlmd_parent_step_id: Optional[int] = Field(default=None, nullable=True)
    mlmd_producer_step_id: Optional[int] = Field(default=None, nullable=True)

    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    @classmethod
    def from_create_model(cls, model: ArtifactModel) -> "ArtifactSchema":
        """Create an `ArtifactSchema` from an `ArtifactModel`.

        Args:
            model: The `ArtifactModel` to create the schema from.

        Returns:
            The created `ArtifactSchema`.
        """
        return cls(
            id=model.id,
            name=model.name,
            parent_step_id=model.parent_step_id,
            producer_step_id=model.producer_step_id,
            type=model.type,
            uri=model.uri,
            materializer=model.materializer,
            data_type=model.data_type,
            is_cached=model.is_cached,
            mlmd_id=model.mlmd_id,
            mlmd_parent_step_id=model.mlmd_parent_step_id,
            mlmd_producer_step_id=model.mlmd_producer_step_id,
        )

    def to_model(self) -> ArtifactModel:
        """Convert an `ArtifactSchema` to an `ArtifactModel`.

        Returns:
            The created `ArtifactModel`.
        """
        return ArtifactModel(
            id=self.id,
            name=self.name,
            parent_step_id=self.parent_step_id,
            producer_step_id=self.producer_step_id,
            type=self.type,
            uri=self.uri,
            materializer=self.materializer,
            data_type=self.data_type,
            is_cached=self.is_cached,
            mlmd_id=self.mlmd_id,
            mlmd_parent_step_id=self.mlmd_parent_step_id,
            mlmd_producer_step_id=self.mlmd_producer_step_id,
            created=self.created,
            updated=self.updated,
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
    artifact_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ArtifactSchema.__tablename__,
        source_column="artifact_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )
    name: str  # Name of the input in the step
