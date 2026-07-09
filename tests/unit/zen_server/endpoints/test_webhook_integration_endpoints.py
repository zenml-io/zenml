from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from zenml.enums import WebhookType
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


def test_receive_webhook_event_returns_404_for_missing_integration(
    monkeypatch,
) -> None:
    integration_id = uuid4()
    store = _Store(integration=None)
    adapter = _Adapter()
    _install_dependencies(monkeypatch, store, adapter)

    with pytest.raises(HTTPException) as error:
        _receive(integration_id)

    assert error.value.status_code == status.HTTP_404_NOT_FOUND
    assert store.secret_requests == 0
    assert store.records == []
    assert adapter.authenticate_calls == 0
    assert adapter.parse_calls == 0


def test_receive_webhook_event_returns_404_for_provider_type_mismatch(
    monkeypatch,
) -> None:
    integration_id = uuid4()
    store = _Store(
        integration=SimpleNamespace(
            webhook_type=WebhookType.GITHUB, active=True
        )
    )
    adapter = _Adapter()
    _install_dependencies(monkeypatch, store, adapter)

    with pytest.raises(HTTPException) as error:
        _receive(integration_id)

    assert error.value.status_code == status.HTTP_404_NOT_FOUND
    assert store.secret_requests == 0
    assert store.records == []
    assert adapter.authenticate_calls == 0
    assert adapter.parse_calls == 0


def test_receive_webhook_event_records_auth_failure_for_active_integration(
    monkeypatch,
) -> None:
    integration_id = uuid4()
    store = _Store(
        integration=SimpleNamespace(
            webhook_type=WebhookType.CUSTOM, active=True
        )
    )
    adapter = _Adapter(auth_error=WebhookAuthenticationError("bad auth"))
    _install_dependencies(monkeypatch, store, adapter)

    with pytest.raises(HTTPException) as error:
        _receive(integration_id)

    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert store.secret_requests == 1
    assert len(store.records) == 1
    recorded_id, update = store.records[0]
    assert recorded_id == integration_id
    assert update.auth_failed is True
    assert update.error_summary == "bad auth"
    assert adapter.authenticate_calls == 1
    assert adapter.parse_calls == 0


def test_receive_webhook_event_does_not_record_auth_failure_for_inactive_integration(
    monkeypatch,
) -> None:
    integration_id = uuid4()
    store = _Store(
        integration=SimpleNamespace(
            webhook_type=WebhookType.CUSTOM, active=False
        )
    )
    adapter = _Adapter(auth_error=WebhookAuthenticationError("bad auth"))
    _install_dependencies(monkeypatch, store, adapter)

    with pytest.raises(HTTPException) as error:
        _receive(integration_id)

    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert store.secret_requests == 1
    assert store.records == []
    assert adapter.authenticate_calls == 1
    assert adapter.parse_calls == 0


def test_receive_webhook_event_returns_409_for_inactive_integration_after_auth(
    monkeypatch,
) -> None:
    integration_id = uuid4()
    store = _Store(
        integration=SimpleNamespace(
            webhook_type=WebhookType.CUSTOM, active=False
        )
    )
    adapter = _Adapter()
    _install_dependencies(monkeypatch, store, adapter)

    with pytest.raises(HTTPException) as error:
        _receive(integration_id)

    assert error.value.status_code == status.HTTP_409_CONFLICT
    assert store.secret_requests == 1
    assert store.records == []
    assert adapter.authenticate_calls == 1
    assert adapter.parse_calls == 0


def test_receive_webhook_event_records_invalid_payload_after_auth(
    monkeypatch,
) -> None:
    integration_id = uuid4()
    store = _Store(
        integration=SimpleNamespace(
            webhook_type=WebhookType.CUSTOM, active=True
        )
    )
    adapter = _Adapter(payload_error=WebhookPayloadError("bad payload"))
    _install_dependencies(monkeypatch, store, adapter)

    with pytest.raises(HTTPException) as error:
        _receive(integration_id)

    assert error.value.status_code == status.HTTP_400_BAD_REQUEST
    assert store.secret_requests == 1
    assert len(store.records) == 1
    recorded_id, update = store.records[0]
    assert recorded_id == integration_id
    assert update.invalid_payload is True
    assert update.error_summary == "bad payload"
    assert adapter.authenticate_calls == 1
    assert adapter.parse_calls == 1


def test_receive_webhook_event_records_accepted_event(monkeypatch) -> None:
    integration_id = uuid4()
    store = _Store(
        integration=SimpleNamespace(
            webhook_type=WebhookType.CUSTOM, active=True
        )
    )
    adapter = _Adapter()
    _install_dependencies(monkeypatch, store, adapter)

    response = _receive(integration_id)

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert store.secret_requests == 1
    assert len(store.records) == 1
    recorded_id, update = store.records[0]
    assert recorded_id == integration_id
    assert update.accepted is True
    assert adapter.authenticate_calls == 1
    assert adapter.parse_calls == 1
