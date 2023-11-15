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

from typing import (
    TYPE_CHECKING,
    ClassVar,
    List,
    Optional,
    Type,
    Union,
)

from pydantic import BaseModel, Field

from zenml.logger import get_logger
from zenml.models import BaseFilterModel, RoleResponseModel
from zenml.models.base_models import (
    BaseRequestModel,
    BaseResponseModel,
    update_model,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.models.user_models import UserResponseModel

if TYPE_CHECKING:
    from sqlmodel.sql.expression import Select, SelectOfScalar

    from zenml.models.filter_models import AnySchema
    from zenml.models.team_models import TeamResponseModel

logger = get_logger(__name__)

# ---- #
# BASE #
# ---- #


class ServiceAccountBaseModel(BaseModel):
    """Base model for service accounts."""

    name: str = Field(
        title="The unique username for the account.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: str = Field(
        default="",
        title="A description of the service account.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )

    active: bool = Field(default=False, title="Whether the account is active.")


# -------- #
# RESPONSE #
# -------- #


class ServiceAccountResponseModel(ServiceAccountBaseModel, BaseResponseModel):
    """Response model for service accounts."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "name",
        "active",
    ]

    teams: Optional[List["TeamResponseModel"]] = Field(
        default=None, title="The list of teams for this service account."
    )
    roles: Optional[List["RoleResponseModel"]] = Field(
        default=None, title="The list of roles for this service account."
    )

    def to_user_model(self) -> UserResponseModel:
        """Converts the service account to a user model.

        For now, a lot of code still relies on the active user and resource
        owners being a UserResponse object, which is a superset of the
        ServiceAccountResponse object. We need this method to convert the
        service account to a user.

        Returns:
            The user model.
        """
        return UserResponseModel(
            **self.dict(exclude_none=True),
            is_service_account=True,
            email_opted_in=False,
        )


# ------ #
# FILTER #
# ------ #


class ServiceAccountFilterModel(BaseFilterModel):
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
    )

    def apply_filter(
        self,
        query: Union["Select[AnySchema]", "SelectOfScalar[AnySchema]"],
        table: Type["AnySchema"],
    ) -> Union["Select[AnySchema]", "SelectOfScalar[AnySchema]"]:
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


# ------- #
# REQUEST #
# ------- #


class ServiceAccountRequestModel(BaseRequestModel):
    """Request model for service accounts.

    This model is used to create a service account.
    """

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

    class Config:
        """Pydantic configuration class."""

        # Validate attributes when assigning them
        validate_assignment = True
        extra = "ignore"


# ------ #
# UPDATE #
# ------ #


@update_model
class ServiceAccountUpdateModel(ServiceAccountRequestModel):
    """Update model for service accounts."""

    pass
