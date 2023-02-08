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
"""SQL Model Implementations for Secrets."""
import base64
import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.models.secret_models import (
    SecretRequestModel,
    SecretResponseModel,
    SecretScope,
    SecretUpdateModel,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema


class SecretSchema(NamedSchema, table=True):
    """SQL Model for secrets.

    Attributes:
        name: The name of the secret.
        values: The values of the secret.
    """

    __tablename__ = "secret"

    scope: SecretScope

    values: str = Field(sa_column=Column(TEXT, nullable=False))

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="secrets")

    user_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="secrets")

    @classmethod
    def from_request(cls, secret: SecretRequestModel) -> "SecretSchema":
        """Create a `SecretSchema` from a `SecretRequestModel`.

        Args:
            secret: The `SecretRequestModel` from which to create the schema.

        Returns:
            The created `SecretSchema`.
        """
        assert secret.user is not None, "User must be set for secret creation."
        return cls(
            name=secret.name,
            scope=secret.scope,
            workspace_id=secret.workspace,
            user_id=secret.user,
            values=base64.b64encode(
                json.dumps(secret.clear_values).encode("utf-8")
            ),
        )

    def update(self, secret_update: SecretUpdateModel) -> "SecretSchema":
        """Update a `SecretSchema` from a `SecretUpdateModel`.

        Args:
            secret_update: The `SecretUpdateModel` from which to update the schema.

        Returns:
            The updated `SecretSchema`.
        """
        for field, value in secret_update.dict(
            exclude_unset=True, exclude={"workspace", "user"}
        ).items():
            if field == "values":
                existing_values = json.loads(
                    base64.b64decode(self.values).decode()
                )
                existing_values.update(value)
                # Drop None values
                existing_values = {
                    k: v for k, v in existing_values.items() if v is not None
                }
                self.configuration = base64.b64encode(
                    json.dumps(existing_values).encode("utf-8")
                )
            else:
                setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def to_model(self) -> SecretResponseModel:
        """Converts a secret schema to a secret model.

        Returns:
            The secret model.
        """
        return SecretResponseModel(
            id=self.id,
            name=self.name,
            scope=self.scope,
            values=json.loads(
                base64.b64decode(self.values).decode()
            ),
            user=self.user.to_model() if self.user else None,
            workspace=self.workspace.to_model(),
            created=self.created,
            updated=self.updated,
        )
