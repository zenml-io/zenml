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
from click.testing import CliRunner

from tests.integration.functional.cli.utils import (
    create_sample_role,
    create_sample_user,
    sample_role_name,
)
from zenml.cli.cli import cli
from zenml.client import Client
from zenml.enums import PermissionType
from zenml.zen_stores.base_zen_store import DEFAULT_ADMIN_ROLE


def test_create_role_succeeds() -> None:
    """Test that creating a new role succeeds."""
    role_create_command = cli.commands["role"].commands["create"]
    runner = CliRunner()
    result = runner.invoke(
        role_create_command,
        [sample_role_name(), f"--permissions={PermissionType.READ}"],
    )
    assert result.exit_code == 0


def test_create_existing_role_fails() -> None:
    """Test that creating a role that exists fails."""
    r = create_sample_role()
    role_create_command = cli.commands["role"].commands["create"]
    runner = CliRunner()
    result = runner.invoke(
        role_create_command,
        [r.name, "--permissions=read"],
    )
    assert result.exit_code == 1


def test_update_role_permissions_succeeds() -> None:
    """Test that updating a role succeeds."""
    r = create_sample_role()
    role_update_command = cli.commands["role"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        role_update_command,
        [r.name, f"--add-permission={PermissionType.WRITE.value}"],
    )
    assert result.exit_code == 0


def test_rename_role_succeeds() -> None:
    """Test that updating a role succeeds."""
    r = create_sample_role()
    role_update_command = cli.commands["role"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        role_update_command,
        [r.name, "--name='cat_groomer'"],
    )
    assert result.exit_code == 0


def test_update_role_conflicting_permissions_fails() -> None:
    """Test that updating a role succeeds."""
    r = create_sample_role()
    role_update_command = cli.commands["role"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        role_update_command,
        [
            r.name,
            f"--add-permission={PermissionType.WRITE.value}",
            f"--remove-permission={PermissionType.WRITE.value}",
        ],
    )
    assert result.exit_code == 1


def test_update_default_role_fails() -> None:
    """Test that updating the default role fails."""
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


def test_delete_role_succeeds() -> None:
    """Test that deleting a role succeeds."""
    r = create_sample_role()
    role_update_command = cli.commands["role"].commands["delete"]
    runner = CliRunner()
    result = runner.invoke(
        role_update_command,
        [r.name],
    )
    assert result.exit_code == 0


def test_delete_default_role_fails() -> None:
    """Test that deleting a role succeeds."""
    role_delete_command = cli.commands["role"].commands["delete"]
    runner = CliRunner()
    result = runner.invoke(
        role_delete_command,
        [DEFAULT_ADMIN_ROLE],
    )
    assert result.exit_code == 1


def test_assign_default_role_to_new_user_succeeds() -> None:
    """Test that deleting a role succeeds."""
    user = create_sample_user()
    role_assign_command = cli.commands["role"].commands["assign"]
    runner = CliRunner()
    result = runner.invoke(
        role_assign_command, [DEFAULT_ADMIN_ROLE, f"--user={user.id}"]
    )
    assert result.exit_code == 0
    assigned_roles = Client().get_user(user.id).roles
    assert len(assigned_roles) == 1
    assert assigned_roles[0].name == DEFAULT_ADMIN_ROLE


def test_assign_role_to_user_twice_fails() -> None:
    """Test that deleting a role succeeds."""
    user = create_sample_user()
    role_assign_command = cli.commands["role"].commands["assign"]
    runner = CliRunner()
    Client().create_user_role_assignment(
        role_name_or_id=DEFAULT_ADMIN_ROLE,
        user_name_or_id=str(user.id),
    )

    result = runner.invoke(
        role_assign_command, [DEFAULT_ADMIN_ROLE, f"--user={user.name}"]
    )
    assert result.exit_code == 1


def test_revoke_role_from_new_user_succeeds() -> None:
    """Test that deleting a role assignment succeeds."""
    user = create_sample_user()
    role_assign_command = cli.commands["role"].commands["assign"]
    runner = CliRunner()
    result = runner.invoke(
        role_assign_command, [DEFAULT_ADMIN_ROLE, f"--user={user.name}"]
    )
    assert result.exit_code == 0
    assigned_roles = Client().get_user(user.id).roles
    assert len(assigned_roles) == 1
    assert assigned_roles[0].name == DEFAULT_ADMIN_ROLE

    role_revoke_command = cli.commands["role"].commands["revoke"]
    runner = CliRunner()
    result = runner.invoke(
        role_revoke_command, [DEFAULT_ADMIN_ROLE, f"--user={user.name}"]
    )
    assert result.exit_code == 0
    assigned_roles = Client().get_user(user.id).roles
    assert len(assigned_roles) == 0
