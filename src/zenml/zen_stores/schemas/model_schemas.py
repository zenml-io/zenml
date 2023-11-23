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
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from sqlalchemy import BOOLEAN, INTEGER, TEXT, Column
from sqlmodel import Field, Relationship

from zenml.enums import TaggableResourceTypes
from zenml.models import (
    ModelRequestModel,
    ModelResponseModel,
    ModelUpdateModel,
    ModelVersionArtifactRequestModel,
    ModelVersionArtifactResponseModel,
    ModelVersionPipelineRunRequestModel,
    ModelVersionPipelineRunResponseModel,
    ModelVersionRequestModel,
    ModelVersionResponseModel,
)
from zenml.zen_stores.schemas.artifact_schemas import ArtifactSchema
from zenml.zen_stores.schemas.base_schemas import BaseSchema, NamedSchema
from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.tag_schemas import TagResourceSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    pass


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
            overlaps="tags",
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
    def from_request(cls, model_request: ModelRequestModel) -> "ModelSchema":
        """Convert an `ModelRequestModel` to an `ModelSchema`.

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
    ) -> ModelResponseModel:
        """Convert an `ModelSchema` to an `ModelResponseModel`.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The created `ModelResponseModel`.
        """
        tags = [t.tag.to_model() for t in self.tags]
        if self.model_versions:
            version_numbers = [mv.number for mv in self.model_versions]
            latest_version = self.model_versions[
                version_numbers.index(max(version_numbers))
            ].name
        else:
            latest_version = None
        return ModelResponseModel(
            id=self.id,
            name=self.name,
            user=self.user.to_model() if self.user else None,
            workspace=self.workspace.to_model(),
            created=self.created,
            updated=self.updated,
            license=self.license,
            description=self.description,
            audience=self.audience,
            use_cases=self.use_cases,
            limitations=self.limitations,
            trade_offs=self.trade_offs,
            ethics=self.ethics,
            tags=tags,
            latest_version=latest_version,
        )

    def update(
        self,
        model_update: ModelUpdateModel,
    ) -> "ModelSchema":
        """Updates a `ModelSchema` from a `ModelUpdateModel`.

        Args:
            model_update: The `ModelUpdateModel` to update from.

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
        cls, model_version_request: ModelVersionRequestModel
    ) -> "ModelVersionSchema":
        """Convert an `ModelVersionRequestModel` to an `ModelVersionSchema`.

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
    ) -> ModelVersionResponseModel:
        """Convert an `ModelVersionSchema` to an `ModelVersionResponseModel`.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The created `ModelVersionResponseModel`.
        """
        # Construct {name: {version: id}} dicts for all linked artifacts
        model_artifact_ids: Dict[str, Dict[str, UUID]] = {}
        endpoint_artifact_ids: Dict[str, Dict[str, UUID]] = {}
        data_artifact_ids: Dict[str, Dict[str, UUID]] = {}
        for artifact_link in self.artifact_links:
            if not artifact_link.artifact:
                continue
            artifact = artifact_link.artifact
            if artifact_link.is_model_artifact:
                model_artifact_ids.setdefault(artifact.name, {}).update(
                    {str(artifact.version): artifact.id}
                )
            elif artifact_link.is_endpoint_artifact:
                endpoint_artifact_ids.setdefault(artifact.name, {}).update(
                    {str(artifact.version): artifact.id}
                )
            else:
                data_artifact_ids.setdefault(artifact.name, {}).update(
                    {str(artifact.version): artifact.id}
                )

        # Construct {name: id} dict for all linked pipeline runs
        pipeline_run_ids: Dict[str, UUID] = {}
        for pipeline_run_link in self.pipeline_run_links:
            if not pipeline_run_link.pipeline_run:
                continue
            pipeline_run = pipeline_run_link.pipeline_run
            pipeline_run_ids[pipeline_run.name] = pipeline_run.id

        return ModelVersionResponseModel(
            id=self.id,
            user=self.user.to_model() if self.user else None,
            workspace=self.workspace.to_model(),
            created=self.created,
            updated=self.updated,
            model=self.model.to_model(),
            name=self.name,
            number=self.number,
            description=self.description,
            stage=self.stage,
            model_artifact_ids=model_artifact_ids,
            endpoint_artifact_ids=endpoint_artifact_ids,
            data_artifact_ids=data_artifact_ids,
            pipeline_run_ids=pipeline_run_ids,
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


class ModelVersionArtifactSchema(BaseSchema, table=True):
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
    artifact_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ArtifactSchema.__tablename__,
        source_column="artifact_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    artifact: "ArtifactSchema" = Relationship(
        back_populates="model_versions_artifacts_links"
    )

    is_model_artifact: bool = Field(sa_column=Column(BOOLEAN, nullable=True))
    is_endpoint_artifact: bool = Field(
        sa_column=Column(BOOLEAN, nullable=True)
    )

    @classmethod
    def from_request(
        cls,
        model_version_artifact_request: ModelVersionArtifactRequestModel,
    ) -> "ModelVersionArtifactSchema":
        """Convert an `ModelVersionArtifactRequestModel` to a `ModelVersionArtifactSchema`.

        Args:
            model_version_artifact_request: The request link to convert.

        Returns:
            The converted schema.
        """
        return cls(
            workspace_id=model_version_artifact_request.workspace,
            user_id=model_version_artifact_request.user,
            model_id=model_version_artifact_request.model,
            model_version_id=model_version_artifact_request.model_version,
            artifact_id=model_version_artifact_request.artifact,
            is_model_artifact=model_version_artifact_request.is_model_artifact,
            is_endpoint_artifact=model_version_artifact_request.is_endpoint_artifact,
        )

    def to_model(
        self,
        hydrate: bool = False,
    ) -> ModelVersionArtifactResponseModel:
        """Convert an `ModelVersionArtifactSchema` to an `ModelVersionArtifactResponseModel`.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The created `ModelVersionArtifactResponseModel`.
        """
        return ModelVersionArtifactResponseModel(
            id=self.id,
            user=self.user.to_model() if self.user else None,
            workspace=self.workspace.to_model(),
            created=self.created,
            updated=self.updated,
            model=self.model_id,
            model_version=self.model_version_id,
            artifact=self.artifact.to_model(),
            is_model_artifact=self.is_model_artifact,
            is_endpoint_artifact=self.is_endpoint_artifact,
        )


class ModelVersionPipelineRunSchema(BaseSchema, table=True):
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
    pipeline_run_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=PipelineRunSchema.__tablename__,
        source_column="pipeline_run_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    pipeline_run: "PipelineRunSchema" = Relationship(
        back_populates="model_versions_pipeline_runs_links"
    )

    @classmethod
    def from_request(
        cls,
        model_version_pipeline_run_request: ModelVersionPipelineRunRequestModel,
    ) -> "ModelVersionPipelineRunSchema":
        """Convert an `ModelVersionPipelineRunRequestModel` to an `ModelVersionPipelineRunSchema`.

        Args:
            model_version_pipeline_run_request: The request link to convert.

        Returns:
            The converted schema.
        """
        return cls(
            workspace_id=model_version_pipeline_run_request.workspace,
            user_id=model_version_pipeline_run_request.user,
            model_id=model_version_pipeline_run_request.model,
            model_version_id=model_version_pipeline_run_request.model_version,
            pipeline_run_id=model_version_pipeline_run_request.pipeline_run,
        )

    def to_model(
        self,
        hydrate: bool = False,
    ) -> ModelVersionPipelineRunResponseModel:
        """Convert an `ModelVersionPipelineRunSchema` to an `ModelVersionPipelineRunResponseModel`.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The created `ModelVersionPipelineRunResponseModel`.
        """
        return ModelVersionPipelineRunResponseModel(
            id=self.id,
            user=self.user.to_model() if self.user else None,
            workspace=self.workspace.to_model(),
            created=self.created,
            updated=self.updated,
            model=self.model_id,
            model_version=self.model_version_id,
            pipeline_run=self.pipeline_run.to_model(),
        )
