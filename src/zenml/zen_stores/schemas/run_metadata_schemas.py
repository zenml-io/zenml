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
"""SQLModel implementation of run metadata tables."""

from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import TEXT, VARCHAR, Column
from sqlmodel import Field, Relationship, SQLModel

from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import (
    build_foreign_key_field,
    build_index,
)
from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema


class RunMetadataSchema(BaseSchema, table=True):
    """SQL Model for run metadata."""

    __tablename__ = "run_metadata"

    stack_component_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackComponentSchema.__tablename__,
        source_column="stack_component_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    stack_component: Optional["StackComponentSchema"] = Relationship(
        back_populates="run_metadata"
    )

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="run_metadata")

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    project: "ProjectSchema" = Relationship(back_populates="run_metadata")

    key: str
    value: str = Field(sa_column=Column(TEXT, nullable=False))
    type: str

    publisher_step_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="publisher_step_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )


class RunMetadataResourceSchema(SQLModel, table=True):
    """Table for linking resources to run metadata entries."""

    __tablename__ = "run_metadata_resource"
    __table_args__ = (
        build_index(
            table_name=__tablename__,
            column_names=[
                "resource_id",
                "resource_type",
                "run_metadata_id",
            ],
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    resource_id: UUID
    resource_type: str = Field(sa_column=Column(VARCHAR(255), nullable=False))
    run_metadata_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=RunMetadataSchema.__tablename__,
        source_column="run_metadata_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
