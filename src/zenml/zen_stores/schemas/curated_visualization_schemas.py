# Copyright (c) ZenML GmbH 2025. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing
# permissions and limitations under the License.
"""SQLModel implementation of curated visualization tables."""

from typing import TYPE_CHECKING, Any, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship

from zenml.enums import CuratedVisualizationSize, VisualizationResourceTypes
from zenml.models.v2.core.curated_visualization import (
    CuratedVisualizationRequest,
    CuratedVisualizationResponse,
    CuratedVisualizationResponseBody,
    CuratedVisualizationResponseMetadata,
    CuratedVisualizationResponseResources,
    CuratedVisualizationUpdate,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import (
    build_foreign_key_field,
)
from zenml.zen_stores.schemas.utils import jl_arg

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.artifact_visualization_schemas import (
        ArtifactVisualizationSchema,
    )


class CuratedVisualizationSchema(BaseSchema, table=True):
    """SQL Model for curated visualizations."""

    __tablename__ = "curated_visualization"
    __table_args__ = (
        UniqueConstraint(
            "artifact_visualization_id",
            "resource_id",
            "resource_type",
            name="unique_curated_visualization_resource_link",
        ),
    )

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    artifact_visualization_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="artifact_visualization",
        source_column="artifact_visualization_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        custom_constraint_name="fk_curated_visualization_artifact_visualization_id",
    )

    display_name: Optional[str] = Field(default=None)
    display_order: Optional[int] = Field(default=None)
    layout_size: str = Field(
        default=CuratedVisualizationSize.FULL_WIDTH.value,
        nullable=False,
    )
    resource_id: UUID = Field(nullable=False)
    resource_type: str = Field(nullable=False)

    artifact_visualization: "ArtifactVisualizationSchema" = Relationship(
        back_populates="curated_visualizations"
    )

    @classmethod
    def get_query_options(
        cls,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> Sequence[ExecutableOption]:
        """Get the query options for the schema.

        Args:
            include_metadata: Whether metadata will be included when converting
                the schema to a model.
            include_resources: Whether resources will be included when
                converting the schema to a model.
            **kwargs: Keyword arguments to allow schema specific logic

        Returns:
            A list of query options.
        """
        options: List[ExecutableOption] = []

        if include_resources:
            options.append(selectinload(jl_arg(cls.artifact_visualization)))

        return options

    @classmethod
    def from_request(
        cls, request: CuratedVisualizationRequest
    ) -> "CuratedVisualizationSchema":
        """Convert a request into a schema instance.

        Args:
            request: The request to convert.

        Returns:
            The created schema.
        """
        return cls(
            project_id=request.project,
            artifact_visualization_id=request.artifact_visualization_id,
            display_name=request.display_name,
            display_order=request.display_order,
            layout_size=request.layout_size.value,
            resource_id=request.resource_id,
            resource_type=request.resource_type.value,
        )

    def update(
        self,
        update: CuratedVisualizationUpdate,
    ) -> "CuratedVisualizationSchema":
        """Update a schema instance from an update model.

        Args:
            update: The update definition.

        Returns:
            The updated schema.
        """
        changes = update.model_dump(exclude_unset=True)
        layout_size_update = changes.pop("layout_size", None)
        if layout_size_update is not None:
            self.layout_size = layout_size_update.value

        for field, value in changes.items():
            if hasattr(self, field):
                setattr(self, field, value)

        from zenml.utils.time_utils import utc_now

        self.updated = utc_now()
        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> CuratedVisualizationResponse:
        """Convert schema into response model.

        Args:
            include_metadata: Whether to include metadata in the response.
            include_resources: Whether to include resources in the response.
            **kwargs: Additional keyword arguments.

        Returns:
            The created response model.
        """
        try:
            layout_size_enum = CuratedVisualizationSize(self.layout_size)
        except ValueError:
            layout_size_enum = CuratedVisualizationSize.FULL_WIDTH

        try:
            resource_type_enum = VisualizationResourceTypes(self.resource_type)
        except ValueError:
            resource_type_enum = VisualizationResourceTypes.PROJECT

        artifact_version_id = self.artifact_visualization.artifact_version_id

        body = CuratedVisualizationResponseBody(
            project_id=self.project_id,
            created=self.created,
            updated=self.updated,
            artifact_visualization_id=self.artifact_visualization_id,
            artifact_version_id=artifact_version_id,
            display_name=self.display_name,
            display_order=self.display_order,
            layout_size=layout_size_enum,
            resource_id=self.resource_id,
            resource_type=resource_type_enum,
        )

        metadata = None
        if include_metadata:
            metadata = CuratedVisualizationResponseMetadata()

        resources = None
        if include_resources:
            artifact_visualization = self.artifact_visualization.to_model(
                include_metadata=False,
                include_resources=False,
            )
            resources = CuratedVisualizationResponseResources(
                artifact_visualization=artifact_visualization,
            )

        return CuratedVisualizationResponse(
            id=self.id,
            body=body,
            metadata=metadata,
            resources=resources,
        )
