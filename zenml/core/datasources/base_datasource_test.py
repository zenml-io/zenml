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
import pandas as pd
from zenml.core.datasources.base_datasource import BaseDatasource
from zenml.core.pipelines.base_pipeline import BasePipeline
from zenml.core.repo.repo import Repository
from zenml.core.standards import standard_keys as keys
from zenml.utils import yaml_utils, exceptions

ZENML_ROOT = zenml.__path__[0]
TEST_ROOT = os.path.join(ZENML_ROOT, "testing")

pipeline_root = os.path.join(TEST_ROOT, "test_pipelines")
repo: Repository = Repository.get_instance()
repo.zenml_config.set_pipelines_dir(pipeline_root)


def test_datasource_create():
    name = "my_datasource"
    first_ds = BaseDatasource(name=name)

    assert not first_ds._immutable

    # reload a datasource from a saved config
    p_config = random.choice(repo.get_pipeline_file_paths())
    cfg = yaml_utils.read_yaml(p_config)
    second_ds = BaseDatasource.from_config(cfg[keys.GlobalKeys.PIPELINE])

    assert second_ds._immutable


def test_get_datastep():
    first_ds = BaseDatasource(name="my_datasource")

    assert not first_ds.get_data_step()


def test_to_from_config(equal_datasources):
    first_ds = BaseDatasource(name="my_datasource")

    config = dict({keys.PipelineKeys.STEPS: {}})
    config[keys.PipelineKeys.STEPS][keys.DataSteps.DATA] = {"args": {}}
    config[keys.PipelineKeys.DATASOURCE] = first_ds.to_config()
    second_ds = BaseDatasource.from_config(config)

    assert equal_datasources(first_ds, second_ds, loaded=True)


def test_get_one_pipeline():
    name = "my_datasource"
    first_ds = BaseDatasource(name=name)

    with pytest.raises(exceptions.EmptyDatasourceException):
        _ = first_ds._get_one_pipeline()

    # reload a datasource from a saved config
    p_config = random.choice(repo.get_pipeline_file_paths())
    cfg = yaml_utils.read_yaml(p_config)
    second_ds = BaseDatasource.from_config(cfg[keys.GlobalKeys.PIPELINE])

    assert second_ds._get_one_pipeline()


def test_get_data_file_paths():
    first_ds = BaseDatasource(name="my_datasource")

    first_pipeline = BasePipeline(name="my_pipeline")

    first_pipeline.add_datasource(first_ds)

    # reload a datasource from a saved config
    p_config = random.choice(repo.get_pipeline_file_paths())
    cfg = yaml_utils.read_yaml(p_config)
    second_ds = BaseDatasource.from_config(cfg[keys.GlobalKeys.PIPELINE])

    with pytest.raises(AssertionError):
        _ = second_ds._get_data_file_paths(first_pipeline)

    real_pipeline = second_ds._get_one_pipeline()
    paths = second_ds._get_data_file_paths(real_pipeline)

    # TODO: Find a better way of asserting TFRecords
    assert all(os.path.splitext(p)[-1] == ".gz" for p in paths)


def test_get_datapoints():
    # reload a datasource from a saved config
    p_config = random.choice(repo.get_pipeline_file_paths())
    cfg = yaml_utils.read_yaml(p_config)
    ds: BaseDatasource = BaseDatasource.from_config(
        cfg[keys.GlobalKeys.PIPELINE])

    csv_df = pd.read_csv(os.path.join(TEST_ROOT,
                                      "test_data", "my_dataframe.csv"))

    assert ds.get_datapoints() == len(csv_df.index)


def test_sample_data():
    # reload a datasource from a saved config
    p_config = random.choice(repo.get_pipeline_file_paths())
    cfg = yaml_utils.read_yaml(p_config)
    ds: BaseDatasource = BaseDatasource.from_config(
        cfg[keys.GlobalKeys.PIPELINE])

    sample_df = ds.sample_data()
    csv_df = pd.read_csv(os.path.join(TEST_ROOT,
                                      "test_data", "my_dataframe.csv"))

    # TODO: This fails on the test csv because the age gets typed as
    #  a float in datasource.sample_data() method
    assert sample_df.equals(csv_df)
