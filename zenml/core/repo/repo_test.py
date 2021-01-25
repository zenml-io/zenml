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
from typing import Text
from zenml.core.repo.repo import Repository
from zenml.core.datasources.base_datasource import BaseDatasource
from zenml.core.pipelines.base_pipeline import BasePipeline
from zenml.utils import yaml_utils, path_utils

ZENML_ROOT = os.path.dirname(zenml.__path__[0])


@pytest.fixture
def cleanup_metadata_store():
    # Remove metadata db after a test to avoid test failures by duplicated
    # data sources
    metadata_db_location = os.path.join(".zenml", "local_store", "metadata.db")
    try:
        os.remove(os.path.join(ZENML_ROOT, metadata_db_location))
    except Exception as e:
        print(e)


@pytest.fixture
def cleanup_pipelines_dir():
    def wrapper():
        repo: Repository = Repository.get_instance()
        pipelines_dir = repo.zenml_config.get_pipelines_dir()
        for p_config in path_utils.list_dir(pipelines_dir):
            os.remove(p_config)

    return wrapper


def test_double_init():
    repo: Repository = Repository.get_instance()
    # explicitly constructing another repository should fail
    with pytest.raises(Exception):
        repo2 = Repository()


def test_datasource_get(monkeypatch):

    def mock_datasources(self):
        return [BaseDatasource(name="my_datasource")]

    def mock_datasource_names(self):
        return []

    monkeypatch.setattr("zenml.core.repo.repo.Repository.get_datasources",
                        mock_datasources)

    monkeypatch.setattr("zenml.core.repo.repo.Repository.get_datasources",
                        mock_datasources)

    repo: Repository = Repository.get_instance()

    assert repo.get_datasource_by_name("my_datasource")

    with pytest.raises(Exception):
        _ = repo.get_datasource_by_name("ds_123")


def test_yaml_discovery(monkeypatch):
    repo: Repository = Repository.get_instance()

    mock_paths = ["pipeline_1.yaml", "pipeline_2.yaml", "awjfof.txt"]

    def mock_list_dir(dir_path: Text, only_file_names: bool = False):
        # add a corrupted file into the pipelines
        return mock_paths

    monkeypatch.setattr("zenml.utils.path_utils.list_dir",
                        mock_list_dir)

    paths = repo.get_pipeline_file_paths(only_file_names=True)

    assert paths == mock_paths[:-1]


def test_get_pipelines(monkeypatch, cleanup_pipelines_dir):

    cleanup_pipelines_dir()

    repo: Repository = Repository.get_instance()

    pipelines_dir = repo.zenml_config.get_pipelines_dir()

    mock_configs = [{"name": "p1"}, {"name": "p2"}, {"name": "p3"}]

    mock_names = ["pipeline1.yml", "pipeline2.yml", "pipeline3.yml"]

    for fn, cfg in zip(mock_names, mock_configs):
        yaml_utils.write_yaml(os.path.join(pipelines_dir, fn), cfg)

    def mock_create_pipeline(c):
        return BasePipeline(name=c["name"])
    monkeypatch.setattr("zenml.core.pipelines.base_pipeline.BasePipeline."
                        "from_config",
                        mock_create_pipeline)

    pipelines = repo.get_pipelines()

    assert len(pipelines) == len(mock_configs)

    sorted_pipelines = sorted(pipelines, key=lambda p: p.name)

    assert all(p.name == c["name"] for p, c in zip(sorted_pipelines,
                                                   mock_configs))
