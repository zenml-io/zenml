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


from typing import Any, Optional, cast

from pydantic import BaseModel, Field, SecretStr

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


class CreateUserRequest(CreateRequest[UserModel]):
    """Model for user creation requests."""

    _MODEL_TYPE = UserModel

    name: str = Field(
        title="The unique username for the account.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    full_name: Optional[str] = Field(
        default=None,
        title="The full name for the account owner.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    password: Optional[str] = Field(
        default=None,
        title="Account password.",
        max_length=USER_PASSWORD_MAX_LENGTH,
    )

    @classmethod
    def from_model(cls, model: UserModel, **kwargs: Any) -> "CreateUserRequest":
        """Convert a user domain model into a user create request.

        Args:
            model: The user domain model to convert.
            kwargs: Additional keyword arguments to pass to the user create
                request.

        Returns:
            The user create request.
        """
        return cast(
            CreateUserRequest,
            super().from_model(model, **kwargs, password=model.get_password()),
        )


class CreateUserResponse(UserModel, CreateResponse[UserModel]):
    """Model for user creation responses."""

    _MODEL_TYPE = UserModel

    activation_token: Optional[str] = Field(  # type: ignore[assignment]
        default=None, title="Account activation token."
    )

    @classmethod
    def from_model(
        cls, model: UserModel, **kwargs: Any
    ) -> "CreateUserResponse":
        """Convert a user domain model into a user create response.

        Args:
            model: The user domain model to convert.
            kwargs: Additional keyword arguments to pass to the user create
                response.

        Returns:
            The user create response.
        """
        return cast(
            CreateUserResponse,
            super().from_model(
                model, **kwargs, activation_token=model.get_activation_token()
            ),
        )

    class Config:
        """Pydantic configuration class."""

        # Validate attributes when assigning them
        validate_assignment = True
        underscore_attrs_are_private = True


class UpdateUserRequest(UpdateRequest[UserModel]):
    """Model for user update requests."""

    _MODEL_TYPE = UserModel

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
    password: Optional[SecretStr] = Field(
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
    def from_model(cls, model: UserModel, **kwargs: Any) -> "UpdateUserRequest":
        """Convert a user domain model into an update request.

        Args:
            model: The user domain model to convert.
            kwargs: Additional keyword arguments to pass to the user update
                response.

        Returns:
            The update request.
        """
        return cast(
            UpdateUserRequest,
            super().from_model(model, **kwargs, password=model.get_password()),
        )


class ActivateUserRequest(UpdateRequest[UserModel]):
    """Model for user activation requests."""

    _MODEL_TYPE = UserModel

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
    password: SecretStr = Field(
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


class DeactivateUserResponse(UserModel, UpdateResponse[UserModel]):
    """Model for user deactivation requests."""

    _MODEL_TYPE = UserModel

    activation_token: str = Field(..., title="Account activation token.")  # type: ignore[assignment]

    @classmethod
    def from_model(
        cls, model: UserModel, **kwargs: Any
    ) -> "DeactivateUserResponse":
        """Convert a domain model into a user deactivation response.

        Args:
            model: The domain model to convert.
            kwargs: Additional keyword arguments to pass to the user
                deactivation response.

        Returns:
            The user deactivation response.
        """
        return cast(
            DeactivateUserResponse,
            super().from_model(
                model, **kwargs, activation_token=model.get_activation_token()
            ),
        )

    class Config:
        """Pydantic configuration class."""

        # Validate attributes when assigning them
        validate_assignment = True
        underscore_attrs_are_private = True


class EmailOptInModel(BaseModel):
    """Model for user deactivation requests."""

    email: Optional[str] = Field(
        default=None,
        title="Email address associated with the account.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    email_opted_in: bool = Field(
        title="Whether or not to associate the email with the user"
    )


class CreateRoleRequest(CreateRequest[RoleModel]):
    """Model for role creation requests."""

    _MODEL_TYPE = RoleModel

    name: str = Field(
        title="The unique name of the role.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )


class UpdateRoleRequest(UpdateRequest[RoleModel]):
    """Model for role update requests."""

    _MODEL_TYPE = RoleModel

    name: Optional[str] = Field(
        default=None,
        title="Updated role name.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )


class CreateTeamRequest(CreateRequest[TeamModel]):
    """Model for team creation requests."""

    _MODEL_TYPE = TeamModel

    name: str = Field(
        title="The unique name of the team.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )


class UpdateTeamRequest(UpdateRequest[TeamModel]):
    """Model for team update requests."""

    _MODEL_TYPE = TeamModel

    name: Optional[str] = Field(
        default=None,
        title="Updated team name.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
