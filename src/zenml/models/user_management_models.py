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

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional
from passlib.context import CryptContext
from uuid import UUID

from pydantic import BaseModel, root_validator

from zenml.utils.analytics_utils import AnalyticsTrackedModelMixin


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


class UserCredentialsModel(BaseModel):
    """Pydantic object representing a user credentials.

    Attributes:
        password: User password.
    """

    password: Optional[str] = None
    hashed: bool = False

    @classmethod
    def _get_crypt_context(cls) -> CryptContext:
        """Returns the password encryption context.

        Returns:
            The password encryption context.
        """
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
        if self.hashed:
            pwd_context = self._get_crypt_context()
            return pwd_context.verify(plain_password, self.password)
        else:
            return plain_password == self.password

    @property
    def hashed_password(self) -> Optional[str]:
        """Get the hashed password value.

        Returns:
            The hashed password value.
        """
        if self.password is None:
            return None

        if self.hashed:
            return self.password
        pwd_context = self._get_crypt_context()
        return pwd_context.hash(self.password)

    def hash_password(self) -> None:
        """Hashes the stored password and replaces it with the hashed value, if not already so."""
        if self.password is None:
            return
        self.password = self.hashed_password
        self.hashed = True


class UserModel(AnalyticsTrackedModelMixin):
    """Pydantic object representing a user.

    Attributes:
        id: Id of the user.
        created_at: Date when the user was created.
        name: Name of the user.
        credentials: User credentials.
    """

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["id"]

    id: Optional[UUID] = None
    name: str
    created_at: Optional[datetime] = None
    credentials: Optional[UserCredentialsModel] = None

    def verify_password(self, plain_password: str) -> bool:
        """Try to authenticate with a password.

        Args:
            plain_password: Input password to be verified.

        Returns:
            True if the credentials are valid.
        """
        if not self.credentials:
            return False
        return self.credentials.verify_password(plain_password)

    def remove_credentials(self) -> "UserModel":
        """Returns a copy of this user without the credentials."""
        user_dict = self.dict()
        user_dict.pop("credentials", None)
        return UserModel(**user_dict)


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
