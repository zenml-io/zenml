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
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlmodel import Field, Relationship

from zenml.models import (
    ScheduleRequest,
    ScheduleResponse,
    ScheduleResponseBody,
    ScheduleResponseMetadata,
    ScheduleUpdate,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.pipeline_schemas import PipelineSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.pipeline_deployment_schemas import (
        PipelineDeploymentSchema,
    )


class ScheduleSchema(NamedSchema, table=True):
    """SQL Model for schedules."""

    __tablename__ = "schedule"

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="schedules")

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

    active: bool
    cron_expression: Optional[str] = Field(nullable=True)
    start_time: Optional[datetime] = Field(nullable=True)
    end_time: Optional[datetime] = Field(nullable=True)
    interval_second: Optional[float] = Field(nullable=True)
    catchup: bool

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
            workspace_id=schedule_request.workspace,
            user_id=schedule_request.user,
            pipeline_id=schedule_request.pipeline_id,
            orchestrator_id=schedule_request.orchestrator_id,
            active=schedule_request.active,
            cron_expression=schedule_request.cron_expression,
            start_time=schedule_request.start_time,
            end_time=schedule_request.end_time,
            interval_second=interval_second,
            catchup=schedule_request.catchup,
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
        if schedule_update.active is not None:
            self.active = schedule_update.active
        if schedule_update.cron_expression is not None:
            self.cron_expression = schedule_update.cron_expression
        if schedule_update.start_time is not None:
            self.start_time = schedule_update.start_time
        if schedule_update.end_time is not None:
            self.end_time = schedule_update.end_time
        if schedule_update.interval_second is not None:
            self.interval_second = (
                schedule_update.interval_second.total_seconds()
            )
        if schedule_update.catchup is not None:
            self.catchup = schedule_update.catchup
        self.updated = datetime.utcnow()
        return self

    def to_model(self, hydrate: bool = False) -> ScheduleResponse:
        """Convert a `ScheduleSchema` to a `ScheduleResponseModel`.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The created `ScheduleResponseModel`.
        """
        if self.interval_second is not None:
            interval_second = timedelta(seconds=self.interval_second)
        else:
            interval_second = None

        body = ScheduleResponseBody(
            user=self.user.to_model() if self.user else None,
            active=self.active,
            cron_expression=self.cron_expression,
            start_time=self.start_time,
            end_time=self.end_time,
            interval_second=interval_second,
            catchup=self.catchup,
            updated=self.updated,
            created=self.created,
        )
        metadata = None
        if hydrate:
            metadata = ScheduleResponseMetadata(
                workspace=self.workspace.to_model(),
                pipeline_id=self.pipeline_id,
                orchestrator_id=self.orchestrator_id,
            )

        return ScheduleResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
        )
