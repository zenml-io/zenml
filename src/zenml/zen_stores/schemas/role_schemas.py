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
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel

from zenml.enums import PermissionType
from zenml.new_models import (
    RoleAssignmentRequestModel,
    RoleRequestModel,
    RoleResponseModel, RoleUpdateModel,
)
from zenml.new_models.role_assignment_models import RoleAssignmentResponseModel
from zenml.zen_stores.schemas.base_schemas import BaseSchema, NamedSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.project_schemas import ProjectSchema
    from zenml.zen_stores.schemas.team_schemas import TeamSchema, UserSchema


class RolePermissionSchema(SQLModel, table=True):
    """SQL Model for team assignments."""

    name: PermissionType = Field(primary_key=True)
    role_id: UUID = Field(primary_key=True, foreign_key="roleschema.id")
    roles: List["RoleSchema"] = Relationship(back_populates="permissions")


class RoleSchema(NamedSchema, table=True):
    """SQL Model for roles."""

    user_role_assignments: List["UserRoleAssignmentSchema"] = Relationship(
        back_populates="role", sa_relationship_kwargs={"cascade": "delete"}
    )
    team_role_assignments: List["TeamRoleAssignmentSchema"] = Relationship(
        back_populates="role", sa_relationship_kwargs={"cascade": "delete"}
    )
    permissions: List["RolePermissionSchema"] = Relationship(
        back_populates="roles", sa_relationship_kwargs={"cascade": "delete"}
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

    def update(self, role_update: RoleUpdateModel):
        for field, value in role_update.dict(exclude_unset=True).items():
            setattr(self, field, value)

        self.updated = datetime.now()
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
            permissions=[PermissionType(p.name) for p in self.permissions],
        )


class UserRoleAssignmentSchema(BaseSchema, table=True):
    """SQL Model for assigning roles to users for a given project."""

    role_id: UUID = Field(foreign_key="roleschema.id")
    user_id: UUID = Field(foreign_key="userschema.id")
    project_id: Optional[UUID] = Field(
        foreign_key="projectschema.id", nullable=True
    )

    role: RoleSchema = Relationship(back_populates="user_role_assignments")
    user: "UserSchema" = Relationship(back_populates="assigned_roles")
    project: Optional["ProjectSchema"] = Relationship(
        back_populates="user_role_assignments"
    )

    @classmethod
    def from_request(
        cls, role_assignment: RoleAssignmentRequestModel
    ) -> "UserRoleAssignmentSchema":
        """ """
        return cls(
            role_id=role_assignment.role,
            user_id=role_assignment.user,
            project_id=role_assignment.project,
        )

    def to_model(self) -> RoleAssignmentResponseModel:
        """Convert a `UserRoleAssignmentSchema` to a `RoleAssignmentModel`.

        Returns:
            The converted `RoleAssignmentModel`.
        """
        return RoleAssignmentResponseModel(
            id=self.id,
            role=self.role_id,
            user=self.user_id,
            project=self.project_id,
            created=self.created,
            updated=self.updated,
        )


class TeamRoleAssignmentSchema(BaseSchema, table=True):
    """SQL Model for assigning roles to teams for a given project."""

    role_id: UUID = Field(foreign_key="roleschema.id")
    team_id: UUID = Field(foreign_key="teamschema.id")
    project_id: Optional[UUID] = Field(
        foreign_key="projectschema.id", nullable=True
    )
    role: RoleSchema = Relationship(back_populates="team_role_assignments")
    team: "TeamSchema" = Relationship(back_populates="assigned_roles")
    project: Optional["ProjectSchema"] = Relationship(
        back_populates="team_role_assignments"
    )

    @classmethod
    def from_request(
        cls, role_assignment: RoleAssignmentRequestModel
    ) -> "TeamRoleAssignmentSchema":
        """ """
        return cls(
            role_id=role_assignment.role,
            team_id=role_assignment.team,
            project_id=role_assignment.project,
        )

    def to_model(self) -> RoleAssignmentResponseModel:
        """Convert a `TeamRoleAssignmentSchema` to a `RoleAssignmentModel`.

        Returns:
            The converted `RoleAssignmentModel`.
        """
        return RoleAssignmentResponseModel(
            id=self.id,
            role=self.role_id,
            team=self.team_id,
            project=self.project_id,
            created=self.created,
            updated=self.updated,
        )
