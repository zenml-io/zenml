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
from zenml.enums import PermissionType
from zenml.zen_stores.base_zen_store import DEFAULT_ADMIN_ROLE, \
    DEFAULT_USERNAME, DEFAULT_PROJECT_NAME

SAMPLE_USER = "aria"
SAMPLE_ROLE = "cat_feeder"
SAMPLE_PROJECT = "cat_prj"


@pytest.fixture()
def client_with_sample_user(clean_client: Client) -> Client:
    """Fixture to get a clean global configuration and repository for an
    individual test.

    Args:
        clean_client: Clean client
    """
    clean_client.create_user(name=SAMPLE_USER, password="catnip")
    return clean_client


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


@pytest.fixture()
def client_with_sample_project(clean_client: Client) -> Client:
    """Fixture to get a global configuration with a  role.

    Args:
        clean_client: Clean client
    """
    clean_client.create_project(
        name=SAMPLE_PROJECT,
        description="This project aims to ensure world domination for all "
                    "cat-kind."
    )
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


def test_create_user_that_exists_fails(
    client_with_sample_user,
) -> None:
    """Test that creating a user which exists already, fails."""
    user_create_command = cli.commands["user"].commands["create"]
    runner = CliRunner()
    result = runner.invoke(
        user_create_command,
        [SAMPLE_USER, "--password=thesupercat"],
    )
    result.exit_code == 1


def test_create_user_with_initial_role_succeeds(
    clean_client,
) -> None:
    """Test that creating a new user succeeds."""
    user_create_command = cli.commands["user"].commands["create"]
    runner = CliRunner()
    result = runner.invoke(
        user_create_command,
        ["aria", "--password=thesupercat", f"--role={DEFAULT_ADMIN_ROLE}"],
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
    assert result.exit_code == 0


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
    assert result.exit_code == 0


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
    """Test that updating the metadata of the default user succeeds."""
    user_update_command = cli.commands["user"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        user_update_command,
        [
            DEFAULT_USERNAME,
            "--full_name='De Fault'",
            "--email=default@zenml.io",
        ],
    )

    assert result.exit_code == 0


def test_delete_default_user_fails(
    clean_client,
) -> None:
    """Test that the default user can't be deleted."""
    user_delete_command = cli.commands["user"].commands["delete"]
    runner = CliRunner()
    result = runner.invoke(
        user_delete_command,
        [DEFAULT_USERNAME],
    )

    assert result.exit_code == 1


def test_delete_sample_user_succeeds(
    client_with_sample_user,
) -> None:
    """Test that deleting a user succeeds."""
    user_delete_command = cli.commands["user"].commands["delete"]
    runner = CliRunner()
    result = runner.invoke(
        user_delete_command,
        [SAMPLE_USER],
    )

    assert result.exit_code == 0


# ----- #
# ROLES #
# ----- #


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
        [SAMPLE_ROLE, f"--name='cat_groomer'"],
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


# -------- #
# PROJECTS #
# -------- #

def test_create_project_succeeds(
    clean_client,
) -> None:
    """Test that creating a new role succeeds."""
    project_create_command = cli.commands["project"].commands["create"]
    runner = CliRunner()
    result = runner.invoke(
        project_create_command,
        [SAMPLE_PROJECT],
    )
    assert result.exit_code == 0


def test_create_existing_project_fails(
    client_with_sample_project,
) -> None:
    """Test that creating a new role succeeds."""
    project_create_command = cli.commands["project"].commands["create"]
    runner = CliRunner()
    result = runner.invoke(
        project_create_command,
        [SAMPLE_PROJECT],
    )
    assert result.exit_code == 1


def test_update_existing_project_succeeds(
    client_with_sample_project,
) -> None:
    """Test that creating a new role succeeds."""
    project_update_command = cli.commands["project"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        project_update_command,
        [
            SAMPLE_PROJECT,
            f"--name=dog_prj",
            f"--description='Project to ensure world domination for dog-kind.'"
        ]
    )
    assert result.exit_code == 0


def test_update_default_project_name_fails(
    clean_client,
) -> None:
    """Test that creating a new role succeeds."""
    project_update_command = cli.commands["project"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        project_update_command,
        [
            DEFAULT_PROJECT_NAME,
            f"--name=doc_prj",
        ]
    )
    assert result.exit_code == 1


def test_delete_project_succeeds(
    client_with_sample_project,
) -> None:
    """Test that creating a new role succeeds."""
    project_delete_command = cli.commands["project"].commands["delete"]
    runner = CliRunner()
    result = runner.invoke(
        project_delete_command,
        [
            SAMPLE_PROJECT,
        ]
    )
    assert result.exit_code == 1


def test_delete_default_project_fails(
    clean_client,
) -> None:
    """Test that creating a new role succeeds."""
    project_delete_command = cli.commands["project"].commands["delete"]
    runner = CliRunner()
    result = runner.invoke(
        project_delete_command,
        [
            DEFAULT_PROJECT_NAME,
        ]
    )
    assert result.exit_code == 1
