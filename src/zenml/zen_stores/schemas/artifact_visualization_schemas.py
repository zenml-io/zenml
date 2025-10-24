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
"""SQLModel implementation of artifact visualization table."""

from typing import TYPE_CHECKING, Any, List
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.enums import VisualizationType
from zenml.models import (
    ArtifactVisualizationRequest,
    ArtifactVisualizationResponse,
    ArtifactVisualizationResponseBody,
    ArtifactVisualizationResponseMetadata,
    ArtifactVisualizationResponseResources,
)
from zenml.zen_stores.schemas.artifact_schemas import ArtifactVersionSchema
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.curated_visualization_schemas import (
        CuratedVisualizationSchema,
    )


class ArtifactVisualizationSchema(BaseSchema, table=True):
    """SQL Model for visualizations of artifacts."""

    __tablename__ = "artifact_visualization"

    # Fields
    type: str
    uri: str = Field(sa_column=Column(TEXT, nullable=False))

    # Foreign Keys
    artifact_version_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ArtifactVersionSchema.__tablename__,
        source_column="artifact_version_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )

    # Relationships
    artifact_version: ArtifactVersionSchema = Relationship(
        back_populates="visualizations"
    )
    curated_visualizations: List["CuratedVisualizationSchema"] = Relationship(
        back_populates="artifact_visualization",
        sa_relationship_kwargs=dict(
            order_by="CuratedVisualizationSchema.display_order",
            cascade="delete",
        ),
    )

    @classmethod
    def from_model(
        cls,
        artifact_visualization_request: ArtifactVisualizationRequest,
        artifact_version_id: UUID,
    ) -> "ArtifactVisualizationSchema":
        """Convert a `ArtifactVisualizationRequest` to a `ArtifactVisualizationSchema`.

        Args:
            artifact_visualization_request: The visualization.
            artifact_version_id: The UUID of the artifact version.

        Returns:
            The `ArtifactVisualizationSchema`.
        """
        return cls(
            type=artifact_visualization_request.type.value,
            uri=artifact_visualization_request.uri,
            artifact_version_id=artifact_version_id,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> ArtifactVisualizationResponse:
        """Convert an `ArtifactVisualizationSchema` to a `Visualization`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic



        Returns:
            The `Visualization`.
        """
        body = ArtifactVisualizationResponseBody(
            type=VisualizationType(self.type),
            uri=self.uri,
            created=self.created,
            updated=self.updated,
        )

        metadata = None
        if include_metadata:
            metadata = ArtifactVisualizationResponseMetadata(
                artifact_version_id=self.artifact_version_id,
            )

        resources = None
        if include_resources:
            if self.artifact_version is not None:
                artifact_version = self.artifact_version.to_model(
                    include_metadata=False,
                    include_resources=False,
                )
            else:
                artifact_version = None
            resources = ArtifactVisualizationResponseResources(
                artifact_version=artifact_version,
            )

        return ArtifactVisualizationResponse(
            id=self.id,
            body=body,
            metadata=metadata,
            resources=resources,
        )
