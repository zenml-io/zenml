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
"""Tests for the REST ZenML store."""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace
from typing import Dict, Iterator, Optional
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from zenml.enums import TriggerRunConcurrency
from zenml.exceptions import (
    ExecutionRetentionUnavailableError,
    IllegalOperationError,
)
from zenml.models import ArchiveRequest, WebhookTriggerUpdate
from zenml.zen_stores.rest_zen_store import (
    ARTIFACT_VERSIONS,
    TRIGGERS,
    WEBHOOKS,
    RestZenStore,
    RestZenStoreConfiguration,
)

SERVER_URL = "https://server.example"
SERVER_URL_WITH_SLASH = f"{SERVER_URL}/"


@contextmanager
def serve(
    status: int,
    body: bytes = b"",
    headers: Optional[Dict[str, str]] = None,
    succeed_after: Optional[int] = None,
) -> Iterator[SimpleNamespace]:
    """Serve one canned response on a local port and count the requests.

    Args:
        status: Status of the canned response.
        body: JSON body of the canned response.
        headers: Extra headers of the canned response.
        succeed_after: Number of requests after which the server answers 200.

    Yields:
        The REST store pointed at the server, its URL, and the request count.
    """
    served = SimpleNamespace(attempts=0)
    headers = headers or {}

    class Handler(BaseHTTPRequestHandler):
        def respond(self) -> None:
            served.attempts += 1
            recovered = (
                succeed_after is not None and served.attempts > succeed_after
            )
            self.send_response(200 if recovered else status)
            for header, value in headers.items():
                self.send_header(header, value)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = respond
        do_POST = respond

        def log_message(self, format: str, *args: object) -> None:
            """Suppress local HTTP server logs during the unit test."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        served.url = f"http://127.0.0.1:{server.server_port}"
        served.store = RestZenStore.model_construct(
            config=RestZenStoreConfiguration(url=served.url)
        )
        served.store._api_token = None
        yield served
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_ordinary_session_retries_a_transient_status() -> None:
    """Requests outside execution retention keep their status retries."""
    with serve(503, succeed_after=1) as served:
        response = served.store.session.get(f"{served.url}/any", timeout=2)

    assert response.status_code == 200
    assert served.attempts == 2


def test_retention_request_is_not_retried() -> None:
    """A retention failure reaches the caller at once, as a typed error.

    The server sends `Retry-After` with this error, which urllib3 would
    otherwise honor even for a status it was not told to retry.
    """
    body = (
        b'{"detail":["ExecutionRetentionUnavailableError",'
        b'"storage unavailable"]}'
    )
    with serve(503, body, headers={"Retry-After": "1"}) as served:
        with pytest.raises(ExecutionRetentionUnavailableError):
            served.store.archive_runs(ArchiveRequest(run_ids=[uuid4()]))

    assert served.attempts == 1


@pytest.mark.parametrize(
    ("status", "body", "call"),
    [
        (
            405,
            b'{"detail":"Method Not Allowed"}',
            lambda store: store.restore_pipeline_run(uuid4()),
        ),
        (
            404,
            b'{"detail":"Not Found"}',
            lambda store: store.get_retention_status(),
        ),
    ],
)
def test_server_without_retention_routes_is_named_as_such(
    status, body, call
) -> None:
    """An older server's answer is not mistaken for a missing run.

    Its GET catch-all for unknown API paths turns a POST into a 405 and a
    GET into a 404 without a ZenML error.
    """
    with serve(status, body) as served:
        with pytest.raises(IllegalOperationError, match="does not support"):
            call(served.store)


def test_missing_run_is_still_a_key_error() -> None:
    """A retention route that cannot find the run keeps saying so."""
    with serve(
        404, b'{"detail":["KeyError","Run does not exist."]}'
    ) as served:
        with pytest.raises(KeyError, match="does not exist"):
            served.store.restore_pipeline_run(uuid4())


def test_rest_store_url_is_normalized_before_moving_credentials(
    mocker: MockerFixture,
) -> None:
    """Tests that REST store API tokens use the normalized server URL."""
    credentials_store = mocker.Mock()
    mocker.patch(
        "zenml.zen_stores.rest_zen_store.get_credentials_store",
        return_value=credentials_store,
    )

    config = RestZenStoreConfiguration(
        url=SERVER_URL_WITH_SLASH,
        api_token="test-api-token",
    )

    assert config.url == SERVER_URL
    credentials_store.set_bare_token.assert_called_once_with(
        SERVER_URL, "test-api-token"
    )


def test_delete_artifact_version_can_request_server_side_data_deletion(
    mocker: MockerFixture,
) -> None:
    """Tests forwarding artifact data deletion to the server."""
    store = mocker.Mock()
    artifact_version_id = uuid4()

    RestZenStore.delete_artifact_version_server_side(
        store,
        artifact_version_id=artifact_version_id,
        delete_from_artifact_store=True,
    )

    store._delete_resource.assert_called_once_with(
        resource_id=artifact_version_id,
        route=ARTIFACT_VERSIONS,
        params={
            "delete_metadata": True,
            "delete_from_artifact_store": True,
        },
    )


def test_delete_artifact_version_can_preserve_metadata(
    mocker: MockerFixture,
) -> None:
    """Tests requesting data deletion without metadata deletion."""
    store = mocker.Mock()
    artifact_version_id = uuid4()

    RestZenStore.delete_artifact_version_server_side(
        store,
        artifact_version_id=artifact_version_id,
        delete_metadata=False,
        delete_from_artifact_store=True,
    )

    store._delete_resource.assert_called_once_with(
        resource_id=artifact_version_id,
        route=ARTIFACT_VERSIONS,
        params={
            "delete_metadata": False,
            "delete_from_artifact_store": True,
        },
    )


def test_webhook_trigger_updates_use_full_serialization(
    mocker: MockerFixture,
) -> None:
    """Tests that webhook trigger PUT requests include the complete model."""
    store = mocker.Mock()
    trigger_id = uuid4()
    trigger_update = WebhookTriggerUpdate(
        name="webhook-trigger",
        active=True,
        concurrency=TriggerRunConcurrency.SKIP,
        configuration={"target_events": []},
    )
    store.put.return_value = {}

    with pytest.raises(ValueError, match="Bad response"):
        RestZenStore.update_trigger(
            store,
            trigger_id=trigger_id,
            trigger_update=trigger_update,
        )

    store.put.assert_called_once_with(
        f"{TRIGGERS}/{trigger_id}",
        body=trigger_update,
        params=None,
        exclude_unset=False,
    )


def test_get_raw_webhook_event_uses_delivery_query_parameter(
    mocker: MockerFixture,
) -> None:
    """Provider delivery IDs are not interpolated into URL path segments."""
    store = mocker.Mock()
    webhook_id = uuid4()
    store.get.return_value = {"body": {"message": "hello"}}

    result = RestZenStore.get_raw_webhook_event(
        store,
        webhook_id=webhook_id,
        delivery_id="provider/id:with,characters",
    )

    assert result == {"body": {"message": "hello"}}
    store.get.assert_called_once_with(
        f"{WEBHOOKS}/{webhook_id}/events/raw",
        params={"delivery_id": "provider/id:with,characters"},
    )
