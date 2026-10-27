"""Tests for cancellation observation and heartbeat recovery."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from zenml.enums import ExecutionStatus, PipelineRunStopMode
from zenml.models import StepHeartbeatResponse
from zenml.steps import heartbeat
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
    """Run cancellation respects mode without masking step cancellation."""
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


def test_successful_heartbeat_restores_polling_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Transient authentication failures do not leave polling in backoff."""
    worker = StepHeartbeatWorker(uuid4())
    poll = Mock(
        side_effect=[
            RuntimeError("credentials"),
            RuntimeError("credentials"),
            RuntimeError("credentials"),
            None,
        ]
    )
    sleeps: list[int] = []

    def sleep(seconds: int) -> None:
        sleeps.append(seconds)
        if len(sleeps) == 4:
            worker.stop()

    monkeypatch.setattr(worker, "_heartbeat", poll)
    monkeypatch.setattr(heartbeat.time, "sleep", sleep)
    worker._running = True

    worker._run()

    assert sleeps == [15, 15, 300, 15]
    assert not worker.is_terminated


def test_observed_cancellation_survives_later_heartbeat_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lost credentials cannot undo an already observed stop request."""
    worker = StepHeartbeatWorker(uuid4())
    sleeps: list[int] = []
    interrupts = Mock()

    def sleep(seconds: int) -> None:
        sleeps.append(seconds)
        if len(sleeps) == 4:
            worker.stop()

    monkeypatch.setattr(
        worker, "_heartbeat", Mock(side_effect=RuntimeError("credentials"))
    )
    monkeypatch.setattr(heartbeat._thread, "interrupt_main", interrupts)
    monkeypatch.setattr(heartbeat.time, "sleep", sleep)
    worker._running = True
    worker._terminated = True

    worker._run()

    assert sleeps == [15, 15, 15, 15]
    assert interrupts.call_count == 4
    assert worker.is_terminated
