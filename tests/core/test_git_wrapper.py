#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
from git.exc import InvalidGitRepositoryError, NoSuchPathError
from git.repo.base import Repo
from hypothesis import given
from hypothesis.strategies import text

from zenml.core import git_wrapper


def test_no_exception_raised_if_repository_is_valid_git_repository(tmp_path):
    """Test whether class instantiation works when valid git repository present"""
    Repo.init(tmp_path)
    git_instance = git_wrapper.GitWrapper(tmp_path)
    assert git_instance.repo_path == tmp_path
    assert git_instance.repo_path.exists()
    assert git_instance.repo_path.is_dir()
    assert git_instance.git_root_path == str(
        tmp_path / git_wrapper.GIT_FOLDER_NAME
    )
    assert isinstance(git_instance.git_repo, Repo)


def test_exception_raised_if_repo_is_not_a_git_repository(tmp_path):
    """Initialization of GitWrapper class should raise an exception
    if directory is not a git repository"""
    with pytest.raises(InvalidGitRepositoryError):
        git_wrapper.GitWrapper(tmp_path)


@pytest.fixture(scope="module")
@given(non_path=text(min_size=1))
def test_exception_raised_if_repo_path_does_not_exist(tmp_path, non_path):
    """Initialization of GitWrapper class should raise an exception
    if the repository path does not exist"""
    not_a_path = tmp_path / non_path
    with pytest.raises(NoSuchPathError):
        git_wrapper.GitWrapper(not_a_path)
