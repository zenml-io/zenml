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
server container or pod, or in a job built like one. For example:

    python -m zenml.zen_server.payload_backfill --report
    python -m zenml.zen_server.payload_backfill
"""

import argparse
import os
import sys

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
    args = parser.parse_args()

    store_config = GlobalConfiguration().store_configuration
    if store_config.type != StoreType.SQL:
        logger.error("The payload backfill requires a SQL store.")
        sys.exit(1)
    # Migrating is the job of the database migration, not of a backfill that
    # may run next to servers of the previous release.
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

    if args.report:
        for report in store.get_payload_backfill_report():
            logger.info(
                "`%s`: %d rows to update, inline payload bytes: %s",
                report.table,
                report.pending_rows,
                report.inline_bytes,
            )
        return

    try:
        results = store.backfill_payloads(
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
    for result in results:
        logger.info(
            "`%s`: %d rows updated, %d bytes offloaded, %d rows changed or "
            "deleted while being updated.",
            result.table,
            result.rows_updated,
            result.bytes_offloaded,
            result.rows_skipped,
        )
    if any(result.failed_rows for result in results):
        sys.exit(1)
    logger.info(
        "The backfill finished. Rows that changed while being updated are "
        "left for another run: `--report` shows what remains."
    )


if __name__ == "__main__":
    main()
