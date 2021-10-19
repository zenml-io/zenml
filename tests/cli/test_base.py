#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from click.testing import CliRunner

from zenml.cli.base import clean, init
from zenml.exceptions import InitializationException


def test_init_fails_when_repo_path_is_not_git_repo_already(tmp_path):
    """Check that init command raises an InvalidGitRepositoryError
    when executed outside a valid Git repository"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(init, ["--repo_path", str(tmp_path)])
        assert isinstance(result.exception, InitializationException)
        assert f"Initializing at {tmp_path}" in result.output
        assert result.exit_code == 1


# @pytest.mark.xfail()
# # TODO: [HIGH] fix failing test
# def test_init(tmp_path):
#     """Check that init command works as expected inside temporary directory"""
#     runner = CliRunner()
#     with runner.isolated_filesystem():
#         # TODO: [HIGH] add a step that initializes a git repository in the tmp_path dir
#         Repo.init(str(tmp_path))
#         result = runner.invoke(init, ["--repo_path", str(tmp_path)])
#         # assert result.exit_code == 0
#         assert f"Initializing at {tmp_path}" in result.output
#         assert f"ZenML repo initialized at {tmp_path}" in result.output


# @pytest.mark.xfail()
# # TODO: [HIGH] fix failing test
# def test_assertion_error_raised_when_trying_to_init_when_already_initialized(
#     tmp_path,
# ):
#     """Check that an assertion error is raised when trying to initialize
#     a repo that is already initialized"""
#     runner = CliRunner()
#     # initialize the zenml repository
#     runner.invoke(init, ["--repo_path", str(tmp_path)])
#     # run the command a second time in the same directory
#     result = runner.invoke(init, ["--repo_path", str(tmp_path)])
#     assert result.exit_code == 0
#     assert f"{tmp_path} is already initialized!" in result.output
