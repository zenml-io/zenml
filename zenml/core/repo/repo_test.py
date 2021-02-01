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

import pytest
import os
import zenml
import random
from typing import Text
from zenml.core.repo.repo import Repository
from zenml.core.pipelines.base_pipeline import BasePipeline
from zenml.core.datasources.base_datasource import BaseDatasource
from zenml.utils import yaml_utils
from zenml.utils.version import __version__
from zenml.core.standards import standard_keys as keys

ZENML_ROOT = zenml.__path__[0]
TEST_ROOT = os.path.join(ZENML_ROOT, "testing")

pipeline_root = os.path.join(TEST_ROOT, "test_pipelines")
repo: Repository = Repository.get_instance()
repo.zenml_config.set_pipelines_dir(pipeline_root)


def test_repo_double_init():
    # explicitly constructing another repository should fail
    with pytest.raises(Exception):
        _ = Repository()


def test_get_datasources(run_test_pipelines):
    run_test_pipelines()

    ds_list = repo.get_datasources()

    # TODO: Expand this for more test pipeline types!
    assert len(ds_list) == 1


def test_get_datasource_by_name():
    assert repo.get_datasource_by_name("my_csv_datasource")

    fake_ds = repo.get_datasource_by_name("ds_123")

    assert fake_ds is None


def test_get_datasource_names():
    # TODO: Expand to more test datasources!
    test_ds_names = ["my_csv_datasource"]

    ds_names = repo.get_datasource_names()

    assert sorted(test_ds_names) == sorted(ds_names)


def test_get_pipeline_file_paths(monkeypatch):
    mock_paths = ["pipeline_1.yaml", "pipeline_2.yaml", "awjfof.txt"]

    def mock_list_dir(dir_path: Text, only_file_names: bool = False):
        # add a corrupted file into the pipelines
        return mock_paths

    monkeypatch.setattr("zenml.utils.path_utils.list_dir",
                        mock_list_dir)

    paths = repo.get_pipeline_file_paths(only_file_names=True)

    assert paths == mock_paths[:-1]


def test_get_pipeline_names():
    # TODO: This has to be made dynamic once more pipelines come
    real_p_names = sorted(["csvtest{0}".format(i) for i in range(1, 6)])

    found_p_names = sorted(repo.get_pipeline_names())

    assert real_p_names == found_p_names


def test_get_pipelines():
    p_names = sorted(repo.get_pipeline_names())

    pipelines = repo.get_pipelines()

    pipelines = sorted(pipelines, key=lambda p: p.name)

    assert all(p.name == name for p, name in zip(pipelines, p_names))


def test_get_pipelines_by_datasource():
    # asserted in an earlier test
    ds = repo.get_datasource_by_name("my_csv_datasource")

    p_names = repo.get_pipeline_names()

    ds2 = BaseDatasource(name="ds_12254757")

    pipelines = repo.get_pipelines_by_datasource(ds)

    pipelines_2 = repo.get_pipelines_by_datasource(ds2)

    assert len(pipelines) == len(p_names)

    assert not pipelines_2


def test_get_pipelines_by_type():
    p_names = repo.get_pipeline_names()

    pipelines = repo.get_pipelines_by_type(type_filter=["training"])

    pipelines_2 = repo.get_pipelines_by_type(type_filter=["base"])

    assert len(pipelines) == len(p_names)

    assert not pipelines_2


def test_get_pipeline_by_name(equal_pipelines):
    p_names = repo.get_pipeline_names()

    random_name = random.choice(p_names)
    cfg_list = [y for y in repo.get_pipeline_file_paths()
                if random_name in y]

    cfg = yaml_utils.read_yaml(cfg_list[0])

    p1 = repo.get_pipeline_by_name(random_name)

    p2 = BasePipeline.from_config(cfg)

    assert equal_pipelines(p1, p2, loaded=True)


def test_get_step_versions():

    step_versions = repo.get_step_versions()

    # TODO: Make this less hardcoded
    steps_used = ["zenml.core.steps.data.csv_data_step.CSVDataStep",
                  "zenml.core.steps.preprocesser.standard_preprocesser."
                  "standard_preprocesser.StandardPreprocesser",
                  "zenml.core.steps.split.categorical_domain_split_step."
                  "CategoricalDomainSplit",
                  'zenml.core.steps.trainer.tensorflow_trainers.tf_ff_trainer.'
                  'FeedForwardTrainer'
                  ]

    current_version = "zenml_" + str(__version__)

    assert sorted(steps_used) == sorted(step_versions.keys())
    assert all(current_version in s for s in step_versions.values())


def test_get_step_by_version():
    # TODO: Make this less hardcoded
    steps_used = ["zenml.core.steps.data.csv_data_step.CSVDataStep",
                  "zenml.core.steps.preprocesser.standard_preprocesser."
                  "standard_preprocesser.StandardPreprocesser",
                  "zenml.core.steps.split.categorical_domain_split_step."
                  "CategoricalDomainSplit",
                  'zenml.core.steps.trainer.tensorflow_trainers.tf_ff_trainer.'
                  'FeedForwardTrainer'
                  ]

    random_step = random.choice(steps_used)

    current_version = "zenml_" + str(__version__)

    bogus_version = "asdfghjklöä"

    assert repo.get_step_by_version(random_step, current_version)
    assert repo.get_step_by_version(random_step, bogus_version) is None


def test_get_step_versions_by_type():
    # TODO: Make this less hardcoded
    steps_used = ["zenml.core.steps.data.csv_data_step.CSVDataStep",
                  "zenml.core.steps.preprocesser.standard_preprocesser."
                  "standard_preprocesser.StandardPreprocesser",
                  "zenml.core.steps.split.categorical_domain_split_step."
                  "CategoricalDomainSplit",
                  'zenml.core.steps.trainer.tensorflow_trainers.tf_ff_trainer.'
                  'FeedForwardTrainer'
                  ]

    random_step = random.choice(steps_used)

    current_version = "zenml_" + str(__version__)

    bogus_step = "asdfghjklöä"

    step_versions = repo.get_step_versions_by_type(random_step)

    assert step_versions == {current_version}

    assert repo.get_step_versions_by_type(bogus_step) is None
