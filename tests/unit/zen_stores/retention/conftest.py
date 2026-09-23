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
from zenml.models import ArchiveRequest, ArchiveResponse, ProjectFilter
from zenml.zen_server import retention as server_retention
from zenml.zen_server import utils as server_utils
from zenml.zen_server.archive_storage import ArtifactStoreArchiveStorage
from zenml.zen_server.retention import (
    MAX_CONCURRENT_RETENTION_OPERATIONS,
    RetentionCapacity,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


@pytest.fixture
def storage(tmp_path, monkeypatch) -> ArtifactStoreArchiveStorage:
    """Enable archiving against a temporary local directory."""
    root = str(tmp_path / "objects")
    archive = ArtifactStoreArchiveStorage.from_uri(root)
    monkeypatch.setenv("ZENML_SERVER_ARCHIVE__BACKEND", "local")
    monkeypatch.setenv("ZENML_SERVER_ARCHIVE__URI", root)
    monkeypatch.setenv("ZENML_SERVER_ARCHIVE__AFTER_DAYS", "7")
    return archive


@pytest.fixture
def retention(retention_store, storage, monkeypatch):
    """Drive retention the way a server replica does."""
    monkeypatch.setattr(server_utils, "_zen_store", retention_store)
    monkeypatch.setattr(server_utils, "_archive_storage", storage)
    monkeypatch.setattr(
        server_utils,
        "_retention_capacity",
        RetentionCapacity(MAX_CONCURRENT_RETENTION_OPERATIONS),
    )
    return server_retention


@pytest.fixture
def archive_request(retention_store, retention):
    """Archive or preview a request whose runs need no authorization."""

    def archive(request: ArchiveRequest) -> ArchiveResponse:
        batch = retention_store.select_runs_to_archive(request)
        return retention.archive_batch(request, batch)

    return archive


@pytest.fixture
def archive_run(archive_request):
    """Archive one eligible run and return its bundle ID."""

    def archive(store: SqlZenStore, ids: "ExecutionRun") -> UUID:
        assert archive_request(ArchiveRequest(run_ids=[ids.run])).archived == 1
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


@pytest.fixture
def archive_project(retention_store, archive_request):
    """Archive one batch from the test project through the manual path."""

    def archive():
        project = retention_store.list_projects(ProjectFilter()).items[0].id
        return archive_request(ArchiveRequest(project_id=project))

    return archive
