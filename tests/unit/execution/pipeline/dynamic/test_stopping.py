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
"""Cancellation coordination for dynamic pipeline execution."""

import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from typing import Iterator
from unittest.mock import MagicMock, PropertyMock
from uuid import uuid4

import pytest

from zenml.enums import (
    ExecutionMode,
    ExecutionStatus,
    PipelineRunStopMode,
    StepRuntime,
)
from zenml.exceptions import RunMonitoringError, RunStoppedException
from zenml.execution.pipeline.dynamic.future_registry import FutureRegistry
from zenml.execution.pipeline.dynamic.invocation_dependency_graph import (
    InvocationDependencyGraph,
)
from zenml.execution.pipeline.dynamic.outputs import (
    StepFuture,
    _IsolatedStepFuture,
)
from zenml.execution.pipeline.dynamic.runner import DynamicPipelineRunner
from zenml.execution.step.utils import launch_step


@pytest.fixture
def runner() -> Iterator[DynamicPipelineRunner]:
    """Build a runner without reading a stack or creating a run."""
    value = object.__new__(DynamicPipelineRunner)
    value._run = SimpleNamespace(id=uuid4(), stop_mode=None)
    value._pipeline = SimpleNamespace(name="parent")
    value._snapshot = MagicMock()
    value._orchestrator_run_id = "controller"
    value._orchestrator = MagicMock()
    value._step_operator = None
    value._stop_mode = None
    value._failure_detected = False
    value._shutdown_requested = False
    value._fail_fast = False
    value._continue_on_failure = True
    value._exception = None
    value._monitoring_exception = None
    value._monitoring_failures = {}
    value._drain_completed = True
    value._startup_thread = None
    value._lifecycle_lock = threading.RLock()
    value._startup_event = threading.Event()
    value._monitoring_event = threading.Event()
    value._cancellation_event = threading.Event()
    value._steps_to_monitor = {}
    value._existing_step_runs = {}
    value._existing_child_runs = {}
    value._child_runners = {}
    value._state = SimpleNamespace(id=None)
    value._pause_coordinator = MagicMock()
    value._dependency_graph = InvocationDependencyGraph()
    value._future_registry = FutureRegistry()
    value._executor = ThreadPoolExecutor(max_workers=1)
    yield value
    value._shutdown_requested = True
    value._executor.shutdown(wait=False, cancel_futures=True)


def make_step(
    status: ExecutionStatus = ExecutionStatus.RUNNING,
) -> SimpleNamespace:
    """Build an attempt with no configured backend dependencies."""
    return SimpleNamespace(
        id=uuid4(),
        name="step",
        status=status,
        duration=None,
        exception_info=None,
        config=SimpleNamespace(step_operator=None, outputs={}),
    )


@pytest.mark.parametrize("execution_mode", list(ExecutionMode))
def test_explicit_stop_and_escalation_ignore_failure_policy(
    runner: DynamicPipelineRunner, execution_mode: ExecutionMode
) -> None:
    """A stop remains effective after failure and can be retried/escalated."""
    runner._fail_fast = execution_mode == ExecutionMode.FAIL_FAST
    runner._continue_on_failure = (
        execution_mode == ExecutionMode.CONTINUE_ON_FAILURE
    )
    runner._failure_detected = True
    step = make_step()
    runner._steps_to_monitor[step.name] = step
    child = MagicMock(spec=DynamicPipelineRunner)
    runner._child_runners["child"] = child

    runner.request_stop(PipelineRunStopMode.GRACEFUL)
    runner._orchestrator.stop_isolated_step.assert_not_called()
    child.request_stop.assert_called_with(PipelineRunStopMode.GRACEFUL)

    runner.request_stop(PipelineRunStopMode.IMMEDIATE)
    runner.request_stop(PipelineRunStopMode.GRACEFUL)
    assert runner._stop_mode == PipelineRunStopMode.IMMEDIATE
    assert runner._orchestrator.stop_isolated_step.call_count == 2
    child.request_stop.assert_called_with(PipelineRunStopMode.IMMEDIATE)


def test_run_cancellation_observed_while_infrastructure_is_running(
    runner: DynamicPipelineRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An active Job does not prevent observing the run's cancellation."""
    step = make_step()
    runner._steps_to_monitor[step.name] = step
    client = MagicMock()
    client.zen_store.get_run.return_value = SimpleNamespace(
        id=runner._run.id, stop_mode=PipelineRunStopMode.GRACEFUL
    )
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.Client", lambda: client
    )
    monkeypatch.setattr(
        runner,
        "_get_isolated_step_infra_status",
        lambda _: ExecutionStatus.RUNNING,
    )
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.time.sleep", lambda _: None
    )
    runner._cancellation_event = MagicMock()
    runner._cancellation_event.wait.side_effect = lambda **_: setattr(
        runner, "_shutdown_requested", True
    )

    runner._cancellation_loop()
    runner._monitor_step(step.name, step)

    assert runner._stop_mode == PipelineRunStopMode.GRACEFUL
    assert runner._steps_to_monitor == {step.name: step}
    client.zen_store.get_run.assert_called_once_with(runner._run.id)
    client.get_run_step.assert_not_called()


@pytest.mark.parametrize("stopped", [False, True])
def test_suppressed_retry_settles_its_existing_future(
    runner: DynamicPipelineRunner,
    monkeypatch: pytest.MonkeyPatch,
    stopped: bool,
) -> None:
    """Suppressing an attempt must not strand its invocation in RETRYING."""
    step = make_step(ExecutionStatus.RETRYING)
    runner._failure_detected = not stopped
    runner._stop_mode = PipelineRunStopMode.GRACEFUL if stopped else None
    runner._steps_to_monitor[step.name] = step
    future = StepFuture(
        invocation_id=step.name,
        output_keys=[],
        execution_future=_IsolatedStepFuture(runner._run.id, step.name),
    )
    runner._future_registry.register_step_future(step.name, future)
    client = MagicMock()
    client.get_run_step.return_value = step
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.Client", lambda: client
    )
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.get_remaining_retries",
        lambda **_: 2,
    )
    monkeypatch.setattr(
        runner,
        "_get_isolated_step_infra_status",
        lambda _: ExecutionStatus.FAILED,
    )
    monkeypatch.setattr(runner, "_cleanup_isolated_step", lambda _: None)
    monkeypatch.setattr(runner, "apply_graph_update", lambda *_, **__: None)
    runner._dependency_graph = MagicMock()
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.utils.get_latest_step_run",
        lambda *_, **__: step,
    )

    def publish_stopped(_: object) -> SimpleNamespace:
        step.status = ExecutionStatus.STOPPED
        return step

    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.publish_stopped_step_run",
        publish_stopped,
    )
    runner._monitor_step(step.name, step)

    assert not future.running()
    assert runner._future_registry.await_all_no_raise(timeout=0)
    assert not runner._steps_to_monitor
    with pytest.raises(RunStoppedException if stopped else RuntimeError):
        future.wait()


def test_store_errors_do_not_kill_the_monitoring_thread(
    runner: DynamicPipelineRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sustained read failures remain visible without losing tracked work."""
    step = make_step()
    runner._steps_to_monitor[step.name] = step
    client = MagicMock()
    client.zen_store.get_run.return_value = runner._run
    client.get_run_step.side_effect = ConnectionError("store unavailable")
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.Client", lambda: client
    )
    monkeypatch.setattr(
        runner,
        "_get_isolated_step_infra_status",
        lambda _: ExecutionStatus.FAILED,
    )
    monkeypatch.setattr(runner, "record_failure", MagicMock())
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.time.sleep", lambda _: None
    )
    cycles = []

    def wait(**_: object) -> None:
        cycles.append(None)
        runner._shutdown_requested = len(cycles) == 3

    runner._monitoring_event = MagicMock()
    runner._monitoring_event.wait.side_effect = wait
    runner._monitoring_loop()

    assert len(cycles) == 3
    assert isinstance(runner._monitoring_exception, ConnectionError)
    assert runner._steps_to_monitor == {step.name: step}
    runner.record_failure.assert_called_once()


def test_immediate_stop_covers_a_submission_already_in_flight(
    runner: DynamicPipelineRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The existing submission future bridges the monitor-registration gap."""
    entered = threading.Event()
    release = threading.Event()
    step = make_step()
    compiled = SimpleNamespace(spec=SimpleNamespace(invocation_id=step.name))

    def launch(**_: object) -> SimpleNamespace:
        entered.set()
        assert release.wait(5)
        return step

    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.launch_step", launch
    )
    monkeypatch.setattr(runner, "mark_node_running", lambda **_: None)
    future = runner._queue_concurrent_isolated_step(compiled)
    try:
        assert entered.wait(5)
        runner.request_stop(PipelineRunStopMode.IMMEDIATE)
        runner._orchestrator.stop_isolated_step.assert_not_called()
    finally:
        release.set()
    assert future._wrapped.result(timeout=5) is step
    runner._orchestrator.stop_isolated_step.assert_called_once_with(step)


def test_immediate_drain_reports_unresolved_work(
    runner: DynamicPipelineRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A coordination deadline does not pretend a blocked workload stopped."""
    runner._stop_mode = PipelineRunStopMode.IMMEDIATE
    runner._steps_to_monitor["step"] = make_step()
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.handle_float_env_var",
        lambda *_, **__: 0.0,
    )
    with pytest.raises(TimeoutError, match="shutdown is incomplete"):
        runner._drain_work()
    assert not runner._drain_completed


def test_isolated_future_waits_for_stopping_and_can_be_settled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """STOPPING is not terminal; explicit settlement wakes a waiting future."""
    observed = threading.Event()
    errors = []
    step = make_step(ExecutionStatus.STOPPING)

    def latest(*_: object, **__: object) -> SimpleNamespace:
        observed.set()
        return step

    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.utils.get_latest_step_run", latest
    )
    future = _IsolatedStepFuture(uuid4(), "step")

    def wait() -> None:
        try:
            future.result()
        except BaseException as exception:
            errors.append(exception)

    thread = threading.Thread(target=wait, daemon=True)
    thread.start()
    assert observed.wait(5)
    assert thread.is_alive()
    exception = RunStoppedException("retry cancelled")
    future.set_exception(exception)
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert errors == [exception]


def test_registry_deadline_handles_status_read_failure() -> None:
    """An unavailable store is not followed by an unbounded result wait."""
    registry = FutureRegistry()
    future = MagicMock(spec=StepFuture)
    future.running.side_effect = ConnectionError("unavailable")
    registry.register_step_future("step", future)
    assert not registry.await_all_no_raise(timeout=0)
    future.wait.assert_not_called()


def test_retry_backoff_checks_cancellation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stopping during retry sleep prevents another launcher invocation."""
    launcher = MagicMock()
    launcher.return_value.launch.side_effect = RuntimeError("attempt failed")
    monkeypatch.setattr("zenml.execution.step.utils.StepLauncher", launcher)
    stopped = threading.Event()
    monkeypatch.setattr(
        "zenml.execution.step.utils.time.sleep", lambda _: stopped.set()
    )

    def check() -> None:
        if stopped.is_set():
            raise RunStoppedException("stop requested")

    step = SimpleNamespace(
        config=SimpleNamespace(
            name="step",
            retry=SimpleNamespace(max_retries=3, delay=100, backoff=1),
        )
    )
    with pytest.raises(RunStoppedException):
        launch_step(
            MagicMock(), step, "controller", retry=True, startup_check=check
        )
    assert launcher.call_count == 1


def test_only_first_launch_reuses_an_admitted_step_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A retry gets a new StepRun instead of reexecuting the admitted attempt."""
    first = MagicMock()
    first.launch.side_effect = RuntimeError("attempt failed")
    second = MagicMock()
    launcher = MagicMock(side_effect=[first, second])
    monkeypatch.setattr("zenml.execution.step.utils.StepLauncher", launcher)
    step_run_id = uuid4()
    step = SimpleNamespace(
        config=SimpleNamespace(
            name="step",
            retry=SimpleNamespace(max_retries=1, delay=0, backoff=1),
        )
    )
    launch_step(
        MagicMock(), step, "controller", retry=True, step_run_id=step_run_id
    )
    assert launcher.call_args_list[0].kwargs["step_run_id"] == step_run_id
    assert launcher.call_args_list[1].kwargs["step_run_id"] is None


@pytest.mark.parametrize("failure", ["status", "cleanup"])
def test_terminal_db_state_does_not_hide_backend_observation_failure(
    runner: DynamicPipelineRunner,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    """Unknown backend cleanup retains the attempt for retry and supervision."""
    step = make_step(ExecutionStatus.STOPPED)
    runner._steps_to_monitor[step.name] = step
    client = MagicMock()
    client.get_run_step.return_value = step
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.Client", lambda: client
    )
    status = MagicMock(return_value=ExecutionStatus.STOPPED)
    cleanup = MagicMock()
    if failure == "status":
        status.side_effect = ConnectionError("backend unavailable")
    else:
        cleanup.side_effect = ConnectionError("backend unavailable")
    monkeypatch.setattr(runner, "_get_isolated_step_infra_status", status)
    monkeypatch.setattr(runner._orchestrator, "cleanup_isolated_step", cleanup)

    with pytest.raises(ConnectionError):
        runner._monitor_step(step.name, step)
    assert runner._steps_to_monitor == {step.name: step}


def test_terminal_future_waits_for_backend_monitor_to_finish(
    runner: DynamicPipelineRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Execution settlement includes backend observation after a DB update."""
    step = make_step(ExecutionStatus.COMPLETED)
    runner._steps_to_monitor[step.name] = step
    execution = _IsolatedStepFuture(runner._run.id, step.name)
    execution._finished_step_run = step
    runner._future_registry.register_step_future(
        step.name,
        StepFuture(step.name, output_keys=[], execution_future=execution),
    )
    wait = MagicMock(side_effect=lambda _: runner._steps_to_monitor.clear())
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.time.sleep", wait
    )

    runner._settle_concurrent_work()

    wait.assert_called_once()


@pytest.mark.parametrize(
    "initial_status", [ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED]
)
def test_restarted_failed_controller_drains_existing_isolated_work_without_replay(
    runner: DynamicPipelineRunner,
    monkeypatch: pytest.MonkeyPatch,
    initial_status: ExecutionStatus,
) -> None:
    """Durable stop intent is honored even when the outcome is already FAILED."""
    runner._run = SimpleNamespace(
        id=runner._run.id,
        status=ExecutionStatus.FAILED,
        stop_mode=PipelineRunStopMode.GRACEFUL,
        in_progress=True,
    )
    step = make_step(status=initial_status)
    runner._existing_step_runs[step.name] = step
    client = MagicMock()
    client.zen_store.get_run.return_value = runner._run
    client.zen_store.update_run.return_value = runner._run
    client.get_run_step.return_value = step
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.Client", lambda: client
    )
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.get_step_runtime",
        lambda **_: (StepRuntime.ISOLATED, None),
    )
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.utils.get_latest_step_run",
        lambda *_, **__: step,
    )
    monkeypatch.setattr(
        DynamicPipelineRunner,
        "pipeline",
        PropertyMock(
            side_effect=AssertionError("User code must not be loaded")
        ),
    )

    def infrastructure(_: object) -> ExecutionStatus:
        step.status = ExecutionStatus.COMPLETED
        return ExecutionStatus.COMPLETED

    status = MagicMock(side_effect=infrastructure)
    monkeypatch.setattr(runner, "_get_isolated_step_infra_status", status)
    runner.run_pipeline()

    update = client.zen_store.update_run.call_args.kwargs["run_update"]
    assert update.status == ExecutionStatus.STOPPED
    assert update.in_progress is False
    assert update.stop_mode == PipelineRunStopMode.GRACEFUL
    assert not runner._steps_to_monitor
    status.assert_called_once_with(step)


@pytest.mark.parametrize("unresolved", ["inline", "child"])
def test_stopped_restart_reports_unknown_liveness_without_replaying(
    runner: DynamicPipelineRunner,
    monkeypatch: pytest.MonkeyPatch,
    unresolved: str,
) -> None:
    """A restarted controller cannot manufacture completion for lost work."""
    runner._run = SimpleNamespace(
        id=runner._run.id,
        status=ExecutionStatus.FAILED,
        stop_mode=PipelineRunStopMode.IMMEDIATE,
        in_progress=True,
    )
    if unresolved == "inline":
        step = make_step()
        runner._existing_step_runs[step.name] = step
    else:
        runner._existing_child_runs["child"] = SimpleNamespace(
            in_progress=True
        )
    monkeypatch.setattr(
        "zenml.execution.pipeline.dynamic.runner.get_step_runtime",
        lambda **_: (StepRuntime.INLINE, None),
    )
    monkeypatch.setattr(
        DynamicPipelineRunner,
        "pipeline",
        PropertyMock(
            side_effect=AssertionError("User code must not be loaded")
        ),
    )

    with pytest.raises(RunMonitoringError) as raised:
        runner.run_pipeline()
    assert "immediate" in str(raised.value.original_exception)
    assert runner._run.in_progress
