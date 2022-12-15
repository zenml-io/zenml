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
"""Models representing users."""

import re
from datetime import datetime, timedelta
from secrets import token_hex
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, cast
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr, root_validator

from zenml.config.global_config import GlobalConfiguration
from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger
from zenml.models.base_models import (
    BaseRequestModel,
    BaseResponseModel,
    update_model,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH
from zenml.utils.enum_utils import StrEnum

if TYPE_CHECKING:
    from passlib.context import CryptContext  # type: ignore[import]

    from zenml.models.team_models import TeamResponseModel
logger = get_logger(__name__)


class JWTTokenType(StrEnum):
    """The type of JWT token."""

    ACCESS_TOKEN = "access_token"


class JWTToken(BaseModel):
    """Pydantic object representing a JWT token.

    Attributes:
        token_type: The type of token.
        user_id: The id of the authenticated User
        permissions: The permissions scope of the authenticated user
    """

    JWT_ALGORITHM: ClassVar[str] = "HS256"

    token_type: JWTTokenType
    user_id: UUID
    permissions: List[str]

    @classmethod
    def decode(cls, token_type: JWTTokenType, token: str) -> "JWTToken":
        """Decodes a JWT access token.

        Decodes a JWT access token and returns a `JWTToken` object with the
        information retrieved from its subject claim.

        Args:
            token_type: The type of token.
            token: The encoded JWT token.

        Returns:
            The decoded JWT access token.

        Raises:
            AuthorizationException: If the token is invalid.
        """
        # import here to keep these dependencies out of the client
        from jose import JWTError, jwt

        try:
            payload = jwt.decode(
                token,
                GlobalConfiguration().jwt_secret_key,
                algorithms=[cls.JWT_ALGORITHM],
            )
        except JWTError as e:
            raise AuthorizationException(f"Invalid JWT token: {e}") from e

        subject: str = payload.get("sub")
        if subject is None:
            raise AuthorizationException(
                "Invalid JWT token: the subject claim is missing"
            )
        permissions: List[str] = payload.get("permissions")
        if permissions is None:
            raise AuthorizationException(
                "Invalid JWT token: the permissions scope is missing"
            )

        try:
            return cls(
                token_type=token_type,
                user_id=UUID(subject),
                permissions=set(permissions),
            )
        except ValueError as e:
            raise AuthorizationException(
                f"Invalid JWT token: could not decode subject claim: {e}"
            ) from e

    def encode(self, expire_minutes: Optional[int] = None) -> str:
        """Creates a JWT access token.

        Generates and returns a JWT access token with the subject claim set to
        contain the information in this Pydantic object.

        Args:
            expire_minutes: Number of minutes the token should be valid. If not
                provided, the token will not be set to expire.

        Returns:
            The generated access token.
        """
        # import here to keep these dependencies out of the client
        from jose import jwt

        claims: Dict[str, Any] = {
            "sub": str(self.user_id),
            "permissions": list(self.permissions),
        }

        if expire_minutes:
            expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
            claims["exp"] = expire

        token: str = jwt.encode(
            claims,
            GlobalConfiguration().jwt_secret_key,
            algorithm=self.JWT_ALGORITHM,
        )
        return token


# ---- #
# BASE #
# ---- #


class UserBaseModel(BaseModel):
    """Base model for users."""

    name: str = Field(
        title="The unique username for the account.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    full_name: str = Field(
        default="",
        title="The full name for the account owner.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    email_opted_in: Optional[bool] = Field(
        title="Whether the user agreed to share their email.",
        description="`null` if not answered, `true` if agreed, "
        "`false` if skipped.",
    )

    active: bool = Field(default=False, title="Active account.")

    @classmethod
    def _get_crypt_context(cls) -> "CryptContext":
        """Returns the password encryption context.

        Returns:
            The password encryption context.
        """
        from passlib.context import CryptContext

        return CryptContext(schemes=["bcrypt"], deprecated="auto")


# -------- #
# RESPONSE #
# -------- #


class UserResponseModel(UserBaseModel, BaseResponseModel):
    """Response model for users.

    This returns the activation_token (which is required for the
    user-invitation-flow of the frontend. This also optionally includes the
    team the user is a part of. The email is returned optionally as well
    for use by the analytics on the client-side.
    """

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "name",
        "full_name",
        "active",
        "email_opted_in",
    ]

    activation_token: Optional[str] = Field(
        default=None, max_length=STR_FIELD_MAX_LENGTH
    )
    teams: Optional[List["TeamResponseModel"]] = Field(
        title="The list of teams for this user."
    )
    email: Optional[str] = Field(
        default="",
        title="The email address associated with the account.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def generate_access_token(self, permissions: List[str]) -> str:
        """Generates an access token.

        Generates an access token and returns it.

        Args:
            permissions: Permissions to add to the token

        Returns:
            The generated access token.
        """
        return JWTToken(
            token_type=JWTTokenType.ACCESS_TOKEN,
            user_id=self.id,
            permissions=permissions,
        ).encode()


class UserAuthModel(UserBaseModel, BaseResponseModel):
    """Authentication Model for the User.

    This model is only used server-side. The server endpoints can use this model
    to authenticate the user credentials (Token, Password).
    """

    active: bool = Field(default=False, title="Active account.")

    activation_token: Optional[SecretStr] = Field(default=None, exclude=True)
    password: Optional[SecretStr] = Field(default=None, exclude=True)
    teams: Optional[List["TeamResponseModel"]] = Field(
        title="The list of teams for this user."
    )

    def generate_access_token(self, permissions: List[str]) -> str:
        """Generates an access token.

        Generates an access token and returns it.

        Args:
            permissions: Permissions to add to the token

        Returns:
            The generated access token.
        """
        return JWTToken(
            token_type=JWTTokenType.ACCESS_TOKEN,
            user_id=self.id,
            permissions=permissions,
        ).encode()

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
        return cast(str, pwd_context.hash(secret.get_secret_value()))

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
        if user is not None and user.password is not None:  # and user.active:
            password_hash = user.get_hashed_password()
        pwd_context = cls._get_crypt_context()
        return cast(bool, pwd_context.verify(plain_password, password_hash))

    @classmethod
    def verify_access_token(cls, token: str) -> Optional["UserAuthModel"]:
        """Verifies an access token.

        Verifies an access token and returns the user that was used to generate
        it if the token is valid and None otherwise.

        Args:
            token: The access token to verify.

        Returns:
            The user that generated the token if valid, None otherwise.
        """
        try:
            access_token = JWTToken.decode(
                token_type=JWTTokenType.ACCESS_TOKEN, token=token
            )
        except AuthorizationException:
            return None

        zen_store = GlobalConfiguration().zen_store
        try:
            user = zen_store.get_auth_user(user_name_or_id=access_token.user_id)
        except KeyError:
            return None
        else:
            if user.active:
                return user

        return None

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
        token_hash: Optional[str] = None
        if (
            user is not None
            and user.activation_token is not None
            and not user.active
        ):
            token_hash = user.get_hashed_activation_token()
        pwd_context = cls._get_crypt_context()
        return cast(bool, pwd_context.verify(activation_token, token_hash))


# ------- #
# REQUEST #
# ------- #


class UserRequestModel(UserBaseModel, BaseRequestModel):
    """Request model for users.

    This model is used to create a user. The email field is optional but is
    more commonly set on the UpdateRequestModel which inherits from this model.
    Users can also optionally set their password during creation.
    """

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "name",
        "full_name",
        "active",
        "email_opted_in",
    ]

    email: Optional[str] = Field(
        default=None,
        title="The email address associated with the account.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    password: Optional[str] = Field(
        default=None,
        title="A password for the user.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    activation_token: Optional[str] = Field(
        default=None, max_length=STR_FIELD_MAX_LENGTH
    )

    class Config:
        """Pydantic configuration class."""

        # Validate attributes when assigning them
        validate_assignment = True
        # Forbid extra attributes to prevent unexpected behavior
        extra = "forbid"
        underscore_attrs_are_private = True

    @classmethod
    def _create_hashed_secret(cls, secret: Optional[str]) -> Optional[str]:
        """Hashes the input secret and returns the hash value.

        Only applied if supplied and if not already hashed.

        Args:
            secret: The secret value to hash.

        Returns:
            The secret hash value, or None if no secret was supplied.
        """
        if secret is None:
            return None
        pwd_context = cls._get_crypt_context()
        return cast(str, pwd_context.hash(secret))

    def create_hashed_password(self) -> Optional[str]:
        """Hashes the password.

        Returns:
            The hashed password.
        """
        return self._create_hashed_secret(self.password)

    def create_hashed_activation_token(self) -> Optional[str]:
        """Hashes the activation token.

        Returns:
            The hashed activation token.
        """
        return self._create_hashed_secret(self.activation_token)

    def generate_activation_token(self) -> str:
        """Generates and stores a new activation token.

        Returns:
            The generated activation token.
        """
        self.activation_token = token_hex(32)
        return self.activation_token


# ------ #
# UPDATE #
# ------ #


@update_model
class UserUpdateModel(UserRequestModel):
    """Update model for users."""

    @root_validator
    def user_email_updates(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the UserUpdateModel conforms to the email-opt-in-flow.

        Args:
            values: The values to validate.

        Returns:
            The validated values.

        Raises:
            ValueError: If the email was not provided when the email_opted_in
                field was set to True.
        """
        # When someone sets the email, or updates the email and hasn't
        #  before explicitly opted out, they are opted in
        if values["email"] is not None:
            if values["email_opted_in"] is None:
                values["email_opted_in"] = True

        # It should not be possible to do opt in without an email
        if values["email_opted_in"] is True:
            if values["email"] is None:
                raise ValueError(
                    "Please provide an email, when you are opting-in with "
                    "your email."
                )
        return values
