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
from typing import Any, Dict, Optional, Sequence, cast
from uuid import UUID

from sqlalchemy import TEXT, Column, UniqueConstraint
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.base import ExecutableOption
from sqlalchemy_utils.types.encrypted.encrypted_type import (
    AesGcmEngine,
    InvalidCiphertextError,
)
from sqlmodel import Field, Relationship

from zenml.constants import TEXT_FIELD_MAX_LENGTH
from zenml.models import (
    SecretRequest,
    SecretResponse,
    SecretResponseBody,
    SecretResponseMetadata,
    SecretResponseResources,
    SecretUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import jl_arg


class SecretDecodeError(Exception):
    """Raised when a secret cannot be decoded or decrypted."""


class SecretSchema(NamedSchema, table=True):
    """SQL Model for secrets.

    Attributes:
        name: The name of the secret.
        values: The values of the secret.
    """

    __tablename__ = "secret"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "private",
            "user_id",
            name="unique_secret_name_private_scope_user",
        ),
    )

    private: bool

    values: Optional[bytes] = Field(sa_column=Column(TEXT, nullable=True))

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
            options.extend([joinedload(jl_arg(SecretSchema.user))])

        return options

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

        Raises:
            SecretDecodeError: If the secret values cannot be decoded or
                decrypted.
        """
        if encryption_engine is None:
            try:
                serialized_values = base64.b64decode(encrypted_values).decode()
            except ValueError as e:
                raise SecretDecodeError(
                    "Could not decode base64 encoded secret values: {str(e)}"
                ) from e
        else:
            try:
                serialized_values = encryption_engine.decrypt(encrypted_values)
            except (ValueError, InvalidCiphertextError) as e:
                raise SecretDecodeError(
                    "Could not decrypt secret values. Please check that the "
                    f"encryption key is correct: {str(e)}"
                ) from e

        try:
            return cast(
                Dict[str, str],
                json.loads(serialized_values),
            )
        except json.JSONDecodeError as e:
            raise SecretDecodeError(
                "Could not decode secret values. Please check that the "
                f"secret values are valid JSON: {str(e)}"
            ) from e

    @classmethod
    def from_request(
        cls,
        secret: SecretRequest,
    ) -> "SecretSchema":
        """Create a `SecretSchema` from a `SecretRequest`.

        Args:
            secret: The `SecretRequest` from which to create the schema.

        Returns:
            The created `SecretSchema`.
        """
        assert secret.user is not None, "User must be set for secret creation."
        return cls(
            name=secret.name,
            private=secret.private,
            user_id=secret.user,
            # Don't store secret values implicitly in the secret. The
            # SQL secret store will call `store_secret_values` to store the
            # values separately if SQL is used as the secrets store.
            values=None,
        )

    def update(
        self,
        secret_update: SecretUpdate,
    ) -> "SecretSchema":
        """Update a `SecretSchema` from a `SecretUpdate`.

        Args:
            secret_update: The `SecretUpdate` from which to update the schema.

        Returns:
            The updated `SecretSchema`.
        """
        # Don't update the secret values implicitly in the secret. The
        # SQL secret store will call `set_secret_values` to update the
        # values separately if SQL is used as the secrets store.
        for field, value in secret_update.model_dump(
            exclude_unset=True, exclude={"user", "values"}
        ).items():
            setattr(self, field, value)

        self.updated = utc_now()
        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> SecretResponse:
        """Converts a secret schema to a secret model.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The secret model.
        """
        metadata = None
        if include_metadata:
            metadata = SecretResponseMetadata()

        resources = None
        if include_resources:
            resources = SecretResponseResources(
                user=self.user.to_model() if self.user else None,
            )

        # Don't load the secret values implicitly in the secret. The
        # SQL secret store will call `get_secret_values` to load the
        # values separately if SQL is used as the secrets store.
        body = SecretResponseBody(
            user_id=self.user_id,
            created=self.created,
            updated=self.updated,
            private=self.private,
        )
        return SecretResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )

    def get_secret_values(
        self,
        encryption_engine: Optional[AesGcmEngine] = None,
    ) -> Dict[str, str]:
        """Get the secret values for this secret.

        This method is used by the SQL secrets store to load the secret values
        from the database.

        Args:
            encryption_engine: The encryption engine to use to decrypt the
                secret values. If None, the values will be base64 decoded.

        Returns:
            The secret values

        Raises:
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
        """
        if not self.values:
            raise KeyError(
                f"Secret values for secret {self.id} have not been stored in "
                f"the SQL secrets store."
            )
        return self._load_secret_values(self.values, encryption_engine)

    def set_secret_values(
        self,
        secret_values: Dict[str, str],
        encryption_engine: Optional[AesGcmEngine] = None,
    ) -> None:
        """Create a `SecretSchema` from a `SecretRequest`.

        This method is used by the SQL secrets store to store the secret values
        in the database.

        Args:
            secret_values: The new secret values.
            encryption_engine: The encryption engine to use to encrypt the
                secret values. If None, the values will be base64 encoded.
        """
        self.values = self._dump_secret_values(
            secret_values, encryption_engine
        )
