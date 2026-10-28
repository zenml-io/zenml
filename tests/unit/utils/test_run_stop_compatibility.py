"""Stop requests retain their mode across old and new server responses."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from zenml.enums import (
    ExecutionStatus,
    PipelineRunStopMode,
    StackComponentType,
)
from zenml.exceptions import IllegalOperationError
from zenml.orchestrators import base_orchestrator
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.utils import run_utils


@pytest.mark.parametrize("graceful", [False, True])
@pytest.mark.parametrize(
    "status",
    [
        ExecutionStatus.RUNNING,
        ExecutionStatus.FAILED,
        ExecutionStatus.STOPPING,
        ExecutionStatus.STOPPED,
    ],
)
def test_legacy_orchestrator_keeps_status_only_stop(
    monkeypatch: pytest.MonkeyPatch,
    graceful: bool,
    status: ExecutionStatus,
) -> None:
    """Existing integrations retain their status-only stop and fallback behavior.

    Args:
        monkeypatch: Fixture for replacing external collaborators.
        graceful: Whether to request graceful stopping.
        status: Current run status before the stop request.
    """
    run = SimpleNamespace(
        id=uuid4(),
        status=status,
        orchestrator_run_id="job",
        stop_mode=None,
        stack=SimpleNamespace(
            components={StackComponentType.ORCHESTRATOR: [Mock()]}
        ),
    )
    orchestrator = Mock()
    orchestrator.supports_run_stop_modes = (
        BaseOrchestrator.supports_run_stop_modes.__get__(orchestrator)
    )
    client = Mock()
    publish = Mock()
    monkeypatch.setattr(base_orchestrator, "Client", client)
    monkeypatch.setattr(
        base_orchestrator, "publish_pipeline_run_status_update", publish
    )
    monkeypatch.setattr(
        run_utils.StackComponent, "from_model", Mock(return_value=orchestrator)
    )
    orchestrator.stop_run.side_effect = lambda **kwargs: (
        BaseOrchestrator.stop_run(orchestrator, **kwargs)
    )

    if status in {ExecutionStatus.STOPPING, ExecutionStatus.STOPPED}:
        with pytest.raises(IllegalOperationError, match="already"):
            run_utils.stop_run(run, graceful=graceful)
        orchestrator.stop_run.assert_not_called()
        return

    run_utils.stop_run(run, graceful=graceful)

    client.assert_not_called()
    publish.assert_called_once_with(
        pipeline_run_id=run.id,
        status=ExecutionStatus.STOPPING,
        status_reason="Manual stop requested.",
    )
    orchestrator._stop_run.assert_called_once_with(run=run, graceful=graceful)
    assert run.status == status
    assert run.stop_mode is None


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
        status=ExecutionStatus.STOPPING,
        orchestrator_run_id="job",
        stop_mode=None,
        stack=SimpleNamespace(
            components={StackComponentType.ORCHESTRATOR: [Mock()]}
        ),
    )
    update = Mock(return_value=run)
    client = SimpleNamespace(zen_store=SimpleNamespace(update_run=update))
    monkeypatch.setattr(base_orchestrator, "Client", lambda: client)
    orchestrator = Mock(supports_run_stop_modes=True)
    publish = Mock()
    monkeypatch.setattr(
        base_orchestrator, "publish_pipeline_run_status_update", publish
    )
    monkeypatch.setattr(
        run_utils.StackComponent, "from_model", Mock(return_value=orchestrator)
    )
    orchestrator.stop_run.side_effect = lambda **kwargs: (
        BaseOrchestrator.stop_run(orchestrator, **kwargs)
    )

    run_utils.stop_run(run, graceful=graceful)

    publish.assert_not_called()

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
    orchestrator = Mock(supports_run_stop_modes=True)
    publish = Mock()
    monkeypatch.setattr(
        base_orchestrator, "publish_pipeline_run_status_update", publish
    )

    BaseOrchestrator.stop_run(orchestrator, run, graceful=True)

    request = update.call_args.kwargs["run_update"]
    assert request.status == ExecutionStatus.STOPPING
    assert request.stop_mode == PipelineRunStopMode.GRACEFUL
    orchestrator._stop_run.assert_called_once_with(run=run, graceful=False)
    publish.assert_not_called()
