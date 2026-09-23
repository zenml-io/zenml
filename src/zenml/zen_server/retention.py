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
"""Server policy and admission around the SQL store's retention operations.

The SQL store owns every retention algorithm and receives archive storage
through its `ArchiveStorage` port. This module only decides whether this
server may run an operation now, bounds how many run at once on this replica,
and hands the store the server's storage adapter. Permission checks stay in
the routers, which is why a targeted archive is selected by the store, then
authorized, and only then archived.
"""

from contextlib import contextmanager
from threading import BoundedSemaphore, Lock
from typing import Hashable, Iterator, Optional, Set
from uuid import UUID

from zenml.config.server_config import ArchiveSettings, ServerConfiguration
from zenml.enums import RestoreOutcome
from zenml.exceptions import (
    ExecutionRetentionBusyError,
    ExecutionRetentionConflictError,
    ExecutionRetentionUnavailableError,
    IllegalOperationError,
)
from zenml.models import ArchiveRequest, ArchiveResponse, RestoreResponse
from zenml.zen_server.utils import (
    archive_storage,
    retention_capacity,
    zen_store,
)
from zenml.zen_stores.retention.eligibility import ArchiveBatch

MAX_CONCURRENT_RETENTION_OPERATIONS = 4


class RetentionCapacity:
    """Bound aggregate retention work and duplicate keyed operations."""

    def __init__(self, max_operations: int) -> None:
        """Create a fixed process-local capacity budget.

        Args:
            max_operations: Maximum admitted payload operations.

        Raises:
            ValueError: If the capacity is not positive.
        """
        if max_operations < 1:
            raise ValueError("Retention capacity must be positive.")
        self.max_operations = max_operations
        self._semaphore = BoundedSemaphore(max_operations)
        self._keys: Set[Hashable] = set()
        self._lock = Lock()

    @contextmanager
    def claim(self, key: Optional[Hashable] = None) -> Iterator[None]:
        """Claim capacity without queuing more payload work.

        Args:
            key: Optional operation identity that may only run once at a time.

        Yields:
            Control while the claim is held.

        Raises:
            ExecutionRetentionBusyError: If the process budget or key is busy.
        """
        with self._lock:
            if key is not None and key in self._keys:
                raise ExecutionRetentionBusyError(
                    "This execution-retention operation is already running."
                )
            if not self._semaphore.acquire(blocking=False):
                raise ExecutionRetentionBusyError(
                    "This server replica is at its execution-retention "
                    "capacity. Retry the operation later."
                )
            if key is not None:
                self._keys.add(key)
        try:
            yield
        finally:
            with self._lock:
                if key is not None:
                    self._keys.remove(key)
                self._semaphore.release()


def retention_policy() -> ArchiveSettings:
    """Read the retention policy of a server that can apply it.

    Returns:
        The server's archive settings, whether or not storage is configured.

    Raises:
        IllegalOperationError: The metadata database cannot run retention.
    """
    if not zen_store().supports_execution_retention:
        raise IllegalOperationError(
            "Execution archiving requires a MySQL database."
        )
    return ServerConfiguration.get_server_config().archive


def archive_settings() -> ArchiveSettings:
    """Read the settings of a server that has archive storage.

    Returns:
        The configured archive settings.

    Raises:
        ExecutionRetentionUnavailableError: Archive storage is not
            configured.
    """
    settings = retention_policy()
    if not settings.configured:
        raise ExecutionRetentionUnavailableError(
            "Execution archive storage is not configured on this server; "
            "ask your server administrator to set "
            "ZENML_SERVER_ARCHIVE__BACKEND and ZENML_SERVER_ARCHIVE__URI."
        )
    return settings


def new_archive_settings() -> ArchiveSettings:
    """Read the settings of a server that may create archives now.

    Returns:
        The configured archive settings.

    Raises:
        ExecutionRetentionConflictError: New archive creation is paused.
    """
    settings = archive_settings()
    if not settings.enabled:
        raise ExecutionRetentionConflictError(
            "New execution archiving is paused by "
            "ZENML_SERVER_ARCHIVE__ENABLED. Existing archives remain "
            "restorable, and `dry_run` still previews the current policy."
        )
    return settings


def archive_batch(
    request: ArchiveRequest, batch: ArchiveBatch
) -> ArchiveResponse:
    """Archive or preview a batch the caller is authorized for.

    Args:
        request: The request the batch was selected for.
        batch: Authorized runs to archive or preview.

    Returns:
        Counts and the runs that were refused, each with a reason.
    """
    store = zen_store()
    if request.dry_run:
        # A preview never touches archive storage, so it works before storage
        # is configured and while new archiving is paused.
        result = store.preview_archive(
            batch.run_ids, retention_policy(), force=request.force
        )
    else:
        settings = new_archive_settings()
        with retention_capacity().claim():
            result = store.archive_runs(
                batch.run_ids,
                storage=archive_storage(),
                settings=settings,
                force=request.force,
            )
    result.pending = batch.more
    result.next_after_run_id = batch.next_after_run_id
    return result


def restore_pipeline_run(run_id: UUID) -> RestoreResponse:
    """Restore an archived run's detail within the request.

    A run whose detail is in SQL is answered without touching storage or
    capacity, so deleting an ordinary run never depends on archive storage.

    Args:
        run_id: Authorized run.

    Returns:
        Restored, or a no-op when the run's detail is already in SQL.
    """
    store = zen_store()
    if store.get_run_header(run_id).archive_bundle_id is None:
        return RestoreResponse(run_id=run_id, outcome=RestoreOutcome.NOOP)
    # The store checks the marker again under its own locks, so a restore
    # that finished while this one waited reports a no-op.
    with retention_capacity().claim(key=("restore", run_id)):
        return store.restore_pipeline_run(run_id, storage=archive_storage())


def delete_pipeline_run(run_id: UUID) -> None:
    """Delete a run while preserving the detail of its surviving snapshot.

    Args:
        run_id: Run the caller is authorized to delete.
    """
    restore_pipeline_run(run_id)
    zen_store().delete_run(run_id)


def delete_unused_archive_objects() -> None:
    """Remove deleted runs' objects after the deletion response is sent.

    This is a best-effort background task. Failed deletions keep their catalog
    entries for a later cleanup; they do not roll back the database deletion.
    """
    from zenml.logger import get_logger

    if (
        not zen_store().supports_execution_retention
        or not ServerConfiguration.get_server_config().archive.configured
    ):
        return
    try:
        with retention_capacity().claim(key="archive-cleanup"):
            zen_store().delete_unused_archive_objects(archive_storage())
    except Exception as error:
        get_logger(__name__).warning(
            "Archive object cleanup failed (%s); catalog entries remain for retry.",
            type(error).__name__,
        )
