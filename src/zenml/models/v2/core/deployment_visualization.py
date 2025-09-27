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
"""Models representing deployment visualizations."""

from typing import (
    TYPE_CHECKING,
    ClassVar,
    List,
    Optional,
    Type,
    TypeVar,
)
from uuid import UUID

from pydantic import Field

from zenml.constants import STR_FIELD_MAX_LENGTH
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

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.models.v2.core.artifact_version import ArtifactVersionResponse
    from zenml.models.v2.core.deployment import DeploymentResponse
    from zenml.zen_stores.schemas.base_schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)


# ------------------ Request Model ------------------


class DeploymentVisualizationRequest(ProjectScopedRequest):
    """Request model for deployment visualizations."""

    deployment_id: UUID = Field(
        title="The deployment ID.",
        description="The ID of the deployment associated with the visualization.",
    )
    artifact_version_id: UUID = Field(
        title="The artifact version ID.",
        description="The ID of the artifact version associated with the visualization.",
    )
    visualization_index: int = Field(
        ge=0,
        title="The visualization index.",
        description="The index of the visualization within the artifact version.",
    )
    display_name: Optional[str] = Field(
        default=None,
        title="The display name of the visualization.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    display_order: Optional[int] = Field(
        default=None,
        title="The display order of the visualization.",
    )


# ------------------ Update Model ------------------


class DeploymentVisualizationUpdate(BaseUpdate):
    """Update model for deployment visualizations."""

    display_name: Optional[str] = Field(
        default=None,
        title="The new display name of the visualization.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    display_order: Optional[int] = Field(
        default=None,
        title="The new display order of the visualization.",
    )


# ------------------ Response Model ------------------


class DeploymentVisualizationResponseBody(ProjectScopedResponseBody):
    """Response body for deployment visualizations."""

    deployment_id: UUID = Field(
        title="The deployment ID.",
        description="The ID of the deployment associated with the visualization.",
    )
    artifact_version_id: UUID = Field(
        title="The artifact version ID.",
        description="The ID of the artifact version associated with the visualization.",
    )
    visualization_index: int = Field(
        title="The visualization index.",
        description="The index of the visualization within the artifact version.",
    )
    display_name: Optional[str] = Field(
        default=None,
        title="The display name of the visualization.",
    )
    display_order: Optional[int] = Field(
        default=None,
        title="The display order of the visualization.",
    )


class DeploymentVisualizationResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for deployment visualizations."""


class DeploymentVisualizationResponseResources(ProjectScopedResponseResources):
    """Response resources for deployment visualizations."""

    deployment: Optional["DeploymentResponse"] = Field(
        default=None,
        title="The deployment.",
        description="The deployment associated with the visualization.",
    )
    artifact_version: Optional["ArtifactVersionResponse"] = Field(
        default=None,
        title="The artifact version.",
        description="The artifact version associated with the visualization.",
    )


class DeploymentVisualizationResponse(
    ProjectScopedResponse[
        DeploymentVisualizationResponseBody,
        DeploymentVisualizationResponseMetadata,
        DeploymentVisualizationResponseResources,
    ]
):
    """Response model for deployment visualizations."""

    def get_hydrated_version(self) -> "DeploymentVisualizationResponse":
        """Get the hydrated version of this deployment visualization.

        Returns:
            an instance of the same entity with the metadata and resources fields
            attached.
        """
        from zenml.client import Client

        client = Client()
        return client.zen_store.get_deployment_visualization(self.id)

    # Helper properties
    @property
    def deployment_id(self) -> UUID:
        """The deployment ID.

        Returns:
            The deployment ID.
        """
        return self.get_body().deployment_id

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
    def deployment(self) -> Optional["DeploymentResponse"]:
        """The deployment.

        Returns:
            The deployment.
        """
        return self.get_resources().deployment

    @property
    def artifact_version(self) -> Optional["ArtifactVersionResponse"]:
        """The artifact version.

        Returns:
            The artifact version.
        """
        return self.get_resources().artifact_version


# ------------------ Filter Model ------------------


class DeploymentVisualizationFilter(ProjectScopedFilter):
    """Model to enable advanced filtering of deployment visualizations."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ProjectScopedFilter.FILTER_EXCLUDE_FIELDS,
        "deployment",
        "artifact_version",
    ]
    CUSTOM_SORTING_OPTIONS: ClassVar[List[str]] = [
        *ProjectScopedFilter.CUSTOM_SORTING_OPTIONS,
        "display_order",
        "created",
        "updated",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ProjectScopedFilter.CLI_EXCLUDE_FIELDS,
    ]

    # Set default sort_by to display_order
    sort_by: str = Field(
        default="display_order",
        description="Which column to sort by.",
    )

    deployment: Optional[UUID] = Field(
        default=None,
        description="ID of the deployment associated with the visualization.",
    )
    artifact_version: Optional[UUID] = Field(
        default=None,
        description="ID of the artifact version associated with the visualization.",
    )
    visualization_index: Optional[int] = Field(
        default=None,
        description="Index of the visualization within the artifact version.",
    )
    display_order: Optional[int] = Field(
        default=None,
        description="Display order of the visualization.",
    )

    def apply_sorting(
        self,
        query: AnyQuery,
        table: Type["AnySchema"],
    ) -> AnyQuery:
        """Apply sorting to the deployment visualization query.

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
            column = getattr(table, sort_by)
            if operand == SorterOps.DESCENDING:
                return query.order_by(desc(column).nullslast(), asc(table.id))
            return query.order_by(asc(column).nullsfirst(), asc(table.id))
        elif sort_by in {"created", "updated"}:
            column = getattr(table, sort_by)
            if operand == SorterOps.DESCENDING:
                return query.order_by(desc(column), asc(table.id))
            return query.order_by(asc(column), asc(table.id))

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

        if self.deployment:
            deployment_filter = (
                getattr(table, "deployment_id") == self.deployment
            )
            custom_filters.append(deployment_filter)

        if self.artifact_version:
            artifact_version_filter = (
                getattr(table, "artifact_version_id") == self.artifact_version
            )
            custom_filters.append(artifact_version_filter)

        return custom_filters
