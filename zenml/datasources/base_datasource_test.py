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

import pandas as pd
import pytest

import zenml
from zenml import exceptions
from zenml.datasources import BaseDatasource
from zenml.pipelines import BasePipeline
from zenml.standards import standard_keys as keys
from zenml.utils import yaml_utils

# Nicholas a way to get to the root
ZENML_ROOT = str(Path(zenml.__path__[0]).parent)
TEST_ROOT = os.path.join(ZENML_ROOT, "tests")


def test_datasource_create(repo):
    name = "my_datasource"
    first_ds = BaseDatasource(name=name)

    assert not first_ds._immutable

    # reload a datasource from a saved config
    p_config = random.choice(repo.get_pipeline_file_paths())
    cfg = yaml_utils.read_yaml(p_config)
    second_ds = BaseDatasource.from_config(cfg[keys.GlobalKeys.PIPELINE])

    assert second_ds._immutable


def test_to_from_config(equal_datasources):
    first_ds = BaseDatasource(name="my_datasource")

    config = dict({keys.PipelineKeys.STEPS: {}})
    config[keys.PipelineKeys.STEPS][keys.DataSteps.DATA] = {"args": {}}
    config[keys.PipelineKeys.DATASOURCE] = first_ds.to_config()
    second_ds = BaseDatasource.from_config(config)

    assert equal_datasources(first_ds, second_ds, loaded=True)


def test_get_one_pipeline(repo):
    name = "my_datasource"
    first_ds = BaseDatasource(name=name)

    with pytest.raises(exceptions.EmptyDatasourceException):
        _ = first_ds._get_one_pipeline()

    # reload a datasource from a saved config
    p_config = random.choice(repo.get_pipeline_file_paths())
    cfg = yaml_utils.read_yaml(p_config)
    second_ds = BaseDatasource.from_config(cfg[keys.GlobalKeys.PIPELINE])

    assert second_ds._get_one_pipeline()


def test_get_data_file_paths(repo):
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


def test_get_datapoints(repo):
    # reload a datasource from a saved config
    p_config = random.choice(repo.get_pipeline_file_paths())
    cfg = yaml_utils.read_yaml(p_config)
    ds: BaseDatasource = BaseDatasource.from_config(
        cfg[keys.GlobalKeys.PIPELINE])

    csv_df = pd.read_csv(os.path.join(TEST_ROOT,
                                      "test_data", "my_dataframe.csv"))

    assert ds.n_datapoints == len(csv_df.index)


def test_sample_data(repo):
    # reload a datasource from a saved config
    p_config = random.choice(repo.get_pipeline_file_paths())
    cfg = yaml_utils.read_yaml(p_config)
    ds: BaseDatasource = BaseDatasource.from_config(
        cfg[keys.GlobalKeys.PIPELINE])

    sample_df = ds.sample_data()
    csv_df = pd.read_csv(os.path.join(TEST_ROOT,
                                      "test_data", "my_dataframe.csv"))

    # TODO: This fails for floating point values other than 2.5 in GPA.
    #   Pandas floating point comp might be too strict
    assert sample_df.equals(csv_df)
