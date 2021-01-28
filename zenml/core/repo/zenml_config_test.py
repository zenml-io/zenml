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
from zenml.core.repo.repo import Repository
from zenml.core.repo.zenml_config import ZenMLConfig, PIPELINES_DIR_KEY
from zenml.utils.exceptions import InitializationException
from zenml.utils import yaml_utils
from zenml.core.standards import standard_keys as keys
from zenml.core.repo.constants import ARTIFACT_STORE_DEFAULT_DIR, \
    ZENML_DIR_NAME

ZENML_ROOT = zenml.__path__[0]
TEST_ROOT = os.path.join(ZENML_ROOT, "testing")

pipelines_dir = os.path.join(TEST_ROOT, "test_pipelines")
repo: Repository = Repository.get_instance()
repo.zenml_config.set_pipelines_dir(pipelines_dir)

config_root = os.path.dirname(ZENML_ROOT)
artifact_store_path = os.path.join(config_root, ZENML_DIR_NAME,
                                   ARTIFACT_STORE_DEFAULT_DIR)


def test_zenml_config_init():
    # in the root initialization should work
    _ = ZenMLConfig(config_root)

    # outside of an initialized repo path
    with pytest.raises(InitializationException):
        _ = ZenMLConfig(os.getcwd())


def test_is_zenml_dir():
    ok_path = config_root

    not_ok_path = os.getcwd()

    assert ZenMLConfig.is_zenml_dir(ok_path)
    assert not ZenMLConfig.is_zenml_dir(not_ok_path)


def test_to_from_config(equal_zenml_configs):
    # TODO: This is messed up
    cfg1 = ZenMLConfig(repo_path=config_root)

    cfg2 = cfg1.from_config(cfg1.to_config(path=config_root))

    assert equal_zenml_configs(cfg1, cfg2, loaded=True)


def test_zenml_config_getters():
    cfg1 = ZenMLConfig(repo_path=config_root)

    assert cfg1.get_pipelines_dir()
    assert cfg1.get_artifact_store()
    assert cfg1.get_metadata_store()


def test_zenml_config_setters():
    cfg1 = ZenMLConfig(repo_path=config_root)

    old_store_path = artifact_store_path
    old_pipelines_dir = pipelines_dir

    new_store_path = os.getcwd()

    new_pipelines_dir = "awfkoeghelk"

    cfg1.set_artifact_store(new_store_path)
    cfg1.set_pipelines_dir(new_pipelines_dir)

    updated_cfg = yaml_utils.read_yaml(cfg1.config_path)

    assert updated_cfg[keys.GlobalKeys.ARTIFACT_STORE] == new_store_path
    assert updated_cfg[PIPELINES_DIR_KEY] == new_pipelines_dir

    # revert changes
    cfg1.set_artifact_store(old_store_path)
    cfg1.set_pipelines_dir(old_pipelines_dir)
