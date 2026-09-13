# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Tests for the execution archive scheduler."""

import asyncio
from collections.abc import Coroutine
from threading import Event as ThreadEvent
from typing import Any
from unittest.mock import MagicMock

import pytest

from zenml.enums import RetentionOutcome
from zenml.exceptions import ExecutionRetentionConflictError
from zenml.zen_server import archive_scheduler
from zenml.zen_server import utils as server_utils
from zenml.zen_server.archive_scheduler import ArchiveScheduler

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    """Run scheduler tests on asyncio."""
    return "asyncio"


@pytest.mark.parametrize(
    ("outcome", "expected_second_delay", "expected_schedule_calls"),
    [
        (RetentionOutcome.PAUSED, archive_scheduler.RESUME_DELAY_SECONDS, 1),
        (RetentionOutcome.SUCCEEDED, 120.0, 2),
    ],
)
async def test_scheduler_selects_next_delay_from_sweep_outcome(
    monkeypatch: pytest.MonkeyPatch,
    outcome: RetentionOutcome,
    expected_second_delay: float,
    expected_schedule_calls: int,
) -> None:
    """Paused sweeps resume soon while completed sweeps use the cron."""
    scheduler = ArchiveScheduler("* * * * *")
    schedule_delay = MagicMock(side_effect=[60.0, 120.0])
    sweep = MagicMock(return_value=outcome)
    wait_timeouts: list[float] = []
    second_wait_reached = asyncio.Event()

    async def wait_without_sleeping(
        waiter: Coroutine[Any, Any, bool], timeout: float
    ) -> None:
        waiter.close()
        wait_timeouts.append(timeout)
        if len(wait_timeouts) == 1:
            raise asyncio.TimeoutError

        scheduler._shutdown_event.set()
        second_wait_reached.set()

    monkeypatch.setattr(scheduler, "_seconds_until_next_sweep", schedule_delay)
    monkeypatch.setattr(scheduler, "_sweep", sweep)
    monkeypatch.setattr(
        archive_scheduler.asyncio, "wait_for", wait_without_sleeping
    )

    scheduler.start()
    await second_wait_reached.wait()
    await scheduler.shutdown()

    assert wait_timeouts == [60.0, expected_second_delay]
    assert schedule_delay.call_count == expected_schedule_calls
    sweep.assert_called_once_with()


def test_scheduler_treats_a_sweep_conflict_as_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A live lease held by another replica is a normal running outcome."""
    store = MagicMock()
    store.run_archive_sweep.side_effect = ExecutionRetentionConflictError(
        "Archive sweep lease is already held."
    )
    monkeypatch.setattr(server_utils, "zen_store", lambda: store)

    scheduler = ArchiveScheduler("* * * * *")
    outcome = scheduler._sweep()

    assert outcome == RetentionOutcome.RUNNING
    store.run_archive_sweep.assert_called_once()
    assert (
        store.run_archive_sweep.call_args.kwargs["cancel_event"]
        is scheduler._cancel_event
    )


async def test_shutdown_wakes_pending_scheduler_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shutdown wakes an idle scheduler without cancelling its task."""
    scheduler = ArchiveScheduler("* * * * *")
    monkeypatch.setattr(scheduler, "_seconds_until_next_sweep", lambda: 60.0)

    scheduler.start()
    task = scheduler._task
    assert task is not None
    await asyncio.sleep(0)

    await scheduler.shutdown()

    assert task.done() and not task.cancelled()
    assert scheduler._task is None
    assert scheduler._shutdown_event.is_set()
    assert scheduler._cancel_event.is_set()


async def test_shutdown_waits_for_active_sweep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Application cleanup cannot overtake an active retention worker."""
    scheduler = ArchiveScheduler("* * * * *")
    store = MagicMock()
    entered = ThreadEvent()
    release = ThreadEvent()

    def blocked_sweep(*, cancel_event: ThreadEvent) -> RetentionOutcome:
        entered.set()
        assert release.wait(5)
        assert cancel_event.is_set()
        return RetentionOutcome.PAUSED

    store.run_archive_sweep.side_effect = blocked_sweep
    monkeypatch.setattr(server_utils, "zen_store", lambda: store)
    monkeypatch.setattr(scheduler, "_seconds_until_next_sweep", lambda: 0.0)
    scheduler.start()
    assert await asyncio.to_thread(entered.wait, 3)

    shutdown = asyncio.create_task(scheduler.shutdown())
    await asyncio.sleep(0)
    assert not shutdown.done()
    release.set()
    await shutdown

    assert scheduler._task is None
