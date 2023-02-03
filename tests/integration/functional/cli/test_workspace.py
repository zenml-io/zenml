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
    create_sample_workspace,
    sample_workspace_name,
)
from zenml.cli.cli import cli
from zenml.zen_stores.base_zen_store import DEFAULT_WORKSPACE_NAME


def test_create_workspace_succeeds() -> None:
    """Test that creating a new workspace succeeds."""
    workspace_create_command = cli.commands["workspace"].commands["create"]
    runner = CliRunner()
    result = runner.invoke(
        workspace_create_command,
        [sample_workspace_name()],
    )
    assert result.exit_code == 0


def test_create_existing_workspace_fails() -> None:
    """Test that creating an existing workspace fails."""
    p = create_sample_workspace()
    workspace_create_command = cli.commands["workspace"].commands["create"]
    runner = CliRunner()
    result = runner.invoke(
        workspace_create_command,
        [p.name],
    )
    assert result.exit_code == 1


def test_update_existing_workspace_succeeds() -> None:
    """Test that updating an existing workspace succeeds."""
    p = create_sample_workspace()
    workspace_update_command = cli.commands["workspace"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        workspace_update_command,
        [
            p.name,
            f"--name={sample_workspace_name()}",
            "--description='Workspace to ensure world domination for dog-kind.'",
        ],
    )
    assert result.exit_code == 0


def test_update_default_workspace_name_fails() -> None:
    """Test that updating the default workspace fails."""
    workspace_update_command = cli.commands["workspace"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        workspace_update_command,
        [
            DEFAULT_WORKSPACE_NAME,
            "--name=doc_prj",
        ],
    )
    assert result.exit_code == 1


def test_delete_workspace_succeeds() -> None:
    """Test that deleting a workspace succeeds."""
    p = create_sample_workspace()
    workspace_delete_command = cli.commands["workspace"].commands["delete"]
    runner = CliRunner()
    result = runner.invoke(
        workspace_delete_command,
        [
            p.name,
        ],
    )
    assert result.exit_code == 1


def test_delete_default_workspace_fails() -> None:
    """Test that deleting the default workspace fails."""
    workspace_delete_command = cli.commands["workspace"].commands["delete"]
    runner = CliRunner()
    result = runner.invoke(
        workspace_delete_command,
        [
            DEFAULT_WORKSPACE_NAME,
        ],
    )
    assert result.exit_code == 1
