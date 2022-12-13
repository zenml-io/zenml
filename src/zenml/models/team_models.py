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
"""Models representing teams."""

from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.models.base_models import (
    BaseRequestModel,
    BaseResponseModel,
    update_model,
)
from zenml.models.constants import MODEL_NAME_FIELD_MAX_LENGTH

if TYPE_CHECKING:
    from zenml.models.user_models import UserResponseModel


# ---- #
# BASE #
# ---- #


class TeamBaseModel(BaseModel):
    """Base model for teams."""

    name: str = Field(
        title="The unique name of the team.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )


# -------- #
# RESPONSE #
# -------- #


class TeamResponseModel(TeamBaseModel, BaseResponseModel):
    """Response model for teams."""

    users: List["UserResponseModel"] = Field(
        title="The list of users within this team."
    )

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


# ------- #
# REQUEST #
# ------- #


class TeamRequestModel(TeamBaseModel, BaseRequestModel):
    """Request model for teams."""

    users: Optional[List[UUID]] = Field(
        title="The list of users within this team."
    )


# ------ #
# UPDATE #
# ------ #


@update_model
class TeamUpdateModel(TeamRequestModel):
    """Update model for teams."""
