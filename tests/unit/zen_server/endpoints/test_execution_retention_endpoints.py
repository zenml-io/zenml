# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""HTTP authorization and lifecycle guarantees for execution retention."""

import re
from contextlib import asynccontextmanager
from threading import Event, current_thread
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
from tests.unit.zen_stores.conftest import sql_store as sql_store_fixture
from tests.unit.zen_stores.retention.conftest import storage as storage_fixture
from tests.unit.zen_stores.retention.fixture_graph import FROZEN_NOW, seed_tree

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
from zenml.zen_server.pipeline_execution.utils import BoundedThreadPoolExecutor
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
sql_store = sql_store_fixture
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
def http(sql_store, storage, monkeypatch) -> Iterator[SimpleNamespace]:
    """Mount the real routers over one configured two-step SQL tree."""
    tree = seed_tree(sql_store, FROZEN_NOW)
    sql_store.update_project(
        tree["project"],
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
        monkeypatch.setattr(module, "zen_store", lambda: sql_store)
    monkeypatch.setattr(utils, "zen_store", lambda: sql_store)
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
            tree=tree,
            pending=pending,
            store=sql_store,
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
            .where(PipelineRunSchema.id == http.tree["run"])
            .values(user_id=http.store.get_user("default").id)
        )
        connection.execute(
            update(PipelineSnapshotSchema)
            .where(PipelineSnapshotSchema.id == http.tree["snapshot"])
            .values(user_id=http.store.get_user("default").id)
        )
    if cold:
        assert (
            http.store.archive_project(http.tree["project"]).outcome.value
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
    monkeypatch.setattr(http.storage, "open", blocked)
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

    ids = http.tree
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
        ("get", "run", "restore"),
        ("post", "project", "archive"),
        ("get", "project", "status"),
        ("post", "project", "dry-run"),
    ],
)
def test_operation_routes_deny_before_catalog(
    http, monkeypatch, method: str, scope: str, operation: str
) -> None:
    """UPDATE grants submissions and READ grants status access."""
    denied = Mock(side_effect=HTTPException(403, "Forbidden"))
    module = runs_endpoints if scope == "run" else projects_endpoints
    monkeypatch.setattr(module, "verify_permission_for_model", denied)
    ids = http.tree
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


@pytest.mark.parametrize("scope", ["archive", "restore"])
def test_public_submission_is_accepted_before_completion(
    http, scope: str
) -> None:
    """Queued work returns its task ID before the terminal status."""
    ids = http.tree
    if scope == "restore":
        http.store.archive_project(ids["project"])
        submit = status = f"/api/v1/runs/{ids['run']}/restore"
    else:
        submit = f"/api/v1/projects/{ids['project']}/retention/archive"
        status = f"/api/v1/projects/{ids['project']}/retention/status"
    accepted = http.client.post(submit)
    assert accepted.status_code == 202
    assert accepted.json()["outcome"] == "accepted"
    assert accepted.json()["task_id"] == "task"
    assert len(http.pending) == 1
    http.pending.pop()()
    assert http.client.get(status).json()["outcome"] == "succeeded"


def test_disabled_archive_names_no_private_switch(http, monkeypatch) -> None:
    """The server gate tells users to contact their administrator."""
    monkeypatch.setenv("ZENML_SERVER_ARCHIVE_ENABLED", "false")
    response = http.client.post(
        f"/api/v1/projects/{http.tree['project']}/retention/archive"
    )
    assert response.status_code == 403
    assert "ask your server administrator to enable it" in response.text
    assert "ZENML_SERVER_ARCHIVE_ENABLED" not in response.text
    assert not http.pending


def test_rejected_submission_cannot_clobber_the_running_pass(
    http, monkeypatch
) -> None:
    """A capacity rejection preserves the first pass's operation ID."""
    started, release, finished = Event(), Event(), Event()
    original_open = http.storage.open
    original_execute = SqlZenStore.execute_retention_pass

    def block_upload(path: str, mode: str = "r") -> Any:
        if (
            current_thread().name.startswith("retention-state-test")
            and mode == "wb"
            and str(path).endswith("rows.tar.gz")
        ):
            started.set()
            assert release.wait(10)
        return original_open(path, mode)

    def execute(store: SqlZenStore, claimed: Any) -> Any:
        try:
            return original_execute(store, claimed)
        finally:
            finished.set()

    monkeypatch.setattr(http.storage, "open", block_upload)
    monkeypatch.setattr(SqlZenStore, "execute_retention_pass", execute)
    monkeypatch.setattr(utils, "submit_maintenance_task", http.original_submit)
    executor = BoundedThreadPoolExecutor(
        max_workers=1, thread_name_prefix="retention-state-test"
    )
    monkeypatch.setattr(utils, "_maintenance_executor", executor)
    route = f"/api/v1/projects/{http.tree['project']}/retention/archive"
    try:
        assert http.client.post(route).status_code == 202
        assert started.wait(10)
        assert http.client.post(route).status_code == 429
        assert (
            http.store.get_retention_status(http.tree["project"]).outcome.value
            == "accepted"
        )
    finally:
        release.set()
        assert finished.wait(10)
        executor.shutdown(wait=True)
    assert (
        http.store.get_retention_status(http.tree["project"]).outcome.value
        == "succeeded"
    )


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
    utils.submit_reserved_operation(
        Mock(),
        execute=Mock(),
        abort=abort,
        reauthorize=Mock(side_effect=error),
        operation_failure=RetentionFailure.ARCHIVE_FAILED,
    )
    abort.assert_called_once_with(expected)


def test_status_reports_an_unloadable_store_as_unconfigured(
    sql_store, monkeypatch
) -> None:
    """Status distinguishes a configured ID from a loadable store."""
    project = sql_store.list_projects(ProjectFilter()).items[0].id

    def unavailable(_: SqlZenStore) -> None:
        raise ExecutionRetentionUnavailableError("unavailable")

    monkeypatch.setattr(
        SqlZenStore, "archive_artifact_store", property(unavailable)
    )
    assert sql_store.get_retention_status(project).archive_configured is False
