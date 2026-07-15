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
import pytest

from tests.integration.functional.utils import sample_name
from zenml.enums import WebhookType
from zenml.models import (
    WebhookIntegrationFilter,
    WebhookIntegrationRequest,
    WebhookIntegrationRotateSecretRequest,
    WebhookIntegrationUpdate,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


def test_client_webhook_integration_methods_require_rest_store(
    clean_client,
) -> None:
    """Public webhook integration client methods reject local SQL stores."""
    if not isinstance(clean_client.zen_store, SqlZenStore):
        pytest.skip("Local SQL store behavior is required for this test.")

    error = "This method is not allowed when not connected"
    with pytest.raises(TypeError, match=error):
        clean_client.create_webhook_integration(
            name="webhook",
            webhook_type=WebhookType.CUSTOM,
        )
    with pytest.raises(TypeError, match=error):
        clean_client.get_webhook_integration("webhook")
    with pytest.raises(TypeError, match=error):
        clean_client.list_webhook_integrations()
    with pytest.raises(TypeError, match=error):
        clean_client.update_webhook_integration("webhook", active=False)
    with pytest.raises(TypeError, match=error):
        clean_client.delete_webhook_integration("webhook")
    with pytest.raises(TypeError, match=error):
        clean_client.rotate_webhook_integration_secret("webhook")


def test_zen_store_webhook_integration_lifecycle(clean_client):
    store = clean_client.zen_store
    project_id = clean_client.active_project.id
    name = sample_name("webhook-store")

    result = store.create_webhook_integration(
        WebhookIntegrationRequest(
            project=project_id,
            name=name,
            webhook_type=WebhookType.CUSTOM,
        )
    )

    integration = result.integration

    assert result.secret is not None
    assert integration.name == name
    assert integration.project_id == project_id
    assert integration.webhook_type == WebhookType.CUSTOM
    assert integration.active is True
    assert integration.stats.received_count == 0
    assert integration.get_resources().user is not None
    assert integration.get_resources().user.id == clean_client.active_user.id

    by_id = store.get_webhook_integration(integration.id)

    assert by_id.id == integration.id
    assert by_id.stats.received_count == 0
    assert by_id.get_resources().user is not None
    assert by_id.get_resources().user.id == clean_client.active_user.id

    filtered = store.list_webhook_integrations(
        WebhookIntegrationFilter(
            project=project_id,
            webhook_type=WebhookType.CUSTOM,
            active=True,
        ),
        hydrate=True,
    )

    assert integration.id in {item.id for item in filtered.items}
    assert all(item.stats.received_count == 0 for item in filtered.items)

    updated_name = sample_name("webhook-store-updated")
    updated = store.update_webhook_integration(
        integration_id=integration.id,
        update=WebhookIntegrationUpdate(name=updated_name, active=False),
    )

    assert updated.id == integration.id
    assert updated.name == updated_name
    assert updated.active is False
    assert updated.get_resources().user is not None
    assert updated.get_resources().user.id == clean_client.active_user.id

    inactive_integrations = store.list_webhook_integrations(
        WebhookIntegrationFilter(project=project_id, active=False)
    )

    assert integration.id in {item.id for item in inactive_integrations.items}

    rotated = store.rotate_webhook_integration_secret(
        integration_id=integration.id,
        request=WebhookIntegrationRotateSecretRequest(
            secret="replacement-secret"
        ),
    )

    assert rotated.secret.get_secret_value() == "replacement-secret"

    store.delete_webhook_integration(integration.id)

    with pytest.raises(KeyError):
        store.get_webhook_integration(integration.id)


def test_sql_store_resolves_webhook_secret_references_lazily(clean_client):
    """Webhook secret references resolve their current value at intake time."""
    store = clean_client.zen_store
    if not isinstance(store, SqlZenStore):
        pytest.skip("Webhook secret resolution is server-local behavior.")

    secret_name = sample_name("webhook-reference")
    clean_client.create_secret(secret_name, values={"key": "initial-secret"})
    result = store.create_webhook_integration(
        WebhookIntegrationRequest(
            project=clean_client.active_project.id,
            name=sample_name("webhook-store-reference"),
            webhook_type=WebhookType.CUSTOM,
            secret=f"{{{{{secret_name}.key}}}}",
        )
    )

    try:
        assert (
            store.get_webhook_integration_secret(result.integration.id)
            == "initial-secret"
        )

        clean_client.update_secret(
            secret_name, add_or_update_values={"key": "rotated-secret"}
        )

        assert (
            store.get_webhook_integration_secret(result.integration.id)
            == "rotated-secret"
        )
    finally:
        store.delete_webhook_integration(result.integration.id)
        clean_client.delete_secret(secret_name)
