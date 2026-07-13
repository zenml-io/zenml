"""Tests for snapshot run dispatcher component selection."""

import asyncio
from unittest.mock import MagicMock

import pytest

from zenml.zen_server import utils
from zenml.zen_server.pipeline_execution.snapshot_run_dispatcher import (
    LocalSnapshotRunDispatcher,
    SnapshotRunDispatcher,
    SnapshotRunExecutionRequest,
)


class _RecordingDispatcher(SnapshotRunDispatcher):
    """Dispatcher used to verify dynamic component loading."""

    started = False

    async def start(self) -> None:
        """Record dispatcher startup."""
        self.started = True

    def submit(self, request: SnapshotRunExecutionRequest) -> None:
        """Accept a test request.

        Args:
            request: The test execution request.
        """


@pytest.fixture(autouse=True)
def reset_snapshot_run_dispatcher() -> None:
    """Reset the process-global dispatcher between tests."""
    utils._snapshot_run_dispatcher = None
    yield
    utils._snapshot_run_dispatcher = None


def test_dispatcher_initialization_selection_and_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dispatcher initialization selects local, configured, or fatal paths."""
    config = MagicMock(snapshot_run_dispatcher_implementation_source=None)
    monkeypatch.setattr(utils, "server_config", lambda: config)

    asyncio.run(utils.initialize_snapshot_run_dispatcher())
    assert isinstance(
        utils.snapshot_run_dispatcher(), LocalSnapshotRunDispatcher
    )

    utils._snapshot_run_dispatcher = None
    config.snapshot_run_dispatcher_implementation_source = "test.Dispatcher"
    load_class = MagicMock(return_value=_RecordingDispatcher)
    monkeypatch.setattr(
        "zenml.utils.source_utils.load_and_validate_class",
        load_class,
    )
    asyncio.run(utils.initialize_snapshot_run_dispatcher())
    dispatcher = utils.snapshot_run_dispatcher()
    assert isinstance(dispatcher, _RecordingDispatcher)
    assert dispatcher.started is True
    load_class.assert_called_once()

    utils._snapshot_run_dispatcher = None
    config.snapshot_run_dispatcher_implementation_source = "missing.Dispatcher"
    load_class.side_effect = ImportError("missing")
    with pytest.raises(
        RuntimeError, match="Could not initialize snapshot run dispatcher"
    ):
        asyncio.run(utils.initialize_snapshot_run_dispatcher())
    with pytest.raises(RuntimeError, match="not initialized"):
        utils.snapshot_run_dispatcher()
