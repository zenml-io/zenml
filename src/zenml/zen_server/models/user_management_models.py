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
"""REST API user management models implementation."""


from typing import Optional

from pydantic import BaseModel, Field

from zenml.models.constants import (
    MODEL_NAME_FIELD_MAX_LENGTH,
    USER_ACTIVATION_TOKEN_LENGTH,
    USER_PASSWORD_MAX_LENGTH,
)
from zenml.models.user_management_models import UserModel


class CreateUserRequest(BaseModel):
    """Model for user creation requests."""

    name: str = Field(
        title="The unique username for the account.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    full_name: Optional[str] = Field(
        default=None,
        title="The full name for the account owner.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    email: Optional[str] = Field(
        default=None,
        title="The email address associated with the account.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    password: Optional[str] = Field(
        default=None,
        title="Account password.",
        max_length=USER_PASSWORD_MAX_LENGTH,
    )

    def to_model(self) -> UserModel:
        """Create a `UserModel` from this object.

        Returns:
            The created `UserModel`.
        """
        return UserModel(
            **self.dict(exclude_none=True),
        )

    @classmethod
    def from_model(cls, user: UserModel) -> "CreateUserRequest":
        """Convert from a user model."""
        return cls(**user.dict(), password=user.get_password())


class CreateUserResponse(UserModel):
    """Model for user creation responses."""

    activation_token: Optional[str] = Field(
        default=None, title="Account activation token."
    )

    @classmethod
    def from_model(cls, user: UserModel) -> "CreateUserResponse":
        """Create a `CreateUserResponse` from a `UserModel`.

        Args:
            user: The `UserModel` to create the response from.

        Returns:
            The created `CreateUserResponse`.
        """
        response = cls(
            **user.dict(), activation_token=user.get_activation_token()
        )
        return response

    def to_model(self) -> UserModel:
        """Convert to a user model."""
        return UserModel(
            **self.dict(),
        )


class UpdateUserRequest(BaseModel):
    """Model for user update requests."""

    name: Optional[str] = Field(
        default=None,
        title="Updated username for the account.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    full_name: Optional[str] = Field(
        default=None,
        title="Updated full name for the account owner.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    email: Optional[str] = Field(
        default=None,
        title="Updated email address associated with the account.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    password: Optional[str] = Field(
        default=None,
        title="Updated account password.",
        max_length=USER_PASSWORD_MAX_LENGTH,
    )

    def apply_to_model(self, user: UserModel) -> UserModel:
        """Apply the changes to a `UserModel`.

        Args:
            user: The `UserModel` to apply the changes to.

        Returns:
            The updated `UserModel`.
        """
        for k, v in self.dict(exclude_none=True).items():
            setattr(user, k, v)
        if self.password is not None:
            user.password = self.password
        return user

    @classmethod
    def from_model(cls, user: UserModel) -> "UpdateUserRequest":
        """Convert from a user model."""
        response = cls(**user.dict(), password=user.get_password())
        return response


class ActivateUserRequest(BaseModel):
    """Model for user activation requests."""

    name: Optional[str] = Field(
        default=None,
        title="Unique username for the account.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    full_name: Optional[str] = Field(
        default=None,
        title="Full name for the account owner.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    email: Optional[str] = Field(
        default=None,
        title="Email address associated with the account.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    password: str = Field(
        title="Account password.", max_length=USER_PASSWORD_MAX_LENGTH
    )
    activation_token: str = Field(
        title="Account activation token.",
        min_length=USER_ACTIVATION_TOKEN_LENGTH,
        max_length=USER_ACTIVATION_TOKEN_LENGTH,
    )

    def apply_to_model(self, user: UserModel) -> UserModel:
        """Apply the changes to a `UserModel`.

        Args:
            user: The `UserModel` to apply the changes to.

        Returns:
            The updated `UserModel`.
        """
        for k, v in self.dict(exclude_none=True).items():
            if k in ["activation_token", "password"]:
                continue
            setattr(user, k, v)
        user.password = self.password
        # skip the activation token intentionally, because it is validated
        # separately
        return user


class DeactivateUserResponse(UserModel):
    """Model for user deactivation requests."""

    activation_token: str = Field(..., title="Account activation token.")

    @classmethod
    def from_model(cls, user: UserModel) -> "DeactivateUserResponse":
        """Create a `DeactivateUserResponse` from a `UserModel`.

        Args:
            user: The `UserModel` to create the response from.

        Returns:
            The created `DeactivateUserResponse`.
        """
        response = cls(
            **user.dict(), activation_token=user.get_activation_token()
        )
        return response
