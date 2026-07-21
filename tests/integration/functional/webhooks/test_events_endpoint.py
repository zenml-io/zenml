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
import hashlib
import hmac
from uuid import uuid4

import pytest
import requests

from tests.integration.functional.utils import sample_name
from zenml.enums import WebhookType
from zenml.models import WebhookIntegrationCreateResponse
from zenml.zen_stores.rest_zen_store import RestZenStore


def _require_rest_store(clean_project) -> RestZenStore:
    store = clean_project.zen_store
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


@pytest.fixture
def webhook_integration_factory(clean_project):
    integration_ids = []

    def create(
        name_prefix: str,
        *,
        active: bool = True,
        secret: str | None = None,
    ) -> WebhookIntegrationCreateResponse:
        result = clean_project.create_webhook(
            name=sample_name(name_prefix),
            webhook_type=WebhookType.CUSTOM,
            active=active,
            secret=secret,
        )
        integration_ids.append(result.webhook.id)
        return result

    yield create

    for integration_id in integration_ids:
        clean_project.delete_webhook(integration_id)


def test_webhook_intake_accepts_valid_custom_delivery(
    clean_project, webhook_integration_factory
):
    store = _require_rest_store(clean_project)
    result = webhook_integration_factory("webhook-intake-valid")
    integration = result.webhook
    assert result.secret is not None
    secret = result.secret.get_secret_value()
    body = b'{"pipeline":"training"}'

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

    updated = clean_project.get_webhook(integration.id)
    assert updated.stats.received_count == 1
    assert updated.stats.accepted_count == 1
    assert updated.stats.auth_failed_count == 0
    assert updated.stats.invalid_payload_count == 0
    assert updated.stats.last_received_at is not None
    assert updated.stats.last_accepted_at is not None


@pytest.mark.parametrize(
    (
        "scenario",
        "expected_status",
        "expected_counts",
        "expected_error",
    ),
    [
        ("auth-failure", 401, (1, 0, 1, 0), "Invalid webhook signature."),
        (
            "invalid-payload",
            400,
            (1, 0, 0, 1),
            "Request body must be valid JSON.",
        ),
        ("inactive", 409, (0, 0, 0, 0), None),
        ("type-mismatch", 404, (0, 0, 0, 0), None),
    ],
)
def test_webhook_intake_failure_scenarios(
    clean_project,
    webhook_integration_factory,
    scenario: str,
    expected_status: int,
    expected_counts: tuple[int, int, int, int],
    expected_error: str | None,
):
    store = _require_rest_store(clean_project)
    result = webhook_integration_factory(
        f"webhook-intake-{scenario}",
        active=scenario != "inactive",
    )
    integration = result.webhook
    assert result.secret is not None
    secret = result.secret.get_secret_value()
    body = b"not-json" if scenario == "invalid-payload" else b'{"ok":true}'
    endpoint_path = integration.endpoint_path
    headers = {
        "X-ZenML-Event": "pipeline.ready",
        "X-ZenML-Signature-256": _signature(secret, body),
    }
    if scenario == "auth-failure":
        headers["X-ZenML-Signature-256"] = "sha256=invalid"
    elif scenario == "type-mismatch":
        endpoint_path = endpoint_path.replace("/custom/", "/github/")
        headers = {}

    response = _post_webhook(
        store=store,
        endpoint_path=endpoint_path,
        body=body,
        headers=headers,
    )

    assert response.status_code == expected_status
    updated = clean_project.get_webhook(integration.id)
    assert (
        updated.stats.received_count,
        updated.stats.accepted_count,
        updated.stats.auth_failed_count,
        updated.stats.invalid_payload_count,
    ) == expected_counts
    assert updated.stats.last_error_summary == expected_error
    assert (updated.stats.last_error_at is not None) == (
        expected_error is not None
    )


def test_webhook_intake_returns_not_found_for_unknown_integration(
    clean_project,
):
    store = _require_rest_store(clean_project)
    response = _post_webhook(
        store=store,
        endpoint_path=f"/api/v1/webhooks/custom/{uuid4()}/events",
        body=b'{"pipeline":"training"}',
        headers={},
    )

    assert response.status_code == 404
