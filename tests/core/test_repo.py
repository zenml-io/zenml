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
    assert repo.service is not None
    assert isinstance(repo.service, BaseComponent)
    assert isinstance(repo.service, LocalService)


# def test_get_pipeline_file_paths(repo, monkeypatch):
#     mock_paths = ["pipeline_1.yaml", "pipeline_2.yaml", "awjfof.txt"]

#     def mock_list_dir(dir_path: Text, only_file_names: bool = False):
#         # add a corrupted file into the pipelines
#         return mock_paths

#     monkeypatch.setattr("zenml.utils.path_utils.list_dir", mock_list_dir)

#     paths = repo.get_pipeline_file_paths(only_file_names=True)

#     assert paths == mock_paths[:-1]


# def test_get_pipeline_names(repo):
#     # TODO: This has to be made dynamic once more pipelines come
#     real_p_names = sorted(["csvtest{0}".format(i) for i in range(1, 6)])

#     found_p_names = sorted(repo.get_pipeline_names())

#     assert set(real_p_names) <= set(found_p_names)


# def test_get_pipelines(repo):
#     p_names = sorted(repo.get_pipeline_names())

#     pipelines = repo.get_pipelines()

#     pipelines = sorted(pipelines, key=lambda p: p.name)

#     assert all(p.name == name for p, name in zip(pipelines, p_names))


# def test_get_pipelines_by_type(repo):
#     pipelines = repo.get_pipelines_by_type(type_filter=["training"])

#     pipelines_2 = repo.get_pipelines_by_type(type_filter=["base"])

#     assert len(pipelines) == 5

#     assert not pipelines_2


# def test_get_pipeline_by_name(repo, equal_pipelines):
#     p_names = repo.get_pipeline_names()

#     random_name = random.choice(p_names)
#     cfg_list = [y for y in repo.get_pipeline_file_paths() if random_name in y]

#     cfg = yaml_utils.read_yaml(cfg_list[0])

#     p1 = repo.get_pipeline_by_name(random_name)

#     p2 = BasePipeline.from_config(cfg)

#     assert equal_pipelines(p1, p2, loaded=True)


# def test_get_step_versions(repo):
#     step_versions = repo.get_step_versions()

#     # TODO: Make this less hardcoded
#     steps_used = [
#         "zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser.StandardPreprocesser",
#         "zenml.steps.split.categorical_domain_split_step.CategoricalDomainSplit",
#         "zenml.steps.trainer.tensorflow_trainers.tf_ff_trainer.FeedForwardTrainer",
#     ]

#     current_version = "zenml_" + str(__version__)

#     assert set(steps_used) >= set(step_versions.keys())
#     assert all(current_version in s for s in step_versions.values())


# def test_get_step_by_version(repo):
#     # TODO: Make this less hardcoded
#     steps_used = [
#         "zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser.StandardPreprocesser",
#         "zenml.steps.split.categorical_domain_split_step.CategoricalDomainSplit",
#         "zenml.steps.trainer.tensorflow_trainers.tf_ff_trainer.FeedForwardTrainer",
#     ]

#     random_step = random.choice(steps_used)

#     current_version = "zenml_" + str(__version__)

#     bogus_version = "asdfghjklöä"

#     assert repo.get_step_by_version(random_step, current_version)
#     assert repo.get_step_by_version(random_step, bogus_version) is None


# def test_get_step_versions_by_type(repo):
#     # TODO: Make this less hardcoded
#     steps_used = [
#         "zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser.StandardPreprocesser",
#         "zenml.steps.split.categorical_domain_split_step.CategoricalDomainSplit",
#         "zenml.steps.trainer.tensorflow_trainers.tf_ff_trainer.FeedForwardTrainer",
#     ]

#     random_step = random.choice(steps_used)

#     current_version = "zenml_" + str(__version__)

#     bogus_step = "asdfghjklöä"

#     step_versions = repo.get_step_versions_by_type(random_step)

#     assert step_versions == {current_version}

#     assert repo.get_step_versions_by_type(bogus_step) is None
