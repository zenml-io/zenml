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
from sqlmodel import Field, Relationship, desc, select

from zenml.constants import TEXT_FIELD_MAX_LENGTH
from zenml.enums import TriggerFlavor, TriggerType
from zenml.models import (
    TriggerRequest,
    TriggerResponseMetadata,
    TriggerResponseResources,
    TriggerUpdate,
)
from zenml.triggers.registry import (
    TRIGGER_RETURN_TYPE_UNION,
    TYPE_TO_RESPONSE_BODY_MAPPING,
    TYPE_TO_RESPONSE_MAPPING,
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

    snapshots: list[PipelineSnapshotSchema] = Relationship(
        link_model=TriggerSnapshotSchema,
        sa_relationship_kwargs={"viewonly": True},
    )

    user: UserSchema | None = Relationship(back_populates="triggers")

    # ------------------ FLAT DATA FIELDS FOR FAST FILTERING ----------------------

    next_occurrence: datetime | None = Field(
        nullable=True,
        default=None,
        description="The next occurrence. Applicable for schedules.",
    )

    @property
    def latest_execution(self) -> TriggerExecutionSchema | None:
        """Fetch the latest execution for this trigger.

        Raises:
            RuntimeError: If no session for the schema exists.

        Returns:
            The latest run for this pipeline.
        """
        if session := object_session(self):
            stmt = (
                select(TriggerExecutionSchema)
                .where(TriggerExecutionSchema.trigger_id == self.id)
                .order_by(desc(TriggerExecutionSchema.created_at))
                .limit(1)
            )

            return session.execute(stmt).scalars().one_or_none()
        else:
            raise RuntimeError(
                "Missing DB session to fetch latest run for pipeline."
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
                    selectinload(jl_arg(TriggerSchema.snapshots)),
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
        if trigger_update.active is not None:
            self.active = trigger_update.active

        if trigger_update.name is not None:
            self.name = trigger_update.name

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
            **json.loads(self.configuration),
        )

        for field in body.get_extra_fields():
            setattr(body, field, getattr(self, field))

        metadata = None
        if include_metadata:
            metadata = TriggerResponseMetadata()

        resources = None
        if include_resources:
            latest_execution = self.latest_execution

            resources = TriggerResponseResources(
                user=self.user.to_model() if self.user else None,
                snapshots=[
                    s.to_model(
                        include_resources=False,
                        include_metadata=False,
                        include_config_schema=False,
                        include_python_packages=False,
                    )
                    for s in self.snapshots
                ],
                latest_run=latest_execution.pipeline_run.to_model()
                if latest_execution
                else None,
            )

        return response_cls(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )
