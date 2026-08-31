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
"""Lifecycle tests for the execution archive scheduler."""

import asyncio
import time
from threading import Event
from typing import Callable, Optional

import pytest

from zenml.models import ExecutionArchivePassResult
from zenml.zen_server.execution_archive_scheduler import (
    ExecutionArchiveScheduler,
)


class _BlockingMaintenanceStore:
    """Maintenance store that stops only after observing its callback."""

    def __init__(self) -> None:
        self.started = Event()
        self.stopped = Event()

    def run_execution_archive_maintenance(
        self, *, stop_requested: Callable[[], bool]
    ) -> Optional[ExecutionArchivePassResult]:
        """Block long enough to prove shutdown does not await this call."""
        self.started.set()
        deadline = time.monotonic() + 5
        while not stop_requested() and time.monotonic() < deadline:
            time.sleep(0.001)
        self.stopped.set()
        return None


def test_shutdown_is_prompt_and_signals_the_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shutdown cancels its wrapper and cooperatively stops maintenance."""
    monkeypatch.setattr(
        "zenml.zen_server.execution_archive_scheduler.random.uniform",
        lambda *_: 0,
    )

    async def exercise() -> None:
        store = _BlockingMaintenanceStore()
        scheduler = ExecutionArchiveScheduler(store=store, interval=3600)
        scheduler.start()
        assert await asyncio.to_thread(store.started.wait, 1)

        await asyncio.wait_for(scheduler.shutdown(), timeout=1)

        assert await asyncio.to_thread(store.stopped.wait, 1)

    asyncio.run(exercise())
