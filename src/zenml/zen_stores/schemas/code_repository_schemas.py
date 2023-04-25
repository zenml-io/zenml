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
from typing import Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.models.code_repository_models import (
    CodeReferenceRequestModel,
    CodeReferenceResponseModel,
    CodeRepositoryRequestModel,
    CodeRepositoryResponseModel,
    CodeRepositoryUpdateModel,
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
        cls,
        request: "CodeRepositoryRequestModel",
    ) -> "CodeRepositorySchema":
        """Convert a `CodeRepositoryRequestModel` to a `CodeRepositorySchema`.

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
            source=request.source.json(),
            description=request.description,
            logo_url=request.logo_url,
        )

    def to_model(
        self,
    ) -> "CodeRepositoryResponseModel":
        """Convert a `CodeRepositorySchema` to a `CodeRepositoryResponseModel`.

        Returns:
            The created CodeRepositoryResponseModel.
        """
        return CodeRepositoryResponseModel(
            id=self.id,
            name=self.name,
            workspace=self.workspace.to_model(),
            user=self.user.to_model(True) if self.user else None,
            created=self.created,
            updated=self.updated,
            config=json.loads(self.config),
            source=json.loads(self.source),
            description=self.description,
            logo_url=self.logo_url,
        )

    def update(
        self, update: "CodeRepositoryUpdateModel"
    ) -> "CodeRepositorySchema":
        """Update a `CodeRepositorySchema` with a `CodeRepositoryUpdateModel`.

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
        cls, request: "CodeReferenceRequestModel", workspace_id: UUID
    ) -> "CodeReferenceSchema":
        """Convert a `CodeReferenceRequestModel` to a `CodeReferenceSchema`.

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
    ) -> "CodeReferenceResponseModel":
        """Convert a `CodeReferenceSchema` to a `CodeReferenceResponseModel`.

        Returns:
            The converted model.
        """
        return CodeReferenceResponseModel(
            id=self.id,
            created=self.created,
            updated=self.updated,
            commit=self.commit,
            subdirectory=self.subdirectory,
            code_repository=self.code_repository.to_model(),
        )
