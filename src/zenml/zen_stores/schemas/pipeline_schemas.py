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

from sqlalchemy import TEXT, Column, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlmodel import Field, Relationship

from zenml.config.pipeline_spec import PipelineSpec
from zenml.models.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.models.pipeline_models import (
    PipelineRequestModel,
    PipelineResponseModel,
    PipelineUpdateModel,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import (
        PipelineBuildSchema,
        PipelineDeploymentSchema,
        PipelineRunSchema,
        ScheduleSchema,
    )


class PipelineSchema(NamedSchema, table=True):
    """SQL Model for pipelines."""

    __tablename__ = "pipeline"

    version: str
    version_hash: str

    docstring: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    spec: str = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=False,
        )
    )

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="pipelines")

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )

    user: Optional["UserSchema"] = Relationship(back_populates="pipelines")

    schedules: List["ScheduleSchema"] = Relationship(
        back_populates="pipeline",
    )
    runs: List["PipelineRunSchema"] = Relationship(
        back_populates="pipeline", sa_relationship_kwargs={"cascade": "delete"}
    )
    builds: List["PipelineBuildSchema"] = Relationship(
        back_populates="pipeline"
    )
    deployments: List["PipelineDeploymentSchema"] = Relationship(
        back_populates="pipeline"
    )

    @classmethod
    def from_request(
        cls,
        pipeline_request: "PipelineRequestModel",
    ) -> "PipelineSchema":
        """Convert a `PipelineRequestModel` to a `PipelineSchema`.

        Args:
            pipeline_request: The request model to convert.

        Returns:
            The converted schema.
        """
        return cls(
            name=pipeline_request.name,
            version=pipeline_request.version,
            version_hash=pipeline_request.version_hash,
            workspace_id=pipeline_request.workspace,
            user_id=pipeline_request.user,
            docstring=pipeline_request.docstring,
            spec=pipeline_request.spec.json(sort_keys=True),
        )

    def to_model(
        self,
        last_x_runs: int = 3,
    ) -> "PipelineResponseModel":
        """Convert a `PipelineSchema` to a `PipelineModel`.

        Args:
            last_x_runs: How many runs to use for the execution status

        Returns:
            The created PipelineModel.
        """
        return PipelineResponseModel(
            id=self.id,
            name=self.name,
            version=self.version,
            version_hash=self.version_hash,
            workspace=self.workspace.to_model(),
            user=self.user.to_model(True) if self.user else None,
            docstring=self.docstring,
            spec=PipelineSpec.parse_raw(self.spec),
            created=self.created,
            updated=self.updated,
            status=[run.status for run in self.runs[:last_x_runs]],
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
