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
        webhook_type="custom",
    )

    assert result.secret is not None
    initial_secret = result.secret.get_secret_value()
    webhook = result
    assert webhook.name == name
    assert webhook.webhook_type == "custom"
    assert webhook.active is True
    assert webhook.project_id == clean_client.active_project.id
    assert webhook.stats.received_count == 0

    by_id = clean_client.get_webhook(webhook.id)
    by_name = clean_client.get_webhook(name)

    assert by_id.id == webhook.id
    assert by_name.id == webhook.id
    assert "secret" not in by_id.model_dump()

    listed_by_type = clean_client.list_webhooks(webhook_type="custom")
    listed_by_active_state = clean_client.list_webhooks(active=True)

    assert webhook.id in {item.id for item in listed_by_type.items}
    assert webhook.id in {item.id for item in listed_by_active_state.items}

    updated_name = sample_name("webhook-client-updated")
    updated = clean_client.update_webhook(
        name_id_or_prefix=name,
        name=updated_name,
        active=False,
    )

    assert updated.id == webhook.id
    assert updated.name == updated_name
    assert updated.active is False

    inactive_webhooks = clean_client.list_webhooks(active=False)

    assert webhook.id in {item.id for item in inactive_webhooks.items}

    generated_rotation = clean_client.rotate_webhook_secret(
        name_id_or_prefix=updated_name,
    )

    assert generated_rotation.secret.get_secret_value() != initial_secret

    rotated = clean_client.rotate_webhook_secret(
        name_id_or_prefix=updated_name,
        secret="replacement-secret",
    )

    assert rotated.secret.get_secret_value() == "replacement-secret"

    clean_client.delete_webhook(updated_name)

    with pytest.raises(KeyError):
        clean_client.get_webhook(webhook.id)


def test_client_does_not_echo_user_supplied_webhook_secret(clean_client):
    name = sample_name("webhook-client-secret")

    result = clean_client.create_webhook(
        name=name,
        webhook_type="github",
        secret="user-supplied-secret",
    )

    try:
        assert result.secret is None

        webhook = clean_client.get_webhook(result.id)

        assert "secret" not in webhook.model_dump()
        assert webhook.webhook_type == "github"
    finally:
        clean_client.delete_webhook(result.id)


def test_client_update_webhook_by_name_and_id(
    clean_client,
) -> None:
    """Webhook webhooks can be updated by name and ID."""
    name = sample_name("webhook-client-update")
    result = clean_client.create_webhook(
        name=name,
        webhook_type="custom",
    )
    webhook_id = result.id

    try:
        updated_by_name = clean_client.update_webhook(
            name,
            active=False,
        )
        updated_by_id = clean_client.update_webhook(
            webhook_id,
            active=True,
        )

        assert updated_by_name.id == webhook_id
        assert updated_by_name.active is False
        assert updated_by_id.id == webhook_id
        assert updated_by_id.active is True
    finally:
        clean_client.delete_webhook(webhook_id)
