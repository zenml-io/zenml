# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Archived execution summaries remain readable without archive storage."""

import json
from functools import partial
from typing import Any
from unittest.mock import Mock
from uuid import UUID

import pytest
from sqlalchemy import update
from sqlmodel import Session

from tests.unit.zen_stores.retention.fixture_graph import dynamic_step
from zenml.enums import MetadataResourceTypes
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
from zenml.zen_stores.schemas import (
    PipelineRunSchema,
    RunMetadataResourceSchema,
    RunMetadataSchema,
)


def _add_metadata(
    store: Any,
    project_id: UUID,
    resource_id: UUID,
    resource_type: MetadataResourceTypes,
    key: str,
    value: Any,
) -> None:
    """Attach one scalar metadata value to a run or step fixture."""
    metadata = RunMetadataSchema(
        project_id=project_id,
        key=key,
        value=json.dumps(value),
        type="str",
    )
    with Session(store.engine) as session:
        session.add(metadata)
        session.flush()
        session.add(
            RunMetadataResourceSchema(
                resource_id=resource_id,
                resource_type=resource_type.value,
                run_metadata_id=metadata.id,
            )
        )
        session.commit()


def test_archived_summaries_need_no_archive_storage(
    retention_store: Any,
    run_factory: Any,
    archive_run: Any,
    storage: Any,
    monkeypatch: pytest.MonkeyPatch,
    NOW: Any,
) -> None:
    """Retained fields stay readable and cold detail keeps requiring restore."""
    ids = run_factory(retention_store)
    _add_metadata(
        retention_store,
        ids.project,
        ids.run,
        MetadataResourceTypes.PIPELINE_RUN,
        "run-summary",
        "retained",
    )
    _add_metadata(
        retention_store,
        ids.project,
        ids.consumer,
        MetadataResourceTypes.STEP_RUN,
        "step-summary",
        "retained",
    )
    archive_run(retention_store, ids)
    opened = Mock(side_effect=OSError("storage unavailable"))
    monkeypatch.setattr(storage.artifact_store, "open", opened)

    run = retention_store.get_run(ids.run, hydrate=False)
    step = retention_store.get_run_step(ids.consumer, hydrate=False)
    snapshot = retention_store.get_snapshot(ids.snapshot, hydrate=False)
    blocked = Mock(side_effect=AssertionError("summary triggered hydration"))
    monkeypatch.setattr(type(run), "get_hydrated_version", blocked)
    monkeypatch.setattr(type(step), "get_hydrated_version", blocked)
    monkeypatch.setattr(type(snapshot), "get_hydrated_version", blocked)

    assert run.archive and run.archive.restore_run_id == ids.run
    assert run.start_time is not None and run.end_time == run.start_time
    assert run.run_metadata == {"run-summary": "retained"}
    assert step.archive and step.archive.restore_run_id == ids.run
    assert step.pipeline_run_id == ids.run
    assert step.snapshot_id == ids.snapshot
    assert step.parent_step_ids == [ids.producer]
    assert step.run_metadata == {"step-summary": "retained"}
    assert snapshot.archive and snapshot.archive.restore_run_id == ids.run
    assert snapshot.run_name_template == "example"
    blocked.assert_not_called()
    opened.assert_not_called()

    run.archive.run_metadata = None
    step.archive.run_metadata = None
    step.archive.parent_step_ids = None
    with pytest.raises(RuntimeError, match="archived summary"):
        _ = run.run_metadata
    with pytest.raises(RuntimeError, match="archived summary"):
        _ = step.run_metadata
    with pytest.raises(RuntimeError, match="archived summary"):
        _ = step.parent_step_ids
    blocked.assert_not_called()

    detail_calls = [
        partial(retention_store.get_run, ids.run),
        partial(retention_store.get_run_step, ids.consumer),
        partial(retention_store.get_snapshot, ids.snapshot),
    ]
    for call in detail_calls:
        with pytest.raises(ExecutionArchivedError) as error:
            call(True)
        assert str(ids.run) in str(error.value)
        assert http_exception_from_error(error.value).status_code == 409
    opened.assert_not_called()

    with pytest.raises(ExecutionRetentionUnavailableError) as error:
        retention_store.restore_pipeline_run(ids.run)
    exception = http_exception_from_error(error.value)
    assert exception.status_code == 503
    assert exception.headers["Retry-After"]
    with pytest.raises(ExecutionArchivedError, match="pipeline runs restore"):
        retention_store.create_run_step(dynamic_step(ids, "late", NOW))


def test_mixed_hydrated_pages_keep_hot_detail_and_cold_summaries(
    retention_store: Any,
    run_factory: Any,
    archive_run: Any,
    storage: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One archived item does not fail a hydrated history page."""
    cold = run_factory(retention_store, age_days=100)
    hot = run_factory(retention_store, age_days=1)
    archive_run(retention_store, cold)
    opened = Mock(side_effect=OSError("storage unavailable"))
    monkeypatch.setattr(storage.artifact_store, "open", opened)

    pages = [
        retention_store.list_runs(
            PipelineRunFilter(project=cold.project), hydrate=True
        ),
        retention_store.list_run_steps(
            StepRunFilter(project=cold.project), hydrate=True
        ),
        retention_store.list_snapshots(
            PipelineSnapshotFilter(project=cold.project), hydrate=True
        ),
    ]
    for page in pages:
        archived = [item for item in page.items if item.archive is not None]
        live = [item for item in page.items if item.archive is None]
        assert archived and all(item.metadata is None for item in archived)
        assert live and all(item.metadata is not None for item in live)
    assert any(run.id == hot.run for run in pages[0].items)
    opened.assert_not_called()


def test_snapshot_restore_owner_is_resolved_from_archive_catalog(
    retention_store: Any, run_factory: Any, archive_run: Any
) -> None:
    """A step-only snapshot reference still points to its owning restore run."""
    ids = run_factory(retention_store)
    with retention_store.engine.begin() as connection:
        connection.execute(
            update(PipelineRunSchema)
            .where(PipelineRunSchema.id == ids.run)
            .values(
                snapshot_id=None,
                pipeline_configuration='{"name":"example"}',
            )
        )
    archive_run(retention_store, ids)

    snapshot = retention_store.get_snapshot(ids.snapshot, hydrate=False)

    assert snapshot.archive is not None
    assert snapshot.archive.restore_run_id == ids.run
