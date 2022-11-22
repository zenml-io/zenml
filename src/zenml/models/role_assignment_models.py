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
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, root_validator

from zenml.models.base_models import BaseRequestModel, BaseResponseModel

if TYPE_CHECKING:
    from zenml.models.workspace_models import WorkspaceResponseModel
    from zenml.models.role_models import RoleResponseModel
    from zenml.models.team_models import TeamResponseModel
    from zenml.models.user_models import UserResponseModel

# ---- #
# BASE #
# ---- #


class RoleAssignmentBaseModel(BaseModel):
    """Domain model for role assignments."""

    @root_validator(pre=True)
    def check_team_or_user(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values.get("team") and not values.get("user"):
            raise ValueError("Either team or user is required")
        elif values.get("team") and values.get("user"):
            raise ValueError("An assignment can not contain a user and team")
        return values


# ------- #
# REQUEST #
# ------- #


class RoleAssignmentRequestModel(RoleAssignmentBaseModel, BaseRequestModel):
    workspace: Optional[UUID] = Field(
        None, title="The workspace that the role is limited to."
    )
    team: Optional[UUID] = Field(
        None, title="The team that the role is assigned to."
    )
    user: Optional[UUID] = Field(
        None, title="The user that the role is assigned to."
    )

    role: UUID = Field(title="The role.")

    @root_validator
    def ensure_single_entity(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validates that either `user` or `team` is set.

        Args:
            values: The values to validate.

        Returns:
            The validated values.

        Raises:
            ValueError: If neither `user` nor `team` is set.
        """
        user = values.get("user", None)
        team = values.get("team", None)
        if user and team:
            raise ValueError("Only `user` or `team` is allowed.")

        if not (user or team):
            raise ValueError("Missing `user` or `team` for role assignment.")

        return values


# -------- #
# RESPONSE #
# -------- #


class RoleAssignmentResponseModel(RoleAssignmentBaseModel, BaseResponseModel):
    """"""

    workspace: Optional["WorkspaceResponseModel"] = Field(
        title="The workspace scope of this role assignment.", default=None
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
