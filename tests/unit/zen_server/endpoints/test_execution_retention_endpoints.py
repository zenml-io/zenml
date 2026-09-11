# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""HTTP authorization and lifecycle guarantees for execution retention."""

import re
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from threading import Event
from types import SimpleNamespace
from typing import Any, AsyncIterator, Iterator
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event, select, update
from starlette.middleware.base import BaseHTTPMiddleware
from tests.unit.zen_stores.conftest import NOW as NOW_fixture
from tests.unit.zen_stores.conftest import (
    retention_database as retention_database_fixture,
)
from tests.unit.zen_stores.conftest import (
    retention_store as retention_store_fixture,
)
from tests.unit.zen_stores.retention.conftest import storage as storage_fixture
from tests.unit.zen_stores.retention.fixture_graph import FROZEN_NOW, seed_run

from zenml.enums import RetentionFailure
from zenml.exceptions import (
    ExecutionRetentionUnavailableError,
    IllegalOperationError,
)
from zenml.models import ProjectFilter, ProjectUpdate, UserRequest
from zenml.models.v2.misc.retention import RetentionSettings
from zenml.zen_server import utils
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.middleware import record_requests
from zenml.zen_server.pipeline_execution import utils as execution
from zenml.zen_server.rbac import utils as rbac_utils
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.rbac.rbac_interface import RBACInterface
from zenml.zen_server.routers import (
    hook_invocations_endpoints,
    pipeline_snapshot_endpoints,
    projects_endpoints,
    run_wait_conditions_endpoints,
    runs_endpoints,
    steps_endpoints,
)
from zenml.zen_server.routers.workload_manager_gate import (
    workload_manager_enabled,
)
from zenml.zen_stores.schemas import (
    HookInvocationSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    RunWaitConditionSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore

# Re-export fixtures shared from the store suites.
NOW = NOW_fixture
retention_database = retention_database_fixture
retention_store = retention_store_fixture
storage = storage_fixture

ROUTERS = (
    projects_endpoints,
    runs_endpoints,
    steps_endpoints,
    pipeline_snapshot_endpoints,
    run_wait_conditions_endpoints,
    hook_invocations_endpoints,
)


@pytest.fixture
def http(retention_store, storage, monkeypatch) -> Iterator[SimpleNamespace]:
    """Mount the real routers over one configured two-step run."""
    ids = seed_run(retention_store, FROZEN_NOW)
    retention_store.update_project(
        ids["project"],
        ProjectUpdate(retention=RetentionSettings(archive_after_days=90)),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
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
    pending: list[Any] = []
    original_submit = utils.submit_maintenance_task
    monkeypatch.setattr(
        utils,
        "submit_maintenance_task",
        lambda task: pending.append(task) or "task",
    )
    with TestClient(app) as client:
        yield SimpleNamespace(
            app=app,
            client=client,
            ids=ids,
            pending=pending,
            store=retention_store,
            storage=storage,
            original_submit=original_submit,
        )


@pytest.mark.parametrize(
    "operation",
    (
        "run snapshot step dag wait hook step_status logs code_token "
        "snapshot_run replay step_list run_delete snapshot_delete"
    ).split(),
)
@pytest.mark.parametrize("cold", [False, True])
def test_execution_routes_deny_before_archive_io_or_dispatch(
    http, monkeypatch, operation: str, cold: bool
) -> None:
    """Every execution route enforces READ before cold I/O or dispatch."""
    user = http.store.create_user(
        UserRequest(
            name=f"reader-{uuid4().hex}",
            password="test-password",
            active=True,
            is_admin=False,
        )
    )
    with http.store.engine.begin() as connection:
        connection.execute(
            update(PipelineRunSchema)
            .where(PipelineRunSchema.id == http.ids["run"])
            .values(user_id=http.store.get_user("default").id)
        )
        connection.execute(
            update(PipelineSnapshotSchema)
            .where(PipelineSnapshotSchema.id == http.ids["snapshot"])
            .values(user_id=http.store.get_user("default").id)
        )
    if cold:
        assert (
            http.store.archive_project(http.ids["project"]).outcome.value
            == "succeeded"
        )

    async def authenticated() -> AuthContext:
        context = AuthContext(user=user)
        utils.set_auth_context(context)
        request = utils.request_manager().current_request
        if request is not None:
            request.auth_context = context
        return context

    http.app.dependency_overrides[authorize] = authenticated
    provider = Mock(spec=RBACInterface)
    provider.check_permissions.side_effect = lambda user, resources, action: (
        dict.fromkeys(resources, False)
    )
    monkeypatch.setattr(
        rbac_utils,
        "server_config",
        lambda: SimpleNamespace(rbac_enabled=True),
    )
    monkeypatch.setattr(rbac_utils, "rbac", lambda: provider)
    blocked = Mock(
        side_effect=AssertionError("denied route crossed its boundary")
    )
    monkeypatch.setattr(http.storage, "read", blocked)
    monkeypatch.setattr(execution, "run_snapshot", blocked)
    route_permission = None
    if operation == "step_list":
        monkeypatch.setattr(
            steps_endpoints, "get_allowed_resource_ids", lambda **_: []
        )
        monkeypatch.setattr(
            steps_endpoints, "set_filter_project_scope", lambda _: None
        )
        route_permission = Mock(side_effect=HTTPException(403, "Forbidden"))
        monkeypatch.setattr(
            steps_endpoints, "verify_permission_for_model", route_permission
        )

    ids = http.ids
    paths = {
        "run": ("get", f"runs/{ids['run']}"),
        "snapshot": ("get", f"pipeline_snapshots/{ids['snapshot']}"),
        "step": ("get", f"steps/{ids['step']}"),
        "dag": ("get", f"runs/{ids['run']}/dag"),
        "step_status": ("get", f"steps/{ids['step']}/status"),
        "logs": ("get", f"steps/{ids['step']}/logs"),
        "code_token": (
            "get",
            f"pipeline_snapshots/{ids['snapshot']}/download-token",
        ),
        "snapshot_run": (
            "post",
            f"pipeline_snapshots/{ids['snapshot']}/runs",
        ),
        "replay": ("post", f"runs/{ids['run']}/replay"),
        "step_list": ("get", "steps"),
        "run_delete": ("delete", f"runs/{ids['run']}"),
        "snapshot_delete": (
            "delete",
            f"pipeline_snapshots/{ids['snapshot']}",
        ),
    }
    if operation in ("wait", "hook"):
        table, route = (
            (RunWaitConditionSchema, "run_wait_conditions")
            if operation == "wait"
            else (HookInvocationSchema, "hook_invocations")
        )
        with http.store.engine.begin() as connection:
            child = connection.execute(select(table.id)).scalar_one()
        method, path = "get", f"{route}/{child}"
    else:
        method, path = paths[operation]
    params = {"source": "missing"} if operation == "logs" else {}
    if operation == "step_list":
        params = {"project": str(ids["project"]), "hydrate": "true"}
    response = http.client.request(
        method,
        f"/api/v1/{path}",
        params=params,
        json={} if method == "post" else None,
    )
    assert response.status_code == 403, response.text
    if route_permission is None:
        assert provider.check_permissions.call_count == 1
    else:
        route_permission.assert_called_once()
    blocked.assert_not_called()


@pytest.mark.parametrize(
    "method,scope,operation",
    [
        ("post", "run", "restore"),
        ("post", "project", "archive"),
        ("get", "project", "status"),
    ],
)
def test_operation_routes_deny_before_catalog(
    http, monkeypatch, method: str, scope: str, operation: str
) -> None:
    """UPDATE grants submissions and READ grants status access."""
    denied = Mock(side_effect=HTTPException(403, "Forbidden"))
    module = runs_endpoints if scope == "run" else projects_endpoints
    monkeypatch.setattr(module, "verify_permission_for_model", denied)
    ids = http.ids
    route = (
        f"/api/v1/runs/{ids['run']}/restore"
        if scope == "run"
        else f"/api/v1/projects/{ids['project']}/retention/{operation}"
    )
    statements: list[str] = []

    def observe(
        conn, cursor, statement, parameters, context, executemany
    ) -> None:
        statements.append(statement)

    event.listen(http.store.engine, "before_cursor_execute", observe)
    try:
        response = http.client.request(method, route)
    finally:
        event.remove(http.store.engine, "before_cursor_execute", observe)
    assert response.status_code == 403 and not http.pending
    assert not any(
        re.search(r"(?:FROM|JOIN) archive_bundle\b", s) for s in statements
    )
    assert denied.call_args.kwargs["action"] == (
        Action.UPDATE if method == "post" else Action.READ
    )


def test_archive_is_accepted_before_it_runs(http) -> None:
    """An archive pass returns its task ID before the pass finishes."""
    project = http.ids["project"]
    accepted = http.client.post(
        f"/api/v1/projects/{project}/retention/archive"
    )
    assert accepted.status_code == 202
    assert accepted.json() == {"outcome": "accepted", "task_id": "task"}
    http.pending.pop()()
    status = http.client.get(f"/api/v1/projects/{project}/retention/status")
    assert status.json()["outcome"] == "succeeded"
    assert status.json()["archived"] == 1


def test_restore_finishes_within_the_request(http) -> None:
    """Restore returns its result directly, and a second call is a no-op."""
    http.store.archive_project(http.ids["project"])
    route = f"/api/v1/runs/{http.ids['run']}/restore"
    restored = http.client.post(route)
    assert restored.status_code == 200
    assert restored.json()["outcome"] == "restored"
    assert http.client.post(route).json()["outcome"] == "noop"


def test_disabled_archive_names_no_private_switch(http, monkeypatch) -> None:
    """The server gate tells users to contact their administrator."""
    monkeypatch.delenv("ZENML_SERVER_ARCHIVE_URI")
    response = http.client.post(
        f"/api/v1/projects/{http.ids['project']}/retention/archive"
    )
    assert response.status_code == 403
    assert "ask your server administrator to enable it" in response.text
    assert "ZENML_SERVER_ARCHIVE_URI" not in response.text
    assert not http.pending


def test_second_pass_is_rejected_while_the_first_runs(
    http, monkeypatch
) -> None:
    """Only one pass per project runs; a second submission gets 409."""
    uploading, release = Event(), Event()
    original = http.storage.write

    def pause_upload(uri: str, data: bytes) -> None:
        uploading.set()
        assert release.wait(20)
        original(uri, data)

    monkeypatch.setattr(http.storage, "write", pause_upload)
    route = f"/api/v1/projects/{http.ids['project']}/retention/archive"
    assert http.client.post(route).status_code == 202
    with ThreadPoolExecutor(1) as pool:
        running = pool.submit(http.pending.pop())
        try:
            assert uploading.wait(20)
            assert http.client.post(route).status_code == 409
        finally:
            release.set()
        running.result(timeout=20)
    status = http.store.get_retention_status(http.ids["project"])
    assert status.outcome.value == "succeeded"


@pytest.mark.parametrize(
    "error,expected",
    [
        (
            IllegalOperationError("revoked"),
            RetentionFailure.PERMISSION_REVOKED,
        ),
        (
            RuntimeError("database unavailable"),
            RetentionFailure.ARCHIVE_FAILED,
        ),
    ],
)
def test_worker_reauthorization_failure_is_classified(
    monkeypatch, error: Exception, expected: RetentionFailure
) -> None:
    """Only permission failures use the revoked classification."""
    abort = Mock()
    monkeypatch.setattr(utils, "submit_maintenance_task", lambda task: task())
    utils.submit_archive_pass(
        execute=Mock(), abort=abort, reauthorize=Mock(side_effect=error)
    )
    abort.assert_called_once_with(expected)


def test_status_reports_unusable_storage_as_unconfigured(
    retention_store, monkeypatch
) -> None:
    """Status distinguishes a set archive URI from usable storage."""
    project = retention_store.list_projects(ProjectFilter()).items[0].id

    def unavailable(_: SqlZenStore) -> None:
        raise ExecutionRetentionUnavailableError("unavailable")

    monkeypatch.setattr(SqlZenStore, "archive_storage", property(unavailable))
    assert (
        retention_store.get_retention_status(project).archive_configured
        is False
    )
