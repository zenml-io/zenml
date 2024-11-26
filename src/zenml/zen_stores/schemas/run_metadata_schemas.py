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

from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import TEXT, VARCHAR, Column
from sqlmodel import Field, Relationship, SQLModel

from zenml.enums import MetadataResourceTypes
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.artifact_schemas import ArtifactVersionSchema
    from zenml.zen_stores.schemas.model_schemas import ModelVersionSchema
    from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema


class RunMetadataSchema(BaseSchema, table=True):
    """SQL Model for run metadata."""

    __tablename__ = "run_metadata"

    # Relationship to link to resources
    resources: List["RunMetadataResourceSchema"] = Relationship(
        back_populates="run_metadata",
        sa_relationship_kwargs={"cascade": "delete"},
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
    cached: Optional[bool] = Field(default=False)


class RunMetadataResourceSchema(SQLModel, table=True):
    """Table for linking resources to run metadata entries."""

    __tablename__ = "run_metadata_resource"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    resource_id: UUID
    resource_type: str = Field(sa_column=Column(VARCHAR(255), nullable=False))
    run_metadata_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=RunMetadataSchema.__tablename__,
        source_column="run_metadata_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )

    # Relationship back to the base metadata table
    run_metadata: RunMetadataSchema = Relationship(back_populates="resources")

    # Relationship to link specific resource types
    pipeline_run: List["PipelineRunSchema"] = Relationship(
        back_populates="run_metadata_resources",
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(RunMetadataResourceSchema.resource_type=='{MetadataResourceTypes.PIPELINE_RUN.value}', foreign(RunMetadataResourceSchema.resource_id)==PipelineRunSchema.id)",
            overlaps="run_metadata_resources,step_run,artifact_version,model_version",
        ),
    )
    step_run: List["StepRunSchema"] = Relationship(
        back_populates="run_metadata_resources",
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(RunMetadataResourceSchema.resource_type=='{MetadataResourceTypes.STEP_RUN.value}', foreign(RunMetadataResourceSchema.resource_id)==StepRunSchema.id)",
            overlaps="run_metadata_resources,pipeline_run,artifact_version,model_version",
        ),
    )
    artifact_version: List["ArtifactVersionSchema"] = Relationship(
        back_populates="run_metadata_resources",
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(RunMetadataResourceSchema.resource_type=='{MetadataResourceTypes.ARTIFACT_VERSION.value}', foreign(RunMetadataResourceSchema.resource_id)==ArtifactVersionSchema.id)",
            overlaps="run_metadata_resources,pipeline_run,step_run,model_version",
        ),
    )
    model_version: List["ModelVersionSchema"] = Relationship(
        back_populates="run_metadata_resources",
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(RunMetadataResourceSchema.resource_type=='{MetadataResourceTypes.MODEL_VERSION.value}', foreign(RunMetadataResourceSchema.resource_id)==ModelVersionSchema.id)",
            overlaps="run_metadata_resources,pipeline_run,step_run,artifact_version",
        ),
    )
