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
from sqlalchemy import event
from sqlmodel import Session, select

from tests.integration.functional.utils import sample_name
from zenml.models import (
    WebhookEventStatsUpdate,
    WebhookFilter,
    WebhookRequest,
    WebhookRotateSecretRequest,
    WebhookUpdate,
)
from zenml.zen_stores.schemas.secret_schemas import SecretSchema
from zenml.zen_stores.schemas.webhook_schemas import (
    WebhookSchema,
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
            webhook_type="custom",
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


def test_zen_store_webhook_lifecycle(clean_client):
    store = clean_client.zen_store
    project_id = clean_client.active_project.id
    name = sample_name("webhook-store")

    result = store.create_webhook(
        WebhookRequest(
            project=project_id,
            name=name,
            webhook_type="custom",
        )
    )

    webhook = result

    assert result.secret is not None
    assert webhook.name == name
    assert webhook.project_id == project_id
    assert webhook.webhook_type == "custom"
    assert webhook.active is True
    assert webhook.stats.received_count == 0
    assert webhook.get_resources().user is not None
    assert webhook.get_resources().user.id == clean_client.active_user.id

    store.record_webhook_event(
        webhook.id, WebhookEventStatsUpdate(accepted=True)
    )
    webhook = store.get_webhook(webhook.id)

    assert webhook.stats.received_count == 1
    assert webhook.stats.accepted_count == 1

    with Session(store.engine) as session:
        initial_secret_id = session.exec(
            select(WebhookSchema.secret_id).where(
                WebhookSchema.id == webhook.id
            )
        ).one()

    by_id = store.get_webhook(webhook.id)

    assert by_id.id == webhook.id
    assert by_id.stats.received_count == 1
    assert by_id.get_resources().user is not None
    assert by_id.get_resources().user.id == clean_client.active_user.id

    filtered = store.list_webhooks(
        WebhookFilter(
            project=project_id,
            webhook_type="custom",
            active=True,
        ),
        hydrate=True,
    )

    assert webhook.id in {item.id for item in filtered.items}
    filtered_webhook = next(
        item for item in filtered.items if item.id == webhook.id
    )
    assert filtered_webhook.stats.received_count == 1

    updated_name = sample_name("webhook-store-updated")
    updated = store.update_webhook(
        webhook_id=webhook.id,
        update=WebhookUpdate(
            name=updated_name,
            active=False,
        ),
    )

    assert updated.id == webhook.id
    assert updated.name == updated_name
    assert updated.active is False
    assert updated.get_resources().user is not None
    assert updated.get_resources().user.id == clean_client.active_user.id

    with Session(store.engine) as session:
        updated_secret_id = session.exec(
            select(WebhookSchema.secret_id).where(
                WebhookSchema.id == webhook.id
            )
        ).one()
    assert updated_secret_id == initial_secret_id

    inactive_webhooks = store.list_webhooks(
        WebhookFilter(project=project_id, active=False)
    )

    assert webhook.id in {item.id for item in inactive_webhooks.items}

    rotated = store.rotate_webhook_secret(
        webhook_id=webhook.id,
        request=WebhookRotateSecretRequest(secret="replacement-secret"),
    )

    assert rotated.secret.get_secret_value() == "replacement-secret"

    with Session(store.engine) as session:
        rotated_secret_id = session.exec(
            select(WebhookSchema.secret_id).where(
                WebhookSchema.id == webhook.id
            )
        ).one()
        assert rotated_secret_id == initial_secret_id
    intake_config = store.get_webhook_intake_config(
        webhook.id, expected_webhook_type="custom"
    )
    assert intake_config.secret.get_secret_value() == "replacement-secret"

    store.delete_webhook(webhook.id)

    with pytest.raises(KeyError):
        store.get_webhook(webhook.id)


def test_sql_store_webhook_intake_config_contains_masked_secret(
    clean_client,
) -> None:
    """Webhook intake resolves its secret without exposing it in output."""
    store = clean_client.zen_store
    if not isinstance(store, SqlZenStore):
        pytest.skip("Local SQL store behavior is required for this test.")

    result = store.create_webhook(
        WebhookRequest(
            project=clean_client.active_project.id,
            name=sample_name("webhook-intake-query-count"),
            webhook_type="custom",
        )
    )
    statements = []

    def capture_statement(
        connection, cursor, statement, parameters, context, executemany
    ):
        statements.append(statement)

    event.listen(store.engine, "before_cursor_execute", capture_statement)
    try:
        config = store.get_webhook_intake_config(
            result.id,
            expected_webhook_type="custom",
        )

        assert config.webhook_type == "custom"
        assert config.active is True
        assert config.project_id == clean_client.active_project.id
        secret = config.secret.get_secret_value()
        assert secret not in repr(config)
        assert secret not in config.model_dump_json()
        assert len(statements) == 2
        assert all(
            statement.lstrip().upper().startswith("SELECT")
            for statement in statements
        )

        statements.clear()
        store.record_webhook_event(
            result.id, WebhookEventStatsUpdate(accepted=True)
        )

        assert len(statements) == 1
        assert statements[0].lstrip().upper().startswith("UPDATE")
    finally:
        event.remove(store.engine, "before_cursor_execute", capture_statement)
        store.delete_webhook(result.id)


def test_public_secret_deletion_hides_webhook_owned_secret(
    clean_client,
) -> None:
    """Public secret deletion cannot address internal webhook secrets."""
    store = clean_client.zen_store
    if not isinstance(store, SqlZenStore):
        pytest.skip("Local SQL store behavior is required for this test.")

    result = store.create_webhook(
        WebhookRequest(
            project=clean_client.active_project.id,
            name=sample_name("webhook-owned-secret"),
            webhook_type="custom",
            secret="owned-secret",
        )
    )
    webhook_id = result.id

    try:
        with Session(store.engine) as session:
            schema = session.exec(
                select(WebhookSchema).where(WebhookSchema.id == webhook_id)
            ).one()
            secret_id = schema.secret_id

        with pytest.raises(KeyError):
            store.delete_secret(secret_id)

        intake_config = store.get_webhook_intake_config(
            webhook_id,
            expected_webhook_type="custom",
        )
        assert intake_config.secret.get_secret_value() == "owned-secret"
        assert store.get_webhook(webhook_id).id == webhook_id

        store.delete_webhook(webhook_id)

        with Session(store.engine) as session:
            assert session.get(WebhookSchema, webhook_id) is None
            assert session.get(SecretSchema, secret_id) is None
    finally:
        try:
            store.delete_webhook(webhook_id)
        except KeyError:
            pass
