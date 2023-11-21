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


class TeamRoleAssignmentResponse(
    BaseResponse[
        TeamRoleAssignmentResponseBody, TeamRoleAssignmentResponseMetadata
    ]
):
    """Response model for team role assignments."""

    def get_hydrated_version(self) -> "TeamRoleAssignmentResponse":
        """Get the hydrated version of the team role assignment.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_team_role_assignment(self.id)

    # Body and metadata properties
    @property
    def workspace(self) -> Optional["WorkspaceResponse"]:
        """The `workspace` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().workspace

    @property
    def team(self) -> Optional["TeamResponse"]:
        """The `team` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().team

    @property
    def role(self) -> Optional["RoleResponse"]:
        """The `role` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().role


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
