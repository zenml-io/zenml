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
import pytest
from click.testing import CliRunner

from zenml.cli.cli import cli
from zenml.client import Client
from zenml.enums import SecretScope

TEST_SECRET_NAME = "test_secret"
TEST_SECRET_NAME_PREFIX = TEST_SECRET_NAME[:4]

secret_create_command = cli.commands["secret"].commands["create"]
secret_list_command = cli.commands["secret"].commands["list"]
secret_get_command = cli.commands["secret"].commands["get"]
secret_update_command = cli.commands["secret"].commands["update"]
secret_delete_command = cli.commands["secret"].commands["delete"]
secret_rename_command = cli.commands["secret"].commands["rename"]


def test_create_secret(clean_client):
    """Test that creating a new secret succeeds."""
    runner = CliRunner()
    result = runner.invoke(
        secret_create_command,
        [TEST_SECRET_NAME, "--test_value=aria", "--test_value2=axl"],
    )
    assert result.exit_code == 0
    client = Client()
    created_secret = client.get_secret(TEST_SECRET_NAME)
    assert created_secret is not None
    assert created_secret.values["test_value"].get_secret_value() == "aria"
    assert created_secret.values["test_value2"].get_secret_value() == "axl"


def test_create_secret_with_scope(clean_client):
    """Tests creating a secret with a scope."""
    runner = CliRunner()
    result = runner.invoke(
        secret_create_command,
        [TEST_SECRET_NAME, "--test_value=aria", f"--scope={SecretScope.USER}"],
    )
    assert result.exit_code == 0
    client = Client()
    created_secret = client.get_secret(TEST_SECRET_NAME)
    assert created_secret is not None
    assert created_secret.values["test_value"].get_secret_value() == "aria"
    assert created_secret.scope == SecretScope.USER


def test_create_fails_with_bad_scope(clean_client):
    """Tests that creating a secret with a bad scope fails."""
    runner = CliRunner()
    result = runner.invoke(
        secret_create_command,
        [TEST_SECRET_NAME, "--test_value=aria", "--scope=axl_scope"],
    )
    assert result.exit_code != 0
    client = Client()
    with pytest.raises(KeyError):
        client.get_secret(TEST_SECRET_NAME)


def test_list_secret_works(clean_client):
    """Test that the secret list command works."""
    runner = CliRunner()
    result1 = runner.invoke(
        secret_list_command,
    )
    assert result1.exit_code == 0
    assert TEST_SECRET_NAME not in result1.output

    runner = CliRunner()
    runner.invoke(
        secret_create_command,
        [TEST_SECRET_NAME, "--test_value=aria", "--test_value2=axl"],
    )

    result2 = runner.invoke(
        secret_list_command,
    )
    assert result2.exit_code == 0
    assert TEST_SECRET_NAME in result2.output


def test_get_secret_works(clean_client):
    """Test that the secret get command works."""
    runner = CliRunner()
    result1 = runner.invoke(
        secret_get_command,
        [TEST_SECRET_NAME],
    )
    assert result1.exit_code != 0
    assert "not exist" in result1.output

    runner.invoke(
        secret_create_command,
        [TEST_SECRET_NAME, "--test_value=aria", "--test_value2=axl"],
    )

    result2 = runner.invoke(
        secret_get_command,
        [TEST_SECRET_NAME],
    )
    assert result2.exit_code == 0
    assert "test_value" in result2.output
    assert "test_value2" in result2.output


def test_get_secret_with_prefix_works(clean_client):
    """Test that the secret get command works with a prefix."""
    runner = CliRunner()
    result1 = runner.invoke(
        secret_get_command,
        [TEST_SECRET_NAME_PREFIX],
    )
    assert result1.exit_code != 0
    assert "not exist" in result1.output

    runner.invoke(
        secret_create_command,
        [TEST_SECRET_NAME, "--test_value=aria", "--test_value2=axl"],
    )

    result2 = runner.invoke(
        secret_get_command,
        [TEST_SECRET_NAME_PREFIX],
    )
    assert result2.exit_code == 0
    assert "test_value" in result2.output
    assert "test_value2" in result2.output


def test_get_secret_with_scope_works(clean_client):
    """Test that the secret get command works with a scope."""
    runner = CliRunner()
    result1 = runner.invoke(
        secret_get_command,
        [TEST_SECRET_NAME, f"--scope={SecretScope.USER}"],
    )
    assert result1.exit_code != 0
    assert "not exist" in result1.output

    runner.invoke(
        secret_create_command,
        [
            TEST_SECRET_NAME,
            "--test_value=aria",
            "--test_value2=axl",
            "--scope=user",
        ],
    )

    result2 = runner.invoke(
        secret_get_command,
        [TEST_SECRET_NAME, f"--scope={SecretScope.USER}"],
    )
    assert result2.exit_code == 0
    assert "test_value" in result2.output
    assert "test_value2" in result2.output

    result3 = runner.invoke(
        secret_get_command,
        [TEST_SECRET_NAME, f"--scope={SecretScope.WORKSPACE}"],
    )
    assert result3.exit_code != 0
    assert "not exist" in result3.output


def _check_deleting_nonexistent_secret_fails(runner):
    """Helper method to check that deleting a nonexistent secret fails."""
    result1 = runner.invoke(
        secret_delete_command,
        [TEST_SECRET_NAME, "-y"],
    )
    assert result1.exit_code != 0
    assert "not exist" in result1.output


def test_delete_secret_works(clean_client):
    """Test that the secret delete command works."""
    runner = CliRunner()
    _check_deleting_nonexistent_secret_fails(runner)

    runner.invoke(
        secret_create_command,
        [TEST_SECRET_NAME, "--test_value=aria", "--test_value2=axl"],
    )

    result2 = runner.invoke(
        secret_delete_command,
        [TEST_SECRET_NAME, "-y"],
    )
    assert result2.exit_code == 0
    assert "deleted" in result2.output

    _check_deleting_nonexistent_secret_fails(runner)


def test_rename_secret_works(clean_client):
    """Test that the secret rename command works."""
    A_GOOD_NEW_NAME = "axl"

    runner = CliRunner()
    result1 = runner.invoke(
        secret_rename_command,
        [TEST_SECRET_NAME, "-n", A_GOOD_NEW_NAME],
    )
    assert result1.exit_code != 0
    assert "not exist" in result1.output

    runner.invoke(
        secret_create_command,
        [TEST_SECRET_NAME, "--test_value=aria", "--test_value2=axl"],
    )

    result2 = runner.invoke(
        secret_rename_command,
        [TEST_SECRET_NAME, "-n", A_GOOD_NEW_NAME],
    )
    assert result2.exit_code == 0
    assert "renamed" in result2.output

    result3 = runner.invoke(
        secret_get_command,
        [A_GOOD_NEW_NAME],
    )
    assert result3.exit_code == 0
    assert "test_value" in result3.output
    assert "test_value2" in result3.output

    result4 = runner.invoke(
        secret_rename_command,
        [TEST_SECRET_NAME, "-n", "name"],
    )
    assert result4.exit_code != 0
    assert "cannot be called" in result4.output


def test_update_secret_works(clean_client):
    """Test that the secret update command works."""
    runner = CliRunner()
    client = Client()

    result1 = runner.invoke(
        secret_update_command,
        [TEST_SECRET_NAME, "--test_value=aria", "--test_value2=axl"],
    )
    assert result1.exit_code != 0
    assert "not exist" in result1.output

    runner.invoke(
        secret_create_command,
        [TEST_SECRET_NAME, "--test_value=aria", "--test_value2=axl"],
    )

    result2 = runner.invoke(
        secret_update_command,
        [TEST_SECRET_NAME, "--test_value=blupus", "--test_value2=kami"],
    )
    assert result2.exit_code == 0
    assert "updated" in result2.output

    updated_secret = client.get_secret(TEST_SECRET_NAME)
    assert updated_secret is not None
    assert updated_secret.secret_values["test_value"] == "blupus"
    assert updated_secret.secret_values["test_value2"] == "kami"

    result3 = runner.invoke(
        secret_update_command,
        [TEST_SECRET_NAME, "-r", "test_value2"],
    )
    assert result3.exit_code == 0
    assert "updated" in result3.output
    newly_updated_secret = client.get_secret(TEST_SECRET_NAME)
    assert newly_updated_secret is not None
    assert "test_value2" not in newly_updated_secret.secret_values

    result4 = runner.invoke(
        secret_update_command,
        [TEST_SECRET_NAME, "-s", "user"],
    )
    assert result4.exit_code == 0
    assert "updated" in result4.output
    final_updated_secret = client.get_secret(TEST_SECRET_NAME)
    assert final_updated_secret is not None
    assert final_updated_secret.scope == SecretScope.USER
