#  Copyright (c) maiot GmbH 2021. All Rights Reserved.
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
import random
from pathlib import Path
from typing import Text

import pytest

import zenml
from zenml.datasources import BaseDatasource
from zenml.pipelines import BasePipeline
from zenml.repo import Repository
from zenml.utils import yaml_utils
from zenml.version import __version__

# Nicholas a way to get to the root
ZENML_ROOT = str(Path(zenml.__path__[0]).parent)
TEST_ROOT = os.path.join(ZENML_ROOT, "tests")


def test_repo_double_init():
    # explicitly constructing another repository should fail
    with pytest.raises(Exception):
        _ = Repository()


def test_get_datasources(repo):
    ds_list = repo.get_datasources()

    assert "my_csv_datasource" in [x.name for x in ds_list]


def test_get_datasource_by_name(repo):
    assert repo.get_datasource_by_name("my_csv_datasource")

    fake_ds = repo.get_datasource_by_name("ds_123")

    assert fake_ds is None


def test_get_datasource_names(repo):
    # TODO [LOW]: Automatically expand when new datasource tests are added!
    test_ds_names = ["my_csv_datasource", "image_ds_local", "image_ds_gcp",
                     "json_ds"]

    ds_names = repo.get_datasource_names()

    assert set(test_ds_names) <= set(ds_names)


def test_get_pipeline_file_paths(repo, monkeypatch):
    mock_paths = ["pipeline_1.yaml", "pipeline_2.yaml", "awjfof.txt"]

    def mock_list_dir(dir_path: Text, only_file_names: bool = False):
        # add a corrupted file into the pipelines
        return mock_paths

    monkeypatch.setattr("zenml.utils.path_utils.list_dir",
                        mock_list_dir)

    paths = repo.get_pipeline_file_paths(only_file_names=True)

    assert paths == mock_paths[:-1]


def test_get_pipeline_names(repo):
    # TODO: This has to be made dynamic once more pipelines come
    real_p_names = sorted(["csvtest{0}".format(i) for i in range(1, 6)])

    found_p_names = sorted(repo.get_pipeline_names())

    assert set(real_p_names) <= set(found_p_names)


def test_get_pipelines(repo):
    p_names = sorted(repo.get_pipeline_names())

    pipelines = repo.get_pipelines()

    pipelines = sorted(pipelines, key=lambda p: p.name)

    assert all(p.name == name for p, name in zip(pipelines, p_names))


def test_get_pipelines_by_datasource(repo):
    # asserted in an earlier test
    ds = repo.get_datasource_by_name("my_csv_datasource")

    ds2 = BaseDatasource(name="ds_12254757")

    pipelines = repo.get_pipelines_by_datasource(ds)

    pipelines_2 = repo.get_pipelines_by_datasource(ds2)

    assert len(pipelines) > 0

    assert not pipelines_2


def test_get_pipelines_by_type(repo):
    pipelines = repo.get_pipelines_by_type(type_filter=["training"])

    pipelines_2 = repo.get_pipelines_by_type(type_filter=["base"])

    assert len(pipelines) == 5

    assert not pipelines_2


def test_get_pipeline_by_name(repo, equal_pipelines):
    p_names = repo.get_pipeline_names()

    random_name = random.choice(p_names)
    cfg_list = [y for y in repo.get_pipeline_file_paths()
                if random_name in y]

    cfg = yaml_utils.read_yaml(cfg_list[0])

    p1 = repo.get_pipeline_by_name(random_name)

    p2 = BasePipeline.from_config(cfg)

    assert equal_pipelines(p1, p2, loaded=True)


def test_get_step_versions(repo):
    step_versions = repo.get_step_versions()

    # TODO: Make this less hardcoded
    steps_used = [
        "zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser.StandardPreprocesser",
        "zenml.steps.split.categorical_domain_split_step.CategoricalDomainSplit",
        "zenml.steps.trainer.tensorflow_trainers.tf_ff_trainer.FeedForwardTrainer"
    ]

    current_version = "zenml_" + str(__version__)

    assert set(steps_used) >= set(step_versions.keys())
    assert all(current_version in s for s in step_versions.values())


def test_get_step_by_version(repo):
    # TODO: Make this less hardcoded
    steps_used = [
        "zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser.StandardPreprocesser",
        "zenml.steps.split.categorical_domain_split_step.CategoricalDomainSplit",
        "zenml.steps.trainer.tensorflow_trainers.tf_ff_trainer.FeedForwardTrainer"
    ]

    random_step = random.choice(steps_used)

    current_version = "zenml_" + str(__version__)

    bogus_version = "asdfghjklöä"

    assert repo.get_step_by_version(random_step, current_version)
    assert repo.get_step_by_version(random_step, bogus_version) is None


def test_get_step_versions_by_type(repo):
    # TODO: Make this less hardcoded
    steps_used = [
        "zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser.StandardPreprocesser",
        "zenml.steps.split.categorical_domain_split_step.CategoricalDomainSplit",
        "zenml.steps.trainer.tensorflow_trainers.tf_ff_trainer.FeedForwardTrainer"
    ]

    random_step = random.choice(steps_used)

    current_version = "zenml_" + str(__version__)

    bogus_step = "asdfghjklöä"

    step_versions = repo.get_step_versions_by_type(random_step)

    assert step_versions == {current_version}

    assert repo.get_step_versions_by_type(bogus_step) is None
