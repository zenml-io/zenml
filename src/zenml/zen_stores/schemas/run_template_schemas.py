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
"""SQLModel implementation of run template tables."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional
from uuid import UUID

from sqlalchemy import Column, String, UniqueConstraint
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlmodel import Field, Relationship

from zenml.config.pipeline_spec import PipelineSpec
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
from zenml.zen_stores.schemas.code_repository_schemas import (
    CodeReferenceSchema,
)
from zenml.zen_stores.schemas.pipeline_build_schemas import PipelineBuildSchema
from zenml.zen_stores.schemas.pipeline_schemas import PipelineSchema
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
    pipeline_version_hash: Optional[str] = Field(nullable=True, default=None)
    pipeline_spec: Optional[str] = Field(
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
    pipeline_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineSchema.__tablename__,
        source_column="pipeline_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    build_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=PipelineBuildSchema.__tablename__,
        source_column="build_id",
        target_column="id",
        ondelete="SET NULL",  # TODO
        nullable=False,
    )
    code_reference_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=CodeReferenceSchema.__tablename__,
        source_column="code_reference_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )

    user: Optional["UserSchema"] = Relationship()
    workspace: "WorkspaceSchema" = Relationship()
    pipeline: Optional["PipelineSchema"] = Relationship()
    build: "PipelineBuildSchema" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[RunTemplateSchema.build_id]"}
    )
    code_reference: Optional["CodeReferenceSchema"] = Relationship()

    runs: List["PipelineRunSchema"] = Relationship(
        sa_relationship_kwargs={"cascade": "delete"}
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
        deployment: "PipelineDeploymentSchema",
    ) -> "RunTemplateSchema":
        """Create a schema from a request.

        Args:
            request: The request to convert.
            deployment: Schema of the deployment that is the base of the
                template.

        Raises:
            ValueError: If the deployment does not have an associated build.

        Returns:
            The created schema.
        """
        if not deployment.build_id:
            raise ValueError(
                "Unable to create run template from deployment without build."
            )

        return cls(
            user_id=request.user,
            workspace_id=request.workspace,
            name=request.name,
            description=request.description,
            pipeline_version_hash=deployment.pipeline_version_hash,
            pipeline_spec=deployment.pipeline_spec,
            pipeline_id=deployment.pipeline_id,
            build_id=deployment.build_id,
            code_reference_id=deployment.code_reference_id,
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
        body = RunTemplateResponseBody(
            user=self.user.to_model() if self.user else None,
            created=self.created,
            updated=self.updated,
            latest_run_id=self.runs[-1].id if self.runs else None,
            latest_run_status=self.runs[-1].status if self.runs else None,
            tags=[t.tag.to_model() for t in self.tags],
        )
        metadata = None
        if include_metadata:
            metadata = RunTemplateResponseMetadata(
                workspace=self.workspace.to_model(),
                description=self.description,
                pipeline_version_hash=self.pipeline_version_hash,
                pipeline_spec=PipelineSpec.model_validate_json(
                    self.pipeline_spec
                )
                if self.pipeline_spec
                else None,
            )
        resources = None
        if include_resources:
            resources = RunTemplateResponseResources(
                pipeline=self.pipeline.to_model() if self.pipeline else None,
                build=self.build.to_model(),
                code_reference=self.code_reference.to_model()
                if self.code_reference
                else None,
            )

        return RunTemplateResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )
