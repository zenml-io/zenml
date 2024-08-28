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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast
from uuid import UUID

from pydantic import ConfigDict
from sqlalchemy import BOOLEAN, INTEGER, TEXT, Column
from sqlmodel import Field, Relationship

from zenml.enums import MetadataResourceTypes, TaggableResourceTypes
from zenml.models import (
    BaseResponseMetadata,
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
    ModelVersionResponseResources,
    Page,
)
from zenml.zen_stores.schemas.artifact_schemas import ArtifactVersionSchema
from zenml.zen_stores.schemas.base_schemas import BaseSchema, NamedSchema
from zenml.zen_stores.schemas.constants import MODEL_VERSION_TABLENAME
from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
from zenml.zen_stores.schemas.run_metadata_schemas import RunMetadataSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.tag_schemas import TagResourceSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import get_page_from_list
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import ServiceSchema, StepRunSchema


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
    save_models_to_registry: bool = Field(
        sa_column=Column(BOOLEAN, nullable=False)
    )
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
            save_models_to_registry=model_request.save_models_to_registry,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> ModelResponse:
        """Convert an `ModelSchema` to an `ModelResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The created `ModelResponse`.
        """
        tags = [t.tag.to_model() for t in self.tags]

        if self.model_versions:
            version_numbers = [mv.number for mv in self.model_versions]
            latest_version_idx = version_numbers.index(max(version_numbers))
            latest_version_name = self.model_versions[latest_version_idx].name
            latest_version_id = self.model_versions[latest_version_idx].id
        else:
            latest_version_name = None
            latest_version_id = None

        metadata = None
        if include_metadata:
            metadata = ModelResponseMetadata(
                workspace=self.workspace.to_model(),
                license=self.license,
                description=self.description,
                audience=self.audience,
                use_cases=self.use_cases,
                limitations=self.limitations,
                trade_offs=self.trade_offs,
                ethics=self.ethics,
                save_models_to_registry=self.save_models_to_registry,
            )

        body = ModelResponseBody(
            user=self.user.to_model() if self.user else None,
            created=self.created,
            updated=self.updated,
            tags=tags,
            latest_version_name=latest_version_name,
            latest_version_id=latest_version_id,
        )

        return ModelResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
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
        for field, value in model_update.model_dump(
            exclude_unset=True, exclude_none=True
        ).items():
            setattr(self, field, value)
        self.updated = datetime.utcnow()
        return self


class ModelVersionSchema(NamedSchema, table=True):
    """SQL Model for model version."""

    __tablename__ = MODEL_VERSION_TABLENAME

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
    tags: List["TagResourceSchema"] = Relationship(
        back_populates="model_version",
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(TagResourceSchema.resource_type=='{TaggableResourceTypes.MODEL_VERSION.value}', foreign(TagResourceSchema.resource_id)==ModelVersionSchema.id)",
            cascade="delete",
            overlaps="tags",
        ),
    )

    services: List["ServiceSchema"] = Relationship(
        back_populates="model_version",
    )

    number: int = Field(sa_column=Column(INTEGER, nullable=False))
    description: str = Field(sa_column=Column(TEXT, nullable=True))
    stage: str = Field(sa_column=Column(TEXT, nullable=True))

    run_metadata: List["RunMetadataSchema"] = Relationship(
        back_populates="model_version",
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(RunMetadataSchema.resource_type=='{MetadataResourceTypes.MODEL_VERSION.value}', foreign(RunMetadataSchema.resource_id)==ModelVersionSchema.id)",
            cascade="delete",
            overlaps="run_metadata",
        ),
    )
    pipeline_runs: List["PipelineRunSchema"] = Relationship(
        back_populates="model_version"
    )
    step_runs: List["StepRunSchema"] = Relationship(
        back_populates="model_version"
    )

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())  # type: ignore[assignment]

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
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> ModelVersionResponse:
        """Convert an `ModelVersionSchema` to an `ModelVersionResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The created `ModelVersionResponse`.
        """
        from zenml.models import ServiceResponse

        # Construct {name: {version: id}} dicts for all linked artifacts
        model_artifact_ids: Dict[str, Dict[str, UUID]] = {}
        deployment_artifact_ids: Dict[str, Dict[str, UUID]] = {}
        data_artifact_ids: Dict[str, Dict[str, UUID]] = {}
        for artifact_link in self.artifact_links:
            if not artifact_link.artifact_version:
                continue
            artifact_name = artifact_link.artifact_version.artifact.name
            artifact_version = str(artifact_link.artifact_version.version)
            artifact_version_id = artifact_link.artifact_version.id
            if artifact_link.is_model_artifact:
                model_artifact_ids.setdefault(artifact_name, {}).update(
                    {str(artifact_version): artifact_version_id}
                )
            elif artifact_link.is_deployment_artifact:
                deployment_artifact_ids.setdefault(artifact_name, {}).update(
                    {str(artifact_version): artifact_version_id}
                )
            else:
                data_artifact_ids.setdefault(artifact_name, {}).update(
                    {str(artifact_version): artifact_version_id}
                )

        # Construct {name: id} dict for all linked pipeline runs
        pipeline_run_ids: Dict[str, UUID] = {}
        for pipeline_run_link in self.pipeline_run_links:
            if not pipeline_run_link.pipeline_run:
                continue
            pipeline_run = pipeline_run_link.pipeline_run
            pipeline_run_ids[pipeline_run.name] = pipeline_run.id

        metadata = None
        if include_metadata:
            metadata = ModelVersionResponseMetadata(
                workspace=self.workspace.to_model(),
                description=self.description,
                run_metadata={
                    rm.key: rm.to_model(include_metadata=True)
                    for rm in self.run_metadata
                },
            )

        resources = None
        if include_resources:
            services = cast(
                Page[ServiceResponse],
                get_page_from_list(
                    items_list=self.services,
                    response_model=ServiceResponse,
                    include_resources=include_resources,
                    include_metadata=include_metadata,
                ),
            )
            resources = ModelVersionResponseResources(
                services=services,
            )

        body = ModelVersionResponseBody(
            user=self.user.to_model() if self.user else None,
            created=self.created,
            updated=self.updated,
            stage=self.stage,
            number=self.number,
            model=self.model.to_model(),
            model_artifact_ids=model_artifact_ids,
            data_artifact_ids=data_artifact_ids,
            deployment_artifact_ids=deployment_artifact_ids,
            pipeline_run_ids=pipeline_run_ids,
            tags=[t.tag.to_model() for t in self.tags],
        )

        return ModelVersionResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )

    def update(
        self,
        target_stage: Optional[str] = None,
        target_name: Optional[str] = None,
        target_description: Optional[str] = None,
    ) -> "ModelVersionSchema":
        """Updates a `ModelVersionSchema` to a target stage.

        Args:
            target_stage: The stage to be updated.
            target_name: The version name to be updated.
            target_description: The version description to be updated.

        Returns:
            The updated `ModelVersionSchema`.
        """
        if target_stage is not None:
            self.stage = target_stage
        if target_name is not None:
            self.name = target_name
        if target_description is not None:
            self.description = target_description
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
    artifact_version_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ArtifactVersionSchema.__tablename__,
        source_column="artifact_version_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    artifact_version: "ArtifactVersionSchema" = Relationship(
        back_populates="model_versions_artifacts_links"
    )

    is_model_artifact: bool = Field(sa_column=Column(BOOLEAN, nullable=True))
    is_deployment_artifact: bool = Field(
        sa_column=Column(BOOLEAN, nullable=True)
    )

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())  # type: ignore[assignment]

    @classmethod
    def from_request(
        cls,
        model_version_artifact_request: ModelVersionArtifactRequest,
    ) -> "ModelVersionArtifactSchema":
        """Convert an `ModelVersionArtifactRequest` to a `ModelVersionArtifactSchema`.

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
            artifact_version_id=model_version_artifact_request.artifact_version,
            is_model_artifact=model_version_artifact_request.is_model_artifact,
            is_deployment_artifact=model_version_artifact_request.is_deployment_artifact,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> ModelVersionArtifactResponse:
        """Convert an `ModelVersionArtifactSchema` to an `ModelVersionArtifactResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The created `ModelVersionArtifactResponseModel`.
        """
        return ModelVersionArtifactResponse(
            id=self.id,
            body=ModelVersionArtifactResponseBody(
                created=self.created,
                updated=self.updated,
                model=self.model_id,
                model_version=self.model_version_id,
                artifact_version=self.artifact_version.to_model(),
                is_model_artifact=self.is_model_artifact,
                is_deployment_artifact=self.is_deployment_artifact,
            ),
            metadata=BaseResponseMetadata() if include_metadata else None,
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

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())  # type: ignore[assignment]

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
            model_id=model_version_pipeline_run_request.model,
            model_version_id=model_version_pipeline_run_request.model_version,
            pipeline_run_id=model_version_pipeline_run_request.pipeline_run,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> ModelVersionPipelineRunResponse:
        """Convert an `ModelVersionPipelineRunSchema` to an `ModelVersionPipelineRunResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The created `ModelVersionPipelineRunResponse`.
        """
        return ModelVersionPipelineRunResponse(
            id=self.id,
            body=ModelVersionPipelineRunResponseBody(
                created=self.created,
                updated=self.updated,
                model=self.model_id,
                model_version=self.model_version_id,
                pipeline_run=self.pipeline_run.to_model(),
            ),
            metadata=BaseResponseMetadata() if include_metadata else None,
        )
