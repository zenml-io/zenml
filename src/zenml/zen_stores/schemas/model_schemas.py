#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""SQLModel implementation of model tables."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import BOOLEAN, INTEGER, TEXT, Column
from sqlmodel import Field, Relationship

from zenml.enums import TaggableResourceTypes
from zenml.models import (
    ModelRequest,
    ModelResponse,
    ModelResponseBody,
    ModelResponseMetadata,
    ModelUpdate,
    ModelVersionArtifactRequest,
    ModelVersionArtifactResponse,
    ModelVersionArtifactResponseBody,
    ModelVersionPipelineRunRequest,
    ModelVersionPipelineRunResponse,
    ModelVersionPipelineRunResponseBody,
    ModelVersionRequest,
    ModelVersionResponse,
    ModelVersionResponseBody,
    ModelVersionResponseMetadata,
    UserScopedResponseMetadata,
)
from zenml.zen_stores.schemas.artifact_schemas import ArtifactSchema
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.tag_schemas import TagResourceSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema


class ModelSchema(NamedSchema, table=True):
    """SQL Model for model."""

    __tablename__ = "model"

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="models")

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="models")

    license: str = Field(sa_column=Column(TEXT, nullable=True))
    description: str = Field(sa_column=Column(TEXT, nullable=True))
    audience: str = Field(sa_column=Column(TEXT, nullable=True))
    use_cases: str = Field(sa_column=Column(TEXT, nullable=True))
    limitations: str = Field(sa_column=Column(TEXT, nullable=True))
    trade_offs: str = Field(sa_column=Column(TEXT, nullable=True))
    ethics: str = Field(sa_column=Column(TEXT, nullable=True))
    tags: List["TagResourceSchema"] = Relationship(
        back_populates="model",
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(TagResourceSchema.resource_type=='{TaggableResourceTypes.MODEL.value}', foreign(TagResourceSchema.resource_id)==ModelSchema.id)",
            cascade="delete",
        ),
    )
    model_versions: List["ModelVersionSchema"] = Relationship(
        back_populates="model",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    artifact_links: List["ModelVersionArtifactSchema"] = Relationship(
        back_populates="model",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    pipeline_run_links: List["ModelVersionPipelineRunSchema"] = Relationship(
        back_populates="model",
        sa_relationship_kwargs={"cascade": "delete"},
    )

    @classmethod
    def from_request(cls, model_request: ModelRequest) -> "ModelSchema":
        """Convert an `ModelRequest` to an `ModelSchema`.

        Args:
            model_request: The request model to convert.

        Returns:
            The converted schema.
        """
        return cls(
            name=model_request.name,
            workspace_id=model_request.workspace,
            user_id=model_request.user,
            license=model_request.license,
            description=model_request.description,
            audience=model_request.audience,
            use_cases=model_request.use_cases,
            limitations=model_request.limitations,
            trade_offs=model_request.trade_offs,
            ethics=model_request.ethics,
        )

    def to_model(
        self,
        hydrate: bool = False,
    ) -> ModelResponse:
        """Convert an `ModelSchema` to an `ModelResponse`.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The created `ModelResponse`.
        """
        tags = [t.tag.to_model() for t in self.tags]
        if self.model_versions:
            version_numbers = [mv.number for mv in self.model_versions]
            latest_version = self.model_versions[
                version_numbers.index(max(version_numbers))
            ].name
        else:
            latest_version = None

        metadata = None
        if hydrate:
            metadata = ModelResponseMetadata(
                workspace=self.workspace.to_model(),
                license=self.license,
                description=self.description,
                audience=self.audience,
                use_cases=self.use_cases,
                limitations=self.limitations,
                trade_offs=self.trade_offs,
                ethics=self.ethics,
            )

        body = ModelResponseBody(
            user=self.user.to_model() if self.user else None,
            created=self.created,
            updated=self.updated,
            tags=tags,
            latest_version=latest_version,
        )

        return ModelResponse(
            id=self.id, name=self.name, body=body, metadata=metadata
        )

    def update(
        self,
        model_update: ModelUpdate,
    ) -> "ModelSchema":
        """Updates a `ModelSchema` from a `ModelUpdate`.

        Args:
            model_update: The `ModelUpdate` to update from.

        Returns:
            The updated `ModelSchema`.
        """
        for field, value in model_update.dict(
            exclude_unset=True, exclude_none=True
        ).items():
            setattr(self, field, value)
        self.updated = datetime.utcnow()
        return self


class ModelVersionSchema(NamedSchema, table=True):
    """SQL Model for model version."""

    __tablename__ = "model_version"

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(
        back_populates="model_versions"
    )

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(
        back_populates="model_versions"
    )

    model_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ModelSchema.__tablename__,
        source_column="model_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    model: "ModelSchema" = Relationship(back_populates="model_versions")
    artifact_links: List["ModelVersionArtifactSchema"] = Relationship(
        back_populates="model_version",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    pipeline_run_links: List["ModelVersionPipelineRunSchema"] = Relationship(
        back_populates="model_version",
        sa_relationship_kwargs={"cascade": "delete"},
    )

    number: int = Field(sa_column=Column(INTEGER, nullable=False))
    description: str = Field(sa_column=Column(TEXT, nullable=True))
    stage: str = Field(sa_column=Column(TEXT, nullable=True))

    @classmethod
    def from_request(
        cls, model_version_request: ModelVersionRequest
    ) -> "ModelVersionSchema":
        """Convert an `ModelVersionRequest` to an `ModelVersionSchema`.

        Args:
            model_version_request: The request model version to convert.

        Returns:
            The converted schema.
        """
        return cls(
            workspace_id=model_version_request.workspace,
            user_id=model_version_request.user,
            model_id=model_version_request.model,
            name=model_version_request.name,
            number=model_version_request.number,
            description=model_version_request.description,
            stage=model_version_request.stage,
        )

    def to_model(
        self,
        hydrate: bool = False,
    ) -> ModelVersionResponse:
        """Convert an `ModelVersionSchema` to an `ModelVersionResponse`.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The created `ModelVersionResponse`.
        """
        metadata = None
        if hydrate:
            metadata = ModelVersionResponseMetadata(
                workspace=self.workspace.to_model(),
                description=self.description,
            )

        body = ModelVersionResponseBody(
            user=self.user.to_model() if self.user else None,
            created=self.created,
            updated=self.updated,
            stage=self.stage,
            number=self.number,
            model=self.model.to_model(),
            model_artifact_ids={
                f"{al1.pipeline_name}::{al1.step_name}::{al1.name}": {
                    al2.version: al2.artifact_id
                    for al2 in self.artifact_links
                    if al2.is_model_artifact
                    and al1.name == al2.name
                    and al1.step_name == al2.step_name
                    and al1.pipeline_name == al2.pipeline_name
                }
                for al1 in self.artifact_links
                if al1.is_model_artifact
            },
            data_artifact_ids={
                f"{al1.pipeline_name}::{al1.step_name}::{al1.name}": {
                    al2.version: al2.artifact_id
                    for al2 in self.artifact_links
                    if not (al2.is_endpoint_artifact or al2.is_model_artifact)
                    and al1.name == al2.name
                    and al1.step_name == al2.step_name
                    and al1.pipeline_name == al2.pipeline_name
                }
                for al1 in self.artifact_links
                if not (al1.is_endpoint_artifact or al1.is_model_artifact)
            },
            endpoint_artifact_ids={
                f"{al1.pipeline_name}::{al1.step_name}::{al1.name}": {
                    al2.version: al2.artifact_id
                    for al2 in self.artifact_links
                    if al2.is_endpoint_artifact
                    and al1.name == al2.name
                    and al1.step_name == al2.step_name
                    and al1.pipeline_name == al2.pipeline_name
                }
                for al1 in self.artifact_links
                if al1.is_endpoint_artifact
            },
            pipeline_run_ids={
                pr.name: pr.pipeline_run_id for pr in self.pipeline_run_links
            },
        )

        return ModelVersionResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
        )

    def update(
        self,
        target_stage: Optional[str] = None,
        target_name: Optional[str] = None,
    ) -> "ModelVersionSchema":
        """Updates a `ModelVersionSchema` to a target stage.

        Args:
            target_stage: The stage to be updated.
            target_name: The version name to be updated.

        Returns:
            The updated `ModelVersionSchema`.
        """
        if target_stage is not None:
            self.stage = target_stage
        if target_name is not None:
            self.name = target_name
        self.updated = datetime.utcnow()
        return self


class ModelVersionArtifactSchema(NamedSchema, table=True):
    """SQL Model for linking of Model Versions and Artifacts M:M."""

    __tablename__ = "model_versions_artifacts"

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(
        back_populates="model_versions_artifacts_links"
    )

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(
        back_populates="model_versions_artifacts_links"
    )

    model_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ModelSchema.__tablename__,
        source_column="model_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    model: "ModelSchema" = Relationship(back_populates="artifact_links")
    model_version_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ModelVersionSchema.__tablename__,
        source_column="model_version_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    model_version: "ModelVersionSchema" = Relationship(
        back_populates="artifact_links"
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
        back_populates="model_versions_artifacts_links"
    )

    is_model_artifact: bool = Field(sa_column=Column(BOOLEAN, nullable=True))
    is_endpoint_artifact: bool = Field(
        sa_column=Column(BOOLEAN, nullable=True)
    )
    version: int = Field(sa_column=Column(INTEGER, nullable=False))
    pipeline_name: str = Field(sa_column=Column(TEXT, nullable=False))
    step_name: str = Field(sa_column=Column(TEXT, nullable=False))

    @classmethod
    def from_request(
        cls,
        model_version_artifact_request: ModelVersionArtifactRequest,
        version: int,
    ) -> "ModelVersionArtifactSchema":
        """Convert an `ModelVersionArtifactRequest` to a `ModelVersionArtifactSchema`.

        Args:
            model_version_artifact_request: The request link to convert.
            version: The version of versioned link.

        Returns:
            The converted schema.
        """
        return cls(
            name=model_version_artifact_request.name,
            pipeline_name=model_version_artifact_request.pipeline_name,
            step_name=model_version_artifact_request.step_name,
            workspace_id=model_version_artifact_request.workspace,
            user_id=model_version_artifact_request.user,
            model_id=model_version_artifact_request.model,
            model_version_id=model_version_artifact_request.model_version,
            artifact_id=model_version_artifact_request.artifact,
            is_model_artifact=model_version_artifact_request.is_model_artifact,
            is_endpoint_artifact=model_version_artifact_request.is_endpoint_artifact,
            version=version,
        )

    def to_model(
        self,
        hydrate: bool = False,
    ) -> ModelVersionArtifactResponse:
        """Convert an `ModelVersionArtifactSchema` to an `ModelVersionArtifactResponse`.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The created `ModelVersionArtifactResponse`.
        """
        metadata = None
        if hydrate:
            metadata = UserScopedResponseMetadata()

        body = ModelVersionArtifactResponseBody(
            user=self.user.to_model() if self.user else None,
            created=self.created,
            updated=self.updated,
            name=self.name,
            pipeline_name=self.pipeline_name,
            step_name=self.step_name,
            artifact=self.artifact_id,
            model=self.model_id,
            model_version=self.model_version_id,
            is_model_artifact=self.is_model_artifact,
            is_endpoint_artifact=self.is_endpoint_artifact,
            link_version=self.version,
        )

        return ModelVersionArtifactResponse(
            id=self.id,
            body=body,
            metadata=metadata,
        )


class ModelVersionPipelineRunSchema(NamedSchema, table=True):
    """SQL Model for linking of Model Versions and Pipeline Runs M:M."""

    __tablename__ = "model_versions_runs"

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(
        back_populates="model_versions_pipeline_runs_links"
    )

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(
        back_populates="model_versions_pipeline_runs_links"
    )

    model_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ModelSchema.__tablename__,
        source_column="model_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    model: "ModelSchema" = Relationship(back_populates="pipeline_run_links")
    model_version_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ModelVersionSchema.__tablename__,
        source_column="model_version_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    model_version: "ModelVersionSchema" = Relationship(
        back_populates="pipeline_run_links"
    )
    pipeline_run_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineRunSchema.__tablename__,
        source_column="run_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    pipeline_run: Optional["PipelineRunSchema"] = Relationship(
        back_populates="model_versions_pipeline_runs_links"
    )

    @classmethod
    def from_request(
        cls,
        model_version_pipeline_run_request: ModelVersionPipelineRunRequest,
    ) -> "ModelVersionPipelineRunSchema":
        """Convert an `ModelVersionPipelineRunRequest` to an `ModelVersionPipelineRunSchema`.

        Args:
            model_version_pipeline_run_request: The request link to convert.

        Returns:
            The converted schema.
        """
        return cls(
            workspace_id=model_version_pipeline_run_request.workspace,
            user_id=model_version_pipeline_run_request.user,
            name=model_version_pipeline_run_request.name,
            model_id=model_version_pipeline_run_request.model,
            model_version_id=model_version_pipeline_run_request.model_version,
            pipeline_run_id=model_version_pipeline_run_request.pipeline_run,
        )

    def to_model(
        self,
        hydrate: bool = False,
    ) -> ModelVersionPipelineRunResponse:
        """Convert an `ModelVersionPipelineRunSchema` to an `ModelVersionPipelineRunResponse`.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The created `ModelVersionPipelineRunResponse`.
        """
        metadata = None
        if hydrate:
            metadata = UserScopedResponseMetadata()

        body = ModelVersionPipelineRunResponseBody(
            user=self.user.to_model() if self.user else None,
            created=self.created,
            updated=self.updated,
            name=self.name,
            pipeline_run=self.pipeline_run_id,
            model=self.model_id,
            model_version=self.model_version_id,
        )
        return ModelVersionPipelineRunResponse(
            id=self.id,
            body=body,
            metadata=metadata,
        )
