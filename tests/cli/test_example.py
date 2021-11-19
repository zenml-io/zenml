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

from datetime import datetime
from typing import List

import pytest

from zenml.cli.example import ExamplesRepo, GitExamplesHandler
from zenml.logger import get_logger
from zenml.utils import path_utils

logger = get_logger(__name__)

ZERO_FIVE_ZERO_RELEASE_EXAMPLES = ["legacy", "quickstart"]
NOT_ZERO_FIVE_RELEASE_EXAMPLES = ["not_airflow", "not_legacy", "not_quickstart"]
BAD_VERSIONS = ["aaa", "999999", "111111"]


class MockCommit:
    def __init__(self, committed_datetime: datetime):
        self.committed_datetime = committed_datetime


class MockTag:
    def __init__(self, name: str, commit: MockCommit) -> None:
        self.name = name
        self.commit = commit


class MockRepo:
    def __init__(self, tags: List[MockTag]) -> None:
        self.tags = tags


@pytest.fixture(scope="session")
def cloned_repo_path(tmp_path) -> None:
    """Returns the path of a temporary cloned repository"""
    examples_repo_dir = GitExamplesHandler().examples_repo.examples_dir
    path_utils.copy_dir(examples_repo_dir, tmp_path)
    return tmp_path


def test_check_if_latest_release_works(monkeypatch):
    """Tests to see that latest_release gets the latest_release"""
    mock_tags = [
        MockTag("0.5.0", MockCommit(datetime(2021, 5, 17))),
        MockTag("0.5.1", MockCommit(datetime(2021, 7, 17))),
        MockTag("0.5.2", MockCommit(datetime(2021, 9, 17))),
    ]
    mock_repo = MockRepo(tags=mock_tags)
    examples_repo = ExamplesRepo(cloning_path="")
    monkeypatch.setattr(examples_repo, "repo", mock_repo)

    assert examples_repo.latest_release == "0.5.2"


def test_pull(monkeypatch, mocker, cloned_repo_path) -> None:
    """Check what happens when (valid) desired version for a force redownload
    is higher than the latest version stored in the global config"""
    git_examples_handler = GitExamplesHandler()
    mock_repo = ExamplesRepo(cloning_path="")
    mocker.patch.object(mock_repo.latest_release, return_value="0.5.2")
    mocker.patch.object(mock_repo.is_cloned, return_value=True)
    mocker.patch.object(mock_repo.clone, return_value=None)
    mocker.patch.object(mock_repo.delete, return_value=None)
    mocker.patch.object(mock_repo.checkout, return_value=None)
    monkeypatch.setattr(git_examples_handler, "examples_repo", mock_repo)


# make a fixture that gives us the path to the repository that is cloned
# (copy repository to a temp path + then return that path)
# monkey patch the cloning_path + the cloning + is_cloned


# @pytest.mark.parametrize("example", ZERO_FIVE_ZERO_RELEASE_EXAMPLES)
# def test_list_returns_three_examples_for_0_5_release(
#     example: str, monkey_patch_clone_repo
# ) -> None:
#     """Check the examples returned from zenml example list"""
#     runner = CliRunner()
#     with runner.isolated_filesystem():
#         runner.invoke(mock_pull, ["-f", "-v", "0.5.0"])
#         result = runner.invoke(list)
#         assert result.exit_code == 0
#         assert example in result.output


# @pytest.mark.parametrize("example", ZERO_FIVE_ZERO_RELEASE_EXAMPLES)
# def test_info_returns_zero_exit_code(
#     example: str, monkey_patch_clone_repo
# ) -> None:
#     """Check info command exits without errors"""
#     runner = CliRunner()
#     with runner.isolated_filesystem():
#         runner.invoke(mock_pull, ["-f", "-v", "0.5.0"])
#         result = runner.invoke(mock_info, [example])
#         assert result.exit_code == 0


# def test_pull_earlier_version_returns_zero_exit_code(
#     monkey_patch_clone_repo,
# ) -> None:
#     """Check pull of earlier version exits without errors"""
#     runner = CliRunner()
#     with runner.isolated_filesystem():
#         runner.invoke(mock_pull, ["-f", "-v", "0.5.1"])
#         result = runner.invoke(pull, ["-f", "-v", "0.3.8"])
#         assert result.exit_code == 0


# def test_pull_of_higher_version_than_currently_in_global_config_store(
#     monkey_patch_clone_repo,
# ) -> None:
#     """Check what happens when (valid) desired version for a force redownload
#     is higher than the latest version stored in the global config"""
#     runner = CliRunner()
#     with runner.isolated_filesystem():
#         runner.invoke(mock_pull, ["-f", "-v", "0.5.0"])
#         result = runner.invoke(pull, ["-f", "-v", "0.5.1"])
#         assert result.exit_code == 0


# @pytest.mark.parametrize("bad_version", BAD_VERSIONS)
# def test_pull_of_bad_version_when_valid_version_already_exists(
#     bad_version: str, monkey_patch_clone_repo
# ) -> None:
#     """When user has valid version present in global config, attempts to force
#     redownload invalid versions should fail"""
#     runner = CliRunner()
#     with runner.isolated_filesystem():
#         runner.invoke(mock_pull, ["-f", "-v", "0.5.1"])
#         result = runner.invoke(mock_pull, ["-f", "-v", bad_version])
#         assert result.exit_code != 0


# def test_pull_without_any_flags_should_exit_without_errors(
#     monkey_patch_clone_repo,
# ) -> None:
#     """Check pull command exits without errors"""
#     runner = CliRunner()
#     with runner.isolated_filesystem():
#         result1 = runner.invoke(mock_pull)
#         assert result1.exit_code == 0


# @pytest.mark.parametrize("example", ZERO_FIVE_ZERO_RELEASE_EXAMPLES)
# def test_info_echos_out_readme_content(
#     example: str, monkey_patch_clone_repo
# ) -> None:
#     """Check that info subcommand displays readme content"""
#     # TODO [LOW]: make test handle rich markdown output
#     runner = CliRunner()
#     with runner.isolated_filesystem():
#         # setup the test
#         runner.invoke(mock_pull, ["-f", "-v", "0.5.0"])

#         # get path variables
#         repo_dir = click.get_app_dir(APP_NAME)
#         examples_dir = os.path.join(repo_dir, EXAMPLES_GITHUB_REPO, "examples")
#         readme_path = os.path.join(examples_dir, example, "README.md")

#         result = runner.invoke(mock_info, [example])
#         assert result.exit_code == 0
#         assert example in result.output
#         with open(readme_path) as f:
#             for line in f.read().splitlines():
#                 assert line in result.output
#         examples_dir = os.path.join(os.getcwd(), EXAMPLES_GITHUB_REPO)
#         assert example in os.listdir(examples_dir)


# @pytest.mark.parametrize("bad_example", NOT_ZERO_FIVE_RELEASE_EXAMPLES)
# def test_info_fails_gracefully_when_bad_example_given(
#     tmp_path: str, bad_example: str, monkey_patch_clone_repo
# ) -> None:
#     """Check info command fails gracefully when bad example given"""
#     runner = CliRunner()
#     with runner.isolated_filesystem(tmp_path):
#         runner.invoke(mock_pull, ["-f", "-v", "0.5.0"])
#         result = runner.invoke(mock_info, [bad_example])
#         assert (
#             f"Example {bad_example} is not one of the available options."
#             in result.output
#         )
#         assert bad_example not in os.listdir(tmp_path)


# @pytest.mark.parametrize("bad_example", NOT_ZERO_FIVE_RELEASE_EXAMPLES)
# def test_info_fails_gracefully_when_no_readme_present(
#     tmp_path: str, bad_example: str, monkey_patch_clone_repo
# ) -> None:
#     """Check info command fails gracefully when bad example given"""
#     # get path variables
#     repo_dir = click.get_app_dir(APP_NAME)
#     examples_dir = os.path.join(repo_dir, EXAMPLES_GITHUB_REPO, "examples")

#     runner = CliRunner()
#     with runner.isolated_filesystem(tmp_path):
#         runner.invoke(mock_pull, ["-f", "-v", "0.5.0"])
#         fake_example_path = os.path.join(examples_dir, bad_example)
#         os.mkdir(fake_example_path)
#         result = runner.invoke(mock_info, [bad_example])
#         assert "No README.md file found" in result.output
#         os.rmdir(fake_example_path)


# class MockGitExamplesHandler(GitExamplesHandler):
#     """Mock of our GitExamplesHandler class. Handles cloning and checking out of
#     ZenML Git repository, all managed locally, for the `examples` directory."""

#     def __init__(self, redownload: str = "") -> None:
#         """Initialize the GitExamplesHandler class."""
#         self.clone_repo(redownload)

#     def clone_repo(self, redownload_version: str = "") -> None:
#         """Clone ZenML git repo into global config directory if not already
#         cloned"""
#         installed_version = zenml_version_installed
#         repo_dir = click.get_app_dir(APP_NAME)
#         examples_dir = os.path.join(repo_dir, EXAMPLES_GITHUB_REPO)
#         # delete source directory if force redownload is set
#         if redownload_version:
#             # self.delete_example_source_dir(examples_dir)
#             installed_version = redownload_version

#         config_directory_files = os.listdir(repo_dir)

#         if EXAMPLES_GITHUB_REPO not in config_directory_files:
#             self.clone_from_zero(GIT_REPO_URL, examples_dir)
#             repo = Repo(examples_dir)
#             self.checkout_repository(repo, installed_version)

#     def clone_from_zero(self, git_repo_url: str, local_dir: str) -> None:
#         """Basic functionality to clone a repo."""
#         try:
#             Repo.clone_from(git_repo_url, local_dir, branch="main")
#         except KeyboardInterrupt:
#             self.delete_example_source_dir(local_dir)
#             error("Cancelled download of repository.. Rolled back.")
#             return

#     def clone_when_examples_already_cloned(
#         self, local_dir: str, version: str
#     ) -> None:
#         """Basic functionality to clone the ZenML examples
#         into the global config directory if they are already cloned."""
#         local_dir_path = Path(local_dir)
#         repo = Repo(str(local_dir_path))
#         desired_version = parse(version)
#         if EXAMPLES_GITHUB_REPO in os.listdir(str(local_dir_path)):
#             # self.delete_example_source_dir(str(local_dir_path))
#             # self.clone_from_zero(GIT_REPO_URL, local_dir)
#             self.checkout_repository(
#                 repo, str(desired_version), fallback_to_latest=False
#             )


# mock_pass_git_examples_handler = click.make_pass_decorator(
#     MockGitExamplesHandler, ensure=True
# )


# @example.command(
#     help="Pull examples straight into your current working directory."
# )
# @mock_pass_git_examples_handler
# @click.argument("example_name", required=False, default=None)
# @click.option(
#     "--force",
#     "-f",
#     is_flag=True,
#     help="Force the redownload of the examples folder to the ZenML config "
#     "folder.",
# )
# @click.option(
#     "--version",
#     "-v",
#     type=click.STRING,
#     default=zenml_version_installed,
#     help="The version of ZenML to use for the force-redownloaded examples.",
# )
# def mock_pull(
#     git_examples_handler: MockGitExamplesHandler,
#     example_name: str,
#     force: bool,
#     version: str,
# ) -> None:
#     """Pull examples straight into your current working directory.
#     Add the flag --force or -f to redownload all the examples afresh.
#     Use the flag --version or -v and the version number to specify
#     which version of ZenML you wish to use for the examples."""
#     if force:
#         repo_dir = click.get_app_dir(APP_NAME)
#         examples_dir = os.path.join(repo_dir, EXAMPLES_GITHUB_REPO)
#         declare(f"Recloning ZenML repo for version {version}...")
#         git_examples_handler.clone_when_examples_already_cloned(
#             examples_dir, version
#         )
#         warning("Deleting examples from current working directory...")
#         # git_examples_handler.delete_working_directory_examples_folder()

#     examples_dir = git_examples_handler.get_examples_dir()
#     examples = (
#         git_examples_handler.get_all_examples()
#         if not example_name
#         else [example_name]
#     )
#     # Create destination dir.
#     dst = os.path.join(os.getcwd(), "zenml_examples")
#     path_utils.create_dir_if_not_exists(dst)

#     # Pull specified examples.
#     for eg in examples:
#         dst_dir = os.path.join(dst, eg)
#         # Check if example has already been pulled before.
#         if path_utils.file_exists(dst_dir) and confirmation(
#             f"Example {eg} is already pulled. "
#             f"Do you wish to overwrite the directory?"
#         ):
#             path_utils.rm_dir(dst_dir)

#         declare(f"Pulling example {eg}...")
#         src_dir = os.path.join(examples_dir, eg)
#         path_utils.copy_dir(src_dir, dst_dir)

#         declare(f"Example pulled in directory: {dst_dir}")

#     declare("")
#     declare(
#         "Please read the README.md file in the respective example "
#         "directory to find out more about the example"
#     )


# @example.command(help="Find out more about an example.")
# @mock_pass_git_examples_handler
# @click.argument("example_name")
# def mock_info(
#     git_examples_handler: MockGitExamplesHandler, example_name: str
# ) -> None:
#     """Find out more about an example."""
#     # TODO: [MEDIUM] fix markdown formatting so that it looks nicer (not a
#     #  pure .md dump)
#     example_dir = os.path.join(
#         git_examples_handler.get_examples_dir(), example_name
#     )
#     try:
#         readme_content = git_examples_handler.get_example_readme(example_dir)
#         click.echo(readme_content)
#     except FileNotFoundError:
#         if path_utils.file_exists(example_dir) and path_utils.is_dir(
#             example_dir
#         ):
#             error(f"No README.md file found in {example_dir}")
#         else:
#             error(
#                 f"Example {example_name} is not one of the available options."
#                 f"\nTo list all available examples, type: `zenml example list`"
#             )


# @pytest.fixture()
# def monkey_patch_clone_repo(monkeypatch) -> None:
#     """Mock the clone_repo method"""
#     monkeypatch.setattr(
#         GitExamplesHandler,
#         "clone_repo",
#         MockGitExamplesHandler.clone_repo,
#     )
#     monkeypatch.setattr(
#         GitExamplesHandler,
#         "clone_when_examples_already_cloned",
#         MockGitExamplesHandler.clone_when_examples_already_cloned,
#     )
