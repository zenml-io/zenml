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

import os

from tests.integration.functional.cli.utils import cleanup_secrets, cli_runner
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
    runner = cli_runner()
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
    runner = cli_runner()
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
    runner = cli_runner()
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


def test_list_secret_works():
    """Test that the secret list command works."""
    import io

    import zenml_cli

    # Save original _original_stdout for cleanup
    original_stdout = zenml_cli._original_stdout

    runner = cli_runner(mix_stderr=False)
    try:
        with cleanup_secrets() as secret_name:
            # Capture clean_output writes by replacing _original_stdout
            # with a StringIO buffer before each CLI invocation
            buffer1 = io.StringIO()
            zenml_cli._original_stdout = buffer1

            result1 = runner.invoke(secret_list_command)
            output1 = buffer1.getvalue() + result1.output

            assert result1.exit_code == 0
            assert secret_name not in output1

            runner.invoke(
                secret_create_command,
                [secret_name, "--test_value=aria", "--test_value2=axl"],
            )

            buffer2 = io.StringIO()
            zenml_cli._original_stdout = buffer2

            result2 = runner.invoke(secret_list_command)
            output2 = buffer2.getvalue() + result2.output

            assert result2.exit_code == 0
            assert secret_name in output2
    finally:
        # Restore original state
        zenml_cli._original_stdout = original_stdout


def test_get_secret_works():
    """Test that the secret get command works."""
    runner = cli_runner()
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
    runner = cli_runner()

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
    runner = cli_runner()
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
    runner = cli_runner()
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


def test_rename_secret_works():
    """Test that the secret rename command works."""
    runner = cli_runner()

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
    runner = cli_runner()
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
    runner = cli_runner()
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
