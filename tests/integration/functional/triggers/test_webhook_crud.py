"""Functional tests for webhook trigger store and client CRUD."""

import pytest

from tests.integration.functional.utils import sample_name
from zenml.enums import (
    TriggerFlavor,
    TriggerRunConcurrency,
    WebhookType,
)
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    MergedPullRequest,
    ProjectRequest,
    PushEvent,
    ReleasePublished,
    TriggerFilter,
    WebhookIntegrationRequest,
    WebhookTriggerRequest,
    WebhookTriggerResponse,
    WebhookTriggerUpdate,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


def test_webhook_trigger_store_lifecycle(clean_client):
    """Webhook triggers support store CRUD and detached lifecycle rules."""
    store = clean_client.zen_store
    project_id = clean_client.active_project.id
    custom_integration = store.create_webhook_integration(
        WebhookIntegrationRequest(
            project=project_id,
            name=sample_name("custom-webhook-integration"),
            webhook_type=WebhookType.CUSTOM,
        )
    ).webhook
    github_integration = store.create_webhook_integration(
        WebhookIntegrationRequest(
            project=project_id,
            name=sample_name("github-webhook-integration"),
            webhook_type=WebhookType.GITHUB,
        )
    ).webhook

    with pytest.raises(IllegalOperationError, match="custom webhook"):
        store.create_trigger(
            WebhookTriggerRequest(
                project=project_id,
                name=sample_name("incompatible-webhook-trigger"),
                flavor=TriggerFlavor.CUSTOM_WEBHOOK,
                webhook_integration_id=github_integration.id,
            )
        )

    github_trigger = store.create_trigger(
        WebhookTriggerRequest(
            project=project_id,
            name=sample_name("github-webhook-trigger"),
            flavor=TriggerFlavor.GITHUB_WEBHOOK,
            webhook_integration_id=github_integration.id,
            events=[
                MergedPullRequest(
                    repo="zenml-io/zenml",
                    target_branch="develop",
                ),
                PushEvent(repo="zenml-io/zenml", branch="main"),
            ],
        )
    )

    assert isinstance(github_trigger, WebhookTriggerResponse)
    assert github_trigger.events == [
        MergedPullRequest(
            repo="zenml-io/zenml",
            target_branch="develop",
        ),
        PushEvent(repo="zenml-io/zenml", branch="main"),
    ]

    with pytest.raises(
        IllegalOperationError, match="require event configurations"
    ):
        store.update_trigger(
            trigger_id=github_trigger.id,
            trigger_update=WebhookTriggerUpdate(
                name=github_trigger.name,
                active=github_trigger.active,
                concurrency=github_trigger.concurrency,
                webhook_integration_id=github_trigger.webhook_integration_id,
            ),
        )

    github_trigger = store.update_trigger(
        trigger_id=github_trigger.id,
        trigger_update=WebhookTriggerUpdate(
            name=github_trigger.name,
            active=github_trigger.active,
            concurrency=github_trigger.concurrency,
            webhook_integration_id=github_trigger.webhook_integration_id,
            events=[
                ReleasePublished(
                    repo="zenml-io/zenml",
                    tag="startswith:v",
                    target_branch='oneof:["develop", "main"]',
                )
            ],
        ),
    )

    assert github_trigger.events == [
        ReleasePublished(
            repo="zenml-io/zenml",
            tag="startswith:v",
            target_branch='oneof:["develop", "main"]',
        )
    ]

    trigger = store.create_trigger(
        WebhookTriggerRequest(
            project=project_id,
            name=sample_name("webhook-trigger"),
            flavor=TriggerFlavor.CUSTOM_WEBHOOK,
            webhook_integration_id=custom_integration.id,
            concurrency=TriggerRunConcurrency.SUBMIT,
        )
    )

    assert isinstance(trigger, WebhookTriggerResponse)
    assert trigger.active is True
    assert trigger.webhook_integration_id == custom_integration.id
    assert trigger.webhook_integration == custom_integration
    assert trigger.webhook_type == WebhookType.CUSTOM

    with pytest.raises(IllegalOperationError, match="do not support"):
        store.update_trigger(
            trigger_id=trigger.id,
            trigger_update=WebhookTriggerUpdate(
                name=trigger.name,
                active=trigger.active,
                concurrency=trigger.concurrency,
                webhook_integration_id=trigger.webhook_integration_id,
                events=[MergedPullRequest(repo="zenml-io/zenml")],
            ),
        )

    retrieved = store.get_trigger(trigger.id)
    listed = store.list_triggers(
        TriggerFilter(
            project=project_id,
            webhook_integration_id=custom_integration.id,
        )
    )

    assert retrieved.model_dump() == trigger.model_dump()
    assert trigger.id in {item.id for item in listed.items}

    updated_name = sample_name("webhook-trigger-updated")
    trigger = store.update_trigger(
        trigger_id=trigger.id,
        trigger_update=WebhookTriggerUpdate(
            name=updated_name,
            active=trigger.active,
            concurrency=trigger.concurrency,
            webhook_integration_id=trigger.webhook_integration_id,
        ),
    )

    assert trigger.name == updated_name
    assert trigger.webhook_integration_id == custom_integration.id
    assert trigger.webhook_integration == custom_integration
    assert trigger.active is True
    assert trigger.concurrency == TriggerRunConcurrency.SUBMIT

    other_project = store.create_project(
        ProjectRequest(name=sample_name("webhook-trigger-other-project"))
    )
    cross_project_integration = store.create_webhook_integration(
        WebhookIntegrationRequest(
            project=other_project.id,
            name=sample_name("cross-project-webhook-integration"),
            webhook_type=WebhookType.CUSTOM,
        )
    ).webhook

    with pytest.raises(KeyError, match="not found"):
        store.create_trigger(
            WebhookTriggerRequest(
                project=project_id,
                name=sample_name("cross-project-webhook-trigger"),
                flavor=TriggerFlavor.CUSTOM_WEBHOOK,
                webhook_integration_id=cross_project_integration.id,
            )
        )

    with pytest.raises(KeyError, match="not found"):
        store.update_trigger(
            trigger_id=trigger.id,
            trigger_update=WebhookTriggerUpdate(
                name=trigger.name,
                active=trigger.active,
                concurrency=trigger.concurrency,
                webhook_integration_id=cross_project_integration.id,
            ),
        )

    with pytest.raises(IllegalOperationError, match="custom webhook"):
        store.update_trigger(
            trigger_id=trigger.id,
            trigger_update=WebhookTriggerUpdate(
                name=trigger.name,
                active=trigger.active,
                concurrency=trigger.concurrency,
                webhook_integration_id=github_integration.id,
            ),
        )

    detached = store.update_trigger(
        trigger_id=trigger.id,
        trigger_update=WebhookTriggerUpdate(
            name=trigger.name,
            active=True,
            concurrency=TriggerRunConcurrency.SKIP,
            webhook_integration_id=None,
        ),
    )

    assert detached.webhook_integration_id is None
    assert detached.webhook_integration is None
    assert detached.active is False

    reattached = store.update_trigger(
        trigger_id=trigger.id,
        trigger_update=WebhookTriggerUpdate(
            name=trigger.name,
            active=detached.active,
            concurrency=detached.concurrency,
            webhook_integration_id=custom_integration.id,
        ),
    )

    assert reattached.webhook_integration_id == custom_integration.id
    assert reattached.webhook_integration == custom_integration
    assert reattached.active is False

    reactivated = store.update_trigger(
        trigger_id=trigger.id,
        trigger_update=WebhookTriggerUpdate(
            name=trigger.name,
            active=True,
            concurrency=reattached.concurrency,
            webhook_integration_id=custom_integration.id,
        ),
    )

    assert reactivated.active is True

    store.delete_webhook_integration(custom_integration.id)
    retained = store.get_trigger(trigger.id)

    assert retained.webhook_integration_id is None
    assert retained.webhook_integration is None
    assert retained.active is False
    assert retained.is_archived is False

    store.delete_trigger(trigger.id, soft=True)
    archived = store.get_trigger(trigger.id)

    assert archived.is_archived is True
    assert archived.webhook_integration_id is None


def test_webhook_trigger_client_lifecycle(clean_client):
    """Webhook triggers can be managed through the public client."""
    if isinstance(clean_client.zen_store, SqlZenStore):
        pytest.skip("Webhooks require a REST store.")

    integration = clean_client.create_webhook(
        name=sample_name("webhook-trigger-client-integration"),
        webhook_type=WebhookType.GITHUB,
    ).webhook
    trigger = clean_client.create_webhook_trigger(
        name=sample_name("webhook-trigger-client"),
        webhook_type=WebhookType.GITHUB,
        webhook_integration=integration.name,
        concurrency=TriggerRunConcurrency.SUBMIT,
        events=[
            MergedPullRequest(
                repo="zenml-io/zenml",
                target_branch="develop",
                source_branch="startswith:feature/",
                author="george",
            )
        ],
    )

    assert trigger.webhook_integration_id == integration.id
    assert trigger.webhook_integration == integration
    assert trigger.webhook_type == WebhookType.GITHUB
    assert trigger.events == [
        MergedPullRequest(
            repo="zenml-io/zenml",
            target_branch="develop",
            source_branch="startswith:feature/",
            author="george",
        )
    ]
    assert clean_client.get_webhook_trigger(trigger.name).id == trigger.id

    listed = clean_client.list_webhook_triggers(
        webhook_type=WebhookType.GITHUB,
        webhook_integration_id=integration.id,
    )

    assert trigger.id in {item.id for item in listed.items}

    updated_name = sample_name("webhook-trigger-client-updated")
    updated = clean_client.update_webhook_trigger(
        trigger.id,
        name=updated_name,
    )

    assert updated.name == updated_name
    assert updated.webhook_integration_id == integration.id
    assert updated.webhook_integration == integration
    assert updated.active is True
    assert updated.concurrency == TriggerRunConcurrency.SUBMIT
    assert updated.events == trigger.events

    updated = clean_client.update_webhook_trigger(
        trigger.id,
        concurrency=TriggerRunConcurrency.SKIP,
    )

    assert updated.webhook_integration_id == integration.id
    assert updated.active is True
    assert updated.concurrency == TriggerRunConcurrency.SKIP

    detached = clean_client.update_webhook_trigger(
        trigger.id,
        detach_webhook_integration=True,
    )

    assert detached.webhook_integration_id is None
    assert detached.webhook_integration is None
    assert detached.active is False

    reattached = clean_client.update_webhook_trigger(
        trigger.id,
        webhook_integration=integration.id,
    )

    assert reattached.webhook_integration_id == integration.id
    assert reattached.active is False

    reactivated = clean_client.update_webhook_trigger(
        trigger.id,
        webhook_integration=integration.id,
        active=True,
    )

    assert reactivated.active is True

    clean_client.delete_webhook(integration.id)
    retained = clean_client.get_webhook_trigger(trigger.id)

    assert retained.webhook_integration_id is None
    assert retained.webhook_integration is None
    assert retained.active is False

    clean_client.delete_trigger(trigger.id)

    with pytest.raises(KeyError):
        clean_client.get_webhook_trigger(trigger.id)

    archived = clean_client.get_webhook_trigger(trigger.id, is_archived=True)
    assert archived.is_archived is True
    assert archived.webhook_integration_id is None

    clean_client.delete_trigger(trigger.id, soft=False)

    with pytest.raises(KeyError):
        clean_client.get_webhook_trigger(trigger.id, is_archived=True)


def test_webhook_trigger_client_association_transitions(clean_client):
    """Public client validates webhook trigger association transitions."""
    if isinstance(clean_client.zen_store, SqlZenStore):
        pytest.skip("Webhooks require a REST store.")

    primary = clean_client.create_webhook(
        name=sample_name("webhook-trigger-primary-integration"),
        webhook_type=WebhookType.CUSTOM,
    ).webhook
    replacement = clean_client.create_webhook(
        name=sample_name("webhook-trigger-replacement-integration"),
        webhook_type=WebhookType.CUSTOM,
    ).webhook
    incompatible = clean_client.create_webhook(
        name=sample_name("webhook-trigger-incompatible-integration"),
        webhook_type=WebhookType.GITHUB,
    ).webhook
    trigger = clean_client.create_webhook_trigger(
        name=sample_name("detached-webhook-trigger"),
        webhook_type=WebhookType.CUSTOM,
        active=True,
    )

    assert trigger.webhook_integration_id is None
    assert trigger.active is False

    with pytest.raises(IllegalOperationError):
        clean_client.update_webhook_trigger(
            trigger.id,
            webhook_integration=primary.id,
            detach_webhook_integration=True,
        )

    with pytest.raises(IllegalOperationError, match="custom webhook"):
        clean_client.update_webhook_trigger(
            trigger.id,
            webhook_integration=incompatible.id,
        )

    attached = clean_client.update_webhook_trigger(
        trigger.id,
        webhook_integration=primary.id,
        active=True,
    )

    assert attached.webhook_integration_id == primary.id
    assert attached.active is True

    replaced = clean_client.update_webhook_trigger(
        trigger.id,
        webhook_integration=replacement.id,
    )

    assert replaced.webhook_integration_id == replacement.id
    assert replaced.active is True

    clean_client.delete_trigger(trigger.id, soft=False)
    clean_client.delete_webhook(primary.id)
    clean_client.delete_webhook(replacement.id)
    clean_client.delete_webhook(incompatible.id)
