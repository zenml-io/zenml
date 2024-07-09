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
"""Models representing users."""

from secrets import token_hex
from typing import (
    TYPE_CHECKING,
    AbstractSet,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import (
    BaseDatedResponseBody,
    BaseIdentifiedResponse,
    BaseRequest,
    BaseResponseMetadata,
    BaseResponseResources,
    BaseZenModel,
)
from zenml.models.v2.base.filter import AnyQuery, BaseFilter

if TYPE_CHECKING:
    from passlib.context import CryptContext

    from zenml.models.v2.base.filter import AnySchema

# ------------------ Base Model ------------------


class UserBase(BaseModel):
    """Base model for users."""

    # Fields

    email: Optional[str] = Field(
        default=None,
        title="The email address associated with the account.",
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
    password: Optional[str] = Field(
        default=None,
        title="A password for the user.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    activation_token: Optional[str] = Field(
        default=None, max_length=STR_FIELD_MAX_LENGTH
    )
    external_user_id: Optional[UUID] = Field(
        default=None,
        title="The external user ID associated with the account.",
    )
    user_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The metadata associated with the user.",
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
        return pwd_context.hash(secret)

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


# ------------------ Request Model ------------------


class UserRequest(UserBase, BaseRequest):
    """Request model for users."""

    # Analytics fields for user request models
    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "name",
        "full_name",
        "active",
        "email_opted_in",
    ]

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
    is_admin: bool = Field(
        title="Whether the account is an administrator.",
    )
    active: bool = Field(default=False, title="Whether the account is active.")

    model_config = ConfigDict(
        # Validate attributes when assigning them
        validate_assignment=True,
        # Forbid extra attributes to prevent unexpected behavior
        extra="forbid",
    )


# ------------------ Update Model ------------------


class UserUpdate(UserBase, BaseZenModel):
    """Update model for users."""

    name: Optional[str] = Field(
        title="The unique username for the account.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    full_name: Optional[str] = Field(
        default=None,
        title="The full name for the account owner. Only relevant for user "
        "accounts.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    is_admin: Optional[bool] = Field(
        default=None,
        title="Whether the account is an administrator.",
    )
    active: Optional[bool] = Field(
        default=None, title="Whether the account is active."
    )
    old_password: Optional[str] = Field(
        default=None,
        title="The previous password for the user. Only relevant for user "
        "accounts. Required when updating the password.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    @model_validator(mode="after")
    def user_email_updates(self) -> "UserUpdate":
        """Validate that the UserUpdateModel conforms to the email-opt-in-flow.

        Returns:
            The validated values.

        Raises:
            ValueError: If the email was not provided when the email_opted_in
                field was set to True.
        """
        # When someone sets the email, or updates the email and hasn't
        #  before explicitly opted out, they are opted in
        if self.email is not None:
            if self.email_opted_in is None:
                self.email_opted_in = True

        # It should not be possible to do opt in without an email
        if self.email_opted_in is True:
            if self.email is None:
                raise ValueError(
                    "Please provide an email, when you are opting-in with "
                    "your email."
                )
        return self

    def create_copy(self, exclude: AbstractSet[str]) -> "UserUpdate":
        """Create a copy of the current instance.

        Args:
            exclude: Fields to exclude from the copy.

        Returns:
            A copy of the current instance.
        """
        return UserUpdate(
            **self.model_dump(
                exclude=set(exclude),
                exclude_unset=True,
            )
        )


# ------------------ Response Model ------------------


class UserResponseBody(BaseDatedResponseBody):
    """Response body for users."""

    active: bool = Field(default=False, title="Whether the account is active.")
    activation_token: Optional[str] = Field(
        default=None,
        max_length=STR_FIELD_MAX_LENGTH,
        title="The activation token for the user. Only relevant for user "
        "accounts.",
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
    is_service_account: bool = Field(
        title="Indicates whether this is a service account or a user account."
    )
    is_admin: bool = Field(
        title="Whether the account is an administrator.",
    )


class UserResponseMetadata(BaseResponseMetadata):
    """Response metadata for users."""

    email: Optional[str] = Field(
        default="",
        title="The email address associated with the account. Only relevant "
        "for user accounts.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    hub_token: Optional[str] = Field(
        default=None,
        title="JWT Token for the connected Hub account. Only relevant for user "
        "accounts.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    external_user_id: Optional[UUID] = Field(
        default=None,
        title="The external user ID associated with the account. Only relevant "
        "for user accounts.",
    )
    user_metadata: Dict[str, Any] = Field(
        default={},
        title="The metadata associated with the user.",
    )


class UserResponseResources(BaseResponseResources):
    """Class for all resource models associated with the user entity."""


class UserResponse(
    BaseIdentifiedResponse[
        UserResponseBody, UserResponseMetadata, UserResponseResources
    ]
):
    """Response model for user and service accounts.

    This returns the activation_token that is required for the
    user-invitation-flow of the frontend. The email is returned optionally as
    well for use by the analytics on the client-side.
    """

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "name",
        "full_name",
        "active",
        "email_opted_in",
        "is_service_account",
    ]

    name: str = Field(
        title="The unique username for the account.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "UserResponse":
        """Get the hydrated version of this user.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_user(self.id)

    # Body and metadata properties
    @property
    def active(self) -> bool:
        """The `active` property.

        Returns:
            the value of the property.
        """
        return self.get_body().active

    @property
    def activation_token(self) -> Optional[str]:
        """The `activation_token` property.

        Returns:
            the value of the property.
        """
        return self.get_body().activation_token

    @property
    def full_name(self) -> str:
        """The `full_name` property.

        Returns:
            the value of the property.
        """
        return self.get_body().full_name

    @property
    def email_opted_in(self) -> Optional[bool]:
        """The `email_opted_in` property.

        Returns:
            the value of the property.
        """
        return self.get_body().email_opted_in

    @property
    def is_service_account(self) -> bool:
        """The `is_service_account` property.

        Returns:
            the value of the property.
        """
        return self.get_body().is_service_account

    @property
    def is_admin(self) -> bool:
        """The `is_admin` property.

        Returns:
            Whether the user is an admin.
        """
        return self.get_body().is_admin

    @property
    def email(self) -> Optional[str]:
        """The `email` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().email

    @property
    def hub_token(self) -> Optional[str]:
        """The `hub_token` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().hub_token

    @property
    def external_user_id(self) -> Optional[UUID]:
        """The `external_user_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().external_user_id

    @property
    def user_metadata(self) -> Dict[str, Any]:
        """The `user_metadata` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().user_metadata

    # Helper methods
    @classmethod
    def _get_crypt_context(cls) -> "CryptContext":
        """Returns the password encryption context.

        Returns:
            The password encryption context.
        """
        from passlib.context import CryptContext

        return CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------ Filter Model ------------------


class UserFilter(BaseFilter):
    """Model to enable advanced filtering of all Users."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the user",
    )
    full_name: Optional[str] = Field(
        default=None,
        description="Full Name of the user",
    )
    email: Optional[str] = Field(
        default=None,
        description="Email of the user",
    )
    active: Optional[Union[bool, str]] = Field(
        default=None,
        description="Whether the user is active",
        union_mode="left_to_right",
    )
    email_opted_in: Optional[Union[bool, str]] = Field(
        default=None,
        description="Whether the user has opted in to emails",
        union_mode="left_to_right",
    )
    external_user_id: Optional[Union[UUID, str]] = Field(
        default=None,
        title="The external user ID associated with the account.",
        union_mode="left_to_right",
    )

    def apply_filter(
        self,
        query: AnyQuery,
        table: Type["AnySchema"],
    ) -> AnyQuery:
        """Override to filter out service accounts from the query.

        Args:
            query: The query to which to apply the filter.
            table: The query table.

        Returns:
            The query with filter applied.
        """
        query = super().apply_filter(query=query, table=table)
        query = query.where(
            getattr(table, "is_service_account") != True  # noqa: E712
        )

        return query
