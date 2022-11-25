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

from tests.unit.cli.test_utils import SAMPLE_WORKSPACE, create_sample_project
from zenml.cli.cli import cli
from zenml.zen_stores.base_zen_store import DEFAULT_WORKSPACE_NAME


def test_create_project_succeeds(
    clean_client,
) -> None:
    """Test that creating a new role succeeds."""
    project_create_command = cli.commands["project"].commands["create"]
    runner = CliRunner()
    result = runner.invoke(
        project_create_command,
        [SAMPLE_WORKSPACE],
    )
    assert result.exit_code == 0


def test_create_existing_project_fails(
    clean_client,
) -> None:
    """Test that creating a new role succeeds."""
    create_sample_project(clean_client)
    project_create_command = cli.commands["project"].commands["create"]
    runner = CliRunner()
    result = runner.invoke(
        project_create_command,
        [SAMPLE_WORKSPACE],
    )
    assert result.exit_code == 1


def test_update_existing_project_succeeds(
    clean_client,
) -> None:
    """Test that creating a new role succeeds."""
    create_sample_project(clean_client)
    project_update_command = cli.commands["project"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        project_update_command,
        [
            SAMPLE_WORKSPACE,
            "--name=dog_prj",
            "--description='Project to ensure world domination for dog-kind.'",
        ],
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
            DEFAULT_WORKSPACE_NAME,
            "--name=doc_prj",
        ],
    )
    assert result.exit_code == 1


def test_delete_project_succeeds(
    clean_client,
) -> None:
    """Test that creating a new role succeeds."""
    create_sample_project(clean_client)
    project_delete_command = cli.commands["project"].commands["delete"]
    runner = CliRunner()
    result = runner.invoke(
        project_delete_command,
        [
            SAMPLE_WORKSPACE,
        ],
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
            DEFAULT_WORKSPACE_NAME,
        ],
    )
    assert result.exit_code == 1
