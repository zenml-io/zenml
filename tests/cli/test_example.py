#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:

#       http://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import os

import click
import pytest
from click.testing import CliRunner
from git.repo.base import Repo

from zenml import __version__ as running_zenml_version
from zenml.cli.example import EXAMPLES_GITHUB_REPO, info, list, pull
from zenml.constants import APP_NAME
from zenml.logger import get_logger

# from hypothesis import given
# from hypothesis.strategies import text


logger = get_logger(__name__)

ZERO_FIVE_RELEASE_EXAMPLES = ["airflow", "legacy", "quickstart"]
NOT_ZERO_FIVE_RELEASE_EXAMPLES = ["not_airflow", "not_legacy", "not_quickstart"]
BAD_VERSIONS = ["aaa", "999999", "111111"]


@pytest.mark.parametrize("example", ZERO_FIVE_RELEASE_EXAMPLES)
def test_list_returns_three_examples_for_0_5_release(example: str) -> None:
    """Check the examples returned from zenml example list"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(pull, ["-f", "-v", "0.5.0"])
        result = runner.invoke(list)
        assert result.exit_code == 0
        assert example in result.output


@pytest.mark.parametrize("example", ZERO_FIVE_RELEASE_EXAMPLES)
def test_info_returns_zero_exit_code(example: str) -> None:
    """Check info command exits without errors"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(pull, ["-f", "-v", "0.5.0"])
        result = runner.invoke(info, [example])
        assert result.exit_code == 0


def test_pull_command_returns_zero_exit_code() -> None:
    """Check pull command exits without errors"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(pull, ["-f", "-v", running_zenml_version])
        assert result.exit_code == 0


def test_pull_earlier_version_returns_zero_exit_code() -> None:
    """Check pull of earlier version exits without errors"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(pull, ["-f", "-v", "0.5.1"])
        result = runner.invoke(pull, ["-f", "-v", "0.3.8"])
        assert result.exit_code == 0


@pytest.mark.parametrize("bad_version", BAD_VERSIONS)
def test_pull_of_nonexistent_version_fails(bad_version: str) -> None:
    """When trying to pull a version that doesn't exist,
    ZenML handles the failed cloning"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(pull, ["-f", "-v", bad_version])
        assert result.exit_code != 0


def test_pull_of_higher_version_than_currently_in_global_config_store() -> None:
    """Check what happens when (valid) desired version for a force redownload
    is higher than the latest version stored in the global config"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(pull, ["-f", "-v", "0.5.0"])
        result = runner.invoke(pull, ["-f", "-v", "0.5.1"])
        assert result.exit_code == 0


@pytest.mark.parametrize("bad_version", BAD_VERSIONS)
def test_pull_of_bad_version_when_valid_version_already_exists(
    bad_version: str,
) -> None:
    """When user has valid version present in global config, attempts to force
    redownload invalid versions should fail"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(pull, ["-f", "-v", "0.5.1"])
        result = runner.invoke(pull, ["-f", "-v", bad_version])
        assert result.exit_code != 0


def test_pull_without_any_flags_should_exit_without_errors() -> None:
    """Check pull command exits without errors"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result1 = runner.invoke(pull)
        assert result1.exit_code == 0


@pytest.mark.parametrize("example", ZERO_FIVE_RELEASE_EXAMPLES)
def test_info_echos_out_readme_content(example: str) -> None:
    """Check that info subcommand displays readme content"""
    # TODO: [LOW] make test handle rich markdown output
    runner = CliRunner()
    with runner.isolated_filesystem():
        # setup the test
        runner.invoke(pull, ["-f", "-v", "0.5.0"])

        # get path variables
        repo_dir = click.get_app_dir(APP_NAME)
        examples_dir = os.path.join(repo_dir, EXAMPLES_GITHUB_REPO, "examples")
        readme_path = os.path.join(examples_dir, example, "README.md")

        result = runner.invoke(info, [example])
        assert result.exit_code == 0
        assert example in result.output
        with open(readme_path) as f:
            for line in f.read().splitlines():
                assert line in result.output
        examples_dir = os.path.join(os.getcwd(), EXAMPLES_GITHUB_REPO)
        assert example in os.listdir(examples_dir)


@pytest.mark.parametrize("bad_example", NOT_ZERO_FIVE_RELEASE_EXAMPLES)
def test_info_fails_gracefully_when_bad_example_given(
    tmp_path: str, bad_example: str
) -> None:
    """Check info command fails gracefully when bad example given"""
    runner = CliRunner()
    with runner.isolated_filesystem(tmp_path):
        runner.invoke(pull, ["-f", "-v", "0.5.0"])
        result = runner.invoke(info, [bad_example])
        assert (
            f"Example {bad_example} is not one of the available options."
            in result.output
        )
        assert bad_example not in os.listdir(tmp_path)


def test_user_has_latest_zero_five_version_but_wants_zero_five_one():
    """Test the scenario where the latest version available to the user is 0.5.0
    but the user wants to download 0.5.1. In this case, it should redownload
    and try to checkout the desired version."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # save the repository currently on the local system
        current_saved_global_examples_path = os.path.join(
            click.get_app_dir(APP_NAME), EXAMPLES_GITHUB_REPO
        )
        current_saved_global_examples_repo = Repo(
            current_saved_global_examples_path
        )
        # reset the repo such that it has 0.5.0 as the latest version
        current_saved_global_examples_repo.git.reset("--hard", "0.5.0")
        runner.invoke(pull, ["-f", "-v", "0.5.1"])
        result = runner.invoke(list)
        assert "airflow_local" in result.output
