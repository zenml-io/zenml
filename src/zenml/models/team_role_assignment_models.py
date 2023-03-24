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
    from zenml.models.role_models import RoleResponseModel
    from zenml.models.team_models import TeamResponseModel
    from zenml.models.workspace_models import WorkspaceResponseModel

# ---- #
# BASE #
# ---- #


class TeamRoleAssignmentBaseModel(BaseModel):
    """Base model for role assignments."""


# -------- #
# RESPONSE #
# -------- #


class TeamRoleAssignmentResponseModel(
    TeamRoleAssignmentBaseModel, BaseResponseModel
):
    """Response model for role assignments with all entities hydrated."""

    workspace: Optional["WorkspaceResponseModel"] = Field(
        title="The workspace scope of this role assignment.", default=None
    )
    team: Optional["TeamResponseModel"] = Field(
        title="The team the role is assigned to.", default=None
    )
    role: Optional["RoleResponseModel"] = Field(
        title="The assigned role.", default=None
    )


# ------ #
# FILTER #
# ------ #


class TeamRoleAssignmentFilterModel(BaseFilterModel):
    """Model to enable advanced filtering of all Role Assignments."""

    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Workspace of the RoleAssignment"
    )
    team_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Team in the RoleAssignment"
    )
    role_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Role in the RoleAssignment"
    )


# ------- #
# REQUEST #
# ------- #


class TeamRoleAssignmentRequestModel(
    TeamRoleAssignmentBaseModel, BaseRequestModel
):
    """Request model for role assignments using UUIDs for all entities."""

    workspace: Optional[UUID] = Field(
        default=None, title="The workspace that the role is limited to."
    )
    team: UUID = Field(
        title="The user that the role is assigned to.",
    )

    role: UUID = Field(title="The role.")
