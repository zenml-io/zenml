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
"""Tests for the CONTINUE_ON_FAILURE execution mode of dynamic pipelines."""

from typing import List

import pytest

from zenml import pipeline, step
from zenml.client import Client
from zenml.enums import ExecutionMode, ExecutionStatus
from zenml.exceptions import StepExecutionException
from zenml.execution.pipeline.dynamic.future_registry import StartupCancelled

_executed: List[str] = []


@step
def failing_step() -> int:
    raise RuntimeError("boom")


@step
def record_step(name: str) -> str:
    _executed.append(name)
    return name


@step
def consume_int(value: int) -> int:
    return value


@step
def make_list() -> List[int]:
    return [1, 2, 3]


@step
def fail_on_two(value: int) -> int:
    if value == 2:
        raise RuntimeError("boom")
    _executed.append(f"ok-{value}")
    return value


@pipeline(
    dynamic=True,
    enable_cache=False,
    execution_mode=ExecutionMode.CONTINUE_ON_FAILURE,
)
def unawaited_failure_pipeline() -> None:
    failing_step.submit()
    record_step.submit(name="independent")


def test_unawaited_async_failure_does_not_fail_run() -> None:
    _executed.clear()
    run = unawaited_failure_pipeline()
    assert "independent" in _executed

    run = Client().get_pipeline_run(run.id)
    assert run.status == ExecutionStatus.COMPLETED
    step_statuses = {name: step.status for name, step in run.steps.items()}
    assert step_statuses["failing_step"] == ExecutionStatus.FAILED


@pipeline(
    dynamic=True,
    enable_cache=False,
    execution_mode=ExecutionMode.CONTINUE_ON_FAILURE,
)
def awaited_failure_pipeline() -> None:
    future = failing_step.submit()
    future.result()


def test_awaited_async_failure_still_raises() -> None:
    with pytest.raises(RuntimeError):
        awaited_failure_pipeline()


@pipeline(
    dynamic=True,
    enable_cache=False,
    execution_mode=ExecutionMode.CONTINUE_ON_FAILURE,
)
def sync_failure_pipeline() -> None:
    failing_step()


def test_sync_failure_still_fails_run() -> None:
    with pytest.raises(RuntimeError):
        sync_failure_pipeline()


@pipeline(
    dynamic=True,
    enable_cache=False,
    execution_mode=ExecutionMode.CONTINUE_ON_FAILURE,
)
def cancelled_downstream_pipeline() -> None:
    future = failing_step.submit()
    consume_int.submit(future)
    record_step.submit(name="independent")


def test_downstream_of_failed_async_step_is_cancelled() -> None:
    _executed.clear()
    cancelled_downstream_pipeline()
    assert "independent" in _executed


@pipeline(
    dynamic=True,
    enable_cache=False,
    execution_mode=ExecutionMode.CONTINUE_ON_FAILURE,
)
def awaited_downstream_pipeline() -> None:
    future = failing_step.submit()
    downstream = consume_int.submit(future)
    downstream.result()


def test_awaiting_cancelled_downstream_raises() -> None:
    with pytest.raises(StartupCancelled) as exc_info:
        awaited_downstream_pipeline()

    cause = exc_info.value.__cause__
    assert isinstance(cause, StepExecutionException)
    assert isinstance(cause.__cause__, RuntimeError)


@pipeline(
    dynamic=True,
    enable_cache=False,
    execution_mode=ExecutionMode.CONTINUE_ON_FAILURE,
)
def partial_map_pipeline() -> None:
    values = make_list()
    fail_on_two.map(value=values)


def test_map_partial_failure_does_not_fail_run() -> None:
    _executed.clear()
    partial_map_pipeline()
    assert "ok-1" in _executed
    assert "ok-3" in _executed


@pipeline(
    dynamic=True,
    enable_cache=False,
    execution_mode=ExecutionMode.STOP_ON_FAILURE,
)
def stop_on_failure_unawaited_pipeline() -> None:
    failing_step.submit()


def test_stop_on_failure_unawaited_failure_still_fails_run() -> None:
    with pytest.raises(Exception):
        stop_on_failure_unawaited_pipeline()
