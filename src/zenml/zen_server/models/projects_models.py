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


class CreateProjectModel(BaseModel):
    """Model used for all update operations on stacks."""

    name: str = Field(title="The unique name of the stack.")
    description: Optional[str] = Field(
        default=None, title="The description of the project.", max_length=300
    )

    def to_model(self) -> "ProjectModel":
        """Applies user defined changes to this model."""
        return ProjectModel.parse_obj(self)


class UpdateProjectModel(BaseModel):
    """Model used for all update operations on stacks."""

    name: Optional[str] = Field(
        default=None, title="The unique name of the stack."
    )
    description: Optional[str] = Field(
        default=None, title="The description of the project.", max_length=300
    )

    def apply_to_model(self, project: "ProjectModel") -> "ProjectModel":
        """Applies user defined changes to this model."""
        for key, value in self.dict().items():
            if value is not None:
                setattr(project, key, value)

        return project
