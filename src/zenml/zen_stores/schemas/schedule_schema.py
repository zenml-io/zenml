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
"""SQL Model Implementations for Pipeline Schedules."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship

from zenml.enums import MetadataResourceTypes
from zenml.models import (
    ScheduleRequest,
    ScheduleResponse,
    ScheduleResponseBody,
    ScheduleResponseMetadata,
    ScheduleResponseResources,
    ScheduleUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.pipeline_schemas import PipelineSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import (
    RunMetadataInterface,
    jl_arg,
)

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.pipeline_deployment_schemas import (
        PipelineDeploymentSchema,
    )
    from zenml.zen_stores.schemas.run_metadata_schemas import (
        RunMetadataSchema,
    )


class ScheduleSchema(NamedSchema, RunMetadataInterface, table=True):
    """SQL Model for schedules."""

    __tablename__ = "schedule"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "project_id",
            name="unique_schedule_name_in_project",
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
    project: "ProjectSchema" = Relationship(back_populates="schedules")

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="schedules")

    pipeline_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineSchema.__tablename__,
        source_column="pipeline_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    pipeline: "PipelineSchema" = Relationship(back_populates="schedules")
    deployment: Optional["PipelineDeploymentSchema"] = Relationship(
        back_populates="schedule"
    )

    orchestrator_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackComponentSchema.__tablename__,
        source_column="orchestrator_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    orchestrator: "StackComponentSchema" = Relationship(
        back_populates="schedules"
    )

    run_metadata: List["RunMetadataSchema"] = Relationship(
        sa_relationship_kwargs=dict(
            secondary="run_metadata_resource",
            primaryjoin=f"and_(foreign(RunMetadataResourceSchema.resource_type)=='{MetadataResourceTypes.SCHEDULE.value}', foreign(RunMetadataResourceSchema.resource_id)==ScheduleSchema.id)",
            secondaryjoin="RunMetadataSchema.id==foreign(RunMetadataResourceSchema.run_metadata_id)",
            overlaps="run_metadata",
        ),
    )

    active: bool
    cron_expression: Optional[str] = Field(nullable=True)
    start_time: Optional[datetime] = Field(nullable=True)
    end_time: Optional[datetime] = Field(nullable=True)
    interval_second: Optional[float] = Field(nullable=True)
    catchup: bool
    run_once_start_time: Optional[datetime] = Field(nullable=True)

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

        # if include_metadata:
        #     options.extend(
        #         [
        #             joinedload(jl_arg(ScheduleSchema.run_metadata)),
        #         ]
        #     )

        if include_resources:
            options.extend([joinedload(jl_arg(ScheduleSchema.user))])

        return options

    @classmethod
    def from_request(
        cls, schedule_request: ScheduleRequest
    ) -> "ScheduleSchema":
        """Create a `ScheduleSchema` from a `ScheduleRequest`.

        Args:
            schedule_request: The `ScheduleRequest` to create the schema from.

        Returns:
            The created `ScheduleSchema`.
        """
        if schedule_request.interval_second is not None:
            interval_second = schedule_request.interval_second.total_seconds()
        else:
            interval_second = None
        return cls(
            name=schedule_request.name,
            project_id=schedule_request.project,
            user_id=schedule_request.user,
            pipeline_id=schedule_request.pipeline_id,
            orchestrator_id=schedule_request.orchestrator_id,
            active=schedule_request.active,
            cron_expression=schedule_request.cron_expression,
            start_time=schedule_request.start_time,
            end_time=schedule_request.end_time,
            interval_second=interval_second,
            catchup=schedule_request.catchup,
            run_once_start_time=schedule_request.run_once_start_time,
        )

    def update(self, schedule_update: ScheduleUpdate) -> "ScheduleSchema":
        """Update a `ScheduleSchema` from a `ScheduleUpdateModel`.

        Args:
            schedule_update: The `ScheduleUpdateModel` to update the schema from.

        Returns:
            The updated `ScheduleSchema`.
        """
        if schedule_update.name is not None:
            self.name = schedule_update.name

        self.updated = utc_now()
        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> ScheduleResponse:
        """Convert a `ScheduleSchema` to a `ScheduleResponseModel`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The created `ScheduleResponseModel`.
        """
        if self.interval_second is not None:
            interval_second = timedelta(seconds=self.interval_second)
        else:
            interval_second = None

        body = ScheduleResponseBody(
            user_id=self.user_id,
            project_id=self.project_id,
            active=self.active,
            cron_expression=self.cron_expression,
            start_time=self.start_time,
            end_time=self.end_time,
            interval_second=interval_second,
            catchup=self.catchup,
            updated=self.updated,
            created=self.created,
            run_once_start_time=self.run_once_start_time,
        )
        metadata = None
        if include_metadata:
            metadata = ScheduleResponseMetadata(
                pipeline_id=self.pipeline_id,
                orchestrator_id=self.orchestrator_id,
                run_metadata=self.fetch_metadata(),
            )

        resources = None
        if include_resources:
            resources = ScheduleResponseResources(
                user=self.user.to_model() if self.user else None,
            )

        return ScheduleResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )
