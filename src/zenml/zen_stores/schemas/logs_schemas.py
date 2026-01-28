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
"""SQLModel implementation of pipeline logs tables."""

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import TEXT, VARCHAR, Column, UniqueConstraint
from sqlmodel import Field, Relationship

from zenml.models import (
    LogsRequest,
    LogsResponse,
    LogsResponseBody,
    LogsResponseMetadata,
    LogsResponseResources,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema


class LogsSchema(BaseSchema, table=True):
    """SQL Model for logs."""

    __tablename__ = "logs"

    # Fields
    uri: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    source: str = Field(sa_column=Column(VARCHAR(255), nullable=False))
    log_key: Optional[str] = Field(
        sa_column=Column(VARCHAR(255), nullable=True)
    )

    __table_args__ = (
        UniqueConstraint(
            "log_key",
            name="unique_log_key",
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
    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    pipeline_run_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineRunSchema.__tablename__,
        source_column="pipeline_run_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    step_run_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="step_run_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    artifact_store_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackComponentSchema.__tablename__,
        source_column="artifact_store_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    log_store_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackComponentSchema.__tablename__,
        source_column="log_store_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )

    # Relationships
    project: "ProjectSchema" = Relationship()
    user: Optional["UserSchema"] = Relationship()
    pipeline_run: Optional["PipelineRunSchema"] = Relationship(
        back_populates="logs"
    )
    step_run: Optional["StepRunSchema"] = Relationship(back_populates="logs")

    @classmethod
    def from_request(cls, request: LogsRequest) -> "LogsSchema":
        """Create a `LogsSchema` from a `LogsRequest`.

        Args:
            request: The `LogsRequest` to create the `LogsSchema` from.

        Returns:
            The created `LogsSchema`.
        """
        log_key = None
        if request.pipeline_run_id or request.step_run_id:
            log_key = f"{request.pipeline_run_id}-{request.step_run_id}-{request.source}"

        return LogsSchema(
            id=request.id,
            uri=request.uri,
            source=request.source,
            project_id=request.project,
            user_id=request.user,
            pipeline_run_id=request.pipeline_run_id,
            step_run_id=request.step_run_id,
            artifact_store_id=request.artifact_store_id,
            log_store_id=request.log_store_id,
            log_key=log_key,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> "LogsResponse":
        """Convert a `LogsSchema` to a `LogsResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic

        Returns:
            The created `LogsResponse`.
        """
        body = LogsResponseBody(
            uri=self.uri,
            source=self.source,
            created=self.created,
            updated=self.updated,
            project_id=self.project_id,
            user_id=self.user_id,
        )

        metadata = None
        if include_metadata:
            metadata = LogsResponseMetadata(
                step_run_id=self.step_run_id,
                pipeline_run_id=self.pipeline_run_id,
                artifact_store_id=self.artifact_store_id,
                log_store_id=self.log_store_id,
            )

        resources = None
        if include_resources:
            resources = LogsResponseResources(
                user=self.user.to_model() if self.user else None,
            )

        return LogsResponse(
            id=self.id,
            body=body,
            metadata=metadata,
            resources=resources,
        )
