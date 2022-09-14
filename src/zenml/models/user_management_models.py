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
"""Model definitions for users, teams, and roles."""

import base64
from datetime import datetime, timedelta
import os
from jose import JWTError, jwt

from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, SecretStr, root_validator
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import ENV_ZENML_JWT_SECRET_KEY
from zenml.exceptions import AuthorizationException

from zenml.utils.analytics_utils import AnalyticsTrackedModelMixin
from zenml.utils.enum_utils import StrEnum

if TYPE_CHECKING:
    from passlib.context import CryptContext


class RoleModel(AnalyticsTrackedModelMixin):
    """Pydantic object representing a role.

    Attributes:
        id: Id of the role.
        created_at: Date when the role was created.
        name: Name of the role.
        permissions: Set of permissions allowed by this role.
    """

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["id"]

    id: Optional[UUID] = None
    name: str
    created_at: Optional[datetime] = None


class JWTTokenType(StrEnum):
    """The type of JWT token."""

    ACCESS_TOKEN = "access_token"
    INVITE_TOKEN = "invite_token"


class JWTToken(BaseModel):
    """Pydantic object representing a JWT token.

    Attributes:
        token: The JWT token.
        token_type: The type of token.
    """

    JWT_ALGORITHM: ClassVar[str] = "HS256"

    token_type: JWTTokenType
    user_id: UUID

    @classmethod
    def decode(cls, token_type: JWTTokenType, token: str) -> "JWTToken":
        """Decodes a JWT access token.

        Decodes a JWT access token and returns a JWTToken object with the
        information retrieved from its subject claim.

        Args:
            token_type: The type of token.
            token: The encoded JWT token.

        Returns:
            The decoded JWT access token.

        Raises:
            AuthorizationException: If the token is invalid.
        """

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

        try:
            return cls(token_type=token_type, user_id=UUID(subject))
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
        claims = {
            "sub": str(self.user_id),
        }

        if expire_minutes:
            expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
            claims["exp"] = expire

        token = jwt.encode(
            claims,
            GlobalConfiguration().jwt_secret_key,
            algorithm=self.JWT_ALGORITHM,
        )
        return token


class UserModel(AnalyticsTrackedModelMixin):
    """Pydantic object representing a user.

    Attributes:
        id: Id of the user.
        name: Name of the user.
        full_name: Full name for the user account.
        email: Email address for the user account.
        active: Whether the user account is active.
        created_at: Date when the user was created.
        password: Password for the user account.
        invite_token: Invite token for the user account.
    """

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "id",
        "name",
        "full_name",
        "email",
        "active",
    ]

    id: UUID = Field(default_factory=uuid4)
    name: str = ""
    full_name: str = ""
    email: str = ""
    active: bool = False
    password: Optional[SecretStr] = Field(None, exclude=True)
    invite_token: Optional[SecretStr] = Field(None, exclude=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def _get_crypt_context(cls) -> "CryptContext":
        """Returns the password encryption context.

        Returns:
            The password encryption context.
        """
        from passlib.context import CryptContext

        return CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password: str) -> bool:
        """Verifies a given plain password against the stored password.

        Args:
            plain_password: Input password to be verified.

        Returns:
            True if the passwords match.
        """
        if self.password is None:
            return False
        if not self.active:
            return False
        pwd_context = self._get_crypt_context()
        return pwd_context.verify(
            plain_password, self.password.get_secret_value()
        )

    def get_password(self) -> Optional[str]:
        """Get the password.

        Returns:
            The password as a plain string, if it exists.
        """
        if self.password is None:
            return None
        return self.password.get_secret_value()

    def hash_password(self) -> "UserModel":
        """Hashes the stored password and replaces it with the hashed value.

        Returns:
            The user model, as a convenience.
        """
        if self.password is None:
            return
        pwd_context = self._get_crypt_context()
        self.password = pwd_context.hash(self.password.get_secret_value())
        return self

    def verify_access_token(self, token: JWTToken) -> None:
        """Verifies an access token.

        Verifies an access token and returns True if the token is valid
        and False otherwise.

        Args:
            encoded_token: The access token to verify.
        """
        if (
            token.token_type != JWTTokenType.ACCESS_TOKEN
            or token.user_id != self.id
            or not self.active
        ):
            raise AuthorizationException("Invalid access token")

    def generate_access_token(self) -> str:
        """Generates an access token.

        Generates an access token and returns it.
        """
        return JWTToken(
            token_type=JWTTokenType.ACCESS_TOKEN, user_id=self.id
        ).encode()

    def get_invite_token(self) -> Optional[str]:
        """Get the invite token.

        Returns:
            The invite token as a plain string, if it exists.
        """
        if self.invite_token is None:
            return None
        return self.invite_token.get_secret_value()

    def verify_invite_token(self, invite_token: str) -> None:
        """Verifies a given invite token against the stored invite token.

        Args:
            invite_token: Input invite token to be verified.

        Raises:
            AuthorizationException: If the invite token is invalid.
        """
        if (
            self.active
            or self.invite_token is None
            or invite_token != self.invite_token
        ):
            raise AuthorizationException(
                f"Invalid invite token for user {self.name}"
            )

    def generate_invite_token(self) -> str:
        """Generates and stores a new invite token.

        Returns:
            The generated invite token.
        """
        token = JWTToken(token_type=JWTTokenType.INVITE_TOKEN, user_id=self.id)
        self.invite_token = token.encode()
        return self.invite_token


class TeamModel(AnalyticsTrackedModelMixin):
    """Pydantic object representing a team.

    Attributes:
        id: Id of the team.
        created_at: Date when the team was created.
        name: Name of the team.
    """

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["id"]

    id: Optional[UUID] = None
    name: str
    created_at: Optional[datetime] = None


class RoleAssignmentModel(BaseModel):
    """Pydantic object representing a role assignment.

    Attributes:
        id: Id of the role assignment.
        role_id: Id of the role.
        project_id: Optional ID of a project that the role is limited to.
        team_id: Id of a team to which the role is assigned.
        user_id: Id of a user to which the role is assigned.
        created_at: Date when the role was assigned.
    """

    id: Optional[UUID] = None
    role_id: UUID
    project_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    created_at: Optional[datetime] = None

    @root_validator
    def ensure_single_entity(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validates that either `user_id` or `team_id` is set.

        Args:
            values: The values to validate.

        Returns:
            The validated values.

        Raises:
            ValueError: If neither `user_id` nor `team_id` is set.
        """
        user_id = values.get("user_id", None)
        team_id = values.get("team_id", None)
        if user_id and team_id:
            raise ValueError("Only `user_id` or `team_id` is allowed.")

        if not (user_id or team_id):
            raise ValueError(
                "Missing `user_id` or `team_id` for role assignment."
            )

        return values
