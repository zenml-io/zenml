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
"""Models representing Pipeline Deployments."""

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import DeploymentStatus
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
    TaggableFilter,
)
from zenml.utils.tag_utils import Tag

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.models.v2.core.component import ComponentResponse
    from zenml.models.v2.core.curated_visualization import (
        CuratedVisualizationResponse,
    )
    from zenml.models.v2.core.pipeline import PipelineResponse
    from zenml.models.v2.core.pipeline_snapshot import (
        PipelineSnapshotResponse,
    )
    from zenml.models.v2.core.stack import StackResponse
    from zenml.models.v2.core.tag import TagResponse
    from zenml.zen_stores.schemas.base_schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)
    AnyQuery = TypeVar("AnyQuery", bound=Any)


class DeploymentOperationalState(BaseModel):
    """Operational state of a deployment."""

    status: DeploymentStatus = Field(default=DeploymentStatus.UNKNOWN)
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ------------------ Request Model ------------------


class DeploymentRequest(ProjectScopedRequest):
    """Request model for deployments."""

    name: str = Field(
        title="The name of the deployment.",
        description="A unique name for the deployment within the project.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    snapshot_id: UUID = Field(
        title="The pipeline snapshot ID.",
        description="The ID of the pipeline snapshot associated with the "
        "deployment.",
    )
    deployer_id: UUID = Field(
        title="The deployer ID.",
        description="The ID of the deployer component managing this deployment.",
    )
    auth_key: Optional[str] = Field(
        default=None,
        title="The auth key of the deployment.",
        description="The auth key of the deployment.",
    )
    tags: Optional[List[Union[str, Tag]]] = Field(
        default=None,
        title="Tags of the deployment.",
    )


# ------------------ Update Model ------------------


class DeploymentUpdate(BaseUpdate):
    """Update model for deployments."""

    name: Optional[str] = Field(
        default=None,
        title="The new name of the deployment.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    snapshot_id: Optional[UUID] = Field(
        default=None,
        title="New pipeline snapshot ID.",
    )
    url: Optional[str] = Field(
        default=None,
        title="The new URL of the deployment.",
    )
    status: Optional[DeploymentStatus] = Field(
        default=None,
        title="The new status of the deployment.",
    )
    deployment_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The new metadata of the deployment.",
    )
    auth_key: Optional[str] = Field(
        default=None,
        title="The new auth key of the deployment.",
    )
    add_tags: Optional[List[str]] = Field(
        default=None, title="New tags to add to the deployment."
    )
    remove_tags: Optional[List[str]] = Field(
        default=None, title="Tags to remove from the deployment."
    )

    @classmethod
    def from_operational_state(
        cls, operational_state: DeploymentOperationalState
    ) -> "DeploymentUpdate":
        """Create an update from an operational state.

        Args:
            operational_state: The operational state to create an update from.

        Returns:
            The update.
        """
        return cls(
            status=operational_state.status,
            url=operational_state.url,
            deployment_metadata=operational_state.metadata,
        )


# ------------------ Response Model ------------------


class DeploymentResponseBody(ProjectScopedResponseBody):
    """Response body for deployments."""

    url: Optional[str] = Field(
        default=None,
        title="The URL of the deployment.",
        description="The HTTP URL where the deployment can be accessed.",
    )
    status: Optional[DeploymentStatus] = Field(
        default=None,
        title="The status of the deployment.",
        description="Current operational status of the deployment.",
    )


class DeploymentResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for deployments."""

    deployment_metadata: Dict[str, Any] = Field(
        title="The metadata of the deployment.",
    )
    auth_key: Optional[str] = Field(
        default=None,
        title="The auth key of the deployment.",
        description="The auth key of the deployment.",
    )


class DeploymentResponseResources(ProjectScopedResponseResources):
    """Response resources for deployments."""

    snapshot: Optional["PipelineSnapshotResponse"] = Field(
        default=None,
        title="The pipeline snapshot.",
        description="The pipeline snapshot being deployed.",
    )
    deployer: Optional["ComponentResponse"] = Field(
        default=None,
        title="The deployer.",
        description="The deployer component managing this deployment.",
    )
    pipeline: Optional["PipelineResponse"] = Field(
        default=None,
        title="The pipeline.",
        description="The pipeline being deployed.",
    )
    tags: List["TagResponse"] = Field(
        title="Tags associated with the deployment.",
    )
    visualizations: List["CuratedVisualizationResponse"] = Field(
        default_factory=list,
        title="Curated deployment visualizations.",
    )
    stack: Optional["StackResponse"] = Field(
        default=None,
        title="The stack that was deployed.",
        description="The stack that was deployed.",
    )


class DeploymentResponse(
    ProjectScopedResponse[
        DeploymentResponseBody,
        DeploymentResponseMetadata,
        DeploymentResponseResources,
    ]
):
    """Response model for deployments."""

    name: str = Field(
        title="The name of the deployment.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "DeploymentResponse":
        """Get the hydrated version of this deployment.

        Returns:
            an instance of the same entity with the metadata and resources fields
            attached.
        """
        from zenml.client import Client

        client = Client()
        return client.get_deployment(self.id)

    # Helper properties
    @property
    def url(self) -> Optional[str]:
        """The URL of the deployment.

        Returns:
            The URL of the deployment.
        """
        return self.get_body().url

    @property
    def status(self) -> Optional[DeploymentStatus]:
        """The status of the deployment.

        Returns:
            The status of the deployment.
        """
        return self.get_body().status

    @property
    def deployment_metadata(self) -> Dict[str, Any]:
        """The metadata of the deployment.

        Returns:
            The metadata of the deployment.
        """
        return self.get_metadata().deployment_metadata

    @property
    def auth_key(self) -> Optional[str]:
        """The auth key of the deployment.

        Returns:
            The auth key of the deployment.
        """
        return self.get_metadata().auth_key

    @property
    def snapshot(self) -> Optional["PipelineSnapshotResponse"]:
        """The pipeline snapshot.

        Returns:
            The pipeline snapshot.
        """
        return self.get_resources().snapshot

    @property
    def deployer(self) -> Optional["ComponentResponse"]:
        """The deployer.

        Returns:
            The deployer.
        """
        return self.get_resources().deployer

    @property
    def pipeline(self) -> Optional["PipelineResponse"]:
        """The pipeline.

        Returns:
            The pipeline.
        """
        return self.get_resources().pipeline

    def tags(self) -> List["TagResponse"]:
        """The tags of the deployment.

        Returns:
            The tags of the deployment.
        """
        return self.get_resources().tags

    @property
    def visualizations(self) -> List["CuratedVisualizationResponse"]:
        """The visualizations of the deployment.

        Returns:
            The visualizations of the deployment.
        """
        return self.get_resources().visualizations

    @property
    def stack(self) -> Optional["StackResponse"]:
        """The stack.

        Returns:
            The stack.
        """
        return self.get_resources().stack

    @property
    def snapshot_id(self) -> Optional[UUID]:
        """The pipeline snapshot ID.

        Returns:
            The pipeline snapshot ID.
        """
        snapshot = self.get_resources().snapshot
        if snapshot:
            return snapshot.id
        return None

    @property
    def deployer_id(self) -> Optional[UUID]:
        """The deployer ID.

        Returns:
            The deployer ID.
        """
        deployer = self.get_resources().deployer
        if deployer:
            return deployer.id
        return None


# ------------------ Filter Model ------------------


class DeploymentFilter(ProjectScopedFilter, TaggableFilter):
    """Model to enable advanced filtering of deployments."""

    CUSTOM_SORTING_OPTIONS: ClassVar[List[str]] = [
        *ProjectScopedFilter.CUSTOM_SORTING_OPTIONS,
        *TaggableFilter.CUSTOM_SORTING_OPTIONS,
        "snapshot",
        "pipeline",
    ]
    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ProjectScopedFilter.FILTER_EXCLUDE_FIELDS,
        *TaggableFilter.FILTER_EXCLUDE_FIELDS,
        "pipeline",
    ]
    CLI_EXCLUDE_FIELDS = [
        *ProjectScopedFilter.CLI_EXCLUDE_FIELDS,
        *TaggableFilter.CLI_EXCLUDE_FIELDS,
    ]

    name: Optional[str] = Field(
        default=None,
        description="Name of the deployment.",
    )
    url: Optional[str] = Field(
        default=None,
        description="URL of the deployment.",
    )
    status: Optional[str] = Field(
        default=None,
        description="Status of the deployment.",
    )
    pipeline: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Pipeline associated with the deployment.",
        union_mode="left_to_right",
    )
    snapshot_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Pipeline snapshot ID associated with the deployment.",
        union_mode="left_to_right",
    )
    deployer_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Deployer ID managing the deployment.",
        union_mode="left_to_right",
    )

    def get_custom_filters(
        self, table: Type["AnySchema"]
    ) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        Args:
            table: The query table.

        Returns:
            A list of custom filters.
        """
        from sqlmodel import and_

        from zenml.zen_stores.schemas import (
            DeploymentSchema,
            PipelineSchema,
            PipelineSnapshotSchema,
        )

        custom_filters = super().get_custom_filters(table)

        if self.pipeline:
            pipeline_filter = and_(
                DeploymentSchema.snapshot_id == PipelineSnapshotSchema.id,
                PipelineSnapshotSchema.pipeline_id == PipelineSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.pipeline, table=PipelineSchema
                ),
            )
            custom_filters.append(pipeline_filter)

        return custom_filters

    def apply_sorting(
        self,
        query: "AnyQuery",
        table: Type["AnySchema"],
    ) -> "AnyQuery":
        """Apply sorting to the query.

        Args:
            query: The query to which to apply the sorting.
            table: The query table.

        Returns:
            The query with sorting applied.
        """
        from sqlmodel import asc, desc

        from zenml.enums import SorterOps
        from zenml.zen_stores.schemas import (
            DeploymentSchema,
            PipelineSchema,
            PipelineSnapshotSchema,
        )

        sort_by, operand = self.sorting_params

        if sort_by == "pipeline":
            query = query.outerjoin(
                PipelineSnapshotSchema,
                DeploymentSchema.snapshot_id == PipelineSnapshotSchema.id,
            ).outerjoin(
                PipelineSchema,
                PipelineSnapshotSchema.pipeline_id == PipelineSchema.id,
            )
            column: Any = PipelineSchema.name
        elif sort_by == "snapshot":
            query = query.outerjoin(
                PipelineSnapshotSchema,
                DeploymentSchema.snapshot_id == PipelineSnapshotSchema.id,
            )
            column = PipelineSnapshotSchema.name
        else:
            return super().apply_sorting(query=query, table=table)

        query = query.add_columns(column)

        if operand == SorterOps.ASCENDING:
            query = query.order_by(asc(column))
        else:
            query = query.order_by(desc(column))

        return query
