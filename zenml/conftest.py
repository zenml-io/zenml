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
import shutil
from zenml.core.repo.repo import Repository
from zenml.utils import path_utils, yaml_utils
from zenml.core.pipelines.training_pipeline import TrainingPipeline

# reset pipeline root to redirect to testing so that it writes the yamls there
ZENML_ROOT = zenml.__path__[0]
TEST_ROOT = os.path.join(ZENML_ROOT, "testing")

pipeline_root = os.path.join(TEST_ROOT, "test_pipelines")


@pytest.fixture
def cleanup_metadata_store():
    def wrapper():
        # Remove metadata db after a test to avoid test failures by duplicated
        # data sources
        metadata_db_location = os.path.join(".zenml", "local_store",
                                            "metadata.db")
        try:
            os.remove(os.path.join(ZENML_ROOT, metadata_db_location))
        except Exception as e:
            print(e)

    return wrapper


@pytest.fixture
def cleanup_pipelines_dir():
    def wrapper():
        repo: Repository = Repository.get_instance()
        pipelines_dir = repo.zenml_config.get_pipelines_dir()
        for p_config in path_utils.list_dir(pipelines_dir):
            try:
                os.remove(p_config)
            except Exception as e:
                print(e)

    return wrapper


@pytest.fixture
def cleanup_artifacts():
    def wrapper():
        local_store_path = os.path.join(".zenml", "local_store")
        try:
            local_store = os.path.join(ZENML_ROOT, local_store_path)
            shutil.rmtree(local_store, ignore_errors=False)
        except Exception as e:
            print(e)

    return wrapper


@pytest.fixture
def cleanup(cleanup_metadata_store, cleanup_artifacts):
    cleanup_metadata_store()
    cleanup_artifacts()


@pytest.fixture
def run_test_pipelines():
    def wrapper():
        repo: Repository = Repository.get_instance()
        repo.zenml_config.set_pipelines_dir(pipeline_root)

        for p_config in path_utils.list_dir(pipeline_root):
            y = yaml_utils.read_yaml(p_config)
            p: TrainingPipeline = TrainingPipeline.from_config(y)
            p.run()
    return wrapper


@pytest.fixture
def delete_config():
    def wrapper(filename):
        repo: Repository = Repository.get_instance()
        repo.zenml_config.set_pipelines_dir(pipeline_root)

        try:
            cfg = os.path.join(pipeline_root, filename)
            os.remove(cfg)
        except Exception as e:
            print(e)
            pass

    return wrapper
