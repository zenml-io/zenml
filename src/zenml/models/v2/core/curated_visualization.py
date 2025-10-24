#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Models representing curated visualizations."""

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import Field, NonNegativeInt

from zenml.enums import CuratedVisualizationSize, VisualizationResourceTypes
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
)

if TYPE_CHECKING:
    from zenml.models.v2.core.artifact_visualization import (
        ArtifactVisualizationResponse,
    )


# ------------------ Request Model ------------------


class CuratedVisualizationRequest(ProjectScopedRequest):
    """Request model for curated visualizations.

    Each curated visualization links a pre-rendered artifact visualization
    to a single ZenML resource to surface it in the appropriate UI context.
    Supported resources include:
    - **Deployments**
    - **Models**
    - **Pipelines**
    - **Pipeline Runs**
    - **Pipeline Snapshots**
    - **Projects**
    """

    artifact_visualization_id: UUID = Field(
        title="The artifact visualization ID.",
        description=(
            "Identifier of the artifact visualization that should be surfaced "
            "for the target resource."
        ),
    )
    display_name: Optional[str] = Field(
        default=None,
        title="The display name of the visualization.",
    )
    display_order: Optional[NonNegativeInt] = Field(
        default=None,
        title="The display order of the visualization.",
        description=(
            "Optional ordering hint that must be unique for the combination "
            "of resource type and resource ID."
        ),
    )
    layout_size: CuratedVisualizationSize = Field(
        default=CuratedVisualizationSize.FULL_WIDTH,
        title="The layout size of the visualization.",
        description=(
            "Controls how much horizontal space the visualization occupies "
            "on the dashboard."
        ),
    )
    resource_id: UUID = Field(
        title="The linked resource ID.",
        description=(
            "Identifier of the resource (deployment, model, pipeline, pipeline "
            "run, pipeline snapshot, or project) that should surface this "
            "visualization."
        ),
    )
    resource_type: VisualizationResourceTypes = Field(
        title="The linked resource type.",
        description="Type of the resource associated with this visualization.",
    )


# ------------------ Update Model ------------------


class CuratedVisualizationUpdate(BaseUpdate):
    """Update model for curated visualizations."""

    display_name: Optional[str] = Field(
        default=None,
        title="The new display name of the visualization.",
    )
    display_order: Optional[NonNegativeInt] = Field(
        default=None,
        title="The new display order of the visualization.",
        description=(
            "Optional ordering hint. When provided, it must remain unique for "
            "the combination of resource type and resource ID."
        ),
    )
    layout_size: Optional[CuratedVisualizationSize] = Field(
        default=None,
        title="The updated layout size of the visualization.",
    )


# ------------------ Response Model ------------------


class CuratedVisualizationResponseBody(ProjectScopedResponseBody):
    """Response body for curated visualizations."""

    artifact_visualization_id: UUID = Field(
        title="The artifact visualization ID.",
        description=(
            "Identifier of the artifact visualization that is curated for this resource."
        ),
    )
    artifact_version_id: UUID = Field(
        title="The artifact version ID.",
        description=(
            "Identifier of the artifact version that owns the curated visualization. "
            "Provided for read-only context when available."
        ),
    )
    display_name: Optional[str] = Field(
        default=None,
        title="The display name of the visualization.",
    )
    display_order: Optional[NonNegativeInt] = Field(
        default=None,
        title="The display order of the visualization.",
        description=(
            "Optional ordering hint that is unique per combination of "
            "resource type and resource ID."
        ),
    )
    layout_size: CuratedVisualizationSize = Field(
        default=CuratedVisualizationSize.FULL_WIDTH,
        title="The layout size of the visualization.",
    )
    resource_id: UUID = Field(
        title="The linked resource ID.",
        description="Identifier of the resource associated with this visualization.",
    )
    resource_type: VisualizationResourceTypes = Field(
        title="The linked resource type.",
        description="Type of the resource associated with this visualization.",
    )


class CuratedVisualizationResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for curated visualizations."""


class CuratedVisualizationResponseResources(ProjectScopedResponseResources):
    """Response resources included for curated visualizations."""

    artifact_visualization: "ArtifactVisualizationResponse" = Field(
        title="The artifact visualization.",
        description=(
            "Artifact visualization that is surfaced through this curated visualization."
        ),
    )


class CuratedVisualizationResponse(
    ProjectScopedResponse[
        CuratedVisualizationResponseBody,
        CuratedVisualizationResponseMetadata,
        CuratedVisualizationResponseResources,
    ]
):
    """Response model for curated visualizations."""

    def get_hydrated_version(self) -> "CuratedVisualizationResponse":
        """Get the hydrated version of this curated visualization.

        Returns:
            A hydrated instance of the same entity.
        """
        from zenml.client import Client

        client = Client()
        return client.zen_store.get_curated_visualization(self.id)

    # Helper properties
    @property
    def artifact_visualization_id(self) -> UUID:
        """The artifact visualization ID.

        Returns:
            The artifact visualization ID.
        """
        return self.get_body().artifact_visualization_id

    @property
    def artifact_version_id(self) -> UUID:
        """The artifact version ID.

        Returns:
            The artifact version ID if available.
        """
        return self.get_body().artifact_version_id

    @property
    def display_name(self) -> Optional[str]:
        """The display name of the visualization.

        Returns:
            The display name of the visualization.
        """
        return self.get_body().display_name

    @property
    def display_order(self) -> Optional[int]:
        """The display order of the visualization.

        Returns:
            The display order of the visualization.
        """
        return self.get_body().display_order

    @property
    def layout_size(self) -> CuratedVisualizationSize:
        """The layout size of the visualization.

        Returns:
            The layout size of the visualization.
        """
        return self.get_body().layout_size

    @property
    def artifact_visualization(self) -> "ArtifactVisualizationResponse":
        """The curated artifact visualization resource.

        Returns:
            The artifact visualization resource.
        """
        return self.get_resources().artifact_visualization

    @property
    def resource_id(self) -> UUID:
        """The identifier of the linked resource.

        Returns:
            The resource identifier associated with this visualization.
        """
        return self.get_body().resource_id

    @property
    def resource_type(self) -> VisualizationResourceTypes:
        """The type of the linked resource.

        Returns:
            The resource type associated with this visualization.
        """
        return self.get_body().resource_type
