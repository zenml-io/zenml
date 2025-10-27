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
"""SQLModel implementation of pipeline deployments table."""

import json
from typing import TYPE_CHECKING, Any, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import TEXT, Column, UniqueConstraint
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship, String

from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.enums import (
    DeploymentStatus,
    TaggableResourceTypes,
    VisualizationResourceTypes,
)
from zenml.logger import get_logger
from zenml.models.v2.core.deployment import (
    DeploymentRequest,
    DeploymentResponse,
    DeploymentResponseBody,
    DeploymentResponseMetadata,
    DeploymentResponseResources,
    DeploymentUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.pipeline_snapshot_schemas import (
    PipelineSnapshotSchema,
)
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import jl_arg

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.curated_visualization_schemas import (
        CuratedVisualizationSchema,
    )
    from zenml.zen_stores.schemas.tag_schemas import TagSchema

logger = get_logger(__name__)


class DeploymentSchema(NamedSchema, table=True):
    """SQL Model for pipeline deployment."""

    __tablename__ = "deployment"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "project_id",
            name="unique_deployment_name_in_project",
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
    project: "ProjectSchema" = Relationship(back_populates="deployments")

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="deployments")

    status: str
    url: Optional[str] = Field(
        default=None,
        sa_column=Column(TEXT, nullable=True),
    )
    auth_key: Optional[str] = Field(
        default=None,
        sa_column=Column(TEXT, nullable=True),
    )
    deployment_metadata: str = Field(
        default="{}",
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=False,
        ),
    )
    snapshot_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineSnapshotSchema.__tablename__,
        source_column="snapshot_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    snapshot: Optional["PipelineSnapshotSchema"] = Relationship(
        back_populates="deployment",
    )

    deployer_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackComponentSchema.__tablename__,
        source_column="deployer_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    deployer: Optional["StackComponentSchema"] = Relationship()

    tags: List["TagSchema"] = Relationship(
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(foreign(TagResourceSchema.resource_type)=='{TaggableResourceTypes.DEPLOYMENT.value}', foreign(TagResourceSchema.resource_id)==DeploymentSchema.id)",
            secondary="tag_resource",
            secondaryjoin="TagSchema.id == foreign(TagResourceSchema.tag_id)",
            order_by="TagSchema.name",
            overlaps="tags",
        ),
    )

    visualizations: List["CuratedVisualizationSchema"] = Relationship(
        sa_relationship_kwargs=dict(
            primaryjoin=(
                "and_(CuratedVisualizationSchema.resource_type"
                f"=='{VisualizationResourceTypes.DEPLOYMENT.value}', "
                "foreign(CuratedVisualizationSchema.resource_id)==DeploymentSchema.id)"
            ),
            overlaps="visualizations",
            cascade="delete",
            order_by="CuratedVisualizationSchema.display_order",
        ),
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
                    selectinload(jl_arg(DeploymentSchema.user)),
                    selectinload(jl_arg(DeploymentSchema.deployer)),
                    selectinload(jl_arg(DeploymentSchema.snapshot)).joinedload(
                        jl_arg(PipelineSnapshotSchema.pipeline)
                    ),
                    selectinload(jl_arg(DeploymentSchema.snapshot)).joinedload(
                        jl_arg(PipelineSnapshotSchema.stack)
                    ),
                    selectinload(jl_arg(DeploymentSchema.visualizations)),
                ]
            )

        return options

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> DeploymentResponse:
        """Convert a `DeploymentSchema` to a `DeploymentResponse`.

        Args:
            include_metadata: Whether to include metadata in the response.
            include_resources: Whether to include resources in the response.
            kwargs: Additional keyword arguments.

        Returns:
            The created `DeploymentResponse`.
        """
        status: Optional[DeploymentStatus] = None
        if self.status in DeploymentStatus.values():
            status = DeploymentStatus(self.status)
        elif self.status is not None:
            status = DeploymentStatus.UNKNOWN
            logger.warning(
                f"Deployment status '{self.status}' used for deployment "
                f"{self.name} is not a valid DeploymentStatus value. "
                "Using UNKNOWN instead."
            )

        body = DeploymentResponseBody(
            user_id=self.user_id,
            project_id=self.project_id,
            created=self.created,
            updated=self.updated,
            url=self.url,
            status=status,
        )

        metadata = None
        if include_metadata:
            metadata = DeploymentResponseMetadata(
                deployment_metadata=json.loads(self.deployment_metadata),
                auth_key=self.auth_key,
            )

        resources = None
        if include_resources:
            resources = DeploymentResponseResources(
                user=self.user.to_model() if self.user else None,
                tags=[tag.to_model() for tag in self.tags],
                snapshot=self.snapshot.to_model() if self.snapshot else None,
                deployer=self.deployer.to_model() if self.deployer else None,
                pipeline=self.snapshot.pipeline.to_model()
                if self.snapshot and self.snapshot.pipeline
                else None,
                stack=self.snapshot.stack.to_model()
                if self.snapshot and self.snapshot.stack
                else None,
                visualizations=[
                    visualization.to_model(
                        include_metadata=False,
                        include_resources=False,
                    )
                    for visualization in self.visualizations
                ],
            )

        return DeploymentResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )

    def update(
        self,
        update: DeploymentUpdate,
    ) -> "DeploymentSchema":
        """Updates a `DeploymentSchema` from a `DeploymentUpdate`.

        Args:
            update: The `DeploymentUpdate` to update from.

        Returns:
            The updated `DeploymentSchema`.
        """
        for field, value in update.model_dump(
            exclude_unset=True, exclude_none=True
        ).items():
            if field == "deployment_metadata":
                setattr(self, field, json.dumps(value))
            elif hasattr(self, field):
                setattr(self, field, value)

        self.updated = utc_now()
        return self

    @classmethod
    def from_request(cls, request: DeploymentRequest) -> "DeploymentSchema":
        """Convert a `DeploymentRequest` to a `DeploymentSchema`.

        Args:
            request: The request model to convert.

        Returns:
            The converted schema.
        """
        return cls(
            name=request.name,
            project_id=request.project,
            user_id=request.user,
            status=DeploymentStatus.UNKNOWN.value,
            snapshot_id=request.snapshot_id,
            deployer_id=request.deployer_id,
            auth_key=request.auth_key,
        )
