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
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from pydantic import SecretStr

from zenml.constants import API, VERSION_1, WEBHOOKS
from zenml.dispatcher import EventDispatcher
from zenml.webhooks import (
    ParsedWebhookDelivery,
    ParsedWebhookEvent,
    WebhookAuthenticationError,
    WebhookEvent,
    WebhookEventHandler,
    WebhookIntakeResponse,
    WebhookPayloadError,
)
from zenml.webhooks.providers.github import GitHubWebhookProvider
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.routers import webhook_endpoints as endpoints


def test_webhook_routers_use_public_webhook_prefix() -> None:
    """Management and intake endpoints share the public webhook prefix."""
    expected_prefix = API + VERSION_1 + WEBHOOKS

    assert endpoints.management_router.prefix == expected_prefix
    assert endpoints.intake_router.prefix == expected_prefix


def test_get_raw_webhook_event_inherits_webhook_read_permission(
    monkeypatch,
) -> None:
    """Raw payload reads authorize against their owning webhook."""
    webhook_id = uuid4()
    webhook = SimpleNamespace(id=webhook_id)
    store = Mock()
    store.get_webhook.return_value = webhook
    store.get_raw_webhook_event.return_value = {"body": {"action": "push"}}
    verify = Mock()
    monkeypatch.setattr(endpoints, "zen_store", lambda: store)
    monkeypatch.setattr(endpoints, "verify_permission_for_model", verify)

    result = endpoints.get_raw_webhook_event.__wrapped__(
        webhook_id=webhook_id,
        delivery_id="delivery/with/provider/characters",
        _=Mock(),
    )

    assert result == {"body": {"action": "push"}}
    store.get_webhook.assert_called_once_with(webhook_id, hydrate=False)
    verify.assert_called_once_with(model=webhook, action=Action.READ)
    store.get_raw_webhook_event.assert_called_once_with(
        webhook_id=webhook_id,
        delivery_id="delivery/with/provider/characters",
    )


def test_unknown_webhook_provider_is_hidden_before_body_read() -> None:
    """Unknown provider paths return not found without reading the body."""
    request = _Request(headers={})

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            endpoints.receive_webhook_event(
                webhook_type="unknown",
                webhook_id=uuid4(),
                request=request,
            )
        )

    assert error.value.status_code == status.HTTP_404_NOT_FOUND
    assert request.body_calls == 0


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
                    webhook_type="github",
                    webhook_id=uuid4(),
                    request=request,
                )
            )
        assert error.value.status_code == expected_status
    else:
        response = asyncio.run(
            endpoints.receive_webhook_event(
                webhook_type="github",
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
        parsed_event: bool = True,
        response: WebhookIntakeResponse | None = None,
    ) -> None:
        self.auth_error = auth_error
        self.payload_error = payload_error
        self.parsed_event = parsed_event
        self.response = response or WebhookIntakeResponse()
        self.authenticate_calls = 0
        self.parse_calls = 0

    def authenticate(self, body, headers, secret):
        self.authenticate_calls += 1
        if self.auth_error:
            raise self.auth_error

    def parse_delivery(self, body, headers):
        self.parse_calls += 1
        if self.payload_error:
            raise self.payload_error
        return ParsedWebhookDelivery(
            event=(
                ParsedWebhookEvent(
                    event_type="pipeline.ready",
                    delivery_id="delivery-id",
                    payload={"event": "ready"},
                )
                if self.parsed_event
                else None
            ),
            response=self.response,
        )


class _Handler(WebhookEventHandler):
    def __init__(self) -> None:
        self.events = []

    def handle_webhook_event(self, event: WebhookEvent) -> None:
        self.events.append(event)


def _install_dependencies(monkeypatch, store: _Store, provider: _Provider):
    monkeypatch.setattr(endpoints, "zen_store", lambda: store)
    monkeypatch.setattr(endpoints, "get_webhook_provider", lambda _: provider)


def _receive(webhook_id):
    return endpoints._receive_webhook_event(
        webhook_type="custom",
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
        ("github", True, None, None, 404, None, None),
        (
            "custom",
            True,
            WebhookAuthenticationError("bad auth"),
            None,
            401,
            "auth_failed",
            "bad auth",
        ),
        (
            "custom",
            False,
            WebhookAuthenticationError("bad auth"),
            None,
            401,
            None,
            None,
        ),
        ("custom", False, None, None, 409, None, None),
        (
            "custom",
            True,
            None,
            WebhookPayloadError("bad payload"),
            400,
            "invalid_payload",
            "bad payload",
        ),
        ("custom", True, None, None, 202, "accepted", None),
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
    stored_type: str | None,
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
    handler = _Handler()
    dispatcher = EventDispatcher()
    dispatcher.register_event_handler(handler)

    response = None
    try:
        if expected_status == status.HTTP_202_ACCEPTED:
            response = _receive(webhook_id)
            assert response.status_code == expected_status
        else:
            with pytest.raises(HTTPException) as error:
                _receive(webhook_id)
            assert error.value.status_code == expected_status
            if auth_error is not None:
                assert error.value.detail == "Invalid webhook authentication."

        resolved = stored_type == "custom"
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
            assert response is not None
            assert handler.events == []
            assert response.background is not None
            asyncio.run(response.background())
            assert len(handler.events) == 1
            event = handler.events[0]
            assert event.project_id == store.project_id
            assert event.webhook_id == webhook_id
            assert event.webhook_type == "custom"
            assert event.event_type == "pipeline.ready"
            assert event.delivery_id == "delivery-id"
            assert event.payload == {"event": "ready"}
        else:
            assert handler.events == []
    finally:
        dispatcher.unregister_event_handler(handler)


def test_control_delivery_returns_provider_response_without_dispatch(
    monkeypatch,
) -> None:
    """Accepted control deliveries can return a body without an event."""
    webhook_id = uuid4()
    store = _Store(
        webhook=SimpleNamespace(webhook_type="control", active=True)
    )
    provider = _Provider(
        parsed_event=False,
        response=WebhookIntakeResponse(
            status_code=200,
            body="challenge-value",
            media_type="text/plain",
        ),
    )
    _install_dependencies(monkeypatch, store, provider)

    response = endpoints._receive_webhook_event(
        webhook_type="control",
        webhook_id=webhook_id,
        body=b'{"type":"url_verification"}',
        headers={},
    )

    assert response.status_code == 200
    assert response.body == b"challenge-value"
    assert response.media_type == "text/plain"
    assert response.background is None
    assert len(store.records) == 1
    assert store.records[0][1].accepted is True


def test_receive_webhook_event_generates_missing_delivery_id(
    monkeypatch,
) -> None:
    """Accepted events always receive a stable lookup ID before dispatch."""
    webhook_id = uuid4()
    store = _Store(webhook=SimpleNamespace(webhook_type="custom", active=True))
    provider = _Provider()
    original_parse = provider.parse_delivery

    def parse_without_delivery_id(body, headers):
        parsed = original_parse(body, headers)
        if parsed.event is not None:
            parsed.event.delivery_id = None
        return parsed

    provider.parse_delivery = parse_without_delivery_id
    _install_dependencies(monkeypatch, store, provider)
    handler = _Handler()
    dispatcher = EventDispatcher()
    dispatcher.register_event_handler(handler)

    try:
        response = _receive(webhook_id)
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.background is not None
        asyncio.run(response.background())
        assert len(handler.events) == 1
        assert handler.events[0].delivery_id is not None
    finally:
        dispatcher.unregister_event_handler(handler)
