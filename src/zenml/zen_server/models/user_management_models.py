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

from pydantic import BaseModel, SecretStr

from zenml.models.user_management_models import UserModel


class UserCreateRequest(BaseModel):
    """Pydantic object representing a user create request.

    Attributes:
        name: Name of the user.
        full_name: Full name for the user account.
        email: Email address for the user account.
        password: Password for the user account.
    """

    name: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[SecretStr] = None

    def to_model(self) -> UserModel:
        """Convert to a user model."""
        return UserModel(
            **self.dict(exclude_none=True),
        )


class UserCreateResponse(UserModel):
    """Pydantic object representing a user create response.

    The invite token is included in the response.
    """

    invite_token: Optional[str] = None

    @classmethod
    def from_model(cls, user: UserModel) -> "UserCreateResponse":
        """Convert from a user model."""
        response = cls(**user.dict())
        if user.invite_token.get_secret_value():
            response.invite_token = user.invite_token.get_secret_value()
        return response


class UserUpdateRequest(BaseModel):
    """Pydantic object representing a user update request.

    Attributes:
        name: Name of the user.
        full_name: Full name for the user account.
        email: Email address for the user account.
        password: Password for the user account.
    """

    name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[SecretStr] = None

    def to_model(self, user: UserModel) -> UserModel:
        """Convert to a user model."""
        for k, v in self.dict(exclude_none=True).items():
            setattr(user, k, v)
        if self.password is not None:
            user.password = self.password.get_secret_value()
        return user


class UserActivateRequest(BaseModel):
    """Pydantic object representing a user activation request.

    Attributes:
        name: Name of the user.
        full_name: Full name for the user account.
        email: Email address for the user account.
        password: Password for the user account.
        invite_token: Invite token for the user account.
    """

    name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    password: SecretStr
    invite_token: SecretStr

    def to_model(self, user: UserModel) -> UserModel:
        """Convert to a user model."""
        for k, v in self.dict(exclude_none=True).items():
            if k in ["invite_token", "password"]:
                continue
            setattr(user, k, v)
        user.password = self.password.get_secret_value()
        return user
