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
"""Unit tests for public webhook webhook intake."""

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from pydantic import SecretStr

from zenml.constants import API, VERSION_1, WEBHOOKS
from zenml.enums import WebhookType
from zenml.webhooks import (
    WebhookAuthenticationError,
    WebhookPayloadError,
    register_webhook_event_consumer,
    unregister_webhook_event_consumer,
)
from zenml.webhooks.providers.github import GitHubWebhookProvider
from zenml.zen_server.routers import webhook_endpoints as endpoints


def test_webhook_routers_use_public_webhook_prefix() -> None:
    """Management and intake endpoints share the public webhook prefix."""
    expected_prefix = API + VERSION_1 + WEBHOOKS

    assert endpoints.management_router.prefix == expected_prefix
    assert endpoints.intake_router.prefix == expected_prefix


class _Request:
    def __init__(self, headers):
        self.headers = headers
        self.body_calls = 0

    async def body(self):
        self.body_calls += 1
        return b'{"event":"ready"}'


@pytest.mark.parametrize(
    "event_type, expected_status, expected_body_calls",
    [
        (None, status.HTTP_400_BAD_REQUEST, 0),
        ("push", status.HTTP_202_ACCEPTED, 1),
        ("pull_request", status.HTTP_202_ACCEPTED, 1),
    ],
)
def test_github_pre_validation_happens_before_body_and_store_io(
    monkeypatch,
    event_type: str | None,
    expected_status: int,
    expected_body_calls: int,
) -> None:
    """Reject malformed GitHub metadata before body or store access."""
    provider = GitHubWebhookProvider()
    request = _Request(
        headers={"x-github-event": event_type}
        if event_type is not None
        else {}
    )
    receive_calls = []

    async def _run_in_threadpool(function, **kwargs):
        receive_calls.append((function, kwargs))
        return endpoints.Response(status_code=status.HTTP_202_ACCEPTED)

    monkeypatch.setattr(endpoints, "get_webhook_provider", lambda _: provider)
    monkeypatch.setattr(endpoints, "run_in_threadpool", _run_in_threadpool)

    if expected_status == status.HTTP_400_BAD_REQUEST:
        with pytest.raises(HTTPException) as error:
            asyncio.run(
                endpoints.receive_webhook_event(
                    webhook_type=WebhookType.GITHUB,
                    webhook_id=uuid4(),
                    request=request,
                )
            )
        assert error.value.status_code == expected_status
    else:
        response = asyncio.run(
            endpoints.receive_webhook_event(
                webhook_type=WebhookType.GITHUB,
                webhook_id=uuid4(),
                request=request,
            )
        )
        assert response.status_code == expected_status

    assert request.body_calls == expected_body_calls
    assert len(receive_calls) == expected_body_calls


class _Store:
    def __init__(self, webhook: SimpleNamespace | None) -> None:
        self.webhook = webhook
        self.secret_requests = 0
        self.records = []
        self.secret_id = uuid4()
        self.project_id = uuid4()

    def get_webhook_intake_config(self, webhook_id, expected_webhook_type):
        if (
            self.webhook is None
            or self.webhook.webhook_type != expected_webhook_type
        ):
            raise KeyError(webhook_id)
        self.secret_requests += 1
        return SimpleNamespace(
            webhook_type=self.webhook.webhook_type,
            active=self.webhook.active,
            project_id=self.project_id,
            secret=SecretStr("webhook-secret"),
        )

    def record_webhook_event(self, webhook_id, update):
        self.records.append((webhook_id, update))


class _Provider:
    def __init__(
        self,
        auth_error: Exception | None = None,
        payload_error: Exception | None = None,
    ) -> None:
        self.auth_error = auth_error
        self.payload_error = payload_error
        self.authenticate_calls = 0
        self.parse_calls = 0

    def authenticate(self, body, headers, secret):
        self.authenticate_calls += 1
        if self.auth_error:
            raise self.auth_error

    def parse(self, body, headers):
        self.parse_calls += 1
        if self.payload_error:
            raise self.payload_error
        return SimpleNamespace(
            webhook_type=WebhookType.CUSTOM,
            event_type="pipeline.ready",
            delivery_id="delivery-id",
            payload={"event": "ready"},
        )


class _Consumer:
    def __init__(self) -> None:
        self.events = []

    def consume(self, event):
        self.events.append(event)


def _install_dependencies(monkeypatch, store: _Store, provider: _Provider):
    monkeypatch.setattr(endpoints, "zen_store", lambda: store)
    monkeypatch.setattr(endpoints, "get_webhook_provider", lambda _: provider)


def _receive(webhook_id):
    return endpoints._receive_webhook_event(
        webhook_type=WebhookType.CUSTOM,
        webhook_id=webhook_id,
        body=b'{"event":"ready"}',
        headers={},
    )


@pytest.mark.parametrize(
    (
        "stored_type",
        "active",
        "auth_error",
        "payload_error",
        "expected_status",
        "expected_outcome",
        "expected_error",
    ),
    [
        (None, None, None, None, 404, None, None),
        (WebhookType.GITHUB, True, None, None, 404, None, None),
        (
            WebhookType.CUSTOM,
            True,
            WebhookAuthenticationError("bad auth"),
            None,
            401,
            "auth_failed",
            "bad auth",
        ),
        (
            WebhookType.CUSTOM,
            False,
            WebhookAuthenticationError("bad auth"),
            None,
            401,
            None,
            None,
        ),
        (WebhookType.CUSTOM, False, None, None, 409, None, None),
        (
            WebhookType.CUSTOM,
            True,
            None,
            WebhookPayloadError("bad payload"),
            400,
            "invalid_payload",
            "bad payload",
        ),
        (WebhookType.CUSTOM, True, None, None, 202, "accepted", None),
    ],
    ids=[
        "missing-webhook",
        "provider-mismatch",
        "active-auth-failure",
        "inactive-auth-failure",
        "inactive-authenticated",
        "invalid-payload",
        "accepted",
    ],
)
def test_receive_webhook_event_decision_table(
    monkeypatch,
    stored_type: WebhookType | None,
    active: bool | None,
    auth_error: Exception | None,
    payload_error: Exception | None,
    expected_status: int,
    expected_outcome: str | None,
    expected_error: str | None,
) -> None:
    """Exercise webhook authentication, validation, and consumption paths."""
    webhook_id = uuid4()
    store = _Store(
        webhook=(
            SimpleNamespace(webhook_type=stored_type, active=active)
            if stored_type is not None
            else None
        )
    )
    provider = _Provider(auth_error=auth_error, payload_error=payload_error)
    _install_dependencies(monkeypatch, store, provider)
    consumer = _Consumer()
    register_webhook_event_consumer(consumer)

    try:
        if expected_status == status.HTTP_202_ACCEPTED:
            assert _receive(webhook_id).status_code == expected_status
        else:
            with pytest.raises(HTTPException) as error:
                _receive(webhook_id)
            assert error.value.status_code == expected_status
            if auth_error is not None:
                assert error.value.detail == "Invalid webhook authentication."
    finally:
        unregister_webhook_event_consumer(consumer)

    resolved = stored_type == WebhookType.CUSTOM
    parsed = expected_status in {
        status.HTTP_202_ACCEPTED,
        status.HTTP_400_BAD_REQUEST,
    }
    assert store.secret_requests == int(resolved)
    assert provider.authenticate_calls == int(resolved)
    assert provider.parse_calls == int(parsed)

    if expected_outcome is None:
        assert store.records == []
    else:
        assert len(store.records) == 1
        recorded_id, update = store.records[0]
        assert recorded_id == webhook_id
        assert getattr(update, expected_outcome) is True
        assert update.error_summary == expected_error

    if expected_status == status.HTTP_202_ACCEPTED:
        assert len(consumer.events) == 1
        event = consumer.events[0]
        assert event.project_id == store.project_id
        assert event.webhook_id == webhook_id
        assert event.webhook_type == WebhookType.CUSTOM
        assert event.event_type == "pipeline.ready"
        assert event.delivery_id == "delivery-id"
        assert event.payload == {"event": "ready"}
    else:
        assert consumer.events == []
