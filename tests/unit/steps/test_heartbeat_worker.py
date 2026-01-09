import logging
import time
import uuid
from datetime import datetime, timezone

import pytest

from zenml.config.global_config import GlobalConfiguration
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import (
    InputSpec,
    StepConfiguration,
    StepSpec,
)
from zenml.enums import ExecutionStatus
from zenml.models import (
    StepHeartbeatResponse,
    StepRunResponse,
    StepRunResponseBody,
    StepRunResponseMetadata,
)
from zenml.steps.heartbeat import StepHeartbeatWorker

logger = logging.getLogger(__name__)


class FakeServerHeartbeat:
    def __init__(self, step_id):
        self.execution_status = ExecutionStatus.RUNNING
        self.heartbeat_enabled = True
        self._call_count = 0
        self.step_id = step_id

    def update_step_heartbeat(self, step_run_id) -> StepHeartbeatResponse:
        if self.step_id == step_run_id:
            self._call_count += 1

            return StepHeartbeatResponse(
                status=self.execution_status,
                pipeline_run_status=self.execution_status,
                id=step_run_id,
                latest_heartbeat=datetime.now(tz=timezone.utc),
                heartbeat_enabled=self.heartbeat_enabled,
            )

        else:
            logger.info(f"Race condition for {step_run_id} was met")
            return StepHeartbeatResponse(
                status=ExecutionStatus.RUNNING,
                pipeline_run_status=ExecutionStatus.RUNNING,
                id=step_run_id,
                latest_heartbeat=datetime.now(tz=timezone.utc),
                heartbeat_enabled=True,
            )


def test_heartbeat_worker_with_remote_stopping(monkeypatch):
    step_run_id = uuid.uuid4()

    worker = StepHeartbeatWorker(step_id=step_run_id)

    worker._heartbeat_interval_seconds = 0.1

    fake_server = FakeServerHeartbeat(step_id=step_run_id)

    assert not worker.is_terminated
    assert not worker.is_running

    with monkeypatch.context() as m:
        global_config = GlobalConfiguration()

        m.setattr(global_config, "_zen_store", fake_server)

        worker.start()

        assert worker.is_running
        assert not worker.is_terminated

        time.sleep(0.1)

        assert fake_server._call_count >= 1

        with pytest.raises(KeyboardInterrupt):
            fake_server.execution_status = ExecutionStatus.STOPPED

            time.sleep(0.2)

        assert not worker.is_running
        assert worker.is_terminated


def test_heartbeat_worker_with_eager_stopping(monkeypatch):
    step_run_id = uuid.uuid4()

    worker = StepHeartbeatWorker(step_id=step_run_id)

    worker.STEP_HEARTBEAT_INTERVAL_SECONDS = 0.1

    fake_server = FakeServerHeartbeat(step_id=step_run_id)

    assert not worker.is_terminated
    assert not worker.is_running

    with monkeypatch.context() as m:
        global_config = GlobalConfiguration()

        m.setattr(global_config, "_zen_store", fake_server)

        worker.start()

        assert worker.is_running
        assert not worker.is_terminated

        time.sleep(0.2)

        assert fake_server._call_count >= 1

        worker.stop()

        assert not worker.is_running
        assert not worker.is_terminated


def test_worker_with_disabled_heartbeat(monkeypatch):
    step_run_id = uuid.uuid4()

    worker = StepHeartbeatWorker(step_id=step_run_id)

    worker._heartbeat_interval_seconds = 0.1

    fake_server = FakeServerHeartbeat(step_id=step_run_id)

    assert not worker.is_terminated
    assert not worker.is_running

    with monkeypatch.context() as m:
        global_config = GlobalConfiguration()

        m.setattr(global_config, "_zen_store", fake_server)

        worker.start()

        assert worker.is_running
        assert not worker.is_terminated

        time.sleep(0.1)

        assert fake_server._call_count >= 1

        fake_server.heartbeat_enabled = False

        time.sleep(0.2)

        assert not worker.is_running
        assert not worker.is_terminated


def test_heartbeat_healthiness_check(monkeypatch):
    from zenml.steps import heartbeat

    passable_diff_time = datetime(
        year=2025, month=11, day=27, hour=12, minute=35, tzinfo=timezone.utc
    )
    non_passable_diff_time = datetime(
        year=2025, month=11, day=27, hour=12, minute=27, tzinfo=timezone.utc
    )

    step_run = StepRunResponse(
        id=uuid.uuid4(),
        name="test",
        body=StepRunResponseBody(
            status=ExecutionStatus.RUNNING,
            project_id=uuid.uuid4(),
            created=datetime(
                year=2025,
                month=11,
                day=27,
                hour=12,
                minute=30,
                tzinfo=timezone.utc,
            ),
            updated=datetime(
                year=2025,
                month=11,
                day=27,
                hour=12,
                minute=30,
                tzinfo=timezone.utc,
            ),
            version=1,
            is_retriable=False,
            start_time=None,
            latest_heartbeat=None,
            heartbeat_threshold=10,
        ),
        metadata=StepRunResponseMetadata(
            config=StepConfiguration(
                name="test", heartbeat_healthy_threshold=10
            ),
            spec=StepSpec(
                enable_heartbeat=True,
                source=Source(module="test", type=SourceType.BUILTIN),
                upstream_steps=["test"],
                inputs={
                    "test": InputSpec(step_name="test", output_name="test")
                },
                invocation_id="test",
            ),
            pipeline_run_id=uuid.uuid4(),
            snapshot_id=uuid.uuid4(),
        ),
    )

    fixed = datetime(
        year=2025, month=11, day=27, hour=12, minute=38, tzinfo=timezone.utc
    )

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed if tz is None else fixed.replace(tzinfo=tz)

    with monkeypatch.context() as m:
        m.setattr(heartbeat, "datetime", FixedDateTime)
        # based on start-time is unhealthy
        step_run.body.start_time = non_passable_diff_time
        assert heartbeat.is_heartbeat_unhealthy(
            step_run_id=step_run.id,
            status=step_run.status,
            start_time=step_run.start_time,
            heartbeat_threshold=step_run.heartbeat_threshold,
            latest_heartbeat=step_run.latest_heartbeat,
        )

        # based on start-time is healthy
        step_run.body.start_time = passable_diff_time
        assert not heartbeat.is_heartbeat_unhealthy(
            step_run_id=step_run.id,
            status=step_run.status,
            start_time=step_run.start_time,
            heartbeat_threshold=step_run.heartbeat_threshold,
            latest_heartbeat=step_run.latest_heartbeat,
        )

        # based on heartbeat is unhealthy
        step_run.body.start_time = passable_diff_time
        step_run.body.latest_heartbeat = non_passable_diff_time
        assert heartbeat.is_heartbeat_unhealthy(
            step_run_id=step_run.id,
            status=step_run.status,
            start_time=step_run.start_time,
            heartbeat_threshold=step_run.heartbeat_threshold,
            latest_heartbeat=step_run.latest_heartbeat,
        )

        # based on heartbeat is healthy
        step_run.body.start_time = non_passable_diff_time
        step_run.body.latest_heartbeat = passable_diff_time
        assert not heartbeat.is_heartbeat_unhealthy(
            step_run_id=step_run.id,
            status=step_run.status,
            start_time=step_run.start_time,
            heartbeat_threshold=step_run.heartbeat_threshold,
            latest_heartbeat=step_run.latest_heartbeat,
        )

        # edge-case where both values null = healthy (default response)
        step_run.body.start_time = None
        step_run.body.latest_heartbeat = None
        assert not heartbeat.is_heartbeat_unhealthy(
            step_run_id=step_run.id,
            status=step_run.status,
            start_time=step_run.start_time,
            heartbeat_threshold=step_run.heartbeat_threshold,
            latest_heartbeat=step_run.latest_heartbeat,
        )

        # if step heartbeat not enabled = healthy (default response)
        step_run.body.start_time = non_passable_diff_time
        step_run.body.heartbeat_threshold = None
        assert not heartbeat.is_heartbeat_unhealthy(
            step_run_id=step_run.id,
            status=step_run.status,
            start_time=step_run.start_time,
            heartbeat_threshold=step_run.heartbeat_threshold,
            latest_heartbeat=step_run.latest_heartbeat,
        )
