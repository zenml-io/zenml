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
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from zenml.cli.cli import cli
from zenml.cli.stack_recipes import STACK_RECIPES_REPO_DIR
from zenml.utils import io_utils

SERVER_START_STOP_TIMEOUT = 30


@pytest.fixture(scope="module")
def cli_runner():
    """Fixture to get a CliRunner instance."""
    return CliRunner()


def test_stack_recipes_pull(clean_client, cli_runner):
    """Test pulling stack recipes."""
    pull_command = cli.commands["stack"].commands["recipe"].commands["pull"]
    cli_runner.invoke(pull_command)

    global_repo_dir = io_utils.get_global_config_directory()
    stack_recipes_dir = Path(
        os.path.join(global_repo_dir, STACK_RECIPES_REPO_DIR)
    )
    assert stack_recipes_dir.exists()

    # Test that the stack recipes are pulled locally
    local_repo_dir = Path(os.path.join(os.getcwd(), STACK_RECIPES_REPO_DIR))

    assert local_repo_dir.exists()


def test_stack_recipes_list(clean_client, cli_runner):
    """Test listing stack recipes."""
    list_command = cli.commands["stack"].commands["recipe"].commands["list"]
    result = cli_runner.invoke(list_command)

    assert "aws-minimal" in result.output


def test_stack_recipes_clean(clean_client, cli_runner):
    """Test cleaning stack recipes."""
    pull_command = cli.commands["stack"].commands["recipe"].commands["pull"]
    cli_runner.invoke(pull_command)

    clean_command = cli.commands["stack"].commands["recipe"].commands["clean"]
    cli_runner.invoke(clean_command, ["--yes"])

    # Test that the stack recipes are deleted locally
    local_repo_dir = Path(os.path.join(os.getcwd(), STACK_RECIPES_REPO_DIR))

    # assert that the local repo dir does not exist
    assert not local_repo_dir.exists()
