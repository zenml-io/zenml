# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Authorization precedes archive access; HTTP exposes explicit restore."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event, update
from starlette.middleware.base import BaseHTTPMiddleware

from zenml.enums import ExecutionStatus
from zenml.zen_server import utils
from zenml.zen_server.auth import authorize
from zenml.zen_server.middleware import record_requests
from zenml.zen_server.pipeline_execution import utils as execution
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.routers import (
    pipeline_snapshot_endpoints,
    retention_endpoints,
    runs_endpoints,
    steps_endpoints,
)
from zenml.zen_server.routers.workload_manager_gate import (
    workload_manager_enabled,
)
from zenml.zen_stores.schemas import PipelineRunSchema

ROUTERS = (
    retention_endpoints,
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
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, ids=ids, store=retention_store)


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
        ("POST", "retention/archive", Action.UPDATE),
    ],
)
def test_denied_before_detail_storage_or_dispatch(
    http, storage, monkeypatch, method, path, action
):
    """Denied requests return 403 before 409 or any storage access."""
    http.store.run_archive_sweep()
    denied = Mock(side_effect=HTTPException(403, "Forbidden"))
    blocked = Mock(
        side_effect=AssertionError("denied request crossed boundary")
    )
    for module in ROUTERS:
        for name in (
            "verify_permission_for_model",
            "batch_verify_permissions_for_models",
        ):
            if hasattr(module, name):
                monkeypatch.setattr(module, name, denied)
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
            json={"run_ids": [str(http.ids.run)]}
            if method == "POST"
            else None,
        )
    finally:
        event.remove(http.store.engine, "before_cursor_execute", observe)
    assert response.status_code == 403, response.text
    denied.assert_called_once()
    assert denied.call_args.kwargs["action"] == action
    assert not any("FROM archive_bundle" in sql for sql in statements)
    blocked.assert_not_called()


def test_archive_restore_http_lifecycle(http, monkeypatch):
    """Targeted archiving runs in the request; restore is idempotent."""
    archive = "/api/v1/retention/archive"
    detail = f"/api/v1/runs/{http.ids.run}"
    body = {"run_ids": [str(http.ids.run)]}
    with monkeypatch.context() as disabled:
        disabled.delenv("ZENML_SERVER_ARCHIVE__BACKEND")
        assert http.client.post(archive, json=body).status_code == 503
    assert http.client.post(archive, json={}).status_code == 422
    result = http.client.post(archive, json=body)
    assert result.status_code == 200, result.text
    assert result.json()["archived"] == 1
    assert result.json()["refusals"] == []
    status = http.client.get("/api/v1/retention/status").json()
    assert status["archive_enabled"] and status["archive_after_days"] == 7
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


def test_archiving_an_active_run_is_refused_with_a_reason(http):
    """Forcing past the age never forces past the safety rules."""
    with http.store.engine.begin() as connection:
        connection.execute(
            update(PipelineRunSchema)
            .where(PipelineRunSchema.id == http.ids.run)
            .values(status=ExecutionStatus.RUNNING.value)
        )
    result = http.client.post(
        "/api/v1/retention/archive", json={"run_ids": [str(http.ids.run)]}
    ).json()
    assert result["archived"] == 0 and result["skipped"] == 1
    assert result["refusals"] == [
        {"run_id": str(http.ids.run), "reason": "not_eligible"}
    ]
