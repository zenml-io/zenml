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
"""SQLModel implementation of roles that can be assigned to users or teams."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from zenml.enums import PermissionType
from zenml.new_models.core import (
    RoleRequest,
    RoleResponse,
    RoleResponseMetadata,
    RoleUpdate,
    TeamRoleAssignmentRequest,
    TeamRoleAssignmentResponse,
    TeamRoleAssignmentResponseMetadata,
    UserRoleAssignmentRequest,
    UserRoleAssignmentResponse,
    UserRoleAssignmentResponseMetadata,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema, NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.team_schemas import TeamSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema


class RoleSchema(NamedSchema, table=True):
    """SQL Model for roles."""

    __tablename__ = "role"

    permissions: List["RolePermissionSchema"] = Relationship(
        back_populates="roles", sa_relationship_kwargs={"cascade": "delete"}
    )
    user_role_assignments: List["UserRoleAssignmentSchema"] = Relationship(
        back_populates="role", sa_relationship_kwargs={"cascade": "delete"}
    )
    team_role_assignments: List["TeamRoleAssignmentSchema"] = Relationship(
        back_populates="role", sa_relationship_kwargs={"cascade": "delete"}
    )

    @classmethod
    def from_request(cls, model: RoleRequest) -> "RoleSchema":
        """Create a `RoleSchema` from a `RoleResponse`.

        Args:
            model: The `RoleResponse` from which to create the schema.

        Returns:
            The created `RoleSchema`.
        """
        return cls(name=model.name)

    def update(self, role_update: RoleUpdate) -> "RoleSchema":
        """Update a `RoleSchema` from a `RoleUpdate`.

        Args:
            role_update: The `RoleUpdate` from which to update the schema.

        Returns:
            The updated `RoleSchema`.
        """
        for field, value in role_update.dict(
            exclude_unset=True, exclude={"permissions"}
        ).items():
            setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def to_model(self, hydrate: bool = False) -> RoleResponse:
        """Convert a `RoleSchema` to a `RoleResponseModel`.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The converted `RoleResponseModel`.
        """
        metadata = None
        if hydrate:
            metadata = RoleResponseMetadata()

        return RoleResponse(
            id=self.id,
            name=self.name,
            created=self.created,
            updated=self.updated,
            permissions={PermissionType(p.name) for p in self.permissions},
            metadata=metadata,
        )


class UserRoleAssignmentSchema(BaseSchema, table=True):
    """SQL Model for assigning roles to users for a given workspace."""

    __tablename__ = "user_role_assignment"

    id: UUID = Field(primary_key=True, default_factory=uuid4)
    role_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=RoleSchema.__tablename__,
        source_column="role_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    user_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )

    role: RoleSchema = Relationship(back_populates="user_role_assignments")
    user: Optional["UserSchema"] = Relationship(
        back_populates="assigned_roles"
    )
    workspace: Optional["WorkspaceSchema"] = Relationship(
        back_populates="user_role_assignments"
    )

    @classmethod
    def from_request(
        cls, role_assignment: UserRoleAssignmentRequest
    ) -> "UserRoleAssignmentSchema":
        """Create a `UserRoleAssignmentSchema` from a `RoleAssignmentRequest`.

        Args:
            role_assignment: The `RoleAssignmentRequest` from which to
                create the schema.

        Returns:
            The created `UserRoleAssignmentSchema`.
        """
        return cls(
            role_id=role_assignment.role,
            user_id=role_assignment.user,
            workspace_id=role_assignment.workspace,
        )

    def to_model(self, hydrate: bool = False) -> UserRoleAssignmentResponse:
        """Convert a `UserRoleAssignmentSchema` to a `UserRoleAssignmentResponse`.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The converted `UserRoleAssignmentResponse`.
        """

        metadata = None
        if hydrate:
            metadata = UserRoleAssignmentResponseMetadata(
                workspace=self.workspace.to_model()
                if self.workspace
                else None,
                user=self.user.to_model() if self.user else None,
                role=self.role.to_model(),
                created=self.created,
                updated=self.updated,
            )
        return UserRoleAssignmentResponse(
            id=self.id,
            metadata=metadata,
        )


class TeamRoleAssignmentSchema(BaseSchema, table=True):
    """SQL Model for assigning roles to teams for a given workspace."""

    __tablename__ = "team_role_assignment"

    id: UUID = Field(primary_key=True, default_factory=uuid4)
    role_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=RoleSchema.__tablename__,
        source_column="role_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    team_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=TeamSchema.__tablename__,
        source_column="team_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    role: RoleSchema = Relationship(back_populates="team_role_assignments")
    team: "TeamSchema" = Relationship(back_populates="assigned_roles")
    workspace: Optional["WorkspaceSchema"] = Relationship(
        back_populates="team_role_assignments"
    )

    @classmethod
    def from_request(
        cls, role_assignment: TeamRoleAssignmentRequest
    ) -> "TeamRoleAssignmentSchema":
        """Create a `TeamRoleAssignmentSchema` from a `TeamRoleAssignmentRequest`.

        Args:
            role_assignment: The `TeamRoleAssignmentRequest` from which to
                create the schema.

        Returns:
            The created `TeamRoleAssignmentSchema`.
        """
        return cls(
            role_id=role_assignment.role,
            team_id=role_assignment.team,
            workspace_id=role_assignment.workspace,
        )

    def to_model(self, hydrate: bool = False) -> TeamRoleAssignmentResponse:
        """Convert a `TeamRoleAssignmentSchema` to a `TeamRoleAssignmentResponse`.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The converted `TeamRoleAssignmentResponse`.
        """
        metadata = None
        if hydrate:
            metadata = TeamRoleAssignmentResponseMetadata(
                workspace=self.workspace.to_model()
                if self.workspace
                else None,
                team=self.team.to_model(),
                role=self.role.to_model(),
                created=self.created,
                updated=self.updated,
            )
        return TeamRoleAssignmentResponse(
            id=self.id,
            metadata=metadata,
        )


class RolePermissionSchema(SQLModel, table=True):
    """SQL Model for team assignments."""

    __tablename__ = "role_permission"

    name: PermissionType = Field(primary_key=True)
    role_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=RoleSchema.__tablename__,
        source_column="role_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )
    roles: List["RoleSchema"] = Relationship(back_populates="permissions")
