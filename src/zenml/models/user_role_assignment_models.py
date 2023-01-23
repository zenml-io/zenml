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

from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.models import BaseFilterModel
from zenml.models.base_models import BaseRequestModel, BaseResponseModel

if TYPE_CHECKING:
    from zenml.models.project_models import ProjectResponseModel
    from zenml.models.role_models import RoleResponseModel
    from zenml.models.user_models import UserResponseModel

# ---- #
# BASE #
# ---- #


class UserRoleAssignmentBaseModel(BaseModel):
    """Base model for role assignments."""


# -------- #
# RESPONSE #
# -------- #


class UserRoleAssignmentResponseModel(
    UserRoleAssignmentBaseModel, BaseResponseModel
):
    """Response model for role assignments with all entities hydrated."""

    project: Optional["ProjectResponseModel"] = Field(
        title="The project scope of this role assignment.", default=None
    )
    user: Optional["UserResponseModel"] = Field(
        title="The user the role is assigned to.", default=None
    )
    role: "RoleResponseModel" = Field(title="The assigned role.", default=None)


# ------ #
# FILTER #
# ------ #


class UserRoleAssignmentFilterModel(BaseFilterModel):
    """Model to enable advanced filtering of all Role Assignments."""

    project_id: Union[UUID, str] = Field(
        default=None, description="Project of the RoleAssignment"
    )
    user_id: Union[UUID, str] = Field(
        default=None, description="User in the RoleAssignment"
    )
    role_id: Union[UUID, str] = Field(
        default=None, description="Role in the RoleAssignment"
    )


# ------- #
# REQUEST #
# ------- #


class UserRoleAssignmentRequestModel(
    UserRoleAssignmentBaseModel, BaseRequestModel
):
    """Request model for role assignments using UUIDs for all entities."""

    project: Optional[UUID] = Field(
        None, title="The project that the role is limited to."
    )
    user: UUID = Field(None, title="The user that the role is assigned to.")

    role: UUID = Field(title="The role.")
