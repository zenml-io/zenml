# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Relative retention costs and measured hot-read SQL canaries.

The exact canaries were measured against develop ``10a0a3033e`` (through
resource pools v2) on 2026-09-11 using its store bodies with current schemas
and dependencies. MySQL starts transactions implicitly, so no ``BEGIN`` is
counted. Other assertions compare paths within this build so unrelated query
changes do not inflate fixed ceilings.
"""

import re
from collections import Counter
from contextlib import contextmanager
from functools import partial
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import event

from zenml.enums import MetadataResourceTypes
from zenml.exceptions import (
    ExecutionArchivedError,
    ExecutionRetentionUnavailableError,
)
from zenml.metadata.metadata_types import MetadataTypeEnum
from zenml.models import (
    PipelineRunFilter,
    PipelineSnapshotFilter,
    RunMetadataRequest,
    RunMetadataResource,
    StepRunFilter,
)
from zenml.zen_server.exceptions import http_exception_from_error
from zenml.zen_stores.retention import fences

ATOMIC_BASE_CANARIES = {
    "get_run": {"SELECT": 7},
    "list_run_steps": {"SELECT": 12},
}


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
        "step": partial(store.get_run_step, ids.producer, hydrate=False),
        "snapshot": partial(store.get_snapshot, ids.snapshot, hydrate=False),
        "step_list": partial(
            store.list_run_steps,
            StepRunFilter(project=ids.project, pipeline_run_id=ids.run),
            hydrate=False,
        ),
    }[operation]()


@pytest.mark.parametrize("operation", ATOMIC_BASE_CANARIES)
def test_hot_read_statement_canary(retention_store, tree_factory, operation):
    """Keep two exact prerequisite comparisons as query-plan canaries."""
    ids = tree_factory(retention_store)
    reads = {
        "get_run": partial(retention_store.get_run, ids.run),
        "list_run_steps": partial(
            retention_store.list_run_steps,
            StepRunFilter(project=ids.project),
            hydrate=True,
        ),
    }
    reads[operation]()
    with count_statements(retention_store) as statements:
        reads[operation]()
    assert dict(statements) == ATOMIC_BASE_CANARIES[operation]


@pytest.mark.parametrize("operation", ("run", "step", "snapshot", "step_list"))
def test_archive_marker_adds_no_header_read_statements(
    retention_store, tree_factory, archive_one_tree, operation
):
    """A marker adds no SQL work to an identity-only read."""
    cold = tree_factory(retention_store)
    archive_one_tree(retention_store, cold)
    # Archival is project-wide, so the comparison tree must exist only after it.
    hot = tree_factory(retention_store)
    assert retention_store.get_run(cold.run, hydrate=False).archive_bundle_id
    assert retention_store.get_snapshot(
        cold.snapshot, hydrate=False
    ).archive_bundle_id
    assert (
        retention_store.get_run(hot.run, hydrate=False).archive_bundle_id
        is None
    )
    assert (
        retention_store.get_snapshot(
            hot.snapshot, hydrate=False
        ).archive_bundle_id
        is None
    )
    with count_statements(retention_store) as hot_statements:
        header_read(retention_store, hot, operation)
    with count_statements(retention_store) as cold_statements:
        header_read(retention_store, cold, operation)
    assert cold_statements == hot_statements


def test_execution_insert_fence_adds_locking_statements(
    retention_store, tree_factory, monkeypatch
):
    """The insert guard adds exactly two locking reads."""
    ids = tree_factory(retention_store)

    def insert_metadata():
        key = uuid4().hex
        retention_store.create_run_metadata(
            RunMetadataRequest(
                project=ids.project,
                resources=[
                    RunMetadataResource(
                        id=ids.run,
                        type=MetadataResourceTypes.PIPELINE_RUN,
                    )
                ],
                values={key: "kept"},
                types={key: MetadataTypeEnum.STRING},
            )
        )

    insert_metadata()
    with count_statements(retention_store) as protected:
        insert_metadata()
    monkeypatch.setattr(
        fences, "protect_inserts", lambda *args, **kwargs: None
    )
    with count_statements(retention_store) as unprotected:
        insert_metadata()
    assert protected == unprotected + Counter({"SELECT": 2})


def test_header_lists_survive_unavailable_storage(
    retention_store, tree_factory, archive_one_tree, storage, monkeypatch
):
    """Identity lists stay available while hydrated reads map outage to 503."""
    ids = tree_factory(retention_store)
    archive_one_tree(retention_store, ids)
    opened = Mock(side_effect=OSError("storage unavailable"))
    monkeypatch.setattr(storage, "open", opened)
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
    assert http_exception_from_error(error.value).status_code == 503


@pytest.mark.parametrize("kind", ["runs", "steps"])
def test_hydrated_lists_require_one_bundle(
    retention_store, tree_factory, archive_one_tree, storage, monkeypatch, kind
):
    """Hydrate one bundle and reject mixed bundles before object access."""
    trees = [tree_factory(retention_store), tree_factory(retention_store)]
    for tree in trees:
        archive_one_tree(retention_store, tree)
    if kind == "runs":
        read = retention_store.list_runs
        one = PipelineRunFilter(snapshot_id=trees[0].snapshot)
        mixed = PipelineRunFilter(project=trees[0].project, size=2)
    else:
        read = retention_store.list_run_steps
        one = StepRunFilter(pipeline_run_id=trees[0].run)
        mixed = StepRunFilter(project=trees[0].project, size=4)
    assert read(one, hydrate=True).items
    monkeypatch.setattr(
        storage,
        "open",
        Mock(side_effect=AssertionError("mixed list downloaded an object")),
    )
    with pytest.raises(
        ExecutionArchivedError,
        match=re.escape(
            "list without details (`hydrate=False`) or narrow the filter"
        ),
    ):
        read(mixed, hydrate=True)
    assert read(mixed, hydrate=False).items
