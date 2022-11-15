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

from sqlalchemy import TEXT, Column, ForeignKey
from sqlmodel import Field, Relationship

from zenml.config.pipeline_configurations import PipelineSpec
from zenml.new_models.pipeline_models import PipelineResponseModel
from zenml.zen_stores.schemas.base_schemas import NamedSchema

if TYPE_CHECKING:
    from zenml.new_models import PipelineUpdateModel
    from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
    from zenml.zen_stores.schemas.project_schemas import ProjectSchema
    from zenml.zen_stores.schemas.user_schemas import UserSchema


class PipelineSchema(NamedSchema, table=True):
    """SQL Model for pipelines."""

    docstring: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    spec: str = Field(sa_column=Column(TEXT, nullable=False))

    user_id: UUID = Field(
        sa_column=Column(ForeignKey("userschema.id", ondelete="SET NULL"))
    )
    project_id: UUID = Field(
        sa_column=Column(ForeignKey("projectschema.id", ondelete="CASCADE"))
    )
    user: "UserSchema" = Relationship(back_populates="pipelines")
    project: "ProjectSchema" = Relationship(back_populates="pipelines")

    runs: List["PipelineRunSchema"] = Relationship(
        back_populates="pipeline",
    )

    def to_model(
        self, _block_recursion: bool = False
    ) -> "PipelineResponseModel":
        """Convert a `PipelineSchema` to a `PipelineModel`.

        Args:
            _block_recursion: Don't recursively fill attributes

        Returns:
            The created PipelineModel.
        """
        if _block_recursion:
            return PipelineResponseModel(
                id=self.id,
                name=self.name,
                project=self.project.to_model(),
                user=self.user.to_model(),
                docstring=self.docstring,
                spec=PipelineSpec.parse_raw(self.spec),
                created=self.created,
                updated=self.updated,
            )
        else:
            return PipelineResponseModel(
                id=self.id,
                name=self.name,
                project=self.project.to_model(),
                user=self.user.to_model(),
                runs=[r.to_model(not _block_recursion) for r in self.runs],
                docstring=self.docstring,
                spec=PipelineSpec.parse_raw(self.spec),
                created=self.created,
                updated=self.updated,
            )

    def update(self, pipeline_update: PipelineUpdateModel) -> "PipelineSchema":
        """"""
        if pipeline_update.name:
            self.name = pipeline_update.name

        if pipeline_update.docstring:
            self.docstring = pipeline_update.docstring

        if pipeline_update.spec:
            self.spec = pipeline_update.spec.json(sort_keys=True)

        self.updated = datetime.now()
        return self
