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
"""Resource pool reconciler."""

import random
import threading
from typing import TYPE_CHECKING, Optional

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlmodel import create_engine

from zenml.constants import RESOURCE_POOL_RECONCILIATION_ADVISORY_LOCK_NAME
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.zen_stores.sql_zen_store import SqlZenStore

logger = get_logger(__name__)

FOLLOWER_RETRY_JITTER_FACTOR = 0.2


class ResourcePoolReconciler:
    """Resource pool reconciler."""

    def __init__(self, store: "SqlZenStore") -> None:
        """Initialize the reconciler.

        Args:
            store: SQL store instance used to execute reconciliation passes.
        """
        self._store = store
        self._thread: Optional[threading.Thread] = None
        self._stop_event: Optional[threading.Event] = None
        self._lock_connection: Optional[Connection] = None

        url, connect_args, engine_args = store.config.get_sqlalchemy_config()
        engine_args["pool_size"] = 1
        self._engine = create_engine(
            url=url, connect_args=connect_args, **engine_args
        )

    def start(
        self, interval_seconds: float, max_allocations_per_pool: int
    ) -> None:
        """Start the reconciliation background thread.

        Args:
            interval_seconds: Sleep interval between reconciliation passes.
            max_allocations_per_pool: Maximum allocations to perform per pool
                in each pass.
        """
        if self._thread and self._thread.is_alive():
            return

        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self.run_loop,
            kwargs={
                "stop_event": self._stop_event,
                "interval_seconds": interval_seconds,
                "max_allocations_per_pool": max_allocations_per_pool,
            },
            daemon=True,
            name="resource-pool-reconciliation",
        )
        self._thread.start()
        logger.info(
            "Started resource pool reconciliation loop "
            "(interval_seconds=%s, max_allocations_per_pool=%s).",
            interval_seconds,
            max_allocations_per_pool,
        )

    def stop(self, timeout_seconds: float = 5.0) -> None:
        """Stop the reconciliation background thread.

        Args:
            timeout_seconds: Maximum duration to wait for the thread to stop
                after signaling shutdown.
        """
        if self._stop_event is None or self._thread is None:
            return

        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=timeout_seconds)
            if self._thread.is_alive():
                logger.warning(
                    "Timed out while stopping resource pool reconciliation loop."
                )
                return

        logger.info("Stopped resource pool reconciliation loop.")
        self._thread = None
        self._stop_event = None

    def _try_acquire_lock(self) -> bool:
        """Try to acquire reconciliation leadership lock.

        Returns:
            True if the lock was acquired, False otherwise.
        """
        if self._engine.dialect.name not in {"mysql", "mariadb"}:
            # We're connected to a SQLite DB, we just always run the
            # reconciliation loop.
            return True

        if self._lock_connection is not None:
            try:
                self._lock_connection.execute(text("SELECT 1"))
                return True
            except Exception:
                self._release_lock()

        connection = self._engine.connect()
        try:
            acquired = connection.execute(
                text("SELECT GET_LOCK(:name, 0)"),
                {"name": RESOURCE_POOL_RECONCILIATION_ADVISORY_LOCK_NAME},
            ).scalar_one_or_none()
            if acquired == 1:
                self._lock_connection = connection
                logger.info(
                    "Acquired resource pool reconciliation advisory lock."
                )
                return True
        except Exception:
            logger.exception(
                "Failed to acquire resource pool reconciliation advisory lock."
            )
            connection.close()
            return False

        connection.close()
        return False

    def _release_lock(self) -> None:
        """Release reconciliation leadership lock if currently held."""
        if self._lock_connection is None:
            return

        try:
            self._lock_connection.execute(
                text("SELECT RELEASE_LOCK(:name)"),
                {"name": RESOURCE_POOL_RECONCILIATION_ADVISORY_LOCK_NAME},
            )
            logger.info("Released resource pool reconciliation advisory lock.")
        except Exception:
            logger.exception(
                "Failed to release resource pool reconciliation advisory lock."
            )
        finally:
            self._lock_connection.close()
            self._lock_connection = None

    def run_loop(
        self,
        stop_event: threading.Event,
        interval_seconds: float = 30.0,
        max_allocations_per_pool: int = 100,
    ) -> None:
        """Run reconciliation until stop is requested.

        Args:
            stop_event: Event that signals loop shutdown.
            interval_seconds: Sleep interval between reconciliation passes.
            max_allocations_per_pool: Maximum allocations to perform per pool
                in each pass.

        Raises:
            ValueError: If `interval_seconds` is not greater than 0.
        """
        if interval_seconds <= 0:
            raise ValueError("`interval_seconds` must be greater than 0.")
        try:
            while True:
                if stop_event.is_set():
                    return

                if not self._try_acquire_lock():
                    retry_seconds = interval_seconds + random.uniform(
                        0,
                        interval_seconds * FOLLOWER_RETRY_JITTER_FACTOR,
                    )
                    logger.debug(
                        "Reconciler running in follower mode. "
                        "Retrying leadership acquisition in %.2fs.",
                        retry_seconds,
                    )
                    if stop_event.wait(retry_seconds):
                        return
                    continue

                try:
                    self._store.reconcile_resource_pools(
                        max_allocations_per_pool=max_allocations_per_pool
                    )
                except Exception:
                    logger.exception(
                        "Resource pool reconciliation pass failed."
                    )

                if stop_event.wait(interval_seconds):
                    return
        finally:
            self._release_lock()
