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


from typing import ClassVar, Optional, Type

from pydantic import BaseModel, Field

from zenml.models.constants import (
    MODEL_NAME_FIELD_MAX_LENGTH,
    USER_ACTIVATION_TOKEN_LENGTH,
    USER_PASSWORD_MAX_LENGTH,
)
from zenml.models.user_management_models import RoleModel, TeamModel, UserModel
from zenml.zen_server.models.base_models import (
    CreateRequest,
    CreateResponse,
    UpdateRequest,
    UpdateResponse,
)


class CreateUserRequest(CreateRequest):
    """Model for user creation requests."""

    DOMAIN_MODEL: ClassVar[Type[BaseModel]] = UserModel

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

    @classmethod
    def from_model(cls, model: BaseModel) -> "CreateRequest":
        """Convert a user domain model into a create request.

        Args:
            model: The user domain model to convert.

        Returns:
            The create request.
        """
        assert isinstance(model, UserModel)
        return cls(**model.dict(), password=model.get_password())


class CreateUserResponse(UserModel, CreateResponse):
    """Model for user creation responses."""

    DOMAIN_MODEL: ClassVar[Type[BaseModel]] = UserModel

    activation_token: Optional[str] = Field(
        default=None, title="Account activation token."
    )

    @classmethod
    def from_model(cls, model: BaseModel) -> "CreateResponse":
        """Convert a user domain model into a create response.

        Args:
            model: The user domain model to convert.

        Returns:
            The create response.
        """
        assert isinstance(model, UserModel)

        return cls(
            **model.dict(), activation_token=model.get_activation_token()
        )


class UpdateUserRequest(UpdateRequest):
    """Model for user update requests."""

    DOMAIN_MODEL: ClassVar[Type[BaseModel]] = UserModel

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

    def apply_to_model(self, model: UserModel) -> UserModel:
        """Apply the update changes to a user domain model.

        Args:
            model: The user domain model to update.

        Returns:
            The updated user domain model.
        """
        user = super().apply_to_model(model)
        if self.password is not None:
            user.password = self.password
        return user

    @classmethod
    def from_model(cls, model: UserModel) -> "UpdateRequest":
        """Convert a user domain model into an update request.

        Args:
            model: The user domain model to convert.

        Returns:
            The update request.
        """
        assert isinstance(model, UserModel)

        response = cls(**model.dict(), password=model.get_password())
        return response


class ActivateUserRequest(UpdateRequest):
    """Model for user activation requests."""

    DOMAIN_MODEL: ClassVar[Type[BaseModel]] = UserModel

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

    def apply_to_model(self, model: UserModel) -> UserModel:
        """Apply the update changes to a user domain model.

        Args:
            model: The user domain model to update.

        Returns:
            The updated user domain model.
        """
        for k, v in self.dict(exclude_none=True).items():
            if k in ["activation_token", "password"]:
                continue
            setattr(model, k, v)
        model.password = self.password
        # skip the activation token intentionally, because it is validated
        # separately
        return model


class DeactivateUserResponse(UserModel, UpdateResponse):
    """Model for user deactivation requests."""

    DOMAIN_MODEL: ClassVar[Type[BaseModel]] = UserModel

    activation_token: str = Field(..., title="Account activation token.")

    @classmethod
    def from_model(cls, model: UserModel) -> "UpdateResponse":
        """Convert a domain model into a user deactivation response.

        Args:
            model: The domain model to convert.

        Returns:
            The user deactivation response.
        """
        response = cls(
            **model.dict(), activation_token=model.get_activation_token()
        )
        return response


class CreateRoleRequest(CreateRequest):
    """Model for role creation requests."""

    DOMAIN_MODEL: ClassVar[Type[BaseModel]] = RoleModel

    name: str = Field(
        title="The unique name of the role.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )


class UpdateRoleRequest(UpdateRequest):
    """Model for role update requests."""

    DOMAIN_MODEL: ClassVar[Type[BaseModel]] = RoleModel

    name: Optional[str] = Field(
        default=None,
        title="Updated role name.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )


class CreateTeamRequest(CreateRequest):
    """Model for team creation requests."""

    DOMAIN_MODEL: ClassVar[Type[BaseModel]] = TeamModel

    name: str = Field(
        title="The unique name of the team.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )


class UpdateTeamRequest(UpdateRequest):
    """Model for team update requests."""

    DOMAIN_MODEL: ClassVar[Type[BaseModel]] = TeamModel

    name: Optional[str] = Field(
        default=None,
        title="Updated team name.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
