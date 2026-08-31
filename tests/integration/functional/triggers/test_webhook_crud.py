"""Functional tests for webhook trigger ownership and configuration."""

import pytest

from tests.integration.functional.utils import sample_name
from zenml.enums import TriggerFlavor, TriggerRunConcurrency
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    ProjectRequest,
    TriggerFilter,
    WebhookRequest,
    WebhookTriggerRequest,
    WebhookTriggerResponse,
    WebhookTriggerUpdate,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


def test_webhook_trigger_store_lifecycle(clean_client):
    """Store enforces immutable ownership and guarded webhook deletion."""
    store = clean_client.zen_store
    project_id = clean_client.active_project.id
    webhook = store.create_webhook(
        WebhookRequest(
            project=project_id,
            name=sample_name("custom-webhook"),
            webhook_type="custom",
            active=False,
        )
    ).webhook
    trigger = store.create_trigger(
        WebhookTriggerRequest(
            project=project_id,
            name=sample_name("webhook-trigger"),
            webhook_id=webhook.id,
            configuration={"target_events": []},
            concurrency=TriggerRunConcurrency.SUBMIT,
            active=True,
        )
    )

    assert isinstance(trigger, WebhookTriggerResponse)
    assert trigger.flavor == TriggerFlavor.WEBHOOK
    assert trigger.webhook_id == webhook.id
    assert trigger.webhook == webhook
    assert trigger.active is True
    assert trigger.configuration["target_events"] == []

    with pytest.raises(ValueError, match="empty target_events"):
        store.update_trigger(
            trigger_id=trigger.id,
            trigger_update=WebhookTriggerUpdate(
                name=trigger.name,
                active=True,
                concurrency=trigger.concurrency,
                configuration={"target_events": [{"type": "unsupported"}]},
            ),
        )

    updated = store.update_trigger(
        trigger_id=trigger.id,
        trigger_update=WebhookTriggerUpdate(
            name=sample_name("webhook-trigger-updated"),
            active=False,
            concurrency=TriggerRunConcurrency.SKIP,
            configuration={"target_events": []},
        ),
    )
    assert updated.webhook_id == webhook.id
    assert updated.active is False

    listed = store.list_triggers(
        TriggerFilter(project=project_id, webhook_id=webhook.id)
    )
    assert updated.id in {item.id for item in listed.items}

    other_project = store.create_project(
        ProjectRequest(name=sample_name("webhook-trigger-other-project"))
    )
    with pytest.raises(KeyError, match="not found"):
        store.create_trigger(
            WebhookTriggerRequest(
                project=other_project.id,
                name=sample_name("cross-project-webhook-trigger"),
                webhook_id=webhook.id,
                configuration={"target_events": []},
            )
        )

    with pytest.raises(IllegalOperationError, match="non-archived"):
        store.delete_webhook(webhook.id)

    store.delete_trigger(trigger.id, soft=True)
    archived = store.get_trigger(trigger.id)
    assert archived.is_archived is True
    assert archived.webhook_id == webhook.id
    assert archived.configuration == trigger.configuration

    store.delete_webhook(webhook.id)
    retained = store.get_trigger(trigger.id)
    assert retained.is_archived is True
    assert retained.webhook_id is None
    assert retained.webhook is None
    assert retained.configuration == trigger.configuration


def test_webhook_trigger_client_lifecycle(clean_client):
    """The public client accepts generic full-replacement configuration."""
    if isinstance(clean_client.zen_store, SqlZenStore):
        pytest.skip("Webhooks require a REST store.")

    webhook = clean_client.create_webhook(
        name=sample_name("github-webhook"),
        webhook_type="github",
    ).webhook
    trigger = clean_client.create_webhook_trigger(
        name=sample_name("github-webhook-trigger"),
        webhook=webhook.id,
        configuration={
            "target_events": [
                {
                    "type": "merged_pull_request",
                    "repo": "zenml-io/zenml",
                    "target_branch": "develop",
                }
            ]
        },
    )

    assert trigger.webhook_id == webhook.id
    assert trigger.flavor == TriggerFlavor.WEBHOOK
    assert trigger.configuration["target_events"][0]["type"] == (
        "merged_pull_request"
    )

    updated = clean_client.update_webhook_trigger(
        trigger.id,
        configuration={
            "target_events": [
                {
                    "type": "push",
                    "repo": "zenml-io/zenml",
                    "branch": "main",
                }
            ]
        },
    )
    assert updated.webhook_id == webhook.id
    assert updated.configuration["target_events"][0]["type"] == "push"

    listed = clean_client.list_webhook_triggers(webhook_id=webhook.id)
    assert trigger.id in {item.id for item in listed.items}
