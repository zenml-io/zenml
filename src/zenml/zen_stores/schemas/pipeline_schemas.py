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

from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship

from zenml.config.pipeline_configurations import PipelineSpec
from zenml.new_models.pipeline_models import PipelineResponseModel
from zenml.zen_stores.schemas.base_schemas import ProjectScopedSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import ProjectSchema, UserSchema


class PipelineSchema(ProjectScopedSchema, table=True):
    """SQL Model for pipelines."""

    name: str
    docstring: Optional[str] = Field(max_length=4096, nullable=True)
    spec: str = Field(max_length=4096)

    user: "UserSchema" = Relationship(back_populates="pipelines")
    project: "ProjectSchema" = Relationship(back_populates="pipelines")
    versions: List["PipelineVersionSchema"] = Relationship(
        back_populates="pipeline"
    )
    runs: List["PipelineRunSchema"] = Relationship(
        back_populates="pipeline",
    )

    def to_model(
        self, _block_recursion: bool = False
    ) -> "PipelineResponseModel":
        """Convert a `PipelineSchema` to a `PipelineModel`.

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
