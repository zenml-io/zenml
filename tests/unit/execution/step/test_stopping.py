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
"""Stop regressions for synchronous step retries."""

from types import SimpleNamespace
from unittest.mock import Mock, call
from uuid import uuid4

import pytest

from zenml.config.retry_config import StepRetryConfig
from zenml.enums import ExecutionStatus, PipelineRunStopMode
from zenml.exceptions import IllegalOperationError, RunStoppedException
from zenml.execution.context import ExecutionContext
from zenml.execution.pipeline.dynamic.run_context import (
    DynamicPipelineRunContext,
)
from zenml.execution.step import utils


@pytest.fixture
def state(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Prepare a launcher and client without accessing a configured workspace.

    Args:
        monkeypatch: Fixture for replacing external dependencies.

    Returns:
        Context state and mocked launch, store, and sleep operations.
    """
    run = Mock(id=uuid4(), status=ExecutionStatus.RUNNING, stop_mode=None)
    step = Mock()
    step.config.name = "step"
    step.config.retry = StepRetryConfig(max_retries=3, delay=30, backoff=2)
    launcher = Mock()
    launcher_factory = Mock(return_value=launcher)
    client = Mock()
    client.get_pipeline_run.return_value = run
    client_factory = Mock(return_value=client)
    sleep = Mock()
    monkeypatch.setattr(utils, "StepLauncher", launcher_factory)
    monkeypatch.setattr(utils, "Client", client_factory)
    monkeypatch.setattr("zenml.execution.step.utils.time.sleep", sleep)
    return SimpleNamespace(
        run=run,
        step=step,
        snapshot=Mock(),
        runner=Mock(),
        launcher=launcher,
        launcher_factory=launcher_factory,
        client=client,
        client_factory=client_factory,
        sleep=sleep,
    )


@pytest.mark.parametrize("dynamic", [False, True])
@pytest.mark.parametrize("mode", list(PipelineRunStopMode))
def test_stop_interrupts_retry_backoff(
    state: SimpleNamespace, dynamic: bool, mode: PipelineRunStopMode
) -> None:
    """A stop during a 30-second backoff prevents another attempt promptly.

    Args:
        state: Mocked execution dependencies.
        dynamic: Whether the owning context is a dynamic pipeline context.
        mode: Requested stop mode.
    """
    state.launcher.launch.side_effect = ValueError("Step failed")
    state.sleep.side_effect = lambda _: setattr(state.run, "stop_mode", mode)
    context = (
        DynamicPipelineRunContext(
            pipeline=Mock(),
            snapshot=state.snapshot,
            run=state.run,
            runner=state.runner,
        )
        if dynamic
        else ExecutionContext(pipeline_run=state.run)
    )

    with context, pytest.raises(RunStoppedException):
        utils.launch_step(state.snapshot, state.step, "controller", retry=True)

    state.launcher.launch.assert_called_once()
    state.sleep.assert_called_once_with(1)
    if dynamic:
        state.runner.request_stop.assert_called_once_with(mode)
    else:
        state.runner.request_stop.assert_not_called()


@pytest.mark.parametrize(
    "status,mode",
    [
        (ExecutionStatus.FAILED, PipelineRunStopMode.GRACEFUL),
        (ExecutionStatus.FAILED, PipelineRunStopMode.IMMEDIATE),
        (ExecutionStatus.STOPPING, None),
        (ExecutionStatus.STOPPED, None),
    ],
)
def test_stop_is_checked_before_the_first_attempt(
    state: SimpleNamespace,
    status: ExecutionStatus,
    mode: PipelineRunStopMode | None,
) -> None:
    """Persisted modes and legacy stopped states both prevent launching.

    Args:
        state: Mocked execution dependencies.
        status: Current status of the owning run.
        mode: Optional persisted stop mode.
    """
    state.run.status = status
    state.run.stop_mode = mode
    parent_run = Mock(id=uuid4())
    with (
        ExecutionContext(pipeline_run=parent_run),
        DynamicPipelineRunContext(
            pipeline=Mock(),
            snapshot=state.snapshot,
            run=state.run,
            runner=state.runner,
        ),
        pytest.raises(RunStoppedException),
    ):
        utils.launch_step(state.snapshot, state.step, "controller", retry=True)

    state.launcher_factory.assert_not_called()
    state.sleep.assert_not_called()
    state.client.get_pipeline_run.assert_called_once_with(
        state.run.id, hydrate=False
    )
    state.runner.request_stop.assert_called_once_with(
        mode or PipelineRunStopMode.IMMEDIATE
    )


def test_store_stop_rejection_does_not_consume_retries(
    state: SimpleNamespace,
) -> None:
    """A stop racing attempt creation is surfaced as cancellation.

    Args:
        state: Mocked execution dependencies.
    """

    def reject_attempt() -> None:
        """Simulate a stop arriving between the precheck and attempt creation.

        Raises:
            IllegalOperationError: The store rejects the new attempt.
        """
        state.run.stop_mode = PipelineRunStopMode.GRACEFUL
        raise IllegalOperationError("Cannot create step after stop")

    state.launcher.launch.side_effect = reject_attempt
    with (
        ExecutionContext(pipeline_run=state.run),
        pytest.raises(RunStoppedException),
    ):
        utils.launch_step(state.snapshot, state.step, "controller", retry=True)

    state.launcher.launch.assert_called_once()
    state.sleep.assert_not_called()


def test_unrelated_store_error_retries_and_preserves_the_error(
    state: SimpleNamespace,
) -> None:
    """An unrelated IllegalOperationError remains an ordinary step failure.

    Args:
        state: Mocked execution dependencies.
    """
    state.step.config.retry = StepRetryConfig(
        max_retries=3, delay=2, backoff=2
    )
    error = IllegalOperationError("Unrelated store error")
    state.launcher.launch.side_effect = error
    with (
        ExecutionContext(pipeline_run=state.run),
        pytest.raises(IllegalOperationError) as caught,
    ):
        utils.launch_step(state.snapshot, state.step, "controller", retry=True)

    assert caught.value is error
    assert state.launcher.launch.call_count == 4
    assert state.sleep.call_args_list == [call(1)] * (2 + 4 + 8)
