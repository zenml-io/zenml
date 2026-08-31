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
"""Server-lifetime scheduler for execution-history archive maintenance."""

import asyncio
import random
from functools import partial
from threading import Event
from typing import Callable, Optional, Protocol

from zenml.logger import get_logger
from zenml.models import ExecutionArchivePassResult

logger = get_logger(__name__)


class ExecutionArchiveMaintenanceStore(Protocol):
    """Store capability required by the archive scheduler."""

    def run_execution_archive_maintenance(
        self, *, stop_requested: Callable[[], bool]
    ) -> Optional[ExecutionArchivePassResult]:
        """Run one bounded server-side archive maintenance pass.

        Args:
            stop_requested: Cooperative shutdown signal checked between atomic
                archive operations.

        Returns:
            Completed pass result, or `None` if another replica owns it.
        """


class ExecutionArchiveScheduler:
    """Run bounded archive passes without owning archive state."""

    def __init__(
        self, *, store: ExecutionArchiveMaintenanceStore, interval: float
    ) -> None:
        """Initialize the scheduler.

        Args:
            store: Workspace store exposing server-side maintenance.
            interval: Seconds between pass starts.
        """
        self._store = store
        self._interval = interval
        self._shutdown_event = asyncio.Event()
        self._stop_requested = Event()
        self._task: Optional[asyncio.Task[None]] = None

    def start(self) -> None:
        """Start one scheduler task for this server replica."""
        if self._task is not None:
            return
        self._shutdown_event.clear()
        self._stop_requested = Event()
        self._task = asyncio.create_task(self._run())

    async def shutdown(self) -> None:
        """Stop scheduling without waiting for slow storage operations.

        The worker receives a cooperative stop signal and exits after its
        current atomic archive operation. Canceling the asyncio wrapper keeps
        server shutdown independent from object-store latency.
        """
        self._shutdown_event.set()
        self._stop_requested.set()
        task = self._task
        self._task = None
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def _run(self) -> None:
        initial_delay = random.uniform(0, min(self._interval, 60))
        if await self._wait(initial_delay):
            return
        while not self._shutdown_event.is_set():
            try:
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    partial(
                        self._store.run_execution_archive_maintenance,
                        stop_requested=self._stop_requested.is_set,
                    ),
                )
            except Exception:
                logger.exception("Execution archive maintenance pass failed.")
            if await self._wait(self._interval):
                return

    async def _wait(self, delay: float) -> bool:
        try:
            await asyncio.wait_for(self._shutdown_event.wait(), timeout=delay)
        except asyncio.TimeoutError:
            return False
        return True
