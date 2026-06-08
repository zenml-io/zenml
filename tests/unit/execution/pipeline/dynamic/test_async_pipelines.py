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
"""End-to-end tests for async dynamic pipelines."""

import asyncio
import threading

import pytest

from zenml import pipeline, step

# ---------------------------------------------------------------------------
# Shared state across step bodies running in-process on the local orchestrator.
# Any asyncio primitive stored here is loop-bound, so it must be created lazily
# inside a step body and the dict reset at the start of each run.
# ---------------------------------------------------------------------------

_shared: dict = {}


@step
async def barrier_worker(name: str) -> str:
    _shared["entered"] = _shared.get("entered", 0) + 1
    _shared["max"] = max(_shared.get("max", 0), _shared["entered"])
    barrier = _shared.setdefault("barrier", asyncio.Event())
    if _shared["entered"] >= 2:
        barrier.set()
    # If the two bodies were on different loops, this Event would never be set
    # by the other body and this would time out.
    await asyncio.wait_for(barrier.wait(), timeout=10.0)
    _shared["entered"] -= 1
    return name


@pipeline(dynamic=True, enable_cache=False)
async def async_gather_pipeline() -> None:
    _shared.clear()
    results = await asyncio.gather(barrier_worker("a"), barrier_worker("b"))
    names = sorted(r.load() for r in results)
    assert names == ["a", "b"], names
    assert _shared["max"] == 2, _shared


def test_async_gather_overlaps_on_shared_loop() -> None:
    run = async_gather_pipeline()
    assert run.status.is_successful


@step
async def async_plus_one(x: int) -> int:
    await asyncio.sleep(0.01)
    return x + 1


@step
def sync_times_ten(x: int) -> int:
    return x * 10


@pipeline(dynamic=True, enable_cache=False)
async def async_mixed_pipeline() -> None:
    a = await async_plus_one(10)
    # A sync step cannot be called directly in an async pipeline, it has to be
    # submitted to run on a worker thread.
    b = await sync_times_ten.submit(5)
    assert a.load() == 11, a.load()
    assert b.load() == 50, b.load()


def test_async_dynamic_mixed_steps() -> None:
    run = async_mixed_pipeline()
    assert run.status.is_successful


@pipeline(dynamic=True, enable_cache=False)
async def async_pipeline_calls_sync_step_directly() -> None:
    await sync_times_ten(5)


def test_sync_step_direct_call_rejected_in_async_pipeline() -> None:
    with pytest.raises(RuntimeError, match="submit"):
        async_pipeline_calls_sync_step_directly()


@pipeline(dynamic=True, enable_cache=False)
def sync_mixed_pipeline() -> None:
    a = async_plus_one(10)
    b = sync_times_ten(5)
    assert a.load() == 11, a.load()
    assert b.load() == 50, b.load()


def test_sync_dynamic_mixed_steps() -> None:
    run = sync_mixed_pipeline()
    assert run.status.is_successful


@step
async def async_reads_context() -> str:
    from zenml import get_step_context

    await asyncio.sleep(0.01)
    return get_step_context().step_run.name


@pipeline(dynamic=True, enable_cache=False)
async def async_context_pipeline() -> None:
    out = await async_reads_context()
    assert out.load() == "async_reads_context", out.load()


def test_async_body_has_step_context() -> None:
    run = async_context_pipeline()
    assert run.status.is_successful


# ---------------------------------------------------------------------------
# `submit()` on async steps runs them concurrently in both sync and async
# dynamic pipelines. In an async pipeline the resulting future must be awaited.
# A blocking `.result()` / `.wait()` on the shared loop is rejected because it
# would deadlock the loop.
# ---------------------------------------------------------------------------

_submit_state: dict = {}


@step
async def submit_concurrent_worker(name: str) -> str:
    barrier: threading.Barrier = _submit_state["barrier"]
    await asyncio.sleep(0.01)
    # Each submitted async step runs on its own loop on its own worker thread.
    # The barrier releases only once both workers arrive, proving concurrency.
    barrier.wait(timeout=10.0)
    return name


@pipeline(dynamic=True, enable_cache=False)
def sync_pipeline_submits_async() -> None:
    _submit_state["barrier"] = threading.Barrier(2)
    future_a = submit_concurrent_worker.submit("a", id="worker_a")
    future_b = submit_concurrent_worker.submit("b", id="worker_b")
    results = sorted([future_a.result().load(), future_b.result().load()])
    assert results == ["a", "b"], results


def test_submit_async_steps_run_concurrently_in_sync_pipeline() -> None:
    run = sync_pipeline_submits_async()
    assert run.status.is_successful


@pipeline(dynamic=True, enable_cache=False)
async def async_pipeline_submits_and_awaits() -> None:
    future = async_plus_one.submit(10)
    out = await future
    assert out.load() == 11, out.load()


def test_submit_async_step_in_async_pipeline_is_awaitable() -> None:
    run = async_pipeline_submits_and_awaits()
    assert run.status.is_successful


@step
async def async_double(x: int) -> int:
    await asyncio.sleep(0.01)
    return x * 2


@pipeline(dynamic=True, enable_cache=False)
async def async_pipeline_wires_submit_future() -> None:
    future = async_plus_one.submit(10)
    out = await async_double(future)
    assert out.load() == 22, out.load()


def test_submit_future_wires_into_bare_call() -> None:
    run = async_pipeline_wires_submit_future()
    assert run.status.is_successful


@pipeline(dynamic=True, enable_cache=False)
async def async_pipeline_blocking_result() -> None:
    future = async_plus_one.submit(10)
    future.result()


def test_blocking_result_rejected_in_async_pipeline() -> None:
    with pytest.raises(RuntimeError, match="async pipeline"):
        async_pipeline_blocking_result()


# ---------------------------------------------------------------------------
# A bare step call in an async pipeline returns a coroutine. The step is only
# dispatched once it is awaited, not at call time.
# ---------------------------------------------------------------------------

_lazy_state: dict = {}


@step
async def records_execution() -> int:
    _lazy_state["ran"] = True
    return 1


@pipeline(dynamic=True, enable_cache=False)
async def async_pipeline_lazy_call() -> None:
    _lazy_state.clear()
    coro = records_execution()
    # Yield to the loop. An eagerly dispatched step would run here.
    await asyncio.sleep(0.05)
    assert _lazy_state.get("ran") is None, "step ran before being awaited"
    out = await coro
    assert _lazy_state.get("ran") is True
    assert out.load() == 1, out.load()


def test_bare_call_is_lazy() -> None:
    run = async_pipeline_lazy_call()
    assert run.status.is_successful


# ---------------------------------------------------------------------------
# Invocation IDs are allocated at call time, so they follow call order even
# when the steps are awaited in a different order.
# ---------------------------------------------------------------------------

_id_order: dict = {}


@step
async def async_records_id(x: int) -> int:
    from zenml import get_step_context

    _id_order[x] = get_step_context().step_run.name
    await asyncio.sleep(0.01)
    return x


@pipeline(dynamic=True, enable_cache=False)
async def async_pipeline_id_order() -> None:
    _id_order.clear()
    first = async_records_id(1)
    second = async_records_id(2)
    # Await in reverse order. The first call still owns the unsuffixed ID.
    await second
    await first


def test_invocation_ids_follow_call_order() -> None:
    run = async_pipeline_id_order()
    assert run.status.is_successful
    assert _id_order[1] == "async_records_id", _id_order
    assert _id_order[2] == "async_records_id_2", _id_order
