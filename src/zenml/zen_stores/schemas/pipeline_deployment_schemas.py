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
from typing import TYPE_CHECKING, Any, List, Optional
from uuid import UUID

from sqlalchemy import TEXT, Column, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlmodel import Field, Relationship

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.step_configurations import Step
from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.models import (
    PipelineDeploymentRequest,
    PipelineDeploymentResponse,
    PipelineDeploymentResponseBody,
    PipelineDeploymentResponseMetadata,
)
from zenml.utils.json_utils import pydantic_encoder
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.code_repository_schemas import (
    CodeReferenceSchema,
)
from zenml.zen_stores.schemas.pipeline_build_schemas import PipelineBuildSchema
from zenml.zen_stores.schemas.pipeline_schemas import PipelineSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schedule_schema import ScheduleSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.stack_schemas import StackSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
    from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema


class PipelineDeploymentSchema(BaseSchema, table=True):
    """SQL Model for pipeline deployments."""

    __tablename__ = "pipeline_deployment"

    # Fields
    pipeline_configuration: str = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=False,
        )
    )
    step_configurations: str = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=False,
        )
    )
    client_environment: str = Field(sa_column=Column(TEXT, nullable=False))
    run_name_template: str = Field(nullable=False)
    client_version: str = Field(nullable=True)
    server_version: str = Field(nullable=True)
    pipeline_version_hash: Optional[str] = Field(nullable=True, default=None)
    pipeline_spec: Optional[str] = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=True,
        )
    )
    code_path: Optional[str] = Field(nullable=True)

    # Foreign keys
    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    stack_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackSchema.__tablename__,
        source_column="stack_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    pipeline_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineSchema.__tablename__,
        source_column="pipeline_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    schedule_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=ScheduleSchema.__tablename__,
        source_column="schedule_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    build_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineBuildSchema.__tablename__,
        source_column="build_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    code_reference_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=CodeReferenceSchema.__tablename__,
        source_column="code_reference_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    # This is not a foreign key to remove a cycle which messes with our DB
    # backup process
    template_id: Optional[UUID] = None

    # SQLModel Relationships
    user: Optional["UserSchema"] = Relationship(
        back_populates="deployments",
    )
    project: "ProjectSchema" = Relationship()
    stack: Optional["StackSchema"] = Relationship()
    pipeline: Optional["PipelineSchema"] = Relationship()
    schedule: Optional["ScheduleSchema"] = Relationship()
    build: Optional["PipelineBuildSchema"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[PipelineDeploymentSchema.build_id]"
        }
    )
    code_reference: Optional["CodeReferenceSchema"] = Relationship()

    pipeline_runs: List["PipelineRunSchema"] = Relationship(
        sa_relationship_kwargs={"cascade": "delete"}
    )
    step_runs: List["StepRunSchema"] = Relationship(
        sa_relationship_kwargs={"cascade": "delete"}
    )

    @classmethod
    def from_request(
        cls,
        request: PipelineDeploymentRequest,
        code_reference_id: Optional[UUID],
    ) -> "PipelineDeploymentSchema":
        """Convert a `PipelineDeploymentRequest` to a `PipelineDeploymentSchema`.

        Args:
            request: The request to convert.
            code_reference_id: Optional ID of the code reference for the
                deployment.

        Returns:
            The created `PipelineDeploymentSchema`.
        """
        return cls(
            stack_id=request.stack,
            project_id=request.project,
            pipeline_id=request.pipeline,
            build_id=request.build,
            user_id=request.user,
            schedule_id=request.schedule,
            template_id=request.template,
            code_reference_id=code_reference_id,
            run_name_template=request.run_name_template,
            pipeline_configuration=request.pipeline_configuration.model_dump_json(),
            step_configurations=json.dumps(
                request.step_configurations,
                sort_keys=False,
                default=pydantic_encoder,
            ),
            client_environment=json.dumps(request.client_environment),
            client_version=request.client_version,
            server_version=request.server_version,
            pipeline_version_hash=request.pipeline_version_hash,
            pipeline_spec=json.dumps(
                request.pipeline_spec.model_dump(mode="json"), sort_keys=True
            )
            if request.pipeline_spec
            else None,
            code_path=request.code_path,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> PipelineDeploymentResponse:
        """Convert a `PipelineDeploymentSchema` to a `PipelineDeploymentResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The created `PipelineDeploymentResponse`.
        """
        body = PipelineDeploymentResponseBody(
            user=self.user.to_model() if self.user else None,
            created=self.created,
            updated=self.updated,
        )
        metadata = None
        if include_metadata:
            pipeline_configuration = PipelineConfiguration.model_validate_json(
                self.pipeline_configuration
            )
            step_configurations = json.loads(self.step_configurations)
            for s, c in step_configurations.items():
                step_configurations[s] = Step.model_validate(c)

            metadata = PipelineDeploymentResponseMetadata(
                project=self.project.to_model(),
                run_name_template=self.run_name_template,
                pipeline_configuration=pipeline_configuration,
                step_configurations=step_configurations,
                client_environment=json.loads(self.client_environment),
                client_version=self.client_version,
                server_version=self.server_version,
                pipeline=self.pipeline.to_model() if self.pipeline else None,
                stack=self.stack.to_model() if self.stack else None,
                build=self.build.to_model() if self.build else None,
                schedule=self.schedule.to_model() if self.schedule else None,
                code_reference=self.code_reference.to_model()
                if self.code_reference
                else None,
                pipeline_version_hash=self.pipeline_version_hash,
                pipeline_spec=PipelineSpec.model_validate_json(
                    self.pipeline_spec
                )
                if self.pipeline_spec
                else None,
                code_path=self.code_path,
                template_id=self.template_id,
            )
        return PipelineDeploymentResponse(
            id=self.id,
            body=body,
            metadata=metadata,
        )
