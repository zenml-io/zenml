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
"""Execution payload backfill of ZenML servers, and its command.

Every server runs the backfill once it is due (see `PayloadBackfillTask`).
The command runs where the server runs, with its configuration, to report,
to run the backfill by hand, or to rebuild the tables afterwards. For example:

    python -m zenml.zen_server.payload_backfill_runner --report
    python -m zenml.zen_server.payload_backfill_runner
"""

import argparse
import asyncio
import sys
import threading
from datetime import timedelta
from typing import Optional

from zenml.config.global_config import GlobalConfiguration
from zenml.enums import StoreType
from zenml.exceptions import EntityCreationError
from zenml.logger import get_logger
from zenml.utils.string_utils import (
    get_human_readable_filesize,
    get_human_readable_time,
)
from zenml.utils.time_utils import exponential_backoff_delays, utc_now
from zenml.zen_stores.base_zen_store import BaseZenStore
from zenml.zen_stores.payload_backfill import (
    BACKFILL_BATCH_SIZE,
    BACKFILL_GATE_SETTLE_SECONDS,
    BACKFILL_PAUSE_SECONDS,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore

logger = get_logger(__name__)

PAYLOAD_BACKFILL_RETRY_SECONDS = 60
PAYLOAD_BACKFILL_MAX_RETRY_SECONDS = 60 * 60


class _BackfillIncompleteError(Exception):
    """A backfill run that was not stopped ended without completing."""


class PayloadBackfillTask:
    """Runs the payload backfill in the server, once it is due.

    Every server starts this task. The backfill is due a delay after the
    database got execution payloads: a buffer for the rolling upgrade to
    replace the servers of older releases, which cannot read references.
    Every server derives that time from the database, so a restart does not
    move it. One server at a time runs the backfill, and retries with
    backoff until it records completion; the other servers then stop.
    """

    def __init__(self, store: SqlZenStore, delay_seconds: int) -> None:
        """Initialize the task.

        Args:
            store: The store to backfill.
            delay_seconds: The seconds after the database got execution
                payloads until the backfill is due. 0 never runs it.
        """
        self._store = store
        self._delay_seconds = delay_seconds
        self._task: Optional[asyncio.Task[None]] = None
        self._shutdown = asyncio.Event()
        # Stops a backfill running in a worker thread after its current batch.
        self._stop = threading.Event()

    def start(self) -> None:
        """Start the task, unless its delay is 0."""
        if self._delay_seconds:
            self._task = asyncio.create_task(self._run())

    async def shutdown(self) -> None:
        """Stop the task, and the backfill it runs after its current batch."""
        self._shutdown.set()
        self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _run(self) -> None:
        """Run the backfill once it is due, until it completes."""
        retry_delays = exponential_backoff_delays(
            initial_delay=PAYLOAD_BACKFILL_RETRY_SECONDS,
            max_delay=PAYLOAD_BACKFILL_MAX_RETRY_SECONDS,
            jitter="equal",
        )
        wait: Optional[float] = 0
        try:
            while wait is not None and not await self._wait_for_shutdown(wait):
                try:
                    wait = await asyncio.to_thread(self._run_if_due)
                except Exception as e:
                    wait = next(retry_delays)
                    retry_at = utc_now() + timedelta(seconds=wait)
                    logger.warning(
                        "The payload backfill did not complete: %s. It "
                        "retries in %s, at %s UTC. `python -m "
                        "zenml.zen_server.payload_backfill_runner --report` "
                        "shows what remains.",
                        str(e).rstrip("."),
                        get_human_readable_time(wait),
                        retry_at.strftime("%Y-%m-%d %H:%M:%S"),
                        exc_info=not isinstance(e, _BackfillIncompleteError),
                    )
                if wait == 0:
                    wait = next(retry_delays)
        finally:
            # Also when the task is cancelled: the thread would otherwise run
            # the backfill to its end and hold up the process exit.
            self._stop.set()

    async def _wait_for_shutdown(self, seconds: float) -> bool:
        """Wait until the server shuts down, for at most some seconds.

        Args:
            seconds: The most seconds to wait.

        Returns:
            Whether the server shuts down.
        """
        try:
            await asyncio.wait_for(self._shutdown.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            return False
        return True

    def _run_if_due(self) -> Optional[float]:
        """Run the backfill if it is due and no other server runs it.

        Returns:
            None once the backfill has completed, the seconds until it is
            due, or 0 to try again later.

        Raises:
            _BackfillIncompleteError: If the backfill ran, was not stopped,
                and did not complete.
        """
        if self._store.get_payload_backfill_completion():
            return None
        added = self._store.get_execution_payloads_added()
        remaining = 0.0
        if added:
            due = added + timedelta(seconds=self._delay_seconds)
            remaining = (due - utc_now(tz_aware=added)).total_seconds()
        if remaining > 0:
            logger.info(
                "The payload backfill starts in %s.",
                get_human_readable_time(remaining),
            )
            return remaining
        with self._store.payload_backfill_lock() as acquired:
            if not acquired:
                logger.info("Another process is running the payload backfill.")
                return 0
            # Another server may have completed it in the meantime.
            if self._store.get_payload_backfill_completion():
                return None
            result = self._store.backfill_payloads(stop=self._stop)
        if result.completed:
            logger.info("The payload backfill completed.")
            return None
        if not self._stop.is_set():
            raise _BackfillIncompleteError(result.incomplete_reason)
        logger.info(
            "The payload backfill stopped with the server. It continues when "
            "a server starts."
        )
        return 0


def main() -> None:
    """Move the payloads of existing rows to the payload table, or report.

    Exits with status 1 if asked to rebuild the tables before the backfill
    has completed, without `--force`.
    """
    args = _parse_args()
    store = _open_store()
    if args.report:
        _report(store)
        return
    completed = store.get_payload_backfill_completion()
    if args.optimize_tables and not completed and not args.force:
        logger.error(
            "The backfill has not completed, so the tables are not rebuilt. "
            "Rebuild them once it has completed; `--report` shows what "
            "remains."
        )
        sys.exit(1)
    if args.force or not completed:
        _backfill(store, args)
    elif args.optimize_tables:
        logger.info("The backfill completed on %s.", completed)
        _optimize_tables(store)
    else:
        logger.info(
            "The backfill completed on %s, so there is nothing to do. "
            "`--force` runs it again.",
            completed,
        )


def _parse_args() -> argparse.Namespace:
    """Parse and check the command line arguments.

    Exits with status 2 if an argument is invalid.

    Returns:
        The arguments.
    """
    parser = argparse.ArgumentParser(
        description="Store the execution payloads that existing rows hold "
        "inline in the payload table, and turn on payload references for "
        "new rows. Servers run it themselves once it is due. Run it only "
        "once every server, and every other process that opens the "
        "database, runs a release that reads payload references: releases "
        "before execution payloads cannot. "
        "Safe to stop and to run again."
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Only report the rows that remain, without writing anything or "
        "changing any setting. Reads each table in full.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BACKFILL_BATCH_SIZE,
        help="Rows each batch reads.",
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=BACKFILL_PAUSE_SECONDS,
        help="Seconds to wait after each batch that updated rows.",
    )
    parser.add_argument(
        "--gate-settle-seconds",
        type=float,
        default=BACKFILL_GATE_SETTLE_SECONDS,
        help="Seconds to wait between turning payload references on and "
        "the first pass, so that requests that started before have "
        "finished and the passes need no repeat for them. Rows written "
        "inline later are still caught by the repeated passes.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even if a previous run left nothing to update, such as "
        "after a process wrote payloads inline again.",
    )
    parser.add_argument(
        "--optimize-tables",
        action="store_true",
        help="Once the backfill has completed, rebuild the tables it "
        "updated so that the database releases the disk space of the moved "
        "payloads (MySQL and MariaDB). Needs free disk space about the size "
        "of the largest table. Refused before the backfill has completed; "
        "with `--force`, the backfill runs first and the tables are rebuilt "
        "if it completes.",
    )
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be 1 or more.")
    if min(args.pause_seconds, args.gate_settle_seconds) < 0:
        parser.error("Durations cannot be negative.")
    return args


def _open_store() -> SqlZenStore:
    """Open the server's SQL store, which must be migrated to this release.

    Exits with status 1 if the store is not a SQL store or its database is
    not migrated to this release.

    Returns:
        The store.
    """
    store_config = GlobalConfiguration().store_configuration
    if store_config.type != StoreType.SQL:
        logger.error("The payload backfill requires a SQL store.")
        sys.exit(1)
    # Never migrates: the database must already be at this release.
    store = BaseZenStore.create_store(
        store_config, skip_default_registrations=True, skip_migrations=True
    )
    assert isinstance(store, SqlZenStore)
    if set(store.alembic.current_revisions()) != set(
        store.alembic.head_revisions()
    ):
        logger.error(
            "The database is not migrated to this release: run the database "
            "migration first."
        )
        sys.exit(1)
    return store


def _report(store: SqlZenStore) -> None:
    """Log what the backfill still has to update.

    Args:
        store: The store to report on.
    """
    completed = store.get_payload_backfill_completion()
    logger.info("Last completed: %s.", completed or "never")
    for report in store.get_payload_backfill_report():
        logger.info(
            "`%s`: %d rows to update, inline payload bytes: %s",
            report.table,
            report.pending_rows,
            report.inline_bytes,
        )


def _backfill(store: SqlZenStore, args: argparse.Namespace) -> None:
    """Run the backfill, then rebuild the tables if asked to.

    Exits with status 1 if a server runs the backfill, or the backfill
    stops or does not complete.

    Args:
        store: The store to backfill.
        args: The command line arguments.
    """
    try:
        with store.payload_backfill_lock() as acquired:
            if not acquired:
                logger.error(
                    "A server is running the backfill: its log shows the "
                    "progress, and `--report` what remains."
                )
                sys.exit(1)
            result = store.backfill_payloads(
                batch_size=args.batch_size,
                pause_seconds=args.pause_seconds,
                gate_settle_seconds=args.gate_settle_seconds,
            )
    except (EntityCreationError, RuntimeError) as e:
        logger.error(
            "The backfill stopped: %s Running it again continues where it "
            "stopped.",
            e,
        )
        sys.exit(1)
    if not result.completed:
        logger.error(
            "The backfill did not complete: %s. Run it again; `--report` "
            "shows what remains.",
            result.incomplete_reason,
        )
        sys.exit(1)
    logger.info("The backfill completed.")
    if args.optimize_tables:
        _optimize_tables(store)


def _optimize_tables(store: SqlZenStore) -> None:
    """Rebuild the payload tables and log the space each one released.

    Args:
        store: The store whose tables to rebuild.
    """
    logger.info("Rebuilding the payload tables to release disk space.")
    tables = store.optimize_payload_tables()
    if not tables:
        logger.info("Only MySQL and MariaDB tables need rebuilding.")
    for table in tables:
        logger.info(
            "`%s`: %s before, %s after, rebuilt in %s.",
            table.table,
            get_human_readable_filesize(table.bytes_before),
            get_human_readable_filesize(table.bytes_after),
            get_human_readable_time(table.seconds),
        )


if __name__ == "__main__":
    main()
