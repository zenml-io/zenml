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
    from zenml.models.v2.core.user import UserResponse
    from zenml.models.v2.core.workspace import WorkspaceResponse

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

        return Client().zen_store.get_user_role_assignment(self.id)

    # Body and metadata properties
    @property
    def workspace(self) -> Optional["WorkspaceResponse"]:
        """The `workspace` property."""
        return self.get_metadata().workspace

    @property
    def user(self) -> Optional["UserResponse"]:
        """The`user` property."""
        return self.get_metadata().user

    @property
    def role(self) -> Optional["RoleResponse"]:
        """The `role` property."""
        return self.get_metadata().role


# ------------------ Filter Model ------------------


class UserRoleAssignmentFilter(BaseFilter):
    """Model to enable advanced filtering of all Role Assignments."""

    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Workspace of the RoleAssignment"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="User in the RoleAssignment"
    )
    role_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Role in the RoleAssignment"
    )
