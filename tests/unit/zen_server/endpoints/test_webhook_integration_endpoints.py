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
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from pydantic import SecretStr

from zenml.enums import WebhookType
from zenml.models import WebhookIntegrationUpdate
from zenml.webhooks import WebhookAuthenticationError, WebhookPayloadError
from zenml.zen_server.routers import webhook_integration_endpoints as endpoints


class _Store:
    def __init__(self, integration: SimpleNamespace | None) -> None:
        self.integration = integration
        self.secret_requests = 0
        self.records = []

    def get_webhook_integration(self, integration_id):
        if self.integration is None:
            raise KeyError(integration_id)
        return self.integration

    def get_webhook_integration_secret(self, integration_id):
        self.secret_requests += 1
        return "webhook-secret"

    def record_webhook_event(self, integration_id, update):
        self.records.append((integration_id, update))


class _Adapter:
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


def _install_dependencies(monkeypatch, store: _Store, adapter: _Adapter):
    monkeypatch.setattr(endpoints, "zen_store", lambda: store)
    monkeypatch.setattr(endpoints, "get_webhook_adapter", lambda _: adapter)


def _receive(integration_id):
    return endpoints._receive_webhook_event(
        webhook_type=WebhookType.CUSTOM,
        integration_id=integration_id,
        body=b'{"event":"ready"}',
        headers={},
    )


def test_verify_webhook_secret_reference_access_checks_value_permission(
    monkeypatch,
) -> None:
    """Referenced credentials require permission to read the secret value."""
    referenced_secret = SimpleNamespace(name="webhook-secret")
    store = SimpleNamespace(
        get_secret_by_name_or_id=lambda name: referenced_secret
    )
    verified = []
    monkeypatch.setattr(endpoints, "zen_store", lambda: store)
    monkeypatch.setattr(
        endpoints,
        "verify_permission_for_model",
        lambda **kwargs: verified.append(kwargs),
    )

    endpoints._verify_webhook_secret_reference_access(
        SecretStr("{{webhook-secret.key}}")
    )

    assert verified == [
        {
            "model": referenced_secret,
            "action": endpoints.Action.READ_SECRET_VALUE,
        }
    ]


def test_update_checks_integration_permission_before_secret_access(
    monkeypatch,
) -> None:
    """Integration update access is checked before referenced secret access."""
    integration_id = uuid4()
    integration = SimpleNamespace(id=integration_id)
    updated_integration = SimpleNamespace(id=integration_id)
    calls = []

    class _UpdateStore:
        def get_webhook_integration(self, integration_id, hydrate):
            calls.append("get_integration")
            return integration

        def update_webhook_integration(self, integration_id, update):
            calls.append("update_integration")
            return updated_integration

    monkeypatch.setattr(endpoints, "zen_store", _UpdateStore)
    monkeypatch.setattr(
        endpoints,
        "verify_permission_for_model",
        lambda **kwargs: calls.append(f"verify_{kwargs['action'].value}"),
    )
    monkeypatch.setattr(
        endpoints,
        "_verify_webhook_secret_reference_access",
        lambda secret: calls.append("verify_secret_access"),
    )
    monkeypatch.setattr(
        endpoints,
        "dehydrate_response_model",
        lambda model: model,
    )

    result = endpoints.update_webhook_integration.__wrapped__(
        integration_id=integration_id,
        update=WebhookIntegrationUpdate(secret="{{webhook.key}}"),
        _=SimpleNamespace(),
    )

    assert result is updated_integration
    assert calls == [
        "get_integration",
        "verify_update",
        "verify_secret_access",
        "update_integration",
    ]


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
        "missing-integration",
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
    integration_id = uuid4()
    store = _Store(
        integration=(
            SimpleNamespace(webhook_type=stored_type, active=active)
            if stored_type is not None
            else None
        )
    )
    adapter = _Adapter(auth_error=auth_error, payload_error=payload_error)
    _install_dependencies(monkeypatch, store, adapter)

    if expected_status == status.HTTP_202_ACCEPTED:
        assert _receive(integration_id).status_code == expected_status
    else:
        with pytest.raises(HTTPException) as error:
            _receive(integration_id)
        assert error.value.status_code == expected_status
        if auth_error is not None:
            assert error.value.detail == "Invalid webhook authentication."

    resolved = stored_type == WebhookType.CUSTOM
    parsed = expected_status in {
        status.HTTP_202_ACCEPTED,
        status.HTTP_400_BAD_REQUEST,
    }
    assert store.secret_requests == int(resolved)
    assert adapter.authenticate_calls == int(resolved)
    assert adapter.parse_calls == int(parsed)

    if expected_outcome is None:
        assert store.records == []
    else:
        assert len(store.records) == 1
        recorded_id, update = store.records[0]
        assert recorded_id == integration_id
        assert getattr(update, expected_outcome) is True
        assert update.error_summary == expected_error
