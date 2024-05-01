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
from click.testing import CliRunner

from tests.integration.functional.cli.utils import (
    create_sample_user,
    sample_name,
    user_create_command,
    user_delete_command,
    user_update_command,
)
from zenml.client import Client
from zenml.enums import StoreType

# ----- #
# USERS #
# ----- #


def test_create_user_with_password_succeeds() -> None:
    """Test that creating a new user succeeds."""
    runner = CliRunner()
    result = runner.invoke(
        user_create_command,
        [sample_name(), "--password=thesupercat"],
    )
    assert result.exit_code == 0


def test_create_user_that_exists_fails() -> None:
    """Test that creating a user which exists already, fails."""
    u = create_sample_user()
    runner = CliRunner()
    result = runner.invoke(
        user_create_command,
        [u.name, "--password=thesupercat"],
    )
    assert result.exit_code == 1


def test_update_user_with_new_name_succeeds() -> None:
    """Test that creating a new user succeeds."""
    u = create_sample_user()
    runner = CliRunner()
    result = runner.invoke(
        user_update_command,
        [u.name, f"--name={sample_name()}"],
    )
    assert result.exit_code == 0


def test_update_user_with_new_full_name_succeeds() -> None:
    """Test that creating a new user succeeds."""
    u = create_sample_user()
    runner = CliRunner()
    result = runner.invoke(
        user_update_command,
        [u.name, "--full_name='Aria Vanquisher of Treats'"],
    )
    assert result.exit_code == 0


def test_update_user_with_new_email() -> None:
    """Test that updating the personal details for an account only works locally."""
    u = create_sample_user()
    runner = CliRunner()
    result = runner.invoke(
        user_update_command,
        [u.name, "--email='aria@catnip.io'"],
    )
    if Client().zen_store.type == StoreType.SQL:
        assert result.exit_code == 0
    else:
        assert result.exit_code == 1


def test_delete_user_succeeds() -> None:
    """Test that deleting a user succeeds."""
    u = create_sample_user()
    runner = CliRunner()
    result = runner.invoke(
        user_delete_command,
        [u.name],
    )

    assert result.exit_code == 0
