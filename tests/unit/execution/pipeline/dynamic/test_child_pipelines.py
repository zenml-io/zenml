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
"""End-to-end tests for child pipelines."""

import datetime
import threading
import time
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

import pytest

from zenml import pipeline, step, wait
from zenml.client import Client
from zenml.enums import (
    ExecutionStatus,
    HookType,
    RunWaitConditionResolution,
)


def _hook_noop() -> None:
    pass


# ---------------------------------------------------------------------------
# Reusable steps
# ---------------------------------------------------------------------------


@step
def step_emit_int(value: int = 1) -> int:
    return value


@step
def step_double(value: int) -> int:
    return value * 2


@step
def step_add(a: int, b: int) -> int:
    return a + b


@step
def step_sleep_then_emit(value: int = 7, seconds: float = 0.5) -> int:
    time.sleep(seconds)
    return value


@step
def step_emit_pair() -> Tuple[int, int]:
    return 3, 4


@step
def step_emit_none() -> None:
    return None


@step
def step_assert_int(value: int, expected: int) -> None:
    assert value == expected, f"Expected {expected}, got {value}"


@step
def step_raise() -> None:
    raise RuntimeError("step_raise: intentional test failure")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_in_thread(
    target: Any,
) -> Tuple[threading.Thread, Dict[str, Any], datetime.datetime]:
    holder: Dict[str, Any] = {}

    def _run() -> None:
        try:
            holder["run"] = target()
        except BaseException as exc:
            holder["exc"] = exc

    started_at = datetime.datetime.utcnow()
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread, holder, started_at


def _latest_run_id(
    pipeline_name: str,
    *,
    after: Optional[datetime.datetime] = None,
    timeout: float = 20.0,
    poll_interval: float = 1.0,
    thread: Optional[threading.Thread] = None,
    holder: Optional[Dict[str, Any]] = None,
) -> UUID:
    deadline = time.time() + timeout
    client = Client()
    while True:
        runs = client.list_pipeline_runs(
            pipeline=pipeline_name,
            sort_by="desc:created",
            size=1,
        )
        if runs.items:
            run = runs.items[0]
            if after is None or run.created >= after:
                return run.id

        if holder and (exc := holder.get("exc")):
            raise RuntimeError(
                f"Pipeline `{pipeline_name}` failed before a run was visible."
            ) from exc

        if thread and not thread.is_alive():
            raise RuntimeError(
                f"Pipeline `{pipeline_name}` finished before a run was visible."
            )

        if time.time() >= deadline:
            break

        time.sleep(min(poll_interval, max(0.0, deadline - time.time())))

    raise TimeoutError(
        f"No run for pipeline `{pipeline_name}` after {timeout}s"
    )


def _resolve_pending_wait(
    pipeline_run_id: UUID,
    *,
    resolution: RunWaitConditionResolution = RunWaitConditionResolution.CONTINUE,
    result: Any = None,
    timeout: float = 10.0,
    thread: Optional[threading.Thread] = None,
    holder: Optional[Dict[str, Any]] = None,
) -> UUID:
    deadline = time.time() + timeout
    client = Client()
    while time.time() < deadline:
        conditions = client.list_run_wait_conditions(
            pipeline_run=pipeline_run_id,
            status="pending",
        )
        if conditions.items:
            condition = conditions.items[0]
            client.resolve_run_wait_condition(
                run_wait_condition_id=condition.id,
                resolution=resolution,
                result=result,
            )
            return condition.id

        if holder and (exc := holder.get("exc")):
            raise RuntimeError(
                f"Pipeline run `{pipeline_run_id}` failed before a pending "
                "wait condition was visible."
            ) from exc

        if thread and not thread.is_alive():
            raise RuntimeError(
                f"Pipeline run `{pipeline_run_id}` finished before a pending "
                "wait condition was visible."
            )

        time.sleep(0.1)
    raise TimeoutError(
        f"No pending wait condition on run {pipeline_run_id} after {timeout}s"
    )


def _wait_for_thread(
    thread: threading.Thread, *, timeout: float = 30.0
) -> None:
    thread.join(timeout=timeout)
    assert not thread.is_alive(), "Pipeline thread did not finish in time"


def _refresh(run_id: UUID) -> Any:
    return Client().get_pipeline_run(run_id, hydrate=True)


# ---------------------------------------------------------------------------
# A. Child pipeline call modes
# ---------------------------------------------------------------------------


@pipeline(dynamic=True, enable_cache=False)
def child_emit_int_pipeline() -> int:
    return step_emit_int(value=11)


@pipeline(dynamic=True, enable_cache=False)
def parent_sync_child_pipeline() -> None:
    out = child_emit_int_pipeline()
    step_assert_int(value=out.load(), expected=11)


def test_sync_child_creates_separate_child_run() -> None:
    run = parent_sync_child_pipeline()
    assert run.status.is_successful
    children = Client().list_pipeline_runs(
        parent_run_id=run.id, sort_by="asc:created"
    )
    assert children.total == 1
    child = children.items[0]
    assert child.status.is_successful
    assert child.parent_run is not None
    assert child.parent_run.id == run.id
    assert child.root_run_id == run.id
    assert child.child_key == "pipeline:child_emit_int_pipeline"


@pipeline(dynamic=True, enable_cache=False)
def parent_submit_child_pipeline() -> None:
    future = child_emit_int_pipeline.submit()
    step_assert_int(value=future.result().load(), expected=11)


def test_submit_child_creates_separate_child_run() -> None:
    run = parent_submit_child_pipeline()
    assert run.status.is_successful
    children = Client().list_pipeline_runs(parent_run_id=run.id)
    assert children.total == 1
    assert children.items[0].status.is_successful


@pipeline(dynamic=True, enable_cache=False)
def parent_inline_child_pipeline() -> None:
    out = child_emit_int_pipeline.embed()
    step_assert_int(value=out.load(), expected=11)


def test_inline_child_does_not_create_child_run() -> None:
    run = parent_inline_child_pipeline()
    assert run.status.is_successful
    # No child run is created — the steps execute in the parent run.
    children = Client().list_pipeline_runs(parent_run_id=run.id)
    assert children.total == 0
    # The inline child's steps appear under the parent run.
    parent = _refresh(run.id)
    step_names = set(parent.steps.keys())
    assert "step_emit_int" in step_names
    assert "step_assert_int" in step_names


# ---------------------------------------------------------------------------
# B. I/O between parent and child
# ---------------------------------------------------------------------------


@pipeline(dynamic=True, enable_cache=False)
def child_double_pipeline(x: int) -> int:
    return step_double(x)


@pipeline(dynamic=True, enable_cache=False)
def parent_step_output_to_child_arg() -> None:
    a = step_emit_int(value=5)
    out = child_double_pipeline(a.load())
    step_assert_int(value=out.load(), expected=10)


def test_step_output_passes_to_child_pipeline_arg() -> None:
    run = parent_step_output_to_child_arg()
    assert run.status.is_successful


@pipeline(dynamic=True, enable_cache=False)
def child_pair_pipeline() -> Tuple[int, int]:
    return step_emit_pair()


@pipeline(dynamic=True, enable_cache=False)
def parent_consumes_tuple_child_output() -> None:
    a, b = child_pair_pipeline()
    step_assert_int(value=step_add(a=a, b=b), expected=7)


def test_child_pipeline_tuple_outputs_consumed_by_parent_step() -> None:
    run = parent_consumes_tuple_child_output()
    assert run.status.is_successful


@pipeline(dynamic=True, enable_cache=False)
def child_void_pipeline() -> None:
    step_emit_none()


@pipeline(dynamic=True, enable_cache=False)
def parent_void_child_pipeline() -> None:
    child_void_pipeline()
    step_emit_int()


def test_child_pipeline_with_no_output_succeeds() -> None:
    run = parent_void_child_pipeline()
    assert run.status.is_successful
    children = Client().list_pipeline_runs(parent_run_id=run.id)
    assert children.total == 1
    assert children.items[0].status.is_successful
    assert children.items[0].outputs == {}


# ---------------------------------------------------------------------------
# C. Failure propagation
# ---------------------------------------------------------------------------


@pipeline(dynamic=True, enable_cache=False)
def child_failing_pipeline() -> None:
    step_raise()


@pipeline(dynamic=True, enable_cache=False)
def parent_sync_failing_child_pipeline() -> None:
    child_failing_pipeline()
    step_emit_int()  # Should not be reached.


def test_sync_child_failure_fails_parent() -> None:
    with pytest.raises(BaseException, match="step_raise"):
        parent_sync_failing_child_pipeline()
    # The latest run for this pipeline is in a failed state.
    run_id = _latest_run_id("parent_sync_failing_child_pipeline")
    parent = _refresh(run_id)
    assert parent.status.is_failed
    children = Client().list_pipeline_runs(parent_run_id=parent.id)
    assert children.total == 1
    assert children.items[0].status.is_failed


@pipeline(dynamic=True, enable_cache=False)
def parent_submit_failing_child_pipeline() -> None:
    future = child_failing_pipeline.submit()
    future.wait()


def test_submit_child_failure_fails_parent() -> None:
    with pytest.raises(BaseException, match="step_raise"):
        parent_submit_failing_child_pipeline()
    run_id = _latest_run_id("parent_submit_failing_child_pipeline")
    assert _refresh(run_id).status.is_failed


@pipeline(dynamic=True, enable_cache=False)
def parent_inline_failing_child_pipeline() -> None:
    child_failing_pipeline.embed()


def test_inline_child_failure_aborts_parent_run() -> None:
    with pytest.raises(BaseException, match="step_raise"):
        parent_inline_failing_child_pipeline()
    run_id = _latest_run_id("parent_inline_failing_child_pipeline")
    parent = _refresh(run_id)
    assert parent.status.is_failed
    # Inline mode must not produce a separate child run.
    assert Client().list_pipeline_runs(parent_run_id=parent.id).total == 0


# ---------------------------------------------------------------------------
# D. Nesting (siblings + depth)
# ---------------------------------------------------------------------------


@pipeline(dynamic=True, enable_cache=False)
def child_emit_constant_pipeline(value: int) -> int:
    return step_emit_int(value=value)


@pipeline(dynamic=True, enable_cache=False)
def parent_multiple_concurrent_children() -> None:
    futures = [child_emit_constant_pipeline.submit(value=v) for v in (1, 2, 3)]
    total = step_add(
        a=futures[0].result().load(), b=futures[1].result().load()
    )
    step_assert_int(
        value=step_add(a=total, b=futures[2].result().load()),
        expected=6,
    )


def test_multiple_concurrent_child_pipelines() -> None:
    run = parent_multiple_concurrent_children()
    assert run.status.is_successful
    children = Client().list_pipeline_runs(
        parent_run_id=run.id, sort_by="asc:created"
    )
    assert children.total == 3
    assert all(child.status.is_successful for child in children.items)
    # `child_key` includes the suffix on duplicate base names.
    keys = {child.child_key for child in children.items}
    assert keys == {
        "pipeline:child_emit_constant_pipeline",
        "pipeline:child_emit_constant_pipeline_2",
        "pipeline:child_emit_constant_pipeline_3",
    }


@pipeline(dynamic=True, enable_cache=False)
def grandchild_pipeline() -> int:
    return step_emit_int(value=42)


@pipeline(dynamic=True, enable_cache=False)
def child_with_grandchild_pipeline() -> int:
    return grandchild_pipeline()


@pipeline(dynamic=True, enable_cache=False)
def parent_three_level_pipeline() -> None:
    out = child_with_grandchild_pipeline()
    step_assert_int(value=out.load(), expected=42)


def test_three_level_nesting_root_run_id_propagates() -> None:
    parent_run = parent_three_level_pipeline()
    assert parent_run.status.is_successful

    children = Client().list_pipeline_runs(parent_run_id=parent_run.id)
    assert children.total == 1
    child_run = children.items[0]
    assert child_run.status.is_successful
    assert child_run.parent_run is not None
    assert child_run.parent_run.id == parent_run.id
    assert child_run.root_run_id == parent_run.id

    grandchildren = Client().list_pipeline_runs(parent_run_id=child_run.id)
    assert grandchildren.total == 1
    grandchild_run = grandchildren.items[0]
    assert grandchild_run.status.is_successful
    # Grandchild's parent is the child, but its root is the top-level parent.
    assert grandchild_run.parent_run is not None
    assert grandchild_run.parent_run.id == child_run.id
    assert grandchild_run.root_run_id == parent_run.id


# ---------------------------------------------------------------------------
# E. Wait conditions (no children)
# ---------------------------------------------------------------------------


@pipeline(dynamic=True, enable_cache=False)
def waiting_pipeline_returns_value() -> int:
    answer: int = wait(schema=int, timeout=20, poll_interval=1)
    return step_double(answer)


def test_wait_continue_returns_typed_value() -> None:
    thread, holder, started_at = _run_in_thread(waiting_pipeline_returns_value)
    run_id = _latest_run_id(
        "waiting_pipeline_returns_value",
        after=started_at,
        thread=thread,
        holder=holder,
    )
    _resolve_pending_wait(run_id, result=21, thread=thread, holder=holder)
    _wait_for_thread(thread)
    assert "exc" not in holder, holder.get("exc")
    run = holder["run"]
    assert run.status.is_successful
    # Pipeline returns the doubled answer.
    refreshed = _refresh(run.id)
    assert len(refreshed.outputs) == 1
    only_output = next(iter(refreshed.outputs.values()))
    assert only_output.load() == 42


@pipeline(dynamic=True, enable_cache=False)
def waiting_pipeline_no_schema() -> None:
    wait(timeout=20, poll_interval=1)
    step_emit_int()


def test_wait_continue_without_schema_proceeds() -> None:
    thread, holder, started_at = _run_in_thread(waiting_pipeline_no_schema)
    run_id = _latest_run_id(
        "waiting_pipeline_no_schema",
        after=started_at,
        thread=thread,
        holder=holder,
    )
    _resolve_pending_wait(run_id, thread=thread, holder=holder)
    _wait_for_thread(thread)
    assert "exc" not in holder, holder.get("exc")
    assert holder["run"].status.is_successful


@pipeline(dynamic=True, enable_cache=False)
def waiting_pipeline_to_be_aborted() -> None:
    wait(timeout=20, poll_interval=1)
    step_emit_int()  # Must not run.


def test_wait_abort_aborts_run() -> None:
    thread, holder, started_at = _run_in_thread(waiting_pipeline_to_be_aborted)
    run_id = _latest_run_id(
        "waiting_pipeline_to_be_aborted",
        after=started_at,
        thread=thread,
        holder=holder,
    )
    _resolve_pending_wait(
        run_id,
        resolution=RunWaitConditionResolution.ABORT,
        thread=thread,
        holder=holder,
    )
    _wait_for_thread(thread)
    # The run must not be successful — the server publishes the run as
    # stopped/failed when the wait condition aborts.
    final = _refresh(run_id)
    assert not final.status.is_successful
    # The follow-up step must not have started.
    assert "step_emit_int" not in final.steps


@pipeline(
    dynamic=True,
    enable_cache=False,
    on_end=_hook_noop,
    on_success=_hook_noop,
    on_failure=_hook_noop,
)
def waiting_pipeline_aborted_with_hooks() -> None:
    wait(timeout=20, poll_interval=1)
    step_emit_int()  # Must not run.


def test_wait_abort_fires_run_end_hook_only() -> None:
    thread, holder, started_at = _run_in_thread(
        waiting_pipeline_aborted_with_hooks
    )
    run_id = _latest_run_id(
        "waiting_pipeline_aborted_with_hooks", after=started_at
    )
    _resolve_pending_wait(run_id, resolution=RunWaitConditionResolution.ABORT)
    _wait_for_thread(thread)

    invocations = Client().list_hook_invocations(
        pipeline_run_id=run_id, size=100
    )
    types = {i.hook_type for i in invocations.items}
    # The run reaches a terminal state on abort, so the end hook fires, but
    # neither the success nor the failure hook does.
    assert HookType.RUN_END in types
    assert HookType.RUN_SUCCESS not in types
    assert HookType.RUN_FAILURE not in types


@pipeline(dynamic=True, enable_cache=False)
def waiting_pipeline_short_timeout() -> None:
    wait(timeout=2, poll_interval=1)
    step_emit_int()


def test_wait_timeout_pauses_run_when_no_other_work() -> None:
    run = waiting_pipeline_short_timeout()
    assert run is not None
    final = _refresh(run.id)
    assert final.status == ExecutionStatus.PAUSED
    # The follow-up step must not have started.
    assert "step_emit_int" not in final.steps


# ---------------------------------------------------------------------------
# F. Wait + child interactions
# ---------------------------------------------------------------------------


@pipeline(dynamic=True, enable_cache=False)
def child_slow_doubles_pipeline(x: int) -> int:
    return step_double(step_sleep_then_emit(value=x, seconds=0.5))


@pipeline(dynamic=True, enable_cache=False)
def parent_waits_with_concurrent_child_running() -> None:
    future = child_slow_doubles_pipeline.submit(x=5)
    answer: int = wait(schema=int, timeout=20, poll_interval=1)
    step_assert_int(value=future.result().load(), expected=10)
    step_assert_int(value=answer, expected=99)


def test_parent_waits_while_child_runs_then_wait_resolves() -> None:
    thread, holder, started_at = _run_in_thread(
        parent_waits_with_concurrent_child_running
    )
    parent_run_id = _latest_run_id(
        "parent_waits_with_concurrent_child_running",
        after=started_at,
        thread=thread,
        holder=holder,
    )
    _resolve_pending_wait(
        parent_run_id,
        result=99,
        timeout=15,
        thread=thread,
        holder=holder,
    )
    _wait_for_thread(thread)
    assert "exc" not in holder, holder.get("exc")
    assert holder["run"].status.is_successful
    # Verify the child finished too.
    children = Client().list_pipeline_runs(parent_run_id=parent_run_id)
    assert children.total == 1
    assert children.items[0].status.is_successful


@pipeline(dynamic=True, enable_cache=False)
def child_pipeline_that_waits() -> int:
    answer: int = wait(schema=int, timeout=20, poll_interval=1)
    return step_double(answer)


@pipeline(dynamic=True, enable_cache=False)
def parent_runs_concurrent_child_that_waits() -> None:
    future = child_pipeline_that_waits.submit()
    step_emit_int()  # Parent does its own work alongside.
    step_assert_int(value=future.result().load(), expected=84)


def test_child_waits_while_parent_does_other_work_then_child_wait_resolves() -> (
    None
):
    thread, holder, started_at = _run_in_thread(
        parent_runs_concurrent_child_that_waits
    )
    parent_run_id = _latest_run_id(
        "parent_runs_concurrent_child_that_waits",
        after=started_at,
        thread=thread,
        holder=holder,
    )

    # Wait for the child run to register.
    deadline = time.time() + 15
    child_run_id: Optional[UUID] = None
    while time.time() < deadline:
        children = Client().list_pipeline_runs(parent_run_id=parent_run_id)
        if children.total >= 1:
            child_run_id = children.items[0].id
            break
        time.sleep(0.1)
    assert child_run_id is not None, "Child run never appeared"

    _resolve_pending_wait(
        child_run_id,
        result=42,
        timeout=15,
        thread=thread,
        holder=holder,
    )
    _wait_for_thread(thread)
    assert "exc" not in holder, holder.get("exc")
    parent = holder["run"]
    assert parent.status.is_successful
    children = Client().list_pipeline_runs(parent_run_id=parent.id)
    assert children.items[0].status.is_successful


@pipeline(dynamic=True, enable_cache=False)
def parent_waits_then_child_inline_wait() -> int:
    a: int = wait(schema=int, timeout=20, poll_interval=1, name="first")
    b: int = wait(schema=int, timeout=20, poll_interval=1, name="second")
    return step_add(a=a, b=b)


def test_parent_run_resolves_two_sequential_waits() -> None:
    thread, holder, started_at = _run_in_thread(
        parent_waits_then_child_inline_wait
    )
    run_id = _latest_run_id(
        "parent_waits_then_child_inline_wait",
        after=started_at,
        thread=thread,
        holder=holder,
    )
    _resolve_pending_wait(run_id, result=10, thread=thread, holder=holder)
    _resolve_pending_wait(run_id, result=20, thread=thread, holder=holder)
    _wait_for_thread(thread)
    assert "exc" not in holder, holder.get("exc")
    refreshed = _refresh(holder["run"].id)
    assert refreshed.status.is_successful
    only_output = next(iter(refreshed.outputs.values()))
    assert only_output.load() == 30


# ---------------------------------------------------------------------------
# G. Failure interactions between parent waits and child runs
# ---------------------------------------------------------------------------


@pipeline(dynamic=True, enable_cache=False)
def child_failing_for_parent_wait_test() -> None:
    step_raise()


@pipeline(dynamic=True, enable_cache=False)
def parent_waits_with_concurrent_failing_child() -> None:
    child_failing_for_parent_wait_test.submit()
    # The child fails almost immediately. The parent's wait keeps polling
    # until its own deadline expires, then raises `RunPaused`. The child's
    # exception is recorded on the runner (`_on_failure_detected`), so the
    # subsequent `_settle_concurrent_work` re-raises it and the run is
    # published as FAILED rather than PAUSED.
    wait(schema=int, timeout=3, poll_interval=1)


def test_parent_wait_run_fails_when_concurrent_child_fails() -> None:
    with pytest.raises(BaseException, match="step_raise"):
        parent_waits_with_concurrent_failing_child()
    run_id = _latest_run_id("parent_waits_with_concurrent_failing_child")
    parent = _refresh(run_id)
    assert parent.status.is_failed
    children = Client().list_pipeline_runs(parent_run_id=parent.id)
    assert children.total == 1
    assert children.items[0].status.is_failed


@pipeline(dynamic=True, enable_cache=False)
def child_waits_long_for_parent_fail_test() -> int:
    return wait(schema=int, timeout=3, poll_interval=1)


@pipeline(dynamic=True, enable_cache=False)
def parent_fails_during_concurrent_child_wait() -> None:
    child_waits_long_for_parent_fail_test.submit()
    # Give the child runner a moment to enter `wait()` before we fail.
    step_sleep_then_emit(seconds=0.5)
    step_raise()


def test_child_wait_settles_when_parent_fails() -> None:
    with pytest.raises(BaseException, match="step_raise"):
        parent_fails_during_concurrent_child_wait()
    run_id = _latest_run_id("parent_fails_during_concurrent_child_wait")
    parent = _refresh(run_id)
    assert parent.status.is_failed
    children = Client().list_pipeline_runs(parent_run_id=parent.id)
    assert children.total == 1
    child = children.items[0]
    # The child must be in a terminal/non-running state — either paused
    # (its own wait timed out) or failed.
    assert child.status == ExecutionStatus.PAUSED or child.status.is_failed, (
        f"unexpected child status: {child.status}"
    )


# ---------------------------------------------------------------------------
# H. Parent pauses when a child it depends on times out on its own wait
# ---------------------------------------------------------------------------


@pipeline(dynamic=True, enable_cache=False)
def child_waits_short_for_pause_test() -> int:
    return wait(schema=int, timeout=2, poll_interval=1)


@pipeline(dynamic=True, enable_cache=False)
def parent_awaits_paused_child_via_future_wait() -> None:
    future = child_waits_short_for_pause_test.submit()
    future.wait()


def test_parent_pauses_when_future_wait_observes_paused_child() -> None:
    parent_awaits_paused_child_via_future_wait()
    run_id = _latest_run_id("parent_awaits_paused_child_via_future_wait")
    parent = _refresh(run_id)
    assert parent.status == ExecutionStatus.PAUSED
    children = Client().list_pipeline_runs(parent_run_id=parent.id)
    assert children.total == 1
    assert children.items[0].status == ExecutionStatus.PAUSED


@pipeline(dynamic=True, enable_cache=False)
def parent_sync_step_after_paused_child() -> None:
    future = child_waits_short_for_pause_test.submit()
    # Sync step call. `compile_dynamic_step_invocation` blocks on each
    # `after`-future before launching the step, so the paused child's
    # `RunPaused` propagates here and pauses the parent.
    step_emit_int(value=99, after=future)


def test_parent_pauses_when_sync_step_depends_on_paused_child() -> None:
    parent_sync_step_after_paused_child()
    run_id = _latest_run_id("parent_sync_step_after_paused_child")
    parent = _refresh(run_id)
    assert parent.status == ExecutionStatus.PAUSED
    # The downstream step must not have executed.
    assert "step_emit_int" not in parent.steps
    children = Client().list_pipeline_runs(parent_run_id=parent.id)
    assert children.total == 1
    assert children.items[0].status == ExecutionStatus.PAUSED


@pipeline(dynamic=True, enable_cache=False)
def parent_async_step_after_paused_child() -> None:
    future = child_waits_short_for_pause_test.submit()
    # Concurrent step submission. The body returns immediately; the
    # cascade through the dependency graph plus the child's
    # `_mark_paused` walking up the parent chain is what pauses the
    # parent run here.
    step_emit_int.submit(value=99, after=future)


def test_parent_pauses_when_async_step_depends_on_paused_child() -> None:
    parent_async_step_after_paused_child()
    run_id = _latest_run_id("parent_async_step_after_paused_child")
    parent = _refresh(run_id)
    assert parent.status == ExecutionStatus.PAUSED
    # The downstream step must not have executed.
    assert "step_emit_int" not in parent.steps
    children = Client().list_pipeline_runs(parent_run_id=parent.id)
    assert children.total == 1
    assert children.items[0].status == ExecutionStatus.PAUSED


@pipeline(dynamic=True, enable_cache=False)
def parent_sync_calls_waiting_child_and_exits() -> None:
    child_waits_short_for_pause_test()


def test_sync_child_wait_timeout_pauses_both_parent_and_child() -> None:
    parent_sync_calls_waiting_child_and_exits()
    run_id = _latest_run_id("parent_sync_calls_waiting_child_and_exits")
    parent = _refresh(run_id)
    assert parent.status == ExecutionStatus.PAUSED
    children = Client().list_pipeline_runs(parent_run_id=parent.id)
    assert children.total == 1
    assert children.items[0].status == ExecutionStatus.PAUSED


@pipeline(dynamic=True, enable_cache=False)
def parent_submits_waiting_child_and_exits() -> None:
    child_waits_short_for_pause_test.submit()


def test_submit_child_wait_timeout_pauses_both_parent_and_child() -> None:
    parent_submits_waiting_child_and_exits()
    run_id = _latest_run_id("parent_submits_waiting_child_and_exits")
    parent = _refresh(run_id)
    assert parent.status == ExecutionStatus.PAUSED
    children = Client().list_pipeline_runs(parent_run_id=parent.id)
    assert children.total == 1
    assert children.items[0].status == ExecutionStatus.PAUSED
