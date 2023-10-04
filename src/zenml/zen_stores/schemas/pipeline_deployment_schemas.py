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

import json
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from pydantic.json import pydantic_encoder
from sqlalchemy import TEXT, Column, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlmodel import Field, Relationship

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.models import (
    PipelineDeploymentRequestModel,
    PipelineDeploymentResponseModel,
)
from zenml.models.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.code_repository_schemas import (
    CodeReferenceSchema,
)
from zenml.zen_stores.schemas.pipeline_build_schemas import PipelineBuildSchema
from zenml.zen_stores.schemas.pipeline_schemas import PipelineSchema
from zenml.zen_stores.schemas.schedule_schema import ScheduleSchema
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

    schedule_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=ScheduleSchema.__tablename__,
        source_column="schedule_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    schedule: Optional[ScheduleSchema] = Relationship(
        back_populates="deployment"
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

    code_reference_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=CodeReferenceSchema.__tablename__,
        source_column="code_reference_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    code_reference: Optional["CodeReferenceSchema"] = Relationship()

    runs: List["PipelineRunSchema"] = Relationship(back_populates="deployment")

    run_name_template: str
    pipeline_configuration: str = Field(sa_column=Column(TEXT, nullable=False))
    step_configurations: str = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=False,
        )
    )
    client_environment: str = Field(sa_column=Column(TEXT, nullable=False))

    @classmethod
    def from_request(
        cls,
        request: PipelineDeploymentRequestModel,
        code_reference_id: Optional[UUID],
    ) -> "PipelineDeploymentSchema":
        """Convert a `PipelineDeploymentRequestModel` to a `PipelineDeploymentSchema`.

        Args:
            request: The request to convert.
            code_reference_id: Optional ID of the code reference for the
                deployment.

        Returns:
            The created `PipelineDeploymentSchema`.
        """
        return cls(
            stack_id=request.stack,
            workspace_id=request.workspace,
            pipeline_id=request.pipeline,
            build_id=request.build,
            user_id=request.user,
            schedule_id=request.schedule,
            code_reference_id=code_reference_id,
            run_name_template=request.run_name_template,
            pipeline_configuration=request.pipeline_configuration.json(),
            step_configurations=json.dumps(
                request.step_configurations,
                sort_keys=False,
                default=pydantic_encoder,
            ),
            client_environment=json.dumps(request.client_environment),
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
            workspace=self.workspace.to_model(),
            user=self.user.to_model(True) if self.user else None,
            stack=self.stack.to_model() if self.stack else None,
            pipeline=self.pipeline.to_model() if self.pipeline else None,
            build=self.build.to_model() if self.build else None,
            schedule=self.schedule.to_model() if self.schedule else None,
            code_reference=self.code_reference.to_model()
            if self.code_reference
            else None,
            created=self.created,
            updated=self.updated,
            run_name_template=self.run_name_template,
            pipeline_configuration=PipelineConfiguration.parse_raw(
                self.pipeline_configuration
            ),
            step_configurations=json.loads(self.step_configurations),
            client_environment=json.loads(self.client_environment),
        )
