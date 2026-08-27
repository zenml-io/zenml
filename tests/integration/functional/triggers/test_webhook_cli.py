"""Functional tests for webhook trigger CLI CRUD."""

import io
from unittest.mock import patch

import pytest

import zenml_cli
from tests.cli_runner_utils import cli_runner
from tests.integration.functional.utils import sample_name
from zenml.cli.cli import cli
from zenml.enums import WebhookType
from zenml.zen_stores.sql_zen_store import SqlZenStore

trigger_command = cli.commands["trigger"]
webhook_command = trigger_command.commands["webhook"]
create_command = webhook_command.commands["create"]
list_command = webhook_command.commands["list"]
update_command = webhook_command.commands["update"]
delete_command = webhook_command.commands["delete"]


def test_webhook_trigger_cli_lifecycle(clean_client, tmp_path):
    """Webhook triggers can be managed through CLI commands."""
    if isinstance(clean_client.zen_store, SqlZenStore):
        pytest.skip("Webhooks require a REST store.")

    runner = cli_runner()
    webhook = clean_client.create_webhook(
        name=sample_name("webhook-trigger-cli-webhook"),
        webhook_type=WebhookType.CUSTOM,
    ).webhook
    trigger_name = sample_name("webhook-trigger-cli")
    updated_name = sample_name("webhook-trigger-cli-updated")
    config_path = tmp_path / "custom-webhook.yaml"
    config_path.write_text("target_events: []\n")

    result = runner.invoke(
        create_command,
        [
            trigger_name,
            "--webhook",
            webhook.name,
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0, result.output
    trigger = clean_client.get_webhook_trigger(trigger_name)
    assert trigger.webhook_id == webhook.id
    assert trigger.webhook == webhook

    list_output_buffer = io.StringIO()
    with patch.object(zenml_cli, "_original_stdout", list_output_buffer):
        result = runner.invoke(
            list_command,
            ["--webhook-id", str(webhook.id)],
        )
    list_output = list_output_buffer.getvalue() + result.output

    assert result.exit_code == 0, result.output
    assert trigger_name in list_output

    result = runner.invoke(
        update_command,
        [trigger_name, "--name", updated_name],
    )

    assert result.exit_code == 0, result.output
    renamed = clean_client.get_webhook_trigger(updated_name)
    assert renamed.webhook_id == webhook.id
    assert renamed.webhook == webhook
    assert renamed.active is True

    result = runner.invoke(
        update_command,
        [
            updated_name,
            "--active",
            "false",
        ],
    )

    assert result.exit_code == 0, result.output
    deactivated = clean_client.get_webhook_trigger(updated_name)
    assert deactivated.webhook_id == webhook.id
    assert deactivated.active is False

    result = runner.invoke(delete_command, [updated_name])

    assert result.exit_code == 0, result.output
    archived = clean_client.get_webhook_trigger(
        deactivated.id, is_archived=True
    )
    assert archived.webhook_id == webhook.id


def test_github_webhook_trigger_cli_event_configuration(
    clean_client, tmp_path
):
    """CLI exposes typed GitHub semantic event configuration."""
    if isinstance(clean_client.zen_store, SqlZenStore):
        pytest.skip("Webhooks require a REST store.")

    runner = cli_runner()
    webhook = clean_client.create_webhook(
        name=sample_name("github-webhook-trigger-cli-webhook"),
        webhook_type=WebhookType.GITHUB,
    ).webhook
    trigger_name = sample_name("github-webhook-trigger-cli")
    config_path = tmp_path / "events.yaml"
    config_path.write_text(
        """
target_events:
  - type: merged_pull_request
    repo: zenml-io/zenml
    target_branch: develop
    source_branch: startswith:feature/
    author: george
  - type: push
    repo: zenml-io/zenml
    branch: main
""".lstrip()
    )

    result = runner.invoke(
        create_command,
        [
            trigger_name,
            "--webhook",
            webhook.name,
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0, result.output
    trigger = clean_client.get_webhook_trigger(trigger_name)
    assert trigger.configuration["target_events"] == [
        {
            "type": "merged_pull_request",
            "repo": "zenml-io/zenml",
            "target_branch": "develop",
            "source_branch": "startswith:feature/",
            "author": "george",
        },
        {
            "type": "push",
            "repo": "zenml-io/zenml",
            "branch": "main",
        },
    ]

    clean_client.delete_trigger(trigger.id, soft=False)
    clean_client.delete_webhook(webhook.id)
