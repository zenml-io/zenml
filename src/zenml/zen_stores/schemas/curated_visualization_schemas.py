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

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Sequence
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint, and_
from sqlalchemy.orm import foreign, selectinload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship, SQLModel

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
    build_index,
)
from zenml.zen_stores.schemas.utils import jl_arg

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.artifact_schemas import ArtifactVersionSchema


class CuratedVisualizationResourceSchema(SQLModel, table=True):
    """Link table mapping curated visualizations to resources."""

    __tablename__ = "curated_visualization_resource"
    __table_args__ = (
        UniqueConstraint(
            "visualization_id",
            name="unique_curated_visualization_resource",
        ),
        build_index(__tablename__, ["resource_id", "resource_type"]),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    visualization_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="curated_visualization",
        source_column="visualization_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    resource_id: UUID = Field(nullable=False)
    resource_type: str = Field(nullable=False)

    visualization: "CuratedVisualizationSchema" = Relationship(
        back_populates="resource",
    )


class CuratedVisualizationSchema(BaseSchema, table=True):
    """SQL Model for curated visualizations."""

    __tablename__ = "curated_visualization"
    __table_args__ = (
        build_index(
            __tablename__, ["artifact_version_id", "visualization_index"]
        ),
        build_index(__tablename__, ["display_order"]),
    )

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    artifact_version_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="artifact_version",
        source_column="artifact_version_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )

    visualization_index: int = Field(nullable=False)
    display_name: Optional[str] = Field(default=None)
    display_order: Optional[int] = Field(default=None)
    size: CuratedVisualizationSize = Field(
        default=CuratedVisualizationSize.FULL_WIDTH, nullable=False
    )

    artifact_version: Optional["ArtifactVersionSchema"] = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    resource: Optional[CuratedVisualizationResourceSchema] = Relationship(
        back_populates="visualization",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete"},
        uselist=False,
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
            options.extend(
                [
                    selectinload(jl_arg(cls.artifact_version)),
                    selectinload(jl_arg(cls.resource)),
                ]
            )

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
            artifact_version_id=request.artifact_version_id,
            visualization_index=request.visualization_index,
            display_name=request.display_name,
            display_order=request.display_order,
            size=request.size,
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
        for field, value in update.model_dump(
            exclude_unset=True,
        ).items():
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
        body = CuratedVisualizationResponseBody(
            project_id=self.project_id,
            created=self.created,
            updated=self.updated,
            artifact_version_id=self.artifact_version_id,
            visualization_index=self.visualization_index,
            display_name=self.display_name,
            display_order=self.display_order,
            size=self.size,
        )

        metadata = None
        if include_metadata:
            metadata = CuratedVisualizationResponseMetadata()

        response_resources = None
        if include_resources:
            response_resources = CuratedVisualizationResponseResources(
                artifact_version=self.artifact_version.to_model(
                    include_metadata=include_metadata,
                    include_resources=include_resources,
                )
                if self.artifact_version
                else None,
            )

        return CuratedVisualizationResponse(
            id=self.id,
            body=body,
            metadata=metadata,
            resources=response_resources,
        )


def curated_visualization_relationship_kwargs(
    parent_column_factory: Callable[[], Any],
    resource_type: VisualizationResourceTypes,
) -> Dict[str, Any]:
    """Build sa_relationship_kwargs for curated visualization relationships.

    This helper consolidates the relationship definition for linking parent
    schemas (like DeploymentSchema, ModelSchema) to their curated visualizations
    through the resource link table.

    Args:
        parent_column_factory: A callable that returns the parent column
            (e.g., `lambda: DeploymentSchema.id`). Uses a callable to defer
            evaluation and avoid circular import issues.
        resource_type: The VisualizationResourceTypes enum value indicating
            what type of resource the parent represents.

    Returns:
        A dictionary suitable for passing to Relationship(sa_relationship_kwargs=...).
        The relationship will be read-only (viewonly=True) and eagerly loaded
        via selectin loading.
    """

    def _primaryjoin():
        return and_(
            CuratedVisualizationResourceSchema.resource_type
            == resource_type.value,
            foreign(CuratedVisualizationResourceSchema.resource_id)
            == parent_column_factory(),
        )

    def _secondaryjoin():
        return (
            CuratedVisualizationSchema.id
            == CuratedVisualizationResourceSchema.visualization_id
        )

    return dict(
        secondary="curated_visualization_resource",
        primaryjoin=_primaryjoin,
        secondaryjoin=_secondaryjoin,
        viewonly=True,
        lazy="selectin",
    )
