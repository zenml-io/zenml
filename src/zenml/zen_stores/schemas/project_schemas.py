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
from typing import TYPE_CHECKING, List

from sqlmodel import Relationship

from zenml.models import (
    ProjectRequestModel,
    ProjectResponseModel,
    ProjectUpdateModel,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import (
        ArtifactSchema,
        FlavorSchema,
        PipelineRunSchema,
        PipelineSchema,
        StackComponentSchema,
        StackSchema,
        StepRunSchema,
        TeamRoleAssignmentSchema,
        UserRoleAssignmentSchema,
    )


class ProjectSchema(NamedSchema, table=True):
    """SQL Model for projects."""

    __tablename__ = "workspace"

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
    step_runs: List["StepRunSchema"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "delete"}
    )
    artifacts: List["ArtifactSchema"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"cascade": "delete"}
    )

    @classmethod
    def from_request(cls, project: ProjectRequestModel) -> "ProjectSchema":
        """Create a `ProjectSchema` from a `ProjectResponseModel`.

        Args:
            project: The `ProjectResponseModel` from which to create the schema.

        Returns:
            The created `ProjectSchema`.
        """
        return cls(name=project.name, description=project.description)

    def update(self, project_update: ProjectUpdateModel) -> "ProjectSchema":
        """Update a `ProjectSchema` from a `ProjectUpdateModel`.

        Args:
            project_update: The `ProjectUpdateModel` from which to update the
                schema.

        Returns:
            The updated `ProjectSchema`.
        """
        for field, value in project_update.dict(exclude_unset=True).items():
            setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def to_model(self) -> ProjectResponseModel:
        """Convert a `ProjectSchema` to a `ProjectResponseModel`.

        Returns:
            The converted `ProjectResponseModel`.
        """
        return ProjectResponseModel(
            id=self.id,
            name=self.name,
            description=self.description,
            created=self.created,
            updated=self.updated,
        )
