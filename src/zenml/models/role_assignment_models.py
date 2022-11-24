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
"""Models representing role assignments."""

from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, root_validator

from zenml.models.base_models import BaseRequestModel, BaseResponseModel

if TYPE_CHECKING:
    from zenml.models.project_models import ProjectResponseModel
    from zenml.models.role_models import RoleResponseModel
    from zenml.models.team_models import TeamResponseModel
    from zenml.models.user_models import UserResponseModel

# ---- #
# BASE #
# ---- #


class RoleAssignmentBaseModel(BaseModel):
    """Base model for role assignments."""

    @root_validator(pre=True)
    def check_team_or_user(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Check that either a team or a user is set.

        Args:
            values: The values to validate.

        Returns:
            The validated values.

        Raises:
            ValueError: If both or neither team and user are set.
        """
        if not values.get("team") and not values.get("user"):
            raise ValueError("Either team or user is required")
        elif values.get("team") and values.get("user"):
            raise ValueError("An assignment can not contain a user and team")
        return values


# -------- #
# RESPONSE #
# -------- #


class RoleAssignmentResponseModel(RoleAssignmentBaseModel, BaseResponseModel):
    """Response model for role assignments with all entities hydrated."""

    project: Optional["ProjectResponseModel"] = Field(
        title="The project scope of this role assignment.", default=None
    )
    team: Optional["TeamResponseModel"] = Field(
        title="The team the role is assigned to.", default=None
    )
    user: Optional["UserResponseModel"] = Field(
        title="The team the role is assigned to.", default=None
    )
    role: "RoleResponseModel" = Field(
        title="The team the role is assigned to.", default=None
    )


# ------- #
# REQUEST #
# ------- #


class RoleAssignmentRequestModel(RoleAssignmentBaseModel, BaseRequestModel):
    """Request model for role assignments using UUIDs for all entities."""

    project: Optional[UUID] = Field(
        None, title="The project that the role is limited to."
    )
    team: Optional[UUID] = Field(
        None, title="The team that the role is assigned to."
    )
    user: Optional[UUID] = Field(
        None, title="The user that the role is assigned to."
    )

    role: UUID = Field(title="The role.")
