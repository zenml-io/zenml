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
from typing import List
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel

from zenml.models import TeamModel
from zenml.zen_stores.schemas import TeamRoleAssignmentSchema, UserSchema


class TeamAssignmentSchema(SQLModel, table=True):
    """SQL Model for team assignments."""

    user_id: UUID = Field(primary_key=True, foreign_key="userschema.id")
    team_id: UUID = Field(primary_key=True, foreign_key="teamschema.id")


class TeamSchema(SQLModel, table=True):
    """SQL Model for teams."""

    id: UUID = Field(primary_key=True)
    name: str
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    users: List["UserSchema"] = Relationship(
        back_populates="teams", link_model=TeamAssignmentSchema
    )
    assigned_roles: List["TeamRoleAssignmentSchema"] = Relationship(
        back_populates="team", sa_relationship_kwargs={"cascade": "delete"}
    )

    @classmethod
    def from_create_model(cls, model: TeamModel) -> "TeamSchema":
        """Create a `TeamSchema` from a `TeamModel`.

        Args:
            model: The `TeamModel` from which to create the schema.

        Returns:
            The created `TeamSchema`.
        """
        return cls(id=model.id, name=model.name)

    def from_update_model(self, model: TeamModel) -> "TeamSchema":
        """Update a `TeamSchema` from a `TeamModel`.

        Args:
            model: The `TeamModel` from which to update the schema.

        Returns:
            The updated `TeamSchema`.
        """
        self.name = model.name
        self.updated = datetime.now()
        return self

    def to_model(self) -> TeamModel:
        """Convert a `TeamSchema` to a `TeamModel`.

        Returns:
            The converted `TeamModel`.
        """
        return TeamModel(
            id=self.id,
            name=self.name,
            created=self.created,
            updated=self.updated,
        )
