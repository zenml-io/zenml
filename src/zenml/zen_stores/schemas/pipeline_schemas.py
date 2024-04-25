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

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional
from uuid import UUID

from sqlalchemy import TEXT, Column, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlmodel import Field, Relationship

from zenml.config.pipeline_spec import PipelineSpec
from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.models import (
    PipelineRequest,
    PipelineResponse,
    PipelineResponseBody,
    PipelineResponseMetadata,
    PipelineUpdate,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.pipeline_build_schemas import (
        PipelineBuildSchema,
    )
    from zenml.zen_stores.schemas.pipeline_deployment_schemas import (
        PipelineDeploymentSchema,
    )
    from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
    from zenml.zen_stores.schemas.schedule_schema import ScheduleSchema


class PipelineSchema(NamedSchema, table=True):
    """SQL Model for pipelines."""

    __tablename__ = "pipeline"

    # Fields
    version: str
    version_hash: str
    docstring: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    spec: str = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=False,
        )
    )

    # Foreign keys
    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
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
    workspace: "WorkspaceSchema" = Relationship(back_populates="pipelines")

    schedules: List["ScheduleSchema"] = Relationship(
        back_populates="pipeline",
    )
    runs: List["PipelineRunSchema"] = Relationship(back_populates="pipeline")
    builds: List["PipelineBuildSchema"] = Relationship(
        back_populates="pipeline"
    )
    deployments: List["PipelineDeploymentSchema"] = Relationship(
        back_populates="pipeline",
    )

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
            version=pipeline_request.version,
            version_hash=pipeline_request.version_hash,
            workspace_id=pipeline_request.workspace,
            user_id=pipeline_request.user,
            docstring=pipeline_request.docstring,
            spec=json.dumps(
                pipeline_request.spec.model_dump(mode="json"), sort_keys=True
            ),
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        last_x_runs: int = 3,
        **kwargs: Any,
    ) -> "PipelineResponse":
        """Convert a `PipelineSchema` to a `PipelineResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic
            last_x_runs: How many runs to use for the execution status

        Returns:
            The created PipelineResponse.
        """
        body = PipelineResponseBody(
            user=self.user.to_model() if self.user else None,
            status=[run.status for run in self.runs[:last_x_runs]],
            created=self.created,
            updated=self.updated,
            version=self.version,
        )
        metadata = None
        if include_metadata:
            metadata = PipelineResponseMetadata(
                workspace=self.workspace.to_model(),
                version_hash=self.version_hash,
                spec=PipelineSpec.model_validate_json(self.spec),
                docstring=self.docstring,
            )

        return PipelineResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
        )

    def update(self, pipeline_update: "PipelineUpdate") -> "PipelineSchema":
        """Update a `PipelineSchema` with a `PipelineUpdate`.

        Args:
            pipeline_update: The update model.

        Returns:
            The updated `PipelineSchema`.
        """
        self.updated = datetime.utcnow()
        return self
