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


def test_webhook_trigger_cli_lifecycle(clean_client):
    """Webhook triggers can be managed through CLI commands."""
    if isinstance(clean_client.zen_store, SqlZenStore):
        pytest.skip("Webhooks require a REST store.")

    runner = cli_runner()
    integration = clean_client.create_webhook(
        name=sample_name("webhook-trigger-cli-integration"),
        webhook_type=WebhookType.CUSTOM,
    ).webhook
    trigger_name = sample_name("webhook-trigger-cli")
    updated_name = sample_name("webhook-trigger-cli-updated")

    result = runner.invoke(
        create_command,
        [
            trigger_name,
            "--webhook-type",
            WebhookType.CUSTOM.value,
            "--webhook-integration",
            integration.name,
        ],
    )

    assert result.exit_code == 0, result.output
    trigger = clean_client.get_webhook_trigger(trigger_name)
    assert trigger.webhook_integration_id == integration.id

    list_output_buffer = io.StringIO()
    with patch.object(zenml_cli, "_original_stdout", list_output_buffer):
        result = runner.invoke(
            list_command,
            ["--webhook-integration-id", str(integration.id)],
        )
    list_output = list_output_buffer.getvalue() + result.output

    assert result.exit_code == 0, result.output
    assert trigger_name in list_output

    result = runner.invoke(
        update_command,
        [
            trigger_name,
            "--name",
            updated_name,
            "--detach-webhook-integration",
        ],
    )

    assert result.exit_code == 0, result.output
    detached = clean_client.get_webhook_trigger(updated_name)
    assert detached.webhook_integration_id is None
    assert detached.active is False

    result = runner.invoke(
        update_command,
        [
            updated_name,
            "--webhook-integration",
            integration.name,
            "--active",
            "true",
        ],
    )

    assert result.exit_code == 0, result.output
    reactivated = clean_client.get_webhook_trigger(updated_name)
    assert reactivated.webhook_integration_id == integration.id
    assert reactivated.active is True

    result = runner.invoke(delete_command, [updated_name])

    assert result.exit_code == 0, result.output
    archived = clean_client.get_webhook_trigger(
        reactivated.id, is_archived=True
    )
    assert archived.webhook_integration_id is None
