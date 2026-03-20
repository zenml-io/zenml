from concurrent.futures import Future

import pytest

from zenml.execution.pipeline.dynamic.invocation_state import InvocationState
from zenml.execution.pipeline.dynamic.outputs import (
    _InlineStepFuture,
    _IsolatedStepFuture,
    MapResultsFuture,
    StepFuture,
)


def test_inline_step_future_running_checks() -> None:
    wrapped: Future[object] = Future()
    inline_future = _InlineStepFuture(invocation_id="inline", wrapped=wrapped)
    assert inline_future.running() is True
    wrapped.set_result(object())
    assert inline_future.running() is False


def test_inline_step_future_waits_for_scheduler_dispatch() -> None:
    state = InvocationState(invocation_id="inline")
    inline_future = _InlineStepFuture(invocation_id="inline", state=state)

    assert inline_future.running() is True

    wrapped: Future[object] = Future()
    state.bind_inline_future(wrapped)

    assert inline_future.running() is True

    wrapped.set_result(object())

    assert inline_future.result() is not None
    assert inline_future.running() is False


def test_isolated_step_future_running_checks_before_dispatch() -> None:
    state = InvocationState(invocation_id="isolated")
    isolated_future = _IsolatedStepFuture(
        pipeline_run_id="00000000-0000-0000-0000-000000000000",
        invocation_id="isolated",
        state=state,
    )

    assert isolated_future.running() is True

    state.mark_success(object())

    assert isolated_future.running() is False


def test_invocation_state_rejects_duplicate_dispatch() -> None:
    state = InvocationState(invocation_id="step")
    state.mark_dispatched()

    with pytest.raises(
        RuntimeError, match="Invalid invocation state transition"
    ):
        state.mark_dispatched()


def test_invocation_state_rejects_second_terminal_transition() -> None:
    state = InvocationState(invocation_id="step")
    state.mark_success(object())

    with pytest.raises(
        RuntimeError, match="Invalid invocation state transition"
    ):
        state.mark_failure(RuntimeError("boom"))


def test_map_results_future_waits_for_expansion() -> None:
    expansion: Future[list[StepFuture]] = Future()
    map_future = MapResultsFuture(wrapped=expansion)

    assert map_future.running() is True

    wrapped: Future[object] = Future()
    child_future = StepFuture(
        wrapped=_InlineStepFuture(invocation_id="child", wrapped=wrapped),
        output_keys=[],
    )
    expansion.set_result([child_future])

    assert len(map_future) == 1
    assert map_future.running() is True

    wrapped.set_result(object())

    assert map_future.running() is False
