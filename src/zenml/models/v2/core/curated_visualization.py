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

from typing import (
    TYPE_CHECKING,
    ClassVar,
    List,
    Optional,
    Type,
    TypeVar,
    cast,
)
from uuid import UUID

from pydantic import Field, model_validator

from zenml.enums import VisualizationResourceTypes
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.filter import AnyQuery
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
)
from zenml.models.v2.misc.curated_visualization import (
    CuratedVisualizationResource,
)

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.models.v2.core.artifact_version import ArtifactVersionResponse
    from zenml.zen_stores.schemas.base_schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)


# ------------------ Request Model ------------------


class CuratedVisualizationRequest(ProjectScopedRequest):
    """Request model for curated visualizations.

    Curated visualizations can be attached to any combination of the following
    resource types:
    - **Deployments**: Surface visualizations on deployment dashboards
    - **Models**: Highlight evaluation dashboards and monitoring views next to
      registered models
    - **Pipelines**: Associate visualizations with pipeline definitions
    - **Pipeline Runs**: Attach visualizations to specific execution runs
    - **Pipeline Snapshots**: Link visualizations to snapshot configurations
    - **Projects**: Provide high-level project dashboards and KPI overviews

    A single visualization can be linked to multiple resources of different types,
    enabling reuse across the ML workflow. For example, a model performance
    dashboard could be attached to both a deployment and the pipeline run that
    produced the deployed model.
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
    resources: List[CuratedVisualizationResource] = Field(
        title="Resources associated with this visualization.",
        description=(
            "List of resources (deployments, models, pipelines, pipeline runs, "
            "pipeline snapshots, projects) that should surface this visualization. "
            "Must include at least one resource. Multiple resources of "
            "different types can be specified to reuse visualizations "
            "across the ML workflow."
        ),
    )

    @model_validator(mode="after")
    def validate_resources(self) -> "CuratedVisualizationRequest":
        """Ensure that at least one resource is associated with the visualization.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If no resources are provided.
        """
        if not self.resources:
            raise ValueError(
                "Curated visualizations must be associated with at least one resource."
            )
        return self


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
    resources: List[CuratedVisualizationResource] = Field(
        default_factory=list,
        title="Resources exposing the visualization.",
    )


class CuratedVisualizationResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for curated visualizations."""


class CuratedVisualizationResponseResources(ProjectScopedResponseResources):
    """Response resources for curated visualizations."""

    artifact_version: Optional["ArtifactVersionResponse"] = Field(
        default=None,
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
    def artifact_version(self) -> Optional["ArtifactVersionResponse"]:
        """The artifact version resource.

        Returns:
            The artifact version resource if included.
        """
        return self.get_resources().artifact_version

    def visualization_resources(self) -> List[CuratedVisualizationResource]:
        """Return the resources exposing this visualization.

        Returns:
            List of associated resources.
        """
        return self.get_body().resources


# ------------------ Filter Model ------------------


class CuratedVisualizationFilter(ProjectScopedFilter):
    """Model to enable advanced filtering of curated visualizations."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ProjectScopedFilter.FILTER_EXCLUDE_FIELDS,
        "resource_id",
        "resource_type",
    ]
    CUSTOM_SORTING_OPTIONS: ClassVar[List[str]] = [
        *ProjectScopedFilter.CUSTOM_SORTING_OPTIONS,
        "display_order",
        "created",
        "updated",
        "visualization_index",
    ]

    sort_by: str = Field(
        default="display_order",
        description="Which column to sort by.",
    )

    artifact_version: Optional[UUID] = Field(
        default=None,
        description="ID of the artifact version associated with the visualization.",
    )
    visualization_index: Optional[int] = Field(
        default=None,
        description="Index of the visualization within the artifact version payload.",
    )
    display_order: Optional[int] = Field(
        default=None,
        description="Display order of the visualization.",
    )
    resource_type: Optional[VisualizationResourceTypes] = Field(
        default=None,
        description="Type of the resource exposing the visualization.",
    )
    resource_id: Optional[UUID] = Field(
        default=None,
        description="ID of the resource exposing the visualization.",
    )

    def apply_sorting(
        self,
        query: AnyQuery,
        table: Type["AnySchema"],
    ) -> AnyQuery:
        """Apply sorting to the curated visualization query.

        Args:
            query: The query to which to apply the sorting.
            table: The query table.

        Returns:
            The query with sorting applied.
        """
        from sqlmodel import asc, desc

        from zenml.enums import SorterOps

        sort_by, operand = self.sorting_params

        if sort_by == "display_order":
            column = getattr(table, "display_order")
            if operand == SorterOps.DESCENDING:
                return cast(
                    AnyQuery,
                    query.order_by(desc(column).nulls_last(), asc(table.id)),
                )
            return cast(
                AnyQuery,
                query.order_by(asc(column).nulls_first(), asc(table.id)),
            )

        if sort_by in {"created", "updated", "visualization_index"}:
            column = getattr(table, sort_by)
            if operand == SorterOps.DESCENDING:
                return cast(
                    AnyQuery,
                    query.order_by(desc(column), asc(table.id)),
                )
            return cast(AnyQuery, query.order_by(asc(column), asc(table.id)))

        return super().apply_sorting(query=query, table=table)

    def get_custom_filters(
        self, table: Type["AnySchema"]
    ) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        Args:
            table: The query table.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters(table)

        if self.artifact_version:
            custom_filters.append(
                getattr(table, "artifact_version_id") == self.artifact_version
            )
        if self.visualization_index is not None:
            custom_filters.append(
                getattr(table, "visualization_index")
                == self.visualization_index
            )
        if self.display_order is not None:
            custom_filters.append(
                getattr(table, "display_order") == self.display_order
            )

        # resource-based filtering is handled within the store implementation
        return custom_filters
