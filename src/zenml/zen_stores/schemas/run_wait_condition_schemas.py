#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""SQLModel implementation of run wait condition tables."""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import TEXT, Column, Index, UniqueConstraint
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship

from zenml.models import (
    RunWaitConditionRequest,
    RunWaitConditionResponse,
    RunWaitConditionResponseBody,
    RunWaitConditionResponseMetadata,
    RunWaitConditionResponseResources,
    RunWaitConditionStatus,
    RunWaitConditionType,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.utils import jl_arg

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
    from zenml.zen_stores.schemas.user_schemas import UserSchema


class RunWaitConditionSchema(BaseSchema, table=True):
    """SQLModel schema for persisted run wait conditions."""

    __tablename__ = "run_wait_condition"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "wait_condition_key",
            name="unique_wait_condition_key_per_run",
        ),
        Index(
            "ix_run_wait_condition_run_status_created",
            "run_id",
            "status",
            "created",
        ),
        Index(
            "ix_run_wait_condition_status_lease",
            "status",
            "poller_lease_expires_at",
        ),
        Index(
            "ix_run_wait_condition_run_type_status",
            "run_id",
            "type",
            "status",
        ),
        Index(
            "ix_run_wait_condition_status_updated",
            "status",
            "updated",
        ),
        Index(
            "ix_run_wait_condition_project_created",
            "project_id",
            "created",
        ),
    )

    run_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="pipeline_run",
        source_column="run_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    resolved_by_user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target="user",
        source_column="resolved_by_user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    type: str = Field(nullable=False)
    status: str = Field(nullable=False)
    wait_condition_key: str = Field(nullable=False)
    question: Optional[str] = Field(default=None, nullable=True)
    metadata_json: str = Field(
        sa_column=Column(TEXT, nullable=False),
        default="{}",
    )
    data_schema_json: Optional[str] = Field(
        default=None, sa_column=Column(TEXT, nullable=True)
    )
    resolution: Optional[str] = Field(default=None, nullable=True)
    result_json: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    last_polled_at: Optional[datetime] = Field(nullable=True, default=None)
    poller_instance_id: Optional[str] = Field(default=None, nullable=True)
    poller_lease_expires_at: Optional[datetime] = Field(
        nullable=True, default=None
    )
    resolved_at: Optional[datetime] = Field(nullable=True, default=None)
    upstream_step_names_json: str = Field(
        sa_column=Column(TEXT, nullable=False),
        default="[]",
    )
    downstream_step_names_json: str = Field(
        sa_column=Column(TEXT, nullable=False),
        default="[]",
    )

    run: "PipelineRunSchema" = Relationship(back_populates="wait_conditions")
    resolved_by_user: Optional["UserSchema"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "RunWaitConditionSchema.resolved_by_user_id",
        }
    )

    @classmethod
    def get_query_options(
        cls,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> Sequence[ExecutableOption]:
        """Get query options for converting schema rows to models."""
        options: List[ExecutableOption] = [joinedload(jl_arg(cls.run))]
        if include_resources:
            options.append(joinedload(jl_arg(cls.resolved_by_user)))
        return options

    @classmethod
    def from_request(
        cls, request: RunWaitConditionRequest
    ) -> "RunWaitConditionSchema":
        """Create a schema object from a wait condition create request."""
        return cls(
            run_id=request.run_id,
            project_id=request.project,
            type=request.type.value,
            status=RunWaitConditionStatus.PENDING.value,
            question=request.question,
            metadata_json=json.dumps(request.metadata),
            data_schema_json=(
                json.dumps(request.data_schema)
                if request.data_schema is not None
                else None
            ),
            wait_condition_key=request.wait_condition_key,
            upstream_step_names_json=json.dumps(request.upstream_step_names),
            downstream_step_names_json=json.dumps(
                request.downstream_step_names
            ),
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> RunWaitConditionResponse:
        """Convert the schema row to a response model."""
        metadata_json: Dict[str, Any] = {}
        if self.metadata_json:
            metadata_json = json.loads(self.metadata_json)

        data_schema: Optional[Dict[str, Any]] = None
        if self.data_schema_json:
            data_schema = json.loads(self.data_schema_json)

        result: Optional[Any] = None
        if self.result_json:
            result = json.loads(self.result_json)

        body = RunWaitConditionResponseBody(
            user_id=self.run.user_id,
            project_id=self.run.project_id,
            created=self.created,
            updated=self.updated,
            run_id=self.run_id,
            type=RunWaitConditionType(self.type),
            status=RunWaitConditionStatus(self.status),
            wait_condition_key=self.wait_condition_key,
            last_polled_at=self.last_polled_at,
            poller_instance_id=self.poller_instance_id,
            poller_lease_expires_at=self.poller_lease_expires_at,
            resolved_at=self.resolved_at,
            resolved_by_user_id=self.resolved_by_user_id,
        )

        metadata = None
        if include_metadata:
            metadata = RunWaitConditionResponseMetadata(
                question=self.question,
                metadata=metadata_json,
                data_schema=data_schema,
                resolution=self.resolution,
                result=result,
                upstream_step_names=json.loads(self.upstream_step_names_json),
                downstream_step_names=json.loads(
                    self.downstream_step_names_json
                ),
            )

        resources = None
        if include_resources:
            resources = RunWaitConditionResponseResources(
                run=self.run.to_model(
                    include_metadata=False, include_resources=False
                )
            )

        return RunWaitConditionResponse(
            id=self.id,
            body=body,
            metadata=metadata,
            resources=resources,
        )
