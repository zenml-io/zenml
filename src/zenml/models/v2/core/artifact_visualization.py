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

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import Field

from zenml.enums import VisualizationType
from zenml.models.v2.base.base import (
    BaseDatedResponseBody,
    BaseIdentifiedResponse,
    BaseRequest,
    BaseResponseMetadata,
    BaseResponseResources,
)

if TYPE_CHECKING:
    from zenml.models.v2.core.artifact_version import ArtifactVersionResponse

# ------------------ Request Model ------------------


class ArtifactVisualizationRequest(BaseRequest):
    """Request model for artifact visualization."""

    type: VisualizationType
    uri: str


# ------------------ Update Model ------------------

# There is no update model for artifact visualizations.

# ------------------ Response Model ------------------


class ArtifactVisualizationResponseBody(BaseDatedResponseBody):
    """Response body for artifact visualizations."""

    type: VisualizationType
    uri: str


class ArtifactVisualizationResponseMetadata(BaseResponseMetadata):
    """Response metadata model for artifact visualizations."""

    artifact_version_id: UUID


class ArtifactVisualizationResponseResources(BaseResponseResources):
    """Class for all resource models associated with the artifact visualization."""

    artifact_version: Optional["ArtifactVersionResponse"] = Field(
        default=None,
        title="The artifact version.",
        description="Artifact version that owns this visualization, when included.",
    )


class ArtifactVisualizationResponse(
    BaseIdentifiedResponse[
        ArtifactVisualizationResponseBody,
        ArtifactVisualizationResponseMetadata,
        ArtifactVisualizationResponseResources,
    ]
):
    """Response model for artifact visualizations."""

    def get_hydrated_version(self) -> "ArtifactVisualizationResponse":
        """Get the hydrated version of this artifact visualization.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_artifact_visualization(self.id)

    # Body and metadata properties
    @property
    def type(self) -> VisualizationType:
        """The `type` property.

        Returns:
            the value of the property.
        """
        return self.get_body().type

    @property
    def uri(self) -> str:
        """The `uri` property.

        Returns:
            the value of the property.
        """
        return self.get_body().uri

    @property
    def artifact_version_id(self) -> UUID:
        """The `artifact_version_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().artifact_version_id

    @property
    def artifact_version(self) -> Optional["ArtifactVersionResponse"]:
        """The artifact version resource, if the response was hydrated with it.

        Returns:
            The artifact version resource, if available.
        """
        return self.get_resources().artifact_version


# ------------------ Filter Model ------------------

# There is no filter model for artifact visualizations.
