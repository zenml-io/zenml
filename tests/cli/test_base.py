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

import os

import pytest
from click.testing import CliRunner
from git import Repo

from zenml.cli.base import init
from zenml.core.constants import ZENML_DIR_NAME
from zenml.exceptions import InitializationException

ZENML_INIT_FILENAMES = [
    "zenservice.json",
    "artifact_stores",
    "metadata_stores",
    "orchestrators",
]


@pytest.mark.xfail()
def test_assertion_error_raised_when_trying_to_init_when_already_initialized(
    tmp_path,
):
    """Check that an assertion error is raised when trying to initialize
    a repo that is already initialized"""
    runner = CliRunner()
    Repo.init(path=str(tmp_path))
    runner.invoke(init, ["--repo_path", str(tmp_path)])
    with pytest.raises(AssertionError):
        runner.invoke(init, ["--repo_path", str(tmp_path)])


def test_init_fails_when_repo_path_is_not_git_repo_already(tmp_path):
    """Check that init command raises an InvalidGitRepositoryError
    when executed outside a valid Git repository"""
    runner = CliRunner()
    result = runner.invoke(init, ["--repo_path", str(tmp_path)])
    assert isinstance(result.exception, InitializationException)


@pytest.mark.xfail()
@pytest.mark.parametrize("zenml_init_filenames", ZENML_INIT_FILENAMES)
def test_init(tmp_path, zenml_init_filenames):
    """Check that init command works as expected inside temporary directory"""
    runner = CliRunner()
    Repo.init(path=str(tmp_path))
    runner.invoke(init, ["--repo_path", str(tmp_path)])
    dir_files = os.listdir(tmp_path)
    assert ZENML_DIR_NAME in dir_files
    zen_files = os.listdir(os.path.join(tmp_path, ZENML_DIR_NAME))
    assert zenml_init_filenames in zen_files
