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

import pytest
from click.testing import CliRunner

from zenml.cli.base import clean, init


@pytest.mark.xfail()
# TODO: [HIGH] fix failing test
def test_init_fails_when_repo_path_is_not_git_repo_already(tmp_path):
    """Check that init command raises an InvalidGitRepositoryError
    when executed outside a valid Git repository"""
    runner = CliRunner()
    result = runner.invoke(init, ["--repo_path", str(tmp_path)])
    assert f"Initializing at {tmp_path}" in result.output
    assert result.exit_code == 1
    assert f"{tmp_path} is not a valid git repository!" in result.output


@pytest.mark.xfail()
# TODO: [HIGH] fix failing test
def test_init(tmp_path):
    """Check that init command works as expected inside temporary directory"""
    runner = CliRunner()
    # TODO: [HIGH] add a step that initializes a git repository in the tmp_path dir
    result = runner.invoke(init, ["--repo_path", str(tmp_path)])
    assert result.exit_code == 0
    assert f"Initializing at {tmp_path}" in result.output
    assert f"ZenML repo initialized at {tmp_path}" in result.output


@pytest.mark.xfail()
# TODO: [HIGH] fix failing test
def test_assertion_error_raised_when_trying_to_init_when_already_initialized(
    tmp_path,
):
    """Check that an assertion error is raised when trying to initialize
    a repo that is already initialized"""
    runner = CliRunner()
    # initialize the zenml repository
    runner.invoke(init, ["--repo_path", str(tmp_path)])
    # run the command a second time in the same directory
    result = runner.invoke(init, ["--repo_path", str(tmp_path)])
    assert result.exit_code == 0
    assert f"{tmp_path} is already initialized!" in result.output


def test_clean_only_returns_a_message():
    """Check to make sure that CLI clean invocation only outputs a message"""
    runner = CliRunner()
    result = runner.invoke(clean, ["--yes", "True"])
    assert result.exit_code == 0
    assert "Not implemented for this version" in result.output


def test_clean_checks_before_proceeding_without_explicit_flag():
    """Check to make sure that clean invocation checks before running
    if no explicit flag is passed in"""
    runner = CliRunner()
    result = runner.invoke(clean)
    assert result.exit_code == 0
    assert "Are you sure you want to proceed?" in result.output
