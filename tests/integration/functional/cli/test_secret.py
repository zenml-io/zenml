#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Tests for the Secret Store CLI."""

import json
import os

import pytest
from click.testing import CliRunner

from tests.integration.functional.cli.utils import (
    capture_clean_stdout,
    cleanup_secrets,
)
from tests.integration.functional.utils import sample_name
from zenml.cli.cli import cli
from zenml.client import Client

secret_create_command = cli.commands["secret"].commands["create"]
secret_list_command = cli.commands["secret"].commands["list"]
secret_get_command = cli.commands["secret"].commands["get"]
secret_update_command = cli.commands["secret"].commands["update"]
secret_delete_command = cli.commands["secret"].commands["delete"]
secret_rename_command = cli.commands["secret"].commands["rename"]
secret_export_command = cli.commands["secret"].commands["export"]


def test_create_secret():
    """Test that creating a new secret succeeds."""
    runner = CliRunner()
    with cleanup_secrets() as secret_name:
        result = runner.invoke(
            secret_create_command,
            [secret_name, "--test_value=aria", "--test_value2=axl"],
        )
        assert result.exit_code == 0
        client = Client()
        created_secret = client.get_secret(secret_name)
        assert created_secret is not None
        assert created_secret.values["test_value"].get_secret_value() == "aria"
        assert created_secret.values["test_value2"].get_secret_value() == "axl"


def test_create_private_secret():
    """Test creating private secrets."""
    runner = CliRunner()
    with cleanup_secrets() as secret_name:
        result = runner.invoke(
            secret_create_command,
            [secret_name, "--test_value=aria", "--private"],
        )
        assert result.exit_code == 0
        client = Client()
        created_secret = client.get_secret(secret_name)
        assert created_secret is not None
        assert created_secret.values["test_value"].get_secret_value() == "aria"
        assert created_secret.private is True


def test_create_secret_with_values():
    """Tests creating a secret with values."""
    runner = CliRunner()
    with cleanup_secrets() as secret_name:
        result = runner.invoke(
            secret_create_command,
            [
                secret_name,
                '--values={"test_value":"aria","test_value2":"axl"}',
            ],
        )
        assert result.exit_code == 0
        client = Client()
        created_secret = client.get_secret(secret_name)
        assert created_secret is not None
        assert created_secret.values["test_value"].get_secret_value() == "aria"


def test_create_secret_dry_run_outputs_preview_and_does_not_create():
    """Tests secret create dry-run output and no-op behavior."""
    runner = CliRunner()
    with cleanup_secrets("dry-run-preview") as secret_name:
        with capture_clean_stdout() as buffer:
            result = runner.invoke(
                secret_create_command,
                [
                    secret_name,
                    "--username=dry-run-user",
                    "--password=dry-run-password",
                    "--dry-run",
                ],
                env={"ZENML_CLI_MACHINE_MODE": "true"},
            )

        assert result.exit_code == 0
        payload = json.loads(buffer.getvalue())
        assert payload["dry_run"] is True
        assert payload["action"] == "secret.create"
        assert payload["target"]["name"] == secret_name
        assert payload["validated_input"]["value_keys"] == [
            "username",
            "password",
        ]
        assert payload["details"]["values_redacted"] == {
            "username": "***",
            "password": "***",
        }
        assert "dry-run-user" not in buffer.getvalue()
        assert "dry-run-password" not in buffer.getvalue()

        with pytest.raises(KeyError):
            Client().get_secret(
                secret_name,
                allow_partial_name_match=False,
                allow_partial_id_match=False,
            )


def test_create_secret_dry_run_blocks_interactive():
    """Tests that dry-run rejects interactive secret creation."""
    runner = CliRunner()
    with cleanup_secrets() as secret_name:
        result = runner.invoke(
            secret_create_command,
            [secret_name, "--interactive", "--dry-run"],
            env={"ZENML_CLI_MACHINE_MODE": "true"},
        )

    assert result.exit_code != 0
    payload = json.loads(result.output.strip())
    assert payload["type"] == "DryRunPromptError"
    assert "Dry-run cannot prompt" in payload["error"]


def test_list_secret_works():
    """Test that the secret list command works."""
    runner = CliRunner()
    with cleanup_secrets() as secret_name:
        with capture_clean_stdout() as buffer1:
            result1 = runner.invoke(secret_list_command)
            output1 = buffer1.getvalue() + result1.output

        assert result1.exit_code == 0
        assert secret_name not in output1

        runner.invoke(
            secret_create_command,
            [secret_name, "--test_value=aria", "--test_value2=axl"],
        )

        with capture_clean_stdout() as buffer2:
            result2 = runner.invoke(secret_list_command)
            output2 = buffer2.getvalue() + result2.output

        assert result2.exit_code == 0
        assert secret_name in output2


def test_get_secret_works():
    """Test that the secret get command works."""
    runner = CliRunner()
    with cleanup_secrets() as secret_name:
        result1 = runner.invoke(
            secret_get_command,
            [secret_name],
        )
        assert result1.exit_code != 0
        assert "Could not find a secret" in result1.output

        runner.invoke(
            secret_create_command,
            [secret_name, "--test_value=aria", "--test_value2=axl"],
        )

        result2 = runner.invoke(
            secret_get_command,
            [secret_name],
        )
        assert result2.exit_code == 0
        assert "test_value" in result2.output
        assert "test_value2" in result2.output


def test_get_secret_with_prefix_works():
    """Test that the secret get command works with a prefix."""
    runner = CliRunner()

    with cleanup_secrets() as secret_name_prefix:
        result1 = runner.invoke(
            secret_get_command,
            [secret_name_prefix],
        )
        assert result1.exit_code != 0
        assert "Could not find a secret" in result1.output

        runner.invoke(
            secret_create_command,
            [
                sample_name(secret_name_prefix),
                "--test_value=aria",
                "--test_value2=axl",
            ],
        )

        result2 = runner.invoke(
            secret_get_command,
            [secret_name_prefix],
        )
        assert result2.exit_code == 0
        assert "test_value" in result2.output
        assert "test_value2" in result2.output


def test_get_private_secret():
    """Test that the secret get command works with a private secret."""
    runner = CliRunner()
    with cleanup_secrets() as secret_name:
        result1 = runner.invoke(
            secret_get_command,
            [secret_name],
        )
        assert result1.exit_code != 0
        assert "Could not find a secret" in result1.output

        result1 = runner.invoke(
            secret_get_command,
            [secret_name, "--private", "true"],
        )
        assert result1.exit_code != 0
        assert "Could not find a secret" in result1.output

        result1 = runner.invoke(
            secret_get_command,
            [secret_name, "--private", "false"],
        )
        assert result1.exit_code != 0
        assert "Could not find a secret" in result1.output

        runner.invoke(
            secret_create_command,
            [
                secret_name,
                "--test_value=aria",
                "--test_value2=axl",
                "--private",
            ],
        )

        result2 = runner.invoke(
            secret_get_command,
            [secret_name],
        )
        assert result2.exit_code == 0
        assert "test_value" in result2.output
        assert "test_value2" in result2.output

        result2 = runner.invoke(
            secret_get_command,
            [secret_name, "--private", "true"],
        )
        assert result2.exit_code == 0
        assert "test_value" in result2.output
        assert "test_value2" in result2.output

        result3 = runner.invoke(
            secret_get_command,
            [secret_name, "--private", "false"],
        )
        assert result3.exit_code != 0
        assert "Could not find a secret" in result3.output


def test_get_secret_outputs_json_error_in_machine_mode():
    """Test structured JSON errors for missing secrets in machine mode."""
    runner = CliRunner()
    with cleanup_secrets() as secret_name:
        result = runner.invoke(
            secret_get_command,
            [secret_name],
            env={"ZENML_CLI_MACHINE_MODE": "true"},
        )

    assert result.exit_code != 0
    payload = json.loads(result.output.strip())
    assert "Could not find a secret" in payload["error"]
    assert payload["type"] == "error"
    assert payload["exit_code"] == 1


def test_update_secret_dry_run_outputs_preview_and_does_not_update():
    """Tests secret update dry-run output and no-op behavior."""
    runner = CliRunner()
    with cleanup_secrets() as secret_name:
        create_result = runner.invoke(
            secret_create_command,
            [
                secret_name,
                "--username=aria",
                "--legacy=old-value",
                "--private",
            ],
        )
        assert create_result.exit_code == 0

        with capture_clean_stdout() as buffer:
            result = runner.invoke(
                secret_update_command,
                [
                    secret_name,
                    "--token=new-token",
                    "--remove-keys",
                    "legacy",
                    "--dry-run",
                ],
                env={"ZENML_CLI_MACHINE_MODE": "true"},
            )

        assert result.exit_code == 0
        payload = json.loads(buffer.getvalue())
        assert payload["dry_run"] is True
        assert payload["action"] == "secret.update"
        assert payload["target"]["name"] == secret_name
        assert payload["validated_input"]["add_or_update_keys"] == ["token"]
        assert payload["validated_input"]["remove_keys"] == ["legacy"]
        assert payload["details"]["existing_private"] is True
        assert payload["details"]["values_redacted"] == {"token": "***"}
        assert "new-token" not in buffer.getvalue()

        secret = Client().get_secret(secret_name)
        assert secret.private is True
        assert secret.values["username"].get_secret_value() == "aria"
        assert secret.values["legacy"].get_secret_value() == "old-value"
        assert "token" not in secret.values


def _check_deleting_nonexistent_secret_fails(runner, secret_name):
    """Helper method to check that deleting a nonexistent secret fails."""
    result1 = runner.invoke(
        secret_delete_command,
        [secret_name, "-y"],
    )
    assert result1.exit_code != 0
    assert "not exist" in result1.output


def test_delete_secret_works():
    """Test that the secret delete command works."""
    runner = CliRunner()
    with cleanup_secrets() as secret_name:
        _check_deleting_nonexistent_secret_fails(runner, secret_name)

        runner.invoke(
            secret_create_command,
            [secret_name, "--test_value=aria", "--test_value2=axl"],
        )

        result2 = runner.invoke(
            secret_delete_command,
            [secret_name, "-y"],
        )
        assert result2.exit_code == 0
        assert "deleted" in result2.output

        _check_deleting_nonexistent_secret_fails(runner, secret_name)


def test_delete_secret_auto_confirms_in_machine_mode():
    """Test that machine mode auto-confirms secret deletion."""
    runner = CliRunner()
    client = Client()
    with cleanup_secrets() as secret_name:
        runner.invoke(
            secret_create_command,
            [secret_name, "--test_value=aria", "--test_value2=axl"],
        )

        result = runner.invoke(
            secret_delete_command,
            [secret_name],
            env={"ZENML_CLI_MACHINE_MODE": "true"},
        )

        assert result.exit_code == 0
        assert "deleted" in result.output
        assert not client.list_secrets(name=secret_name).items


def test_rename_secret_works():
    """Test that the secret rename command works."""
    runner = CliRunner()

    with cleanup_secrets() as secret_name:
        with cleanup_secrets() as new_secret_name:
            result1 = runner.invoke(
                secret_rename_command,
                [secret_name, "-n", new_secret_name],
            )
            assert result1.exit_code != 0
            assert "not exist" in result1.output

            runner.invoke(
                secret_create_command,
                [secret_name, "--test_value=aria", "--test_value2=axl"],
            )

            result2 = runner.invoke(
                secret_rename_command,
                [secret_name, "-n", new_secret_name],
            )
            assert result2.exit_code == 0
            assert "renamed" in result2.output

            result3 = runner.invoke(
                secret_get_command,
                [new_secret_name],
            )
            assert result3.exit_code == 0
            assert "test_value" in result3.output
            assert "test_value2" in result3.output

            result4 = runner.invoke(
                secret_rename_command,
                [new_secret_name, "-n", "name"],
            )
            assert result4.exit_code != 0
            assert "cannot be called" in result4.output


def test_update_secret_works():
    """Test that the secret update command works."""
    runner = CliRunner()
    client = Client()

    with cleanup_secrets() as secret_name:
        result1 = runner.invoke(
            secret_update_command,
            [secret_name, "--test_value=aria", "--test_value2=axl"],
        )
        assert result1.exit_code != 0
        assert "not exist" in result1.output

        runner.invoke(
            secret_create_command,
            [secret_name, "--test_value=aria", "--test_value2=axl"],
        )

        result2 = runner.invoke(
            secret_update_command,
            [secret_name, "--test_value=blupus", "--test_value2=kami"],
        )
        assert result2.exit_code == 0
        assert "updated" in result2.output

        updated_secret = client.get_secret(secret_name)
        assert updated_secret is not None
        assert updated_secret.secret_values["test_value"] == "blupus"
        assert updated_secret.secret_values["test_value2"] == "kami"

        result3 = runner.invoke(
            secret_update_command,
            [
                secret_name,
                '--values={"test_value":"json", "test_value2":"yaml"}',
            ],
        )
        assert result3.exit_code == 0
        assert "updated" in result3.output

        updated_secret = client.get_secret(secret_name)
        assert updated_secret is not None
        assert updated_secret.secret_values["test_value"] == "json"
        assert updated_secret.secret_values["test_value2"] == "yaml"

        result4 = runner.invoke(
            secret_update_command,
            [secret_name, "-r", "test_value2"],
        )
        assert result4.exit_code == 0
        assert "updated" in result4.output
        newly_updated_secret = client.get_secret(secret_name)
        assert newly_updated_secret is not None
        assert "test_value2" not in newly_updated_secret.secret_values

        result5 = runner.invoke(
            secret_update_command,
            [secret_name, "--private", "true"],
        )
        assert result5.exit_code == 0
        assert "updated" in result5.output
        final_updated_secret = client.get_secret(secret_name)
        assert final_updated_secret is not None
        assert final_updated_secret.private is True


def test_export_import_secret():
    """Test that exporting and importing a secret works."""
    runner = CliRunner()
    with cleanup_secrets() as secret_name:
        # Create a secret
        result = runner.invoke(
            secret_create_command,
            [secret_name, "--test_value=aria", "--test_value2=axl"],
        )
        assert result.exit_code == 0

        filename = f"{secret_name}.yaml"

        try:
            # Export the secret
            result = runner.invoke(secret_export_command, [secret_name])
            assert result.exit_code == 0
            assert os.path.exists(filename)

            # Import the secret
            new_secret_name = f"{secret_name}_new"
            result = runner.invoke(
                secret_create_command, [new_secret_name, "-v", f"@{filename}"]
            )
            assert result.exit_code == 0

        finally:
            if os.path.exists(filename):
                os.remove(filename)

        # Check that the secret was imported correctly
        client = Client()
        created_secret = client.get_secret(secret_name)
        imported_secret = client.get_secret(new_secret_name)
        assert created_secret.values == imported_secret.values
