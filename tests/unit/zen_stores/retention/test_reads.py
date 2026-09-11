# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Archived headers remain usable; detail requires an explicit restore."""

from unittest.mock import Mock

import pytest

from tests.unit.zen_stores.retention.fixture_graph import dynamic_step
from zenml.exceptions import (
    ExecutionArchivedError,
    ExecutionRetentionUnavailableError,
)
from zenml.models import (
    PipelineRunFilter,
    PipelineSnapshotFilter,
    StepRunFilter,
)
from zenml.zen_server.exceptions import http_exception_from_error


def test_reads_need_no_archive_storage(
    retention_store, run_factory, archive_run, storage, monkeypatch, NOW
):
    """Headers work and detail fails with 409 even when storage is unavailable."""
    ids = run_factory(retention_store)
    archive_run(retention_store, ids)
    opened = Mock(side_effect=OSError("storage unavailable"))
    monkeypatch.setattr(storage.artifact_store, "open", opened)
    calls = [
        lambda hydrate: retention_store.get_run(ids.run, hydrate=hydrate),
        lambda hydrate: retention_store.get_run_step(
            ids.consumer, hydrate=hydrate
        ),
        lambda hydrate: retention_store.get_snapshot(
            ids.snapshot, hydrate=hydrate
        ),
        lambda hydrate: retention_store.list_runs(
            PipelineRunFilter(project=ids.project), hydrate=hydrate
        ),
        lambda hydrate: retention_store.list_run_steps(
            StepRunFilter(project=ids.project), hydrate=hydrate
        ),
        lambda hydrate: retention_store.list_snapshots(
            PipelineSnapshotFilter(project=ids.project), hydrate=hydrate
        ),
    ]
    for call in calls:
        assert call(False)
        with pytest.raises(ExecutionArchivedError) as error:
            call(True)
        assert "restore" in str(error.value)
        assert http_exception_from_error(error.value).status_code == 409
    opened.assert_not_called()

    with pytest.raises(ExecutionRetentionUnavailableError) as error:
        retention_store.restore_pipeline_run(ids.run)
    exception = http_exception_from_error(error.value)
    assert exception.status_code == 503
    assert exception.headers["Retry-After"]
    assert retention_store.get_run(ids.run, hydrate=False).archive_bundle_id
    with pytest.raises(ExecutionArchivedError, match="pipeline runs restore"):
        retention_store.create_run_step(dynamic_step(ids, "late", NOW))
