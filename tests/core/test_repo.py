# Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

# TODO: [MEDIUM] add basic CRUD tests back in

import os
from pathlib import Path

import pytest
from git.repo.base import Repo

import zenml
from zenml.core.base_component import BaseComponent
from zenml.core.constants import ZENML_DIR_NAME
from zenml.core.git_wrapper import GitWrapper
from zenml.core.local_service import LocalService
from zenml.core.repo import Repository
from zenml.stacks.base_stack import BaseStack

# a way to get to the root
ZENML_ROOT = str(Path(zenml.__path__[0]).parent)
TEST_ROOT = os.path.join(ZENML_ROOT, "tests")


def test_repo_init_from_empty_directory_raises_error(tmp_path: str) -> None:
    """Check empty directory"""
    with pytest.raises(FileNotFoundError):
        _ = Repository(os.path.join(tmp_path, "empty_repo"))


def test_initializing_repository_from_root_sets_cwd_as_repo_path() -> None:
    """Check initializing repository from root sets current directory
    as the ZenML repository path"""
    current_dir = os.getcwd()
    os.chdir("/")
    repo = Repository()
    assert repo.path == "/"
    os.chdir(current_dir)


def test_initializing_repository_without_git_repo_does_not_raise_error(
    tmp_path: str,
) -> None:
    """Check initializing repository without git repository does not raise error"""
    repo = Repository(str(tmp_path))
    assert repo.git_wrapper is None


def test_initializing_repo_with_git_repo_present_sets_git_wrapper(
    tmp_path: str,
) -> None:
    """Check initializing repository with git repository sets git wrapper"""
    git_repo_instance = Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    assert repo.git_wrapper is not None
    assert repo.git_wrapper.repo_path == str(tmp_path)
    assert repo.git_wrapper.git_repo == git_repo_instance


def test_initializing_repo_sets_up_service(tmp_path: str) -> None:
    """Check initializing repository sets up service"""
    repo = Repository(str(tmp_path))
    assert repo.service is not None
    assert isinstance(repo.service, BaseComponent)
    assert isinstance(repo.service, LocalService)


def test_repo_double_init(tmp_path: str) -> None:
    """explicitly constructing another repository should fail"""
    _ = Repo.init(tmp_path)
    os.mkdir(os.path.join(tmp_path, ZENML_DIR_NAME))

    with pytest.raises(Exception):
        _ = Repository(str(tmp_path)).init_repo(
            repo_path=tmp_path, analytics_opt_in=False
        )


def test_repo_init_without_git_repo_initialized_raises_error(
    tmp_path: str,
) -> None:
    """Check initializing repository without git repository raises error"""
    with pytest.raises(Exception):
        _ = Repository(str(tmp_path)).init_repo(
            repo_path=tmp_path, analytics_opt_in=False
        )


def test_init_repo_creates_a_zen_folder(tmp_path: str) -> None:
    """Check initializing repository creates a ZenML folder"""
    _ = Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_stack = LocalService().get_stack("local_stack")
    repo.init_repo(
        repo_path=tmp_path, analytics_opt_in=False, stack=local_stack
    )
    assert os.path.exists(os.path.join(tmp_path, ZENML_DIR_NAME))


def test_get_git_wrapper_returns_the_wrapper(tmp_path: str) -> None:
    """Check get_git_wrapper returns the wrapper"""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    assert repo.get_git_wrapper() is not None
    assert repo.get_git_wrapper().git_repo == GitWrapper(tmp_path).git_repo


def test_getting_the_active_service_returns_local_service(
    tmp_path: str,
) -> None:
    """Check getting the active service"""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    assert repo.get_service() is not None
    assert isinstance(repo.get_service(), BaseComponent)
    assert isinstance(repo.get_service(), LocalService)
    assert repo.get_service() == repo.service


def test_getting_active_stack_key_returns_local_stack(
    tmp_path: str,
) -> None:
    """Check getting the active stack key"""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    repo.set_active_stack("local_stack")
    assert repo.get_active_stack_key() == "local_stack"


def test_getting_active_stack_returns_local_stack(
    tmp_path: str,
) -> None:
    """Check getting the active stack"""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    repo.set_active_stack("local_stack")
    assert repo.get_active_stack() == LocalService().get_stack("local_stack")
    assert isinstance(repo.get_active_stack(), BaseStack)


def test_get_pipelines_returns_list(tmp_path: str) -> None:
    """Check get_pipelines returns a list"""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    repo.set_active_stack("local_stack")
    our_pipelines = repo.get_pipelines()
    assert our_pipelines is not None
    assert isinstance(our_pipelines, list)


def test_get_pipelines_returns_same_list_when_stack_specified(tmp_path) -> None:
    """Check get_pipelines returns the same list when stack specified"""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    repo.set_active_stack("local_stack")
    our_pipelines_default = repo.get_pipelines()
    our_pipelines_local = repo.get_pipelines(stack_key="local_stack")
    assert our_pipelines_default == our_pipelines_local


def test_get_pipeline_returns_none_if_non_existent(tmp_path: str) -> None:
    """Check get_pipeline returns None if it doesn't exist"""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    repo.set_active_stack("local_stack")
    our_pipeline = repo.get_pipeline("not_a_pipeline")
    assert our_pipeline is None


def test_get_pipeline_returns_same_when_stack_specified(tmp_path: str) -> None:
    """Check get_pipeline returns the same if stack specified"""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    repo.set_active_stack("local_stack")
    our_pipeline_default = repo.get_pipeline("pipeline_1")
    our_pipeline_local = repo.get_pipeline(
        "pipeline_1", stack_key="local_stack"
    )
    assert our_pipeline_default == our_pipeline_local
