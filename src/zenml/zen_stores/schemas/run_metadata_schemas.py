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
"""SQLModel implementation of pipeline run metadata tables."""

import json
from typing import TYPE_CHECKING, Any, List, Optional
from uuid import UUID

from sqlalchemy import TEXT, VARCHAR, Column
from sqlmodel import Field, Relationship

from zenml.enums import MetadataResourceTypes
from zenml.metadata.metadata_types import MetadataTypeEnum
from zenml.models import (
    RunMetadataResponse,
    RunMetadataResponseBody,
    RunMetadataResponseMetadata,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.artifact_schemas import ArtifactVersionSchema
    from zenml.zen_stores.schemas.model_schemas import ModelVersionSchema
    from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
    from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema


class RunMetadataSchema(BaseSchema, table=True):
    """SQL Model for run metadata."""

    __tablename__ = "run_metadata"

    resource_id: UUID
    resource_type: str = Field(sa_column=Column(VARCHAR(255), nullable=False))
    pipeline_run: List["PipelineRunSchema"] = Relationship(
        back_populates="run_metadata",
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(RunMetadataSchema.resource_type=='{MetadataResourceTypes.PIPELINE_RUN.value}', foreign(RunMetadataSchema.resource_id)==PipelineRunSchema.id)",
            overlaps="run_metadata,step_run,artifact_version,model_version",
        ),
    )
    step_run: List["StepRunSchema"] = Relationship(
        back_populates="run_metadata",
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(RunMetadataSchema.resource_type=='{MetadataResourceTypes.STEP_RUN.value}', foreign(RunMetadataSchema.resource_id)==StepRunSchema.id)",
            overlaps="run_metadata,pipeline_run,artifact_version,model_version",
        ),
    )
    artifact_version: List["ArtifactVersionSchema"] = Relationship(
        back_populates="run_metadata",
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(RunMetadataSchema.resource_type=='{MetadataResourceTypes.ARTIFACT_VERSION.value}', foreign(RunMetadataSchema.resource_id)==ArtifactVersionSchema.id)",
            overlaps="run_metadata,pipeline_run,step_run,model_version",
        ),
    )
    model_version: List["ModelVersionSchema"] = Relationship(
        back_populates="run_metadata",
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(RunMetadataSchema.resource_type=='{MetadataResourceTypes.MODEL_VERSION.value}', foreign(RunMetadataSchema.resource_id)==ModelVersionSchema.id)",
            overlaps="run_metadata,pipeline_run,step_run,artifact_version",
        ),
    )
    stack_component_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackComponentSchema.__tablename__,
        source_column="stack_component_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    stack_component: Optional["StackComponentSchema"] = Relationship(
        back_populates="run_metadata"
    )

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="run_metadata")

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="run_metadata")

    key: str
    value: str = Field(sa_column=Column(TEXT, nullable=False))
    type: str

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> "RunMetadataResponse":
        """Convert a `RunMetadataSchema` to a `RunMetadataResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The created `RunMetadataResponse`.
        """
        body = RunMetadataResponseBody(
            user=self.user.to_model() if self.user else None,
            key=self.key,
            created=self.created,
            updated=self.updated,
            value=json.loads(self.value),
            type=MetadataTypeEnum(self.type),
        )
        metadata = None
        if include_metadata:
            metadata = RunMetadataResponseMetadata(
                workspace=self.workspace.to_model(),
                resource_id=self.resource_id,
                resource_type=MetadataResourceTypes(self.resource_type),
                stack_component_id=self.stack_component_id,
            )

        return RunMetadataResponse(
            id=self.id,
            body=body,
            metadata=metadata,
        )
