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
from zenml.core.pipelines.base_pipeline import BasePipeline
from zenml.core.datasources.base_datasource import BaseDatasource
from zenml.core.repo.repo import Repository
from zenml.utils.enums import PipelineStatusTypes
from zenml.core.standards import standard_keys as keys
from zenml.utils import exceptions

ZENML_ROOT = zenml.__path__[0]
TEST_ROOT = os.path.join(ZENML_ROOT, "testing")

pipeline_root = os.path.join(TEST_ROOT, "test_pipelines")
repo: Repository = Repository.get_instance()
repo.zenml_config.set_pipelines_dir(pipeline_root)


def test_executed():
    name = "my_pipeline"
    p = BasePipeline(name=name)
    assert not p.is_executed_in_metadata_store

    random_run_pipeline = random.choice(repo.get_pipelines())

    assert random_run_pipeline.is_executed_in_metadata_store


def test_naming():
    name = "my_pipeline"
    p = BasePipeline(name=name)
    # file_name = p.file_name
    pipeline_name = p.pipeline_name

    # assert p.get_type_from_file_name(file_name) == p.PIPELINE_TYPE
    assert p.get_name_from_pipeline_name(pipeline_name) == name
    # assert p.get_type_from_pipeline_name(pipeline_name) == p.PIPELINE_TYPE


def test_get_status(run_test_pipelines):
    run_test_pipelines()
    name = "my_pipeline"
    p = BasePipeline(name=name)

    # passing this test means that if the pipeline is not in the metadata
    # store, it is (semantically) not started yet
    assert p.get_status() == PipelineStatusTypes.NotStarted.name

    run_pipeline = random.choice(repo.get_pipelines())

    assert run_pipeline.get_status() == PipelineStatusTypes.Succeeded.name


def test_register_pipeline(delete_config):
    name = "my_pipeline"
    p: BasePipeline = BasePipeline(name=name)

    p._check_registered()

    random_run_pipeline = random.choice(repo.get_pipelines())
    with pytest.raises(exceptions.AlreadyExistsException):
        random_run_pipeline._check_registered()

    p.register_pipeline({"name": name})

    delete_config(p.file_name)


def test_add_datasource():
    name = "my_pipeline"
    p: BasePipeline = BasePipeline(name=name)

    p.add_datasource(BaseDatasource(name="my_datasource"))

    assert isinstance(p.datasource, BaseDatasource)

    assert not p.steps_dict[keys.TrainingSteps.DATA]


def test_pipeline_copy():
    random_run_pipeline = random.choice(repo.get_pipelines())

    new_name = "my_second_pipeline"

    new_pipeline = random_run_pipeline.copy(new_name=new_name)

    assert not new_pipeline._immutable
    assert isinstance(new_pipeline, random_run_pipeline.__class__)


def test_get_pipeline_config():
    # test just the pipeline config block added to the steps_config
    name = "my_pipeline"
    p: BasePipeline = BasePipeline(name=name)

    config = p.get_pipeline_config()

    assert name in config[keys.PipelineKeys.NAME]
    assert config[keys.PipelineKeys.TYPE] == "base"
    assert config[keys.PipelineKeys.ENABLE_CACHE] is True
    assert config[keys.PipelineKeys.DATASOURCE] is None
    assert config[keys.PipelineKeys.SOURCE].split("@")[0] == \
           "zenml.core.pipelines.base_pipeline.BasePipeline"
