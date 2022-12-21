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

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.config.pipeline_configurations import PipelineSpec
from zenml.models.pipeline_models import PipelineResponseModel
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema

if TYPE_CHECKING:
    from zenml.models import PipelineUpdateModel
    from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema


class PipelineSchema(NamedSchema, table=True):
    """SQL Model for pipelines."""

    __tablename__ = "pipeline"

    docstring: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    spec: str = Field(sa_column=Column(TEXT, nullable=False))

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

    user: Optional["UserSchema"] = Relationship(back_populates="pipelines")

    runs: List["PipelineRunSchema"] = Relationship(
        back_populates="pipeline",
        sa_relationship_kwargs={"order_by": "asc(PipelineRunSchema.created)"},
    )

    def to_model(
        self,
        _block_recursion: bool = False,
        last_x_runs: int = 3,
    ) -> "PipelineResponseModel":
        """Convert a `PipelineSchema` to a `PipelineModel`.

        Args:
            _block_recursion: Don't recursively fill attributes
            last_x_runs: How many runs to use for the execution status

        Returns:
            The created PipelineModel.
        """
        x_runs = self.runs[:last_x_runs]
        status_last_x_runs = []
        for run in x_runs:
            status_last_x_runs.append(run.status)
        if _block_recursion:
            return PipelineResponseModel(
                id=self.id,
                name=self.name,
                project=self.project.to_model(),
                user=self.user.to_model() if self.user else None,
                docstring=self.docstring,
                spec=PipelineSpec.parse_raw(self.spec),
                created=self.created,
                updated=self.updated,
                status=status_last_x_runs,
            )
        else:
            return PipelineResponseModel(
                id=self.id,
                name=self.name,
                project=self.project.to_model(),
                user=self.user.to_model() if self.user else None,
                runs=[r.to_model(True) for r in self.runs],
                docstring=self.docstring,
                spec=PipelineSpec.parse_raw(self.spec),
                created=self.created,
                updated=self.updated,
                status=status_last_x_runs,
            )

    def update(
        self, pipeline_update: "PipelineUpdateModel"
    ) -> "PipelineSchema":
        """Update a `PipelineSchema` with a `PipelineUpdateModel`.

        Args:
            pipeline_update: The update model.

        Returns:
            The updated `PipelineSchema`.
        """
        if pipeline_update.name:
            self.name = pipeline_update.name

        if pipeline_update.docstring:
            self.docstring = pipeline_update.docstring

        if pipeline_update.spec:
            self.spec = pipeline_update.spec.json(sort_keys=True)

        self.updated = datetime.utcnow()
        return self
