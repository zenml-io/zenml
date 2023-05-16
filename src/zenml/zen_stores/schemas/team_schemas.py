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
"""SQLModel implementation of team tables."""

from datetime import datetime
from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlmodel import Relationship, SQLModel

from zenml.models import TeamResponseModel
from zenml.models.team_models import TeamUpdateModel
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.role_schemas import TeamRoleAssignmentSchema
    from zenml.zen_stores.schemas.user_schemas import UserSchema


class TeamAssignmentSchema(SQLModel, table=True):
    """SQL Model for team assignments."""

    __tablename__ = "team_assignment"

    user_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="user",  # TODO: how to reference `UserSchema.__tablename__`?
        source_column="user_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )
    team_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="team",  # TODO: how to reference `TeamSchema.__tablename__`?
        source_column="team_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )


class TeamSchema(NamedSchema, table=True):
    """SQL Model for teams."""

    __tablename__ = "team"

    users: List["UserSchema"] = Relationship(
        back_populates="teams", link_model=TeamAssignmentSchema
    )
    assigned_roles: List["TeamRoleAssignmentSchema"] = Relationship(
        back_populates="team", sa_relationship_kwargs={"cascade": "delete"}
    )

    def update(self, team_update: TeamUpdateModel) -> "TeamSchema":
        """Update a `TeamSchema` with a `TeamUpdateModel`.

        Args:
            team_update: The `TeamUpdateModel` to update the schema with.

        Returns:
            The updated `TeamSchema`.
        """
        for field, value in team_update.dict(exclude_unset=True).items():
            if field == "users":
                pass
            else:
                setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def to_model(self, _block_recursion: bool = False) -> TeamResponseModel:
        """Convert a `TeamSchema` to a `TeamResponseModel`.

        Args:
            _block_recursion: Don't recursively fill attributes

        Returns:
            The converted `TeamResponseModel`.
        """
        if _block_recursion:
            return TeamResponseModel(
                id=self.id,
                name=self.name,
                created=self.created,
                updated=self.updated,
                users=[],
            )
        else:
            return TeamResponseModel(
                id=self.id,
                name=self.name,
                created=self.created,
                updated=self.updated,
                users=[u.to_model(_block_recursion=False) for u in self.users],
            )
