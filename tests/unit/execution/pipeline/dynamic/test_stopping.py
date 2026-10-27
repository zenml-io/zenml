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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Regressions for stopping dynamic pipelines with outstanding attempts."""

import threading
from concurrent.futures import Future
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from zenml.enums import ExecutionMode, ExecutionStatus, PipelineRunStopMode
from zenml.execution.pipeline.dynamic.future_registry import (
    FutureRegistry,
    StartupCancelled,
)
from zenml.execution.pipeline.dynamic.invocation_dependency_graph import (
    InvocationDependencyGraph,
    NodeState,
)
from zenml.execution.pipeline.dynamic.outputs import (
    StepFuture,
    _InlineStepFuture,
    _IsolatedStepFuture,
)
from zenml.execution.pipeline.dynamic.runner import DynamicPipelineRunner


@pytest.fixture
def runner() -> DynamicPipelineRunner:
    """Create a runner without loading a stack or contacting a workspace.

    Returns:
        A runner with isolated state and mocked infrastructure.
    """
    value = object.__new__(DynamicPipelineRunner)
    value._run = SimpleNamespace(
        id=uuid4(), status=ExecutionStatus.RUNNING, stop_mode=None
    )
    value._pipeline = SimpleNamespace(name="parent")
    value._orchestrator = MagicMock()
    value._step_operator = None
    value._stop_mode = None
    value._failure_detected = False
    value._shutdown_requested = False
    value._fail_fast = False
    value._continue_on_failure = True
    value._exception = None
    value._lifecycle_lock = threading.RLock()
    value._startup_event = threading.Event()
    value._monitoring_event = threading.Event()
    value._steps_to_monitor = {}
    value._child_runners = {}
    value._dependency_graph = InvocationDependencyGraph()
    value._future_registry = FutureRegistry()
    return value


def make_step(status: ExecutionStatus) -> SimpleNamespace:
    """Create the observed state of one isolated attempt.

    Args:
        status: The attempt's reported status.

    Returns:
        The attempt state consumed by the monitoring loop.
    """
    return SimpleNamespace(
        id=uuid4(),
        name="step",
        status=status,
        duration=None,
        exception_info=None,
        config=SimpleNamespace(step_operator=None, outputs={}),
    )


def prepare_monitor_iteration(
    runner: DynamicPipelineRunner,
    step: SimpleNamespace,
    infra_status: ExecutionStatus,
    monkeypatch: pytest.MonkeyPatch,
) -> MagicMock:
    """Configure external reads for one real monitoring iteration.

    Args:
        runner: The runner under test.
        step: The attempt to monitor.
        infra_status: The status reported by the infrastructure.
        monkeypatch: Fixture for replacing external dependencies.

    Returns:
        The mocked workspace client.
    """
    client = MagicMock()
    client.zen_store.get_run.return_value = runner._run
    client.get_run_step.return_value = step
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.Client", lambda: client
    )
    monkeypatch.setattr(
        runner, "_get_isolated_step_infra_status", lambda _: infra_status
    )
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.handle_float_env_var",
        lambda *args, **kwargs: 0.0,
    )
    runner._monitoring_event = MagicMock()
    runner._monitoring_event.wait.side_effect = lambda **kwargs: setattr(
        runner, "_shutdown_requested", True
    )
    runner._steps_to_monitor[step.name] = step
    return client


@pytest.mark.parametrize("execution_mode", list(ExecutionMode))
def test_explicit_stop_escalates_after_failure(
    runner: DynamicPipelineRunner, execution_mode: ExecutionMode
) -> None:
    """Graceful stop drains, while immediate stop ignores the failure policy.

    Args:
        runner: The runner under test.
        execution_mode: The failure policy to exercise.
    """
    runner._fail_fast = execution_mode == ExecutionMode.FAIL_FAST
    runner._continue_on_failure = (
        execution_mode == ExecutionMode.CONTINUE_ON_FAILURE
    )
    original_error = RuntimeError("original failure")
    runner._failure_detected = True
    runner._exception = original_error
    step = make_step(ExecutionStatus.RUNNING)
    runner._steps_to_monitor[step.name] = step
    child = MagicMock(spec=DynamicPipelineRunner)
    runner._child_runners["child"] = child

    runner.request_stop(PipelineRunStopMode.GRACEFUL)
    runner._orchestrator.stop_isolated_step.assert_not_called()
    child.request_stop.assert_called_with(PipelineRunStopMode.GRACEFUL)

    runner.request_stop(PipelineRunStopMode.IMMEDIATE)
    runner.request_stop(PipelineRunStopMode.GRACEFUL)
    assert runner._stop_mode == PipelineRunStopMode.IMMEDIATE
    assert runner._exception is original_error
    runner._orchestrator.stop_isolated_step.assert_called_with(step)
    child.request_stop.assert_called_with(PipelineRunStopMode.IMMEDIATE)


@pytest.mark.parametrize(
    ("mode", "legacy"),
    [
        (PipelineRunStopMode.GRACEFUL, False),
        (PipelineRunStopMode.IMMEDIATE, False),
        (PipelineRunStopMode.IMMEDIATE, True),
    ],
)
def test_stop_is_observed_while_infrastructure_remains_active(
    runner: DynamicPipelineRunner,
    monkeypatch: pytest.MonkeyPatch,
    mode: PipelineRunStopMode,
    legacy: bool,
) -> None:
    """Running infrastructure must not skip checking the run's stop request.

    Args:
        runner: The runner under test.
        monkeypatch: Fixture for replacing external dependencies.
        mode: Whether the running attempt should drain or stop immediately.
        legacy: Whether to use the status-only stop representation.
    """
    step = make_step(ExecutionStatus.RUNNING)
    if legacy:
        runner._run.status = ExecutionStatus.STOPPING
    else:
        runner._run.stop_mode = mode
    client = prepare_monitor_iteration(
        runner, step, ExecutionStatus.RUNNING, monkeypatch
    )

    runner._monitoring_loop()

    assert runner._stop_mode == mode
    if mode == PipelineRunStopMode.IMMEDIATE:
        runner._orchestrator.stop_isolated_step.assert_called_once_with(step)
    else:
        runner._orchestrator.stop_isolated_step.assert_not_called()
    client.zen_store.get_run.assert_called_once_with(runner._run.id)
    assert runner._steps_to_monitor == {step.name: step}


def test_graceful_stop_preserves_active_future_and_prevents_new_startup(
    runner: DynamicPipelineRunner,
) -> None:
    """Stopping settles pending work without completing an active attempt.

    Args:
        runner: The runner under test.
    """
    execution = Future()
    active = StepFuture(
        invocation_id="active",
        output_keys=[],
        execution_future=_InlineStepFuture(execution, "active"),
    )
    runner._register_concurrent_step_invocation(
        active, initial_state=NodeState.RUNNING
    )
    pending = StepFuture(invocation_id="pending", output_keys=[])
    runner._register_concurrent_step_invocation(pending, after=active)

    runner.request_stop(PipelineRunStopMode.GRACEFUL)

    assert active.running()
    assert not pending.running()
    with pytest.raises(StartupCancelled):
        pending.wait()
    with pytest.raises(StartupCancelled):
        runner._run_sync_step(MagicMock())
    runner._orchestrator.stop_isolated_step.assert_not_called()
    execution.set_result(make_step(ExecutionStatus.COMPLETED))
    runner._future_registry.await_all_no_raise()


def test_immediate_stop_catches_a_late_submission(
    runner: DynamicPipelineRunner,
) -> None:
    """A submission finishing after the stop request is still cancelled.

    Args:
        runner: The runner under test.
    """
    runner.request_stop(PipelineRunStopMode.IMMEDIATE)
    step = make_step(ExecutionStatus.PROVISIONING)

    runner._register_isolated_step_for_monitoring(step.name, step)

    runner._orchestrator.stop_isolated_step.assert_called_once_with(step)


@pytest.mark.parametrize(
    ("explicit_stop", "infra_status", "stop_fails_once"),
    [
        (False, ExecutionStatus.FAILED, False),
        (True, ExecutionStatus.FAILED, False),
        (True, ExecutionStatus.RUNNING, False),
        (True, ExecutionStatus.RUNNING, True),
    ],
)
def test_suppressed_retry_settles_the_existing_future(
    runner: DynamicPipelineRunner,
    monkeypatch: pytest.MonkeyPatch,
    explicit_stop: bool,
    infra_status: ExecutionStatus,
    stop_fails_once: bool,
) -> None:
    """A suppressed retry must not leave the original future waiting forever.

    Args:
        runner: The runner under test.
        monkeypatch: Fixture for replacing external dependencies.
        explicit_stop: Whether cancellation follows a stop request or failure.
        infra_status: The status reported by the backend Job.
        stop_fails_once: Whether the first backend stop fails transiently.
    """
    step = make_step(ExecutionStatus.RETRYING)
    future = StepFuture(
        invocation_id=step.name,
        output_keys=[],
        execution_future=_IsolatedStepFuture(runner._run.id, step.name),
    )
    runner._register_concurrent_step_invocation(
        future, initial_state=NodeState.RUNNING
    )
    if explicit_stop:
        runner._run.stop_mode = PipelineRunStopMode.GRACEFUL
    else:
        runner._failure_detected = True
        runner._exception = RuntimeError("another step failed")
    prepare_monitor_iteration(runner, step, infra_status, monkeypatch)
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.get_remaining_retries",
        lambda **kwargs: 2,
    )
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.utils.get_latest_step_run",
        lambda *args, **kwargs: step,
    )

    def publish_stopped(step_run_id: object) -> SimpleNamespace:
        """Apply the terminal update to the mocked attempt.

        Args:
            step_run_id: The attempt receiving the update.

        Returns:
            The stopped attempt.
        """
        assert step_run_id == step.id
        step.status = ExecutionStatus.STOPPED
        return step

    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.publish_stopped_step_run",
        publish_stopped,
    )
    retry = MagicMock()
    monkeypatch.setattr(runner, "_queue_concurrent_isolated_step", retry)

    if stop_fails_once:
        runner._orchestrator.stop_isolated_step.side_effect = RuntimeError(
            "Backend unavailable"
        )
        runner._monitoring_loop()
        assert step.status == ExecutionStatus.RETRYING
        assert runner._steps_to_monitor == {step.name: step}
        assert future.running()
        runner._orchestrator.stop_isolated_step.side_effect = None
        runner._shutdown_requested = False

    runner._monitoring_loop()

    retry.assert_not_called()
    assert runner._orchestrator.stop_isolated_step.call_count == (
        int(explicit_stop) + int(stop_fails_once)
    )
    assert step.status == ExecutionStatus.STOPPED
    assert not future.running()
    with pytest.raises(RuntimeError, match="stopped"):
        future.wait()
    runner._future_registry.await_all_no_raise()
    assert not runner._steps_to_monitor


@pytest.mark.parametrize("failed", [False, True])
def test_drained_stop_uses_existing_terminal_status_update(
    runner: DynamicPipelineRunner,
    monkeypatch: pytest.MonkeyPatch,
    failed: bool,
) -> None:
    """Finalization reports STOPPED and leaves failure preservation to the server.

    Args:
        runner: The runner under test.
        monkeypatch: Fixture for replacing external dependencies.
        failed: Whether the server preserves an earlier failure.
    """
    runner._state = SimpleNamespace(claim=nullcontext)
    runner._pipeline = SimpleNamespace(
        name="parent",
        configuration=SimpleNamespace(parameters={}),
        _call_entrypoint=lambda: None,
    )
    runner.request_stop(PipelineRunStopMode.GRACEFUL)
    client = MagicMock()
    client.zen_store.update_run.return_value = SimpleNamespace(
        status=ExecutionStatus.FAILED if failed else ExecutionStatus.STOPPED
    )
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.Client", lambda: client
    )
    hooks = MagicMock()
    monkeypatch.setattr(runner, "_fire_terminal_run_hooks", hooks)

    runner._run_entrypoint_and_finalize()

    update = client.zen_store.update_run.call_args.kwargs["run_update"]
    assert update.model_dump(exclude_unset=True) == {
        "status": ExecutionStatus.STOPPED
    }
    assert hooks.call_args.args[0] == runner._run.status
