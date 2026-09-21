# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Archived execution summaries remain readable without archive storage."""

import json
from functools import partial
from typing import Any
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import update
from sqlmodel import Session

from tests.unit.zen_stores.retention.fixture_graph import dynamic_step
from zenml.client import Client
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
    PipelineSnapshotSchema,
    RunMetadataResourceSchema,
    RunMetadataSchema,
    ScheduleSchema,
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


def _attach_schedule(store: Any, ids: Any) -> UUID:
    """Attach a retained schedule to the fixture snapshot."""
    schedule = ScheduleSchema(
        name=str(uuid4()),
        project_id=ids.project,
        user_id=None,
        pipeline_id=ids.pipeline,
        orchestrator_id=None,
        active=False,
        cron_expression=None,
        start_time=None,
        end_time=None,
        interval_second=None,
        catchup=False,
        run_once_start_time=None,
    )
    with Session(store.engine) as session:
        session.add(schedule)
        session.flush()
        schedule_id = schedule.id
        snapshot = session.get(PipelineSnapshotSchema, ids.snapshot)
        assert snapshot is not None
        snapshot.schedule_id = schedule_id
        session.add(snapshot)
        session.commit()
    return schedule_id


def test_archived_summaries_need_no_archive_storage(
    retention_store: Any,
    run_factory: Any,
    archive_run: Any,
    storage: Any,
    monkeypatch: pytest.MonkeyPatch,
    NOW: Any,
    retention,
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

    # A list page leaves these out; reading them fetches the summary once
    # instead of hydrating detail that is no longer in the database.
    monkeypatch.setattr(
        Client, "zen_store", property(lambda _: retention_store)
    )
    run.archive.run_metadata = None
    step.archive.run_metadata = None
    step.archive.parent_step_ids = None
    assert run.run_metadata == {"run-summary": "retained"}
    assert step.run_metadata == {"step-summary": "retained"}
    assert step.parent_step_ids == [ids.producer]
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
        retention.restore_pipeline_run(ids.run)
    exception = http_exception_from_error(error.value)
    assert exception.status_code == 503
    assert exception.headers["Retry-After"]
    with pytest.raises(ExecutionArchivedError, match="pipeline runs restore"):
        retention_store.create_run_step(dynamic_step(ids, "late", NOW))


@pytest.mark.parametrize(
    "read_path", ["single", "hydrated_list", "unhydrated_list"]
)
@pytest.mark.parametrize("include_full_metadata", [False, True])
def test_archived_run_summaries_preserve_full_metadata_option(
    retention_store: Any,
    run_factory: Any,
    archive_run: Any,
    storage: Any,
    monkeypatch: pytest.MonkeyPatch,
    read_path: str,
    include_full_metadata: bool,
) -> None:
    """Every archived summary path applies the same metadata projection."""
    ids = run_factory(retention_store)
    schedule_id = _attach_schedule(retention_store, ids)
    _add_metadata(
        retention_store,
        ids.project,
        ids.run,
        MetadataResourceTypes.PIPELINE_RUN,
        "run-summary",
        "run",
    )
    _add_metadata(
        retention_store,
        ids.project,
        ids.consumer,
        MetadataResourceTypes.STEP_RUN,
        "step-summary",
        "step",
    )
    _add_metadata(
        retention_store,
        ids.project,
        schedule_id,
        MetadataResourceTypes.SCHEDULE,
        "schedule-summary",
        "schedule",
    )
    archive_run(retention_store, ids)
    opened = Mock(side_effect=AssertionError("summary read archive storage"))
    monkeypatch.setattr(storage.artifact_store, "open", opened)

    if read_path == "single":
        run = retention_store.get_run(
            ids.run,
            hydrate=False,
            include_full_metadata=include_full_metadata,
        )
    else:
        page = retention_store.list_runs(
            PipelineRunFilter(project=ids.project),
            hydrate=read_path == "hydrated_list",
            include_full_metadata=include_full_metadata,
        )
        run = page.items[0]

    expected = {"run-summary": "run"}
    if include_full_metadata:
        expected.update(
            {
                "consumer::step-summary": "step",
                "schedule:schedule-summary": "schedule",
            }
        )
    assert run.run_metadata == expected
    opened.assert_not_called()


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


@pytest.mark.parametrize("kind", ["static", "dynamic", "legacy"])
def test_run_dag_links_the_producer_to_its_consumer(
    retention_store, run_factory, kind
):
    """Each way of storing step definitions yields the same two-step graph.

    The fixture loads the consumer's row before the producer's, and a legacy
    run has no snapshot to read the graph from.
    """
    ids = run_factory(retention_store, kind)

    dag = retention_store.get_pipeline_run_dag(ids.run)

    steps = {node.name: node for node in dag.nodes if node.type == "step"}
    assert set(steps) == {"producer", "consumer"}
    assert steps["producer"].id == ids.producer
    reachable = {steps["producer"].node_id}
    for _ in dag.edges:
        reachable |= {
            edge.target for edge in dag.edges if edge.source in reachable
        }
    assert steps["consumer"].node_id in reachable
