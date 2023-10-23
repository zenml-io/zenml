#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Models representing artifact visualizations."""

from typing import Optional
from uuid import UUID

from zenml.enums import VisualizationType
from zenml.models.v2.base.base import (
    BaseRequest,
    BaseResponse,
    BaseResponseBody,
    BaseResponseMetadata,
)
from zenml.models.v2.base.utils import hydrated_property

# ------------------ Request Model ------------------


class ArtifactVisualizationRequest(BaseRequest):
    """Request model for artifact visualization."""

    type: VisualizationType
    uri: str


# ------------------ Update Model ------------------

# There is no update model for artifact visualizations.

# ------------------ Response Model ------------------


class ArtifactVisualizationResponseBody(BaseResponseBody):
    """Response body for artifact visualizations."""

    type: VisualizationType
    uri: str


class ArtifactVisualizationResponseMetadata(BaseResponseMetadata):
    """Response metadata model for artifact visualizations."""

    artifact_id: UUID


class ArtifactVisualizationResponse(BaseResponse):
    """Response model for artifact visualizations."""

    # Body and metadata pair
    body: "ArtifactVisualizationResponseBody"
    metadata: Optional["ArtifactVisualizationResponseMetadata"]

    def get_hydrated_version(self) -> "ArtifactVisualizationResponse":
        """Get the hydrated version of this artifact visualization."""
        from zenml.client import Client

        return Client().zen_store.get_artifact_visualization(self.id)

    # Body and metadata properties
    @property
    def type(self):
        """The `type` property."""
        return self.body.type

    @property
    def uri(self):
        """The `uri` property."""
        return self.body.uri

    @hydrated_property
    def artifact_id(self):
        """The `artifact_id` property"""
        return self.metadata.artifact_id


# ------------------ Filter Model ------------------

# There is no filter model for artifact visualizations.
