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
"""Models representing user role assignments."""

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import Field

from zenml.new_models.base import (
    BaseRequest,
    BaseResponse,
    BaseResponseBody,
    BaseResponseMetadata,
    hydrated_property,
)

if TYPE_CHECKING:
    from zenml.new_models.core.role import RoleResponse
    from zenml.new_models.core.user import UserResponse
    from zenml.new_models.core.workspace import WorkspaceResponse

# ------------------ Request Model ------------------


class UserRoleAssignmentRequest(BaseRequest):
    """Request model for user role assignments."""

    workspace: Optional[UUID] = Field(
        default=None,
        title="The workspace that the role is limited to.",
    )
    user: UUID = Field(title="The user that the role is assigned to.")

    role: UUID = Field(title="The role.")


# ------------------ Update Model ------------------

# There is no update model for user role assignments.

# ------------------ Response Model ------------------


class UserRoleAssignmentResponseBody(BaseResponseBody):
    """Response body for user role assignments."""


class UserRoleAssignmentResponseMetadata(BaseResponseMetadata):
    """Response metadata for user role assignments."""

    workspace: Optional["WorkspaceResponse"] = Field(
        title="The workspace scope of this role assignment.", default=None
    )
    user: Optional["UserResponse"] = Field(
        title="The user the role is assigned to.", default=None
    )
    role: Optional["RoleResponse"] = Field(
        title="The assigned role.", default=None
    )


class UserRoleAssignmentResponse(BaseResponse):
    """Response model for user role assignments."""

    # Body and metadata pair
    body: "UserRoleAssignmentResponseBody"
    metadata: Optional["UserRoleAssignmentResponseMetadata"]

    def get_hydrated_version(self) -> "UserRoleAssignmentResponse":
        """Get the hydrated version of this user role assignment."""
        from zenml.client import Client

        return Client().get_user_role_assignment(self.id)

    # Body and metadata properties
    @hydrated_property
    def workspace(self):
        """The `workspace` property."""
        return self.metadata.workspace

    @hydrated_property
    def user(self):
        """The`user` property."""
        return self.metadata.user

    @hydrated_property
    def role(self):
        """The `role` property."""
        return self.metadata.role
