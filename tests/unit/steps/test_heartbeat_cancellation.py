"""Tests for cancellation observation and heartbeat recovery."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from zenml.enums import ExecutionStatus, PipelineRunStopMode
from zenml.models import StepHeartbeatResponse
from zenml.steps.heartbeat import StepHeartbeatWorker


@pytest.mark.parametrize(
    "mode,run_status,step_status,expected",
    [
        (
            PipelineRunStopMode.GRACEFUL,
            ExecutionStatus.STOPPING,
            ExecutionStatus.RUNNING,
            False,
        ),
        (
            PipelineRunStopMode.GRACEFUL,
            ExecutionStatus.FAILED,
            ExecutionStatus.RUNNING,
            False,
        ),
        (
            PipelineRunStopMode.IMMEDIATE,
            ExecutionStatus.FAILED,
            ExecutionStatus.RUNNING,
            True,
        ),
        (None, ExecutionStatus.STOPPING, ExecutionStatus.RUNNING, True),
        (None, ExecutionStatus.RUNNING, ExecutionStatus.RUNNING, False),
        (
            PipelineRunStopMode.GRACEFUL,
            ExecutionStatus.STOPPING,
            ExecutionStatus.CANCELLING,
            True,
        ),
        (
            PipelineRunStopMode.GRACEFUL,
            ExecutionStatus.STOPPING,
            ExecutionStatus.STOPPING,
            True,
        ),
    ],
)
def test_heartbeat_cancellation_modes(
    monkeypatch: pytest.MonkeyPatch,
    mode: PipelineRunStopMode | None,
    run_status: ExecutionStatus,
    step_status: ExecutionStatus,
    expected: bool,
) -> None:
    """Run cancellation respects mode without masking step cancellation.

    Args:
        monkeypatch: Fixture for replacing external collaborators.
        mode: Requested stop mode.
        run_status: Pipeline status before the stop.
        step_status: Status of the current step attempt.
        expected: Whether the worker should interrupt execution.
    """
    worker = StepHeartbeatWorker(uuid4())
    response = StepHeartbeatResponse(
        id=worker.step_id,
        status=step_status,
        pipeline_run_status=run_status,
        stop_mode=mode,
        heartbeat_enabled=True,
        latest_heartbeat=datetime.now(timezone.utc),
    )
    store = Mock(update_step_heartbeat=Mock(return_value=response))
    monkeypatch.setattr(
        "zenml.config.global_config.GlobalConfiguration",
        lambda: SimpleNamespace(zen_store=store),
    )

    worker._heartbeat()

    assert worker.is_terminated is expected
    store.update_step_heartbeat.assert_called_once_with(
        step_run_id=worker.step_id,
        heartbeat_liveness_timeout_seconds=315,
    )
