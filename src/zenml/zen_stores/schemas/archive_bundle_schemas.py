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
    """Catalog row for one archived execution tree.

    A bundle holds the detail rows of a single root pipeline run tree that
    were moved out of the database. Archived identity rows point back here
    through their `archive_bundle_id` column, which is a plain UUID without a
    foreign key: the index and foreign-key rollout on the three large identity
    tables is deferred until it has been timed. Readers can identify archived
    rows without joining the catalog. Catalog records are retained; an
    expired pending claim is marked failed, never deleted.

    `root_run_id` is SET NULL rather than CASCADE because a snapshot archived
    in the same bundle can outlive the root run; a restore of a deleted run is
    refused, never resurrected. Archive objects are never deleted by this
    lifecycle.
    """

    __tablename__ = "archive_bundle"
    __table_args__ = (
        Index(
            "ix_archive_bundle_active_root_id", "active_root_id", unique=True
        ),
        Index(
            "ix_archive_bundle_root_created_id", "root_run_id", "created", "id"
        ),
    )

    active_root_id: Optional[UUID] = Field(default=None, nullable=True)
    claim_token: int = Field(
        default=1,
        sa_column=Column(BigInteger, nullable=False, server_default="1"),
    )
    claim_expires_at: Optional[datetime] = Field(default=None, nullable=True)

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    root_run_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=PipelineRunSchema.__tablename__,
        source_column="root_run_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )

    uri: Optional[str] = Field(
        default=None, sa_column=Column(TEXT, nullable=True)
    )
    size_bytes: Optional[int] = Field(
        default=None, sa_column=Column(BigInteger, nullable=True)
    )
    manifest_hash: Optional[str] = Field(default=None, nullable=True)
    format_version: int = Field(nullable=False)
    status: str = Field(nullable=False)
    claimed_by: Optional[str] = Field(nullable=True, default=None)
    status_reason: Optional[str] = Field(
        sa_column=Column(TEXT, nullable=True), default=None
    )
    restored_at: Optional[datetime] = Field(nullable=True, default=None)
