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
"""SQL Model Implementations for Users, Teams, Roles."""


from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from zenml.models import RoleAssignmentModel, RoleModel, TeamModel, UserModel

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.project_schemas import ProjectSchema


class TeamAssignmentSchema(SQLModel, table=True):
    """SQL Model for team assignments."""

    user_id: UUID = Field(primary_key=True, foreign_key="userschema.id")
    team_id: UUID = Field(primary_key=True, foreign_key="teamschema.id")


class UserSchema(SQLModel, table=True):
    """SQL Model for users."""

    id: UUID = Field(primary_key=True, default_factory=uuid4)
    name: str
    creation_date: datetime = Field(default_factory=datetime.now)

    teams: List["TeamSchema"] = Relationship(
        back_populates="users", link_model=TeamAssignmentSchema
    )
    assigned_roles: List["UserRoleAssignmentSchema"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "delete"}
    )

    @classmethod
    def from_create_model(cls, model: UserModel) -> "UserSchema":
        return cls(name=model.name)

    def from_update_model(self, model: UserModel) -> "UserSchema":
        self.name = model.name
        return self

    def to_model(self) -> UserModel:
        return UserModel(id=self.id, name=self.name, created_at=self.creation_date)


class TeamSchema(SQLModel, table=True):
    """SQL Model for teams."""

    id: UUID = Field(primary_key=True, default_factory=uuid4)
    name: str
    created_at: datetime = Field(default_factory=datetime.now)

    users: List["UserSchema"] = Relationship(
        back_populates="teams", link_model=TeamAssignmentSchema
    )
    assigned_roles: List["TeamRoleAssignmentSchema"] = Relationship(
        back_populates="team", sa_relationship_kwargs={"cascade": "delete"}
    )

    @classmethod
    def from_create_model(cls, model: TeamModel) -> "TeamSchema":
        return cls(name=model.name)

    def to_model(self) -> TeamModel:
        return TeamModel(id=self.id, name=self.name, created_at=self.created_at)


class RoleSchema(SQLModel, table=True):
    """SQL Model for roles."""

    id: UUID = Field(primary_key=True, default_factory=uuid4)
    name: str
    created_at: datetime = Field(default_factory=datetime.now)

    user_role_assignments: List["UserRoleAssignmentSchema"] = Relationship(
        back_populates="role", sa_relationship_kwargs={"cascade": "delete"}
    )
    team_role_assignments: List["TeamRoleAssignmentSchema"] = Relationship(
        back_populates="role", sa_relationship_kwargs={"cascade": "delete"}
    )

    @classmethod
    def from_create_model(cls, model: RoleModel) -> "RoleSchema":
        return cls(name=model.name)

    def to_model(self) -> RoleModel:
        return RoleModel(id=self.id, name=self.name, created_at=self.created_at)


class UserRoleAssignmentSchema(SQLModel, table=True):
    """SQL Model for assigning roles to users for a given project."""

    id: UUID = Field(primary_key=True, default_factory=uuid4)
    role_id: UUID = Field(foreign_key="roleschema.id")
    user_id: UUID = Field(foreign_key="userschema.id")
    project_id: Optional[UUID] = Field(
        foreign_key="projectschema.id", nullable=True
    )
    created_at: datetime = Field(default_factory=datetime.now)

    role: RoleSchema = Relationship(back_populates="user_role_assignments")
    user: UserSchema = Relationship(back_populates="assigned_roles")
    project: Optional["ProjectSchema"] = Relationship(
        back_populates="user_role_assignments"
    )

    def to_model(self) -> RoleAssignmentModel:
        return RoleAssignmentModel(
            id=self.id,
            role_id=self.role_id,
            user_id=self.user_id,
            project_id=self.project_id,
            created_at=self.created_at,
        )


class TeamRoleAssignmentSchema(SQLModel, table=True):
    """SQL Model for assigning roles to teams for a given project."""

    id: UUID = Field(primary_key=True, default_factory=uuid4)
    role_id: UUID = Field(foreign_key="roleschema.id")
    team_id: UUID = Field(foreign_key="teamschema.id")
    project_id: Optional[UUID] = Field(
        foreign_key="projectschema.id", nullable=True
    )
    created_at: datetime = Field(default_factory=datetime.now)

    role: RoleSchema = Relationship(back_populates="team_role_assignments")
    team: TeamSchema = Relationship(back_populates="assigned_roles")
    project: Optional["ProjectSchema"] = Relationship(
        back_populates="team_role_assignments"
    )

    def to_model(self) -> RoleAssignmentModel:
        return RoleAssignmentModel(
            id=self.id,
            role_id=self.role_id,
            team_id=self.team_id,
            project_id=self.project_id,
            created_at=self.created_at,
        )
