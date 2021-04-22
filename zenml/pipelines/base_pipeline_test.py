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

import pytest

import zenml
from zenml import exceptions
from zenml.backends.orchestrator import OrchestratorBaseBackend
from zenml.datasources import BaseDatasource, ImageDatasource
from zenml.enums import PipelineStatusTypes, GDPComponent
from zenml.pipelines import BasePipeline, TrainingPipeline
from zenml.standards import standard_keys as keys
from zenml.steps import BaseStep
from zenml.utils import path_utils

# Nicholas a way to get to the root
ZENML_ROOT = str(Path(zenml.__path__[0]).parent)
TEST_ROOT = os.path.join(ZENML_ROOT, "tests")


def test_executed(repo):
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

    assert p.get_name_from_pipeline_name(pipeline_name) == name


def test_get_status(repo):
    name = "my_pipeline"
    p = BasePipeline(name=name)

    # passing this test means that if the pipeline is not in the metadata
    # store, it is (semantically) not started yet
    assert p.get_status() == PipelineStatusTypes.NotStarted.name

    run_pipeline = random.choice(repo.get_pipelines())

    assert run_pipeline.get_status() == PipelineStatusTypes.Succeeded.name


def test_register_pipeline(repo, delete_config):
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

    # assert not p.steps_dict[keys.TrainingSteps.DATA]


def test_pipeline_copy(repo):
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

    p_name = p.pipeline_name

    p_args = config[keys.PipelineKeys.ARGS]

    assert p_args[keys.PipelineDetailKeys.NAME] == p_name
    # assert p_args[keys.PipelineDetailKeys.TYPE] == "base"
    assert p_args[keys.PipelineDetailKeys.ENABLE_CACHE] is True
    assert config[keys.PipelineKeys.DATASOURCE] == {}
    assert config[keys.PipelineKeys.SOURCE].split("@")[0] == \
           "zenml.pipelines.base_pipeline.BasePipeline"
    # TODO: Expand this to more pipelines


def test_get_steps_config():
    # TODO: Expand this to more steps
    name = "my_pipeline"
    p: BasePipeline = BasePipeline(name=name)

    kwargs = {"number": 1, "description": "abcdefg"}
    step = BaseStep(**kwargs)

    p.steps_dict["test"] = step

    cfg = p.get_steps_config()

    steps_cfg = cfg[keys.PipelineKeys.STEPS]

    # avoid missing args / type inconsistencies
    assert steps_cfg["test"] == step.to_config()


def test_get_artifacts_uri_by_component(repo):
    test_component_name = GDPComponent.SplitGen.name

    ps = repo.get_pipelines_by_type([TrainingPipeline.PIPELINE_TYPE])

    p: BasePipeline = ps[0]

    uri_list = p.get_artifacts_uri_by_component(test_component_name)

    # assert it is not empty
    assert uri_list
    # assert artifact was written
    uri = uri_list[0]
    written_artifacts = path_utils.list_dir(uri)
    assert written_artifacts
    # TODO: Ugly TFRecord validation
    assert all((("tfrecord" in name and
                 os.path.splitext(name)[-1] == ".gz") for name in f)
               for _, _, f in os.walk(uri))


def test_to_from_config(equal_pipelines):
    p1: BasePipeline = BasePipeline(name="my_pipeline")

    ds = ImageDatasource(name="my_datasource")

    p1.add_datasource(ds)

    p2 = BasePipeline.from_config(p1.to_config())

    assert equal_pipelines(p1, p2, loaded=True)


def test_load_config(repo, equal_pipelines):
    p1 = random.choice(repo.get_pipelines())

    pipeline_config = p1.load_config()

    p2 = BasePipeline.from_config(pipeline_config)

    assert equal_pipelines(p1, p2, loaded=True)


def test_run_config():
    p = BasePipeline(name="my_pipeline")

    class MockBackend(OrchestratorBaseBackend):
        def run(self, config):
            return {"message": "Run triggered!"}

    # run config without a specified backend
    p.run_config(p.to_config())

    p.backend = "123"

    with pytest.raises(Exception):
        # not a backend subclass error
        p.run_config(p.to_config())

    p.backend = MockBackend()

    assert not p.run_config(p.to_config())


def test_run_base(delete_config):
    # Test of pipeline.run(), without artifact / metadata store change
    p = BasePipeline(name="my_pipeline")

    class MockBackend(OrchestratorBaseBackend):
        def run(self, config):
            return {"message": "Run triggered!"}

    backend = MockBackend()

    p.run(backend=backend)

    assert p._immutable

    delete_config(p.file_name)
