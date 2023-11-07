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

from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.enums import VisualizationType
from zenml.models import (
    ArtifactVisualizationRequest,
    ArtifactVisualizationResponse,
    ArtifactVisualizationResponseBody,
    ArtifactVisualizationResponseMetadata,
)
from zenml.zen_stores.schemas import ArtifactSchema, BaseSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field


class ArtifactVisualizationSchema(BaseSchema, table=True):
    """SQL Model for visualizations of artifacts."""

    __tablename__ = "artifact_visualization"

    # Fields
    type: VisualizationType
    uri: str = Field(sa_column=Column(TEXT, nullable=False))

    # Foreign Keys
    artifact_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ArtifactSchema.__tablename__,
        source_column="artifact_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )

    # Relationships
    artifact: ArtifactSchema = Relationship(back_populates="visualizations")

    @classmethod
    def from_model(
        cls,
        artifact_visualization_request: ArtifactVisualizationRequest,
        artifact_id: UUID,
    ) -> "ArtifactVisualizationSchema":
        """Convert a `ArtifactVisualizationRequest` to a `ArtifactVisualizationSchema`.

        Args:
            artifact_visualization_request: The visualization.
            artifact_id: The UUID of the artifact.

        Returns:
            The `ArtifactVisualizationSchema`.
        """
        return cls(
            type=artifact_visualization_request.type,
            uri=artifact_visualization_request.uri,
            artifact_id=artifact_id,
        )

    def to_model(self, hydrate: bool = False) -> ArtifactVisualizationResponse:
        """Convert an `ArtifactVisualizationSchema` to a `Visualization`.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The `Visualization`.
        """
        body = ArtifactVisualizationResponseBody(
            type=self.type,
            uri=self.uri,
            created=self.created,
            updated=self.updated,
        )

        metadata = None
        if hydrate:
            metadata = ArtifactVisualizationResponseMetadata(
                artifact_id=self.artifact_id,
            )

        return ArtifactVisualizationResponse(
            id=self.id,
            body=body,
            metadata=metadata,
        )
