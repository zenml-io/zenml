import pytest

from tests.integration.functional.utils import sample_name
from zenml.enums import WebhookType


def test_client_webhook_integration_lifecycle(clean_client):
    name = sample_name("webhook-client")

    result = clean_client.create_webhook_integration(
        name=name,
        webhook_type=WebhookType.CUSTOM,
    )

    assert result.secret is not None
    integration = result.integration
    assert integration.name == name
    assert integration.webhook_type == WebhookType.CUSTOM
    assert integration.active is True
    assert integration.project_id == clean_client.active_project.id
    assert integration.endpoint_path.endswith(
        f"/custom/{integration.id}/events"
    )
    assert integration.stats.received_count == 0

    by_id = clean_client.get_webhook_integration(integration.id)
    by_name = clean_client.get_webhook_integration(name)

    assert by_id.id == integration.id
    assert by_name.id == integration.id
    assert "secret" not in by_id.model_dump()

    listed_by_type = clean_client.list_webhook_integrations(
        webhook_type=WebhookType.CUSTOM
    )
    listed_by_active_state = clean_client.list_webhook_integrations(
        active=True
    )

    assert integration.id in {item.id for item in listed_by_type.items}
    assert integration.id in {item.id for item in listed_by_active_state.items}

    updated_name = sample_name("webhook-client-updated")
    updated = clean_client.update_webhook_integration(
        name_id_or_prefix=name,
        name=updated_name,
        active=False,
    )

    assert updated.id == integration.id
    assert updated.name == updated_name
    assert updated.active is False

    inactive_integrations = clean_client.list_webhook_integrations(
        active=False
    )

    assert integration.id in {item.id for item in inactive_integrations.items}

    rotated = clean_client.rotate_webhook_integration_secret(
        name_id_or_prefix=updated_name,
        secret="replacement-secret",
    )

    assert rotated.secret.get_secret_value() == "replacement-secret"

    clean_client.delete_webhook_integration(updated_name)

    with pytest.raises(KeyError):
        clean_client.get_webhook_integration(integration.id)


def test_client_does_not_echo_user_supplied_webhook_secret(clean_client):
    name = sample_name("webhook-client-secret")

    result = clean_client.create_webhook_integration(
        name=name,
        webhook_type=WebhookType.GITHUB,
        secret="user-supplied-secret",
    )

    try:
        assert result.secret is None

        integration = clean_client.get_webhook_integration(
            result.integration.id
        )

        assert "secret" not in integration.model_dump()
        assert integration.webhook_type == WebhookType.GITHUB
    finally:
        clean_client.delete_webhook_integration(result.integration.id)
