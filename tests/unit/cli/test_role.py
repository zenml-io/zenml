#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
from zenml.enums import PermissionType
from zenml.zen_stores.base_zen_store import DEFAULT_ADMIN_ROLE

SAMPLE_ROLE = "cat_feeder"


@pytest.fixture()
def client_with_sample_role(clean_client: Client) -> Client:
    """Fixture to get a global configuration with a  role.

    Args:
        clean_client: Clean client
    """
    clean_client.create_role(
        name=SAMPLE_ROLE, permissions_list=[PermissionType.READ]
    )
    return clean_client


def test_create_role_succeeds(
    clean_client,
) -> None:
    """Test that creating a new role succeeds."""
    role_create_command = cli.commands["role"].commands["create"]
    runner = CliRunner()
    result = runner.invoke(
        role_create_command,
        [SAMPLE_ROLE, f"--permissions={PermissionType.READ}"],
    )
    assert result.exit_code == 0


def test_create_existing_role_fails(
    client_with_sample_role,
) -> None:
    """Test that creating a role that exists fails."""
    role_create_command = cli.commands["role"].commands["create"]
    runner = CliRunner()
    result = runner.invoke(
        role_create_command,
        [SAMPLE_ROLE, "--permissions=read"],
    )
    assert result.exit_code == 1


def test_update_role_permissions_succeeds(
    client_with_sample_role,
) -> None:
    """Test that updating a role succeeds."""
    role_update_command = cli.commands["role"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        role_update_command,
        [SAMPLE_ROLE, f"--add-permission={PermissionType.WRITE.value}"],
    )
    assert result.exit_code == 0


def test_rename_role_succeeds(
    client_with_sample_role,
) -> None:
    """Test that updating a role succeeds."""
    role_update_command = cli.commands["role"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        role_update_command,
        [SAMPLE_ROLE, "--name='cat_groomer'"],
    )
    assert result.exit_code == 0


def test_update_role_conflicting_permissions_fails(
    client_with_sample_role,
) -> None:
    """Test that updating a role succeeds."""
    role_update_command = cli.commands["role"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        role_update_command,
        [
            SAMPLE_ROLE,
            f"--add-permission={PermissionType.WRITE.value}",
            f"--remove-permission={PermissionType.WRITE.value}",
        ],
    )
    assert result.exit_code == 1


def test_update_default_role_fails(
    client_with_sample_role,
) -> None:
    """Test that updating a role succeeds."""
    role_update_command = cli.commands["role"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        role_update_command,
        [
            DEFAULT_ADMIN_ROLE,
            f"--remove-permission={PermissionType.WRITE.value}",
        ],
    )
    assert result.exit_code == 1


def test_delete_role_succeeds(
    client_with_sample_role,
) -> None:
    """Test that deleting a role succeeds."""
    role_update_command = cli.commands["role"].commands["delete"]
    runner = CliRunner()
    result = runner.invoke(
        role_update_command,
        [SAMPLE_ROLE],
    )
    assert result.exit_code == 0


def test_delete_default_role_fails(
    clean_client,
) -> None:
    """Test that deleting a role succeeds."""
    role_update_command = cli.commands["role"].commands["delete"]
    runner = CliRunner()
    result = runner.invoke(
        role_update_command,
        [DEFAULT_ADMIN_ROLE],
    )
    assert result.exit_code == 1
