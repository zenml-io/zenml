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
from zenml.client import Client
from zenml.enums import MetadataResourceTypes
from zenml.exceptions import (
    ExecutionArchivedError,
    ExecutionRetentionUnavailableError,
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
    run.get_body().summary.run_metadata = None
    step.get_body().summary.run_metadata = None
    step.get_body().summary.parent_step_ids = None
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
        retention.restore_pipeline_run(retention_store.get_run_header(ids.run))
    exception = http_exception_from_error(error.value)
    assert exception.status_code == 503
    assert exception.headers["Retry-After"]
    with pytest.raises(
        ExecutionArchivedError, match="pipeline runs unarchive"
    ):
        retention_store.create_run_step(dynamic_step(ids, "late", NOW))


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


@pytest.mark.parametrize("isolation", ["REPEATABLE READ", "READ COMMITTED"])
def test_cache_lookup_when_archiving_between_selection_and_hydration(
    retention_store, run_factory, archive_run, monkeypatch, isolation
):
    """An archive race returns either a usable snapshot or a cache miss."""
    from sqlalchemy import event

    from zenml.orchestrators.cache_utils import get_cached_step_run

    ids = run_factory(retention_store)
    monkeypatch.setattr(
        Client, "zen_store", property(lambda _: retention_store)
    )
    monkeypatch.setattr(
        Client,
        "active_project",
        property(lambda _: retention_store.get_project(ids.project)),
    )
    expected = retention_store.get_run_step(ids.producer).get_metadata()
    previous_options = retention_store.engine.get_execution_options()
    retention_store.engine.update_execution_options(isolation_level=isolation)
    selected = False

    def archive_after_selection(
        connection, cursor, statement, parameters, context, many
    ):
        nonlocal selected
        if (
            not selected
            and statement.lstrip().startswith("SELECT")
            and "step_run.cache_key =" in statement
            and "count(" not in statement.lower()
        ):
            selected = True
            archive_run(retention_store, ids)

    event.listen(
        retention_store.engine, "after_cursor_execute", archive_after_selection
    )
    try:
        candidate = get_cached_step_run(str(ids.producer))
    finally:
        event.remove(
            retention_store.engine,
            "after_cursor_execute",
            archive_after_selection,
        )
        retention_store.engine.update_execution_options(
            isolation_level=previous_options.get(
                "isolation_level", "REPEATABLE READ"
            )
        )
    assert selected
    if candidate is not None:
        assert candidate.archive is None
        assert candidate.metadata is not None
        assert candidate.cache_expires_at is None
        assert candidate.source_code is not None
        assert candidate.docstring == expected.docstring
        assert candidate.source_code == expected.source_code
    if isolation == "READ COMMITTED":
        assert candidate is None


@pytest.mark.parametrize("identifier_kind", ["uuid", "name", "prefix"])
def test_run_detail_lookup_enforces_hydration_after_resolution(
    retention_store, run_factory, archive_run, monkeypatch, identifier_kind
):
    """Every identifier preserves ordinary detail and rejects archived detail."""
    ids = run_factory(retention_store)
    with Session(retention_store.engine) as session:
        session.get(PipelineRunSchema, ids.run).name = "lookup-example"
        session.commit()
    expected = retention_store.get_run(ids.run)
    identifier = {
        "uuid": ids.run,
        "name": expected.name,
        "prefix": str(ids.run)[:8],
    }[identifier_kind]
    monkeypatch.setattr(
        Client, "zen_store", property(lambda _: retention_store)
    )
    client = object.__new__(Client)
    assert (
        client.get_pipeline_run(identifier, project=ids.project).metadata
        == expected.metadata
    )
    archive_run(retention_store, ids)
    assert (
        client.get_pipeline_run(
            identifier, project=ids.project, hydrate=False
        ).id
        == ids.run
    )
    with pytest.raises(ExecutionArchivedError):
        client.get_pipeline_run(identifier, project=ids.project, hydrate=True)
