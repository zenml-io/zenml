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
"""Project Models for the API endpoint definitions."""
from typing import Optional

from pydantic import BaseModel, Field

from zenml.models import ProjectModel
from zenml.models.constants import (
    MODEL_DESCRIPTIVE_FIELD_MAX_LENGTH,
    MODEL_NAME_FIELD_MAX_LENGTH,
)


class CreateProjectRequest(BaseModel):
    """Project model for create requests."""

    name: str = Field(
        title="The unique name of the project.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    description: Optional[str] = Field(
        default=None,
        title="The description of the project.",
        max_length=MODEL_DESCRIPTIVE_FIELD_MAX_LENGTH,
    )

    def to_model(self) -> "ProjectModel":
        """Create a `ProjectModel` from this object.

        Returns:
            The created `ProjectModel`.
        """
        return ProjectModel.parse_obj(self)

    @classmethod
    def from_model(cls, project: ProjectModel) -> "CreateProjectRequest":
        """Convert from a project model."""
        return cls(**project.dict())


class UpdateProjectRequest(BaseModel):
    """Project model for update requests."""

    name: Optional[str] = Field(
        default=None,
        title="The new name of the project.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    description: Optional[str] = Field(
        default=None,
        title="The new description of the project.",
        max_length=MODEL_DESCRIPTIVE_FIELD_MAX_LENGTH,
    )

    def apply_to_model(self, project: "ProjectModel") -> "ProjectModel":
        """Applies user defined changes to the given `ProjectModel`.

        Args:
            project: The `ProjectModel` to apply the changes to.

        Returns:
            The updated `ProjectModel`.
        """
        for key, value in self.dict(exclude_none=True).items():
            setattr(project, key, value)

        return project

    @classmethod
    def from_model(cls, project: ProjectModel) -> "UpdateProjectRequest":
        """Convert from a project model."""
        return cls(**project.dict())
