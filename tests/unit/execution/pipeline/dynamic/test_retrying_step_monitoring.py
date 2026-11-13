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
"""Tests for monitoring an isolated step run in `RETRYING` status."""

import threading
from concurrent.futures import Future
from types import SimpleNamespace
from typing import Any, List, Tuple
from uuid import uuid4

import pytest

from zenml.config.retry_config import StepRetryConfig
from zenml.enums import ExecutionStatus
from zenml.execution.pipeline.dynamic import runner as runner_module
from zenml.execution.pipeline.dynamic.future_registry import FutureRegistry
from zenml.execution.pipeline.dynamic.outputs import (
    StepFuture,
    _IsolatedStepFuture,
)
from zenml.execution.pipeline.dynamic.runner import DynamicPipelineRunner


def _retrying_step_run(version: int, max_retries: int) -> Any:
    return SimpleNamespace(
        id=uuid4(),
        name="retrying_step",
        status=ExecutionStatus.RETRYING,
        version=version,
        duration=None,
        exception_info=None,
        spec=None,
        config=SimpleNamespace(
            retry=StepRetryConfig(max_retries=max_retries),
            step_operator=None,
            command=None,
        ),
    )


def _run_one_monitoring_pass(
    monkeypatch: pytest.MonkeyPatch,
    step_run: Any,
    failure_detected: bool,
) -> Tuple[StepFuture, List[str]]:
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.utils.get_latest_step_run",
        lambda *_args, **_kwargs: step_run,
    )
    monkeypatch.setattr(
        runner_module,
        "Client",
        lambda: SimpleNamespace(get_run_step=lambda _: step_run),
    )

    launched: Future[Any] = Future()
    launched.set_result(step_run)
    registry = FutureRegistry()
    future = StepFuture(invocation_id="retrying_step", output_keys=[])
    registry.register_step_future(invocation_id="retrying_step", future=future)
    registry.bind_step_execution_future(
        invocation_id="retrying_step",
        future=_IsolatedStepFuture(
            wrapped=launched,
            pipeline_run_id=uuid4(),
            invocation_id="retrying_step",
        ),
    )

    calls: List[str] = []
    runner = object.__new__(DynamicPipelineRunner)
    runner._run = SimpleNamespace(id=uuid4())
    runner._steps_to_monitor = {"retrying_step": step_run}
    runner._shutdown_requested = False
    runner._failure_detected = failure_detected
    runner._lifecycle_lock = threading.RLock()
    runner._future_registry = registry
    runner._get_isolated_step_infra_status = lambda _: ExecutionStatus.FAILED
    runner._cleanup_isolated_step = lambda _: None
    runner._fail_concurrent_node = lambda **_: calls.append("failed")
    runner._queue_concurrent_isolated_step = lambda **_: calls.append(
        "relaunched"
    )

    def _stop_after_one_pass(timeout: float) -> None:
        runner._shutdown_requested = True

    runner._monitoring_event = SimpleNamespace(
        wait=_stop_after_one_pass, clear=lambda: None
    )
    runner._monitoring_loop()
    return future, calls


@pytest.mark.parametrize(
    "version,max_retries,failure_detected",
    [
        # Retries left, but another failure was already recorded.
        (2, 2, True),
        # No retries left by the runner's count.
        (3, 2, False),
    ],
)
def test_retrying_step_that_is_not_relaunched_fails(
    monkeypatch: pytest.MonkeyPatch,
    version: int,
    max_retries: int,
    failure_detected: bool,
) -> None:
    """A `RETRYING` step that won't be relaunched resolves as failed."""
    step_run = _retrying_step_run(version=version, max_retries=max_retries)

    future, calls = _run_one_monitoring_pass(
        monkeypatch, step_run, failure_detected=failure_detected
    )

    assert calls == ["failed"]
    assert not future.running()
    with pytest.raises(RuntimeError, match="retrying_step"):
        future.result()
