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

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import Field

from zenml.new_models.base import (
    BaseRequest,
    BaseResponse,
    BaseResponseMetadata,
    hydrated_property,
)

if TYPE_CHECKING:
    from zenml.new_models.core.role import RoleResponse
    from zenml.new_models.core.team import TeamResponse
    from zenml.new_models.core.workspace import WorkspaceResponse

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


class TeamRoleAssignmentResponseMetadata(BaseResponseMetadata):
    """Response metadata model for team role assignments."""

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

    # Metadata related field, method and properties
    metadata: Optional["TeamRoleAssignmentResponseMetadata"]

    def get_hydrated_version(self) -> "TeamRoleAssignmentResponse":
        # TODO: Implement it with the parameterized calls
        from zenml.client import Client

        return Client().get_team_role_assignment(self.id)

    @hydrated_property
    def workspace(self):
        """The workspace property."""
        return self.metadata.workspace

    @hydrated_property
    def team(self):
        """The team property."""
        return self.metadata.team

    @hydrated_property
    def role(self):
        """The role property."""
        return self.metadata.role
