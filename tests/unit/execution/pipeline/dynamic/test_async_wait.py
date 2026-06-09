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
"""End-to-end tests for `zenml.wait()` in async dynamic pipelines."""

import asyncio
import os
import sys
import time

import pytest
from tests.unit.execution.pipeline.dynamic.test_child_pipelines import (
    _latest_run_id,
    _refresh,
    _resolve_pending_wait,
    _run_in_thread,
    _wait_for_thread,
)

from zenml import pipeline, step, wait
from zenml.client import Client
from zenml.enums import ExecutionStatus
from zenml.execution.pipeline.dynamic.interactive_input_utils import (
    read_stdin_line_with_timeout,
)
from zenml.execution.pipeline.dynamic.runner import _WaitInterrupt

# Shared flag set by a step body that runs on the pipeline loop while a wait is
# pending. Reset at the start of each run that uses it.
_drain_state: dict = {}


@step
async def async_wait_double(value: int) -> int:
    await asyncio.sleep(0.01)
    return value * 2


@step
async def async_wait_marker(value: int = 1) -> int:
    await asyncio.sleep(0.05)
    _drain_state["done"] = True
    return value


# ---------------------------------------------------------------------------
# Awaiting `zenml.wait(...)` resolves to the typed value.
# ---------------------------------------------------------------------------


@pipeline(dynamic=True, enable_cache=False)
async def async_waiting_returns_value() -> int:
    answer: int = await wait(schema=int, timeout=20, poll_interval=1)
    return await async_wait_double(answer)


def test_async_wait_continue_returns_typed_value() -> None:
    thread, holder, started_at = _run_in_thread(async_waiting_returns_value)
    run_id = _latest_run_id("async_waiting_returns_value", after=started_at)
    _resolve_pending_wait(run_id, result=21)
    _wait_for_thread(thread)
    assert "exc" not in holder, holder.get("exc")
    run = holder["run"]
    assert run.status.is_successful
    refreshed = _refresh(run.id)
    assert len(refreshed.outputs) == 1
    only_output = next(iter(refreshed.outputs.values()))
    assert only_output.load() == 42


# ---------------------------------------------------------------------------
# The await frees the loop, so work scheduled on it keeps draining while the
# wait is pending. A blocking wait on the loop would freeze this.
# ---------------------------------------------------------------------------


@pipeline(dynamic=True, enable_cache=False)
async def async_wait_with_concurrent_loop_task() -> None:
    _drain_state.clear()
    # The bare step call runs on the pipeline loop once scheduled as a task.
    task = asyncio.create_task(async_wait_marker())
    answer: int = await wait(schema=int, timeout=30, poll_interval=1)
    assert answer == 5, answer
    out = await task
    assert out.load() == 1, out.load()


def test_async_wait_does_not_freeze_loop() -> None:
    thread, holder, started_at = _run_in_thread(
        async_wait_with_concurrent_loop_task
    )
    run_id = _latest_run_id(
        "async_wait_with_concurrent_loop_task", after=started_at
    )
    # The task scheduled on the loop must complete while the wait is pending.
    # If the wait froze the loop, the task could not run.
    deadline = time.time() + 15.0
    while time.time() < deadline and not _drain_state.get("done"):
        time.sleep(0.05)
    assert _drain_state.get("done") is True, (
        "concurrent loop task did not run while the wait was pending"
    )
    pending = Client().list_run_wait_conditions(
        pipeline_run=run_id, status="pending"
    )
    assert pending.items, "wait resolved before the concurrent task finished"
    _resolve_pending_wait(run_id, result=5)
    _wait_for_thread(thread)
    assert "exc" not in holder, holder.get("exc")
    assert holder["run"].status.is_successful


# ---------------------------------------------------------------------------
# Only one wait can be active per run. Gathering two waits rejects the second.
# ---------------------------------------------------------------------------


@pipeline(dynamic=True, enable_cache=False)
async def async_double_wait() -> None:
    await asyncio.gather(
        wait(schema=int, timeout=20, poll_interval=1),
        wait(schema=int, timeout=20, poll_interval=1),
    )


@pytest.mark.filterwarnings(
    "ignore:coroutine.*was never awaited:RuntimeWarning"
)
def test_async_second_concurrent_wait_rejected() -> None:
    # The second `wait(...)` raises synchronously while `gather`'s arguments
    # are evaluated, so the first wait's coroutine is never awaited.
    with pytest.raises(RuntimeError, match="Only one"):
        async_double_wait()


# ---------------------------------------------------------------------------
# `zenml.wait(...)` is rejected from inside a step and from a worker thread.
# ---------------------------------------------------------------------------


@step
async def async_step_calls_wait() -> None:
    await wait(schema=int, timeout=20, poll_interval=1)


@pipeline(dynamic=True, enable_cache=False)
async def async_pipeline_wait_in_step() -> None:
    await async_step_calls_wait()


def test_async_wait_inside_step_rejected() -> None:
    with pytest.raises(RuntimeError, match="cannot be called inside a step"):
        async_pipeline_wait_in_step()


@pipeline(dynamic=True, enable_cache=False)
async def async_pipeline_wait_from_worker_thread() -> None:
    # `asyncio.to_thread` copies the run context to a worker thread, so the
    # context guard passes and the pipeline-thread guard fires.
    await asyncio.to_thread(wait, schema=int, timeout=20, poll_interval=1)


def test_async_wait_from_worker_thread_rejected() -> None:
    with pytest.raises(RuntimeError, match="pipeline thread"):
        async_pipeline_wait_from_worker_thread()


# ---------------------------------------------------------------------------
# A wait that never resolves pauses the run after in-flight work drains.
# ---------------------------------------------------------------------------


@pipeline(dynamic=True, enable_cache=False)
async def async_waiting_short_timeout() -> None:
    await wait(timeout=2, poll_interval=1)
    await async_wait_double(1)  # Must not run.


def test_async_wait_timeout_pauses_run() -> None:
    run = async_waiting_short_timeout()
    assert run is not None
    final = _refresh(run.id)
    assert final.status == ExecutionStatus.PAUSED
    assert "async_wait_double" not in final.steps


# ---------------------------------------------------------------------------
# Ctrl+C on an async pipeline reaches the loop thread as a cancellation. The
# wait poll runs on a worker thread, so the cancellation is forwarded to it via
# `_WaitInterrupt` to abort the wait the same way a sync Ctrl+C does. These
# cover the forwarding primitives; the end-to-end signal path is verified
# manually since unit tests cannot deliver SIGINT deterministically.
# ---------------------------------------------------------------------------


def test_wait_interrupt_blocks_then_wakes() -> None:
    interrupt = _WaitInterrupt()
    try:
        assert interrupt.wait(timeout=0.01) is False
        interrupt.trigger()
        assert interrupt.wait(timeout=1.0) is True
    finally:
        interrupt.close()


def test_read_stdin_aborts_on_interrupt_fd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdin_read_fd, stdin_write_fd = os.pipe()
    interrupt = _WaitInterrupt()
    try:
        interrupt.trigger()
        with os.fdopen(stdin_read_fd) as fake_stdin:
            monkeypatch.setattr(sys, "stdin", fake_stdin)
            with pytest.raises(KeyboardInterrupt):
                read_stdin_line_with_timeout(
                    timeout=1.0, interrupt_fd=interrupt.fd
                )
    finally:
        os.close(stdin_write_fd)
        interrupt.close()
