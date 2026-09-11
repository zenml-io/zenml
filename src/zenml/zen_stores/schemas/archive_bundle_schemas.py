#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""SQL Model for the execution archive bundle catalog."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import TEXT, BigInteger, Column, Index
from sqlmodel import Field

from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field


class ArchiveBundleSchema(BaseSchema, table=True):
    """Catalog row for one archived pipeline run.

    A bundle holds the detail of one pipeline run, its steps, its
    exclusively owned snapshots, and their step configurations. Archived
    identity rows point back here through their `archive_bundle_id` column,
    a plain UUID without a foreign key: the index and foreign-key rollout on
    the three large identity tables is deferred until it has been timed.

    The row is inserted in the same transaction that sets those markers, so
    a row exists exactly when an object is authoritative. It is kept after a
    restore, with `restored_at` set, to enforce the restore grace period.
    `run_id` is SET NULL rather than CASCADE because a snapshot archived in
    the same bundle can outlive its run. Archive objects are never deleted.
    """

    __tablename__ = "archive_bundle"
    __table_args__ = (Index("ix_archive_bundle_run_id", "run_id"),)

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    run_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineRunSchema.__tablename__,
        source_column="run_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    uri: str = Field(sa_column=Column(TEXT, nullable=False))
    size_bytes: int = Field(sa_column=Column(BigInteger, nullable=False))
    content_hash: str = Field(nullable=False)
    format_version: int = Field(nullable=False)
    restored_at: Optional[datetime] = Field(nullable=True, default=None)
