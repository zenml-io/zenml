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
"""SQL Model Implementations for code repositories."""

import json
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import TEXT, Column, UniqueConstraint
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship

from zenml.models import (
    CodeReferenceRequest,
    CodeReferenceResponse,
    CodeReferenceResponseBody,
    CodeReferenceResponseMetadata,
    CodeRepositoryRequest,
    CodeRepositoryResponse,
    CodeRepositoryResponseBody,
    CodeRepositoryResponseMetadata,
    CodeRepositoryResponseResources,
    CodeRepositoryUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import BaseSchema, NamedSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import jl_arg


class CodeRepositorySchema(NamedSchema, table=True):
    """SQL Model for code repositories."""

    __tablename__ = "code_repository"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "project_id",
            name="unique_code_repository_name_in_project",
        ),
    )

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    project: "ProjectSchema" = Relationship(back_populates="code_repositories")

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )

    user: Optional["UserSchema"] = Relationship(
        back_populates="code_repositories"
    )

    config: str = Field(sa_column=Column(TEXT, nullable=False))
    source: str = Field(sa_column=Column(TEXT, nullable=False))
    logo_url: Optional[str] = Field()
    description: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))

    @classmethod
    def get_query_options(
        cls,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> Sequence[ExecutableOption]:
        """Get the query options for the schema.

        Args:
            include_metadata: Whether metadata will be included when converting
                the schema to a model.
            include_resources: Whether resources will be included when
                converting the schema to a model.
            **kwargs: Keyword arguments to allow schema specific logic

        Returns:
            A list of query options.
        """
        options = []

        if include_resources:
            options.extend(
                [
                    joinedload(jl_arg(CodeRepositorySchema.user)),
                ]
            )

        return options

    @classmethod
    def from_request(
        cls, request: "CodeRepositoryRequest"
    ) -> "CodeRepositorySchema":
        """Convert a `CodeRepositoryRequest` to a `CodeRepositorySchema`.

        Args:
            request: The request model to convert.

        Returns:
            The converted schema.
        """
        return cls(
            name=request.name,
            project_id=request.project,
            user_id=request.user,
            config=json.dumps(request.config),
            source=request.source.model_dump_json(),
            description=request.description,
            logo_url=request.logo_url,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> "CodeRepositoryResponse":
        """Convert a `CodeRepositorySchema` to a `CodeRepositoryResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The created CodeRepositoryResponse.
        """
        body = CodeRepositoryResponseBody(
            user_id=self.user_id,
            project_id=self.project_id,
            source=json.loads(self.source),
            logo_url=self.logo_url,
            created=self.created,
            updated=self.updated,
        )
        metadata = None
        if include_metadata:
            metadata = CodeRepositoryResponseMetadata(
                config=json.loads(self.config),
                description=self.description,
            )

        resources = None
        if include_resources:
            resources = CodeRepositoryResponseResources(
                user=self.user.to_model() if self.user else None,
            )

        return CodeRepositoryResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )

    def update(self, update: "CodeRepositoryUpdate") -> "CodeRepositorySchema":
        """Update a `CodeRepositorySchema` with a `CodeRepositoryUpdate`.

        Args:
            update: The update model.

        Returns:
            The updated `CodeRepositorySchema`.
        """
        if update.name:
            self.name = update.name

        if update.description:
            self.description = update.description

        if update.logo_url:
            self.logo_url = update.logo_url

        if update.config:
            self.config = json.dumps(update.config)

        self.updated = utc_now()
        return self


class CodeReferenceSchema(BaseSchema, table=True):
    """SQL Model for code references."""

    __tablename__ = "code_reference"

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    project: "ProjectSchema" = Relationship()

    code_repository_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=CodeRepositorySchema.__tablename__,
        source_column="code_repository_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    code_repository: "CodeRepositorySchema" = Relationship()

    commit: str
    subdirectory: str

    @classmethod
    def from_request(
        cls, request: "CodeReferenceRequest", project_id: UUID
    ) -> "CodeReferenceSchema":
        """Convert a `CodeReferenceRequest` to a `CodeReferenceSchema`.

        Args:
            request: The request model to convert.
            project_id: The project ID.

        Returns:
            The converted schema.
        """
        return cls(
            project_id=project_id,
            commit=request.commit,
            subdirectory=request.subdirectory,
            code_repository_id=request.code_repository,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> "CodeReferenceResponse":
        """Convert a `CodeReferenceSchema` to a `CodeReferenceResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic

            kwargs: Additional keyword arguments.

        Returns:
            The converted model.
        """
        body = CodeReferenceResponseBody(
            commit=self.commit,
            subdirectory=self.subdirectory,
            code_repository=self.code_repository.to_model(),
            created=self.created,
            updated=self.updated,
        )
        metadata = None
        if include_metadata:
            metadata = CodeReferenceResponseMetadata()

        return CodeReferenceResponse(
            id=self.id,
            body=body,
            metadata=metadata,
        )
