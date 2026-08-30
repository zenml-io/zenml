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
"""SQL schema for the execution archive catalog."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import TEXT, BigInteger, Column, String, UniqueConstraint
from sqlmodel import Field

from zenml.enums import ExecutionArchiveState
from zenml.exceptions import ExecutionArchiveStateError
from zenml.models import ExecutionArchiveObject, ExecutionArchiveResponse
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.schema_utils import build_index


class ExecutionArchiveSchema(BaseSchema, table=True):
    """One immutable archive generation and its current authority state."""

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
        build_index(
            table_name=__tablename__, column_names=["purge_pending_at"]
        ),
        build_index(
            table_name=__tablename__,
            column_names=["state", "updated", "id"],
        ),
    )

    # Logical identifiers intentionally have no foreign keys: purge must still
    # locate objects after project and execution rows have been deleted.
    project_id: UUID
    root_run_id: UUID
    generation: int
    state: str = Field(sa_column=Column(String(32), nullable=False))
    source_fingerprint: str = Field(
        sa_column=Column(String(64), nullable=False)
    )
    source_updated_at: datetime
    storage_target_digest: str = Field(
        sa_column=Column(String(64), nullable=False)
    )
    object_key: Optional[str] = Field(
        default=None, sa_column=Column(TEXT, nullable=True)
    )
    object_sha256: Optional[str] = Field(
        default=None, sa_column=Column(String(64), nullable=True)
    )
    object_stored_bytes: Optional[int] = Field(
        default=None, sa_column=Column(BigInteger, nullable=True)
    )
    object_decoded_bytes: Optional[int] = Field(
        default=None, sa_column=Column(BigInteger, nullable=True)
    )
    source_bytes: Optional[int] = Field(
        default=None, sa_column=Column(BigInteger, nullable=True)
    )
    owner: Optional[str] = Field(
        default=None, sa_column=Column(String(255), nullable=True)
    )
    claim_token: int = Field(
        default=0,
        sa_column=Column(BigInteger, nullable=False, server_default="0"),
    )
    owner_expires_at: Optional[datetime] = Field(default=None, nullable=True)
    committed_at: Optional[datetime] = Field(default=None, nullable=True)
    compacted_at: Optional[datetime] = Field(default=None, nullable=True)
    restored_at: Optional[datetime] = Field(default=None, nullable=True)
    purge_pending_at: Optional[datetime] = Field(default=None, nullable=True)
    last_error: Optional[str] = Field(
        default=None, sa_column=Column(TEXT, nullable=True)
    )

    @property
    def archive_state(self) -> ExecutionArchiveState:
        """Return the typed lifecycle state.

        Returns:
            Archive state.
        """
        return ExecutionArchiveState(self.state)

    @property
    def requires_restore(self) -> bool:
        """Return whether SQL may contain archive payload markers.

        A corruption found before compaction leaves SQL authoritative. A
        corruption found while restoring a cold archive does not. The
        timestamps disambiguate those two cases without another lifecycle
        state.

        Returns:
            Whether full payload reads require restoration.
        """
        return self.archive_state.is_authoritative or (
            self.archive_state == ExecutionArchiveState.CORRUPT
            and self.compacted_at is not None
            and self.restored_at is None
        )

    def set_object(self, *, key: str, object_: ExecutionArchiveObject) -> None:
        """Record the one verified object of this generation.

        Args:
            key: Full immutable object key.
            object_: Verified object metadata.
        """
        self.object_key = key
        self.object_sha256 = object_.sha256
        self.object_stored_bytes = object_.stored_bytes
        self.object_decoded_bytes = object_.decoded_bytes

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> ExecutionArchiveResponse:
        """Convert the catalog row to its detached API view.

        Args:
            include_metadata: Unused; the response is not paginated metadata.
            include_resources: Unused; the response has no relationships.
            **kwargs: Unused schema conversion arguments.

        Returns:
            Detached archive generation.
        """
        return ExecutionArchiveResponse(
            id=self.id,
            project_id=self.project_id,
            root_run_id=self.root_run_id,
            generation=self.generation,
            state=self.archive_state,
            requires_restore=self.requires_restore,
            source_fingerprint=self.source_fingerprint,
            source_updated_at=self.source_updated_at,
            storage_target_digest=self.storage_target_digest,
            object=self._object(),
            source_bytes=self.source_bytes,
            committed_at=self.committed_at,
            compacted_at=self.compacted_at,
            restored_at=self.restored_at,
            purge_pending_at=self.purge_pending_at,
            last_error=self.last_error,
            created=self.created,
        )

    def _object(self) -> Optional[ExecutionArchiveObject]:
        values = (
            self.object_sha256,
            self.object_stored_bytes,
            self.object_decoded_bytes,
        )
        if all(value is None for value in values):
            return None
        if any(value is None for value in values):
            raise ExecutionArchiveStateError(
                f"Execution archive {self.id} has incomplete object metadata."
            )
        return ExecutionArchiveObject(
            sha256=self.object_sha256,
            stored_bytes=self.object_stored_bytes,
            decoded_bytes=self.object_decoded_bytes,
        )
