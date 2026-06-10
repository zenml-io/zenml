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
"""SQLModel implementation of hook invocation tables."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import Column, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship, SQLModel

from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.enums import ExecutionStatus, HookType
from zenml.models import (
    ExceptionInfo,
    HookInvocationRequest,
    HookInvocationResponse,
    HookInvocationResponseBody,
    HookInvocationResponseMetadata,
    HookInvocationResponseResources,
)
from zenml.models.v2.core.artifact_version import ArtifactVersionResponse
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.utils import jl_arg

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.artifact_schemas import ArtifactVersionSchema
    from zenml.zen_stores.schemas.logs_schemas import LogsSchema
    from zenml.zen_stores.schemas.user_schemas import UserSchema


class HookInvocationSchema(BaseSchema, table=True):
    """SQL Model for hook invocations of pipeline runs."""

    __tablename__ = "hook_invocation"

    # Fields
    hook_type: str = Field(nullable=False)
    name: Optional[str] = Field(nullable=True)
    status: str = Field(nullable=False)
    start_time: datetime = Field(nullable=False)
    end_time: Optional[datetime] = Field(nullable=True)
    source: Optional[str] = Field(nullable=True)
    exception_info: Optional[str] = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=True,
        )
    )

    # Foreign keys
    pipeline_run_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="pipeline_run",
        source_column="pipeline_run_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    step_run_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target="step_run",
        source_column="step_run_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target="user",
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="project",
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )

    # Relationships
    user: Optional["UserSchema"] = Relationship()
    output_artifacts: List["HookInvocationOutputArtifactSchema"] = (
        Relationship(
            back_populates="hook_invocation",
            sa_relationship_kwargs={"cascade": "delete"},
        )
    )
    # No cascade delete. A hook's logs entry is shared with the step or
    # pipeline run, so deleting the invocation only unlinks it.
    logs: List["LogsSchema"] = Relationship(back_populates="hook_invocation")

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
        from zenml.zen_stores.schemas import ArtifactVersionSchema

        options = []

        if include_resources:
            options.extend(
                [
                    selectinload(jl_arg(HookInvocationSchema.user)),
                    selectinload(jl_arg(HookInvocationSchema.logs)),
                    selectinload(jl_arg(HookInvocationSchema.output_artifacts))
                    .joinedload(
                        jl_arg(
                            HookInvocationOutputArtifactSchema.artifact_version
                        ),
                        innerjoin=True,
                    )
                    .joinedload(
                        jl_arg(ArtifactVersionSchema.artifact), innerjoin=True
                    ),
                ]
            )

        return options

    @classmethod
    def from_request(
        cls, request: "HookInvocationRequest"
    ) -> "HookInvocationSchema":
        """Create a hook invocation schema from a request model.

        Args:
            request: The hook invocation request model.

        Returns:
            The hook invocation schema.
        """
        return cls(
            id=request.id,
            project_id=request.project,
            user_id=request.user,
            hook_type=request.hook_type.value,
            name=request.name,
            status=request.status.value,
            start_time=request.start_time,
            end_time=request.end_time,
            source=request.source,
            pipeline_run_id=request.pipeline_run_id,
            step_run_id=request.step_run_id,
            exception_info=request.exception_info.model_dump_json()
            if request.exception_info
            else None,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> "HookInvocationResponse":
        """Convert a `HookInvocationSchema` to a `HookInvocationResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic

        Returns:
            The created HookInvocationResponse.
        """
        body = HookInvocationResponseBody(
            user_id=self.user_id,
            project_id=self.project_id,
            hook_type=HookType(self.hook_type),
            status=ExecutionStatus(self.status),
            start_time=self.start_time,
            end_time=self.end_time,
            pipeline_run_id=self.pipeline_run_id,
            step_run_id=self.step_run_id,
            created=self.created,
            updated=self.updated,
        )

        metadata = None
        if include_metadata:
            metadata = HookInvocationResponseMetadata(
                source=self.source,
                exception_info=ExceptionInfo.model_validate_json(
                    self.exception_info
                )
                if self.exception_info
                else None,
            )

        resources = None
        if include_resources:
            outputs: Dict[str, List["ArtifactVersionResponse"]] = {}
            for output_artifact in self.output_artifacts:
                outputs.setdefault(output_artifact.name, []).append(
                    output_artifact.artifact_version.to_model()
                )

            resources = HookInvocationResponseResources(
                user=self.user.to_model() if self.user else None,
                outputs=outputs,
                log_collection=[
                    log.to_model()
                    for log in sorted(self.logs, key=lambda log: log.created)
                ],
            )

        return HookInvocationResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )


class HookInvocationOutputArtifactSchema(SQLModel, table=True):
    """SQL Model that defines which artifacts are outputs of which hook."""

    __tablename__ = "hook_invocation_output_artifact"

    # Fields
    name: str = Field(nullable=False, primary_key=True)

    # Foreign keys
    hook_invocation_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=HookInvocationSchema.__tablename__,
        source_column="hook_invocation_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
        custom_constraint_name=(
            "fk_hook_invocation_output_artifact_hook_invocation_id"
        ),
    )
    artifact_version_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="artifact_version",
        source_column="artifact_version_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
        custom_constraint_name=(
            "fk_hook_invocation_output_artifact_artifact_version_id"
        ),
    )

    # Relationships
    hook_invocation: "HookInvocationSchema" = Relationship(
        back_populates="output_artifacts"
    )
    artifact_version: "ArtifactVersionSchema" = Relationship(
        sa_relationship_kwargs={"lazy": "joined"},
    )
