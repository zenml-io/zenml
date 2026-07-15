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
from zenml.client import Client
from zenml.enums import WebhookType
from zenml.exceptions import IllegalOperationError
from zenml.zen_stores.sql_zen_store import SqlZenStore


@pytest.fixture
def clean_client(clean_project: Client) -> Client:
    """Return the active client when it is connected to a server."""
    if isinstance(clean_project.zen_store, SqlZenStore):
        pytest.skip("Webhooks require a REST store.")
    return clean_project


def test_client_webhook_lifecycle(clean_client):
    name = sample_name("webhook-client")

    result = clean_client.create_webhook(
        name=name,
        webhook_type=WebhookType.CUSTOM,
    )

    assert result.secret is not None
    integration = result.webhook
    assert integration.name == name
    assert integration.webhook_type == WebhookType.CUSTOM
    assert integration.active is True
    assert integration.project_id == clean_client.active_project.id
    assert integration.endpoint_path.endswith(
        f"/custom/{integration.id}/events"
    )
    assert integration.stats.received_count == 0

    by_id = clean_client.get_webhook(integration.id)
    by_name = clean_client.get_webhook(name)

    assert by_id.id == integration.id
    assert by_name.id == integration.id
    assert "secret" not in by_id.model_dump()

    listed_by_type = clean_client.list_webhooks(
        webhook_type=WebhookType.CUSTOM
    )
    listed_by_active_state = clean_client.list_webhooks(active=True)

    assert integration.id in {item.id for item in listed_by_type.items}
    assert integration.id in {item.id for item in listed_by_active_state.items}

    updated_name = sample_name("webhook-client-updated")
    updated = clean_client.update_webhook(
        name_id_or_prefix=name,
        name=updated_name,
        active=False,
    )

    assert updated.id == integration.id
    assert updated.name == updated_name
    assert updated.active is False

    inactive_integrations = clean_client.list_webhooks(active=False)

    assert integration.id in {item.id for item in inactive_integrations.items}

    rotated = clean_client.rotate_webhook_secret(
        name_id_or_prefix=updated_name,
        secret="replacement-secret",
    )

    assert rotated.secret.get_secret_value() == "replacement-secret"

    clean_client.delete_webhook(updated_name)

    with pytest.raises(KeyError):
        clean_client.get_webhook(integration.id)


def test_client_does_not_echo_user_supplied_webhook_secret(clean_client):
    name = sample_name("webhook-client-secret")

    result = clean_client.create_webhook(
        name=name,
        webhook_type=WebhookType.GITHUB,
        secret="user-supplied-secret",
    )

    try:
        assert result.secret is None

        integration = clean_client.get_webhook(result.webhook.id)

        assert "secret" not in integration.model_dump()
        assert integration.webhook_type == WebhookType.GITHUB
    finally:
        clean_client.delete_webhook(result.webhook.id)


def test_client_update_webhook_by_name_and_id(
    clean_client,
) -> None:
    """Webhook integrations can be updated by name and ID."""
    name = sample_name("webhook-client-update")
    result = clean_client.create_webhook(
        name=name,
        webhook_type=WebhookType.CUSTOM,
    )
    integration_id = result.webhook.id

    try:
        updated_by_name = clean_client.update_webhook(
            name,
            active=False,
        )
        updated_by_id = clean_client.update_webhook(
            integration_id,
            active=True,
        )

        assert updated_by_name.id == integration_id
        assert updated_by_name.active is False
        assert updated_by_id.id == integration_id
        assert updated_by_id.active is True
    finally:
        clean_client.delete_webhook(integration_id)


def test_client_rejects_rotation_for_referenced_webhook_secret(clean_client):
    """Referenced webhook secrets can be updated but not rotated."""
    integration_name = sample_name("webhook-client-reference")
    secret_name = sample_name("webhook-signing-secret")
    clean_client.create_secret(secret_name, values={"key": "initial-secret"})
    result = clean_client.create_webhook(
        name=integration_name,
        webhook_type=WebhookType.CUSTOM,
        secret="managed-secret",
    )

    try:
        clean_client.update_webhook(
            integration_name,
            secret=f"{{{{{secret_name}.key}}}}",
        )

        with pytest.raises(IllegalOperationError, match="zenml secret update"):
            clean_client.rotate_webhook_secret(integration_name)

        clean_client.update_webhook(
            integration_name,
            secret="managed-secret-again",
        )
        with pytest.raises(IllegalOperationError, match="webhook update"):
            clean_client.rotate_webhook_secret(
                integration_name,
                secret=f"{{{{{secret_name}.key}}}}",
            )

        rotated = clean_client.rotate_webhook_secret(integration_name)

        assert rotated.secret.get_secret_value()
    finally:
        clean_client.delete_webhook(result.webhook.id)
        clean_client.delete_secret(secret_name)
