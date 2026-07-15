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
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from tests.integration.functional.utils import sample_name
from zenml.enums import WebhookType
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    WebhookIntegrationFilter,
    WebhookIntegrationRequest,
    WebhookIntegrationRotateSecretRequest,
    WebhookIntegrationUpdate,
)
from zenml.zen_stores.schemas.secret_schemas import SecretSchema
from zenml.zen_stores.schemas.webhook_integration_schemas import (
    WebhookIntegrationSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


def test_client_webhook_methods_require_rest_store(
    clean_client,
) -> None:
    """Public webhook client methods reject local SQL stores."""
    if not isinstance(clean_client.zen_store, SqlZenStore):
        pytest.skip("Local SQL store behavior is required for this test.")

    error = "This method is not allowed when not connected"
    with pytest.raises(TypeError, match=error):
        clean_client.create_webhook(
            name="webhook",
            webhook_type=WebhookType.CUSTOM,
        )
    with pytest.raises(TypeError, match=error):
        clean_client.get_webhook("webhook")
    with pytest.raises(TypeError, match=error):
        clean_client.list_webhooks()
    with pytest.raises(TypeError, match=error):
        clean_client.update_webhook("webhook", active=False)
    with pytest.raises(TypeError, match=error):
        clean_client.delete_webhook("webhook")
    with pytest.raises(TypeError, match=error):
        clean_client.rotate_webhook_secret("webhook")


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

    integration = result.webhook

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


def test_sql_store_protects_webhook_owned_secret(clean_client) -> None:
    """Webhook-owned secrets require explicit webhook deletion."""
    store = clean_client.zen_store
    if not isinstance(store, SqlZenStore):
        pytest.skip("Local SQL store behavior is required for this test.")

    result = store.create_webhook_integration(
        WebhookIntegrationRequest(
            project=clean_client.active_project.id,
            name=sample_name("webhook-owned-secret"),
            webhook_type=WebhookType.CUSTOM,
            secret="owned-secret",
        )
    )
    webhook_id = result.webhook.id

    try:
        with Session(store.engine) as session:
            schema = session.exec(
                select(WebhookIntegrationSchema).where(
                    WebhookIntegrationSchema.id == webhook_id
                )
            ).one()
            secret_id = schema.secret_id

            secret = session.get(SecretSchema, secret_id)
            assert secret is not None
            session.delete(secret)
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            with pytest.raises(IllegalOperationError):
                store._delete_secret_schema(
                    secret_id=secret_id, session=session
                )

        assert store.get_webhook_integration_secret(webhook_id) == (
            "owned-secret"
        )
        assert store.get_webhook_integration(webhook_id).id == webhook_id

        store.delete_webhook_integration(webhook_id)

        with Session(store.engine) as session:
            assert session.get(WebhookIntegrationSchema, webhook_id) is None
            assert session.get(SecretSchema, secret_id) is None
    finally:
        try:
            store.delete_webhook_integration(webhook_id)
        except KeyError:
            pass


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
            store.get_webhook_integration_secret(result.webhook.id)
            == "initial-secret"
        )

        clean_client.update_secret(
            secret_name, add_or_update_values={"key": "rotated-secret"}
        )

        assert (
            store.get_webhook_integration_secret(result.webhook.id)
            == "rotated-secret"
        )
    finally:
        store.delete_webhook_integration(result.webhook.id)
        clean_client.delete_secret(secret_name)
