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
from typing import Any, Dict, Optional, TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field, root_validator, validator

from zenml.new_models.base_models import BaseRequestModel, BaseResponseModel

if TYPE_CHECKING:
    from zenml.new_models.project_models import ProjectResponseModel
    from zenml.new_models.user_models import TeamResponseModel
    from zenml.new_models.user_models import UserResponseModel
    from zenml.new_models.role_models import RoleResponseModel

# ---- #
# BASE #
# ---- #


class RoleAssignmentBaseModel(BaseModel):
    """Domain model for role assignments."""

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

    @validator('user', always=True)
    @classmethod
    def check_team_or_user(cls, user, values):
        if not values.get('team') and not user:
            raise ValueError('Either team or user is required')
        elif values.get('team') and user:
            raise ValueError('A role assignment can not contain a user and '
                             'team')
        return user

# ------- #
# REQUEST #
# ------- #


class RoleAssignmentRequestModel(RoleAssignmentBaseModel, BaseRequestModel):
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

