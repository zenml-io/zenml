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

from typing import TYPE_CHECKING, List

from sqlmodel import Relationship

from zenml.new_models import ProjectModel, ProjectRequestModel
from zenml.zen_stores.schemas.base_schemas import BaseSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import (
        FlavorSchema,
        PipelineRunSchema,
        PipelineSchema,
        StackComponentSchema,
        StackSchema,
        TeamRoleAssignmentSchema,
        UserRoleAssignmentSchema,
    )


class ProjectSchema(BaseSchema, table=True):
    """SQL Model for projects."""

    name: str
    description: str

    user_role_assignments: List["UserRoleAssignmentSchema"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "delete"}
    )
    team_role_assignments: List["TeamRoleAssignmentSchema"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete"},
    )
    stacks: List["StackSchema"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "delete"}
    )
    components: List["StackComponentSchema"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "delete"}
    )
    flavors: List["FlavorSchema"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "delete"}
    )
    pipelines: List["PipelineSchema"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "delete"}
    )
    runs: List["PipelineRunSchema"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "delete"}
    )

    @classmethod
    def from_request(cls, project: ProjectRequestModel) -> "ProjectSchema":
        """Create a `ProjectSchema` from a `ProjectModel`.

        Args:
            project: The `ProjectModel` from which to create the schema.

        Returns:
            The created `ProjectSchema`.
        """
        return cls(name=project.name, description=project.description)

    def to_model(self) -> ProjectModel:
        """Convert a `ProjectSchema` to a `ProjectModel`.

        Returns:
            The converted `ProjectModel`.
        """
        return ProjectModel(
            id=self.id,
            name=self.name,
            description=self.description,
            created=self.created,
            updated=self.updated,
        )
