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

from tests.integration.functional.cli.test_utils import (
    create_sample_project,
    sample_project_name,
)
from zenml.cli.cli import cli
from zenml.zen_stores.base_zen_store import DEFAULT_PROJECT_NAME


def test_create_project_succeeds() -> None:
    """Test that creating a new project succeeds."""
    project_create_command = cli.commands["project"].commands["create"]
    runner = CliRunner()
    result = runner.invoke(
        project_create_command,
        [sample_project_name()],
    )
    assert result.exit_code == 0


def test_create_existing_project_fails() -> None:
    """Test that creating an existing project fails."""
    p = create_sample_project()
    project_create_command = cli.commands["project"].commands["create"]
    runner = CliRunner()
    result = runner.invoke(
        project_create_command,
        [p.name],
    )
    assert result.exit_code == 1


def test_update_existing_project_succeeds() -> None:
    """Test that updating an existing project succeeds."""
    p = create_sample_project()
    project_update_command = cli.commands["project"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        project_update_command,
        [
            p.name,
            f"--name={sample_project_name()}",
            "--description='Project to ensure world domination for dog-kind.'",
        ],
    )
    assert result.exit_code == 0


def test_update_default_project_name_fails() -> None:
    """Test that updating the default project fails."""
    project_update_command = cli.commands["project"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        project_update_command,
        [
            DEFAULT_PROJECT_NAME,
            "--name=doc_prj",
        ],
    )
    assert result.exit_code == 1


def test_delete_project_succeeds() -> None:
    """Test that deleting a project succeeds."""
    p = create_sample_project()
    project_delete_command = cli.commands["project"].commands["delete"]
    runner = CliRunner()
    result = runner.invoke(
        project_delete_command,
        [
            p.name,
        ],
    )
    assert result.exit_code == 1


def test_delete_default_project_fails() -> None:
    """Test that deleting the default project fails."""
    project_delete_command = cli.commands["project"].commands["delete"]
    runner = CliRunner()
    result = runner.invoke(
        project_delete_command,
        [
            DEFAULT_PROJECT_NAME,
        ],
    )
    assert result.exit_code == 1
