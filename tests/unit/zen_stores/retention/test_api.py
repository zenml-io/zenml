# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Authorization precedes archive access; HTTP exposes explicit restore."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event, update
from sqlmodel import Session
from starlette.middleware.base import BaseHTTPMiddleware

from zenml.enums import (
    ExecutionStatus,
    MetadataResourceTypes,
    SourceType,
    VisualizationResourceTypes,
)
from zenml.exceptions import ExecutionRetentionUnavailableError
from zenml.models import (
    PipelineRunRequest,
    PipelineSnapshotResponse,
    PlatformEventTriggerRequest,
    UserFilter,
)
from zenml.zen_server import utils
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.middleware import record_requests
from zenml.zen_server.pipeline_execution import utils as execution
from zenml.zen_server.rbac import endpoint_utils
from zenml.zen_server.rbac import utils as rbac_utils
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.retention import RetentionCapacity
from zenml.zen_server.routers import (
    curated_visualization_endpoints,
    logs_endpoints,
    pipeline_snapshot_endpoints,
    projects_endpoints,
    retention_endpoints,
    run_metadata_endpoints,
    runs_endpoints,
    steps_endpoints,
    trigger_endpoints,
)
from zenml.zen_stores.schemas import LogsSchema, PipelineRunSchema

ROUTERS = (
    retention_endpoints,
    run_metadata_endpoints,
    runs_endpoints,
    steps_endpoints,
    pipeline_snapshot_endpoints,
    projects_endpoints,
    curated_visualization_endpoints,
    logs_endpoints,
    trigger_endpoints,
)


@pytest.fixture
def http(
    retention_store, retention, run_factory, monkeypatch, archive_project
):
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
    # A server without a workload manager never mounts these routes.
    for module in (runs_endpoints, pipeline_snapshot_endpoints):
        app.include_router(module.workload_router, prefix=module.router.prefix)
    monkeypatch.setattr(utils, "zen_store", lambda: retention_store)
    auth_context = AuthContext(
        user=retention_store.list_users(UserFilter()).items[0]
    )

    async def authenticated() -> AuthContext:
        utils.set_auth_context(auth_context)
        return auth_context

    app.dependency_overrides[authorize] = authenticated
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
            ids=ids,
            store=retention_store,
            retention=retention,
            archive=archive_project,
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
        ("POST", "pipeline_snapshots/{snapshot}/runs", Action.READ),
        ("POST", "runs/{run}/replay", Action.READ),
        ("POST", "runs/{run}/restore", Action.READ),
        ("DELETE", "runs/{run}", Action.DELETE),
        ("POST", "retention/archive", Action.UPDATE),
    ],
)
def test_denied_before_detail_storage_or_dispatch(
    http, storage, monkeypatch, method, path, action
):
    """Denied requests return 403 before 409 or any storage access."""
    http.archive()
    denied = Mock(side_effect=HTTPException(403, "Forbidden"))
    blocked = Mock(
        side_effect=AssertionError("denied request crossed boundary")
    )
    for module in (
        retention_endpoints,
        run_metadata_endpoints,
        runs_endpoints,
        steps_endpoints,
    ):
        monkeypatch.setattr(module, "verify_permission_for_model", denied)
    monkeypatch.setattr(endpoint_utils, "verify_permission_for_model", denied)
    monkeypatch.setattr(
        retention_endpoints, "batch_verify_permissions_for_models", denied
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


@pytest.mark.parametrize(
    "endpoint",
    [
        "visualization_run",
        "visualization_snapshot",
        "trigger_run",
        "trigger_snapshot",
        "attach",
        "detach",
        "logs",
    ],
)
def test_related_endpoints_authorize_archived_owners(
    http, storage, monkeypatch, endpoint
):
    """Related resources check the execution owner's permission before detail."""
    http.archive()
    checked = []

    def deny_owner(model, *, action):
        if model.id in {http.ids.run, http.ids.snapshot}:
            checked.append((model.id, action))
            raise HTTPException(403, "Forbidden")

    for module in (
        curated_visualization_endpoints,
        logs_endpoints,
        trigger_endpoints,
        endpoint_utils,
    ):
        monkeypatch.setattr(module, "verify_permission_for_model", deny_owner)
    opened = Mock(side_effect=AssertionError("denied request read archive"))
    monkeypatch.setattr(storage, "read", opened)
    body = None
    owner = (
        http.ids.snapshot
        if endpoint.endswith("snapshot") or endpoint in {"attach", "detach"}
        else http.ids.run
    )
    action = Action.READ
    if endpoint.startswith("visualization"):
        monkeypatch.setattr(
            type(http.store),
            "get_curated_visualization",
            lambda *args, **kwargs: SimpleNamespace(
                resource_id=owner,
                resource_type=VisualizationResourceTypes.PIPELINE_SNAPSHOT
                if owner == http.ids.snapshot
                else VisualizationResourceTypes.PIPELINE_RUN,
            ),
        )
        method, path = "GET", f"curated_visualizations/{uuid4()}"
    elif endpoint.startswith("trigger"):
        source_type = (
            SourceType.PIPELINE_SNAPSHOT
            if owner == http.ids.snapshot
            else SourceType.PIPELINE_RUN
        )
        body = PlatformEventTriggerRequest(
            project=http.ids.project,
            name="archive-source",
            source_entity={"id": owner, "type": source_type},
            target_events=[
                "run_completed" if owner == http.ids.snapshot else "completed"
            ],
        ).model_dump(mode="json")
        method, path, action = "POST", "triggers", Action.UPDATE
    elif endpoint in {"attach", "detach"}:
        trigger_id = uuid4()
        monkeypatch.setattr(
            type(http.store),
            "get_trigger",
            lambda self, **kwargs: SimpleNamespace(
                id=trigger_id, project_id=http.ids.project, snapshots=[]
            ),
        )
        method = "PUT" if endpoint == "attach" else "DELETE"
        path = f"triggers/{trigger_id}/pipeline_snapshots/{http.ids.snapshot}"
    else:
        method, path, action = "POST", "logs", Action.UPDATE
        body = {
            "project": str(http.ids.project),
            "step_run_id": str(http.ids.producer),
            "source": "runner",
        }

    response = http.client.request(method, f"/api/v1/{path}", json=body)

    assert response.status_code == 403, response.text
    assert checked == [(owner, action)]
    opened.assert_not_called()


def test_read_permission_restores_without_allowing_run_updates(
    http, monkeypatch
):
    """A reader can restore detail without gaining run update permission."""
    http.archive()
    checked_actions = []

    def allow_read(model, action):
        checked_actions.append(action)
        if action != Action.READ:
            raise HTTPException(403, "Forbidden")

    monkeypatch.setattr(
        runs_endpoints, "verify_permission_for_model", allow_read
    )
    monkeypatch.setattr(
        endpoint_utils, "verify_permission_for_model", allow_read
    )

    restored = http.client.post(f"/api/v1/runs/{http.ids.run}/restore")
    update_response = http.client.put(f"/api/v1/runs/{http.ids.run}", json={})

    assert restored.status_code == 200, restored.text
    assert restored.json()["outcome"] == "restored"
    assert update_response.status_code == 403, update_response.text
    assert checked_actions == [Action.READ, Action.UPDATE]


def test_get_entity_header_authorization_precedes_dehydration(
    monkeypatch,
):
    """The opt-in getter authorizes its header before returning redacted data."""
    resource_id = uuid4()
    header = object()
    hydrated = object()
    redacted = object()
    events = []

    def verify(model, *, action):
        events.append(("authorize", model, action))

    def get(entity_id, *, authorizer, hydrate):
        assert entity_id == resource_id and hydrate is True
        authorizer(header)
        events.append(("hydrate", hydrated))
        return hydrated

    def dehydrate(model):
        events.append(("dehydrate", model))
        return redacted

    monkeypatch.setattr(endpoint_utils, "verify_permission_for_model", verify)
    monkeypatch.setattr(endpoint_utils, "dehydrate_response_model", dehydrate)

    result = endpoint_utils.verify_permissions_and_get_entity(
        id=resource_id,
        get_method=get,
        authorize_in_store=True,
        hydrate=True,
    )

    assert result is redacted
    assert events == [
        ("authorize", header, Action.READ),
        ("hydrate", hydrated),
        ("dehydrate", hydrated),
    ]


def test_get_entity_default_authorization_order_is_unchanged(monkeypatch):
    """Existing helper callers still authorize the fetched response."""
    resource_id = uuid4()
    model = object()
    events = []

    def get(entity_id, *, hydrate):
        assert entity_id == resource_id and hydrate is False
        events.append(("get", model))
        return model

    def verify(response, *, action):
        events.append(("authorize", response, action))

    def dehydrate(response):
        events.append(("dehydrate", response))
        return response

    monkeypatch.setattr(endpoint_utils, "verify_permission_for_model", verify)
    monkeypatch.setattr(endpoint_utils, "dehydrate_response_model", dehydrate)

    result = endpoint_utils.verify_permissions_and_get_entity(
        id=resource_id,
        get_method=get,
        hydrate=False,
    )

    assert result is model
    assert events == [
        ("get", model),
        ("authorize", model, Action.READ),
        ("dehydrate", model),
    ]


def test_step_status_checks_only_the_owning_run_once(http, monkeypatch):
    """A scalar step read performs one permission check for its owning run."""
    checks = Mock(
        side_effect=lambda *, user, resources, action: {
            resource: True for resource in resources
        }
    )
    monkeypatch.setattr(
        rbac_utils,
        "server_config",
        lambda: SimpleNamespace(rbac_enabled=True),
    )
    monkeypatch.setattr(
        rbac_utils,
        "is_owned_by_authenticated_user",
        lambda _: False,
    )
    monkeypatch.setattr(
        rbac_utils,
        "rbac",
        lambda: SimpleNamespace(check_permissions=checks),
    )

    response = http.client.get(f"/api/v1/steps/{http.ids.producer}/status")

    assert response.status_code == 200, response.text
    assert checks.call_count == 1
    assert {
        (resource.type, resource.id)
        for resource in checks.call_args.kwargs["resources"]
    } == {(ResourceType.PIPELINE_RUN, http.ids.run)}


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
    summary = http.client.get(detail, params={"hydrate": "false"})
    assert summary.status_code == 200
    assert summary.json()["body"]["archive"]["restore_run_id"] == str(
        http.ids.run
    )
    response = http.client.get(detail)
    assert (
        response.status_code == 409
        and "zenml pipeline runs unarchive" in response.text
    )
    assert (
        http.client.post(detail + "/restore").json()["outcome"] == "restored"
    )
    assert http.client.get(detail).status_code == 200
    assert http.client.post(detail + "/restore").json()["outcome"] == "noop"


@pytest.mark.parametrize(
    ("resource_attribute", "resource_type"),
    [
        ("run", MetadataResourceTypes.PIPELINE_RUN),
        ("producer", MetadataResourceTypes.STEP_RUN),
    ],
)
@pytest.mark.parametrize("archived", [False, True])
@pytest.mark.parametrize("denied_action", [None, Action.UPDATE, Action.CREATE])
def test_metadata_writes_authorize_retained_run_headers(
    http,
    storage,
    monkeypatch,
    resource_attribute,
    resource_type,
    archived,
    denied_action,
):
    """Metadata writes require owning-run and project permissions, hot or cold."""
    if archived:
        http.archive()
    resource_id = getattr(http.ids, resource_attribute)
    opened = Mock(side_effect=AssertionError("metadata read archive storage"))
    monkeypatch.setattr(storage.artifact_store, "open", opened)
    permissions = Mock(
        side_effect=lambda *, user, resources, action: {
            resource: action != denied_action for resource in resources
        }
    )
    monkeypatch.setattr(
        rbac_utils,
        "server_config",
        lambda: SimpleNamespace(rbac_enabled=True),
    )
    # Fixture runs are server-owned; exercise the non-owner permission path.
    monkeypatch.setattr(
        rbac_utils, "is_owned_by_authenticated_user", lambda _: False
    )
    monkeypatch.setattr(
        rbac_utils,
        "rbac",
        lambda: SimpleNamespace(check_permissions=permissions),
    )

    response = http.client.post(
        "/api/v1/run-metadata",
        json={
            "project": str(http.ids.project),
            "resources": [
                {"id": str(resource_id), "type": resource_type.value}
            ],
            "values": {"retained": "cold"},
            "types": {"retained": "str"},
        },
    )

    assert response.status_code == (200 if denied_action is None else 403), (
        response.text
    )
    update_check = permissions.call_args_list[0].kwargs
    assert update_check["action"] == Action.UPDATE
    assert {
        (resource.type, resource.id, resource.project_id)
        for resource in update_check["resources"]
    } == {(ResourceType.PIPELINE_RUN, http.ids.run, http.ids.project)}
    if denied_action == Action.UPDATE:
        assert permissions.call_count == 1
    else:
        assert permissions.call_count == 2
        create_check = permissions.call_args_list[1].kwargs
        assert create_check["action"] == Action.CREATE
        assert {
            (resource.type, resource.project_id)
            for resource in create_check["resources"]
        } == {(ResourceType.RUN_METADATA, http.ids.project)}
    if resource_type == MetadataResourceTypes.PIPELINE_RUN:
        resource = http.store.get_run(resource_id, hydrate=not archived)
    else:
        resource = http.store.get_run_step(resource_id, hydrate=not archived)
    assert resource.run_metadata == (
        {"retained": "cold"} if denied_action is None else {}
    )
    opened.assert_not_called()


def test_archived_snapshot_rest_updates_follow_description_semantics(http):
    """REST permits tag changes but rejects real cold-description writes."""
    http.archive()
    path = f"/api/v1/pipeline_snapshots/{http.ids.snapshot}"

    added = http.client.put(
        path,
        json={"description": None, "add_tags": ["cold-tag"]},
    )
    assert added.status_code == 200, added.text
    snapshot = PipelineSnapshotResponse.model_validate(added.json())
    assert {tag.name for tag in snapshot.tags} == {"cold-tag"}

    removed = http.client.put(
        path,
        json={"description": None, "remove_tags": ["cold-tag"]},
    )
    assert removed.status_code == 200, removed.text
    snapshot = PipelineSnapshotResponse.model_validate(removed.json())
    assert snapshot.tags == []

    noop = http.client.put(path, json={"description": ""})
    assert noop.status_code == 200, noop.text

    blocked = http.client.put(path, json={"description": "cold edit"})
    assert blocked.status_code == 409, blocked.text


def test_archived_http_summaries_and_logs_need_no_storage(
    http, storage, monkeypatch
):
    """SQL-backed archive browsing and log lookup survive a storage outage."""
    with Session(http.store.engine) as session:
        session.add_all(
            [
                LogsSchema(
                    project_id=http.ids.project,
                    pipeline_run_id=http.ids.run,
                    source="orchestrator",
                    uri="test://run.log",
                ),
                LogsSchema(
                    project_id=http.ids.project,
                    step_run_id=http.ids.producer,
                    source="step",
                    uri="test://step.log",
                ),
            ]
        )
        session.commit()
    http.archive()
    opened = Mock(side_effect=OSError("storage unavailable"))
    monkeypatch.setattr(storage.artifact_store, "open", opened)
    fetched = Mock(return_value=[])
    monkeypatch.setattr(runs_endpoints, "fetch_logs", fetched)
    monkeypatch.setattr(steps_endpoints, "fetch_logs", fetched)

    summaries = [
        f"runs/{http.ids.run}?hydrate=false",
        f"steps/{http.ids.producer}?hydrate=false",
        f"pipeline_snapshots/{http.ids.snapshot}?hydrate=false",
    ]
    for path in summaries:
        response = http.client.get("/api/v1/" + path)
        assert response.status_code == 200, response.text
        assert response.json()["body"]["archive"] is not None

    assert (
        http.client.get(
            f"/api/v1/runs/{http.ids.run}/logs",
            params={"source": "orchestrator"},
        ).status_code
        == 200
    )
    assert (
        http.client.get(
            f"/api/v1/steps/{http.ids.producer}/logs",
            params={"source": "step"},
        ).status_code
        == 200
    )
    assert fetched.call_count == 2
    opened.assert_not_called()


@pytest.mark.parametrize("resource", ["runs", "steps", "pipeline_snapshots"])
def test_mixed_hydrated_http_pages_preserve_archive_summaries(
    http, run_factory, storage, monkeypatch, resource
):
    """Real list routes serialize hot details and cold summaries during outages."""
    run_factory(http.store, age_days=1)
    http.archive()
    opened = Mock(side_effect=OSError("archive storage unavailable"))
    monkeypatch.setattr(storage.artifact_store, "open", opened)

    response = http.client.get(
        f"/api/v1/{resource}",
        params={"project": str(http.ids.project), "hydrate": "true"},
    )

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    archived = [item for item in items if item["body"]["archive"] is not None]
    hot = [item for item in items if item["body"]["archive"] is None]
    assert archived and all(item["metadata"] is None for item in archived)
    assert hot and all(item["metadata"] is not None for item in hot)
    for item in archived:
        archive = item["body"]["archive"]
        assert archive["bundle_id"]
        if resource == "pipeline_snapshots":
            assert archive["restore_run_id"] is None
            assert archive["run_name_template"]
        else:
            assert archive["restore_run_id"] == str(http.ids.run)
            assert archive["run_metadata"] == {}
    opened.assert_not_called()


def test_archived_snapshot_detail_outlives_deleted_run(http):
    """Deleting an archived owner preserves a readable, reusable snapshot."""
    before = http.store.get_snapshot(http.ids.snapshot)
    http.archive()
    deleted = http.client.delete(f"/api/v1/runs/{http.ids.run}")
    assert deleted.status_code == 200, deleted.text

    response = http.client.get(
        f"/api/v1/pipeline_snapshots/{http.ids.snapshot}",
    )

    assert response.status_code == 200, response.text
    after = PipelineSnapshotResponse.model_validate(response.json())
    assert after.archive_bundle_id is None
    assert after.metadata == before.metadata

    run, created = http.store.get_or_create_run(
        PipelineRunRequest(
            project=http.ids.project,
            name="reuse-surviving-snapshot",
            snapshot=http.ids.snapshot,
            status=ExecutionStatus.RUNNING,
        )
    )
    assert created and run.snapshot.id == http.ids.snapshot


def test_snapshot_restore_locator_requires_run_permission(http, monkeypatch):
    """The owning restore run is disclosed only after its own read check."""
    http.archive()
    checked = []

    def verify(model, *, action):
        checked.append(model.id)
        if model.id == http.ids.run:
            raise HTTPException(403, "Forbidden")

    monkeypatch.setattr(endpoint_utils, "verify_permission_for_model", verify)

    response = http.client.get(
        f"/api/v1/pipeline_snapshots/{http.ids.snapshot}",
        params={"hydrate": "false"},
    )

    assert response.status_code == 403, response.text
    assert checked == [http.ids.snapshot, http.ids.run]


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "runs/{run}"),
        ("GET", "runs/{run}/pipeline-configuration"),
        ("GET", "runs/{run}/dag"),
        ("GET", "steps/{producer}"),
        ("GET", "steps/{producer}/step-configuration"),
        ("GET", "pipeline_snapshots/{snapshot}"),
        ("POST", "runs/{run}/replay"),
    ],
)
def test_cold_configuration_and_replay_require_restore(http, method, path):
    """Operations that need archived definitions consistently return 409."""
    http.archive()

    response = http.client.request(
        method, "/api/v1/" + path.format(**http.ids.model_dump())
    )

    assert response.status_code == 409, response.text
    assert str(http.ids.run) in response.text


def test_archiving_an_active_run_is_refused_with_a_reason(http):
    """Execution-safety rules apply to every manual request."""
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


def test_archive_dry_run_uses_read_permission(http, monkeypatch):
    """A preview authorizes as a read before dispatching to the store."""
    denied = Mock(side_effect=HTTPException(403, "Forbidden"))
    monkeypatch.setattr(
        retention_endpoints, "batch_verify_permissions_for_models", denied
    )

    response = http.client.post(
        "/api/v1/retention/archive",
        json={"run_ids": [str(http.ids.run)], "dry_run": True},
    )

    assert response.status_code == 403
    assert denied.call_args.kwargs["action"] == Action.READ


def test_pipeline_permission_does_not_archive_its_runs(http, monkeypatch):
    """Runs are authorized themselves, not through the pipeline above them."""
    verified = []

    def deny_runs(models, action):
        verified.extend(model.id for model in models)
        raise HTTPException(403, "Forbidden")

    monkeypatch.setattr(
        retention_endpoints, "verify_permission_for_model", Mock()
    )
    monkeypatch.setattr(
        retention_endpoints, "batch_verify_permissions_for_models", deny_runs
    )

    response = http.client.post(
        "/api/v1/retention/archive",
        json={"pipeline_id": str(http.ids.pipeline)},
    )

    assert response.status_code == 403, response.text
    assert verified == [http.ids.run]
    assert http.store.get_run_header(http.ids.run).archive_bundle_id is None


def test_force_needs_a_server_admin(http):
    """Only an admin can set aside the policy an admin configured."""
    editor = http.store.list_users(UserFilter()).items[0].model_copy(deep=True)
    editor.body.is_admin = False
    http.client.app.dependency_overrides[authorize] = lambda: AuthContext(
        user=editor
    )

    forced = http.client.post(
        "/api/v1/retention/archive",
        json={"run_ids": [str(http.ids.run)], "force": True},
    )
    unforced = http.client.post(
        "/api/v1/retention/archive",
        json={"run_ids": [str(http.ids.run)]},
    )

    assert forced.status_code == 403, forced.text
    assert "server admins" in forced.text
    assert unforced.status_code == 200, unforced.text


def test_paused_archive_request_is_not_advertised_as_retryable(
    http, monkeypatch
):
    """An intentional pause is a 409 and keeps explicit restore available."""
    http.archive()
    monkeypatch.setenv("ZENML_SERVER_ARCHIVE__ENABLED", "false")
    archive = http.client.post(
        "/api/v1/retention/archive",
        json={"run_ids": [str(http.ids.run)], "force": True},
    )

    assert archive.status_code == 409
    assert "Retry-After" not in archive.headers
    restored = http.client.post(f"/api/v1/runs/{http.ids.run}/restore")
    assert restored.status_code == 200
    assert restored.json()["outcome"] == "restored"


def test_retention_capacity_returns_actionable_busy_response(
    http, monkeypatch
):
    """A replica at its retention capacity says so instead of queueing."""
    capacity = RetentionCapacity(1)
    monkeypatch.setattr(utils, "_retention_capacity", capacity)

    with capacity.claim():
        response = http.client.post(
            "/api/v1/retention/archive",
            json={"run_ids": [str(http.ids.run)]},
        )

    assert response.status_code == 429, response.text


def test_archived_run_and_snapshot_delete_over_http(http):
    """REST deletion authorizes from SQL headers, run before snapshot."""
    http.archive()
    snapshot = f"/api/v1/pipeline_snapshots/{http.ids.snapshot}"

    assert http.client.delete(snapshot).status_code == 409
    assert (
        http.client.delete(f"/api/v1/runs/{http.ids.run}").status_code == 200
    )
    assert http.client.delete(snapshot).status_code == 200


def test_archived_run_delete_preserves_run_when_storage_is_unavailable(
    http, storage, monkeypatch
):
    """Deletion cannot orphan snapshot detail when restoration fails."""
    http.archive()
    monkeypatch.setattr(
        storage,
        "read",
        Mock(
            side_effect=ExecutionRetentionUnavailableError(
                "Storage unavailable"
            )
        ),
    )

    response = http.client.delete(f"/api/v1/runs/{http.ids.run}")

    assert response.status_code == 503, response.text
    assert http.store.get_run(http.ids.run, hydrate=False).archive_bundle_id


def test_misspelled_archive_control_field_is_rejected(http):
    """A typo in `dry_run` cannot turn a preview into a real archive."""
    response = http.client.post(
        "/api/v1/retention/archive",
        json={"run_ids": [str(http.ids.run)], "dry_run_": True},
    )

    assert response.status_code == 422, response.text
    assert http.store.get_run(http.ids.run).archive_bundle_id is None


@pytest.mark.parametrize("storage_fails", [False, True])
def test_run_delete_cleans_archive_after_commit(
    http, storage, monkeypatch, storage_fails
):
    """Delete commits first; storage failure keeps a retryable catalog entry."""
    from pathlib import Path

    from sqlmodel import select

    from zenml.zen_stores.schemas import ArchiveBundleSchema

    http.archive()
    with Session(http.store.engine) as session:
        bundle = session.exec(select(ArchiveBundleSchema)).one()
        bundle_id, uri = bundle.id, bundle.uri
    original_remove = storage.remove

    def remove_after_commit(path):
        with pytest.raises(KeyError):
            http.store.get_run_header(http.ids.run)
        assert (
            http.store.get_snapshot(http.ids.snapshot).archive_bundle_id
            is None
        )
        return False if storage_fails else original_remove(path)

    remove = Mock(side_effect=remove_after_commit)
    monkeypatch.setattr(storage, "remove", remove)
    response = http.client.delete(f"/api/v1/runs/{http.ids.run}")
    assert response.status_code == 200, response.text
    remove.assert_called_once_with(uri)
    assert Path(uri).exists() == storage_fails
    with Session(http.store.engine) as session:
        assert (
            session.get(ArchiveBundleSchema, bundle_id) is not None
        ) == storage_fails
    if storage_fails:
        monkeypatch.setattr(storage, "remove", original_remove)
        http.retention.delete_unused_archive_objects()
        assert not Path(uri).exists()
        with Session(http.store.engine) as session:
            assert session.get(ArchiveBundleSchema, bundle_id) is None


def test_failed_run_delete_does_not_remove_archive(http, storage, monkeypatch):
    """A failed SQL deletion must never schedule removal of the archive."""
    http.archive()
    remove = Mock(wraps=storage.remove)
    monkeypatch.setattr(storage, "remove", remove)
    monkeypatch.setattr(
        type(http.store),
        "delete_run",
        Mock(side_effect=RuntimeError("delete failed")),
    )
    response = http.client.delete(f"/api/v1/runs/{http.ids.run}")
    assert response.status_code == 500
    remove.assert_not_called()


def test_project_delete_keeps_uris_until_async_cleanup(
    http, storage, archive_request, NOW, monkeypatch
):
    """Project cascades keep catalog URIs until their objects are removed."""
    from datetime import timedelta
    from pathlib import Path

    from sqlmodel import select

    from tests.unit.zen_stores.retention.fixture_graph import (
        graph_rows,
        insert_rows,
    )
    from zenml.models import ArchiveRequest, ProjectRequest
    from zenml.zen_stores.schemas import ArchiveBundleSchema

    project = http.store.create_project(
        ProjectRequest(name=f"delete-{uuid4()}")
    )
    graph = graph_rows(project.id, NOW - timedelta(days=100), "static")
    insert_rows(http.store, graph)
    run_id = graph["pipeline_run"][0]["id"]
    assert archive_request(ArchiveRequest(run_ids=[run_id])).archived == 1
    with Session(http.store.engine) as session:
        bundle = session.exec(
            select(ArchiveBundleSchema).where(
                ArchiveBundleSchema.run_id == run_id
            )
        ).one()
        uri = bundle.uri
    original_remove = storage.remove

    def remove_after_commit(path):
        with pytest.raises(KeyError):
            http.store.get_project(project.id)
        with Session(http.store.engine) as session:
            row = session.get(ArchiveBundleSchema, bundle.id)
            assert row.project_id is None and row.run_id is None
        return original_remove(path)

    monkeypatch.setattr(storage, "remove", remove_after_commit)
    response = http.client.delete(f"/api/v1/projects/{project.id}")
    assert response.status_code == 200, response.text
    assert not Path(uri).exists()
