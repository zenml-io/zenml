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
"""SQL Model Implementations for Pipelines and Pipeline Runs."""

from typing import TYPE_CHECKING, Any, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import TEXT, Column, UniqueConstraint
from sqlalchemy.orm import joinedload, object_session
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship, desc, select

from zenml.enums import TaggableResourceTypes
from zenml.models import (
    PipelineRequest,
    PipelineResponse,
    PipelineResponseBody,
    PipelineResponseMetadata,
    PipelineResponseResources,
    PipelineUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import jl_arg

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.pipeline_build_schemas import (
        PipelineBuildSchema,
    )
    from zenml.zen_stores.schemas.pipeline_deployment_schemas import (
        PipelineDeploymentSchema,
    )
    from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
    from zenml.zen_stores.schemas.schedule_schema import ScheduleSchema
    from zenml.zen_stores.schemas.tag_schemas import TagSchema


class PipelineSchema(NamedSchema, table=True):
    """SQL Model for pipelines."""

    __tablename__ = "pipeline"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "project_id",
            name="unique_pipeline_name_in_project",
        ),
    )
    # Fields
    description: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))

    # Foreign keys
    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )

    # Relationships
    user: Optional["UserSchema"] = Relationship(back_populates="pipelines")
    project: "ProjectSchema" = Relationship(back_populates="pipelines")

    schedules: List["ScheduleSchema"] = Relationship(
        back_populates="pipeline",
    )
    builds: List["PipelineBuildSchema"] = Relationship(
        back_populates="pipeline"
    )
    deployments: List["PipelineDeploymentSchema"] = Relationship(
        back_populates="pipeline",
    )
    tags: List["TagSchema"] = Relationship(
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(foreign(TagResourceSchema.resource_type)=='{TaggableResourceTypes.PIPELINE.value}', foreign(TagResourceSchema.resource_id)==PipelineSchema.id)",
            secondary="tag_resource",
            secondaryjoin="TagSchema.id == foreign(TagResourceSchema.tag_id)",
            order_by="TagSchema.name",
            overlaps="tags",
        ),
    )

    @property
    def latest_run(self) -> Optional["PipelineRunSchema"]:
        """Fetch the latest run for this pipeline.

        Raises:
            RuntimeError: If no session for the schema exists.

        Returns:
            The latest run for this pipeline.
        """
        from zenml.zen_stores.schemas import PipelineRunSchema

        if session := object_session(self):
            return (
                session.execute(
                    select(PipelineRunSchema)
                    .where(PipelineRunSchema.pipeline_id == self.id)
                    .order_by(desc(PipelineRunSchema.created))
                    .limit(1)
                )
                .scalars()
                .one_or_none()
            )
        else:
            raise RuntimeError(
                "Missing DB session to fetch latest run for pipeline."
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
                    joinedload(jl_arg(PipelineSchema.user)),
                    # joinedload(jl_arg(PipelineSchema.tags)),
                ]
            )

        return options

    @classmethod
    def from_request(
        cls,
        pipeline_request: "PipelineRequest",
    ) -> "PipelineSchema":
        """Convert a `PipelineRequest` to a `PipelineSchema`.

        Args:
            pipeline_request: The request model to convert.

        Returns:
            The converted schema.
        """
        return cls(
            name=pipeline_request.name,
            description=pipeline_request.description,
            project_id=pipeline_request.project,
            user_id=pipeline_request.user,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> "PipelineResponse":
        """Convert a `PipelineSchema` to a `PipelineResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic

        Returns:
            The created PipelineResponse.
        """
        body = PipelineResponseBody(
            user_id=self.user_id,
            project_id=self.project_id,
            created=self.created,
            updated=self.updated,
        )

        metadata = None
        if include_metadata:
            metadata = PipelineResponseMetadata(
                description=self.description,
            )

        resources = None
        if include_resources:
            latest_run = self.latest_run
            latest_run_user = latest_run.user if latest_run else None

            resources = PipelineResponseResources(
                user=self.user.to_model() if self.user else None,
                latest_run_user=latest_run_user.to_model()
                if latest_run_user
                else None,
                latest_run_id=latest_run.id if latest_run else None,
                latest_run_status=latest_run.status if latest_run else None,
                tags=[tag.to_model() for tag in self.tags],
            )

        return PipelineResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )

    def update(self, pipeline_update: "PipelineUpdate") -> "PipelineSchema":
        """Update a `PipelineSchema` with a `PipelineUpdate`.

        Args:
            pipeline_update: The update model.

        Returns:
            The updated `PipelineSchema`.
        """
        self.description = pipeline_update.description
        self.updated = utc_now()
        return self
