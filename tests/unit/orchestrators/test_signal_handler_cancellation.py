"""Tests for signal classification during pipeline cancellation."""

import signal
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
            ExecutionStatus.FAILED,
            PipelineRunStopMode.IMMEDIATE,
            ExecutionStatus.FAILED,
            RunInterruptedException,
            False,
        ),
        (
            ExecutionStatus.STOPPING,
            PipelineRunStopMode.IMMEDIATE,
            ExecutionStatus.COMPLETED,
            RunInterruptedException,
            False,
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
    """An actual signal is distinguished from graceful pipeline draining."""
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


@pytest.mark.parametrize(
    "previous_raises", [None, RuntimeError, KeyboardInterrupt]
)
def test_previous_callback_does_not_override_classified_stop(
    monkeypatch: pytest.MonkeyPatch,
    previous_raises: type[BaseException] | None,
) -> None:
    """Previous callbacks retain their effects without masking cancellation."""
    step = Mock(spec=StepRunResponse)
    step.name = "step"
    handler = SignalHandler(step, ExecutionMode.FAIL_FAST)
    stopped = RunStoppedException("Stopped by the user")
    monkeypatch.setattr(handler, "_finalize_shutdown", lambda: stopped)
    previous = Mock(side_effect=previous_raises)
    handler._previous[signal.SIGINT] = previous

    with pytest.raises(RunStoppedException) as caught:
        handler._handle(signal.SIGINT, None)

    assert caught.value is stopped
    previous.assert_called_once_with(signal.SIGINT, None)


def test_default_sigint_handler_does_not_replace_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default KeyboardInterrupt callback preserves the stop exception."""
    step = Mock(spec=StepRunResponse)
    step.name = "step"
    handler = SignalHandler(step, ExecutionMode.FAIL_FAST)
    stopped = RunStoppedException("Stopped by the user")
    monkeypatch.setattr(handler, "_finalize_shutdown", lambda: stopped)
    handler._previous[signal.SIGINT] = signal.default_int_handler

    with pytest.raises(RunStoppedException) as caught:
        handler._handle(signal.SIGINT, None)

    assert caught.value is stopped
