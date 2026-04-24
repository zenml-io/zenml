# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""SQL Model Implementations for Triggers."""

import json
from datetime import datetime
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.session import object_session
from sqlalchemy.sql.base import ExecutableOption
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import TEXT, VARCHAR, String
from sqlmodel import Field, Relationship, col, desc, select

from zenml.constants import TEXT_FIELD_MAX_LENGTH
from zenml.enums import TriggerFlavor, TriggerType
from zenml.models import (
    TRIGGER_RETURN_TYPE_UNION,
    TriggerRequest,
    TriggerResponseMetadata,
    TriggerResponseResources,
    TriggerSnapshotDispatchState,
    TriggerUpdate,
)
from zenml.models.v2.core.triggers import TriggerBase
from zenml.triggers.registry import (
    TYPE_TO_RESPONSE_BODY_MAPPING,
    TYPE_TO_RESPONSE_MAPPING,
)
from zenml.zen_stores.schemas import PipelineRunSchema, PipelineSnapshotSchema
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import (
    build_foreign_key_field,
    build_index,
)
from zenml.zen_stores.schemas.trigger_assoc import (
    TriggerExecutionSchema,
    TriggerSnapshotSchema,
)
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import (
    jl_arg,
)


class TriggerSchema(NamedSchema, table=True):
    """SQL Model for schedules."""

    __tablename__ = "trigger"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "project_id",
            name="unique_trigger_name_in_project",
        ),
        build_index(
            table_name=__tablename__,
            column_names=[
                "type",
            ],
        ),
        build_index(
            table_name=__tablename__,
            column_names=["flavor", "next_occurrence"],
        ),
        build_index(
            table_name=__tablename__,
            column_names=["flavor", "source_entity"],
        ),
    )

    # -------------------- BASE FIELDS

    active: bool = Field(
        nullable=False, description="Whether the trigger is active."
    )
    is_archived: bool = Field(
        nullable=False,
        default=False,
        description="Soft-deletion flag. If Trigger is set to archived"
        " it is preserved in the DB but otherwise unusable.",
    )
    type: str = Field(
        sa_column=Column(VARCHAR(20), nullable=False),
        description="The Trigger type e.g. webhook, schedule, etc.",
    )
    flavor: str = Field(
        sa_column=Column(VARCHAR(50), nullable=False),
        description="The Trigger category e.g. native schedule, github webhook, etc.",
    )
    configuration: str = Field(
        sa_column=Column(
            String(length=TEXT_FIELD_MAX_LENGTH).with_variant(TEXT, "mysql"),
            nullable=False,
        ),
        description="JSON object - the extra trigger object parameters",
    )
    concurrency: str = Field(
        sa_column=Column(VARCHAR(20), nullable=False),
        description="The trigger execution concurrency (SKIP, SUBMIT, etc.)",
    )
    end_time: datetime | None = Field(
        nullable=True,
        default=None,
        description="The point in time after which the trigger stops creating runs.",
    )
    max_runs: int | None = Field(
        nullable=True,
        default=None,
        description="Maximum number of runs a trigger can create per attached snapshot.",
    )
    # -------------------- FOREIGN KEYS ------------------------------------

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )

    project: ProjectSchema = Relationship(back_populates="triggers")

    user_id: UUID | None = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )

    # ------------------ RELATIONSHIPS --------------------------------------------

    # Reference to attached executable snapshots.
    snapshots: list[PipelineSnapshotSchema] = Relationship(
        link_model=TriggerSnapshotSchema,
        sa_relationship_kwargs={"viewonly": True},
    )
    snapshot_links: list[TriggerSnapshotSchema] = Relationship(
        sa_relationship_kwargs={"cascade": "delete"}
    )

    user: UserSchema | None = Relationship(back_populates="triggers")

    # ------------------ FLAT DATA FIELDS FOR FAST FILTERING ----------------------

    next_occurrence: datetime | None = Field(
        nullable=True,
        default=None,
        description="The next occurrence. Applicable for schedules.",
    )

    source_entity: str | None = Field(
        sa_column=Column(VARCHAR(255), default=None, nullable=True),
        description="The event source(e.g. pipeline:<uuid>. Applicable for platform events.",
    )

    target_events: str | None = Field(
        sa_column=Column(
            String(length=TEXT_FIELD_MAX_LENGTH).with_variant(TEXT, "mysql"),
            nullable=True,
            default=None,
        ),
        description="The target events of the trigger (e.g. event:run_completed). Applicable for platform events.",
    )

    @property
    def latest_run(self) -> PipelineRunSchema | None:
        """Fetch the latest execution for this trigger.

        Raises:
            RuntimeError: If no session for the schema exists.

        Returns:
            The latest run for this pipeline.
        """
        if session := object_session(self):
            stmt = (
                select(PipelineRunSchema)
                .join(
                    TriggerExecutionSchema,
                    col(TriggerExecutionSchema.pipeline_run_id)
                    == col(PipelineRunSchema.id),
                )
                .where(TriggerExecutionSchema.trigger_id == self.id)
                .order_by(desc(TriggerExecutionSchema.created_at))
                .limit(1)
            )

            return session.execute(stmt).scalars().one_or_none()
        else:
            raise RuntimeError(
                "Missing DB session to fetch latest pipeline run for trigger."
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
                    selectinload(jl_arg(TriggerSchema.snapshots)).selectinload(
                        jl_arg(PipelineSnapshotSchema.source_snapshot)
                    ),
                    selectinload(jl_arg(TriggerSchema.snapshot_links)),
                ]
            )

        return options

    @classmethod
    def from_request(cls, trigger_request: TriggerRequest) -> "TriggerSchema":
        """Creates a TriggerSchema object from a TriggerRequest.

        Args:
            trigger_request: A TriggerRequest object.

        Returns:
            A TriggerSchema object.
        """
        extra_fields = trigger_request.get_extra_fields()

        schema = cls(
            name=trigger_request.name,
            project_id=trigger_request.project,
            user_id=trigger_request.user,
            active=trigger_request.active,
            configuration=trigger_request.get_config(),
            flavor=trigger_request.flavor,
            type=trigger_request.type,
            concurrency=trigger_request.concurrency,
            end_time=trigger_request.end_time,
            max_runs=trigger_request.max_runs,
        )

        for field_name, value in extra_fields.items():
            setattr(schema, field_name, value)

        return schema

    def update(self, trigger_update: TriggerUpdate) -> "TriggerSchema":
        """Applies update operation (and validations).

        Args:
            trigger_update: A TriggerUpdate object.

        Returns:
            The updated TriggerSchema.
        """
        for field, value in trigger_update.model_dump(
            exclude_unset=True,
            include=set(TriggerBase.model_fields.keys()),
        ).items():
            if field in ["type"]:
                continue
            setattr(self, field, value)

        self.configuration = trigger_update.get_config()

        for field_name, value in trigger_update.get_extra_fields().items():
            setattr(self, field_name, value)

        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> TRIGGER_RETURN_TYPE_UNION:
        """Converts to Pydantic response model.

        Args:
            include_metadata: Flag - to include metadata.
            include_resources: Flag - include resources.
            **kwargs: Keyword arguments

        Returns:
            A TriggerResponse object.
        """
        body_cls = TYPE_TO_RESPONSE_BODY_MAPPING[self.type]
        response_cls = TYPE_TO_RESPONSE_MAPPING[self.type]

        body = body_cls(
            user_id=self.user_id,
            project_id=self.project_id,
            active=self.active,
            updated=self.updated,
            created=self.created,
            is_archived=self.is_archived,
            type=TriggerType(self.type),
            flavor=TriggerFlavor(self.flavor),
            name=self.name,
            concurrency=self.concurrency,
            end_time=self.end_time,
            max_runs=self.max_runs,
            **json.loads(self.configuration),
        )

        for field in body.get_extra_fields():
            setattr(body, field, getattr(self, field))

        metadata = None
        if include_metadata:
            metadata = TriggerResponseMetadata()

        resources = None
        if include_resources:
            latest_run = self.latest_run
            display_snapshot_id_by_executable_id: dict[UUID, UUID] = {}
            snapshots = []
            executable_snapshots = []
            for snapshot in self.snapshots:
                snapshot_model = snapshot.to_model()
                executable_snapshots.append(snapshot_model)
                display_snapshot = (
                    snapshot.source_snapshot.to_model()
                    if snapshot.source_snapshot is not None
                    else snapshot_model
                )
                snapshots.append(display_snapshot)
                display_snapshot_id_by_executable_id[snapshot.id] = (
                    display_snapshot.id
                )

            snapshot_dispatch_states: dict[
                UUID, TriggerSnapshotDispatchState
            ] = {}
            for snapshot_link in self.snapshot_links:
                parsed_state = snapshot_link.parsed_dispatch_state
                display_snapshot_id = display_snapshot_id_by_executable_id.get(
                    snapshot_link.snapshot_id
                )
                if (
                    parsed_state is not None
                    and display_snapshot_id is not None
                ):
                    snapshot_dispatch_states[display_snapshot_id] = (
                        parsed_state
                    )

            resources = TriggerResponseResources(
                user=self.user.to_model() if self.user else None,
                snapshots=snapshots,
                executable_snapshots=executable_snapshots,
                latest_run=latest_run.to_model()
                if latest_run is not None
                else None,
                snapshot_dispatch_states=snapshot_dispatch_states,
            )

        return response_cls(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )
