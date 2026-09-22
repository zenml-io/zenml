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
"""Server-side execution retention: archive storage, policy, and admission.

The SQL store only reads and writes the database. Everything that also needs
the server's archive settings, the archive object storage, or this replica's
admission budget lives here. Permission checks stay in the routers, which is
why a targeted archive is split into expanding the target and archiving the
resulting batch: the router authorizes the expanded runs in between.
"""

from threading import Event
from typing import Optional
from uuid import UUID

from zenml.config.server_config import ArchiveSettings, ServerConfiguration
from zenml.enums import RestoreOutcome, RetentionOutcome
from zenml.exceptions import (
    ExecutionRetentionConflictError,
    ExecutionRetentionUnavailableError,
    IllegalOperationError,
)
from zenml.models import ArchiveRequest, ArchiveResponse, RestoreResponse
from zenml.zen_stores.retention.archiver import (
    ArchivePass,
    archive_runs,
    preview_runs,
)
from zenml.zen_stores.retention.capacity import (
    MAX_CONCURRENT_RETENTION_OPERATIONS,
    RetentionCapacity,
)
from zenml.zen_stores.retention.eligibility import ArchiveBatch, expand_target
from zenml.zen_stores.retention.restorer import restore_run
from zenml.zen_stores.retention.storage import ArchiveStorage
from zenml.zen_stores.sql_zen_store import SQLDatabaseDriver, SqlZenStore


class RetentionController:
    """Archive, preview, and restore pipeline runs for one server replica."""

    def __init__(
        self, store: SqlZenStore, storage: Optional[ArchiveStorage] = None
    ) -> None:
        """Bind the controller to the server's SQL store.

        Args:
            store: The server's SQL store.
            storage: Archive storage to use instead of the configured one.
        """
        self.store = store
        self._storage = storage
        self.capacity = RetentionCapacity(MAX_CONCURRENT_RETENTION_OPERATIONS)

    @property
    def archive_settings(self) -> ArchiveSettings:
        """Read the settings of a server that has archive storage.

        Returns:
            The configured archive settings.

        Raises:
            ExecutionRetentionUnavailableError: Archive storage is not
                configured.
        """
        settings = self._policy()
        if not settings.configured:
            raise ExecutionRetentionUnavailableError(
                "Execution archive storage is not configured on this server; "
                "ask your server administrator to set "
                "ZENML_SERVER_ARCHIVE__BACKEND and "
                "ZENML_SERVER_ARCHIVE__URI."
            )
        return settings

    @property
    def archive_storage(self) -> ArchiveStorage:
        """Create the storage named by the server's archive settings once.

        Returns:
            Storage rooted at the configured archive URI.
        """
        if self._storage is None:
            settings = self.archive_settings
            self._storage = ArchiveStorage.from_uri(
                settings.root_uri, connector_id=settings.connector_id
            )
        return self._storage

    def run_archive_sweep(
        self, cancel_event: Optional[Event] = None
    ) -> RetentionOutcome:
        """Run one bounded archive sweep, if no other replica is sweeping.

        Args:
            cancel_event: Cooperative scheduler shutdown signal.

        Returns:
            The sweep outcome.

        Raises:
            ExecutionRetentionConflictError: Scheduled archiving is switched
                off, or another replica holds the lease.
        """
        settings = self._settings_for_new_archives()
        if not settings.schedule_enabled:
            raise ExecutionRetentionConflictError(
                "Scheduled execution archiving is disabled by "
                "ZENML_SERVER_ARCHIVE__SCHEDULE_ENABLED. Use a manual archive "
                "request instead."
            )
        with self.capacity.claim():
            archive_pass = ArchivePass(
                self.store.engine,
                self.archive_storage,
                settings,
                cancel_event=cancel_event,
            )
            archive_pass.accept()
            return archive_pass.run().last_outcome

    def expand_target(self, request: ArchiveRequest) -> ArchiveBatch:
        """Resolve an archive request to the bounded batch of runs it names.

        This runs before the caller is authorized for those runs, so it only
        selects them. Whether the server can archive at all is checked in
        `archive_batch`, once the caller is known to be allowed to ask.

        Args:
            request: Runs, pipeline, or project to archive.

        Returns:
            The runs to authorize and then archive or preview.
        """
        return expand_target(
            self.store.engine,
            request,
            ServerConfiguration.get_server_config().archive,
        )

    def archive_batch(
        self, request: ArchiveRequest, batch: ArchiveBatch
    ) -> ArchiveResponse:
        """Archive or preview a batch the caller is authorized for.

        Args:
            request: The request the batch was expanded from.
            batch: Authorized runs to archive or preview.

        Returns:
            Counts and the runs that were refused, each with a reason.
        """
        if request.dry_run:
            # A preview never touches archive storage, so it works before
            # storage is configured and while new archiving is paused.
            result = preview_runs(
                self.store.engine,
                self._policy(),
                batch.run_ids,
                force=request.force,
            )
        else:
            settings = self._settings_for_new_archives()
            with self.capacity.claim():
                result = archive_runs(
                    self.store.engine,
                    self.archive_storage,
                    settings,
                    batch.run_ids,
                    force=request.force,
                )
        result.pending = batch.more
        result.next_after_run_id = batch.next_after_run_id
        return result

    def restore_pipeline_run(self, run_id: UUID) -> RestoreResponse:
        """Restore an archived run's detail within the request.

        Args:
            run_id: Authorized run.

        Returns:
            Restored, or a no-op when the run's detail is already in SQL.
        """
        run = self.store.get_run_header(run_id)
        if run.archive_bundle_id is None:
            return RestoreResponse(run_id=run.id, outcome=RestoreOutcome.NOOP)
        # `restore_run` checks the marker again under its own locks, so a
        # restore that finished while this one waited reports a no-op.
        with self.capacity.claim(key=("restore", run.id)):
            return restore_run(self.store.engine, self.archive_storage, run.id)

    def delete_pipeline_run(self, run_id: UUID) -> None:
        """Delete a run while preserving the detail of its surviving snapshot.

        Args:
            run_id: Run the caller is authorized to delete.
        """
        self.restore_pipeline_run(run_id)
        self.store.delete_run(run_id)

    def _policy(self) -> ArchiveSettings:
        """Read the retention policy of a server that can apply it.

        Returns:
            The server's archive settings, whether or not storage is
            configured.

        Raises:
            IllegalOperationError: The metadata database is not MySQL.
        """
        if self.store.config.driver != SQLDatabaseDriver.MYSQL:
            raise IllegalOperationError(
                "Execution archiving requires a MySQL database."
            )
        return ServerConfiguration.get_server_config().archive

    def _settings_for_new_archives(self) -> ArchiveSettings:
        """Read the settings of a server that may create archives now.

        Returns:
            The configured archive settings.

        Raises:
            ExecutionRetentionConflictError: New archive creation is paused.
        """
        settings = self.archive_settings
        if not settings.enabled:
            raise ExecutionRetentionConflictError(
                "New execution archiving is paused by "
                "ZENML_SERVER_ARCHIVE__ENABLED. Existing archives remain "
                "restorable, and `dry_run` still previews the current policy."
            )
        return settings
