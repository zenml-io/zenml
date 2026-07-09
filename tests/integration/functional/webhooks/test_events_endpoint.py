import hashlib
import hmac
from uuid import uuid4

import pytest
import requests

from tests.integration.functional.utils import sample_name
from zenml.enums import WebhookType
from zenml.zen_stores.rest_zen_store import RestZenStore


def _require_rest_store(clean_client) -> RestZenStore:
    store = clean_client.zen_store
    if not isinstance(store, RestZenStore):
        pytest.skip("Webhook intake endpoint tests require a REST store.")
    return store


def _signature(secret: str, body: bytes) -> str:
    return (
        "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    )


def _post_webhook(
    store: RestZenStore,
    endpoint_path: str,
    body: bytes,
    headers: dict[str, str],
) -> requests.Response:
    return requests.post(
        store.url + endpoint_path,
        data=body,
        headers=headers,
        timeout=31,
    )


def test_webhook_intake_accepts_valid_custom_delivery(clean_client):
    store = _require_rest_store(clean_client)
    result = clean_client.create_webhook_integration(
        name=sample_name("webhook-intake-valid"),
        webhook_type=WebhookType.CUSTOM,
    )
    integration = result.integration
    assert result.secret is not None
    secret = result.secret.get_secret_value()
    body = b'{"pipeline":"training"}'

    try:
        response = _post_webhook(
            store=store,
            endpoint_path=integration.endpoint_path,
            body=body,
            headers={
                "X-ZenML-Event": "pipeline.ready",
                "X-ZenML-Delivery": "delivery-1",
                "X-ZenML-Signature-256": _signature(secret, body),
            },
        )

        assert response.status_code == 202
        assert response.content == b""

        updated = clean_client.get_webhook_integration(integration.id)
        assert updated.stats.received_count == 1
        assert updated.stats.accepted_count == 1
        assert updated.stats.auth_failed_count == 0
        assert updated.stats.invalid_payload_count == 0
        assert updated.stats.last_received_at is not None
        assert updated.stats.last_accepted_at is not None
    finally:
        clean_client.delete_webhook_integration(integration.id)


def test_webhook_intake_records_auth_failures_for_active_integrations(
    clean_client,
):
    store = _require_rest_store(clean_client)
    result = clean_client.create_webhook_integration(
        name=sample_name("webhook-intake-auth"),
        webhook_type=WebhookType.CUSTOM,
    )
    integration = result.integration
    body = b'{"pipeline":"training"}'

    try:
        response = _post_webhook(
            store=store,
            endpoint_path=integration.endpoint_path,
            body=body,
            headers={
                "X-ZenML-Event": "pipeline.ready",
                "X-ZenML-Signature-256": "sha256=invalid",
            },
        )

        assert response.status_code == 401

        updated = clean_client.get_webhook_integration(integration.id)
        assert updated.stats.received_count == 1
        assert updated.stats.accepted_count == 0
        assert updated.stats.auth_failed_count == 1
        assert updated.stats.invalid_payload_count == 0
        assert updated.stats.last_error_at is not None
        assert updated.stats.last_error_summary == "Invalid webhook signature."
    finally:
        clean_client.delete_webhook_integration(integration.id)


def test_webhook_intake_records_invalid_payload_after_auth(clean_client):
    store = _require_rest_store(clean_client)
    result = clean_client.create_webhook_integration(
        name=sample_name("webhook-intake-payload"),
        webhook_type=WebhookType.CUSTOM,
    )
    integration = result.integration
    assert result.secret is not None
    secret = result.secret.get_secret_value()
    body = b"not-json"

    try:
        response = _post_webhook(
            store=store,
            endpoint_path=integration.endpoint_path,
            body=body,
            headers={
                "X-ZenML-Event": "pipeline.ready",
                "X-ZenML-Signature-256": _signature(secret, body),
            },
        )

        assert response.status_code == 400

        updated = clean_client.get_webhook_integration(integration.id)
        assert updated.stats.received_count == 1
        assert updated.stats.accepted_count == 0
        assert updated.stats.auth_failed_count == 0
        assert updated.stats.invalid_payload_count == 1
        assert updated.stats.last_error_at is not None
        assert (
            updated.stats.last_error_summary
            == "Request body must be valid JSON."
        )
    finally:
        clean_client.delete_webhook_integration(integration.id)


def test_webhook_intake_rejects_inactive_integration_without_stats(
    clean_client,
):
    store = _require_rest_store(clean_client)
    result = clean_client.create_webhook_integration(
        name=sample_name("webhook-intake-inactive"),
        webhook_type=WebhookType.CUSTOM,
        active=False,
    )
    integration = result.integration
    assert result.secret is not None
    secret = result.secret.get_secret_value()
    body = b'{"pipeline":"training"}'

    try:
        response = _post_webhook(
            store=store,
            endpoint_path=integration.endpoint_path,
            body=body,
            headers={
                "X-ZenML-Event": "pipeline.ready",
                "X-ZenML-Signature-256": _signature(secret, body),
            },
        )

        assert response.status_code == 409

        updated = clean_client.get_webhook_integration(integration.id)
        assert updated.stats.received_count == 0
        assert updated.stats.accepted_count == 0
        assert updated.stats.auth_failed_count == 0
        assert updated.stats.invalid_payload_count == 0
    finally:
        clean_client.delete_webhook_integration(integration.id)


def test_webhook_intake_does_not_record_type_mismatch(clean_client):
    store = _require_rest_store(clean_client)
    result = clean_client.create_webhook_integration(
        name=sample_name("webhook-intake-mismatch"),
        webhook_type=WebhookType.CUSTOM,
    )
    integration = result.integration
    endpoint_path = integration.endpoint_path.replace("/custom/", "/github/")

    try:
        response = _post_webhook(
            store=store,
            endpoint_path=endpoint_path,
            body=b'{"pipeline":"training"}',
            headers={},
        )

        assert response.status_code == 404

        updated = clean_client.get_webhook_integration(integration.id)
        assert updated.stats.received_count == 0
        assert updated.stats.accepted_count == 0
        assert updated.stats.auth_failed_count == 0
        assert updated.stats.invalid_payload_count == 0
    finally:
        clean_client.delete_webhook_integration(integration.id)


def test_webhook_intake_returns_not_found_for_unknown_integration(
    clean_client,
):
    store = _require_rest_store(clean_client)
    response = _post_webhook(
        store=store,
        endpoint_path=f"/api/v1/webhooks/custom/{uuid4()}/events",
        body=b'{"pipeline":"training"}',
        headers={},
    )

    assert response.status_code == 404
