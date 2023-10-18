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
"""Models representing teams."""

from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from pydantic import Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.new_models.base import (
    BaseFilter,
    BaseRequest,
    BaseResponse,
    BaseResponseBody,
    BaseResponseMetadata,
    hydrated_property,
    update_model,
)

if TYPE_CHECKING:
    from zenml.new_models.core import UserResponse

# ------------------ Request Model ------------------


class TeamRequest(BaseRequest):
    """Request model for teams."""

    name: str = Field(
        title="The unique name of the team.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    users: Optional[List[UUID]] = Field(
        default=None, title="The list of users within this team."
    )


# ------------------ Update Model ------------------


@update_model
class TeamUpdate(TeamRequest):
    """Update model for teams."""


# ------------------ Response Model ------------------


class TeamResponseBody(BaseResponseBody):
    """Response body for teams."""


class TeamResponseMetadata(BaseResponseMetadata):
    """Response metadata for teams."""

    users: List["UserResponse"] = Field(
        title="The list of users within this team."
    )


class TeamResponse(BaseResponse):
    """Response model  for teams."""

    name: str = Field(
        title="The unique name of the team.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    # Body and metadata pair
    body: "TeamResponseBody"
    metadata: Optional["TeamResponseMetadata"]

    def get_hydrated_version(self) -> "TeamResponse":
        """Get the hydrated version of this team."""
        from zenml.client import Client

        return Client().get_team(self.id)

    # Helper methods
    @property
    def user_ids(self) -> List[UUID]:
        """Returns a list of user IDs that are part of this team.

        Returns:
            A list of user IDs.
        """
        if self.users:
            return [u.id for u in self.users]
        else:
            return []

    @property
    def user_names(self) -> List[str]:
        """Returns a list names of users that are part of this team.

        Returns:
            A list of names of users.
        """
        if self.users:
            return [u.name for u in self.users]
        else:
            return []

    # Body and metadata properties
    @hydrated_property
    def users(self) -> List["UserResponse"]:
        """The `users` property."""
        return self.metadata.users


# ------------------ Filter Model ------------------


class TeamFilter(BaseFilter):
    """Model to enable advanced filtering of all Teams."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the team",
    )
