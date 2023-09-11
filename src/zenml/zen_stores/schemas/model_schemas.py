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
"""SQLModel implementation of model tables."""


import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.models import (
    ModelRequestModel,
    ModelResponseModel,
    ModelUpdateModel,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema


class ModelSchema(NamedSchema, table=True):
    """SQL Model for model."""

    __tablename__ = "model"

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="models")

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="models")

    license: str = Field(sa_column=Column(TEXT, nullable=True))
    description: str = Field(sa_column=Column(TEXT, nullable=True))
    audience: str = Field(sa_column=Column(TEXT, nullable=True))
    use_cases: str = Field(sa_column=Column(TEXT, nullable=True))
    limitations: str = Field(sa_column=Column(TEXT, nullable=True))
    trade_offs: str = Field(sa_column=Column(TEXT, nullable=True))
    ethic: str = Field(sa_column=Column(TEXT, nullable=True))
    tags: str = Field(sa_column=Column(TEXT, nullable=True))

    @classmethod
    def from_request(cls, model_request: ModelRequestModel) -> "ModelSchema":
        """Convert an `ModelRequestModel` to an `ModelSchema`.

        Args:
            model_request: The request model to convert.

        Returns:
            The converted schema.
        """
        return cls(
            name=model_request.name,
            workspace_id=model_request.workspace,
            user_id=model_request.user,
            license=model_request.license,
            description=model_request.description,
            audience=model_request.audience,
            use_cases=model_request.use_cases,
            limitations=model_request.limitations,
            trade_offs=model_request.trade_offs,
            ethic=model_request.ethic,
            tags=json.dumps(model_request.tags),
        )

    def to_model(self) -> ModelResponseModel:
        """Convert an `ModelSchema` to an `ModelResponseModel`.

        Returns:
            The created `ModelResponseModel`.
        """
        return ModelResponseModel(
            id=self.id,
            name=self.name,
            user=self.user.to_model() if self.user else None,
            workspace=self.workspace.to_model(),
            created=self.created,
            updated=self.updated,
            license=self.license,
            description=self.description,
            audience=self.audience,
            use_cases=self.use_cases,
            limitations=self.limitations,
            trade_offs=self.trade_offs,
            ethic=self.ethic,
            tags=json.loads(self.tags),
        )

    def update(
        self,
        model_update: ModelUpdateModel,
    ) -> "ModelSchema":
        """Updates a `ModelSchema` from a `ModelUpdateModel`.

        Args:
            model_update: The `ModelUpdateModel` to update from.

        Returns:
            The updated `ModelSchema`.
        """
        for field, value in model_update.dict(exclude_unset=True).items():
            if field == "tags":
                setattr(self, field, json.dumps(value))
            else:
                setattr(self, field, value)
        self.updated = datetime.utcnow()
        return self
