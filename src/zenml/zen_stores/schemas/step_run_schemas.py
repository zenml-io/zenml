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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence
from uuid import UUID

from pydantic import ConfigDict
from sqlalchemy import TEXT, Column, String, UniqueConstraint
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship, SQLModel

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step
from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.enums import (
    ExecutionStatus,
    MetadataResourceTypes,
    StepRunInputArtifactType,
)
from zenml.models import (
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
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.constants import MODEL_VERSION_TABLENAME
from zenml.zen_stores.schemas.pipeline_deployment_schemas import (
    PipelineDeploymentSchema,
)
from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import (
    RunMetadataInterface,
    jl_arg,
)

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.artifact_schemas import ArtifactVersionSchema
    from zenml.zen_stores.schemas.logs_schemas import LogsSchema
    from zenml.zen_stores.schemas.model_schemas import ModelVersionSchema
    from zenml.zen_stores.schemas.run_metadata_schemas import RunMetadataSchema


class StepRunSchema(NamedSchema, RunMetadataInterface, table=True):
    """SQL Model for steps of pipeline runs."""

    __tablename__ = "step_run"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "pipeline_run_id",
            name="unique_step_name_for_pipeline_run",
        ),
    )

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
    deployment_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineDeploymentSchema.__tablename__,
        source_column="deployment_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    pipeline_run_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=PipelineRunSchema.__tablename__,
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
    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    model_version_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=MODEL_VERSION_TABLENAME,
        source_column="model_version_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )

    # Relationships
    project: "ProjectSchema" = Relationship(back_populates="step_runs")
    user: Optional["UserSchema"] = Relationship(back_populates="step_runs")
    deployment: Optional["PipelineDeploymentSchema"] = Relationship(
        back_populates="step_runs"
    )
    run_metadata: List["RunMetadataSchema"] = Relationship(
        sa_relationship_kwargs=dict(
            secondary="run_metadata_resource",
            primaryjoin=f"and_(foreign(RunMetadataResourceSchema.resource_type)=='{MetadataResourceTypes.STEP_RUN.value}', foreign(RunMetadataResourceSchema.resource_id)==StepRunSchema.id)",
            secondaryjoin="RunMetadataSchema.id==foreign(RunMetadataResourceSchema.run_metadata_id)",
            overlaps="run_metadata",
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
    pipeline_run: "PipelineRunSchema" = Relationship(
        back_populates="step_runs"
    )
    model_version: "ModelVersionSchema" = Relationship(
        back_populates="step_runs",
    )
    original_step_run: Optional["StepRunSchema"] = Relationship(
        sa_relationship_kwargs={"remote_side": "StepRunSchema.id"}
    )

    model_config = ConfigDict(protected_namespaces=())  # type: ignore[assignment]

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
        from zenml.zen_stores.schemas import ModelVersionSchema

        options = [
            joinedload(jl_arg(StepRunSchema.deployment)),
            joinedload(jl_arg(StepRunSchema.pipeline_run)),
        ]

        if include_metadata:
            options.extend(
                [
                    joinedload(jl_arg(StepRunSchema.logs)),
                    # joinedload(jl_arg(StepRunSchema.parents)),
                    # joinedload(jl_arg(StepRunSchema.run_metadata)),
                ]
            )

        if include_resources:
            options.extend(
                [
                    joinedload(jl_arg(StepRunSchema.model_version)).joinedload(
                        jl_arg(ModelVersionSchema.model), innerjoin=True
                    ),
                    joinedload(jl_arg(StepRunSchema.user)),
                    # joinedload(jl_arg(StepRunSchema.input_artifacts)),
                    # joinedload(jl_arg(StepRunSchema.output_artifacts)),
                ]
            )

        return options

    @classmethod
    def from_request(
        cls, request: StepRunRequest, deployment_id: Optional[UUID]
    ) -> "StepRunSchema":
        """Create a step run schema from a step run request model.

        Args:
            request: The step run request model.
            deployment_id: The deployment ID.

        Returns:
            The step run schema.
        """
        return cls(
            name=request.name,
            project_id=request.project,
            user_id=request.user,
            start_time=request.start_time,
            end_time=request.end_time,
            status=request.status.value,
            deployment_id=deployment_id,
            original_step_run_id=request.original_step_run_id,
            pipeline_run_id=request.pipeline_run_id,
            docstring=request.docstring,
            cache_key=request.cache_key,
            code_hash=request.code_hash,
            source_code=request.source_code,
        )

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
            ValueError: In case the step run configuration is missing.
        """
        step = None
        if self.deployment is not None:
            step_configurations = json.loads(
                self.deployment.step_configurations
            )
            if self.name in step_configurations:
                pipeline_configuration = (
                    PipelineConfiguration.model_validate_json(
                        self.deployment.pipeline_configuration
                    )
                )
                pipeline_configuration.finalize_substitutions(
                    start_time=self.pipeline_run.start_time,
                    inplace=True,
                )
                step = Step.from_dict(
                    step_configurations[self.name],
                    pipeline_configuration=pipeline_configuration,
                )
        if not step and self.step_configuration:
            # In this legacy case, we're guaranteed to have the merged
            # config stored in the DB, which means we can instantiate the
            # `Step` object directly without passing the pipeline
            # configuration.
            step = Step.model_validate_json(self.step_configuration)
        elif not step:
            raise ValueError(
                f"Unable to load the configuration for step `{self.name}` from "
                "the database. To solve this please delete the pipeline run "
                "that this step run belongs to. Pipeline Run ID: "
                f"`{self.pipeline_run_id}`."
            )

        body = StepRunResponseBody(
            user_id=self.user_id,
            project_id=self.project_id,
            status=ExecutionStatus(self.status),
            start_time=self.start_time,
            end_time=self.end_time,
            created=self.created,
            updated=self.updated,
            model_version_id=self.model_version_id,
            substitutions=step.config.substitutions,
        )
        metadata = None
        if include_metadata:
            metadata = StepRunResponseMetadata(
                config=step.config,
                spec=step.spec,
                cache_key=self.cache_key,
                code_hash=self.code_hash,
                docstring=self.docstring,
                source_code=self.source_code,
                logs=self.logs.to_model() if self.logs else None,
                deployment_id=self.deployment_id,
                pipeline_run_id=self.pipeline_run_id,
                original_step_run_id=self.original_step_run_id,
                parent_step_ids=[p.parent_id for p in self.parents],
                run_metadata=self.fetch_metadata(),
            )

        resources = None
        if include_resources:
            model_version = None
            if self.model_version:
                model_version = self.model_version.to_model()

            input_artifacts: Dict[str, List[StepRunInputResponse]] = {}
            for input_artifact in self.input_artifacts:
                if input_artifact.name not in input_artifacts:
                    input_artifacts[input_artifact.name] = []
                step_run_input = StepRunInputResponse(
                    input_type=StepRunInputArtifactType(input_artifact.type),
                    **input_artifact.artifact_version.to_model().model_dump(),
                )
                input_artifacts[input_artifact.name].append(step_run_input)

            output_artifacts: Dict[str, List["ArtifactVersionResponse"]] = {}
            for output_artifact in self.output_artifacts:
                if output_artifact.name not in output_artifacts:
                    output_artifacts[output_artifact.name] = []
                output_artifacts[output_artifact.name].append(
                    output_artifact.artifact_version.to_model()
                )

            resources = StepRunResponseResources(
                user=self.user.to_model() if self.user else None,
                model_version=model_version,
                inputs=input_artifacts,
                outputs=output_artifacts,
            )

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

        self.updated = utc_now()

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
    artifact_version: "ArtifactVersionSchema" = Relationship(
        back_populates="input_of_step_runs",
        sa_relationship_kwargs={"lazy": "joined"},
    )


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
        back_populates="output_of_step_runs",
        sa_relationship_kwargs={"lazy": "joined"},
    )
