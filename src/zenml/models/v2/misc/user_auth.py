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
"""Model definition for auth users."""

import re
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import Field, SecretStr

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import BaseZenModel

if TYPE_CHECKING:
    from passlib.context import CryptContext


class UserAuthModel(BaseZenModel):
    """Authentication Model for the User.

    This model is only used server-side. The server endpoints can use this model
    to authenticate the user credentials (Token, Password).
    """

    id: UUID = Field(title="The unique resource id.")

    created: datetime = Field(title="Time when this resource was created.")
    updated: datetime = Field(
        title="Time when this resource was last updated."
    )

    active: bool = Field(default=False, title="Active account.")
    is_service_account: bool = Field(
        title="Indicates whether this is a service account or a regular user "
        "account."
    )

    activation_token: Optional[SecretStr] = Field(default=None, exclude=True)
    password: Optional[SecretStr] = Field(default=None, exclude=True)
    name: str = Field(
        title="The unique username for the account.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    full_name: str = Field(
        default="",
        title="The full name for the account owner. Only relevant for user "
        "accounts.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    email_opted_in: Optional[bool] = Field(
        default=None,
        title="Whether the user agreed to share their email. Only relevant for "
        "user accounts",
        description="`null` if not answered, `true` if agreed, "
        "`false` if skipped.",
    )

    hub_token: Optional[str] = Field(
        default=None,
        title="JWT Token for the connected Hub account. Only relevant for user "
        "accounts.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    @classmethod
    def _get_crypt_context(cls) -> "CryptContext":
        """Returns the password encryption context.

        Returns:
            The password encryption context.
        """
        from passlib.context import CryptContext

        return CryptContext(schemes=["bcrypt"], deprecated="auto")

    @classmethod
    def _is_hashed_secret(cls, secret: SecretStr) -> bool:
        """Checks if a secret value is already hashed.

        Args:
            secret: The secret value to check.

        Returns:
            True if the secret value is hashed, otherwise False.
        """
        return (
            re.match(r"^\$2[ayb]\$.{56}$", secret.get_secret_value())
            is not None
        )

    @classmethod
    def _get_hashed_secret(cls, secret: Optional[SecretStr]) -> Optional[str]:
        """Hashes the input secret and returns the hash value.

        Only applied if supplied and if not already hashed.

        Args:
            secret: The secret value to hash.

        Returns:
            The secret hash value, or None if no secret was supplied.
        """
        if secret is None:
            return None
        if cls._is_hashed_secret(secret):
            return secret.get_secret_value()
        pwd_context = cls._get_crypt_context()
        return pwd_context.hash(secret.get_secret_value())

    def get_password(self) -> Optional[str]:
        """Get the password.

        Returns:
            The password as a plain string, if it exists.
        """
        if self.password is None:
            return None
        return self.password.get_secret_value()

    def get_hashed_password(self) -> Optional[str]:
        """Returns the hashed password, if configured.

        Returns:
            The hashed password.
        """
        return self._get_hashed_secret(self.password)

    def get_hashed_activation_token(self) -> Optional[str]:
        """Returns the hashed activation token, if configured.

        Returns:
            The hashed activation token.
        """
        return self._get_hashed_secret(self.activation_token)

    @classmethod
    def verify_password(
        cls, plain_password: str, user: Optional["UserAuthModel"] = None
    ) -> bool:
        """Verifies a given plain password against the stored password.

        Args:
            plain_password: Input password to be verified.
            user: User for which the password is to be verified.

        Returns:
            True if the passwords match.
        """
        # even when the user or password is not set, we still want to execute
        # the password hash verification to protect against response discrepancy
        # attacks (https://cwe.mitre.org/data/definitions/204.html)
        password_hash: Optional[str] = None
        if (
            user is not None
            # Disable password verification for service accounts as an extra
            # security measure. Service accounts should only be used with API
            # keys.
            and not user.is_service_account
            and user.password is not None
        ):  # and user.active:
            password_hash = user.get_hashed_password()
        pwd_context = cls._get_crypt_context()
        return pwd_context.verify(plain_password, password_hash)

    @classmethod
    def verify_activation_token(
        cls, activation_token: str, user: Optional["UserAuthModel"] = None
    ) -> bool:
        """Verifies a given activation token against the stored token.

        Args:
            activation_token: Input activation token to be verified.
            user: User for which the activation token is to be verified.

        Returns:
            True if the token is valid.
        """
        # even when the user or token is not set, we still want to execute the
        # token hash verification to protect against response discrepancy
        # attacks (https://cwe.mitre.org/data/definitions/204.html)
        token_hash: str = ""
        if (
            user is not None
            # Disable activation tokens for service accounts as an extra
            # security measure. Service accounts should only be used with API
            # keys.
            and not user.is_service_account
            and user.activation_token is not None
            and not user.active
        ):
            token_hash = user.get_hashed_activation_token() or ""
        pwd_context = cls._get_crypt_context()
        return pwd_context.verify(activation_token, token_hash)
