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
"""SQLModel implementation for authorized OAuth2 devices."""

from datetime import datetime, timedelta
from secrets import token_hex
from typing import Optional, Tuple
from uuid import UUID

from passlib.context import CryptContext
from sqlmodel import Relationship

from zenml.enums import OAuthDeviceStatus
from zenml.models import (
    OAuthDeviceInternalRequest,
    OAuthDeviceInternalResponse,
    OAuthDeviceInternalUpdate,
    OAuthDeviceResponse,
    OAuthDeviceResponseBody,
    OAuthDeviceResponseMetadata,
    OAuthDeviceUpdate,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema


class OAuthDeviceSchema(BaseSchema, table=True):
    """SQL Model for authorized OAuth2 devices."""

    __tablename__ = "auth_devices"

    client_id: UUID
    user_code: str
    device_code: str
    status: OAuthDeviceStatus
    failed_auth_attempts: int = 0
    expires: Optional[datetime] = None
    last_login: Optional[datetime] = None
    trusted_device: bool = False
    os: Optional[str] = None
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    python_version: Optional[str] = None
    zenml_version: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="auth_devices")

    @classmethod
    def _generate_user_code(cls) -> str:
        """Generate a user code for an OAuth2 device.

        Returns:
            The generated user code.
        """
        return token_hex(16)

    @classmethod
    def _generate_device_code(cls) -> str:
        """Generate a device code.

        Returns:
            The generated device code.
        """
        return token_hex(32)

    @classmethod
    def _get_hashed_code(cls, code: str) -> str:
        """Hashes the input code and returns the hash value.

        Args:
            code: The code value to hash.

        Returns:
            The code hash value.
        """
        context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return context.hash(code)

    @classmethod
    def from_request(
        cls, request: OAuthDeviceInternalRequest
    ) -> Tuple["OAuthDeviceSchema", str, str]:
        """Create an authorized device DB entry from a device authorization request.

        Args:
            request: The device authorization request.

        Returns:
            The created `OAuthDeviceSchema`, the user code and the device code.
        """
        user_code = cls._generate_user_code()
        device_code = cls._generate_device_code()
        hashed_user_code = cls._get_hashed_code(user_code)
        hashed_device_code = cls._get_hashed_code(device_code)
        now = datetime.utcnow()
        return (
            cls(
                client_id=request.client_id,
                user_code=hashed_user_code,
                device_code=hashed_device_code,
                status=OAuthDeviceStatus.PENDING,
                failed_auth_attempts=0,
                expires=now + timedelta(seconds=request.expires_in),
                os=request.os,
                ip_address=request.ip_address,
                hostname=request.hostname,
                python_version=request.python_version,
                zenml_version=request.zenml_version,
                city=request.city,
                region=request.region,
                country=request.country,
                created=now,
                updated=now,
            ),
            user_code,
            device_code,
        )

    def update(self, device_update: OAuthDeviceUpdate) -> "OAuthDeviceSchema":
        """Update an authorized device from a device update model.

        Args:
            device_update: The device update model.

        Returns:
            The updated `OAuthDeviceSchema`.
        """
        for field, value in device_update.dict(exclude_none=True).items():
            if hasattr(self, field):
                setattr(self, field, value)

        if device_update.locked is True:
            self.status = OAuthDeviceStatus.LOCKED
        elif device_update.locked is False:
            self.status = OAuthDeviceStatus.ACTIVE

        self.updated = datetime.utcnow()
        return self

    def internal_update(
        self, device_update: OAuthDeviceInternalUpdate
    ) -> Tuple["OAuthDeviceSchema", Optional[str], Optional[str]]:
        """Update an authorized device from an internal device update model.

        Args:
            device_update: The internal device update model.

        Returns:
            The updated `OAuthDeviceSchema` and the new user code and device
            code, if they were generated.
        """
        now = datetime.utcnow()
        user_code: Optional[str] = None
        device_code: Optional[str] = None

        # This call also takes care of setting fields that have the same
        # name in the internal model and the schema.
        self.update(device_update)

        if device_update.expires_in is not None:
            if device_update.expires_in <= 0:
                self.expires = None
            else:
                self.expires = now + timedelta(
                    seconds=device_update.expires_in
                )
        if device_update.update_last_login:
            self.last_login = now
        if device_update.generate_new_codes:
            user_code = self._generate_user_code()
            device_code = self._generate_device_code()
            self.user_code = self._get_hashed_code(user_code)
            self.device_code = self._get_hashed_code(device_code)
        self.updated = now
        return self, user_code, device_code

    def to_model(self, hydrate: bool = False) -> OAuthDeviceResponse:
        """Convert a device schema to a device response model.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The converted device response model.
        """
        metadata = None
        if hydrate:
            metadata = OAuthDeviceResponseMetadata(
                python_version=self.python_version,
                zenml_version=self.zenml_version,
                city=self.city,
                region=self.region,
                country=self.country,
                failed_auth_attempts=self.failed_auth_attempts,
                last_login=self.last_login,
            )

        body = OAuthDeviceResponseBody(
            user=self.user.to_model() if self.user else None,
            created=self.created,
            updated=self.updated,
            client_id=self.client_id,
            expires=self.expires,
            trusted_device=self.trusted_device,
            status=self.status,
            os=self.os,
            ip_address=self.ip_address,
            hostname=self.hostname,
        )
        return OAuthDeviceResponse(
            id=self.id,
            body=body,
            metadata=metadata,
        )

    def to_internal_model(
        self, hydrate: bool = False
    ) -> OAuthDeviceInternalResponse:
        """Convert a device schema to an internal device response model.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The converted internal device response model.
        """
        device_model = self.to_model(hydrate=hydrate)
        return OAuthDeviceInternalResponse(
            id=device_model.id,
            body=device_model.body,
            metadata=device_model.metadata,
            user_code=self.user_code,
            device_code=self.device_code,
        )
