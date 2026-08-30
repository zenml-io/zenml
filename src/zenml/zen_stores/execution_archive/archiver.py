#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Non-destructive export and verification of execution archives."""

from datetime import datetime
from typing import TYPE_CHECKING, Callable, Optional
from uuid import UUID

import zenml
from zenml.config.server_config import ServerConfiguration
from zenml.constants import (
    DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_LEASE_SECONDS,
)
from zenml.enums import ExecutionArchiveState
from zenml.exceptions import (
    ArchiveUnavailableError,
    ExecutionArchiveParityError,
    ExecutionArchiveStateError,
)
from zenml.logger import get_logger
from zenml.models import ExecutionArchiveObject, ExecutionArchiveResponse
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.execution_archive.capture import (
    ExecutionArchiveCapture,
    ExecutionArchiveCapturer,
)
from zenml.zen_stores.execution_archive.catalog import (
    ExecutionArchiveCatalog,
    ExecutionArchiveClaim,
)
from zenml.zen_stores.execution_archive.codec import (
    canonical_json,
    compress,
    decompress,
)
from zenml.zen_stores.execution_archive.exceptions import (
    ArchiveObjectInvalidError,
    ChecksumMismatchError,
)
from zenml.zen_stores.execution_archive.payload import (
    ExecutionArchivePayload,
    parse_execution_archive_payload,
)
from zenml.zen_stores.execution_archive.storage import (
    ExecutionArchiveStorage,
    build_execution_archive_storage,
)
from zenml.zen_stores.execution_archive.worker import (
    new_execution_archive_worker_id,
)

if TYPE_CHECKING:
    from zenml.zen_stores.sql_zen_store import SqlZenStore

logger = get_logger(__name__)


class ExecutionArchiveExporter:
    """Export one execution tree, verify it, and leave SQL untouched."""

    def __init__(
        self,
        *,
        store: "SqlZenStore",
        config: Optional[ServerConfiguration] = None,
        storage: Optional[ExecutionArchiveStorage] = None,
        clock: Callable[[], datetime] = utc_now,
        owner: Optional[str] = None,
        lease_seconds: float = (
            DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_LEASE_SECONDS
        ),
    ) -> None:
        """Initialize the exporter.

        Args:
            store: SQL Zen store containing execution history.
            config: Deployment archive configuration used to build storage.
            storage: Injected archive storage, primarily for testing.
            clock: Source of timestamps.
            owner: Unique worker identity.
            lease_seconds: Duration of each fenced ownership lease.
        """
        self._store = store
        self._workspace_id = store.get_deployment_id()
        if storage is None:
            storage = build_execution_archive_storage(
                config or ServerConfiguration.get_server_config(),
                workspace_id=self._workspace_id,
            )
        self._storage = storage
        self._clock = clock
        self._lease_seconds = lease_seconds
        self._owner = owner or new_execution_archive_worker_id()
        self._catalog = ExecutionArchiveCatalog(store.engine)
        self._capturer = ExecutionArchiveCapturer(store.engine)

    def export(
        self, *, project_id: UUID, root_run_id: UUID
    ) -> ExecutionArchiveResponse:
        """Export and verify one execution tree without changing SQL payload.

        Args:
            project_id: Project that owns the root run.
            root_run_id: Root run of the execution tree.

        Returns:
            Verified archive generation.

        Raises:
            ArchiveUnavailableError: If stored bytes are unavailable or
                invalid.
            Exception: Any source or storage failure, after recording a safe
                catalog outcome.
        """
        capture = self._capturer.capture(
            project_id=project_id, root_run_id=root_run_id
        )
        claim = self._catalog.start_export(
            project_id=project_id,
            root_run_id=root_run_id,
            source_fingerprint=capture.source_fingerprint,
            source_updated_at=capture.family.latest_mutation,
            storage_target_digest=self._storage.target_digest,
            source_bytes=capture.family.source_bytes,
            owner=self._owner,
            lease_seconds=self._lease_seconds,
        )
        original_state = claim.archive.state
        try:
            if original_state == ExecutionArchiveState.VERIFIED:
                self._verify_existing(claim, capture)
                archive = self._catalog.clear_error(claim)
                self._clean_other_attempts(
                    self._catalog.object_key(archive.id)
                )
                return archive
            return self._write_and_verify(claim, capture)
        except (
            ArchiveObjectInvalidError,
            ChecksumMismatchError,
        ) as e:
            self._catalog.try_record_failure(
                claim, e, state=ExecutionArchiveState.CORRUPT
            )
            raise ArchiveUnavailableError(
                f"Execution archive {claim.archive_id} is corrupt: {e}"
            ) from e
        except ArchiveUnavailableError as e:
            if original_state == ExecutionArchiveState.VERIFIED:
                self._catalog.try_record_failure(claim, e)
            else:
                self._catalog.try_record_failure(
                    claim, e, state=ExecutionArchiveState.FAILED
                )
            raise
        except Exception as e:
            self._catalog.try_record_failure(
                claim, e, state=ExecutionArchiveState.FAILED
            )
            raise
        finally:
            self._catalog.release(claim)

    def _write_and_verify(
        self,
        claim: ExecutionArchiveClaim,
        capture: ExecutionArchiveCapture,
    ) -> ExecutionArchiveResponse:
        payload = capture.to_payload(
            archive_id=claim.archive_id,
            workspace_id=self._workspace_id,
            generation=claim.archive.generation,
            writer_version=zenml.__version__,
            writer_alembic_revision=",".join(
                self._store.alembic.current_revisions()
            ),
            created_at=self._clock(),
        )
        decoded = canonical_json(payload)
        encoded = compress(decoded)
        key = self._storage.object_key(
            project_id=claim.archive.project_id,
            archive_id=claim.archive_id,
            claim_token=claim.token,
        )
        claim = self._catalog.renew(claim, lease_seconds=self._lease_seconds)
        try:
            object_ = self._storage.write_verified(
                key, encoded, decoded_bytes=len(decoded)
            )
            decode_archive_payload(
                encoded=encoded,
                object_=object_,
                archive=claim.archive,
                workspace_id=self._workspace_id,
            )
            claim = self._catalog.renew(
                claim, lease_seconds=self._lease_seconds
            )
            self._require_unchanged(capture)
            archive = self._catalog.mark_verified(
                claim, key=key, object_=object_
            )
            self._clean_other_attempts(key)
            return archive
        except Exception:
            # The fencing token makes this key private to the failed attempt,
            # so cleanup cannot delete an object committed by a newer worker.
            try:
                self._storage.delete(key)
            except Exception:
                logger.warning(
                    "Could not clean up uncommitted execution archive object "
                    "%s.",
                    key,
                    exc_info=True,
                )
            raise

    def _verify_existing(
        self,
        claim: ExecutionArchiveClaim,
        capture: ExecutionArchiveCapture,
    ) -> None:
        archive = claim.archive
        if archive.object is None:
            raise ExecutionArchiveStateError(
                f"Verified archive {archive.id} has no object metadata."
            )
        load_archive_payload(
            storage=self._storage,
            object_key=self._catalog.object_key(archive.id),
            archive=archive,
            workspace_id=self._workspace_id,
        )
        self._require_unchanged(capture)

    def _require_unchanged(self, capture: ExecutionArchiveCapture) -> None:
        fresh = self._capturer.capture(
            project_id=capture.family.project_id,
            root_run_id=capture.family.root_run_id,
        )
        if fresh.source_fingerprint != capture.source_fingerprint:
            raise ExecutionArchiveParityError(
                "The execution tree changed during archive export."
            )

    def _clean_other_attempts(self, committed_key: str) -> None:
        try:
            self._storage.delete_other_attempts(committed_key)
        except Exception:
            # Verification is already durable. A later retry can safely
            # repeat this best-effort storage cleanup.
            logger.warning(
                "Could not clean up superseded execution archive write "
                "attempts beside %s.",
                committed_key,
                exc_info=True,
            )


def load_archive_payload(
    *,
    storage: ExecutionArchiveStorage,
    object_key: str,
    archive: ExecutionArchiveResponse,
    workspace_id: UUID,
) -> ExecutionArchivePayload:
    """Read and validate one generation's immutable archive object.

    Args:
        storage: Configured archive storage.
        object_key: Full immutable object key.
        archive: Catalog metadata for the generation.
        workspace_id: Immutable deployment namespace.

    Returns:
        Validated, self-contained execution payload.

    Raises:
        ExecutionArchiveStateError: If catalog metadata is incomplete or the
            configured target differs from the recorded target.
    """
    if storage.target_digest != archive.storage_target_digest:
        raise ExecutionArchiveStateError(
            "The configured execution archive target differs from the target "
            f"recorded by generation {archive.id}."
        )
    if archive.object is None:
        raise ExecutionArchiveStateError(
            f"Execution archive {archive.id} has no object metadata."
        )
    encoded = storage.read_verified(object_key, archive.object)
    return decode_archive_payload(
        encoded=encoded,
        object_=archive.object,
        archive=archive,
        workspace_id=workspace_id,
    )


def decode_archive_payload(
    *,
    encoded: bytes,
    object_: ExecutionArchiveObject,
    archive: ExecutionArchiveResponse,
    workspace_id: UUID,
) -> ExecutionArchivePayload:
    """Decode archive bytes and verify their complete semantic identity.

    Args:
        encoded: Verified compressed bytes.
        object_: Expected object metadata.
        archive: Catalog metadata for the generation.
        workspace_id: Immutable deployment namespace.

    Returns:
        Validated archive payload.

    Raises:
        ArchiveObjectInvalidError: If the decoded object violates its format
            or describes another generation.
    """
    decoded = decompress(encoded)
    if len(decoded) != object_.decoded_bytes:
        raise ArchiveObjectInvalidError(
            f"Execution archive {archive.id} decoded to {len(decoded)} bytes "
            f"instead of {object_.decoded_bytes}."
        )
    payload = parse_execution_archive_payload(decoded)
    expected = (
        archive.id,
        workspace_id,
        archive.project_id,
        archive.root_run_id,
        archive.generation,
        archive.source_fingerprint,
    )
    actual = (
        payload.archive_id,
        payload.workspace_id,
        payload.project_id,
        payload.root_run_id,
        payload.generation,
        payload.source_fingerprint,
    )
    if actual != expected:
        raise ArchiveObjectInvalidError(
            f"Execution archive {archive.id} describes another generation."
        )
    return payload
