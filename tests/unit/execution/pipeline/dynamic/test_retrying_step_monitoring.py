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
"""Tests for monitoring isolated steps that the server marks as `RETRYING`."""

import threading
from concurrent.futures import Future
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
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
from zenml.models import ExceptionInfo
from zenml.utils import exception_utils

INVOCATION_ID = "flaky_step"
ATTEMPT_END_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _MonitoringHarness:
    """Runs one monitoring pass over a single `RETRYING` step run."""

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        version: int = 1,
        max_retries: int = 2,
        failure_detected: bool = False,
        exception_info: Optional[ExceptionInfo] = None,
    ) -> None:
        self.step_run: Any = SimpleNamespace(
            id=uuid4(),
            name=INVOCATION_ID,
            status=ExecutionStatus.RETRYING,
            version=version,
            duration=None,
            end_time=ATTEMPT_END_TIME,
            exception_info=exception_info,
            spec=None,
            config=SimpleNamespace(
                retry=StepRetryConfig(max_retries=max_retries)
            ),
        )
        self.published: List[Dict[str, Any]] = []
        self.relaunched: List[Any] = []
        self.failed_nodes: List[BaseException] = []

        monkeypatch.setenv("ZENML_DYNAMIC_PIPELINE_MONITORING_DELAY", "0")
        monkeypatch.setattr(
            runner_module,
            "Client",
            lambda: SimpleNamespace(get_run_step=lambda _: self.step_run),
        )
        monkeypatch.setattr(
            runner_module,
            "publish_step_run_status_update",
            self._publish_status,
        )
        monkeypatch.setattr(
            "zenml.execution.pipeline.dynamic.utils.get_latest_step_run",
            lambda *_args, **_kwargs: self.step_run,
        )
        monkeypatch.setattr(
            "zenml.config.step_configurations.Step",
            lambda **kwargs: SimpleNamespace(**kwargs),
        )

        launch: Future[Any] = Future()
        launch.set_result(self.step_run)
        self.future = StepFuture(invocation_id=INVOCATION_ID, output_keys=[])
        registry = FutureRegistry()
        registry.register_step_future(
            invocation_id=INVOCATION_ID, future=self.future
        )
        registry.bind_step_execution_future(
            invocation_id=INVOCATION_ID,
            future=_IsolatedStepFuture(
                wrapped=launch,
                pipeline_run_id=uuid4(),
                invocation_id=INVOCATION_ID,
            ),
        )

        runner = object.__new__(DynamicPipelineRunner)
        runner._steps_to_monitor = {INVOCATION_ID: self.step_run}
        runner._shutdown_requested = False
        runner._failure_detected = failure_detected
        runner._lifecycle_lock = threading.RLock()
        runner._future_registry = registry
        runner._get_isolated_step_infra_status = lambda _: (
            ExecutionStatus.FAILED
        )
        runner._cleanup_isolated_step = lambda _: None
        runner._fail_concurrent_node = lambda invocation_id, exception: (
            self.failed_nodes.append(exception)
        )
        runner._queue_concurrent_isolated_step = self._relaunch
        # The loop waits on this event between passes, so requesting shutdown
        # here makes `_monitoring_loop()` return after a single pass.
        runner._monitoring_event = SimpleNamespace(
            wait=lambda timeout: setattr(runner, "_shutdown_requested", True),
            clear=lambda: None,
        )
        self.runner = runner

    def _publish_status(self, **kwargs: Any) -> Any:
        self.published.append(kwargs)
        self.step_run.status = kwargs["status"]
        if kwargs["exception_info"]:
            self.step_run.exception_info = kwargs["exception_info"]
        return self.step_run

    def _relaunch(self, step: Any) -> _IsolatedStepFuture:
        self.relaunched.append(step)
        return _IsolatedStepFuture(
            pipeline_run_id=uuid4(), invocation_id=INVOCATION_ID
        )


def test_step_is_relaunched_when_retries_are_left(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A `RETRYING` step with retries left is relaunched, not stopped."""
    harness = _MonitoringHarness(monkeypatch)

    harness.runner._monitoring_loop()

    assert len(harness.relaunched) == 1
    assert harness.published == []
    assert harness.failed_nodes == []


def test_step_is_stopped_when_run_already_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The failed attempt's exception is kept, not replaced by the reason."""
    original = exception_utils.collect_exception_information(
        ValueError("boom")
    )
    harness = _MonitoringHarness(
        monkeypatch, failure_detected=True, exception_info=original
    )

    harness.runner._monitoring_loop()

    assert harness.relaunched == []
    assert harness.published == [
        {
            "step_run_id": harness.step_run.id,
            "status": ExecutionStatus.STOPPED,
            "end_time": ATTEMPT_END_TIME,
            "exception_info": None,
        }
    ]
    (failure,) = harness.failed_nodes
    assert isinstance(failure.__cause__, ValueError)
    assert str(failure.__cause__) == "boom"
    with pytest.raises(ValueError, match="boom"):
        harness.future.result()


def test_step_is_stopped_with_reason_when_no_retries_are_left(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without an exception from the attempt, the reason becomes the error."""
    harness = _MonitoringHarness(monkeypatch, version=3)

    harness.runner._monitoring_loop()

    assert harness.relaunched == []
    (published,) = harness.published
    assert published["status"] == ExecutionStatus.STOPPED
    message = (
        f"Step `{INVOCATION_ID}` failed and was not retried because it has "
        "no retries left."
    )
    assert published["exception_info"].message == message
    (failure,) = harness.failed_nodes
    assert str(failure.__cause__) == message
    with pytest.raises(RuntimeError, match="no retries left"):
        harness.future.result()
