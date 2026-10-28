"""Stop requests retain their mode across old and new server responses."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from zenml.enums import ExecutionStatus, PipelineRunStopMode
from zenml.exceptions import IllegalOperationError
from zenml.orchestrators import base_orchestrator
from zenml.orchestrators.base_orchestrator import BaseOrchestrator


@pytest.mark.parametrize("graceful", [False, True])
def test_old_server_stop_preserves_requested_backend_mode(
    monkeypatch: pytest.MonkeyPatch, graceful: bool
) -> None:
    """An omitted capability field uses the legacy status update contract.

    Args:
        monkeypatch: Fixture for replacing external collaborators.
        graceful: Whether to request graceful stopping.
    """
    run = SimpleNamespace(
        id=uuid4(),
        status=ExecutionStatus.RUNNING,
        orchestrator_run_id="job",
        stop_mode=None,
    )
    update = Mock(return_value=run)
    client = SimpleNamespace(zen_store=SimpleNamespace(update_run=update))
    monkeypatch.setattr(base_orchestrator, "Client", lambda: client)
    orchestrator = Mock()

    BaseOrchestrator.stop_run(orchestrator, run, graceful=graceful)

    request = update.call_args.kwargs["run_update"]
    assert request.status == ExecutionStatus.STOPPING
    assert request.stop_mode == (
        PipelineRunStopMode.GRACEFUL
        if graceful
        else PipelineRunStopMode.IMMEDIATE
    )
    orchestrator._stop_run.assert_called_once_with(run=run, graceful=graceful)


def test_persisted_immediate_mode_cannot_be_downgraded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Backend cleanup follows the server's strongest persisted stop request.

    Args:
        monkeypatch: Fixture for replacing external collaborators.
    """
    run = SimpleNamespace(
        id=uuid4(),
        status=ExecutionStatus.FAILED,
        orchestrator_run_id="job",
        stop_mode=PipelineRunStopMode.IMMEDIATE,
    )
    update = Mock(return_value=run)
    client = SimpleNamespace(zen_store=SimpleNamespace(update_run=update))
    monkeypatch.setattr(base_orchestrator, "Client", lambda: client)
    orchestrator = Mock()

    monkeypatch.setattr(
        base_orchestrator, "publish_pipeline_run_status_update", Mock()
    )

    BaseOrchestrator.stop_run(orchestrator, run, graceful=True)

    request = update.call_args.kwargs["run_update"]
    assert request.status == ExecutionStatus.STOPPING
    assert request.stop_mode == PipelineRunStopMode.GRACEFUL
    orchestrator._stop_run.assert_called_once_with(run=run, graceful=False)


@pytest.mark.parametrize(
    "status,backend_id",
    [(ExecutionStatus.COMPLETED, "job"), (ExecutionStatus.RUNNING, None)],
)
def test_unstoppable_run_is_rejected_before_backend_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    status: ExecutionStatus,
    backend_id: str | None,
) -> None:
    """Completed runs and runs without a backend ID cannot be stopped.

    Args:
        monkeypatch: Fixture for replacing external collaborators.
        status: Stored execution status.
        backend_id: Existing orchestrator run identifier.
    """
    run = SimpleNamespace(
        id=uuid4(),
        status=status,
        orchestrator_run_id=backend_id,
    )
    client = Mock()
    monkeypatch.setattr(base_orchestrator, "Client", lambda: client)

    message = "completed" if backend_id else "no orchestrator run id"
    with pytest.raises(IllegalOperationError, match=message):
        BaseOrchestrator.stop_run(Mock(), run, graceful=True)

    client.zen_store.update_run.assert_not_called()
