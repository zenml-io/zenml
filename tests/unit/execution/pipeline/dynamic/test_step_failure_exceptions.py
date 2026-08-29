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
"""Tests for the exception raised when a dynamic step fails."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from zenml import pipeline, step
from zenml.enums import ExecutionStatus
from zenml.exceptions import StepExecutionException
from zenml.execution.pipeline.dynamic.future_registry import FutureRegistry
from zenml.execution.pipeline.dynamic.outputs import (
    StepFuture,
    _IsolatedStepFuture,
)
from zenml.execution.pipeline.dynamic.runner import (
    DynamicPipelineRunner,
    RunPaused,
)


@step
def failing_step() -> int:
    raise RuntimeError("boom")


@step
def consume_int(value: int) -> int:
    return value


@pipeline(dynamic=True, enable_cache=False)
def sync_failure_pipeline() -> None:
    failing_step()


def test_sync_failure_raises_original_exception() -> None:
    with pytest.raises(RuntimeError):
        sync_failure_pipeline()


@pipeline(dynamic=True, enable_cache=False)
def explicit_wait_pipeline() -> None:
    future = failing_step.submit()
    future.wait()


@pipeline(dynamic=True, enable_cache=False)
def explicit_result_pipeline() -> None:
    future = failing_step.submit()
    future.result()


def test_explicit_wait_raises_original_exception() -> None:
    with pytest.raises(RuntimeError):
        explicit_wait_pipeline()


def test_explicit_result_raises_original_exception() -> None:
    with pytest.raises(RuntimeError):
        explicit_result_pipeline()


@pipeline(dynamic=True, enable_cache=False)
def implicit_sync_input_pipeline() -> None:
    future = failing_step.submit()
    consume_int(future)


def test_implicit_sync_input_raises_step_execution_exception() -> None:
    with pytest.raises(StepExecutionException) as exc_info:
        implicit_sync_input_pipeline()
    assert isinstance(exc_info.value.original_exception, RuntimeError)
    assert exc_info.value.__cause__ is exc_info.value.original_exception


@pipeline(dynamic=True, enable_cache=False)
def implicit_async_input_pipeline() -> None:
    future = failing_step.submit()
    consume_int.submit(future)


def test_implicit_async_input_raises_step_execution_exception() -> None:
    with pytest.raises(StepExecutionException):
        implicit_async_input_pipeline()


@step
def noop_step() -> None:
    return None


@pipeline(dynamic=True, enable_cache=False)
def unawaited_pipeline() -> None:
    failing_step.submit()


def test_unawaited_failure_raises_step_execution_exception() -> None:
    with pytest.raises(StepExecutionException):
        unawaited_pipeline()


def _settling_runner(
    registry: FutureRegistry, *, continue_on_failure: bool = False
) -> DynamicPipelineRunner:
    """Build a runner with only the state that settlement reads."""
    runner = object.__new__(DynamicPipelineRunner)
    runner._exception = None
    runner._continue_on_failure = continue_on_failure
    runner._future_registry = registry
    return runner


def _unawaited_failed_isolated_step(
    monkeypatch: pytest.MonkeyPatch,
) -> FutureRegistry:
    """Register an isolated step that failed before the monitor noticed."""
    failed_step_run = SimpleNamespace(
        status=ExecutionStatus.FAILED,
        exception_info=None,
    )
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.utils.get_latest_step_run",
        lambda *_args, **_kwargs: failed_step_run,
    )

    registry = FutureRegistry()
    registry.register_step_future(
        invocation_id="failing_step",
        future=StepFuture(
            invocation_id="failing_step",
            output_keys=[],
            execution_future=_IsolatedStepFuture(
                pipeline_run_id=uuid4(),
                invocation_id="failing_step",
            ),
        ),
    )
    return registry


def test_unawaited_isolated_failure_raises_during_settlement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An isolated failure is raised even before the monitor processes it."""
    runner = _settling_runner(_unawaited_failed_isolated_step(monkeypatch))

    with pytest.raises(RuntimeError, match="failing_step"):
        runner._settle_concurrent_work()


def test_unawaited_isolated_failure_settles_when_continuing_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CONTINUE_ON_FAILURE lets the run settle past an unawaited failure."""
    runner = _settling_runner(
        _unawaited_failed_isolated_step(monkeypatch),
        continue_on_failure=True,
    )

    runner._settle_concurrent_work()


def test_paused_node_settles_without_failing() -> None:
    """A node that inherited a pause is not a failure at settlement."""
    registry = FutureRegistry()
    registry.register_step_future(
        invocation_id="paused_step",
        future=StepFuture(invocation_id="paused_step", output_keys=[]),
    )
    registry.set_startup_exception(
        invocation_id="paused_step", exception=RunPaused()
    )

    _settling_runner(registry)._settle_concurrent_work()


@pipeline(dynamic=True, enable_cache=False)
def after_sync_pipeline() -> None:
    future = failing_step.submit()
    noop_step(after=future)


def test_after_sync_raises_step_execution_exception() -> None:
    with pytest.raises(StepExecutionException):
        after_sync_pipeline()


@pipeline(dynamic=True, enable_cache=False)
def after_async_pipeline() -> None:
    future = failing_step.submit()
    noop_step.submit(after=future)


def test_after_async_raises_step_execution_exception() -> None:
    with pytest.raises(StepExecutionException):
        after_async_pipeline()
