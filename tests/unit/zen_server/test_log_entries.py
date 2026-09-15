#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Regression tests for runner retrieval through both log endpoints."""

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Iterator
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from zenml.constants import LOGS_RUNNER_SOURCE
from zenml.exceptions import (
    IllegalOperationError,
    LogStoreError,
    LogStoreRateLimitError,
    LogStoreUnavailableError,
)
from zenml.models import (
    LogEntry,
    LogsEntriesResponse,
    LogsResponse,
    LogsResponseBody,
)
from zenml.zen_server import logs as runner_logs
from zenml.zen_server.auth import authorize
from zenml.zen_server.routers import logs_endpoints, runs_endpoints


class RequestManager:
    """Execute endpoint functions without a server worker pool."""

    async def execute(
        self, func: Any, deduplicate: Any, *args: Any, **kwargs: Any
    ) -> Any:
        """Execute the wrapped endpoint, including its HTTP error translation."""
        return func(*args, **kwargs)


@pytest.fixture
def endpoint(mocker: MockerFixture) -> Iterator[SimpleNamespace]:
    """Create an in-process app with mocked storage and workload I/O."""
    now = datetime(2026, 1, 2, tzinfo=timezone.utc)
    run = SimpleNamespace(
        id=uuid4(),
        trigger=None,
        source_snapshot=None,
        snapshot=SimpleNamespace(
            id=uuid4(), template_id=None, source_snapshot_id=None
        ),
    )
    logs = LogsResponse(
        id=uuid4(),
        body=LogsResponseBody(
            created=now,
            updated=now,
            project_id=uuid4(),
            user_id=uuid4(),
            source=LOGS_RUNNER_SOURCE,
            pipeline_run_id=run.id,
        ),
    )
    run.log_collection = [logs]
    store = mocker.Mock()
    store.get_logs.return_value = logs
    store.get_run.return_value = run
    mocker.patch.object(logs_endpoints, "zen_store", return_value=store)
    mocker.patch.object(runs_endpoints, "zen_store", return_value=store)
    authorize_run = mocker.patch.object(
        logs_endpoints, "verify_permission_for_model"
    )
    mocker.patch.object(
        runs_endpoints, "verify_permissions_and_get_entity", return_value=run
    )
    mocker.patch(
        "zenml.zen_server.utils.request_manager", return_value=RequestManager()
    )
    manager = mocker.Mock()
    manager.get_logs.return_value = "\n".join(
        LogEntry(message=f"runner {i}").model_dump_json() for i in range(3)
    )
    mocker.patch.object(runner_logs, "workload_manager", return_value=manager)
    mocker.patch.object(
        runner_logs,
        "server_config",
        return_value=SimpleNamespace(workload_manager_enabled=True),
    )
    normal_fetch = mocker.patch.object(
        logs_endpoints, "fetch_logs", return_value=LogsEntriesResponse()
    )
    app = FastAPI()
    app.include_router(logs_endpoints.router)
    app.include_router(runs_endpoints.router)
    app.dependency_overrides[authorize] = lambda: None
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
            logs=logs,
            run=run,
            manager=manager,
            authorize_run=authorize_run,
            normal_fetch=normal_fetch,
            url=f"/api/v1/logs/{logs.id}/entries",
            store=store,
        )


@pytest.mark.parametrize("kind", ["trigger", "snapshot", "resume"])
def test_new_and_legacy_endpoints_select_the_same_runner_workload(
    endpoint: SimpleNamespace, kind: str
) -> None:
    """Every runner launch path keeps the legacy workload ID selection."""
    if kind == "trigger":
        endpoint.run.trigger = SimpleNamespace(id=uuid4())
    elif kind == "snapshot":
        endpoint.run.source_snapshot = SimpleNamespace(id=uuid4())
    expected_id = (
        endpoint.run.snapshot.id if kind == "snapshot" else endpoint.run.id
    )
    new = endpoint.client.get(endpoint.url, params={"limit": 2})
    assert new.status_code == 200
    assert [entry["message"] for entry in new.json()["items"]] == [
        "runner 0",
        "runner 1",
    ]
    assert new.json()["before"] is None
    assert new.json()["after"] is None
    endpoint.authorize_run.assert_called_once()
    endpoint.normal_fetch.assert_not_called()
    endpoint.manager.get_logs.assert_called_once_with(workload_id=expected_id)
    for params in [
        {"source": LOGS_RUNNER_SOURCE},
        {"logs_id": str(endpoint.logs.id)},
    ]:
        old = endpoint.client.get(
            f"/api/v1/runs/{endpoint.run.id}/logs", params=params
        )
        assert old.status_code == 200
        assert [entry["message"] for entry in old.json()] == [
            "runner 0",
            "runner 1",
            "runner 2",
        ]
        endpoint.manager.get_logs.assert_called_with(workload_id=expected_id)


def test_legacy_runner_without_log_model_still_works(
    endpoint: SimpleNamespace,
) -> None:
    """Runs from before the log collection existed still expose runner logs."""
    endpoint.run.log_collection = []
    endpoint.run.snapshot.template_id = uuid4()
    response = endpoint.client.get(
        f"/api/v1/runs/{endpoint.run.id}/logs",
        params={"source": LOGS_RUNNER_SOURCE},
    )
    assert response.status_code == 200
    assert len(response.json()) == 3


@pytest.mark.parametrize(
    "params",
    [
        {"before": ""},
        {"after": "token"},
        {"start": "newest"},
        {"search": "runner"},
        {"level": "ERROR"},
        {"since": "2026-01-01"},
        {"until": "2026-01-03"},
    ],
)
def test_runner_rejects_unsupported_queries_without_fetching(
    endpoint: SimpleNamespace, params: dict[str, str]
) -> None:
    """The endpoint must not silently drop runner pagination or filters."""
    response = endpoint.client.get(endpoint.url, params=params)
    assert response.status_code == 400
    assert "Runner logs" in response.text
    endpoint.manager.get_logs.assert_not_called()


def test_runner_without_snapshot_reports_error(
    endpoint: SimpleNamespace,
) -> None:
    """Missing workloads must not look like empty successful pages."""
    endpoint.run.snapshot = None
    response = endpoint.client.get(endpoint.url)
    assert response.status_code == 400
    assert "no snapshot" in response.text
    endpoint.manager.get_logs.assert_not_called()


def test_runner_permission_checked_before_workload_access(
    endpoint: SimpleNamespace,
) -> None:
    """Runner dispatch cannot bypass the owning run's read permission."""
    endpoint.authorize_run.side_effect = IllegalOperationError("forbidden")
    assert endpoint.client.get(endpoint.url).status_code == 403
    endpoint.manager.get_logs.assert_not_called()


@pytest.mark.parametrize(
    "error,status",
    [
        (LogStoreError("invalid response"), 502),
        (LogStoreUnavailableError("unavailable"), 503),
        (LogStoreRateLimitError("rate limited", retry_after=17), 429),
    ],
)
def test_log_store_errors_have_actionable_http_status(
    endpoint: SimpleNamespace, error: Exception, status: int
) -> None:
    """Backend failures reach HTTP clients without becoming generic 500s."""
    endpoint.logs.body.source = "step"
    endpoint.normal_fetch.side_effect = error
    response = endpoint.client.get(endpoint.url)
    assert response.status_code == status
    if status == 429:
        assert response.headers["Retry-After"] == "17"


def test_datadog_cursor_and_time_bound_round_trip_over_http(
    endpoint: SimpleNamespace, mocker: MockerFixture
) -> None:
    """Wire serialization preserves the signed query and provider token."""
    from zenml.enums import StackComponentType
    from zenml.log_stores.datadog.datadog_flavor import DatadogLogStoreConfig
    from zenml.log_stores.datadog.datadog_log_store import DatadogLogStore

    now = datetime(2026, 1, 3, tzinfo=timezone.utc)
    datadog = DatadogLogStore(
        name="test",
        id=uuid4(),
        user=uuid4(),
        created=now,
        updated=now,
        config=DatadogLogStoreConfig(api_key="test", application_key="test"),
        flavor="datadog",
        type=StackComponentType.LOG_STORE,
    )
    endpoint.logs.body.source = "step"
    endpoint.logs.body.log_store_id = datadog.id

    def fetch(
        logs: LogsResponse, zen_store: Any, **kwargs: Any
    ) -> LogsEntriesResponse:
        return datadog.fetch(logs, **kwargs)

    endpoint.normal_fetch.side_effect = fetch
    event = {
        "id": "native-id",
        "attributes": {"message": "message 1", "timestamp": now.isoformat()},
    }
    post = mocker.patch(
        "zenml.log_stores.datadog.datadog_log_store.requests.post",
        return_value=SimpleNamespace(
            status_code=200,
            json=lambda: {
                "data": [event],
                "meta": {"page": {"after": "native/+=?token"}},
            },
        ),
    )
    first = endpoint.client.get(
        endpoint.url,
        params={"start": "newest", "search": "message", "limit": 50},
    )
    assert first.status_code == 200
    data = first.json()
    assert data["after"] is None
    continuation = {
        "before": data["before"],
        "until": data["until"],
        "search": "message",
        "limit": 50,
    }
    assert (
        endpoint.client.get(endpoint.url, params=continuation).status_code
        == 200
    )
    calls = post.call_args_list
    assert len(calls) == 2
    assert (
        calls[0].kwargs["json"]["filter"] == calls[1].kwargs["json"]["filter"]
    )
    assert calls[1].kwargs["json"]["page"]["cursor"] == "native/+=?token"
    continuation["search"] = "different"
    assert (
        endpoint.client.get(endpoint.url, params=continuation).status_code
        == 400
    )
    assert post.call_count == 2


@pytest.mark.parametrize("resource", ["runs", "steps"])
def test_legacy_endpoints_keep_parameters_and_list_response(
    endpoint: SimpleNamespace, mocker: MockerFixture, resource: str
) -> None:
    """Old run and step consumers can still fetch by source or log model ID."""
    from zenml.zen_server.routers import steps_endpoints

    logs = endpoint.logs
    logs.body.source = "step"
    page = LogsEntriesResponse(items=[LogEntry(message="legacy")])
    mocker.patch.object(runs_endpoints, "fetch_logs", return_value=page)
    mocker.patch.object(steps_endpoints, "fetch_logs", return_value=page)
    mocker.patch.object(
        steps_endpoints, "zen_store", return_value=endpoint.store
    )
    mocker.patch.object(steps_endpoints, "verify_permission")
    endpoint.store.get_run_step.return_value = SimpleNamespace(
        id=uuid4(),
        pipeline_run_id=endpoint.run.id,
        project_id=logs.project_id,
        log_collection=[logs],
    )
    endpoint.client.app.include_router(steps_endpoints.router)
    entity_id = (
        endpoint.run.id
        if resource == "runs"
        else endpoint.store.get_run_step.return_value.id
    )
    for params in [{"source": "step"}, {"logs_id": str(logs.id)}]:
        response = endpoint.client.get(
            f"/api/v1/{resource}/{entity_id}/logs", params=params
        )
        assert response.status_code == 200
        assert response.json() == [page.items[0].model_dump(mode="json")]
