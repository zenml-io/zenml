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

from tests.integration.functional.cli.test_utils import (
    create_sample_team,
    create_sample_user,
    sample_name,
    sample_team_name,
    team_create_command,
    team_delete_command,
    team_describe_command,
    team_list_command,
    team_update_command,
    user_create_command,
    user_delete_command,
    user_update_command,
)
from zenml.client import Client
from zenml.zen_stores.base_zen_store import (
    DEFAULT_ADMIN_ROLE,
    DEFAULT_USERNAME,
)

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


def test_create_user_with_initial_role_succeeds() -> None:
    """Test that creating a new user succeeds."""
    runner = CliRunner()
    result = runner.invoke(
        user_create_command,
        [
            sample_name(),
            "--password=thesupercat",
            f"--role={DEFAULT_ADMIN_ROLE}",
        ],
    )
    assert result.exit_code == 0


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


def test_update_user_with_new_email_succeeds() -> None:
    """Test that creating a new user succeeds."""
    u = create_sample_user()
    runner = CliRunner()
    result = runner.invoke(
        user_update_command,
        [u.name, "--email='aria@catnip.io'"],
    )
    assert result.exit_code == 0


def test_update_default_user_name_fails() -> None:
    """Test that updating the name of the default user fails."""
    runner = CliRunner()
    result = runner.invoke(
        user_update_command,
        [DEFAULT_USERNAME, f"--name={sample_name()}"],
    )
    assert result.exit_code == 1


def test_update_default_user_metadata_succeeds() -> None:
    """Test that updating the metadata of the default user succeeds."""
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


def test_delete_default_user_fails() -> None:
    """Test that the default user can't be deleted."""
    runner = CliRunner()
    result = runner.invoke(
        user_delete_command,
        [DEFAULT_USERNAME],
    )

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


# ----- #
# TEAMS #
# ----- #


def test_create_team_succeeds() -> None:
    """Test that creating a new team with users succeeds."""
    u = create_sample_user()
    runner = CliRunner()
    result = runner.invoke(
        team_create_command,
        [sample_team_name(), f"--user={DEFAULT_USERNAME}", f"--user={u.name}"],
    )
    assert result.exit_code == 0


def test_create_team_without_users_succeeds() -> None:
    """Test that creating a new team with users succeeds."""
    runner = CliRunner()
    result = runner.invoke(
        team_create_command,
        [sample_team_name()],
    )
    assert result.exit_code == 0


def test_describe_team_succeeds() -> None:
    """Test that creating a new team with users succeeds."""
    team = create_sample_team()
    runner = CliRunner()
    result = runner.invoke(
        team_describe_command,
        [team.name],
    )
    assert result.exit_code == 0


def test_list_team_succeeds() -> None:
    """Test that creating a new team with users succeeds."""
    create_sample_team()
    runner = CliRunner()
    result = runner.invoke(
        team_list_command,
    )
    assert result.exit_code == 0


def test_update_team_name_succeeds() -> None:
    """Test that creating a new team with users succeeds."""
    team = create_sample_team()
    new_name = sample_team_name()
    runner = CliRunner()
    result = runner.invoke(
        team_update_command, [team.name, f"--name={new_name}"]
    )
    assert result.exit_code == 0
    assert Client().get_team(new_name)


def test_update_team_members_succeeds() -> None:
    """Test that updating a new team with new users succeeds."""
    team = create_sample_team()
    user = create_sample_user()
    runner = CliRunner()
    result = runner.invoke(
        team_update_command, [team.name, f"--add-user={user.name}"]
    )
    assert result.exit_code == 0
    updated_team = Client().get_team(str(team.id))
    assert user.id in updated_team.user_ids


def test_update_team_members_ambiguously_fails() -> None:
    """Test that updating a team with ambiguous instructions fails."""
    team = create_sample_team()
    user = create_sample_user()
    runner = CliRunner()
    result = runner.invoke(
        team_update_command,
        [team.name, f"--add-user={user.name}" f"--remove-user={user.name}"],
    )
    assert result.exit_code == 1
    updated_team = Client().get_team(str(team.id))
    assert set(team.user_ids) == set(updated_team.user_ids)


def test_delete_team_succeeds() -> None:
    """Test that deleting a user succeeds."""
    team = create_sample_team()
    runner = CliRunner()
    result = runner.invoke(
        team_delete_command,
        [team.name],
    )

    assert result.exit_code == 0
