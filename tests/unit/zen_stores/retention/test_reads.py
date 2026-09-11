# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Read costs, outage behavior, and per-request limits of archived reads.

Statement counts are compared between paths inside this build, so unrelated
query changes never inflate a fixed ceiling a later change has to chase.
"""

import gc
import weakref
from collections import Counter
from contextlib import contextmanager
from functools import partial
from unittest.mock import Mock

import pytest
from sqlalchemy import event

from zenml.enums import ExecutionStatus, RetentionOutcome
from zenml.exceptions import (
    ExecutionArchivedError,
    ExecutionRetentionUnavailableError,
)
from zenml.models import (
    PipelineRunFilter,
    PipelineSnapshotFilter,
    StepRunFilter,
    StepRunRequest,
)
from zenml.zen_server.exceptions import http_exception_from_error
from zenml.zen_stores.retention import reader


@contextmanager
def count_statements(store):
    """Count SQL statement kinds inside one operation."""
    statements = Counter()

    def observe(conn, cursor, statement, parameters, context, executemany):
        statements[statement.split()[0].upper()] += 1

    event.listen(store.engine, "before_cursor_execute", observe)
    try:
        yield statements
    finally:
        event.remove(store.engine, "before_cursor_execute", observe)


def header_read(store, ids, operation):
    """Read one execution identity without archived detail."""
    return {
        "run": partial(store.get_run, ids.run, hydrate=False),
        "step_list": partial(
            store.list_run_steps,
            StepRunFilter(project=ids.project, pipeline_run_id=ids.run),
            hydrate=False,
        ),
    }[operation]()


@pytest.mark.parametrize("operation", ("run", "step_list"))
def test_archive_marker_adds_no_header_read_statements(
    retention_store, run_factory, archive_run, operation
):
    """A marker adds no SQL work to an identity-only read."""
    cold = run_factory(retention_store)
    archive_run(retention_store, cold)
    # A pass archives every eligible run, so the hot run must come after it.
    hot = run_factory(retention_store)
    assert (
        retention_store.get_run(hot.run, hydrate=False).archive_bundle_id
        is None
    )
    with count_statements(retention_store) as hot_statements:
        header_read(retention_store, hot, operation)
    with count_statements(retention_store) as cold_statements:
        header_read(retention_store, cold, operation)
    assert cold_statements == hot_statements


def test_header_lists_survive_unavailable_storage(
    retention_store, run_factory, archive_run, storage, monkeypatch
):
    """Lists without detail stay available while detailed reads return 503."""
    ids = run_factory(retention_store)
    archive_run(retention_store, ids)
    opened = Mock(side_effect=OSError("storage unavailable"))
    monkeypatch.setattr(storage.artifact_store, "open", opened)
    for method, filters in (
        (retention_store.list_runs, PipelineRunFilter(project=ids.project)),
        (retention_store.list_run_steps, StepRunFilter(project=ids.project)),
        (
            retention_store.list_snapshots,
            PipelineSnapshotFilter(project=ids.project),
        ),
    ):
        assert method(filters, hydrate=False).items
    opened.assert_not_called()
    with pytest.raises(ExecutionRetentionUnavailableError) as error:
        retention_store.get_run(ids.run)
    exception = http_exception_from_error(error.value)
    assert exception.status_code == 503
    assert exception.headers["Retry-After"]


def archive_runs(store, run_factory, count):
    """Archive several runs, each into its own bundle."""
    runs = [run_factory(store, age_days=100 + index) for index in range(count)]
    outcome = store.archive_project(runs[0].project)
    assert outcome.outcome == RetentionOutcome.SUCCEEDED
    return runs


@pytest.mark.parametrize(
    "read",
    [
        lambda store, ids: store.list_runs(
            PipelineRunFilter(project=ids.project), hydrate=True
        ),
        lambda store, ids: store.list_snapshots(
            PipelineSnapshotFilter(project=ids.project), hydrate=True
        ),
    ],
    ids=["runs", "snapshots"],
)
def test_detailed_lists_load_several_bundles_up_to_the_cap(
    retention_store, run_factory, storage, monkeypatch, read
):
    """A page may span bundles until it needs more than one request loads."""
    runs = archive_runs(retention_store, run_factory, 3)
    page = read(retention_store, runs[0])
    assert len({item.body.archive_bundle_id for item in page.items}) == 3
    assert all(item.metadata is not None for item in page.items)

    monkeypatch.setattr(reader, "MAX_BUNDLES_PER_READ", 2)
    downloads = Mock(side_effect=AssertionError("over-cap read downloaded"))
    monkeypatch.setattr(storage, "read", downloads)
    with pytest.raises(ExecutionArchivedError, match="hydrate=False"):
        read(retention_store, runs[0])
    downloads.assert_not_called()


def test_detailed_lists_respect_the_compressed_byte_cap(
    retention_store, run_factory, storage, monkeypatch
):
    """The total size of a page's objects is capped before any download."""
    runs = archive_runs(retention_store, run_factory, 2)
    monkeypatch.setattr(reader, "MAX_COMPRESSED_BYTES_PER_READ", 1)
    with pytest.raises(ExecutionArchivedError, match="smaller page"):
        retention_store.list_runs(
            PipelineRunFilter(project=runs[0].project), hydrate=True
        )


def test_one_decoded_bundle_is_alive_at_a_time(
    retention_store, run_factory, storage, monkeypatch
):
    """A page is converted bundle by bundle, releasing each before the next."""
    runs = archive_runs(retention_store, run_factory, 3)
    alive = weakref.WeakSet()
    most_alive = 0
    original = reader.index_document

    def tracked(document):
        nonlocal most_alive
        gc.collect()
        most_alive = max(most_alive, len(alive) + 1)
        detail = original(document)
        alive.add(detail)
        return detail

    monkeypatch.setattr(reader, "index_document", tracked)
    page = retention_store.list_run_steps(
        StepRunFilter(project=runs[0].project), hydrate=True
    )
    assert len({item.body.archive_bundle_id for item in page.items}) == 3
    assert most_alive == 1


def test_step_insert_into_an_archived_run_fails(
    retention_store, run_factory, archive_run, NOW
):
    """Adding a step to an archived run needs a restore first."""
    ids = run_factory(retention_store, "dynamic")
    archive_run(retention_store, ids)
    with pytest.raises(ExecutionArchivedError, match="pipeline runs restore"):
        retention_store.create_run_step(
            StepRunRequest(
                project=ids.project,
                name="late",
                pipeline_run_id=ids.run,
                status=ExecutionStatus.COMPLETED,
                start_time=NOW,
                end_time=NOW,
            )
        )
