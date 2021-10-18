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
from hypothesis.strategies import lists, text

import zenml.core.git_wrapper

GITIGNORE_FILENAME = ".gitignore"


def test_no_exception_raised_if_repository_is_valid_git_repository(tmp_path):
    """Test whether class instantiation works when valid git repository present"""
    Repo.init(tmp_path)
    git_instance = zenml.core.git_wrapper.GitWrapper(tmp_path)
    assert git_instance.repo_path == tmp_path
    assert git_instance.repo_path.exists()
    assert git_instance.repo_path.is_dir()
    assert git_instance.git_root_path == str(
        tmp_path / zenml.core.git_wrapper.GIT_FOLDER_NAME
    )
    assert isinstance(git_instance.git_repo, Repo)


def test_exception_raised_if_repo_is_not_a_git_repository(tmp_path):
    """Initialization of GitWrapper class should raise an exception
    if directory is not a git repository"""
    with pytest.raises(InvalidGitRepositoryError):
        zenml.core.git_wrapper.GitWrapper(tmp_path)


@pytest.fixture(scope="module")
@given(non_path=text(min_size=1))
def test_exception_raised_if_repo_path_does_not_exist(tmp_path, non_path):
    """Initialization of GitWrapper class should raise an exception
    if the repository path does not exist"""
    not_a_path = tmp_path / non_path
    with pytest.raises(NoSuchPathError):
        zenml.core.git_wrapper.GitWrapper(not_a_path)


@pytest.fixture(scope="module")
@given(sample_items=lists(text()))
def test_creating_gitignore_with_items_when_none_exists(tmp_path, sample_items):
    """Test whether creating a gitignore file with items works when no gitignore file exists"""
    Repo.init(tmp_path)
    git_instance = zenml.core.git_wrapper.GitWrapper(tmp_path)
    try:
        git_instance.add_gitignore(sample_items())
    except Exception as e:
        assert False, f"Exception raised: {e}"


@pytest.fixture(scope="module")
@given(sample_items=lists(text()))
def test_appending_items_to_gitignore_when_it_already_exists_returns_no_exceptions(
    tmp_path, sample_items
):
    """Test whether appending items to gitignore file works when gitignore file already exists"""
    git_instance = zenml.core.git_wrapper.GitWrapper(tmp_path)
    with open(tmp_path / GITIGNORE_FILENAME, "w") as gitignore_file:
        gitignore_file.write(text())
        try:
            git_instance.add_gitignore(sample_items())
        except Exception as e:
            assert False, f"Exception raised: {e}"


def test_items_appended_correctly_to_gitignore_file_when_no_file_exists(
    tmp_path,
):
    """Test items are correctly to gitignore file"""
    test_items = ["an item", "another item"]
    file_contents = """

# ZenML
an item
another item"""

    Repo.init(tmp_path)
    git_instance = zenml.core.git_wrapper.GitWrapper(tmp_path)
    git_instance.add_gitignore(test_items)
    with open(tmp_path / GITIGNORE_FILENAME, "r") as gitignore_file:
        assert gitignore_file.read() == file_contents


def test_items_appended_correctly_to_gitignore_file_when_file_already_exists(
    tmp_path,
):
    """NotImplementError is thrown when append_file method is called"""
    test_items = ["an item", "another item"]
    Repo.init(tmp_path)
    git_instance = zenml.core.git_wrapper.GitWrapper(tmp_path)
    with open(tmp_path / GITIGNORE_FILENAME, "w") as _:
        with pytest.raises(NotImplementedError):
            git_instance.add_gitignore(test_items)
