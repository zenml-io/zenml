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
"""Models representing team role assignments."""

from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID

from pydantic import Field

from zenml.models.v2.base.base import (
    BaseRequest,
    BaseResponse,
    BaseResponseBody,
    BaseResponseMetadata,
)
from zenml.models.v2.base.filter import BaseFilter
from zenml.models.v2.base.utils import hydrated_property

if TYPE_CHECKING:
    from zenml.models.v2.core.role import RoleResponse
    from zenml.models.v2.core.team import TeamResponse
    from zenml.models.v2.core.workspace import WorkspaceResponse

# ------------------ Request Model ------------------


class TeamRoleAssignmentRequest(BaseRequest):
    """Request model for team role assignments."""

    workspace: Optional[UUID] = Field(
        default=None,
        title="The workspace that the role is limited to.",
    )
    team: UUID = Field(title="The team that the role is assigned to.")
    role: UUID = Field(title="The role.")


# ------------------ Update Model ------------------

# There is no update model for team role assignments.

# ------------------ Response Model ------------------


class TeamRoleAssignmentResponseBody(BaseResponseBody):
    """Response model for team role assignments."""


class TeamRoleAssignmentResponseMetadata(BaseResponseMetadata):
    """Response metadata for team role assignments."""

    workspace: Optional["WorkspaceResponse"] = Field(
        title="The workspace scope of this role assignment.", default=None
    )
    team: Optional["TeamResponse"] = Field(
        title="The team the role is assigned to.", default=None
    )
    role: Optional["RoleResponse"] = Field(
        title="The assigned role.", default=None
    )


class TeamRoleAssignmentResponse(BaseResponse):
    """Response model for team role assignments."""

    # Body and metadata pair
    body: "TeamRoleAssignmentResponseBody"
    metadata: Optional["TeamRoleAssignmentResponseMetadata"]

    def get_hydrated_version(self) -> "TeamRoleAssignmentResponse":
        """Get the hydrated version of the team role assignment."""
        from zenml.client import Client

        return Client().zen_store.get_team_role_assignment(self.id)

    # Body and metadata properties
    @hydrated_property
    def workspace(self):
        """The `workspace` property."""
        return self.metadata.workspace

    @hydrated_property
    def team(self):
        """The `team` property."""
        return self.metadata.team

    @hydrated_property
    def role(self):
        """The `role` property."""
        return self.metadata.role


# ------------------ Filter Model ------------------


class TeamRoleAssignmentFilter(BaseFilter):
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
