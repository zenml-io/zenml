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
import io
from unittest.mock import patch

import pytest

import zenml_cli
from tests.cli_runner_utils import cli_runner
from tests.integration.functional.utils import sample_name
from zenml.cli.cli import cli
from zenml.client import Client
from zenml.enums import WebhookType
from zenml.zen_stores.sql_zen_store import SqlZenStore


@pytest.fixture
def clean_client(clean_project: Client) -> Client:
    """Return the active client when it is connected to a server."""
    if isinstance(clean_project.zen_store, SqlZenStore):
        pytest.skip("Webhooks require a REST store.")
    return clean_project


webhook_command = cli.commands["webhook"]
create_command = webhook_command.commands["create"]
describe_command = webhook_command.commands["describe"]
list_command = webhook_command.commands["list"]
update_command = webhook_command.commands["update"]
rotate_secret_command = webhook_command.commands["rotate-secret"]
delete_command = webhook_command.commands["delete"]


def _delete_if_exists(name_or_id: str) -> None:
    client = Client()
    try:
        client.delete_webhook(name_or_id)
    except KeyError:
        pass


def test_webhook_cli_lifecycle(clean_client):
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

        integration = clean_client.get_webhook(name)
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
        updated = clean_client.get_webhook(updated_name)
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
            clean_client.get_webhook(updated.id)
    finally:
        _delete_if_exists(updated_name)
        _delete_if_exists(name)


def test_webhook_cli_does_not_echo_user_supplied_secret(
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

        integration = clean_client.get_webhook(name)
        assert integration.webhook_type == WebhookType.GITHUB
        assert "secret" not in integration.model_dump()
    finally:
        _delete_if_exists(name)
