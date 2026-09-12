# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Scheduled execution archive sweeps.

The sweep runs on the cron expression in `ZENML_SERVER_ARCHIVE__SCHEDULE`.
Every replica schedules it, and the lease in the server settings row decides
which one actually sweeps; the others find the lease live and do nothing.

Each sweep is bounded by `ZENML_SERVER_ARCHIVE__MAX_RUNS_PER_PASS` and a
time budget, so a backlog is drained over several sweeps rather than in one
long transaction. A sweep that stops on its budget is resumed shortly after
instead of waiting for the next cron occurrence.
"""

import asyncio
import random
from typing import Optional

from zenml.enums import RetentionOutcome
from zenml.exceptions import ExecutionRetentionConflictError
from zenml.logger import get_logger
from zenml.utils.native_schedules import next_occurrence_for_cron
from zenml.utils.time_utils import utc_now

logger = get_logger(__name__)

# Replicas fire on the same cron minute, so a short random offset keeps them
# from all contending for the same lease at once.
MAX_JITTER_SECONDS = 30

# A sweep that stopped on its budget still has work queued behind it.
RESUME_DELAY_SECONDS = 5


class ArchiveScheduler:
    """Runs one bounded archive sweep per cron occurrence."""

    def __init__(self, schedule: str) -> None:
        """Bind the schedule without starting anything.

        Args:
            schedule: Validated cron expression.
        """
        self.schedule = schedule
        self._shutdown_event = asyncio.Event()
        self._task: Optional[asyncio.Task[None]] = None

    def start(self) -> None:
        """Start the scheduling loop on the running event loop."""
        self._shutdown_event.clear()
        self._task = asyncio.create_task(self._run())

    async def shutdown(self) -> None:
        """Stop the scheduling loop, abandoning the lease to expire."""
        self._shutdown_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        """Sweep on every cron occurrence until the server shuts down."""
        delay = self._seconds_until_next_sweep()
        while not self._shutdown_event.is_set():
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(), timeout=delay
                )
                return
            except asyncio.TimeoutError:
                pass
            try:
                outcome = await asyncio.get_event_loop().run_in_executor(
                    None, self._sweep
                )
            except Exception:
                logger.exception("Error during the archive sweep")
                outcome = RetentionOutcome.FAILED
            delay = (
                RESUME_DELAY_SECONDS
                if outcome == RetentionOutcome.PAUSED
                else self._seconds_until_next_sweep()
            )

    def _sweep(self) -> RetentionOutcome:
        """Run one bounded sweep, unless another replica is already sweeping.

        Returns:
            The sweep outcome, or `RUNNING` when another replica holds the
            lease.
        """
        from zenml.zen_server.utils import zen_store

        try:
            return zen_store().run_archive_sweep()
        except ExecutionRetentionConflictError:
            logger.debug("Another replica is running the archive sweep.")
            return RetentionOutcome.RUNNING

    def _seconds_until_next_sweep(self) -> float:
        """Return how long to wait for the next cron occurrence.

        Returns:
            Seconds until the next occurrence, plus a random offset.
        """
        now = utc_now()
        occurrence = next_occurrence_for_cron(self.schedule, base=now)
        jitter = random.uniform(0, MAX_JITTER_SECONDS)
        return max((occurrence - now).total_seconds(), 0.0) + jitter
