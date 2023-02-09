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
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.models.constants import TEXT_FIELD_MAX_LENGTH
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
    def _dump_secret_values(cls, values: Dict[str, str]) -> str:
        """Dump the secret values to a string.

        Args:
            values: The secret values to dump.

        Raises:
            ValueError: If the secret values do not fit in the database field.

        Returns:
            The dumped secret values.
        """
        serialized_values = base64.b64encode(
            json.dumps(values).encode("utf-8")
        )

        if len(serialized_values) > TEXT_FIELD_MAX_LENGTH:
            raise ValueError(
                "Database representation of secret values exceeds max "
                "length. Please use fewer values or consider using shorter "
                "secret keys and/or values."
            )

        return serialized_values

    @classmethod
    def _load_secret_values(
        cls,
        serialized_values: str,
    ) -> Dict[str, str]:
        """Load the secret values from a string.

        Args:
            serialized_values: The serialized secret values.

        Returns:
            The loaded secret values.
        """
        return json.loads(base64.b64decode(serialized_values).decode())

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
            values=cls._dump_secret_values(secret.clear_values),
        )

    def update(self, secret_update: SecretUpdateModel) -> "SecretSchema":
        """Update a `SecretSchema` from a `SecretUpdateModel`.

        The method also knows how to handle the `values` field of the secret
        update model: It will update the existing values with the new values
        and drop `None` values.

        Args:
            secret_update: The `SecretUpdateModel` from which to update the schema.

        Returns:
            The updated `SecretSchema`.
        """
        for field, value in secret_update.dict(
            exclude_unset=True, exclude={"workspace", "user"}
        ).items():
            if field == "values":
                existing_values = self._load_secret_values(self.values)
                existing_values.update(value)
                # Drop None values
                existing_values = {
                    k: v for k, v in existing_values.items() if v is not None
                }
                self.values = self._dump_secret_values(existing_values)
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
            values=self._load_secret_values(self.values),
            user=self.user.to_model() if self.user else None,
            workspace=self.workspace.to_model(),
            created=self.created,
            updated=self.updated,
        )
