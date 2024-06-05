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
"""Models representing service accounts."""

from typing import TYPE_CHECKING, ClassVar, List, Optional, Type, Union

from pydantic import ConfigDict, Field

from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import (
    BaseDatedResponseBody,
    BaseIdentifiedResponse,
    BaseRequest,
    BaseResponseMetadata,
    BaseResponseResources,
    BaseUpdate,
)
from zenml.models.v2.base.filter import AnyQuery, BaseFilter

if TYPE_CHECKING:
    from zenml.models.v2.base.filter import AnySchema
    from zenml.models.v2.core.user import UserResponse


# ------------------ Request Model ------------------
class ServiceAccountRequest(BaseRequest):
    """Request model for service accounts."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "name",
        "active",
    ]

    name: str = Field(
        title="The unique name for the service account.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: Optional[str] = Field(
        default=None,
        title="A description of the service account.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    active: bool = Field(title="Whether the service account is active or not.")
    model_config = ConfigDict(validate_assignment=True, extra="ignore")


# ------------------ Update Model ------------------


class ServiceAccountUpdate(BaseUpdate):
    """Update model for service accounts."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["name", "active"]

    name: Optional[str] = Field(
        title="The unique name for the service account.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    description: Optional[str] = Field(
        title="A description of the service account.",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    active: Optional[bool] = Field(
        title="Whether the service account is active or not.",
        default=None,
    )

    model_config = ConfigDict(validate_assignment=True)


# ------------------ Response Model ------------------


class ServiceAccountResponseBody(BaseDatedResponseBody):
    """Response body for service accounts."""

    active: bool = Field(default=False, title="Whether the account is active.")


class ServiceAccountResponseMetadata(BaseResponseMetadata):
    """Response metadata for service accounts."""

    description: str = Field(
        default="",
        title="A description of the service account.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )


class ServiceAccountResponseResources(BaseResponseResources):
    """Class for all resource models associated with the service account entity."""


class ServiceAccountResponse(
    BaseIdentifiedResponse[
        ServiceAccountResponseBody,
        ServiceAccountResponseMetadata,
        ServiceAccountResponseResources,
    ]
):
    """Response model for service accounts."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "name",
        "active",
    ]

    name: str = Field(
        title="The unique username for the account.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "ServiceAccountResponse":
        """Get the hydrated version of this service account.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_service_account(self.id)

    def to_user_model(self) -> "UserResponse":
        """Converts the service account to a user model.

        For now, a lot of code still relies on the active user and resource
        owners being a UserResponse object, which is a superset of the
        ServiceAccountResponse object. We need this method to convert the
        service account to a user.

        Returns:
            The user model.
        """
        from zenml.models.v2.core.user import (
            UserResponse,
            UserResponseBody,
            UserResponseMetadata,
        )

        return UserResponse(
            id=self.id,
            name=self.name,
            body=UserResponseBody(
                active=self.active,
                is_service_account=True,
                email_opted_in=False,
                created=self.created,
                updated=self.updated,
                is_admin=False,
            ),
            metadata=UserResponseMetadata(
                description=self.description,
            ),
        )

    # Body and metadata properties
    @property
    def active(self) -> bool:
        """The `active` property.

        Returns:
            the value of the property.
        """
        return self.get_body().active

    @property
    def description(self) -> str:
        """The `description` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().description


# ------------------ Filter Model ------------------
class ServiceAccountFilter(BaseFilter):
    """Model to enable advanced filtering of service accounts."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the user",
    )
    description: Optional[str] = Field(
        default=None,
        title="Filter by the service account description.",
    )
    active: Optional[Union[bool, str]] = Field(
        default=None,
        description="Whether the user is active",
        union_mode="left_to_right",
    )

    def apply_filter(
        self,
        query: AnyQuery,
        table: Type["AnySchema"],
    ) -> AnyQuery:
        """Override to filter out user accounts from the query.

        Args:
            query: The query to which to apply the filter.
            table: The query table.

        Returns:
            The query with filter applied.
        """
        query = super().apply_filter(query=query, table=table)
        query = query.where(
            getattr(table, "is_service_account") == True  # noqa: E712
        )

        return query
