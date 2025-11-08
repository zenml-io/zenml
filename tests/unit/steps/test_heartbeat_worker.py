import time
import uuid
from datetime import datetime, timezone

import pytest

from zenml import StepHeartbeatResponse
from zenml.config.global_config import GlobalConfiguration
from zenml.enums import ExecutionStatus
from zenml.steps.heartbeat import StepHeartbeatWorker


class FakeServerHeartbeat:
    def __init__(self):
        self.execution_status = ExecutionStatus.RUNNING
        self._call_count = 0

    def update_step_heartbeat(self, step_run_id) -> StepHeartbeatResponse:
        self._call_count += 1

        return StepHeartbeatResponse(
            status=self.execution_status,
            id=step_run_id,
            latest_heartbeat=datetime.now(tz=timezone.utc),
        )


def test_heartbeat_worker_with_remote_stopping(monkeypatch):
    step_run_id = uuid.uuid4()

    worker = StepHeartbeatWorker(step_id=step_run_id)

    worker.STEP_HEARTBEAT_INTERVAL_SECONDS = 1

    fake_server = FakeServerHeartbeat()

    assert not worker.is_terminated
    assert not worker.is_running

    with monkeypatch.context() as m:
        global_config = GlobalConfiguration()

        m.setattr(global_config, "_zen_store", fake_server)

        worker.start()

        assert worker.is_running
        assert not worker.is_terminated

        time.sleep(1)

        assert fake_server._call_count >= 1

        with pytest.raises(KeyboardInterrupt):
            fake_server.execution_status = ExecutionStatus.STOPPED

            time.sleep(2)

        assert not worker.is_running
        assert worker.is_terminated


def test_heartbeat_worker_with_eager_stopping(monkeypatch):
    step_run_id = uuid.uuid4()

    worker = StepHeartbeatWorker(step_id=step_run_id)

    worker.STEP_HEARTBEAT_INTERVAL_SECONDS = 1

    fake_server = FakeServerHeartbeat()

    assert not worker.is_terminated
    assert not worker.is_running

    with monkeypatch.context() as m:
        global_config = GlobalConfiguration()

        m.setattr(global_config, "_zen_store", fake_server)

        worker.start()

        assert worker.is_running
        assert not worker.is_terminated

        time.sleep(1)

        assert fake_server._call_count >= 1

        worker.stop()

        assert not worker.is_running
        assert not worker.is_terminated
