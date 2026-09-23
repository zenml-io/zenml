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
    ExecutionArchivedError,
    ExecutionRetentionBusyError,
    ExecutionRetentionConflictError,
    ExecutionRetentionUnavailableError,
    MaxConcurrentTasksError,
)
from zenml.logger import get_logger
from zenml.models import (
    ArchiveRequest,
    ArchiveResponse,
    PipelineRunResponse,
    RestoreResponse,
)
from zenml.zen_server.archive_storage import ArtifactStoreArchiveStorage
from zenml.zen_server.utils import submit_maintenance_task, zen_store
from zenml.zen_stores.retention.eligibility import ArchiveBatch

logger = get_logger(__name__)

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


# One budget and one storage client per replica. The storage is created on
# first use, so a server without archive storage still serves everything
# that needs none.
_capacity = RetentionCapacity(MAX_CONCURRENT_RETENTION_OPERATIONS)
_storage: Optional[ArtifactStoreArchiveStorage] = None


def retention_policy() -> ArchiveSettings:
    """Read the retention policy of a server that can apply it.

    Returns:
        The server's archive settings, whether or not storage is configured.
    """
    zen_store().require_execution_retention()
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
            "ZENML_SERVER_ARCHIVE__URI."
        )
    return settings


def archive_storage() -> ArtifactStoreArchiveStorage:
    """Return the archive storage named by the server's settings.

    Returns:
        Storage rooted at the configured archive URI.
    """
    global _storage
    if _storage is None:
        settings = archive_settings()
        _storage = ArtifactStoreArchiveStorage.from_uri(settings.root_uri)
    return _storage


def initialize_retention() -> None:
    """Validate configured retention without contacting object storage.

    Raises:
        IllegalOperationError: Archiving is configured on an unsupported database.
    """  # noqa: DOC502
    if ServerConfiguration.get_server_config().archive.configured:
        archive_settings()


def archive_batch(
    request: ArchiveRequest, batch: ArchiveBatch
) -> ArchiveResponse:
    """Archive or preview a batch the caller is authorized for.

    Args:
        request: The request the batch was selected for.
        batch: Authorized runs to archive or preview.

    Returns:
        Counts and the runs that were refused, each with a reason.

    Raises:
        ExecutionRetentionConflictError: New archive creation is paused.
    """
    store = zen_store()
    if request.dry_run:
        # A preview never touches archive storage, so it works before storage
        # is configured and while new archiving is paused.
        result = store.preview_archive(
            batch.run_ids, retention_policy(), force=request.force
        )
    else:
        settings = archive_settings()
        if not settings.enabled:
            raise ExecutionRetentionConflictError(
                "New execution archiving is paused by "
                "ZENML_SERVER_ARCHIVE__ENABLED. Existing archives remain "
                "restorable, and `dry_run` still previews the current policy."
            )
        with _capacity.claim():
            result = store.archive_runs(
                batch.run_ids,
                storage=archive_storage(),
                settings=settings,
                force=request.force,
            )
    result.pending = batch.more
    result.next_after_run_id = batch.next_after_run_id
    return result


def restore_pipeline_run(run: PipelineRunResponse) -> RestoreResponse:
    """Restore an archived run's detail within the request.

    A run whose detail is in SQL is answered without touching storage or
    capacity.

    Args:
        run: Header of the authorized run.

    Returns:
        Restored, or a no-op when the run's detail is already in SQL.
    """
    if run.archive_bundle_id is None:
        return RestoreResponse(run_id=run.id, outcome=RestoreOutcome.NOOP)
    # The store checks the marker again under its own locks, so a restore
    # that finished while this one waited reports a no-op.
    with _capacity.claim(key=("restore", run.id)):
        return zen_store().restore_pipeline_run(
            run.id, storage=archive_storage()
        )


def delete_pipeline_run(run_id: UUID) -> None:
    """Delete a run while preserving the detail of its surviving snapshot.

    The store refuses to delete an archived run under its row lock, so only
    that case pays for a restore, and an ordinary deletion never depends on
    archive storage.

    Args:
        run_id: Run the caller is authorized to delete.
    """
    store = zen_store()
    try:
        store.delete_run(run_id)
    except ExecutionArchivedError:
        restore_pipeline_run(store.get_run_header(run_id))
        store.delete_run(run_id)


def schedule_archive_cleanup() -> None:
    """Submit bounded object cleanup after SQL deletion has committed.

    Busy or stopping workers leave catalog entries for a later deletion to
    retry, without turning the committed deletion into an error response.
    """
    store = zen_store()
    if (
        not store.supports_execution_retention
        or not ServerConfiguration.get_server_config().archive.configured
    ):
        return

    def cleanup() -> None:
        try:
            with _capacity.claim():
                store.delete_unused_archive_objects(archive_storage())
        except ExecutionRetentionBusyError:
            logger.debug(
                "Archive cleanup deferred: retention capacity is busy."
            )

    try:
        submit_maintenance_task(cleanup)
    except MaxConcurrentTasksError:
        logger.debug("Archive cleanup deferred: maintenance executor is busy.")
    except Exception as error:
        logger.warning(
            "Could not schedule archive cleanup (%s); catalog entries remain "
            "for retry.",
            type(error).__name__,
        )
