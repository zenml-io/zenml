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
from pathlib import Path
from typing import List

import click
import pytest
from click.testing import CliRunner
from git.exc import GitCommandError
from git.repo.base import Repo
from packaging.version import parse

from zenml import __version__ as zenml_version_installed
from zenml.cli.example import EXAMPLES_GITHUB_REPO, info, list, pull
from zenml.cli.utils import error, warning
from zenml.constants import APP_NAME, GIT_REPO_URL
from zenml.logger import get_logger
from zenml.utils import path_utils

# from hypothesis import given
# from hypothesis.strategies import text

logger = get_logger(__name__)

ZERO_FIVE_RELEASE_EXAMPLES = ["airflow", "legacy", "quickstart"]
NOT_ZERO_FIVE_RELEASE_EXAMPLES = ["not_airflow", "not_legacy", "not_quickstart"]
BAD_VERSIONS = ["aaa", "999999", "111111"]


class MockGitExamplesHandler(object):
    """Mock of our GitExamplesHandler class. Handles cloning and checking out of
    ZenML Git repository, all managed locally, for the `examples` directory."""

    def __init__(self, redownload: str = "") -> None:
        """Initialize the GitExamplesHandler class."""
        self.clone_repo(redownload)

    def clone_repo(self, redownload_version: str = "") -> None:
        """Clone ZenML git repo into global config directory if not already
        cloned"""
        installed_version = zenml_version_installed
        repo_dir = click.get_app_dir(APP_NAME)
        examples_dir = os.path.join(repo_dir, EXAMPLES_GITHUB_REPO)
        # delete source directory if force redownload is set
        if redownload_version:
            self.delete_example_source_dir(examples_dir)
            installed_version = redownload_version

        config_directory_files = os.listdir(repo_dir)

        if (
            redownload_version
            or EXAMPLES_GITHUB_REPO not in config_directory_files
        ):
            self.clone_from_zero(GIT_REPO_URL, examples_dir)
            repo = Repo(examples_dir)
            self.checkout_repository(repo, installed_version)

    def clone_from_zero(self, git_repo_url: str, local_dir: str) -> None:
        """Basic functionality to clone a repo."""
        try:
            Repo.clone_from(git_repo_url, local_dir, branch="main")
        except KeyboardInterrupt:
            self.delete_example_source_dir(local_dir)
            error("Cancelled download of repository.. Rolled back.")
            return

    def checkout_repository(
        self,
        repository: Repo,
        desired_version: str,
        fallback_to_latest: bool = True,
    ) -> None:
        """Checks out a branch or tag of a git repository

        Args:
            repository: a Git repository reference.
            desired_version: a valid ZenML release version number.
            fallback_to_latest: Whether to default to the latest released
            version or not if `desired_version` does not exist.
        """
        try:
            repository.git.checkout(desired_version)
        except GitCommandError:
            if fallback_to_latest:
                last_release = parse(repository.tags[-1].name)
                repository.git.checkout(last_release)
                warning(
                    f"You just tried to download examples for version "
                    f"{desired_version}. "
                    f"There is no corresponding release or version. We are "
                    f"going to "
                    f"default to the last release: {last_release}"
                )
            else:
                error(
                    f"You just tried to checkout the repository for version "
                    f"{desired_version}. "
                    f"There is no corresponding release or version. Please try "
                    f"again with a version number corresponding to an actual "
                    f"release."
                )
                raise

    def clone_when_examples_already_cloned(
        self, local_dir: str, version: str
    ) -> None:
        """Basic functionality to clone the ZenML examples
        into the global config directory if they are already cloned."""
        local_dir_path = Path(local_dir)
        repo = Repo(str(local_dir_path))
        desired_version = parse(version)
        self.delete_example_source_dir(str(local_dir_path))
        self.clone_from_zero(GIT_REPO_URL, local_dir)
        self.checkout_repository(
            repo, str(desired_version), fallback_to_latest=False
        )

    def get_examples_dir(self) -> str:
        """Return the examples dir"""
        return os.path.join(
            click.get_app_dir(APP_NAME), EXAMPLES_GITHUB_REPO, "examples"
        )

    def get_all_examples(self) -> List[str]:
        """Get all the examples"""
        return [
            name
            for name in sorted(os.listdir(self.get_examples_dir()))
            if (
                not name.startswith(".")
                and not name.startswith("__")
                and not name.startswith("README")
            )
        ]

    def get_example_readme(self, example_path: str) -> str:
        """Get the example README file contents.

        Raises:
            FileNotFoundError: if the file doesn't exist.
        """
        with open(os.path.join(example_path, "README.md")) as readme:
            readme_content = readme.read()
        return readme_content

    def delete_example_source_dir(self, source_path: str) -> None:
        """Clean the example directory. This method checks that we are
        inside the ZenML config directory before performing its deletion.

        Args:
            source_path (str): The path to the example source directory.

        Raises:
            ValueError: If the source_path is not the ZenML config directory.
        """
        config_directory_path = str(
            os.path.join(click.get_app_dir(APP_NAME), EXAMPLES_GITHUB_REPO)
        )
        if source_path == config_directory_path:
            path_utils.rm_dir(source_path)
        else:
            raise ValueError(
                "You can only delete the source directory from your ZenML "
                "config directory"
            )

    def delete_working_directory_examples_folder(self) -> None:
        """Delete the zenml_examples folder from the current working
        directory."""
        cwd_directory_path = os.path.join(os.getcwd(), EXAMPLES_GITHUB_REPO)
        if os.path.exists(cwd_directory_path):
            path_utils.rm_dir(str(cwd_directory_path))


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


@pytest.mark.parametrize("bad_example", NOT_ZERO_FIVE_RELEASE_EXAMPLES)
def test_info_fails_gracefully_when_no_readme_present(
    tmp_path: str, bad_example: str
) -> None:
    """Check info command fails gracefully when bad example given"""
    # get path variables
    repo_dir = click.get_app_dir(APP_NAME)
    examples_dir = os.path.join(repo_dir, EXAMPLES_GITHUB_REPO, "examples")

    runner = CliRunner()
    with runner.isolated_filesystem(tmp_path):
        runner.invoke(pull, ["-f", "-v", "0.5.0"])
        fake_example_path = os.path.join(examples_dir, bad_example)
        os.mkdir(fake_example_path)
        result = runner.invoke(info, [bad_example])
        assert "No README.md file found" in result.output
        os.rmdir(fake_example_path)


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
