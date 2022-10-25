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
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from zenml.models import RoleAssignmentModel, RoleModel
from zenml.zen_stores.schemas import ProjectSchema, TeamSchema, UserSchema


class RoleSchema(SQLModel, table=True):
    """SQL Model for roles."""

    id: UUID = Field(primary_key=True)
    name: str
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    user_role_assignments: List["UserRoleAssignmentSchema"] = Relationship(
        back_populates="role", sa_relationship_kwargs={"cascade": "delete"}
    )
    team_role_assignments: List["TeamRoleAssignmentSchema"] = Relationship(
        back_populates="role", sa_relationship_kwargs={"cascade": "delete"}
    )

    @classmethod
    def from_create_model(cls, model: RoleModel) -> "RoleSchema":
        """Create a `RoleSchema` from a `RoleModel`.

        Args:
            model: The `RoleModel` from which to create the schema.

        Returns:
            The created `RoleSchema`.
        """
        return cls(id=model.id, name=model.name)

    def from_update_model(self, model: RoleModel) -> "RoleSchema":
        """Update a `RoleSchema` from a `RoleModel`.

        Args:
            model: The `RoleModel` from which to update the schema.

        Returns:
            The updated `RoleSchema`.
        """
        self.name = model.name
        self.updated = datetime.now()
        return self

    def to_model(self) -> RoleModel:
        """Convert a `RoleSchema` to a `RoleModel`.

        Returns:
            The converted `RoleModel`.
        """
        return RoleModel(
            id=self.id,
            name=self.name,
            created=self.created,
            updated=self.updated,
        )


class UserRoleAssignmentSchema(SQLModel, table=True):
    """SQL Model for assigning roles to users for a given project."""

    id: UUID = Field(primary_key=True, default_factory=uuid4)
    role_id: UUID = Field(foreign_key="roleschema.id")
    user_id: UUID = Field(foreign_key="userschema.id")
    project_id: Optional[UUID] = Field(
        foreign_key="projectschema.id", nullable=True
    )
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    role: RoleSchema = Relationship(back_populates="user_role_assignments")
    user: UserSchema = Relationship(back_populates="assigned_roles")
    project: Optional["ProjectSchema"] = Relationship(
        back_populates="user_role_assignments"
    )

    def to_model(self) -> RoleAssignmentModel:
        """Convert a `UserRoleAssignmentSchema` to a `RoleAssignmentModel`.

        Returns:
            The converted `RoleAssignmentModel`.
        """
        return RoleAssignmentModel(
            id=self.id,
            role=self.role_id,
            user=self.user_id,
            project=self.project_id,
            created=self.created,
            updated=self.updated,
        )


class TeamRoleAssignmentSchema(SQLModel, table=True):
    """SQL Model for assigning roles to teams for a given project."""

    id: UUID = Field(primary_key=True, default_factory=uuid4)
    role_id: UUID = Field(foreign_key="roleschema.id")
    team_id: UUID = Field(foreign_key="teamschema.id")
    project_id: Optional[UUID] = Field(
        foreign_key="projectschema.id", nullable=True
    )
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    role: RoleSchema = Relationship(back_populates="team_role_assignments")
    team: TeamSchema = Relationship(back_populates="assigned_roles")
    project: Optional["ProjectSchema"] = Relationship(
        back_populates="team_role_assignments"
    )

    def to_model(self) -> RoleAssignmentModel:
        """Convert a `TeamRoleAssignmentSchema` to a `RoleAssignmentModel`.

        Returns:
            The converted `RoleAssignmentModel`.
        """
        return RoleAssignmentModel(
            id=self.id,
            role=self.role_id,
            team=self.team_id,
            project=self.project_id,
            created=self.created,
            updated=self.updated,
        )
