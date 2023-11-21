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
from typing import Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.metadata.metadata_types import MetadataTypeEnum
from zenml.models import (
    RunMetadataResponse,
    RunMetadataResponseBody,
    RunMetadataResponseMetadata,
)
from zenml.zen_stores.schemas.artifact_schemas import ArtifactSchema
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema


class RunMetadataSchema(BaseSchema, table=True):
    """SQL Model for run metadata."""

    __tablename__ = "run_metadata"

    pipeline_run_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineRunSchema.__tablename__,
        source_column="pipeline_run_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    pipeline_run: Optional["PipelineRunSchema"] = Relationship(
        back_populates="run_metadata"
    )

    step_run_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="step_run_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    step_run: Optional["StepRunSchema"] = Relationship(
        back_populates="run_metadata"
    )

    artifact_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=ArtifactSchema.__tablename__,
        source_column="artifact_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    artifact: Optional["ArtifactSchema"] = Relationship(
        back_populates="run_metadata"
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
    type: MetadataTypeEnum

    def to_model(self, hydrate: bool = False) -> "RunMetadataResponse":
        """Convert a `RunMetadataSchema` to a `RunMetadataResponse`.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The created `RunMetadataResponse`.
        """
        body = RunMetadataResponseBody(
            user=self.user.to_model() if self.user else None,
            key=self.key,
            created=self.created,
            updated=self.updated,
            value=json.loads(self.value),
            type=self.type,
        )
        metadata = None
        if hydrate:
            metadata = RunMetadataResponseMetadata(
                workspace=self.workspace.to_model(),
                pipeline_run_id=self.pipeline_run_id,
                step_run_id=self.step_run_id,
                artifact_id=self.artifact_id,
                stack_component_id=self.stack_component_id,
            )

        return RunMetadataResponse(
            id=self.id,
            body=body,
            metadata=metadata,
        )
