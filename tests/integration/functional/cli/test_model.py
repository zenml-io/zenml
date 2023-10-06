#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Test zenml Model Control Plane CLI commands."""


from uuid import uuid4

import pytest
from click.testing import CliRunner

from tests.integration.functional.cli.conftest import NAME, PREFIX
from zenml.cli.cli import cli


def test_model_list(clean_workspace_with_models):
    """Test that zenml model list does not fail."""
    runner = CliRunner()
    list_command = cli.commands["model"].commands["list"]
    result = runner.invoke(list_command)
    assert result.exit_code == 0


def test_model_create_short_names(clean_workspace_with_models):
    """Test that zenml model create does not fail with short names."""
    runner = CliRunner()
    create_command = cli.commands["model"].commands["register"]
    result = runner.invoke(
        create_command,
        args=[
            "-n",
            PREFIX + str(uuid4()),
            "-l",
            "a",
            "-d",
            "b",
            "-a",
            "c",
            "-u",
            "d",
            "--tradeoffs",
            "f",
            "-e",
            "g",
            "--limitations",
            "e",
            "-t",
            "i",
            "-t",
            "j",
            "-t",
            "k",
        ],
    )
    assert result.exit_code == 0


def test_model_create_full_names(clean_workspace_with_models):
    """Test that zenml model create does not fail with full names."""
    runner = CliRunner()
    create_command = cli.commands["model"].commands["register"]
    result = runner.invoke(
        create_command,
        args=[
            "--name",
            PREFIX + str(uuid4()),
            "--limitations",
            "a",
            "--description",
            "b",
            "--audience",
            "c",
            "--use-cases",
            "d",
            "--tradeoffs",
            "f",
            "--ethical",
            "g",
            "--limitations",
            "e",
            "--tag",
            "i",
            "--tag",
            "j",
            "--tag",
            "k",
        ],
    )
    assert result.exit_code == 0


def test_model_create_only_required(clean_workspace_with_models):
    """Test that zenml model create does not fail."""
    runner = CliRunner()
    create_command = cli.commands["model"].commands["register"]
    result = runner.invoke(
        create_command,
        args=["--name", PREFIX + str(uuid4())],
    )
    assert result.exit_code == 0


def test_model_create_without_required_fails(clean_workspace_with_models):
    """Test that zenml model create fails."""
    runner = CliRunner()
    create_command = cli.commands["model"].commands["register"]
    result = runner.invoke(
        create_command,
    )
    assert result.exit_code != 0


def test_model_delete_found(clean_workspace_with_models):
    """Test that zenml model delete does not fail."""
    runner = CliRunner()
    name = PREFIX + str(uuid4())
    create_command = cli.commands["model"].commands["register"]
    runner.invoke(
        create_command,
        args=["--name", name],
    )
    delete_command = cli.commands["model"].commands["delete"]
    result = runner.invoke(
        delete_command,
        args=[name, "-y"],
    )
    assert result.exit_code == 0


def test_model_delete_not_found(clean_workspace_with_models):
    """Test that zenml model delete fail."""
    runner = CliRunner()
    name = PREFIX + str(uuid4())
    delete_command = cli.commands["model"].commands["delete"]
    result = runner.invoke(
        delete_command,
        args=[name],
    )
    assert result.exit_code != 0


def test_model_version_list(clean_workspace_with_models):
    """Test that zenml model version list does not fail."""
    runner = CliRunner()
    list_command = cli.commands["model"].commands["version"].commands["list"]
    result = runner.invoke(
        list_command,
        args=[NAME],
    )
    assert result.exit_code == 0


def test_model_version_list_fails_on_bad_model(clean_workspace_with_models):
    """Test that zenml model version list fails."""
    runner = CliRunner()
    list_command = cli.commands["model"].commands["version"].commands["list"]
    result = runner.invoke(
        list_command,
        args=["foo"],
    )
    assert result.exit_code != 0


@pytest.mark.parametrize(
    "command",
    ("artifacts", "deployments", "model_objects", "runs"),
)
def test_model_version_links_list(command: str, clean_workspace_with_models):
    """Test that zenml model version artifacts list fails."""
    runner = CliRunner()
    list_command = cli.commands["model"].commands["version"].commands[command]
    result = runner.invoke(
        list_command,
        args=[NAME, "1"],
    )
    assert result.exit_code == 0


def test_model_version_update(clean_workspace_with_models):
    """Test that zenml model version stage update pass."""
    runner = CliRunner()
    update_command = (
        cli.commands["model"].commands["version"].commands["update"]
    )
    result = runner.invoke(
        update_command,
        args=[NAME, "1", "-s", "production"],
    )
    assert result.exit_code == 0
