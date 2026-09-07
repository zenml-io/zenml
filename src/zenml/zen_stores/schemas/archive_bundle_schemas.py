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

from sqlalchemy import TEXT, BigInteger, Column
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
    rows without joining the catalog. Application code must never delete a catalog row while
    identity rows reference it; rows disappear only through the project
    cascade or after the retention job reclaims a bundle.

    `root_run_id` is SET NULL rather than CASCADE because a snapshot archived
    in the same bundle can outlive the root run; a restore of a deleted run is
    refused, never resurrected. Reclaiming catalog rows whose root run is gone
    is the retention job's decision, not a database cascade.
    """

    __tablename__ = "archive_bundle"

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

    uri: str = Field(sa_column=Column(TEXT, nullable=False))
    size_bytes: int = Field(sa_column=Column(BigInteger, nullable=False))
    row_counts: str = Field(sa_column=Column(TEXT, nullable=False))
    manifest_hash: str = Field(nullable=False)
    # Restore compatibility is decided by the archive format version and its
    # adapters, never by replaying migrations; the schema revision is kept as
    # a diagnostic only.
    format_version: int = Field(nullable=False)
    schema_revision: str = Field(nullable=False)
    status: str = Field(nullable=False)
    # Who holds the claim while the row is pending or restoring, and why a
    # row ended up failed or restored with conflicts. `updated` is the claim
    # time.
    claimed_by: Optional[str] = Field(nullable=True, default=None)
    status_reason: Optional[str] = Field(
        sa_column=Column(TEXT, nullable=True), default=None
    )
    restored_at: Optional[datetime] = Field(nullable=True, default=None)
