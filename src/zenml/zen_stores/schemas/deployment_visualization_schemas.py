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
"""SQLModel implementation of deployment visualization table."""

from typing import TYPE_CHECKING, Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.core.deployment_visualization import (
    DeploymentVisualizationRequest,
    DeploymentVisualizationResponse,
    DeploymentVisualizationResponseBody,
    DeploymentVisualizationResponseMetadata,
    DeploymentVisualizationResponseResources,
    DeploymentVisualizationUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.artifact_schemas import ArtifactVersionSchema
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import (
    build_foreign_key_field,
    build_index,
)
from zenml.zen_stores.schemas.utils import jl_arg

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.deployment_schemas import DeploymentSchema


class DeploymentVisualizationSchema(BaseSchema, table=True):
    """SQL Model for deployment visualizations."""

    __tablename__ = "deployment_visualization"
    __table_args__ = (
        UniqueConstraint(
            "deployment_id",
            "artifact_version_id",
            "visualization_index",
            name="unique_deployment_visualization",
        ),
        build_index(
            __tablename__,
            ["deployment_id"],
        ),
        build_index(
            __tablename__,
            ["display_order"],
        ),
    )

    # Foreign Keys
    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )

    deployment_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="deployment",
        source_column="deployment_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )

    artifact_version_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ArtifactVersionSchema.__tablename__,
        source_column="artifact_version_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )

    # Fields
    visualization_index: int = Field(nullable=False)
    display_name: Optional[str] = Field(
        max_length=STR_FIELD_MAX_LENGTH, default=None
    )
    display_order: Optional[int] = Field(default=None)

    # Relationships
    deployment: Optional["DeploymentSchema"] = Relationship(
        back_populates="visualizations",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    artifact_version: Optional[ArtifactVersionSchema] = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"}
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
        options = []

        if include_resources:
            options.extend(
                [
                    selectinload(jl_arg(cls.deployment)),
                    selectinload(jl_arg(cls.artifact_version)),
                ]
            )

        return options

    @classmethod
    def from_request(
        cls, request: DeploymentVisualizationRequest
    ) -> "DeploymentVisualizationSchema":
        """Convert a `DeploymentVisualizationRequest` to a `DeploymentVisualizationSchema`.

        Args:
            request: The request model to convert.

        Returns:
            The converted schema.
        """
        return cls(
            project_id=request.project,
            deployment_id=request.deployment_id,
            artifact_version_id=request.artifact_version_id,
            visualization_index=request.visualization_index,
            display_name=request.display_name,
            display_order=request.display_order,
        )

    def update(
        self,
        update: DeploymentVisualizationUpdate,
    ) -> "DeploymentVisualizationSchema":
        """Updates a `DeploymentVisualizationSchema` from a `DeploymentVisualizationUpdate`.

        Args:
            update: The `DeploymentVisualizationUpdate` to update from.

        Returns:
            The updated `DeploymentVisualizationSchema`.
        """
        for field, value in update.model_dump(
            exclude_unset=True, exclude_none=True
        ).items():
            if hasattr(self, field):
                setattr(self, field, value)

        self.updated = utc_now()
        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> DeploymentVisualizationResponse:
        """Convert a `DeploymentVisualizationSchema` to a `DeploymentVisualizationResponse`.

        Args:
            include_metadata: Whether to include metadata in the response.
            include_resources: Whether to include resources in the response.
            **kwargs: Additional keyword arguments, including `include_deployment`
                to control whether deployment resources are included (default True).

        Returns:
            The created `DeploymentVisualizationResponse`.
        """
        include_deployment = kwargs.get("include_deployment", True)

        body = DeploymentVisualizationResponseBody(
            user_id=None,
            project_id=self.project_id,
            created=self.created,
            updated=self.updated,
            deployment_id=self.deployment_id,
            artifact_version_id=self.artifact_version_id,
            visualization_index=self.visualization_index,
            display_name=self.display_name,
            display_order=self.display_order,
        )

        metadata = None
        if include_metadata:
            metadata = DeploymentVisualizationResponseMetadata()

        resources = None
        if include_resources:
            resources = DeploymentVisualizationResponseResources(
                deployment=self.deployment.to_model(
                    include_metadata=include_metadata,
                    include_resources=include_resources,
                )
                if self.deployment and include_deployment
                else None,
                artifact_version=self.artifact_version.to_model(
                    include_metadata=include_metadata,
                    include_resources=include_resources,
                )
                if self.artifact_version
                else None,
            )

        return DeploymentVisualizationResponse(
            id=self.id,
            body=body,
            metadata=metadata,
            resources=resources,
        )
