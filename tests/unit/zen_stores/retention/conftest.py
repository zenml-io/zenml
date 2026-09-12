# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Pipeline runs and archive storage for the MySQL retention suite."""

from datetime import timedelta
from uuid import UUID

import pytest
from pydantic import BaseModel, ConfigDict

from tests.unit.zen_stores.retention.fixture_graph import (
    graph_rows,
    insert_rows,
)
from zenml.enums import RetentionOutcome
from zenml.models import ProjectFilter
from zenml.zen_stores.retention.storage import ArchiveStorage
from zenml.zen_stores.sql_zen_store import SqlZenStore


@pytest.fixture
def storage(tmp_path, monkeypatch) -> ArchiveStorage:
    """Enable archiving against a temporary local directory."""
    root = str(tmp_path / "objects")
    archive = ArchiveStorage.from_uri(root)
    monkeypatch.setenv("ZENML_SERVER_ARCHIVE__BACKEND", "local")
    monkeypatch.setenv("ZENML_SERVER_ARCHIVE__URI", root)
    monkeypatch.setenv("ZENML_SERVER_ARCHIVE__AFTER_DAYS", "7")
    monkeypatch.setattr(
        SqlZenStore, "archive_storage", property(lambda _: archive)
    )
    return archive


@pytest.fixture
def archive_run(storage):
    """Sweep one eligible run out of SQL and return its bundle ID."""

    def archive(store: SqlZenStore, ids: "ExecutionRun") -> UUID:
        assert store.run_archive_sweep() == RetentionOutcome.SUCCEEDED
        bundle_id = store.get_run(ids.run, hydrate=False).archive_bundle_id
        assert bundle_id is not None
        return bundle_id

    return archive


class ExecutionRun(BaseModel):
    """Identify the shared two-step pipeline run."""

    model_config = ConfigDict(frozen=True)

    project: UUID
    pipeline: UUID
    run: UUID
    snapshot: UUID
    producer: UUID
    consumer: UUID


@pytest.fixture
def run_factory(NOW):
    """Create two-step runs with snapshot, step, or inline definitions."""

    def create(
        store: SqlZenStore,
        kind: str = "static",
        age_days: int = 100,
        parent: UUID | None = None,
    ) -> ExecutionRun:
        project = store.list_projects(ProjectFilter()).items[0].id
        source = graph_rows(project, NOW - timedelta(days=age_days), kind)
        source["pipeline_run"][0].update(
            parent_run_id=parent, root_run_id=parent
        )
        insert_rows(store, source)
        return ExecutionRun(
            project=project,
            pipeline=source["pipeline"][0]["id"],
            run=source["pipeline_run"][0]["id"],
            snapshot=source["pipeline_snapshot"][0]["id"],
            producer=source["step_run"][0]["id"],
            consumer=source["step_run"][1]["id"],
        )

    return create
