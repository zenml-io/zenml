"""Stop requests retain their mode across old and new server responses."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from zenml.enums import ExecutionStatus, PipelineRunStopMode
from zenml.exceptions import IllegalOperationError
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.utils import run_utils


@pytest.mark.parametrize("graceful", [False, True])
def test_old_server_stop_preserves_requested_backend_mode(
    monkeypatch: pytest.MonkeyPatch, graceful: bool
) -> None:
    """An omitted capability field uses the legacy status update contract."""
    run = SimpleNamespace(
        id=uuid4(),
        status=ExecutionStatus.RUNNING,
        orchestrator_run_id="job",
        stop_mode=None,
        get_body=lambda: SimpleNamespace(model_fields_set=set()),
    )
    update = Mock(return_value=run)
    client = SimpleNamespace(zen_store=SimpleNamespace(update_run=update))
    monkeypatch.setattr(run_utils, "Client", lambda: client)
    orchestrator = Mock()

    BaseOrchestrator.stop_run(orchestrator, run, graceful=graceful)

    request = update.call_args.kwargs["run_update"]
    assert request.status == ExecutionStatus.STOPPING
    assert "stop_mode" not in request.model_fields_set
    orchestrator._stop_run.assert_called_once_with(run=run, graceful=graceful)


def test_persisted_immediate_mode_cannot_be_downgraded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Backend cleanup follows the server's strongest persisted stop request."""
    run = SimpleNamespace(
        id=uuid4(),
        status=ExecutionStatus.FAILED,
        orchestrator_run_id=None,
        stop_mode=PipelineRunStopMode.IMMEDIATE,
        get_body=lambda: SimpleNamespace(model_fields_set={"stop_mode"}),
    )
    update = Mock(return_value=run)
    client = SimpleNamespace(zen_store=SimpleNamespace(update_run=update))
    monkeypatch.setattr(run_utils, "Client", lambda: client)
    orchestrator = Mock()

    BaseOrchestrator.stop_run(orchestrator, run, graceful=True)

    request = update.call_args.kwargs["run_update"]
    assert request.stop_mode == PipelineRunStopMode.GRACEFUL
    orchestrator._stop_run.assert_called_once_with(run=run, graceful=False)


@pytest.mark.parametrize(
    "status,backend_id",
    [(ExecutionStatus.FAILED, "job"), (ExecutionStatus.RUNNING, None)],
)
def test_old_server_rejects_new_cleanup_contract(
    monkeypatch: pytest.MonkeyPatch,
    status: ExecutionStatus,
    backend_id: str | None,
) -> None:
    """Old servers cannot silently accept cleanup they cannot represent."""
    run = SimpleNamespace(
        id=uuid4(),
        status=status,
        orchestrator_run_id=backend_id,
        get_body=lambda: SimpleNamespace(model_fields_set=set()),
    )
    client = Mock()
    monkeypatch.setattr(run_utils, "Client", lambda: client)

    with pytest.raises(IllegalOperationError, match="upgraded"):
        run_utils.request_run_stop(run, graceful=True)

    client.zen_store.update_run.assert_not_called()
