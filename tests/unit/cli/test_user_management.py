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

from tests.unit.cli.test_utils import (
    SAMPLE_USER,
    create_sample_team,
    create_sample_user,
    team_create_command,
    team_delete_command,
    team_describe_command,
    team_list_command,
    team_update_command,
    user_create_command,
    user_delete_command,
    user_update_command,
)
from zenml.zen_stores.base_zen_store import DEFAULT_ADMIN_ROLE, DEFAULT_USERNAME

# ----- #
# USERS #
# ----- #


def test_create_user_with_password_succeeds(
    clean_client,
) -> None:
    """Test that creating a new user succeeds."""
    runner = CliRunner()
    result = runner.invoke(
        user_create_command,
        ["aria", "--password=thesupercat"],
    )
    assert result.exit_code == 0


def test_create_user_that_exists_fails(
    clean_client,
) -> None:
    """Test that creating a user which exists already, fails."""
    create_sample_user(clean_client)
    runner = CliRunner()
    result = runner.invoke(
        user_create_command,
        [SAMPLE_USER, "--password=thesupercat"],
    )
    assert result.exit_code == 1


def test_create_user_with_initial_role_succeeds(
    clean_client,
) -> None:
    """Test that creating a new user succeeds."""
    runner = CliRunner()
    result = runner.invoke(
        user_create_command,
        ["aria", "--password=thesupercat", f"--role={DEFAULT_ADMIN_ROLE}"],
    )
    assert result.exit_code == 0


def test_update_user_with_new_name_succeeds(
    clean_client,
) -> None:
    """Test that creating a new user succeeds."""
    create_sample_user(clean_client)
    runner = CliRunner()
    result = runner.invoke(
        user_update_command,
        [SAMPLE_USER, "--name=blupus"],
    )
    assert result.exit_code == 0


def test_update_user_with_new_full_name_succeeds(
    clean_client,
) -> None:
    """Test that creating a new user succeeds."""
    create_sample_user(clean_client)
    runner = CliRunner()
    result = runner.invoke(
        user_update_command,
        [SAMPLE_USER, "--full_name='Aria Vanquisher of Treats'"],
    )
    assert result.exit_code == 0


def test_update_user_with_new_email_succeeds(
    clean_client,
) -> None:
    """Test that creating a new user succeeds."""
    create_sample_user(clean_client)
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
    runner = CliRunner()
    result = runner.invoke(
        user_delete_command,
        [DEFAULT_USERNAME],
    )

    assert result.exit_code == 1


def test_delete_sample_user_succeeds(
    clean_client,
) -> None:
    """Test that deleting a user succeeds."""
    create_sample_user(clean_client)
    runner = CliRunner()
    result = runner.invoke(
        user_delete_command,
        [SAMPLE_USER],
    )

    assert result.exit_code == 0


# ----- #
# TEAMS #
# ----- #


def test_create_team_succeeds(
    clean_client,
) -> None:
    """Test that creating a new team with users succeeds."""
    create_sample_user(clean_client)
    runner = CliRunner()
    result = runner.invoke(
        team_create_command,
        ["ZenEmEl", f"--user={DEFAULT_USERNAME}", f"--user={SAMPLE_USER}"],
    )
    assert result.exit_code == 0


def test_create_team_without_users_succeeds(
    clean_client,
) -> None:
    """Test that creating a new team with users succeeds."""
    create_sample_user(clean_client)
    runner = CliRunner()
    result = runner.invoke(
        team_create_command,
        ["ZenEmEl"],
    )
    assert result.exit_code == 0


def test_describe_team_succeeds(
    clean_client,
) -> None:
    """Test that creating a new team with users succeeds."""
    team = create_sample_team(clean_client)
    runner = CliRunner()
    result = runner.invoke(
        team_describe_command,
        [team.name],
    )
    assert result.exit_code == 0


def test_list_team_succeeds(
    clean_client,
) -> None:
    """Test that creating a new team with users succeeds."""
    create_sample_team(clean_client)
    runner = CliRunner()
    result = runner.invoke(
        team_list_command,
    )
    assert result.exit_code == 0


def test_update_team_name_succeeds(
    clean_client,
) -> None:
    """Test that creating a new team with users succeeds."""
    team = create_sample_team(clean_client)
    new_name = "lupines"
    runner = CliRunner()
    result = runner.invoke(
        team_update_command, [team.name, f"--name={new_name}"]
    )
    assert result.exit_code == 0
    assert clean_client.get_team(new_name)


def test_update_team_members_succeeds(
    clean_client,
) -> None:
    """Test that updating a new team with new users succeeds."""
    team = create_sample_team(clean_client)
    user = create_sample_user(clean_client)
    runner = CliRunner()
    result = runner.invoke(
        team_update_command, [team.name, f"--add-user={user.name}"]
    )
    assert result.exit_code == 0
    updated_team = clean_client.get_team(str(team.id))
    assert user.id in updated_team.user_ids


def test_update_team_members_ambiguously_fails(
    clean_client,
) -> None:
    """Test that updating a team with ambiguous instructions fails."""
    team = create_sample_team(clean_client)
    user = create_sample_user(clean_client)
    runner = CliRunner()
    result = runner.invoke(
        team_update_command,
        [team.name, f"--add-user={user.name}" f"--remove-user={user.name}"],
    )
    assert result.exit_code == 1
    updated_team = clean_client.get_team(str(team.id))
    assert set(team.user_ids) == set(updated_team.user_ids)


def test_delete_team_succeeds(
    clean_client,
) -> None:
    """Test that deleting a user succeeds."""
    team = create_sample_team(clean_client)
    runner = CliRunner()
    result = runner.invoke(
        team_delete_command,
        [team.name],
    )

    assert result.exit_code == 0
