#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
from click.testing import CliRunner

from zenml.cli.cli import cli
from zenml.client import Client
from zenml.zen_stores.base_zen_store import ADMIN_ROLE, DEFAULT_USERNAME

SAMPLE_USER = "aria"


@pytest.fixture()
def client_with_sample_user(clean_client: Client) -> Client:
    """Fixture to get a clean global configuration and repository for an
    individual test.

    Args:
        clean_client: Clean client
    """
    clean_client.create_user(name=SAMPLE_USER, password="catnip")
    return clean_client


# ----- #
# USERS #
# ----- #


def test_create_user_with_password_succeeds(
    clean_client,
) -> None:
    """Test that creating a new user succeeds."""
    user_create_command = cli.commands["user"].commands["create"]
    runner = CliRunner()
    result = runner.invoke(
        user_create_command,
        ["aria", "--password=thesupercat"],
    )
    assert result.exit_code == 0


def test_create_user_with_initial_role_succeeds(
    clean_client,
) -> None:
    """Test that creating a new user succeeds."""
    user_create_command = cli.commands["user"].commands["create"]
    runner = CliRunner()
    result = runner.invoke(
        user_create_command,
        ["aria", "--password=thesupercat", f"--role={ADMIN_ROLE}"],
    )
    assert result.exit_code == 0


def test_update_user_with_new_name_succeeds(
    client_with_sample_user,
) -> None:
    """Test that creating a new user succeeds."""
    user_update_command = cli.commands["user"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        user_update_command,
        [SAMPLE_USER, "--name=blupus"],
    )
    assert result.exit_code == 0


def test_update_user_with_new_full_name_succeeds(
    client_with_sample_user,
) -> None:
    """Test that creating a new user succeeds."""
    user_update_command = cli.commands["user"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        user_update_command,
        [SAMPLE_USER, "--full_name='Aria Vanquisher of Treats'"],
    )


def test_update_user_with_new_email_succeeds(
    client_with_sample_user,
) -> None:
    """Test that creating a new user succeeds."""
    user_update_command = cli.commands["user"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        user_update_command,
        [SAMPLE_USER, "--email='aria@catnip.io'"],
    )


def test_update_default_user_name_fails(
    clean_client,
) -> None:
    """Test that updating the name of the default user fails."""
    user_update_command = cli.commands["user"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        user_update_command,
        [DEFAULT_USERNAME, "--name='blupus'"],
    )

    assert result.exit_code == 1


def test_update_default_user_metadata_succeeds(
    clean_client,
) -> None:
    """Test that updating the name of the default user fails."""
    user_update_command = cli.commands["user"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        user_update_command,
        [DEFAULT_USERNAME,
         "--full_name='De Fault'",
         "--email=default@zenml.io"],
    )

    assert result.exit_code == 0
