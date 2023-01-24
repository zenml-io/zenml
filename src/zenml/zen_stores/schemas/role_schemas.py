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
from zenml.models import (
    RoleRequestModel,
    RoleResponseModel,
    RoleUpdateModel,
    TeamRoleAssignmentRequestModel,
    TeamRoleAssignmentResponseModel,
    UserRoleAssignmentRequestModel,
)
from zenml.models.user_role_assignment_models import (
    UserRoleAssignmentResponseModel,
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
    def from_request(cls, model: RoleRequestModel) -> "RoleSchema":
        """Create a `RoleSchema` from a `RoleResponseModel`.

        Args:
            model: The `RoleResponseModel` from which to create the schema.

        Returns:
            The created `RoleSchema`.
        """
        return cls(name=model.name)

    def update(self, role_update: RoleUpdateModel) -> "RoleSchema":
        """Update a `RoleSchema` from a `RoleUpdateModel`.

        Args:
            role_update: The `RoleUpdateModel` from which to update the schema.

        Returns:
            The updated `RoleSchema`.
        """
        for field, value in role_update.dict(
            exclude_unset=True, exclude={"permissions"}
        ).items():
            setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def to_model(self) -> RoleResponseModel:
        """Convert a `RoleSchema` to a `RoleResponseModel`.

        Returns:
            The converted `RoleResponseModel`.
        """
        return RoleResponseModel(
            id=self.id,
            name=self.name,
            created=self.created,
            updated=self.updated,
            permissions={PermissionType(p.name) for p in self.permissions},
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
        cls, role_assignment: UserRoleAssignmentRequestModel
    ) -> "UserRoleAssignmentSchema":
        """Create a `UserRoleAssignmentSchema` from a `RoleAssignmentRequestModel`.

        Args:
            role_assignment: The `RoleAssignmentRequestModel` from which to
                create the schema.

        Returns:
            The created `UserRoleAssignmentSchema`.
        """
        return cls(
            role_id=role_assignment.role,
            user_id=role_assignment.user,
            workspace_id=role_assignment.workspace,
        )

    def to_model(self) -> UserRoleAssignmentResponseModel:
        """Convert a `UserRoleAssignmentSchema` to a `RoleAssignmentModel`.

        Returns:
            The converted `RoleAssignmentModel`.
        """
        return UserRoleAssignmentResponseModel(
            id=self.id,
            workspace=self.workspace.to_model() if self.workspace else None,
            user=self.user.to_model(_block_recursion=True)
            if self.user
            else None,
            role=self.role.to_model(),
            created=self.created,
            updated=self.updated,
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
        cls, role_assignment: TeamRoleAssignmentRequestModel
    ) -> "TeamRoleAssignmentSchema":
        """Create a `TeamRoleAssignmentSchema` from a `RoleAssignmentRequestModel`.

        Args:
            role_assignment: The `RoleAssignmentRequestModel` from which to
                create the schema.

        Returns:
            The created `TeamRoleAssignmentSchema`.
        """
        return cls(
            role_id=role_assignment.role,
            team_id=role_assignment.team,
            workspace_id=role_assignment.workspace,
        )

    def to_model(self) -> TeamRoleAssignmentResponseModel:
        """Convert a `TeamRoleAssignmentSchema` to a `RoleAssignmentModel`.

        Returns:
            The converted `RoleAssignmentModel`.
        """
        return TeamRoleAssignmentResponseModel(
            id=self.id,
            workspace=self.workspace.to_model() if self.workspace else None,
            team=self.team.to_model(_block_recursion=True),
            role=self.role.to_model(),
            created=self.created,
            updated=self.updated,
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
