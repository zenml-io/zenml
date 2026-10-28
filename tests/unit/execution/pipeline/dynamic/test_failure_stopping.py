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
"""Persist dynamic failures before a later stop drains the remaining work."""

from contextlib import nullcontext
from types import SimpleNamespace
from typing import Callable
from unittest.mock import MagicMock

import pytest

from tests.unit.execution.pipeline.dynamic.test_stopping import (
    runner as runner,
)
from tests.unit.zen_stores.test_run_stopping import (
    create_run as create_run,
)
from tests.unit.zen_stores.test_run_stopping import (
    store as store,
)
from zenml.client import Client
from zenml.enums import ExecutionMode, ExecutionStatus, PipelineRunStopMode
from zenml.exceptions import RunStoppedException
from zenml.execution.pipeline.dynamic import runner as runner_module
from zenml.execution.pipeline.dynamic.runner import DynamicPipelineRunner
from zenml.models import (
    PipelineRunResponse,
    PipelineRunUpdate,
    StepRunRequest,
    StepRunUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.sql_zen_store import SqlZenStore


@pytest.mark.parametrize("during_settlement", [False, True])
@pytest.mark.parametrize("mode", [None, *PipelineRunStopMode])
@pytest.mark.parametrize("active_child", [False, True])
def test_failure_is_persisted_before_draining(
    runner: DynamicPipelineRunner,
    clean_client: Client,
    store: SqlZenStore,
    create_run: Callable[..., PipelineRunResponse],
    monkeypatch: pytest.MonkeyPatch,
    during_settlement: bool,
    mode: PipelineRunStopMode | None,
    active_child: bool,
) -> None:
    """A later stop preserves the original failure and closes run activity.

    Args:
        runner: Runner with isolated execution state.
        clean_client: Client connected to the disposable SQLite store.
        store: Disposable SQLite store.
        create_run: Factory for runs in the disposable store.
        monkeypatch: Fixture for replacing infrastructure and drain timing.
        during_settlement: Whether failure surfaces after the entrypoint returns.
        mode: Stop to request during draining, or None to finish normally.
        active_child: Whether only a child run has an active step.
    """
    run = create_run(execution_mode=ExecutionMode.STOP_ON_FAILURE)
    work_run = create_run(parent=run.id) if active_child else run
    active_step = store.create_run_step(
        StepRunRequest(
            name="step",
            project=work_run.project_id,
            pipeline_run_id=work_run.id,
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
    runner._continue_on_failure = False
    runner._state = SimpleNamespace(claim=nullcontext)
    runner._pipeline = SimpleNamespace(
        name="stopping",
        configuration=SimpleNamespace(parameters={}),
        entrypoint=entrypoint,
        _call_entrypoint=entrypoint,
    )
    hooks = MagicMock()
    monkeypatch.setattr(runner, "_fire_terminal_run_hooks", hooks)
    monkeypatch.setattr(runner_module, "Client", lambda: clean_client)
    publish_failure = MagicMock(
        wraps=runner_module.publish_failed_pipeline_run
    )
    monkeypatch.setattr(
        runner_module, "publish_failed_pipeline_run", publish_failure
    )

    def finish_outstanding_work() -> None:
        before_stop = store.get_run(run.id)
        assert before_stop.status == ExecutionStatus.FAILED
        assert before_stop.in_progress
        assert before_stop.end_time is None
        assert before_stop.exception_info is not None
        assert before_stop.exception_info.message == str(original)
        assert runner._exception is original

        if mode is not None:
            requested = store.update_run(
                run.id, PipelineRunUpdate(stop_mode=mode)
            )
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
        if active_child:
            store.update_run(
                work_run.id,
                PipelineRunUpdate(status=ExecutionStatus.COMPLETED),
            )

    monkeypatch.setattr(
        runner._future_registry,
        "await_all_no_raise",
        finish_outstanding_work,
    )

    if mode is None:
        with pytest.raises(ValueError) as raised:
            runner._run_entrypoint_and_finalize()
        assert raised.value is original
    else:
        runner._run_entrypoint_and_finalize()

    final = store.get_run(run.id)
    assert final.status == ExecutionStatus.FAILED
    assert final.exception_info is not None
    assert final.exception_info.message == str(original)
    assert final.exception_info.source == "builtins.ValueError"
    assert not final.in_progress
    assert final.end_time is not None
    assert final.stop_mode == mode
    assert store.get_run_step(active_step.id).status == (
        ExecutionStatus.STOPPED
        if mode == PipelineRunStopMode.IMMEDIATE
        else ExecutionStatus.COMPLETED
    )
    if active_child:
        child = store.get_run(work_run.id)
        assert not child.in_progress
        assert child.end_time is not None
    assert publish_failure.call_count == (2 if mode is None else 1)
    hooks.assert_called_once_with(ExecutionStatus.FAILED, original)


@pytest.mark.parametrize("mode", list(PipelineRunStopMode))
@pytest.mark.parametrize("exception_class", [RunStoppedException, ValueError])
def test_exception_after_stop_does_not_replace_stopped_outcome(
    runner: DynamicPipelineRunner,
    clean_client: Client,
    store: SqlZenStore,
    create_run: Callable[..., PipelineRunResponse],
    monkeypatch: pytest.MonkeyPatch,
    mode: PipelineRunStopMode,
    exception_class: type[Exception],
) -> None:
    """Only failures preceding the stop are preserved as failed outcomes.

    Args:
        runner: Runner with isolated execution state.
        clean_client: Client connected to the disposable SQLite store.
        store: Disposable SQLite store.
        create_run: Factory for runs in the disposable store.
        monkeypatch: Fixture for replacing infrastructure calls.
        mode: Explicit stop mode observed before cancellation.
        exception_class: Failure or cancellation raised after the stop.
    """
    run = create_run()
    store.update_run(run.id, PipelineRunUpdate(stop_mode=mode))
    runner._run = run
    runner.request_stop(mode)
    runner._state = SimpleNamespace(claim=nullcontext)
    runner._pipeline = SimpleNamespace(
        name="stopping",
        configuration=SimpleNamespace(parameters={}),
        _call_entrypoint=MagicMock(side_effect=exception_class("after stop")),
    )
    monkeypatch.setattr(runner, "_fire_terminal_run_hooks", MagicMock())
    monkeypatch.setattr(runner_module, "Client", lambda: clean_client)
    publish_failure = MagicMock(
        wraps=runner_module.publish_failed_pipeline_run
    )
    monkeypatch.setattr(
        runner_module, "publish_failed_pipeline_run", publish_failure
    )

    runner._run_entrypoint_and_finalize()

    final = store.get_run(run.id)
    assert final.status == ExecutionStatus.STOPPED
    assert final.exception_info is None
    assert not final.in_progress
    assert final.end_time is not None
    publish_failure.assert_not_called()
