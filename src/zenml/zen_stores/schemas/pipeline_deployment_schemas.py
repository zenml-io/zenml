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
"""SQLModel implementation of pipeline deployment tables."""

from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.config.pipeline_deployment import PipelineDeployment
from zenml.models import (
    PipelineDeploymentRequestModel,
    PipelineDeploymentResponseModel,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.pipeline_build_schemas import PipelineBuildSchema
from zenml.zen_stores.schemas.pipeline_schemas import PipelineSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.stack_schemas import StackSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import PipelineRunSchema


class PipelineDeploymentSchema(BaseSchema, table=True):
    """SQL Model for pipeline deployments."""

    __tablename__ = "pipeline_deployment"

    stack_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackSchema.__tablename__,
        source_column="stack_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    stack: "StackSchema" = Relationship(back_populates="deployments")

    pipeline_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineSchema.__tablename__,
        source_column="pipeline_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    pipeline: "PipelineSchema" = Relationship(back_populates="deployments")

    build_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineBuildSchema.__tablename__,
        source_column="build_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    build: Optional["PipelineBuildSchema"] = Relationship(
        back_populates="deployments"
    )

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="deployments")

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="deployments")

    runs: List["PipelineRunSchema"] = Relationship(back_populates="deployment")

    configuration: str = Field(sa_column=Column(TEXT, nullable=False))

    @classmethod
    def from_request(
        cls, request: PipelineDeploymentRequestModel
    ) -> "PipelineDeploymentSchema":
        """Convert a `PipelineDeploymentRequestModel` to a `PipelineDeploymentSchema`.

        Args:
            request: The request to convert.

        Returns:
            The created `PipelineDeploymentSchema`.
        """
        configuration = request.configuration.json()

        return cls(
            stack_id=request.stack,
            workspace_id=request.workspace,
            pipeline_id=request.pipeline,
            build_id=request.build,
            user_id=request.user,
            configuration=configuration,
        )

    def to_model(
        self,
    ) -> PipelineDeploymentResponseModel:
        """Convert a `PipelineDeploymentSchema` to a `PipelineDeploymentResponseModel`.

        Returns:
            The created `PipelineDeploymentResponseModel`.
        """
        return PipelineDeploymentResponseModel(
            id=self.id,
            configuration=PipelineDeployment.parse_raw(self.configuration),
            workspace=self.workspace.to_model(),
            user=self.user.to_model(True) if self.user else None,
            stack=self.stack.to_model() if self.stack else None,
            pipeline=(
                self.pipeline.to_model(False) if self.pipeline else None
            ),
            build=self.build.to_model() if self.build else None,
            created=self.created,
            updated=self.updated,
        )
