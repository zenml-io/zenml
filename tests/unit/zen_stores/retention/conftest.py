# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Pipeline runs and archive storage for the MySQL retention suite."""

from datetime import timedelta
from typing import Any, Dict, List
from uuid import UUID

import pytest
from pydantic import BaseModel, ConfigDict

from tests.unit.zen_stores.retention.fixture_graph import (
    graph_rows,
    insert_rows,
    read_tables,
)
from zenml.enums import RetentionOutcome
from zenml.models import ProjectFilter, ProjectUpdate
from zenml.models.v2.misc.retention import RetentionSettings
from zenml.zen_stores.retention.storage import ArchiveStorage
from zenml.zen_stores.sql_zen_store import SqlZenStore


@pytest.fixture
def storage(tmp_path, monkeypatch) -> ArchiveStorage:
    """Enable archiving against a temporary local directory."""
    root = str(tmp_path / "objects")
    archive = ArchiveStorage.from_uri(root)
    monkeypatch.setenv("ZENML_SERVER_ARCHIVE_URI", root)
    monkeypatch.setattr(
        SqlZenStore, "archive_storage", property(lambda _: archive)
    )
    return archive


@pytest.fixture
def archive_run(storage):
    """Archive a project with one eligible run and return its bundle ID."""

    def archive(store: SqlZenStore, ids: "ExecutionRun") -> UUID:
        outcome = store.archive_project(ids.project)
        assert outcome.outcome == RetentionOutcome.SUCCEEDED
        bundle_id = store.get_run(ids.run, hydrate=False).archive_bundle_id
        assert bundle_id is not None
        return bundle_id

    return archive


@pytest.fixture
def rows():
    """Provide SQL snapshots for atomicity assertions."""
    return read_tables


class ExecutionRun(BaseModel):
    """Identify the shared two-step pipeline run."""

    model_config = ConfigDict(frozen=True)

    project: UUID
    run: UUID
    snapshot: UUID
    producer: UUID
    consumer: UUID


FixtureRows = Dict[str, List[Dict[str, Any]]]


def configure(source: FixtureRows, kind: str) -> None:
    """Select snapshot, step, or legacy inline configuration ownership.

    Args:
        source: Independent graph rows.
        kind: Static, dynamic, or legacy ownership.
    """
    if kind == "dynamic":
        source["pipeline_snapshot"][0]["is_dynamic"] = True
        steps = {row["name"]: row["id"] for row in source["step_run"]}
        for row in source["step_configuration"]:
            row.update(snapshot_id=None, step_run_id=steps[row["name"]])
    elif kind == "legacy":
        snapshot = source["pipeline_snapshot"][0]
        source["pipeline_run"][0].update(
            snapshot_id=None,
            pipeline_configuration=snapshot["pipeline_configuration"],
            client_environment=snapshot["client_environment"],
        )
        definitions = {
            row["name"]: row["config"] for row in source["step_configuration"]
        }
        for row in source["step_run"]:
            row.update(
                snapshot_id=None, step_configuration=definitions[row["name"]]
            )
        source["step_configuration"] = []


@pytest.fixture
def run_factory(NOW):
    """Create two-step runs with snapshot, step, or inline definitions."""

    def create(
        store: SqlZenStore, kind: str = "static", age_days: int = 100
    ) -> ExecutionRun:
        """Build the selected ownership graph and enable a 7-day policy.

        Args:
            store: Isolated metadata store.
            kind: Static, dynamic, or legacy configuration ownership.
            age_days: How long ago the run finished.

        Returns:
            Created execution identities.
        """
        project = store.list_projects(ProjectFilter()).items[0].id
        source = graph_rows(project, NOW - timedelta(days=age_days))
        configure(source, kind)
        insert_rows(store, source)
        store.update_project(
            project,
            ProjectUpdate(retention=RetentionSettings(archive_after_days=7)),
        )
        return ExecutionRun(
            project=project,
            run=source["pipeline_run"][0]["id"],
            snapshot=source["pipeline_snapshot"][0]["id"],
            producer=source["step_run"][0]["id"],
            consumer=source["step_run"][1]["id"],
        )

    return create
