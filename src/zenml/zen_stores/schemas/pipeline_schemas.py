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
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

from zenml.config.pipeline_configurations import PipelineSpec
from zenml.enums import ArtifactType
from zenml.models import PipelineModel, PipelineRunModel
from zenml.models.pipeline_models import ArtifactModel, StepRunModel

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import ProjectSchema, UserSchema


class PipelineSchema(SQLModel, table=True):
    """SQL Model for pipelines."""

    id: UUID = Field(primary_key=True)

    name: str

    project_id: UUID = Field(
        sa_column=Column(ForeignKey("projectschema.id", ondelete="CASCADE"))
    )
    project: "ProjectSchema" = Relationship(back_populates="pipelines")

    user_id: UUID = Field(
        sa_column=Column(ForeignKey("userschema.id", ondelete="SET NULL"))
    )
    user: "UserSchema" = Relationship(back_populates="pipelines")

    docstring: Optional[str] = Field(nullable=True)
    spec: str

    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    runs: List["PipelineRunSchema"] = Relationship(
        back_populates="pipeline",
        sa_relationship_kwargs={"cascade": "all, delete"},
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

    id: UUID = Field(primary_key=True)
    name: str

    # project_id - redundant since stack has this
    user: Optional[UUID] = Field(foreign_key="userschema.id", nullable=True)
    stack_id: Optional[UUID] = Field(
        foreign_key="stackschema.id", nullable=True
    )
    pipeline_id: Optional[UUID] = Field(
        foreign_key="pipelineschema.id", nullable=True
    )

    git_sha: Optional[str] = Field(nullable=True)
    zenml_version: str

    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    pipeline: PipelineSchema = Relationship(back_populates="runs")

    mlmd_id: int = Field(default=None, nullable=True)

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
            stack_id=run.stack_id,
            user=run.user,
            pipeline_id=run.pipeline_id,
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
        self.name = model.name
        self.git_sha = model.git_sha
        if model.zenml_version is not None:
            self.zenml_version = model.zenml_version
        if model.mlmd_id is not None:
            self.mlmd_id = model.mlmd_id
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
            stack_id=self.stack_id,
            user=self.user,
            pipeline_id=self.pipeline_id,
            git_sha=self.git_sha,
            zenml_version=self.zenml_version,
            mlmd_id=self.mlmd_id,
            created=self.created,
            updated=self.updated,
        )


class StepRunSchema(SQLModel, table=True):
    """SQL Model for steps of pipeline runs."""

    id: UUID = Field(primary_key=True)
    name: str

    pipeline_run_id: UUID = Field(foreign_key="pipelinerunschema.id")

    docstring: Optional[str]
    parameters: str
    entrypoint_name: str

    mlmd_id: int = Field(default=None, nullable=True)

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
            docstring=model.docstring,
            parameters=json.dumps(model.parameters),
            entrypoint_name=model.entrypoint_name,
            mlmd_id=model.mlmd_id,
        )

    def to_model(
        self, parent_step_ids: List[UUID], mlmd_parent_step_ids: List[int]
    ) -> StepRunModel:
        """Convert a `StepRunSchema` to a `StepRunModel`.

        Args:
            parent_step_ids: The parent step ids to link to the step.
            mlmd_parent_step_ids: The parent step ids in MLMD.

        Returns:
            The created StepRunModel.
        """
        return StepRunModel(
            id=self.id,
            name=self.name,
            pipeline_run_id=self.pipeline_run_id,
            parent_step_ids=parent_step_ids,
            docstring=self.docstring,
            parameters=json.loads(self.parameters),
            entrypoint_name=self.entrypoint_name,
            mlmd_id=self.mlmd_id,
            mlmd_parent_step_ids=mlmd_parent_step_ids,
            created=self.created,
            updated=self.updated,
        )


class StepRunOrderSchema(SQLModel, table=True):
    """SQL Model that defines the order of steps."""

    parent_id: UUID = Field(foreign_key="steprunschema.id", primary_key=True)
    child_id: UUID = Field(foreign_key="steprunschema.id", primary_key=True)


class ArtifactSchema(SQLModel, table=True):
    """SQL Model for artifacts of steps."""

    id: UUID = Field(primary_key=True)
    name: str  # Name of the output in the parent step

    parent_step_id: UUID = Field(foreign_key="steprunschema.id")
    producer_step_id: UUID = Field(foreign_key="steprunschema.id")

    type: ArtifactType
    uri: str
    materializer: str
    data_type: str
    is_cached: bool

    mlmd_id: int = Field(default=None, nullable=True)
    mlmd_parent_step_id: int = Field(default=None, nullable=True)
    mlmd_producer_step_id: int = Field(default=None, nullable=True)

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


class StepInputArtifactSchema(SQLModel, table=True):
    """SQL Model that defines which artifacts are inputs to which step."""

    step_id: UUID = Field(foreign_key="steprunschema.id", primary_key=True)
    artifact_id: UUID = Field(foreign_key="artifactschema.id", primary_key=True)
    name: str  # Name of the input in the step
