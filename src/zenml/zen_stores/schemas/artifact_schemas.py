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
"""SQLModel implementation of artifact table."""

from typing import TYPE_CHECKING, Any, List, Optional, Sequence, Tuple
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import TEXT, Column, UniqueConstraint
from sqlalchemy.orm import joinedload, object_session
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship, asc, col, desc, select

from zenml.config.source import Source
from zenml.enums import (
    ArtifactSaveType,
    ArtifactType,
    ExecutionStatus,
    MetadataResourceTypes,
    TaggableResourceTypes,
)
from zenml.models import (
    ArtifactResponse,
    ArtifactResponseBody,
    ArtifactResponseMetadata,
    ArtifactResponseResources,
    ArtifactUpdate,
    ArtifactVersionRequest,
    ArtifactVersionResponse,
    ArtifactVersionResponseBody,
    ArtifactVersionResponseMetadata,
    ArtifactVersionResponseResources,
    ArtifactVersionUpdate,
)
from zenml.models.v2.core.artifact import ArtifactRequest
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import BaseSchema, NamedSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import (
    RunMetadataInterface,
    jl_arg,
)

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.artifact_visualization_schemas import (
        ArtifactVisualizationSchema,
    )
    from zenml.zen_stores.schemas.model_schemas import (
        ModelVersionArtifactSchema,
    )
    from zenml.zen_stores.schemas.run_metadata_schemas import RunMetadataSchema
    from zenml.zen_stores.schemas.step_run_schemas import (
        StepRunInputArtifactSchema,
        StepRunOutputArtifactSchema,
    )
    from zenml.zen_stores.schemas.tag_schemas import TagSchema


class ArtifactSchema(NamedSchema, table=True):
    """SQL Model for artifacts."""

    __tablename__ = "artifact"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "project_id",
            name="unique_artifact_name_in_project",
        ),
    )

    # Fields
    has_custom_name: bool
    versions: List["ArtifactVersionSchema"] = Relationship(
        back_populates="artifact",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    tags: List["TagSchema"] = Relationship(
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(foreign(TagResourceSchema.resource_type)=='{TaggableResourceTypes.ARTIFACT.value}', foreign(TagResourceSchema.resource_id)==ArtifactSchema.id)",
            secondary="tag_resource",
            secondaryjoin="TagSchema.id == foreign(TagResourceSchema.tag_id)",
            order_by="TagSchema.name",
            overlaps="tags",
        ),
    )

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    project: "ProjectSchema" = Relationship()

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(
        back_populates="artifacts",
    )

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
        options = []

        if include_resources:
            options.extend(
                [
                    joinedload(jl_arg(ArtifactSchema.user)),
                    # joinedload(jl_arg(ArtifactSchema.tags)),
                ]
            )

        return options

    @property
    def latest_version(self) -> Optional["ArtifactVersionSchema"]:
        """Fetch the latest version for this artifact.

        Raises:
            RuntimeError: If no session for the schema exists.

        Returns:
            The latest version for this artifact.
        """
        if session := object_session(self):
            return (
                session.execute(
                    select(ArtifactVersionSchema)
                    .where(ArtifactVersionSchema.artifact_id == self.id)
                    .order_by(desc(ArtifactVersionSchema.created))
                    .limit(1)
                )
                .scalars()
                .one_or_none()
            )
        else:
            raise RuntimeError(
                "Missing DB session to fetch latest version for artifact."
            )

    @classmethod
    def from_request(
        cls,
        artifact_request: ArtifactRequest,
    ) -> "ArtifactSchema":
        """Convert an `ArtifactRequest` to an `ArtifactSchema`.

        Args:
            artifact_request: The request model to convert.

        Returns:
            The converted schema.
        """
        return cls(
            name=artifact_request.name,
            has_custom_name=artifact_request.has_custom_name,
            project_id=artifact_request.project,
            user_id=artifact_request.user,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> ArtifactResponse:
        """Convert an `ArtifactSchema` to an `ArtifactResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic



        Returns:
            The created `ArtifactResponse`.
        """
        # Create the body of the model
        body = ArtifactResponseBody(
            user_id=self.user_id,
            project_id=self.project_id,
            created=self.created,
            updated=self.updated,
        )

        # Create the metadata of the model
        metadata = None
        if include_metadata:
            metadata = ArtifactResponseMetadata(
                has_custom_name=self.has_custom_name,
            )

        resources = None
        if include_resources:
            latest_id, latest_name = None, None
            if latest_version := self.latest_version:
                latest_id = latest_version.id
                latest_name = latest_version.version

            resources = ArtifactResponseResources(
                user=self.user.to_model() if self.user else None,
                tags=[tag.to_model() for tag in self.tags],
                latest_version_id=latest_id,
                latest_version_name=latest_name,
            )

        return ArtifactResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )

    def update(self, artifact_update: ArtifactUpdate) -> "ArtifactSchema":
        """Update an `ArtifactSchema` with an `ArtifactUpdate`.

        Args:
            artifact_update: The update model to apply.

        Returns:
            The updated `ArtifactSchema`.
        """
        self.updated = utc_now()
        if artifact_update.name:
            self.name = artifact_update.name
            self.has_custom_name = True
        if artifact_update.has_custom_name is not None:
            self.has_custom_name = artifact_update.has_custom_name
        return self


class ArtifactVersionSchema(BaseSchema, RunMetadataInterface, table=True):
    """SQL Model for artifact versions."""

    __tablename__ = "artifact_version"
    __table_args__ = (
        UniqueConstraint(
            "version",
            "artifact_id",
            name="unique_version_for_artifact_id",
        ),
    )

    # Fields
    version: str
    version_number: Optional[int]
    type: str
    uri: str = Field(sa_column=Column(TEXT, nullable=False))
    materializer: str = Field(sa_column=Column(TEXT, nullable=False))
    data_type: str = Field(sa_column=Column(TEXT, nullable=False))
    tags: List["TagSchema"] = Relationship(
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(foreign(TagResourceSchema.resource_type)=='{TaggableResourceTypes.ARTIFACT_VERSION.value}', foreign(TagResourceSchema.resource_id)==ArtifactVersionSchema.id)",
            secondary="tag_resource",
            secondaryjoin="TagSchema.id == foreign(TagResourceSchema.tag_id)",
            order_by="TagSchema.name",
            overlaps="tags",
        ),
    )
    save_type: str = Field(sa_column=Column(TEXT, nullable=False))

    # Foreign keys
    artifact_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ArtifactSchema.__tablename__,
        source_column="artifact_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    artifact_store_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackComponentSchema.__tablename__,
        source_column="artifact_store_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )

    # Relationships
    artifact: "ArtifactSchema" = Relationship(back_populates="versions")
    user: Optional["UserSchema"] = Relationship(
        back_populates="artifact_versions"
    )
    project: "ProjectSchema" = Relationship(back_populates="artifact_versions")
    run_metadata: List["RunMetadataSchema"] = Relationship(
        sa_relationship_kwargs=dict(
            secondary="run_metadata_resource",
            primaryjoin=f"and_(foreign(RunMetadataResourceSchema.resource_type)=='{MetadataResourceTypes.ARTIFACT_VERSION.value}', foreign(RunMetadataResourceSchema.resource_id)==ArtifactVersionSchema.id)",
            secondaryjoin="RunMetadataSchema.id==foreign(RunMetadataResourceSchema.run_metadata_id)",
            overlaps="run_metadata",
        ),
    )
    visualizations: List["ArtifactVisualizationSchema"] = Relationship(
        back_populates="artifact_version",
        sa_relationship_kwargs={"cascade": "delete"},
    )

    # Needed for cascade deletion behavior
    model_versions_artifacts_links: List["ModelVersionArtifactSchema"] = (
        Relationship(
            back_populates="artifact_version",
            sa_relationship_kwargs={"cascade": "delete"},
        )
    )
    output_of_step_runs: List["StepRunOutputArtifactSchema"] = Relationship(
        back_populates="artifact_version",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    input_of_step_runs: List["StepRunInputArtifactSchema"] = Relationship(
        back_populates="artifact_version",
        sa_relationship_kwargs={"cascade": "delete"},
    )

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
        options = []

        # if include_metadata:
        #     options.extend(
        #         [
        #             joinedload(jl_arg(ArtifactVersionSchema.visualizations)),
        #             joinedload(jl_arg(ArtifactVersionSchema.run_metadata)),
        #         ]
        #     )

        if include_resources:
            options.extend(
                [
                    joinedload(jl_arg(ArtifactVersionSchema.user)),
                    # joinedload(jl_arg(ArtifactVersionSchema.tags)),
                ]
            )

        return options

    @property
    def producer_run_ids(self) -> Optional[Tuple[UUID, UUID]]:
        """Fetch the producer run IDs for this artifact version.

        Raises:
            RuntimeError: If no session for the schema exists.

        Returns:
            The producer step run ID and pipeline run ID for this artifact
            version.
        """
        from zenml.zen_stores.schemas import (
            StepRunOutputArtifactSchema,
            StepRunSchema,
        )

        if session := object_session(self):
            row = session.execute(
                select(StepRunSchema.id, StepRunSchema.pipeline_run_id)
                .join(
                    StepRunOutputArtifactSchema,
                    col(StepRunOutputArtifactSchema.step_id)
                    == col(StepRunSchema.id),
                )
                .where(col(StepRunOutputArtifactSchema.artifact_id) == self.id)
                .where(
                    col(StepRunSchema.status)
                    == ExecutionStatus.COMPLETED.value
                )
                # Fetch the oldest step run
                .order_by(asc(StepRunSchema.created))
                .limit(1)
            ).one_or_none()

            return (row[0], row[1]) if row else None
        else:
            raise RuntimeError(
                "Missing DB session to fetch producer run for artifact version."
            )

    @classmethod
    def from_request(
        cls,
        artifact_version_request: ArtifactVersionRequest,
    ) -> "ArtifactVersionSchema":
        """Convert an `ArtifactVersionRequest` to an `ArtifactVersionSchema`.

        Args:
            artifact_version_request: The request model to convert.

        Raises:
            ValueError: If the request does not specify a version number.

        Returns:
            The converted schema.
        """
        if not artifact_version_request.version:
            raise ValueError("Missing version for artifact version request.")

        try:
            version_number = int(artifact_version_request.version)
        except ValueError:
            version_number = None
        return cls(
            artifact_id=artifact_version_request.artifact_id,
            version=str(artifact_version_request.version),
            version_number=version_number,
            artifact_store_id=artifact_version_request.artifact_store_id,
            project_id=artifact_version_request.project,
            user_id=artifact_version_request.user,
            type=artifact_version_request.type.value,
            uri=artifact_version_request.uri,
            materializer=artifact_version_request.materializer.model_dump_json(),
            data_type=artifact_version_request.data_type.model_dump_json(),
            save_type=artifact_version_request.save_type.value,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> ArtifactVersionResponse:
        """Convert an `ArtifactVersionSchema` to an `ArtifactVersionResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic



        Returns:
            The created `ArtifactVersionResponse`.
        """
        try:
            materializer = Source.model_validate_json(self.materializer)
        except ValidationError:
            # This is an old source which was an importable source path
            materializer = Source.from_import_path(self.materializer)

        try:
            data_type = Source.model_validate_json(self.data_type)
        except ValidationError:
            # This is an old source which was an importable source path
            data_type = Source.from_import_path(self.data_type)

        # Create the body of the model
        artifact = self.artifact.to_model()
        body = ArtifactVersionResponseBody(
            user_id=self.user_id,
            project_id=self.project_id,
            artifact=artifact,
            version=self.version or str(self.version_number),
            uri=self.uri,
            type=ArtifactType(self.type),
            materializer=materializer,
            data_type=data_type,
            created=self.created,
            updated=self.updated,
            save_type=ArtifactSaveType(self.save_type),
            artifact_store_id=self.artifact_store_id,
        )

        # Create the metadata of the model
        metadata = None
        if include_metadata:
            metadata = ArtifactVersionResponseMetadata(
                visualizations=[v.to_model() for v in self.visualizations],
                run_metadata=self.fetch_metadata(),
            )

        resources = None
        if include_resources:
            producer_step_run_id, producer_pipeline_run_id = None, None
            if producer_run_ids := self.producer_run_ids:
                # TODO: Why was the producer_pipeline_run_id only set for one
                # of the cases before?
                producer_step_run_id, producer_pipeline_run_id = (
                    producer_run_ids
                )

            resources = ArtifactVersionResponseResources(
                user=self.user.to_model() if self.user else None,
                tags=[tag.to_model() for tag in self.tags],
                producer_step_run_id=producer_step_run_id,
                producer_pipeline_run_id=producer_pipeline_run_id,
            )

        return ArtifactVersionResponse(
            id=self.id,
            body=body,
            metadata=metadata,
            resources=resources,
        )

    def update(
        self, artifact_version_update: ArtifactVersionUpdate
    ) -> "ArtifactVersionSchema":
        """Update an `ArtifactVersionSchema` with an `ArtifactVersionUpdate`.

        Args:
            artifact_version_update: The update model to apply.

        Returns:
            The updated `ArtifactVersionSchema`.
        """
        self.updated = utc_now()
        return self
