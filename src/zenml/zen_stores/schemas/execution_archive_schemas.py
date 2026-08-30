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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""SQL schemas of the execution archive catalog."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import TEXT, BigInteger, Column, String, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlmodel import Field

from zenml.enums import ExecutionArchiveState
from zenml.models import ExecutionArchiveObject, ExecutionArchiveResponse
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import (
    build_foreign_key_field,
    build_index,
)


class ExecutionArchiveStorageTargetSchema(BaseSchema, table=True):
    """Destination of archive objects, as configured on the server.

    A target's identity (flavor, configuration, prefix) never changes and
    is keyed by its digest; a configuration change records another target,
    and archives written to the old one keep resolving against it.
    """

    __tablename__ = "execution_archive_storage_target"
    __table_args__ = (
        UniqueConstraint(
            "digest", name="unique_execution_archive_storage_target_digest"
        ),
    )

    flavor: str = Field(sa_column=Column(String(255), nullable=False))
    # The importable source of the flavor is captured so the target does
    # not depend on the mutable `flavor` table.
    flavor_source: str = Field(sa_column=Column(TEXT, nullable=False))
    configuration: str = Field(
        sa_column=Column(
            String(length=16777215).with_variant(mysql.MEDIUMTEXT, "mysql"),
            nullable=False,
        )
    )
    path_prefix: str = Field(sa_column=Column(String(512), nullable=False))
    digest: str = Field(sa_column=Column(String(64), nullable=False))


class ExecutionArchiveSchema(BaseSchema, table=True):
    """Authority record of one archive generation of an execution family.

    `root_run_id` is a logical identifier, not a foreign key: the catalog
    row outlives the hot rows it describes. The row follows its project.
    """

    __tablename__ = "execution_archive"
    __table_args__ = (
        UniqueConstraint(
            "root_run_id",
            "generation",
            name="unique_execution_archive_root_generation",
        ),
        build_index(
            table_name=__tablename__, column_names=["project_id", "state"]
        ),
    )

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        custom_constraint_name="fk_execution_archive_project_id_project",
    )
    root_run_id: UUID
    generation: int
    state: str = Field(sa_column=Column(String(32), nullable=False))
    source_fingerprint: str = Field(
        sa_column=Column(String(64), nullable=False)
    )
    storage_target_id: UUID = Field(
        foreign_key="execution_archive_storage_target.id", nullable=False
    )
    manifest_sha256: Optional[str] = Field(
        default=None, sa_column=Column(String(64), nullable=True)
    )
    manifest_stored_bytes: Optional[int] = Field(
        default=None, sa_column=Column(BigInteger, nullable=True)
    )
    execution_sha256: Optional[str] = Field(
        default=None, sa_column=Column(String(64), nullable=True)
    )
    execution_stored_bytes: Optional[int] = Field(
        default=None, sa_column=Column(BigInteger, nullable=True)
    )
    snapshot_sha256: Optional[str] = Field(
        default=None, sa_column=Column(String(64), nullable=True)
    )
    snapshot_stored_bytes: Optional[int] = Field(
        default=None, sa_column=Column(BigInteger, nullable=True)
    )
    stored_bytes: Optional[int] = Field(
        default=None, sa_column=Column(BigInteger, nullable=True)
    )
    # The worker currently exporting, compacting or restoring the
    # generation, and until when its claim lasts unless renewed.
    owner: Optional[str] = Field(
        default=None, sa_column=Column(String(255), nullable=True)
    )
    owner_expires_at: Optional[datetime] = Field(default=None, nullable=True)
    committed_at: Optional[datetime] = Field(default=None, nullable=True)
    compacted_at: Optional[datetime] = Field(default=None, nullable=True)
    restored_at: Optional[datetime] = Field(default=None, nullable=True)
    last_error: Optional[str] = Field(
        default=None, sa_column=Column(TEXT, nullable=True)
    )

    @property
    def archive_state(self) -> ExecutionArchiveState:
        """The typed archive state.

        Returns:
            The state.
        """
        return ExecutionArchiveState(self.state)

    def set_objects(
        self,
        *,
        manifest: ExecutionArchiveObject,
        execution: ExecutionArchiveObject,
        snapshots: ExecutionArchiveObject,
    ) -> None:
        """Record the exported object references.

        Args:
            manifest: The manifest object.
            execution: The execution payload object.
            snapshots: The snapshot payload object.
        """
        self.manifest_sha256 = manifest.sha256
        self.manifest_stored_bytes = manifest.stored_bytes
        self.execution_sha256 = execution.sha256
        self.execution_stored_bytes = execution.stored_bytes
        self.snapshot_sha256 = snapshots.sha256
        self.snapshot_stored_bytes = snapshots.stored_bytes

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> ExecutionArchiveResponse:
        """Convert the catalog row to its detached view.

        Args:
            include_metadata: Unused; the response has no metadata.
            include_resources: Unused; the response has no resources.
            **kwargs: Unused.

        Returns:
            The archive response.
        """
        return ExecutionArchiveResponse(
            id=self.id,
            project_id=self.project_id,
            root_run_id=self.root_run_id,
            generation=self.generation,
            state=self.archive_state,
            source_fingerprint=self.source_fingerprint,
            storage_target_id=self.storage_target_id,
            manifest=_object(self.manifest_sha256, self.manifest_stored_bytes),
            execution_payload=_object(
                self.execution_sha256, self.execution_stored_bytes
            ),
            snapshot_payload=_object(
                self.snapshot_sha256, self.snapshot_stored_bytes
            ),
            stored_bytes=self.stored_bytes,
            committed_at=self.committed_at,
            compacted_at=self.compacted_at,
            restored_at=self.restored_at,
            last_error=self.last_error,
            created=self.created,
        )


def _object(
    sha256: Optional[str], stored_bytes: Optional[int]
) -> Optional[ExecutionArchiveObject]:
    if sha256 is None or stored_bytes is None:
        return None
    return ExecutionArchiveObject(sha256=sha256, stored_bytes=stored_bytes)
