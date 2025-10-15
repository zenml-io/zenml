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

from pydantic import Field

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
    from zenml.models.v2.core.artifact_version import ArtifactVersionResponse


# ------------------ Request Model ------------------


class CuratedVisualizationRequest(ProjectScopedRequest):
    """Request model for curated visualizations.

    Each curated visualization is linked to exactly one resource of the following
    types:
    - **Deployments**: Surface visualizations on deployment dashboards
    - **Models**: Highlight evaluation dashboards and monitoring views next to
      registered models
    - **Pipelines**: Associate visualizations with pipeline definitions
    - **Pipeline Runs**: Attach visualizations to specific execution runs
    - **Pipeline Snapshots**: Link visualizations to snapshot configurations
    - **Projects**: Provide high-level project dashboards and KPI overviews

    To attach a visualization to multiple resources, create separate curated
    visualization entries for each resource.
    """

    artifact_version_id: UUID = Field(
        title="The artifact version ID.",
        description="Identifier of the artifact version providing the visualization.",
    )
    visualization_index: int = Field(
        ge=0,
        title="The visualization index.",
        description="Index of the visualization within the artifact version payload.",
    )
    display_name: Optional[str] = Field(
        default=None,
        title="The display name of the visualization.",
    )
    display_order: Optional[int] = Field(
        default=None,
        title="The display order of the visualization.",
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
    display_order: Optional[int] = Field(
        default=None,
        title="The new display order of the visualization.",
    )
    layout_size: Optional[CuratedVisualizationSize] = Field(
        default=None,
        title="The updated layout size of the visualization.",
    )


# ------------------ Response Model ------------------


class CuratedVisualizationResponseBody(ProjectScopedResponseBody):
    """Response body for curated visualizations."""

    artifact_version_id: UUID = Field(
        title="The artifact version ID.",
        description="Identifier of the artifact version providing the visualization.",
    )
    visualization_index: int = Field(
        title="The visualization index.",
        description="Index of the visualization within the artifact version payload.",
    )
    display_name: Optional[str] = Field(
        default=None,
        title="The display name of the visualization.",
    )
    display_order: Optional[int] = Field(
        default=None,
        title="The display order of the visualization.",
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

    artifact_version: "ArtifactVersionResponse" = Field(
        title="The artifact version.",
        description="Artifact version from which the visualization originates.",
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
    def artifact_version_id(self) -> UUID:
        """The artifact version ID.

        Returns:
            The artifact version ID.
        """
        return self.get_body().artifact_version_id

    @property
    def visualization_index(self) -> int:
        """The visualization index.

        Returns:
            The visualization index.
        """
        return self.get_body().visualization_index

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
    def artifact_version(self) -> "ArtifactVersionResponse":
        """The artifact version resource.

        Returns:
            The artifact version resource if included.
        """
        return self.get_resources().artifact_version

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
