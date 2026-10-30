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
from typing import Callable
from unittest.mock import MagicMock, call
from uuid import uuid4

import pytest

from tests.unit.zen_stores.test_run_stopping import (
    create_run as create_run,
)
from tests.unit.zen_stores.test_run_stopping import (
    store as store,
)
from zenml.client import Client
from zenml.enums import (
    ExecutionMode,
    ExecutionStatus,
    HookType,
    PipelineRunStopMode,
)
from zenml.execution.pipeline.dynamic import runner as runner_module
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
from zenml.models import (
    PipelineRunResponse,
    PipelineRunUpdate,
    StepRunRequest,
    StepRunUpdate,
)
from zenml.orchestrators import base_orchestrator, publish_utils
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.sql_zen_store import SqlZenStore


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
    value._orchestrator = MagicMock(supports_run_stop_modes=True)
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
    monkeypatch.setattr(runner_module, "Client", lambda: client)
    monkeypatch.setattr(
        runner, "_get_isolated_step_infra_status", lambda _: infra_status
    )
    monkeypatch.setattr(
        runner_module,
        "handle_float_env_var",
        lambda *args, **kwargs: 0.0,
    )
    runner._monitoring_event = MagicMock()
    runner._monitoring_event.wait.side_effect = lambda **kwargs: setattr(
        runner, "_shutdown_requested", True
    )
    runner._steps_to_monitor[step.name] = step
    return client


def test_immediate_stop_catches_late_submission_after_failure(
    runner: DynamicPipelineRunner,
) -> None:
    """An explicit stop cancels even late submissions after an earlier failure.

    Args:
        runner: The runner under test.
    """
    original_error = RuntimeError("original failure")
    runner._failure_detected = True
    runner._exception = original_error
    runner.request_stop(PipelineRunStopMode.IMMEDIATE)
    runner.request_stop(PipelineRunStopMode.GRACEFUL)
    assert runner._stop_mode == PipelineRunStopMode.IMMEDIATE
    assert runner._exception is original_error

    late_step = make_step(ExecutionStatus.PROVISIONING)
    runner._register_isolated_step_for_monitoring("late", late_step)
    runner._orchestrator.stop_isolated_step.assert_called_once_with(late_step)


@pytest.mark.parametrize("mode", list(PipelineRunStopMode))
def test_stop_is_observed_while_infrastructure_remains_active(
    runner: DynamicPipelineRunner,
    monkeypatch: pytest.MonkeyPatch,
    mode: PipelineRunStopMode,
) -> None:
    """Running infrastructure must not skip checking the run's stop request.

    Args:
        runner: The runner under test.
        monkeypatch: Fixture for replacing external dependencies.
        mode: Whether the running attempt should drain or stop immediately.
    """
    step = make_step(ExecutionStatus.RUNNING)
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


@pytest.mark.parametrize("mode", [None, *PipelineRunStopMode])
def test_removed_worker_is_stopped_only_after_immediate_request(
    runner: DynamicPipelineRunner,
    monkeypatch: pytest.MonkeyPatch,
    mode: PipelineRunStopMode | None,
) -> None:
    """A removed worker preserves cancellation without hiding ordinary failures.

    Args:
        runner: The runner under test.
        monkeypatch: Fixture for replacing external dependencies.
        mode: Optional stop mode requested before worker termination.
    """
    step = make_step(ExecutionStatus.PROVISIONING)
    runner._run.stop_mode = mode
    prepare_monitor_iteration(
        runner, step, ExecutionStatus.FAILED, monkeypatch
    )
    stopped = make_step(ExecutionStatus.STOPPED)
    failed = make_step(ExecutionStatus.FAILED)
    monkeypatch.setattr(
        runner_module, "publish_stopped_step_run", lambda _: stopped
    )
    monkeypatch.setattr(
        runner_module, "publish_failed_step_run", lambda _: failed
    )
    finished = MagicMock()
    monkeypatch.setattr(runner, "_on_step_finished", finished)

    runner._monitoring_loop()

    if mode == PipelineRunStopMode.IMMEDIATE:
        finished.assert_called_once_with(step_run=stopped)
    else:
        finished.assert_called_once_with(step_run=failed)
    assert not runner._steps_to_monitor


def test_suppressed_retry_settles_the_existing_future(
    runner: DynamicPipelineRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A suppressed retry must not leave the original future waiting forever.

    Args:
        runner: The runner under test.
        monkeypatch: Fixture for replacing external dependencies.
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
    runner._run.stop_mode = PipelineRunStopMode.GRACEFUL
    prepare_monitor_iteration(
        runner, step, ExecutionStatus.RUNNING, monkeypatch
    )
    monkeypatch.setattr(
        runner_module,
        "get_remaining_retries",
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
        runner_module,
        "publish_stopped_step_run",
        publish_stopped,
    )
    retry = MagicMock()
    monkeypatch.setattr(runner, "_queue_concurrent_isolated_step", retry)

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
    runner._orchestrator.stop_isolated_step.assert_called_with(step)
    assert step.status == ExecutionStatus.STOPPED
    assert not future.running()
    with pytest.raises(RuntimeError, match="stopped"):
        future.wait()
    runner._future_registry.await_all_no_raise()
    assert not runner._steps_to_monitor


@pytest.fixture
def hooks(
    runner: DynamicPipelineRunner, monkeypatch: pytest.MonkeyPatch
) -> MagicMock:
    """Observe hook dispatch without executing user hooks.

    Args:
        runner: Runner with isolated execution state.
        monkeypatch: Fixture for replacing hook execution.

    Returns:
        The hook execution mock.
    """
    runner._snapshot = SimpleNamespace(
        pipeline_configuration=SimpleNamespace(
            end_hook_source="end",
            failure_hook_source="failure",
            success_hook_source="success",
        )
    )
    hook = MagicMock()
    monkeypatch.setattr(runner_module, "run_lifecycle_hook", hook)
    return hook


@pytest.mark.parametrize(
    "mode,during_settlement",
    [
        (PipelineRunStopMode.GRACEFUL, False),
        (PipelineRunStopMode.IMMEDIATE, True),
        (None, False),
        (None, True),
    ],
)
def test_failure_drain_preserves_orchestrator_stop_contract(
    runner: DynamicPipelineRunner,
    clean_client: Client,
    store: SqlZenStore,
    create_run: Callable[..., PipelineRunResponse],
    monkeypatch: pytest.MonkeyPatch,
    hooks: MagicMock,
    during_settlement: bool,
    mode: PipelineRunStopMode | None,
) -> None:
    """Failure draining preserves modern failure outcomes and legacy stopping.

    Args:
        runner: Runner with isolated execution state.
        clean_client: Client connected to the disposable SQLite store.
        store: Disposable SQLite store.
        create_run: Factory for runs in the disposable store.
        monkeypatch: Fixture for replacing infrastructure and drain timing.
        hooks: Hook execution mock that preserves real dispatch decisions.
        during_settlement: Whether failure surfaces after the entrypoint returns.
        mode: Explicit stop mode, or None for a legacy status-only stop.
    """
    run = create_run(execution_mode=ExecutionMode.STOP_ON_FAILURE)
    active_step = store.create_run_step(
        StepRunRequest(
            name="step",
            project=run.project_id,
            pipeline_run_id=run.id,
            status=ExecutionStatus.RUNNING,
            start_time=utc_now(),
        )
    )
    original = ValueError("Pipeline failed before the stop request")

    def entrypoint() -> None:
        if during_settlement:
            runner.record_failure(original)
        else:
            raise original

    runner._run = run
    runner._orchestrator.supports_run_stop_modes = mode is not None
    runner._continue_on_failure = False
    runner._state = SimpleNamespace(claim=nullcontext)
    runner._pipeline = SimpleNamespace(
        name="stopping",
        configuration=SimpleNamespace(parameters={}),
        entrypoint=entrypoint,
        _call_entrypoint=entrypoint,
    )
    monkeypatch.setattr(runner_module, "Client", lambda: clean_client)
    monkeypatch.setattr(publish_utils, "Client", lambda: clean_client)

    def finish_outstanding_work() -> None:
        before_stop = store.get_run(run.id)
        assert before_stop.in_progress
        assert before_stop.end_time is None
        assert runner._exception is original
        if mode is None:
            assert before_stop.status == ExecutionStatus.RUNNING
            assert before_stop.exception_info is None
            base_orchestrator.BaseOrchestrator.stop_run(
                runner._orchestrator, before_stop, graceful=False
            )
            runner._orchestrator._stop_run.assert_called_once_with(
                run=before_stop, graceful=False
            )
            assert store.get_run(run.id).status == ExecutionStatus.STOPPING
            runner.request_stop(PipelineRunStopMode.IMMEDIATE)
            store.update_run_step(
                active_step.id,
                StepRunUpdate(
                    status=ExecutionStatus.STOPPED, end_time=utc_now()
                ),
            )
            return

        assert before_stop.status == ExecutionStatus.FAILED
        assert before_stop.exception_info is not None
        assert before_stop.exception_info.message == str(original)

        requested = store.update_run(run.id, PipelineRunUpdate(stop_mode=mode))
        assert requested.status == ExecutionStatus.FAILED
        runner.request_stop(mode)
        if mode == PipelineRunStopMode.IMMEDIATE:
            # Provider termination can leave database rows active until
            # the controller publishes the terminal stop update.
            return

        store.update_run_step(
            active_step.id,
            StepRunUpdate(
                status=ExecutionStatus.COMPLETED, end_time=utc_now()
            ),
        )

    monkeypatch.setattr(
        runner._future_registry,
        "await_all_no_raise",
        finish_outstanding_work,
    )

    runner._run_entrypoint_and_finalize()

    final = store.get_run(run.id)
    assert not final.in_progress
    assert final.end_time is not None
    assert final.stop_mode == mode
    assert store.get_run_step(active_step.id).status == (
        ExecutionStatus.STOPPED
        if mode in {None, PipelineRunStopMode.IMMEDIATE}
        else ExecutionStatus.COMPLETED
    )
    if mode is None:
        assert final.status == ExecutionStatus.STOPPED
        assert final.exception_info is None
        hooks.assert_called_once_with(
            "end", HookType.RUN_END, optional_args=(None,)
        )
        return

    assert final.status == ExecutionStatus.FAILED
    assert final.exception_info is not None
    assert final.exception_info.message == str(original)
    assert final.exception_info.source == "builtins.ValueError"
    assert hooks.call_args_list == [
        call("end", HookType.RUN_END, optional_args=(original,)),
        call("failure", HookType.RUN_FAILURE, optional_args=(original,)),
    ]


@pytest.mark.parametrize("mode", list(PipelineRunStopMode))
def test_stop_fires_only_the_end_hook(
    runner: DynamicPipelineRunner,
    clean_client: Client,
    store: SqlZenStore,
    create_run: Callable[..., PipelineRunResponse],
    monkeypatch: pytest.MonkeyPatch,
    hooks: MagicMock,
    mode: PipelineRunStopMode,
) -> None:
    """Cancellation records a stopped outcome without dispatching failure hooks.

    Args:
        runner: Runner with isolated execution state.
        clean_client: Client connected to the disposable SQLite store.
        store: Disposable SQLite store.
        create_run: Factory for runs in the disposable store.
        monkeypatch: Fixture for replacing infrastructure calls.
        hooks: Hook execution mock that preserves real dispatch decisions.
        mode: Explicit stop mode observed before cancellation.
    """
    run = create_run()
    store.update_run(run.id, PipelineRunUpdate(stop_mode=mode))
    runner._run = run
    runner.request_stop(mode)
    runner._state = SimpleNamespace(claim=nullcontext)
    runner._pipeline = SimpleNamespace(
        name="stopping",
        configuration=SimpleNamespace(parameters={}),
        _call_entrypoint=lambda: None,
    )
    monkeypatch.setattr(runner_module, "Client", lambda: clean_client)

    runner._run_entrypoint_and_finalize()

    final = store.get_run(run.id)
    assert final.status == ExecutionStatus.STOPPED
    assert final.exception_info is None
    assert not final.in_progress
    assert final.end_time is not None
    hooks.assert_called_once_with(
        "end", HookType.RUN_END, optional_args=(None,)
    )
