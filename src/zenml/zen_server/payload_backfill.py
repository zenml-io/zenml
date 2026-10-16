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
"""Execution payload backfill entry point for ZenML server deployments.

Runs where the server runs, with its configuration and cloud identity: in a
server container or pod, or in a job built like one, as the Helm chart does
once offloading is enabled. For example:

    python -m zenml.zen_server.payload_backfill --report
    python -m zenml.zen_server.payload_backfill
"""

import argparse
import os
import sys
import time

from zenml.config.global_config import GlobalConfiguration
from zenml.constants import ENV_ZENML_DISABLE_DATABASE_MIGRATION
from zenml.enums import StoreType
from zenml.exceptions import (
    IllegalOperationError,
    NonRetryablePayloadStorageError,
    PayloadStorageUnavailableError,
)
from zenml.logger import get_logger
from zenml.zen_stores.base_zen_store import BaseZenStore
from zenml.zen_stores.payload_storage.backfill import (
    BACKFILL_BATCH_SIZE,
    BACKFILL_PAUSE_SECONDS,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore

logger = get_logger(__name__)


def main() -> None:
    """Offload the payloads of existing rows, or report what remains."""
    parser = argparse.ArgumentParser(
        description="Offload the execution payloads that existing rows hold "
        "inline to payload storage. Safe to stop and to run again."
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Only report the rows that remain, without writing anything. "
        "Reads each table in full.",
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
        "--start-delay-seconds",
        type=float,
        default=0,
        help="Seconds to wait before starting, such as for the rolling "
        "restart that enabled offloading to replace every server.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even if a previous run left nothing to update, such as "
        "after offloading was disabled and enabled again.",
    )
    parser.add_argument(
        "--optimize-tables",
        action="store_true",
        help="Once the backfill has completed, rebuild the tables it "
        "updated so that the database releases the disk space of the "
        "offloaded payloads (MySQL and MariaDB). Needs free disk space "
        "about the size of the largest table.",
    )
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be 1 or more.")
    if args.pause_seconds < 0 or args.start_delay_seconds < 0:
        parser.error(
            "--pause-seconds and --start-delay-seconds cannot be negative."
        )

    store_config = GlobalConfiguration().store_configuration
    if store_config.type != StoreType.SQL:
        logger.error("The payload backfill requires a SQL store.")
        sys.exit(1)
    # Never migrates. Not through `skip_migrations`, which also skips the
    # payload storage location check.
    os.environ[ENV_ZENML_DISABLE_DATABASE_MIGRATION] = "true"
    store = BaseZenStore.create_store(
        store_config, skip_default_registrations=True
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

    completed = store.get_payload_backfill_completion()
    if args.report:
        logger.info("Last completed: %s.", completed or "never")
        for report in store.get_payload_backfill_report():
            logger.info(
                "`%s`: %d rows to update, inline payload bytes: %s",
                report.table,
                report.pending_rows,
                report.inline_bytes,
            )
        return
    if completed and not args.force:
        logger.info(
            "The backfill completed on %s, so there is nothing to do. "
            "`--force` runs it again.",
            completed,
        )
        if args.optimize_tables:
            _optimize_tables(store)
        return
    if args.start_delay_seconds:
        logger.info(
            "Starting the backfill in %.0f seconds.", args.start_delay_seconds
        )
        time.sleep(args.start_delay_seconds)

    try:
        result = store.backfill_payloads(
            batch_size=args.batch_size, pause_seconds=args.pause_seconds
        )
    except (
        IllegalOperationError,
        NonRetryablePayloadStorageError,
        PayloadStorageUnavailableError,
    ) as e:
        logger.error(
            "The backfill stopped: %s Running it again continues where it "
            "stopped.",
            e,
        )
        sys.exit(1)
    for table in result.tables:
        logger.info(
            "`%s`: %d rows updated, %d bytes offloaded, %d updates skipped "
            "because the row changed.",
            table.table,
            table.rows_updated,
            table.bytes_offloaded,
            table.rows_skipped,
        )
    if not result.completed:
        logger.error(
            "The backfill did not complete: run it again. `--report` shows "
            "what remains."
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
            "`%s`: %.1f MiB before, %.1f MiB after.",
            table.table,
            table.bytes_before / 2**20,
            table.bytes_after / 2**20,
        )


if __name__ == "__main__":
    main()
