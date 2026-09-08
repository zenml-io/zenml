# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Retention dry runs through HTTP, client and CLI without database writes."""

from typing import Any
from unittest.mock import Mock

import pytest
from click.testing import CliRunner
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event
from tests.unit.zen_stores.test_execution_retention_eligibility import (
    make_tree,
)
from tests.unit.zen_stores.test_execution_retention_eligibility import (
    sql_store as sql_store,
)

from zenml.cli.project import project
from zenml.client import Client
from zenml.models import ProjectUpdate
from zenml.models.v2.misc.retention import (
    RetentionDryRunRequest,
    RetentionSettings,
)
from zenml.zen_server.auth import authorize
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.routers import projects_endpoints as endpoints
from zenml.zen_stores.rest_zen_store import RestZenStore
from zenml.zen_stores.sql_zen_store import SqlZenStore


@pytest.mark.parametrize("allowed", [True, False])
def test_http_inventory_requires_update_and_never_writes(
    sql_store: SqlZenStore, monkeypatch: pytest.MonkeyPatch, allowed: bool
) -> None:
    """Authorization precedes inventory; all execution and project rows are unchanged.

    Args:
        sql_store: Isolated SQL store.
        monkeypatch: Isolated environment and dependency overrides.
        allowed: Whether project UPDATE permission is granted.
    """
    tree = make_tree(sql_store)
    app = FastAPI()
    app.include_router(endpoints.router)
    app.dependency_overrides[authorize] = lambda: Mock()
    monkeypatch.setattr(endpoints, "zen_store", lambda: sql_store)
    permission = Mock(
        side_effect=None if allowed else HTTPException(403, "Forbidden")
    )
    monkeypatch.setattr(endpoints, "verify_permission_for_model", permission)
    statements = []

    def record(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        statements.append(statement)

    with sql_store.engine.connect() as connection:
        before = "\n".join(connection.connection.driver_connection.iterdump())
    event.listen(sql_store.engine, "before_cursor_execute", record)
    try:
        with TestClient(app) as http:
            response = http.post(
                f"/api/v1/projects/{tree['project']}/retention/dry-run",
                json={"archive_after_days": 90},
            )
    finally:
        event.remove(sql_store.engine, "before_cursor_execute", record)
    assert response.status_code == (200 if allowed else 403)
    assert permission.call_args.kwargs["action"] == Action.UPDATE
    assert permission.call_args.kwargs["model"].id == tree["project"]
    if allowed:
        body = response.json()
        assert body["eligible_tree_count"] == 1
        assert body["effective_policy"]["archive_after_days"] == 90
        assert body["tables"]["pipeline_run"]["rows_deleted"] == 0
        assert (
            body["message"]
            == "estimates are logical bytes; no data was changed"
        )
    else:
        assert not any("pipeline_run" in statement for statement in statements)
    assert all(
        statement.lstrip().upper().startswith("SELECT")
        for statement in statements
    )
    with sql_store.engine.connect() as connection:
        assert (
            "\n".join(connection.connection.driver_connection.iterdump())
            == before
        )


def test_client_and_cli_preview_same_policy(
    sql_store: SqlZenStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The client and requested CLI route use the same typed store contract.

    Args:
        sql_store: Isolated SQL store.
        monkeypatch: Isolated environment and dependency overrides.
    """
    tree = make_tree(sql_store)
    monkeypatch.setattr(Client, "zen_store", property(lambda _: sql_store))
    client = Client()
    sql_store.update_project(
        tree["project"],
        ProjectUpdate(retention=RetentionSettings(archive_after_days=180)),
    )
    report = client.retention_dry_run(
        project=tree["project"], archive_after_days=90
    )
    assert report.eligible_tree_count == 1
    assert (
        sql_store.get_project(tree["project"]).retention.archive_after_days
        == 180
    )
    result = CliRunner().invoke(
        project,
        [
            "retention",
            "dry-run",
            "--project",
            str(tree["project"]),
            "--archive-after-days",
            "90",
        ],
    )
    assert result.exit_code == 0, result.output
    assert '"eligible_tree_count": 1' in result.output
    assert "no data was changed" in result.output


def test_rest_store_uses_inventory_endpoint(sql_store: SqlZenStore) -> None:
    """REST serialization preserves the request and flat response.

    Args:
        sql_store: Isolated SQL store.
    """
    tree = make_tree(sql_store)
    request = RetentionDryRunRequest(archive_after_days=90)
    expected = sql_store.retention_dry_run(tree["project"], request)
    transport = Mock(spec=RestZenStore)
    transport.post.return_value = expected.model_dump(mode="json")
    assert (
        RestZenStore.retention_dry_run(transport, tree["project"], request)
        == expected
    )
    transport.post.assert_called_once_with(
        f"/projects/{tree['project']}/retention/dry-run", body=request
    )
