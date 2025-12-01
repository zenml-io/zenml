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
"""Pipeline snapshot schemas."""

import json
from typing import TYPE_CHECKING, Any, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import TEXT, CheckConstraint, Column, String, UniqueConstraint
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import joinedload, object_session, selectinload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship, asc, col, desc, select

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.step_configurations import Step
from zenml.constants import MEDIUMTEXT_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.enums import TaggableResourceTypes, VisualizationResourceTypes
from zenml.logger import get_logger
from zenml.models import (
    PipelineSnapshotRequest,
    PipelineSnapshotResponse,
    PipelineSnapshotResponseBody,
    PipelineSnapshotResponseMetadata,
    PipelineSnapshotResponseResources,
    PipelineSnapshotUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.code_repository_schemas import (
    CodeReferenceSchema,
)
from zenml.zen_stores.schemas.pipeline_build_schemas import PipelineBuildSchema
from zenml.zen_stores.schemas.pipeline_schemas import PipelineSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schedule_schema import ScheduleSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.stack_schemas import StackSchema
from zenml.zen_stores.schemas.tag_schemas import TagSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import jl_arg

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.curated_visualization_schemas import (
        CuratedVisualizationSchema,
    )
    from zenml.zen_stores.schemas.deployment_schemas import (
        DeploymentSchema,
    )
    from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
    from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema

logger = get_logger(__name__)


class PipelineSnapshotSchema(BaseSchema, table=True):
    """SQL Model for pipeline snapshots."""

    __tablename__ = "pipeline_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "pipeline_id",
            "name",
            name="unique_name_for_pipeline_id",
        ),
    )

    # Fields
    name: Optional[str] = Field(nullable=True)
    description: Optional[str] = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=True,
        )
    )
    is_dynamic: bool = Field(nullable=False, default=False)

    pipeline_configuration: str = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=False,
        )
    )
    client_environment: str = Field(sa_column=Column(TEXT, nullable=False))
    run_name_template: str = Field(nullable=False)
    client_version: str = Field(nullable=True)
    server_version: str = Field(nullable=True)
    pipeline_version_hash: Optional[str] = Field(nullable=True, default=None)
    pipeline_spec: Optional[str] = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=True,
        )
    )
    code_path: Optional[str] = Field(nullable=True)

    # Foreign keys
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
    stack_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackSchema.__tablename__,
        source_column="stack_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    pipeline_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=PipelineSchema.__tablename__,
        source_column="pipeline_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    schedule_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=ScheduleSchema.__tablename__,
        source_column="schedule_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    build_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineBuildSchema.__tablename__,
        source_column="build_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    code_reference_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=CodeReferenceSchema.__tablename__,
        source_column="code_reference_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    # This is not a foreign key to remove a cycle which messes with our DB
    # backup process
    source_snapshot_id: Optional[UUID] = None

    # Deprecated, remove once we remove run templates entirely
    template_id: Optional[UUID] = None

    # SQLModel Relationships
    source_snapshot: Optional["PipelineSnapshotSchema"] = Relationship(
        sa_relationship_kwargs=dict(
            primaryjoin="PipelineSnapshotSchema.source_snapshot_id == foreign(PipelineSnapshotSchema.id)",
            viewonly=True,
        ),
    )
    user: Optional["UserSchema"] = Relationship(
        back_populates="snapshots",
    )
    project: "ProjectSchema" = Relationship(back_populates="snapshots")
    stack: Optional["StackSchema"] = Relationship()
    pipeline: "PipelineSchema" = Relationship()
    schedule: Optional["ScheduleSchema"] = Relationship()
    build: Optional["PipelineBuildSchema"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[PipelineSnapshotSchema.build_id]"
        }
    )
    code_reference: Optional["CodeReferenceSchema"] = Relationship()

    pipeline_runs: List["PipelineRunSchema"] = Relationship(
        sa_relationship_kwargs={"cascade": "delete"}
    )
    step_runs: List["StepRunSchema"] = Relationship(
        sa_relationship_kwargs={"cascade": "delete"}
    )
    step_configurations: List["StepConfigurationSchema"] = Relationship(
        sa_relationship_kwargs={
            "cascade": "delete",
            "order_by": "asc(StepConfigurationSchema.index)",
        }
    )
    deployment: Optional["DeploymentSchema"] = Relationship(
        back_populates="snapshot"
    )
    step_count: int
    tags: List["TagSchema"] = Relationship(
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(foreign(TagResourceSchema.resource_type)=='{TaggableResourceTypes.PIPELINE_SNAPSHOT.value}', foreign(TagResourceSchema.resource_id)==PipelineSnapshotSchema.id)",
            secondary="tag_resource",
            secondaryjoin="TagSchema.id == foreign(TagResourceSchema.tag_id)",
            order_by="TagSchema.name",
            overlaps="tags",
        ),
    )
    visualizations: List["CuratedVisualizationSchema"] = Relationship(
        sa_relationship_kwargs=dict(
            primaryjoin=(
                "and_(CuratedVisualizationSchema.resource_type"
                f"=='{VisualizationResourceTypes.PIPELINE_SNAPSHOT.value}', "
                "foreign(CuratedVisualizationSchema.resource_id)==PipelineSnapshotSchema.id)"
            ),
            overlaps="visualizations",
            cascade="delete",
            order_by="CuratedVisualizationSchema.display_order",
        ),
    )

    @property
    def latest_run(self) -> Optional["PipelineRunSchema"]:
        """Fetch the latest run for this snapshot.

        Raises:
            RuntimeError: If no session for the schema exists.

        Returns:
            The latest run for this snapshot.
        """
        from zenml.zen_stores.schemas import (
            PipelineRunSchema,
            PipelineSnapshotSchema,
        )

        if session := object_session(self):
            return (
                session.execute(
                    select(PipelineRunSchema)
                    .join(
                        PipelineSnapshotSchema,
                        col(PipelineSnapshotSchema.id)
                        == col(PipelineRunSchema.snapshot_id),
                    )
                    .where(
                        # The snapshot for this run used this snapshot as a
                        # source (e.g. run triggered from the server,
                        # invocation of a deployment). We currently do not
                        # include runs created directly from a snapshot (e.g.
                        # run directly, scheduled runs), as these happen before
                        # the user officially creates (= assigns a name to) the
                        # snapshot.
                        col(PipelineSnapshotSchema.source_snapshot_id)
                        == self.id,
                    )
                    .order_by(desc(PipelineRunSchema.created))
                    .limit(1)
                )
                .scalars()
                .one_or_none()
            )
        else:
            raise RuntimeError(
                "Missing DB session to fetch latest run for snapshot."
            )

    def get_step_configurations(
        self, include: Optional[List[str]] = None
    ) -> List["StepConfigurationSchema"]:
        """Get step configurations for the snapshot.

        Args:
            include: List of step names to include. If not given, all step
                configurations will be included.

        Raises:
            RuntimeError: If no session for the schema exists.

        Returns:
            List of step configurations.
        """
        if session := object_session(self):
            query = (
                select(StepConfigurationSchema)
                .where(StepConfigurationSchema.snapshot_id == self.id)
                .order_by(asc(StepConfigurationSchema.index))
            )

            if include:
                query = query.where(
                    col(StepConfigurationSchema.name).in_(include)
                )

            return list(session.execute(query).scalars().all())
        else:
            raise RuntimeError(
                "Missing DB session to fetch step configurations."
            )

    def get_step_configuration(
        self, step_name: str
    ) -> "StepConfigurationSchema":
        """Get a step configuration of the snapshot.

        Args:
            step_name: The name of the step to get the configuration for.

        Raises:
            KeyError: If the step configuration is not found.

        Returns:
            The step configuration.
        """
        step_configs = self.get_step_configurations(include=[step_name])
        if len(step_configs) == 0:
            raise KeyError(
                f"Step configuration for step `{step_name}` not found."
            )
        return step_configs[0]

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

        if include_metadata:
            options.extend(
                [
                    joinedload(jl_arg(PipelineSnapshotSchema.stack)),
                    joinedload(jl_arg(PipelineSnapshotSchema.build)),
                    joinedload(jl_arg(PipelineSnapshotSchema.pipeline)),
                    joinedload(jl_arg(PipelineSnapshotSchema.schedule)),
                    joinedload(jl_arg(PipelineSnapshotSchema.code_reference)),
                ]
            )

        if include_resources:
            options.extend(
                [
                    joinedload(jl_arg(PipelineSnapshotSchema.user)),
                    selectinload(
                        jl_arg(PipelineSnapshotSchema.visualizations)
                    ),
                ]
            )

        return options

    @classmethod
    def from_request(
        cls,
        request: PipelineSnapshotRequest,
        code_reference_id: Optional[UUID],
    ) -> "PipelineSnapshotSchema":
        """Create schema from request.

        Args:
            request: The request to convert.
            code_reference_id: Optional ID of the code reference for the
                snapshot.

        Returns:
            The created schema.
        """
        client_env = json.dumps(request.client_environment)
        if len(client_env) > TEXT_FIELD_MAX_LENGTH:
            logger.warning(
                "Client environment is too large to be stored in the database. "
                "Skipping."
            )
            client_env = "{}"

        name = None
        if isinstance(request.name, str):
            name = request.name

        return cls(
            name=name,
            description=request.description,
            is_dynamic=request.is_dynamic,
            stack_id=request.stack,
            project_id=request.project,
            pipeline_id=request.pipeline,
            build_id=request.build,
            user_id=request.user,
            schedule_id=request.schedule,
            template_id=request.template,
            source_snapshot_id=request.source_snapshot,
            code_reference_id=code_reference_id,
            run_name_template=request.run_name_template,
            pipeline_configuration=request.pipeline_configuration.model_dump_json(),
            step_count=len(request.step_configurations),
            client_environment=client_env,
            client_version=request.client_version,
            server_version=request.server_version,
            pipeline_version_hash=request.pipeline_version_hash,
            pipeline_spec=json.dumps(
                request.pipeline_spec.model_dump(mode="json"), sort_keys=True
            )
            if request.pipeline_spec
            else None,
            code_path=request.code_path,
        )

    def update(
        self, update: PipelineSnapshotUpdate
    ) -> "PipelineSnapshotSchema":
        """Update the schema.

        Args:
            update: The update to apply.

        Returns:
            The updated schema.
        """
        if isinstance(update.name, str):
            self.name = update.name
        elif update.name is False:
            self.name = None

        if update.description:
            self.description = update.description

        self.updated = utc_now()
        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        include_python_packages: bool = False,
        include_config_schema: Optional[bool] = None,
        step_configuration_filter: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> PipelineSnapshotResponse:
        """Convert schema to response.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            include_python_packages: Whether the python packages will be filled.
            include_config_schema: Whether the config schema will be filled.
            step_configuration_filter: List of step configurations to include in
                the response. If not given, all step configurations will be
                included.
            **kwargs: Keyword arguments to allow schema specific logic

        Returns:
            The response.
        """
        runnable = False
        if self.build and not self.build.is_local and self.build.stack_id:
            runnable = True

        deployable = False
        if (
            not self.is_dynamic
            and self.build
            and self.stack
            and self.stack.has_deployer
        ):
            deployable = True

        body = PipelineSnapshotResponseBody(
            user_id=self.user_id,
            project_id=self.project_id,
            created=self.created,
            updated=self.updated,
            runnable=runnable,
            deployable=deployable,
            is_dynamic=self.is_dynamic,
        )
        metadata = None
        if include_metadata:
            pipeline_configuration = PipelineConfiguration.model_validate_json(
                self.pipeline_configuration
            )
            step_configurations = {}
            for step_configuration in self.get_step_configurations(
                include=step_configuration_filter
            ):
                step_configurations[step_configuration.name] = Step.from_dict(
                    json.loads(step_configuration.config),
                    pipeline_configuration,
                )

            client_environment = json.loads(self.client_environment)
            if not include_python_packages:
                client_environment.pop("python_packages", None)

            config_template = None
            config_schema = None

            if include_config_schema and self.build and self.build.stack_id:
                from zenml.zen_stores import template_utils

                if step_configuration_filter:
                    # If only a subset of step configurations is requested,
                    # we still need to get all of them to generate the config
                    # template and schema
                    all_step_configurations = {
                        step_configuration.name: Step.from_dict(
                            json.loads(step_configuration.config),
                            pipeline_configuration,
                        )
                        for step_configuration in self.get_step_configurations()
                    }
                else:
                    all_step_configurations = step_configurations

                config_template = template_utils.generate_config_template(
                    snapshot=self,
                    pipeline_configuration=pipeline_configuration,
                    step_configurations=all_step_configurations,
                )
                config_schema = template_utils.generate_config_schema(
                    snapshot=self,
                    pipeline_configuration=pipeline_configuration,
                    step_configurations=all_step_configurations,
                )

            metadata = PipelineSnapshotResponseMetadata(
                description=self.description,
                run_name_template=self.run_name_template,
                pipeline_configuration=pipeline_configuration,
                step_configurations=step_configurations,
                client_environment=client_environment,
                client_version=self.client_version,
                server_version=self.server_version,
                pipeline_version_hash=self.pipeline_version_hash,
                pipeline_spec=PipelineSpec.model_validate_json(
                    self.pipeline_spec
                )
                if self.pipeline_spec
                else None,
                code_path=self.code_path,
                template_id=self.template_id,
                source_snapshot_id=self.source_snapshot_id,
                config_schema=config_schema,
                config_template=config_template,
            )

        resources = None
        if include_resources:
            latest_run = self.latest_run
            latest_run_user = latest_run.user if latest_run else None

            resources = PipelineSnapshotResponseResources(
                user=self.user.to_model() if self.user else None,
                pipeline=self.pipeline.to_model(),
                stack=self.stack.to_model() if self.stack else None,
                build=self.build.to_model() if self.build else None,
                schedule=self.schedule.to_model() if self.schedule else None,
                code_reference=self.code_reference.to_model()
                if self.code_reference
                else None,
                deployment=self.deployment.to_model()
                if self.deployment
                else None,
                tags=[tag.to_model() for tag in self.tags],
                latest_run_id=latest_run.id if latest_run else None,
                latest_run_status=latest_run.status if latest_run else None,
                latest_run_user=latest_run_user.to_model()
                if latest_run_user
                else None,
                visualizations=[
                    visualization.to_model(
                        include_metadata=False,
                        include_resources=False,
                    )
                    for visualization in self.visualizations
                ],
            )

        return PipelineSnapshotResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )


class StepConfigurationSchema(BaseSchema, table=True):
    """SQL Model for step configurations."""

    __tablename__ = "step_configuration"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "step_run_id",
            "name",
            name="unique_step_configuration_for_snapshot_or_step_run",
        ),
        CheckConstraint(
            "(snapshot_id IS NULL AND step_run_id IS NOT NULL) OR "
            "(snapshot_id IS NOT NULL AND step_run_id IS NULL)",
            name="ck_step_configuration_snapshot_step_run_exclusivity",
        ),
    )

    index: int
    name: str
    config: str = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=False,
        )
    )

    snapshot_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=PipelineSnapshotSchema.__tablename__,
        source_column="snapshot_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    step_run_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="step_run",
        source_column="step_run_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
