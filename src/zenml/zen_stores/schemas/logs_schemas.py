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
"""SQLModel implementation of pipeline logs tables."""


from typing import Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.models.logs_models import LogsResponseModel
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema


class LogsSchema(BaseSchema, table=True):
    """SQL Model for logs."""

    __tablename__ = "logs"

    pipeline_run_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineRunSchema.__tablename__,
        source_column="pipeline_run_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    pipeline_run: Optional["PipelineRunSchema"] = Relationship(
        back_populates="logs"
    )

    step_run_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="step_run_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    step_run: Optional["StepRunSchema"] = Relationship(back_populates="logs")

    artifact_store_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=StackComponentSchema.__tablename__,
        source_column="stack_component_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    artifact_store: Optional["StackComponentSchema"] = Relationship(
        back_populates="run_or_step_logs"
    )

    uri: str = Field(sa_column=Column(TEXT, nullable=False))

    def to_model(self) -> "LogsResponseModel":
        """Convert a `LogsSchema` to a `LogsResponseModel`.

        Returns:
            The created `LogsModel`.
        """
        return LogsResponseModel(
            id=self.id,
            pipeline_run_id=self.pipeline_run_id,
            step_run_id=self.step_run_id,
            artifact_store_id=self.artifact_store_id,
            uri=self.uri,
            created=self.created,
            updated=self.updated,
        )
