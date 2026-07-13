import io
from unittest.mock import patch

import pytest

import zenml_cli
from tests.cli_runner_utils import cli_runner
from tests.integration.functional.utils import sample_name
from zenml.cli.cli import cli
from zenml.client import Client
from zenml.enums import WebhookType

webhook_integration_command = cli.commands["webhook-integration"]
create_command = webhook_integration_command.commands["create"]
describe_command = webhook_integration_command.commands["describe"]
list_command = webhook_integration_command.commands["list"]
update_command = webhook_integration_command.commands["update"]
rotate_secret_command = webhook_integration_command.commands["rotate-secret"]
delete_command = webhook_integration_command.commands["delete"]


def _delete_if_exists(name_or_id: str) -> None:
    client = Client()
    try:
        client.delete_webhook_integration(name_or_id)
    except KeyError:
        pass


def test_webhook_integration_cli_lifecycle(clean_client):
    runner = cli_runner()
    name = sample_name("webhook-cli")
    updated_name = sample_name("webhook-cli-updated")

    try:
        result = runner.invoke(
            create_command,
            [name, "--type", WebhookType.CUSTOM.value],
        )

        assert result.exit_code == 0, result.output
        assert "Signing secret:" in result.output

        integration = clean_client.get_webhook_integration(name)
        assert integration.webhook_type == WebhookType.CUSTOM
        assert integration.active is True

        list_output_buffer = io.StringIO()
        with patch.object(zenml_cli, "_original_stdout", list_output_buffer):
            result = runner.invoke(list_command)
        list_output = list_output_buffer.getvalue() + result.output

        assert result.exit_code == 0, result.output
        assert name in list_output
        assert "Unknown column(s) ignored" not in list_output

        result = runner.invoke(describe_command, [name])

        assert result.exit_code == 0, result.output
        assert name in result.output
        assert integration.endpoint_path in result.output

        result = runner.invoke(
            update_command,
            [name, "--name", updated_name, "--inactive"],
        )

        assert result.exit_code == 0, result.output
        updated = clean_client.get_webhook_integration(updated_name)
        assert updated.id == integration.id
        assert updated.active is False

        result = runner.invoke(
            rotate_secret_command,
            [updated_name, "--secret", "replacement-secret"],
        )

        assert result.exit_code == 0, result.output
        assert "Signing secret: replacement-secret" in result.output

        result = runner.invoke(delete_command, [updated_name, "--yes"])

        assert result.exit_code == 0, result.output
        with pytest.raises(KeyError):
            clean_client.get_webhook_integration(updated.id)
    finally:
        _delete_if_exists(updated_name)
        _delete_if_exists(name)


def test_webhook_integration_cli_does_not_echo_user_supplied_secret(
    clean_client,
):
    runner = cli_runner()
    name = sample_name("webhook-cli-secret")

    try:
        result = runner.invoke(
            create_command,
            [
                name,
                "--type",
                WebhookType.GITHUB.value,
                "--secret",
                "user-supplied-secret",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "user-supplied-secret" not in result.output
        assert "Signing secret:" not in result.output

        integration = clean_client.get_webhook_integration(name)
        assert integration.webhook_type == WebhookType.GITHUB
        assert "secret" not in integration.model_dump()
    finally:
        _delete_if_exists(name)


def test_webhook_integration_cli_rejects_rotation_for_secret_reference(
    clean_client,
):
    """The CLI guides referenced credentials to the secret update command."""
    runner = cli_runner()
    integration_name = sample_name("webhook-cli-reference")
    secret_name = sample_name("webhook-cli-secret")
    clean_client.create_secret(secret_name, values={"key": "secret-value"})

    try:
        create_result = runner.invoke(
            create_command,
            [
                integration_name,
                "--type",
                WebhookType.CUSTOM.value,
                "--secret",
                "managed-secret",
            ],
        )
        assert create_result.exit_code == 0, create_result.output

        update_result = runner.invoke(
            update_command,
            [
                integration_name,
                "--secret",
                f"{{{{{secret_name}.key}}}}",
            ],
        )
        assert update_result.exit_code == 0, update_result.output

        rotate_result = runner.invoke(
            rotate_secret_command, [integration_name]
        )

        assert rotate_result.exit_code != 0
        assert "zenml secret update" in rotate_result.output
    finally:
        _delete_if_exists(integration_name)
        clean_client.delete_secret(secret_name)
