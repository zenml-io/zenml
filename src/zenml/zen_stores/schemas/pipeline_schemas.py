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
from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from zenml.models import PipelineModel, PipelineRunModel


class PipelineSchema(SQLModel, table=True):
    """SQL Model for pipelines."""

    id: UUID = Field(primary_key=True, default_factory=uuid4)

    name: str

    project_id: UUID = Field(foreign_key="projectschema.id")
    # repository_id: UUID = Field(foreign_key="coderepositoryschema.id")
    owner: UUID = Field(foreign_key="userschema.id")

    docstring: Optional[str] = Field(nullable=True)
    configuration: str

    created_at: datetime = Field(default_factory=datetime.now)

    runs: List["PipelineRunSchema"] = Relationship(
        back_populates="pipeline",
    )

    @classmethod
    def from_create_model(cls, model: PipelineModel) -> "PipelineSchema":
        return cls(
            name=model.name,
            project_id=model.project_id,
            owner=model.owner,
            docstring=model.docstring,
            configuration=json.dumps(model.configuration),
        )

    def from_update_model(self, model: PipelineModel) -> "PipelineSchema":
        self.name = model.name
        self.docstring = model.docstring
        return self

    def to_model(self) -> "PipelineModel":
        return PipelineModel(
            id=self.id,
            name=self.name,
            project_id=self.project_id,
            owner=self.owner,
            docstring=self.docstring,
            configuration=json.loads(self.configuration),
            created_at=self.created_at,
        )


class PipelineRunSchema(SQLModel, table=True):
    """SQL Model for pipeline runs."""

    id: UUID = Field(primary_key=True, default_factory=uuid4)
    mlmd_id: int = Field(default=None, nullable=True)
    name: str

    # project_id - redundant since stack has this
    owner: Optional[UUID] = Field(foreign_key="userschema.id", nullable=True)
    stack_id: Optional[UUID] = Field(
        foreign_key="stackschema.id", nullable=True
    )
    pipeline_id: Optional[UUID] = Field(
        foreign_key="pipelineschema.id", nullable=True
    )

    runtime_configuration: Optional[str] = Field(nullable=True)
    git_sha: Optional[str] = Field(nullable=True)
    zenml_version: str

    created_at: datetime = Field(default_factory=datetime.now)

    pipeline: PipelineSchema = Relationship(back_populates="runs")

    @classmethod
    def from_create_model(
        cls,
        model: PipelineRunModel,
        pipeline: Optional[PipelineSchema] = None,
    ) -> "PipelineRunSchema":
        return cls(
            mlmd_id=model.mlmd_id,
            name=model.name,
            stack_id=model.stack_id,
            owner=model.owner,
            pipeline_id=model.pipeline_id,
            runtime_configuration=json.dumps(model.runtime_configuration),
            git_sha=model.git_sha,
            zenml_version=model.zenml_version,
            pipeline=pipeline,
        )

    def from_update_model(self, model: PipelineRunModel) -> "PipelineRunSchema":
        self.mlmd_id = model.mlmd_id
        self.name = model.name
        self.runtime_configuration = json.dumps(model.runtime_configuration)
        self.git_sha = model.git_sha
        self.zenml_version = model.zenml_version
        return self

    def to_model(self) -> PipelineRunModel:
        return PipelineRunModel(
            id=self.id,
            mlmd_id=self.mlmd_id,
            name=self.name,
            stack_id=self.stack_id,
            owner=self.owner,
            pipeline_id=self.pipeline_id,
            runtime_configuration=json.loads(self.runtime_configuration),
            git_sha=self.git_sha,
            zenml_version=self.zenml_version,
            created_at=self.created_at,
        )
