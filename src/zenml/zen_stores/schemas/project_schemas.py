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
"""SQL Model Implementations for Projects."""

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from zenml.models import ProjectModel

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.user_management_schemas import (
        TeamRoleAssignmentSchema,
        UserRoleAssignmentSchema,
    )


class ProjectSchema(SQLModel, table=True):
    """SQL Model for projects."""

    id: UUID = Field(primary_key=True, default_factory=uuid4)
    name: str
    description: Optional[str] = Field(nullable=True)
    created_at: datetime = Field(default_factory=datetime.now)

    user_role_assignments: List["UserRoleAssignmentSchema"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "delete"}
    )
    team_role_assignments: List["TeamRoleAssignmentSchema"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "delete"}
    )

    @classmethod
    def from_create_model(cls, model: ProjectModel) -> "ProjectSchema":
        return cls(name=model.name, description=model.description)

    def from_update_model(self, model: ProjectModel) -> "ProjectSchema":
        self.name = model.name
        self.description = model.description
        return self

    def to_model(self) -> ProjectModel:
        return ProjectModel(
            id=self.id,
            name=self.name,
            description=self.description,
            created_at=self.created_at,
        )
