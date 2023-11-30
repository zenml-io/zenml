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
from typing import Dict, Optional, cast
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlalchemy_utils.types.encrypted.encrypted_type import AesGcmEngine
from sqlmodel import Field, Relationship

from zenml.constants import TEXT_FIELD_MAX_LENGTH
from zenml.enums import SecretScope
from zenml.models.secret_models import (
    SecretRequestModel,
    SecretResponseModel,
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

    values: bytes = Field(sa_column=Column(TEXT, nullable=False))

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
    user: "UserSchema" = Relationship(back_populates="secrets")

    @classmethod
    def _dump_secret_values(
        cls, values: Dict[str, str], encryption_engine: Optional[AesGcmEngine]
    ) -> bytes:
        """Dump the secret values to a string.

        Args:
            values: The secret values to dump.
            encryption_engine: The encryption engine to use to encrypt the
                secret values. If None, the values will be base64 encoded.

        Raises:
            ValueError: If the secret values do not fit in the database field.

        Returns:
            The serialized encrypted secret values.
        """
        serialized_values = json.dumps(values)

        if encryption_engine is None:
            encrypted_values = base64.b64encode(
                serialized_values.encode("utf-8")
            )
        else:
            encrypted_values = encryption_engine.encrypt(serialized_values)

        if len(encrypted_values) > TEXT_FIELD_MAX_LENGTH:
            raise ValueError(
                "Database representation of secret values exceeds max "
                "length. Please use fewer values or consider using shorter "
                "secret keys and/or values."
            )

        return encrypted_values

    @classmethod
    def _load_secret_values(
        cls,
        encrypted_values: bytes,
        encryption_engine: Optional[AesGcmEngine] = None,
    ) -> Dict[str, str]:
        """Load the secret values from a base64 encoded byte string.

        Args:
            encrypted_values: The serialized encrypted secret values.
            encryption_engine: The encryption engine to use to decrypt the
                secret values. If None, the values will be base64 decoded.

        Returns:
            The loaded secret values.
        """
        if encryption_engine is None:
            serialized_values = base64.b64decode(encrypted_values).decode()
        else:
            serialized_values = encryption_engine.decrypt(encrypted_values)

        return cast(
            Dict[str, str],
            json.loads(serialized_values),
        )

    @classmethod
    def from_request(
        cls,
        secret: SecretRequestModel,
        encryption_engine: Optional[AesGcmEngine] = None,
    ) -> "SecretSchema":
        """Create a `SecretSchema` from a `SecretRequestModel`.

        Args:
            secret: The `SecretRequestModel` from which to create the schema.
            encryption_engine: The encryption engine to use to encrypt the
                secret values. If None, the values will be base64 encoded.

        Returns:
            The created `SecretSchema`.
        """
        assert secret.user is not None, "User must be set for secret creation."
        return cls(
            name=secret.name,
            scope=secret.scope,
            workspace_id=secret.workspace,
            user_id=secret.user,
            values=cls._dump_secret_values(
                secret.secret_values, encryption_engine
            ),
        )

    def update(
        self,
        secret_update: SecretUpdateModel,
        encryption_engine: Optional[AesGcmEngine] = None,
    ) -> "SecretSchema":
        """Update a `SecretSchema` from a `SecretUpdateModel`.

        The method also knows how to handle the `values` field of the secret
        update model: It will update the existing values with the new values
        and drop `None` values.

        Args:
            secret_update: The `SecretUpdateModel` from which to update the schema.
            encryption_engine: The encryption engine to use to encrypt the
                secret values. If None, the values will be base64 encoded.

        Returns:
            The updated `SecretSchema`.
        """
        for field, value in secret_update.dict(
            exclude_unset=True, exclude={"workspace", "user"}
        ).items():
            if field == "values":
                existing_values = self._load_secret_values(
                    self.values, encryption_engine
                )
                existing_values.update(secret_update.secret_values)
                # Drop values removed in the update
                for k, v in secret_update.values.items():
                    if v is None and k in existing_values:
                        del existing_values[k]
                self.values = self._dump_secret_values(
                    existing_values, encryption_engine
                )
            else:
                setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def to_model(
        self,
        encryption_engine: Optional[AesGcmEngine] = None,
        include_values: bool = True,
    ) -> SecretResponseModel:
        """Converts a secret schema to a secret model.

        Args:
            encryption_engine: The encryption engine to use to decrypt the
                secret values. If None, the values will be base64 decoded.
            include_values: Whether to include the secret values in the
                response model or not.

        Returns:
            The secret model.
        """
        return SecretResponseModel(
            id=self.id,
            name=self.name,
            scope=self.scope,
            values=self._load_secret_values(self.values, encryption_engine)
            if include_values
            else {},
            user=self.user.to_model() if self.user else None,
            workspace=self.workspace.to_model(),
            created=self.created,
            updated=self.updated,
        )
