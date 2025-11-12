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
"""Models representing devices."""

from datetime import datetime
from typing import Optional, Union
from uuid import UUID

from pydantic import Field

from zenml.enums import OAuthDeviceStatus
from zenml.models.v2.base.base import (
    BaseRequest,
    BaseUpdate,
)
from zenml.models.v2.base.scoped import (
    UserScopedFilter,
    UserScopedResponse,
    UserScopedResponseBody,
    UserScopedResponseMetadata,
    UserScopedResponseResources,
)

# ------------------ Request Model ------------------


class OAuthDeviceInternalRequest(BaseRequest):
    """Internal request model for OAuth2 devices."""

    client_id: UUID = Field(description="The client ID of the OAuth2 device.")
    expires_in: int = Field(
        description="The number of seconds after which the OAuth2 device "
        "expires and can no longer be used for authentication."
    )
    os: str | None = Field(
        default=None,
        description="The operating system of the device used for "
        "authentication.",
    )
    ip_address: str | None = Field(
        default=None,
        description="The IP address of the device used for authentication.",
    )
    hostname: str | None = Field(
        default=None,
        description="The hostname of the device used for authentication.",
    )
    python_version: str | None = Field(
        default=None,
        description="The Python version of the device used for authentication.",
    )
    zenml_version: str | None = Field(
        default=None,
        description="The ZenML version of the device used for authentication.",
    )
    city: str | None = Field(
        default=None,
        description="The city where the device is located.",
    )
    region: str | None = Field(
        default=None,
        description="The region where the device is located.",
    )
    country: str | None = Field(
        default=None,
        description="The country where the device is located.",
    )


# ------------------ Update Model ------------------


class OAuthDeviceUpdate(BaseUpdate):
    """OAuth2 device update model."""

    locked: bool | None = Field(
        default=None,
        description="Whether to lock or unlock the OAuth2 device. A locked "
        "device cannot be used for authentication.",
    )


class OAuthDeviceInternalUpdate(OAuthDeviceUpdate):
    """OAuth2 device update model used internally for authentication."""

    user_id: UUID | None = Field(
        default=None, description="User that owns the OAuth2 device."
    )
    status: OAuthDeviceStatus | None = Field(
        default=None, description="The new status of the OAuth2 device."
    )
    expires_in: int | None = Field(
        default=None,
        description="Set the device to expire in the given number of seconds. "
        "If the value is 0 or negative, the device is set to never expire.",
    )
    failed_auth_attempts: int | None = Field(
        default=None,
        description="Set the number of failed authentication attempts.",
    )
    trusted_device: bool | None = Field(
        default=None,
        description="Whether to mark the OAuth2 device as trusted. A trusted "
        "device has a much longer validity time.",
    )
    update_last_login: bool = Field(
        default=False, description="Whether to update the last login date."
    )
    generate_new_codes: bool = Field(
        default=False,
        description="Whether to generate new user and device codes.",
    )
    os: str | None = Field(
        default=None,
        description="The operating system of the device used for "
        "authentication.",
    )
    ip_address: str | None = Field(
        default=None,
        description="The IP address of the device used for authentication.",
    )
    hostname: str | None = Field(
        default=None,
        description="The hostname of the device used for authentication.",
    )
    python_version: str | None = Field(
        default=None,
        description="The Python version of the device used for authentication.",
    )
    zenml_version: str | None = Field(
        default=None,
        description="The ZenML version of the device used for authentication.",
    )
    city: str | None = Field(
        default=None,
        description="The city where the device is located.",
    )
    region: str | None = Field(
        default=None,
        description="The region where the device is located.",
    )
    country: str | None = Field(
        default=None,
        description="The country where the device is located.",
    )


# ------------------ Response Model ------------------


class OAuthDeviceResponseBody(UserScopedResponseBody):
    """Response body for OAuth2 devices."""

    client_id: UUID = Field(description="The client ID of the OAuth2 device.")
    expires: datetime | None = Field(
        default=None,
        description="The expiration date of the OAuth2 device after which "
        "the device is no longer valid and cannot be used for "
        "authentication.",
    )
    trusted_device: bool = Field(
        description="Whether the OAuth2 device was marked as trusted. A "
        "trusted device has a much longer validity time.",
    )
    status: OAuthDeviceStatus = Field(
        description="The status of the OAuth2 device."
    )
    os: str | None = Field(
        default=None,
        description="The operating system of the device used for "
        "authentication.",
    )
    ip_address: str | None = Field(
        default=None,
        description="The IP address of the device used for authentication.",
    )
    hostname: str | None = Field(
        default=None,
        description="The hostname of the device used for authentication.",
    )


class OAuthDeviceResponseMetadata(UserScopedResponseMetadata):
    """Response metadata for OAuth2 devices."""

    python_version: str | None = Field(
        default=None,
        description="The Python version of the device used for authentication.",
    )
    zenml_version: str | None = Field(
        default=None,
        description="The ZenML version of the device used for authentication.",
    )
    city: str | None = Field(
        default=None,
        description="The city where the device is located.",
    )
    region: str | None = Field(
        default=None,
        description="The region where the device is located.",
    )
    country: str | None = Field(
        default=None,
        description="The country where the device is located.",
    )
    failed_auth_attempts: int = Field(
        description="The number of failed authentication attempts.",
    )
    last_login: datetime | None = Field(
        description="The date of the last successful login."
    )


class OAuthDeviceResponseResources(UserScopedResponseResources):
    """Class for all resource models associated with the OAuthDevice entity."""


class OAuthDeviceResponse(
    UserScopedResponse[
        OAuthDeviceResponseBody,
        OAuthDeviceResponseMetadata,
        OAuthDeviceResponseResources,
    ]
):
    """Response model for OAuth2 devices."""

    _warn_on_response_updates = False

    def get_hydrated_version(self) -> "OAuthDeviceResponse":
        """Get the hydrated version of this OAuth2 device.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_authorized_device(self.id)

    # Body and metadata properties
    @property
    def client_id(self) -> UUID:
        """The `client_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().client_id

    @property
    def expires(self) -> datetime | None:
        """The `expires` property.

        Returns:
            the value of the property.
        """
        return self.get_body().expires

    @property
    def trusted_device(self) -> bool:
        """The `trusted_device` property.

        Returns:
            the value of the property.
        """
        return self.get_body().trusted_device

    @property
    def status(self) -> OAuthDeviceStatus:
        """The `status` property.

        Returns:
            the value of the property.
        """
        return self.get_body().status

    @property
    def os(self) -> str | None:
        """The `os` property.

        Returns:
            the value of the property.
        """
        return self.get_body().os

    @property
    def ip_address(self) -> str | None:
        """The `ip_address` property.

        Returns:
            the value of the property.
        """
        return self.get_body().ip_address

    @property
    def hostname(self) -> str | None:
        """The `hostname` property.

        Returns:
            the value of the property.
        """
        return self.get_body().hostname

    @property
    def python_version(self) -> str | None:
        """The `python_version` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().python_version

    @property
    def zenml_version(self) -> str | None:
        """The `zenml_version` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().zenml_version

    @property
    def city(self) -> str | None:
        """The `city` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().city

    @property
    def region(self) -> str | None:
        """The `region` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().region

    @property
    def country(self) -> str | None:
        """The `country` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().country

    @property
    def failed_auth_attempts(self) -> int:
        """The `failed_auth_attempts` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().failed_auth_attempts

    @property
    def last_login(self) -> datetime | None:
        """The `last_login` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().last_login


class OAuthDeviceInternalResponse(OAuthDeviceResponse):
    """OAuth2 device response model used internally for authentication."""

    user_code: str = Field(
        title="The user code.",
    )
    device_code: str = Field(
        title="The device code.",
    )

    def _verify_code(
        self,
        code: str,
        code_hash: str | None,
    ) -> bool:
        """Verifies a given code against the stored (hashed) code.

        Args:
            code: The code to verify.
            code_hash: The hashed code to verify against.

        Returns:
            True if the code is valid, False otherwise.
        """
        from passlib.context import CryptContext

        context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        result = context.verify(code, code_hash)

        return result

    def verify_user_code(
        self,
        user_code: str,
    ) -> bool:
        """Verifies a given user code against the stored (hashed) user code.

        Args:
            user_code: The user code to verify.

        Returns:
            True if the user code is valid, False otherwise.
        """
        return self._verify_code(user_code, self.user_code)

    def verify_device_code(
        self,
        device_code: str,
    ) -> bool:
        """Verifies a given device code against the stored (hashed) device code.

        Args:
            device_code: The device code to verify.

        Returns:
            True if the device code is valid, False otherwise.
        """
        return self._verify_code(device_code, self.device_code)


# ------------------ Filter Model ------------------


class OAuthDeviceFilter(UserScopedFilter):
    """Model to enable advanced filtering of OAuth2 devices."""

    expires: datetime | str | None | None = Field(
        default=None,
        description="The expiration date of the OAuth2 device.",
        union_mode="left_to_right",
    )
    client_id: UUID | str | None = Field(
        default=None,
        description="The client ID of the OAuth2 device.",
        union_mode="left_to_right",
    )
    status: OAuthDeviceStatus | str | None = Field(
        default=None,
        description="The status of the OAuth2 device.",
        union_mode="left_to_right",
    )
    trusted_device: bool | str | None = Field(
        default=None,
        description="Whether the OAuth2 device was marked as trusted.",
        union_mode="left_to_right",
    )
    failed_auth_attempts: int | str | None = Field(
        default=None,
        description="The number of failed authentication attempts.",
        union_mode="left_to_right",
    )
    last_login: datetime | str | None | None = Field(
        default=None,
        description="The date of the last successful login.",
        union_mode="left_to_right",
    )
