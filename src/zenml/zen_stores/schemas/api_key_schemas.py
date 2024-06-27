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
"""SQLModel implementation of user tables."""

from datetime import datetime
from secrets import token_hex
from typing import Any, Optional, Tuple
from uuid import UUID

from passlib.context import CryptContext
from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.models import (
    APIKeyInternalResponse,
    APIKeyInternalUpdate,
    APIKeyRequest,
    APIKeyResponse,
    APIKeyResponseBody,
    APIKeyResponseMetadata,
    APIKeyRotateRequest,
    APIKeyUpdate,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema


class APIKeySchema(NamedSchema, table=True):
    """SQL Model for API keys."""

    __tablename__ = "api_key"

    description: str = Field(sa_column=Column(TEXT))
    key: str
    previous_key: Optional[str] = Field(default=None, nullable=True)
    retain_period: int = Field(default=0)
    active: bool = Field(default=True)
    last_login: Optional[datetime] = None
    last_rotated: Optional[datetime] = None

    service_account_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="service_account_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    service_account: "UserSchema" = Relationship(back_populates="api_keys")

    @classmethod
    def _generate_jwt_secret_key(cls) -> str:
        """Generate a random API key.

        Returns:
            A random API key.
        """
        return token_hex(32)

    @classmethod
    def _get_hashed_key(cls, key: str) -> str:
        """Hashes the input key and returns the hash value.

        Args:
            key: The key value to hash.

        Returns:
            The key hash value.
        """
        context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return context.hash(key)

    @classmethod
    def from_request(
        cls,
        service_account_id: UUID,
        request: APIKeyRequest,
    ) -> Tuple["APIKeySchema", str]:
        """Convert a `APIKeyRequest` to a `APIKeySchema`.

        Args:
            service_account_id: The service account id to associate the key
                with.
            request: The request model to convert.

        Returns:
            The converted schema and the un-hashed API key.
        """
        key = cls._generate_jwt_secret_key()
        hashed_key = cls._get_hashed_key(key)
        now = datetime.utcnow()
        return (
            cls(
                name=request.name,
                description=request.description or "",
                key=hashed_key,
                service_account_id=service_account_id,
                created=now,
                updated=now,
            ),
            key,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> APIKeyResponse:
        """Convert a `APIKeySchema` to an `APIKeyResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic

            **kwargs: Keyword arguments to filter models.

        Returns:
            The created APIKeyResponse.
        """
        metadata = None
        if include_metadata:
            metadata = APIKeyResponseMetadata(
                description=self.description,
                retain_period_minutes=self.retain_period,
                last_login=self.last_login,
                last_rotated=self.last_rotated,
            )

        body = APIKeyResponseBody(
            created=self.created,
            updated=self.updated,
            active=self.active,
            service_account=self.service_account.to_service_account_model(),
        )

        return APIKeyResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
        )

    def to_internal_model(
        self, hydrate: bool = False
    ) -> APIKeyInternalResponse:
        """Convert a `APIKeySchema` to an `APIKeyInternalResponse`.

        The internal response model includes the hashed key values.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The created APIKeyInternalResponse.
        """
        model = self.to_model(include_metadata=hydrate)
        model.get_body().key = self.key

        return APIKeyInternalResponse(
            id=self.id,
            name=self.name,
            previous_key=self.previous_key,
            body=model.body,
            metadata=model.metadata,
        )

    def update(self, update: APIKeyUpdate) -> "APIKeySchema":
        """Update an `APIKeySchema` with an `APIKeyUpdate`.

        Args:
            update: The update model.

        Returns:
            The updated `APIKeySchema`.
        """
        for field, value in update.model_dump(exclude_none=True).items():
            if hasattr(self, field):
                setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def internal_update(self, update: APIKeyInternalUpdate) -> "APIKeySchema":
        """Update an `APIKeySchema` with an `APIKeyInternalUpdate`.

        The internal update can also update the last used timestamp.

        Args:
            update: The update model.

        Returns:
            The updated `APIKeySchema`.
        """
        self.update(update)

        if update.update_last_login:
            self.last_login = self.updated

        return self

    def rotate(
        self,
        rotate_request: APIKeyRotateRequest,
    ) -> Tuple["APIKeySchema", str]:
        """Rotate the key for an `APIKeySchema`.

        Args:
            rotate_request: The rotate request model.

        Returns:
            The updated `APIKeySchema` and the new un-hashed key.
        """
        self.updated = datetime.utcnow()
        self.previous_key = self.key
        self.retain_period = rotate_request.retain_period_minutes
        new_key = self._generate_jwt_secret_key()
        self.key = self._get_hashed_key(new_key)
        self.last_rotated = self.updated

        return self, new_key
