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
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
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
    CodeRepositoryUpdate,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema, NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema


class CodeRepositorySchema(NamedSchema, table=True):
    """SQL Model for code repositories."""

    __tablename__ = "code_repository"

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(
        back_populates="code_repositories"
    )

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
            workspace_id=request.workspace,
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
            user=self.user.to_model() if self.user else None,
            source=json.loads(self.source),
            logo_url=self.logo_url,
            created=self.created,
            updated=self.updated,
        )
        metadata = None
        if include_metadata:
            metadata = CodeRepositoryResponseMetadata(
                workspace=self.workspace.to_model(),
                config=json.loads(self.config),
                description=self.description,
            )
        return CodeRepositoryResponse(
            id=self.id,
            name=self.name,
            metadata=metadata,
            body=body,
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

        self.updated = datetime.utcnow()
        return self


class CodeReferenceSchema(BaseSchema, table=True):
    """SQL Model for code references."""

    __tablename__ = "code_reference"

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship()

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
        cls, request: "CodeReferenceRequest", workspace_id: UUID
    ) -> "CodeReferenceSchema":
        """Convert a `CodeReferenceRequest` to a `CodeReferenceSchema`.

        Args:
            request: The request model to convert.
            workspace_id: The workspace ID.

        Returns:
            The converted schema.
        """
        return cls(
            workspace_id=workspace_id,
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
