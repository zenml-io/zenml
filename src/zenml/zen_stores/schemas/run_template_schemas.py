#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""SQLModel implementation of run template tables."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional
from uuid import UUID

from sqlalchemy import Column, String, UniqueConstraint
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlmodel import Field, Relationship

from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.enums import TaggableResourceTypes
from zenml.models import (
    RunTemplateRequest,
    RunTemplateResponse,
    RunTemplateResponseBody,
    RunTemplateResponseMetadata,
    RunTemplateResponseResources,
    RunTemplateUpdate,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.pipeline_deployment_schemas import (
        PipelineDeploymentSchema,
    )
    from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
    from zenml.zen_stores.schemas.tag_schemas import TagResourceSchema


class RunTemplateSchema(BaseSchema, table=True):
    """SQL Model for run templates."""

    __tablename__ = "run_template"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "workspace_id",
            name="unique_template_name_in_workspace",
        ),
    )

    name: str = Field(nullable=False)
    description: Optional[str] = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=True,
        )
    )

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    source_deployment_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="pipeline_deployment",
        source_column="source_deployment_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )

    user: Optional["UserSchema"] = Relationship()
    workspace: "WorkspaceSchema" = Relationship()
    source_deployment: Optional["PipelineDeploymentSchema"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[RunTemplateSchema.source_deployment_id]"
        }
    )

    runs: List["PipelineRunSchema"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "RunTemplateSchema.id==PipelineDeploymentSchema.template_id",
            "secondaryjoin": "PipelineDeploymentSchema.id==PipelineRunSchema.deployment_id",
            "secondary": "pipeline_deployment",
            "cascade": "delete",
            "viewonly": True,
            "order_by": "PipelineRunSchema.created",
        }
    )

    tags: List["TagResourceSchema"] = Relationship(
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(TagResourceSchema.resource_type=='{TaggableResourceTypes.RUN_TEMPLATE.value}', foreign(TagResourceSchema.resource_id)==RunTemplateSchema.id)",
            cascade="delete",
            overlaps="tags",
        ),
    )

    @classmethod
    def from_request(
        cls,
        request: RunTemplateRequest,
    ) -> "RunTemplateSchema":
        """Create a schema from a request.

        Args:
            request: The request to convert.


        Returns:
            The created schema.
        """
        return cls(
            user_id=request.user,
            workspace_id=request.workspace,
            name=request.name,
            description=request.description,
            source_deployment_id=request.source_deployment_id,
        )

    def update(self, update: RunTemplateUpdate) -> "RunTemplateSchema":
        """Update the schema.

        Args:
            update: The update model.

        Returns:
            The updated schema.
        """
        for field, value in update.model_dump(
            exclude_unset=True, exclude_none=True
        ).items():
            setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> RunTemplateResponse:
        """Convert the schema to a response model.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic

        Returns:
            Model representing this schema.
        """
        runnable = False
        if (
            self.source_deployment
            and self.source_deployment.build
            and self.source_deployment.stack
        ):
            runnable = True

        body = RunTemplateResponseBody(
            user=self.user.to_model() if self.user else None,
            created=self.created,
            updated=self.updated,
            runnable=runnable,
            latest_run_id=self.runs[-1].id if self.runs else None,
            latest_run_status=self.runs[-1].status if self.runs else None,
        )

        metadata = None
        if include_metadata:
            if self.source_deployment:
                from zenml.config.pipeline_run_configuration import (
                    PipelineRunConfiguration,
                )
                from zenml.config.step_configurations import (
                    StepConfigurationUpdate,
                )

                source_deployment = self.source_deployment.to_model()

                steps_configs = {
                    name: step.config.model_dump(
                        include=set(StepConfigurationUpdate.model_fields),
                        exclude={"name", "outputs"},
                    )
                    for name, step in source_deployment.step_configurations.items()
                }

                for config in steps_configs.values():
                    config["settings"].pop("docker", None)

                pipeline_config = (
                    source_deployment.pipeline_configuration.model_dump(
                        include=set(PipelineRunConfiguration.model_fields),
                        exclude={"schedule", "build", "parameters"},
                    )
                )

                pipeline_config["settings"].pop("docker", None)

                config_template = {
                    "run_name": source_deployment.run_name_template,
                    "steps": steps_configs,
                    **pipeline_config,
                }
            else:
                config_template = None

            metadata = RunTemplateResponseMetadata(
                workspace=self.workspace.to_model(),
                description=self.description,
                config_template=config_template,
            )

        resources = None
        if include_resources:
            if self.source_deployment:
                pipeline = (
                    self.source_deployment.pipeline.to_model()
                    if self.source_deployment.pipeline
                    else None
                )
                build = (
                    self.source_deployment.build.to_model()
                    if self.source_deployment.build
                    else None
                )
                code_reference = (
                    self.source_deployment.code_reference.to_model()
                    if self.source_deployment.code_reference
                    else None
                )
            else:
                pipeline = None
                build = None
                code_reference = None

            resources = RunTemplateResponseResources(
                source_deployment=self.source_deployment.to_model()
                if self.source_deployment
                else None,
                pipeline=pipeline,
                build=build,
                code_reference=code_reference,
                tags=[t.tag.to_model() for t in self.tags],
            )

        return RunTemplateResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )
