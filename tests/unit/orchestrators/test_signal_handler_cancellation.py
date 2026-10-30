"""Tests for signal classification during pipeline cancellation."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from zenml.enums import ExecutionMode, ExecutionStatus, PipelineRunStopMode
from zenml.exceptions import RunInterruptedException, RunStoppedException
from zenml.models import StepRunResponse
from zenml.orchestrators import signal_handler
from zenml.orchestrators.signal_handler import SignalHandler


@pytest.mark.parametrize(
    "run_status,mode,step_status,expected_exception,should_publish",
    [
        (
            ExecutionStatus.FAILED,
            PipelineRunStopMode.IMMEDIATE,
            ExecutionStatus.RUNNING,
            RunStoppedException,
            True,
        ),
        (
            ExecutionStatus.FAILED,
            PipelineRunStopMode.GRACEFUL,
            ExecutionStatus.RUNNING,
            RunInterruptedException,
            False,
        ),
        (
            ExecutionStatus.STOPPING,
            PipelineRunStopMode.GRACEFUL,
            ExecutionStatus.RUNNING,
            RunInterruptedException,
            False,
        ),
        (
            ExecutionStatus.FAILED,
            None,
            ExecutionStatus.RUNNING,
            RunStoppedException,
            True,
        ),
        (
            ExecutionStatus.STOPPING,
            None,
            ExecutionStatus.RUNNING,
            RunStoppedException,
            True,
        ),
        (
            ExecutionStatus.STOPPING,
            PipelineRunStopMode.GRACEFUL,
            ExecutionStatus.STOPPING,
            RunStoppedException,
            True,
        ),
    ],
)
def test_signal_preserves_failures_and_respects_stop_mode(
    monkeypatch: pytest.MonkeyPatch,
    run_status: ExecutionStatus,
    mode: PipelineRunStopMode | None,
    step_status: ExecutionStatus,
    expected_exception: type[Exception],
    should_publish: bool,
) -> None:
    """An actual signal is distinguished from graceful pipeline draining.

    Args:
        monkeypatch: Fixture for replacing external collaborators.
        run_status: Pipeline status before the stop.
        mode: Requested stop mode.
        step_status: Status of the current step attempt.
        expected_exception: Expected signal classification.
        should_publish: Whether to publish a stopped step status.
    """
    step = Mock(spec=StepRunResponse)
    step.id = uuid4()
    step.pipeline_run_id = uuid4()
    step.status = step_status
    run = SimpleNamespace(status=run_status, stop_mode=mode)
    client = Mock(
        get_pipeline_run=Mock(return_value=run),
        get_run_step=Mock(return_value=step),
    )
    publish = Mock()
    monkeypatch.setattr(signal_handler, "Client", lambda: client)
    monkeypatch.setattr(
        signal_handler.publish_utils, "publish_step_run_status_update", publish
    )
    handler = SignalHandler(step, ExecutionMode.FAIL_FAST)

    result = handler._finalize_shutdown()

    assert isinstance(result, expected_exception)
    assert publish.call_count == int(should_publish)
    if should_publish:
        assert publish.call_args.kwargs["status"] == ExecutionStatus.STOPPED
    assert run.status == run_status
    client.zen_store.update_run.assert_not_called()
