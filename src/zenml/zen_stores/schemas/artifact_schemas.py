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
"""SQLModel implementation of artifact tables."""


from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.config.source import Source
from zenml.enums import ArtifactType, VisualizationType
from zenml.models import ArtifactRequestModel, ArtifactResponseModel
from zenml.models.visualization_models import VisualizationModel
from zenml.zen_stores.schemas.base_schemas import BaseSchema, NamedSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.run_metadata_schemas import RunMetadataSchema
    from zenml.zen_stores.schemas.step_run_schemas import (
        StepRunInputArtifactSchema,
        StepRunOutputArtifactSchema,
    )


class ArtifactSchema(NamedSchema, table=True):
    """SQL Model for artifacts."""

    __tablename__ = "artifact"

    artifact_store_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackComponentSchema.__tablename__,
        source_column="artifact_store_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="artifacts")

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="artifacts")

    type: ArtifactType
    uri: str = Field(sa_column=Column(TEXT, nullable=False))
    materializer: str = Field(sa_column=Column(TEXT, nullable=False))
    data_type: str = Field(sa_column=Column(TEXT, nullable=False))

    run_metadata: List["RunMetadataSchema"] = Relationship(
        back_populates="artifact",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    input_to_step_runs: List["StepRunInputArtifactSchema"] = Relationship(
        back_populates="artifact",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    output_of_step_runs: List["StepRunOutputArtifactSchema"] = Relationship(
        back_populates="artifact",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    visualizations: List["ArtifactVisualizationSchema"] = Relationship(
        back_populates="artifact",
        sa_relationship_kwargs={"cascade": "delete"},
    )

    @classmethod
    def from_request(
        cls, artifact_request: ArtifactRequestModel
    ) -> "ArtifactSchema":
        """Convert an `ArtifactRequestModel` to an `ArtifactSchema`.

        Args:
            artifact_request: The request model to convert.

        Returns:
            The converted schema.
        """
        return cls(
            name=artifact_request.name,
            artifact_store_id=artifact_request.artifact_store_id,
            workspace_id=artifact_request.workspace,
            user_id=artifact_request.user,
            type=artifact_request.type,
            uri=artifact_request.uri,
            materializer=artifact_request.materializer.json(),
            data_type=artifact_request.data_type.json(),
        )

    def to_model(
        self, producer_step_run_id: Optional[UUID]
    ) -> ArtifactResponseModel:
        """Convert an `ArtifactSchema` to an `ArtifactModel`.

        Args:
            producer_step_run_id: The ID of the step run that produced this
                artifact.

        Returns:
            The created `ArtifactModel`.
        """
        metadata = {
            metadata_schema.key: metadata_schema.to_model()
            for metadata_schema in self.run_metadata
        }

        try:
            materializer = Source.parse_raw(self.materializer)
        except ValidationError:
            # This is an old source which was simply an importable source path
            materializer = Source.from_import_path(self.materializer)

        try:
            data_type = Source.parse_raw(self.data_type)
        except ValidationError:
            # This is an old source which was simply an importable source path
            data_type = Source.from_import_path(self.data_type)

        return ArtifactResponseModel(
            id=self.id,
            name=self.name,
            artifact_store_id=self.artifact_store_id,
            user=self.user.to_model() if self.user else None,
            workspace=self.workspace.to_model(),
            type=self.type,
            uri=self.uri,
            materializer=materializer,
            data_type=data_type,
            created=self.created,
            updated=self.updated,
            producer_step_run_id=producer_step_run_id,
            metadata=metadata,
            visualizations=[vis.to_model() for vis in self.visualizations],
        )


class ArtifactVisualizationSchema(BaseSchema, table=True):
    """SQL Model for visualizations of artifacts."""

    __tablename__ = "artifact_visualization"

    type: VisualizationType
    uri: str = Field(sa_column=Column(TEXT, nullable=False))

    artifact_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ArtifactSchema.__tablename__,
        source_column="artifact_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    artifact: ArtifactSchema = Relationship(back_populates="visualizations")

    @classmethod
    def from_model(
        cls, visualization: VisualizationModel, artifact_id: UUID
    ) -> "ArtifactVisualizationSchema":
        """Convert a `Visualization` to a `ArtifactVisualizationSchema`.

        Args:
            visualization: The visualization.
            artifact_id: The ID of the artifact this visualization belongs to.

        Returns:
            The `ArtifactVisualizationSchema`.
        """
        return cls(
            type=visualization.type,
            uri=visualization.uri,
            artifact_id=artifact_id,
        )

    def to_model(self) -> VisualizationModel:
        """Convert an `ArtifactVisualizationSchema` to a `Visualization`.

        Returns:
            The `Visualization`.
        """
        return VisualizationModel(type=self.type, uri=self.uri)
