# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Small SQL trees and public archive operations shared by both database tiers."""

import os
from datetime import timedelta
from typing import Any, Dict, List
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ConfigDict

from tests.unit.zen_stores.retention.fixture_graph import (
    graph_rows,
    insert_rows,
    read_tables,
)
from zenml.artifact_stores.local_artifact_store import (
    LocalArtifactStore,
    LocalArtifactStoreConfig,
)
from zenml.enums import RetentionOutcome, StackComponentType
from zenml.models import ProjectFilter, ProjectUpdate
from zenml.models.v2.misc.retention import RetentionSettings
from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
    SqlZenStoreConfiguration,
)


@pytest.fixture
def storage(tmp_path, NOW, monkeypatch):
    """Enable public archive operations against a temporary artifact store."""
    component = LocalArtifactStore(
        config=LocalArtifactStoreConfig(path=str(tmp_path / "objects")),
        name="archive",
        id=uuid4(),
        flavor="local",
        type=StackComponentType.ARTIFACT_STORE,
        user=None,
        created=NOW,
        updated=NOW,
    )
    monkeypatch.setattr(
        SqlZenStore, "archive_artifact_store", property(lambda _: component)
    )
    monkeypatch.setenv("ZENML_SERVER_ARCHIVE_ENABLED", "true")
    monkeypatch.setenv(
        "ZENML_SERVER_ARCHIVE_ARTIFACT_STORE_ID", str(component.id)
    )
    return component


@pytest.fixture
def archive_one_tree(storage):
    """Provide public archival after the storage fixture configures its destination."""

    def archive(store, ids):
        outcome = store.archive_project(ids.project)
        assert outcome.outcome == RetentionOutcome.SUCCEEDED
        return store.get_run(ids.run, hydrate=False).archive_bundle_id

    return archive


@pytest.fixture
def rows():
    """Provide SQL snapshots for atomicity assertions."""
    return read_tables


class ExecutionTree(BaseModel):
    """Identify the shared two-step execution graph."""

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
def tree_factory(NOW):
    """Provide independent snapshot, step, and inline definition factories."""

    def create(store: SqlZenStore, kind: str = "static") -> ExecutionTree:
        """Build the selected ownership graph.

        Args:
            store: Isolated metadata store.
            kind: Static, dynamic, or legacy configuration ownership.

        Returns:
            Created execution identities.
        """
        project = store.list_projects(ProjectFilter()).items[0].id
        source = graph_rows(project, NOW - timedelta(days=100))
        configure(source, kind)
        insert_rows(store, source)
        store.update_project(
            project,
            ProjectUpdate(retention=RetentionSettings(archive_after_days=7)),
        )
        return ExecutionTree(
            project=project,
            run=source["pipeline_run"][0]["id"],
            snapshot=source["pipeline_snapshot"][0]["id"],
            producer=source["step_run"][0]["id"],
            consumer=source["step_run"][1]["id"],
        )

    return create


@pytest.fixture
def mysql_store() -> SqlZenStore:
    """Use only the explicitly supplied isolated MySQL database."""
    url = os.environ.get("ZENML_RETENTION_TEST_MYSQL_URL")
    if not url:
        pytest.skip("Set ZENML_RETENTION_TEST_MYSQL_URL for the MySQL tier.")
    store = SqlZenStore(
        config=SqlZenStoreConfiguration(url=url),
    )
    assert store.engine.dialect.name == "mysql"
    return store
