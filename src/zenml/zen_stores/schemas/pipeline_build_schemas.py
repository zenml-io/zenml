#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""SQLModel implementation of pipeline build tables."""

import json
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import Column, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlmodel import Field, Relationship

from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.models import (
    PipelineBuildRequest,
    PipelineBuildResponse,
    PipelineBuildResponseBody,
    PipelineBuildResponseMetadata,
)
from zenml.utils.json_utils import pydantic_encoder
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.pipeline_schemas import PipelineSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.stack_schemas import StackSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema


class PipelineBuildSchema(BaseSchema, table=True):
    """SQL Model for pipeline builds."""

    __tablename__ = "pipeline_build"

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="builds")

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="builds")

    stack_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackSchema.__tablename__,
        source_column="stack_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    stack: Optional["StackSchema"] = Relationship(back_populates="builds")

    pipeline_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineSchema.__tablename__,
        source_column="pipeline_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    pipeline: Optional["PipelineSchema"] = Relationship(
        back_populates="builds"
    )

    template_deployment_id: Optional[UUID] = None
    images: str = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=False,
        )
    )

    is_local: bool
    contains_code: bool

    zenml_version: Optional[str]
    python_version: Optional[str]
    checksum: Optional[str]

    @classmethod
    def from_request(
        cls, request: PipelineBuildRequest
    ) -> "PipelineBuildSchema":
        """Convert a `PipelineBuildRequest` to a `PipelineBuildSchema`.

        Args:
            request: The request to convert.

        Returns:
            The created `PipelineBuildSchema`.
        """
        return cls(
            stack_id=request.stack,
            workspace_id=request.workspace,
            user_id=request.user,
            pipeline_id=request.pipeline,
            images=json.dumps(request.images, default=pydantic_encoder),
            is_local=request.is_local,
            contains_code=request.contains_code,
            zenml_version=request.zenml_version,
            python_version=request.python_version,
            checksum=request.checksum,
            template_deployment_id=request.template_deployment_id,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> PipelineBuildResponse:
        """Convert a `PipelineBuildSchema` to a `PipelineBuildResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The created `PipelineBuildResponse`.
        """
        body = PipelineBuildResponseBody(
            user=self.user.to_model() if self.user else None,
            created=self.created,
            updated=self.updated,
        )
        metadata = None
        if include_metadata:
            metadata = PipelineBuildResponseMetadata(
                workspace=self.workspace.to_model(),
                pipeline=self.pipeline.to_model() if self.pipeline else None,
                stack=self.stack.to_model() if self.stack else None,
                images=json.loads(self.images),
                zenml_version=self.zenml_version,
                python_version=self.python_version,
                checksum=self.checksum,
                is_local=self.is_local,
                contains_code=self.contains_code,
                template_deployment_id=self.template_deployment_id,
            )
        return PipelineBuildResponse(
            id=self.id,
            body=body,
            metadata=metadata,
        )
