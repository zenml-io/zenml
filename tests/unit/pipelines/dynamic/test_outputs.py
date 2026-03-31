from concurrent.futures import Future

from zenml.execution.pipeline.dynamic.outputs import (
    _InlineStepFuture,
)


def test_inline_step_future_running_checks() -> None:
    wrapped: Future[object] = Future()
    inline_future = _InlineStepFuture(wrapped=wrapped, invocation_id="inline")
    assert inline_future.running() is True
    wrapped.set_result(object())
    assert inline_future.running() is False
