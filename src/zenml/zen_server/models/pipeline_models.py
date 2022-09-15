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
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.models import PipelineModel
from zenml.models.constants import MODEL_NAME_FIELD_MAX_LENGTH


class CreatePipelineRequest(BaseModel):
    """Pipeline model for create requests."""

    name: str = Field(
        title="The name of the pipeline.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    docstring: Optional[str]
    configuration: Dict[str, str]

    def to_model(self, project: UUID, user: UUID) -> "PipelineModel":
        """Create a `PipelineModel` from this object.

        Args:
            project: Project context of the pipeline.
            user: User context of the pipeline

        Returns:
            The created `PipelineModel`.
        """
        return PipelineModel(project=project, user=user, **self.dict())

    @classmethod
    def from_model(cls, pipeline: PipelineModel) -> "CreatePipelineRequest":
        """Convert from a `PipelineModel`."""
        return cls(**pipeline.dict())


class UpdatePipelineRequest(BaseModel):
    """Pipeline model for update requests."""

    name: Optional[str] = Field(
        title="The name of the pipeline.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    docstring: Optional[str]
    # TODO: [server] have another look at this to figure out if adding a
    #  single k:v pair overwrites the existing k:v pairs
    configuration: Optional[Dict[str, str]]

    def apply_to_model(self, pipeline: "PipelineModel") -> "PipelineModel":
        """Update a `PipelineModel` from this object.

        Args:
            pipeline: The `PipelineModel` to apply the changes to.

        Returns:
            The updated `PipelineModel`.
        """
        for key, value in self.dict(exclude_none=True).items():
            setattr(pipeline, key, value)

        return pipeline

    @classmethod
    def from_model(cls, pipeline: PipelineModel) -> "UpdatePipelineRequest":
        """Convert from a `PipelineModel` model."""
        return cls(**pipeline.dict())
