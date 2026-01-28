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
from sqlalchemy.dialects.mysql.types import MEDIUMTEXT
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import VARCHAR, String
from sqlmodel import Field, Relationship

from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.enums import TriggerCategory, TriggerType
from zenml.models import (
    ScheduleUpdatePayload,
    TriggerRequest,
    TriggerResponse,
    TriggerResponseBody,
    TriggerResponseMetadata,
    TriggerResponseResources,
    TriggerUpdate,
)
from zenml.zen_stores.schemas import PipelineSnapshotSchema
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
    RunMetadataInterface,
    jl_arg,
)


class TriggerSchema(NamedSchema, RunMetadataInterface, table=True):
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
                "trigger_type",
            ],
        ),
        build_index(
            table_name=__tablename__,
            column_names=[
                "category",
            ],
        ),
        build_index(
            table_name=__tablename__,
            column_names=["category", "next_occurrence"],
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
    trigger_type: str = Field(
        sa_column=Column(VARCHAR(20), nullable=False),
        description="The Trigger type e.g. webhook, schedule, etc.",
    )
    category: str = Field(
        sa_column=Column(VARCHAR(50), nullable=False),
        description="The Trigger category e.g. native schedule, github webhook, etc.",
    )
    data: str = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=False,
        ),
        description="JSON object - the extra trigger object parameters",
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

    user_id: UUID | None = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )

    # ------------------ RELATIONSHIPS --------------------------------------------

    snapshot_links: list["TriggerSnapshotSchema"] = Relationship(
        back_populates="trigger",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )

    snapshots: list[PipelineSnapshotSchema] = Relationship(
        back_populates="triggers",
        link_model=TriggerSnapshotSchema,
        sa_relationship_kwargs={"viewonly": True},
    )

    trigger_executions: list[TriggerExecutionSchema] = Relationship(
        back_populates="trigger",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )

    # ------------------ FLAT DATA FIELDS FOR FAST FILTERING ----------------------

    next_occurrence: datetime | None = Field(
        nullable=True,
        default=None,
        description="The next occurrence. Applicable for schedules.",
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
                    selectinload(jl_arg(TriggerSchema.snapshots)).joinedload(
                        jl_arg(PipelineSnapshotSchema.triggers), innerjoin=True
                    ),
                    selectinload(
                        jl_arg(TriggerSchema.trigger_executions)
                    ).joinedload(
                        jl_arg(TriggerExecutionSchema.trigger), innerjoin=True
                    ),
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
        from zenml.utils.native_schedules import calculate_first_occurrence

        if trigger_request.trigger_type == TriggerType.schedule:
            next_occurrence = calculate_first_occurrence(trigger_request.data)
        else:
            next_occurrence = None

        return cls(
            name=trigger_request.name,
            project_id=trigger_request.project,
            user_id=trigger_request.user,
            active=trigger_request.active,
            data=trigger_request.data,
            trigger_type=trigger_request.trigger_type,
            category=trigger_request.category,
            next_occurrence=next_occurrence,
        )

    def update(self, trigger_update: TriggerUpdate) -> "TriggerSchema":
        """Applies update operation (and validations).

        Args:
            trigger_update: A TriggerUpdate object.

        Returns:
            The updated TriggerSchema.

        Raises:
            ValueError: If trigger_update is invalid.
        """
        if trigger_update.active is not None:
            self.active = trigger_update.active

        if trigger_update.name is not None:
            self.name = trigger_update.name

        if trigger_update.data is not None:
            if self.type == TriggerType.schedule.value:
                if not isinstance(trigger_update.data, ScheduleUpdatePayload):
                    raise ValueError(
                        "Expected ScheduleUpdatePayload update object for schedule trigger"
                    )

                if trigger_update.data.next_occurrence:
                    self.next_occurrence = trigger_update.data.next_occurrence

            self.data = trigger_update.data.model_dump_json()

        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> TriggerResponse:
        """Converts to Pydantic response model.

        Args:
            include_metadata: Flag - to include metadata.
            include_resources: Flag - include resources.
            **kwargs: Keyword arguments

        Returns:
            A TriggerResponse object.
        """
        if self.trigger_type == TriggerType.schedule.value:
            data = ScheduleUpdatePayload(**json.loads(self.data))
        else:
            data = None

        body = TriggerResponseBody(
            user_id=self.user_id,
            project_id=self.project_id,
            active=self.active,
            updated=self.updated,
            created=self.created,
            is_archived=self.is_archived,
            trigger_type=TriggerType(self.trigger_type),
            category=TriggerCategory(self.category),
            data=data,
        )

        metadata = None
        if include_metadata:
            metadata = TriggerResponseMetadata()

        resources = None
        if include_resources:
            resources = TriggerResponseResources(
                user=self.user.to_model() if self.user else None,
                snapshots=[s.to_model() for s in self.snapshots],
            )

        return TriggerResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )
