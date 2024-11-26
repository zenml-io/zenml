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
"""SQLModel implementation of step run tables."""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from pydantic import ConfigDict
from sqlalchemy import TEXT, Column, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlmodel import Field, Relationship, SQLModel

from zenml.config.step_configurations import Step
from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.enums import (
    ExecutionStatus,
    MetadataResourceTypes,
    StepRunInputArtifactType,
)
from zenml.metadata.metadata_types import MetadataType
from zenml.models import (
    RunMetadataEntry,
    StepRunRequest,
    StepRunResponse,
    StepRunResponseBody,
    StepRunResponseMetadata,
    StepRunUpdate,
)
from zenml.models.v2.core.artifact_version import ArtifactVersionResponse
from zenml.models.v2.core.step_run import (
    StepRunInputResponse,
    StepRunResponseResources,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.constants import MODEL_VERSION_TABLENAME
from zenml.zen_stores.schemas.pipeline_deployment_schemas import (
    PipelineDeploymentSchema,
)
from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.artifact_schemas import ArtifactVersionSchema
    from zenml.zen_stores.schemas.logs_schemas import LogsSchema
    from zenml.zen_stores.schemas.model_schemas import ModelVersionSchema
    from zenml.zen_stores.schemas.run_metadata_schemas import (
        RunMetadataResourceSchema,
    )


class StepRunSchema(NamedSchema, table=True):
    """SQL Model for steps of pipeline runs."""

    __tablename__ = "step_run"

    # Fields
    start_time: Optional[datetime] = Field(nullable=True)
    end_time: Optional[datetime] = Field(nullable=True)
    status: str = Field(nullable=False)

    docstring: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    cache_key: Optional[str] = Field(nullable=True)
    source_code: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    code_hash: Optional[str] = Field(nullable=True)

    step_configuration: str = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=True,
        )
    )

    # Foreign keys
    original_step_run_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=__tablename__,
        source_column="original_step_run_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    deployment_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=PipelineDeploymentSchema.__tablename__,
        source_column="deployment_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    pipeline_run_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=PipelineRunSchema.__tablename__,  # type: ignore[has-type]
        source_column="pipeline_run_id",
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
    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    model_version_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=MODEL_VERSION_TABLENAME,
        source_column="model_version_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )

    # Relationships
    workspace: "WorkspaceSchema" = Relationship(back_populates="step_runs")
    user: Optional["UserSchema"] = Relationship(back_populates="step_runs")
    deployment: Optional["PipelineDeploymentSchema"] = Relationship(
        back_populates="step_runs"
    )
    run_metadata_resources: List["RunMetadataResourceSchema"] = Relationship(
        back_populates="step_run",
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(RunMetadataResourceSchema.resource_type=='{MetadataResourceTypes.STEP_RUN.value}', foreign(RunMetadataResourceSchema.resource_id)==StepRunSchema.id)",
            cascade="delete",
            overlaps="run_metadata_resources",
        ),
    )
    input_artifacts: List["StepRunInputArtifactSchema"] = Relationship(
        sa_relationship_kwargs={"cascade": "delete"}
    )
    output_artifacts: List["StepRunOutputArtifactSchema"] = Relationship(
        sa_relationship_kwargs={"cascade": "delete"}
    )
    logs: Optional["LogsSchema"] = Relationship(
        back_populates="step_run",
        sa_relationship_kwargs={"cascade": "delete", "uselist": False},
    )
    parents: List["StepRunParentsSchema"] = Relationship(
        sa_relationship_kwargs={
            "cascade": "delete",
            "primaryjoin": "StepRunParentsSchema.child_id == StepRunSchema.id",
        },
    )
    model_version: "ModelVersionSchema" = Relationship(
        back_populates="step_runs",
    )
    original_step_run: Optional["StepRunSchema"] = Relationship(
        sa_relationship_kwargs={"remote_side": "StepRunSchema.id"}
    )

    model_config = ConfigDict(protected_namespaces=())  # type: ignore[assignment]

    @classmethod
    def from_request(cls, request: StepRunRequest) -> "StepRunSchema":
        """Create a step run schema from a step run request model.

        Args:
            request: The step run request model.

        Returns:
            The step run schema.
        """
        return cls(
            name=request.name,
            workspace_id=request.workspace,
            user_id=request.user,
            start_time=request.start_time,
            end_time=request.end_time,
            status=request.status.value,
            original_step_run_id=request.original_step_run_id,
            pipeline_run_id=request.pipeline_run_id,
            deployment_id=request.deployment,
            docstring=request.docstring,
            cache_key=request.cache_key,
            code_hash=request.code_hash,
            source_code=request.source_code,
            model_version_id=request.model_version_id,
        )

    def fetch_metadata_collection(self) -> Dict[str, List[RunMetadataEntry]]:
        """Fetches all the metadata entries related to the step run.

        Returns:
            a dictionary, where the key is the key of the metadata entry
                and the values represent the list of entries with this key.
        """
        metadata_collection: Dict[str, List[RunMetadataEntry]] = {}

        # Fetch the metadata related to this step
        for rm in self.run_metadata_resources:
            if rm.run_metadata.key not in metadata_collection:
                metadata_collection[rm.run_metadata.key] = []
            metadata_collection[rm.run_metadata.key].append(
                RunMetadataEntry(
                    value=json.loads(rm.run_metadata.value),
                    created=rm.run_metadata.created,
                )
            )

        return metadata_collection

    def fetch_metadata(self) -> Dict[str, MetadataType]:
        """Fetches the latest metadata entry related to the step run.

        Returns:
            a dictionary, where the key is the key of the metadata entry
                and the values represent the latest entry with this key.
        """
        metadata_collection = self.fetch_metadata_collection()
        return {
            k: sorted(v, key=lambda x: x.created, reverse=True)[0].value
            for k, v in metadata_collection.items()
        }

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> StepRunResponse:
        """Convert a `StepRunSchema` to a `StepRunResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The created StepRunResponse.

        Raises:
            ValueError: In case the step run configuration can not be loaded.
            RuntimeError: If the step run schema does not have a deployment_id
                or a step_configuration.
        """
        run_metadata = self.fetch_metadata()

        input_artifacts = {
            artifact.name: StepRunInputResponse(
                input_type=StepRunInputArtifactType(artifact.type),
                **artifact.artifact_version.to_model().model_dump(),
            )
            for artifact in self.input_artifacts
        }

        output_artifacts: Dict[str, List["ArtifactVersionResponse"]] = {}
        for artifact in self.output_artifacts:
            if artifact.name not in output_artifacts:
                output_artifacts[artifact.name] = []
            output_artifacts[artifact.name].append(
                artifact.artifact_version.to_model()
            )

        full_step_config = None
        if self.deployment is not None:
            step_configuration = json.loads(
                self.deployment.step_configurations
            )
            if self.name in step_configuration:
                full_step_config = Step.model_validate(
                    step_configuration[self.name]
                )
            elif not self.step_configuration:
                raise ValueError(
                    f"Unable to load the configuration for step `{self.name}` from the"
                    f"database. To solve this please delete the pipeline run that this"
                    f"step run belongs to. Pipeline Run ID: `{self.pipeline_run_id}`."
                )

        # the step configuration moved into the deployment - the following case is to ensure
        # backwards compatibility
        if full_step_config is None:
            if self.step_configuration:
                full_step_config = Step.model_validate_json(
                    self.step_configuration
                )
            else:
                raise RuntimeError(
                    "Step run model creation has failed. Each step run entry "
                    "should either have a deployment_id or step_configuration."
                )

        body = StepRunResponseBody(
            user=self.user.to_model() if self.user else None,
            status=ExecutionStatus(self.status),
            start_time=self.start_time,
            end_time=self.end_time,
            inputs=input_artifacts,
            outputs=output_artifacts,
            created=self.created,
            updated=self.updated,
            model_version_id=self.model_version_id,
        )
        metadata = None
        if include_metadata:
            metadata = StepRunResponseMetadata(
                workspace=self.workspace.to_model(),
                config=full_step_config.config,
                spec=full_step_config.spec,
                cache_key=self.cache_key,
                code_hash=self.code_hash,
                docstring=self.docstring,
                source_code=self.source_code,
                logs=self.logs.to_model() if self.logs else None,
                deployment_id=self.deployment_id,
                pipeline_run_id=self.pipeline_run_id,
                original_step_run_id=self.original_step_run_id,
                parent_step_ids=[p.parent_id for p in self.parents],
                run_metadata=run_metadata,
            )

        resources = None
        if include_resources:
            model_version = None
            if self.model_version:
                model_version = self.model_version.to_model()

            resources = StepRunResponseResources(model_version=model_version)

        return StepRunResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )

    def update(self, step_update: "StepRunUpdate") -> "StepRunSchema":
        """Update a step run schema with a step run update model.

        Args:
            step_update: The step run update model.

        Returns:
            The updated step run schema.
        """
        for key, value in step_update.model_dump(
            exclude_unset=True, exclude_none=True
        ).items():
            if key == "status":
                self.status = value.value
            if key == "end_time":
                self.end_time = value
            if key == "model_version_id":
                if value and self.model_version_id is None:
                    self.model_version_id = value

        self.updated = datetime.utcnow()

        return self


class StepRunParentsSchema(SQLModel, table=True):
    """SQL Model that defines the order of steps."""

    __tablename__ = "step_run_parents"

    # Foreign Keys
    parent_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="parent_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )
    child_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="child_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )


class StepRunInputArtifactSchema(SQLModel, table=True):
    """SQL Model that defines which artifacts are inputs to which step."""

    __tablename__ = "step_run_input_artifact"

    # Fields
    name: str = Field(nullable=False, primary_key=True)
    type: str

    # Foreign keys
    step_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="step_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )
    # Note: We keep the name artifact_id instead of artifact_version_id here to
    # avoid having to drop and recreate the primary key constraint.
    artifact_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="artifact_version",
        source_column="artifact_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )

    # Relationships
    step_run: "StepRunSchema" = Relationship(back_populates="input_artifacts")
    artifact_version: "ArtifactVersionSchema" = Relationship()


class StepRunOutputArtifactSchema(SQLModel, table=True):
    """SQL Model that defines which artifacts are outputs of which step."""

    __tablename__ = "step_run_output_artifact"

    # Fields
    name: str

    # Foreign keys
    step_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="step_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )
    # Note: we keep the name artifact_id instead of artifact_version_id here to
    # avoid having to drop and recreate the primary key constraint.
    artifact_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="artifact_version",
        source_column="artifact_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )

    # Relationship
    step_run: "StepRunSchema" = Relationship(back_populates="output_artifacts")
    artifact_version: "ArtifactVersionSchema" = Relationship(
        back_populates="output_of_step_runs"
    )
