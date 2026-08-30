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
"""Archiving one execution family: export, verify, switch authority, compact.

An export writes the family's two payload objects and its manifest, reads
them back and compares a fresh capture of SQL with what was written; the
generation ends `VERIFIED` and SQL stays authoritative. Every operation
claims the generation first, so two workers never work on one generation
at once. Compaction — making the archive authoritative and clearing SQL —
ships separately, once every server replica can read archived payload.
"""

import os
import socket
from datetime import datetime, timedelta
from typing import Callable, Optional
from uuid import UUID, uuid4

from sqlalchemy.engine import Engine

from zenml.constants import (
    DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_FAMILY_STORED_BYTES,
)
from zenml.enums import ExecutionArchiveState
from zenml.exceptions import ArchiveUnavailableError
from zenml.models import ExecutionArchiveResponse
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.execution_archive.capture import (
    ExecutionArchiveCapture,
    ExecutionArchiveCapturer,
    ExecutionArchiveFamily,
)
from zenml.zen_stores.execution_archive.catalog import ExecutionArchiveCatalog
from zenml.zen_stores.execution_archive.codec import canonical_json
from zenml.zen_stores.execution_archive.eligibility import (
    evaluate_eligibility,
)
from zenml.zen_stores.execution_archive.exceptions import (
    ChecksumMismatchError,
    ExecutionArchiveNotEligibleError,
    ExecutionArchiveParityError,
    ExecutionArchiveStateError,
)
from zenml.zen_stores.execution_archive.models import (
    ArchiveObjectKind,
    ExecutionArchiveManifest,
)
from zenml.zen_stores.execution_archive.storage import (
    BaseExecutionArchiveObjectStore,
)
from zenml.zen_stores.execution_archive.targets import ExecutionArchiveTargets

DEFAULT_BATCH_SIZE = 500
# A claim outlives any single batch by far; it is renewed after every one.
DEFAULT_CLAIM_SECONDS = 15 * 60


class ExecutionArchiver:
    """Exports, compacts and restores one execution family at a time."""

    def __init__(
        self,
        engine: Engine,
        *,
        targets: ExecutionArchiveTargets,
        workspace_id: UUID,
        writer_version: str,
        writer_alembic_revision: str,
        clock: Callable[[], datetime] = utc_now,
        batch_size: int = DEFAULT_BATCH_SIZE,
        claim_seconds: float = DEFAULT_CLAIM_SECONDS,
        max_stored_bytes: int = (
            DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_FAMILY_STORED_BYTES
        ),
    ) -> None:
        """Initialize the archiver.

        Args:
            engine: The SQL store engine.
            targets: The storage targets.
            workspace_id: The workspace the archives belong to.
            writer_version: The ZenML version writing archives.
            writer_alembic_revision: The database revision written from.
            clock: Source of the current time.
            batch_size: Rows moved per transaction during compaction.
            claim_seconds: How long a claim on a generation lasts.
            max_stored_bytes: The largest payload that may be archived.
        """
        self._engine = engine
        self._targets = targets
        self._workspace_id = workspace_id
        self._writer_version = writer_version
        self._writer_alembic_revision = writer_alembic_revision
        self._clock = clock
        self._batch_size = batch_size
        self._claim_seconds = claim_seconds
        self._max_stored_bytes = max_stored_bytes
        self._owner = f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
        self._catalog = ExecutionArchiveCatalog(engine)
        self._captures = ExecutionArchiveCapturer(
            engine, max_stored_bytes=max_stored_bytes
        )

    def export(
        self,
        *,
        project_id: UUID,
        root_run_id: UUID,
        older_than: timedelta,
        capture: Optional[ExecutionArchiveCapture] = None,
    ) -> ExecutionArchiveResponse:
        """Write the family's objects and verify them against fresh SQL.

        SQL payload is not touched. The generation ends `VERIFIED`, or
        `FAILED` / `CORRUPT` with the error recorded. Exporting a verified
        generation again re-reads and re-checks it; an authoritative one is
        returned as it is.

        Args:
            project_id: The project of the family.
            root_run_id: The root run of the family.
            older_than: How long the family must have been unchanged.
            capture: A capture of the family taken moments ago, to avoid
                reading it again.

        Returns:
            The generation.

        Raises:
            ExecutionArchiveParityError: If the stored manifest or a fresh
                capture differ from what was exported.
            Exception: Whatever stopped the export, after it was recorded.
        """
        latest = self._catalog.latest_for_root(root_run_id)
        if latest is not None and latest.state.is_authoritative:
            return latest
        capture = capture or self._captures.capture(
            project_id=project_id, root_run_id=root_run_id
        )
        self._require_eligible(capture.family, older_than)
        archive = self._catalog.begin_export(
            project_id=project_id,
            root_run_id=root_run_id,
            generation=_next_generation(latest, capture.source_fingerprint),
            source_fingerprint=capture.source_fingerprint,
            storage_target_id=self._targets.current(),
            stored_bytes=capture.family.stored_bytes,
        )
        self._claim(archive.id)
        try:
            store = self._targets.object_store(archive.storage_target_id)
            if archive.state == ExecutionArchiveState.VERIFIED:
                manifest = self._read_manifest(archive, store)
            else:
                manifest = self._export(archive, capture, store)
                archive = self._catalog.require(archive.id)
                if self._read_manifest(archive, store) != manifest:
                    raise ExecutionArchiveParityError(
                        "The stored manifest differs from the exported one."
                    )
            fresh = self._captures.capture(
                project_id=project_id, root_run_id=root_run_id
            )
            if fresh.source_fingerprint != manifest.source_fingerprint:
                raise ExecutionArchiveParityError(
                    "The execution payload changed during the export."
                )
            self._catalog.mark_verified(archive.id)
        except ChecksumMismatchError as e:
            self._catalog.mark_failed(
                archive.id, ExecutionArchiveState.CORRUPT, str(e)
            )
            raise
        except ArchiveUnavailableError as e:
            # The objects could not be read right now; a verified generation
            # stays verified and is checked again on a later pass.
            if archive.state == ExecutionArchiveState.VERIFIED:
                self._catalog.record_error(archive.id, str(e))
            else:
                self._catalog.mark_failed(
                    archive.id, ExecutionArchiveState.FAILED, str(e)
                )
            raise
        except Exception as e:
            self._catalog.mark_failed(
                archive.id, ExecutionArchiveState.FAILED, str(e)
            )
            raise
        finally:
            self._catalog.release(archive.id, owner=self._owner)
        return self._catalog.require(archive.id)

    def _claim(self, archive_id: UUID) -> None:
        self._catalog.claim(
            archive_id, owner=self._owner, seconds=self._claim_seconds
        )

    def _export(
        self,
        archive: ExecutionArchiveResponse,
        capture: ExecutionArchiveCapture,
        store: BaseExecutionArchiveObjectStore,
    ) -> ExecutionArchiveManifest:
        """Write the payload objects and the manifest of a generation.

        Args:
            archive: The generation in `EXPORTING`.
            capture: The captured family.
            store: The object store of the generation's target.

        Returns:
            The manifest as written.

        Raises:
            ExecutionArchiveParityError: If the store returned references
                other than the ones computed from the captured bytes.
        """
        execution = store.put_if_absent(
            ArchiveObjectKind.EXECUTION,
            archive.project_id,
            capture.execution_compressed,
        )
        snapshots = store.put_if_absent(
            ArchiveObjectKind.SNAPSHOT,
            archive.project_id,
            capture.snapshot_compressed,
        )
        if (execution, snapshots) != (
            capture.execution_object,
            capture.snapshot_object,
        ):
            raise ExecutionArchiveParityError(
                "The stored payload objects differ from the captured ones."
            )
        family = capture.family
        manifest = ExecutionArchiveManifest(
            archive_id=archive.id,
            workspace_id=self._workspace_id,
            project_id=archive.project_id,
            root_run_id=archive.root_run_id,
            generation=archive.generation,
            writer_version=self._writer_version,
            writer_alembic_revision=self._writer_alembic_revision,
            source_fingerprint=capture.source_fingerprint,
            run_ids=family.run_ids,
            step_run_ids=family.step_run_ids,
            snapshot_ids=family.snapshot_ids,
            static_configuration_ids=family.static_configuration_ids,
            table_counts=family.table_counts,
            storage_target_id=archive.storage_target_id,
            execution_payload=execution,
            snapshot_payload=snapshots,
            created_at=self._clock(),
        )
        self._catalog.record_objects(
            archive.id,
            manifest=store.put_if_absent(
                ArchiveObjectKind.MANIFEST,
                archive.project_id,
                canonical_json(manifest),
            ),
            execution=execution,
            snapshots=snapshots,
        )
        return manifest

    @staticmethod
    def _read_manifest(
        archive: ExecutionArchiveResponse,
        store: BaseExecutionArchiveObjectStore,
    ) -> ExecutionArchiveManifest:
        if archive.manifest is None:
            raise ExecutionArchiveStateError(
                f"Execution archive {archive.id} has no manifest."
            )
        manifest = store.read_manifest(archive.project_id, archive.manifest)
        if (
            manifest.archive_id,
            manifest.project_id,
            manifest.root_run_id,
            manifest.generation,
            manifest.storage_target_id,
        ) != (
            archive.id,
            archive.project_id,
            archive.root_run_id,
            archive.generation,
            archive.storage_target_id,
        ):
            raise ExecutionArchiveParityError(
                f"The manifest of execution archive {archive.id} describes a "
                "different archive."
            )
        return manifest

    def _require_eligible(
        self, family: ExecutionArchiveFamily, older_than: timedelta
    ) -> None:
        eligibility = evaluate_eligibility(
            family,
            now=self._clock(),
            older_than=older_than,
            max_stored_bytes=self._max_stored_bytes,
        )
        if not eligibility.eligible:
            raise ExecutionArchiveNotEligibleError(
                "The execution family cannot be archived: "
                + ", ".join(eligibility.blockers)
                + "."
            )


def _next_generation(
    latest: Optional[ExecutionArchiveResponse], source_fingerprint: str
) -> int:
    """Pick the generation to write: resume the latest one if it still fits.

    Args:
        latest: The latest generation of the family, if any.
        source_fingerprint: The fingerprint of the family now.

    Returns:
        The generation number.
    """
    if latest is None:
        return 1
    if (
        latest.state
        in (
            ExecutionArchiveState.RESTORED,
            ExecutionArchiveState.CORRUPT,
        )
        or latest.source_fingerprint != source_fingerprint
    ):
        return latest.generation + 1
    return latest.generation
