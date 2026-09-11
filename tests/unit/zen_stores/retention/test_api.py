# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Authorization precedes archive access; HTTP exposes explicit restore."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event
from starlette.middleware.base import BaseHTTPMiddleware

from zenml.exceptions import IllegalOperationError
from zenml.zen_server import utils
from zenml.zen_server.auth import authorize
from zenml.zen_server.middleware import record_requests
from zenml.zen_server.pipeline_execution import utils as execution
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.routers import (
    pipeline_snapshot_endpoints,
    projects_endpoints,
    runs_endpoints,
    steps_endpoints,
)
from zenml.zen_server.routers.workload_manager_gate import (
    workload_manager_enabled,
)

ROUTERS = (
    projects_endpoints,
    runs_endpoints,
    steps_endpoints,
    pipeline_snapshot_endpoints,
)


@pytest.fixture
def http(retention_store, run_factory, storage, monkeypatch):
    """Mount real routers over the shared MySQL execution fixture."""
    ids = run_factory(retention_store)

    @asynccontextmanager
    async def lifespan(app):
        await utils.initialize_request_manager()
        try:
            yield
        finally:
            await utils.cleanup_request_manager()

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(BaseHTTPMiddleware, dispatch=record_requests)
    for module in ROUTERS:
        app.include_router(module.router)
        monkeypatch.setattr(module, "zen_store", lambda: retention_store)
    monkeypatch.setattr(utils, "zen_store", lambda: retention_store)
    app.dependency_overrides[authorize] = lambda: Mock()
    app.dependency_overrides[workload_manager_enabled] = lambda: None
    pending = []
    monkeypatch.setattr(
        utils,
        "submit_maintenance_task",
        lambda task: pending.append(task) or "task",
    )
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client, ids=ids, pending=pending, store=retention_store
        )


@pytest.mark.parametrize(
    "method,path,action",
    [
        ("GET", "runs/{run}", Action.READ),
        ("GET", "runs/{run}/dag", Action.READ),
        ("GET", "pipeline_snapshots/{snapshot}", Action.READ),
        ("GET", "pipeline_snapshots/{snapshot}/download-token", Action.READ),
        ("GET", "steps/{producer}", Action.READ),
        ("GET", "steps/{producer}/status", Action.READ),
        ("GET", "steps/{producer}/logs?source=missing", Action.READ),
        ("GET", "steps?project={project}&hydrate=true", Action.READ),
        ("POST", "pipeline_snapshots/{snapshot}/runs", Action.READ),
        ("POST", "runs/{run}/replay", Action.READ),
        ("POST", "runs/{run}/restore", Action.UPDATE),
        ("POST", "projects/{project}/retention/archive", Action.UPDATE),
        ("GET", "projects/{project}/retention/status", Action.READ),
    ],
)
def test_denied_before_detail_storage_or_dispatch(
    http, storage, monkeypatch, method, path, action
):
    """Denied requests return 403 before 409, storage/catalog access, or dispatch."""
    http.store.archive_project(http.ids.project)
    denied = Mock(side_effect=HTTPException(403, "Forbidden"))
    blocked = Mock(
        side_effect=AssertionError("denied request crossed boundary")
    )
    for module in ROUTERS:
        monkeypatch.setattr(module, "verify_permission_for_model", denied)
    monkeypatch.setattr(
        steps_endpoints, "get_allowed_resource_ids", lambda **_: []
    )
    monkeypatch.setattr(
        steps_endpoints, "set_filter_project_scope", lambda _: None
    )
    monkeypatch.setattr(storage, "read", blocked)
    monkeypatch.setattr(execution, "run_snapshot", blocked)
    statements = []

    def observe(conn, cursor, statement, parameters, context, many):
        statements.append(statement)

    event.listen(http.store.engine, "before_cursor_execute", observe)
    try:
        response = http.client.request(
            method,
            "/api/v1/" + path.format(**http.ids.model_dump()),
            json={} if method == "POST" else None,
        )
    finally:
        event.remove(http.store.engine, "before_cursor_execute", observe)
    assert response.status_code == 403, response.text
    denied.assert_called_once()
    assert denied.call_args.kwargs["action"] == action
    assert not any("FROM archive_bundle" in sql for sql in statements)
    assert not http.pending
    blocked.assert_not_called()


def test_archive_restore_http_lifecycle(http, monkeypatch):
    """Archive runs in the worker; restore completes synchronously and is idempotent."""
    project = f"/api/v1/projects/{http.ids.project}/retention"
    detail = f"/api/v1/runs/{http.ids.run}"
    with monkeypatch.context() as disabled:
        disabled.delenv("ZENML_SERVER_ARCHIVE_URI")
        assert http.client.post(project + "/archive").status_code == 403
        assert not http.pending
    accepted = http.client.post(project + "/archive")
    assert accepted.status_code == 202
    assert accepted.json() == {"outcome": "accepted", "task_id": "task"}
    assert http.client.post(project + "/archive").status_code == 409
    http.pending.pop()()
    status = http.client.get(project + "/status").json()
    assert status["outcome"] == "succeeded" and status["archived"] == 1
    assert (
        http.client.get(detail, params={"hydrate": "false"}).status_code == 200
    )
    response = http.client.get(detail)
    assert (
        response.status_code == 409
        and "zenml pipeline runs restore" in response.text
    )
    assert (
        http.client.post(detail + "/restore").json()["outcome"] == "restored"
    )
    assert http.client.get(detail).status_code == 200
    assert http.client.post(detail + "/restore").json()["outcome"] == "noop"


@pytest.mark.parametrize(
    "error,expected",
    [
        (IllegalOperationError("revoked"), "permission_revoked"),
        (RuntimeError("database unavailable"), "archive_failed"),
    ],
)
def test_worker_reauthorizes_before_execution(monkeypatch, error, expected):
    """Revoked authorization aborts without running the queued pass."""
    abort, execute = Mock(), Mock()
    monkeypatch.setattr(utils, "submit_maintenance_task", lambda task: task())
    utils.submit_archive_pass(
        execute=execute, abort=abort, reauthorize=Mock(side_effect=error)
    )
    abort.assert_called_once_with(expected)
    execute.assert_not_called()


def test_maintenance_task_runs_with_the_submitting_auth_context() -> None:
    """The task sees the caller's auth context, which is reset afterwards."""
    auth_context = Mock()
    submitted = []
    executor = Mock()
    executor.submit.side_effect = lambda run: submitted.append(run)
    seen = []

    with (
        patch.object(utils, "maintenance_executor", return_value=executor),
        patch.object(utils, "get_auth_context", return_value=auth_context),
    ):
        task_id = utils.submit_maintenance_task(
            lambda: seen.append(utils.get_auth_context())
        )

    assert task_id and len(submitted) == 1
    submitted[0]()
    assert seen == [auth_context]
    assert utils._auth_context.get() is None
