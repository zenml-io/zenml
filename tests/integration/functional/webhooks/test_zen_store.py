import pytest

from tests.integration.functional.utils import sample_name
from zenml.enums import WebhookType
from zenml.models import (
    WebhookIntegrationFilter,
    WebhookIntegrationRequest,
    WebhookIntegrationSecretRequest,
    WebhookIntegrationUpdate,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


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

    by_id = store.get_webhook_integration(integration.id)

    assert by_id.id == integration.id
    assert by_id.stats.received_count == 0

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

    inactive_integrations = store.list_webhook_integrations(
        WebhookIntegrationFilter(project=project_id, active=False)
    )

    assert integration.id in {item.id for item in inactive_integrations.items}

    rotated = store.rotate_webhook_integration_secret(
        integration_id=integration.id,
        request=WebhookIntegrationSecretRequest(secret="replacement-secret"),
    )

    assert rotated.secret.get_secret_value() == "replacement-secret"

    store.delete_webhook_integration(integration.id)

    with pytest.raises(KeyError):
        store.get_webhook_integration(integration.id)


def test_zen_store_does_not_echo_user_supplied_webhook_secret(clean_client):
    store = clean_client.zen_store
    project_id = clean_client.active_project.id
    name = sample_name("webhook-store-secret")

    result = store.create_webhook_integration(
        WebhookIntegrationRequest(
            project=project_id,
            name=name,
            webhook_type=WebhookType.GITHUB,
            secret="user-supplied-secret",
        )
    )

    try:
        assert result.secret is None

        integration = store.get_webhook_integration(result.integration.id)

        assert "secret" not in integration.model_dump()
        assert integration.webhook_type == WebhookType.GITHUB
    finally:
        store.delete_webhook_integration(result.integration.id)


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
