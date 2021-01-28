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
from zenml.core.repo.zenml_config import ZenMLConfig
from zenml.utils.exceptions import InitializationException

ZENML_ROOT = zenml.__path__[0]
TEST_ROOT = os.path.join(ZENML_ROOT, "testing")

pipelines_dir = os.path.join(TEST_ROOT, "test_pipelines")
repo: Repository = Repository.get_instance()
repo.zenml_config.set_pipelines_dir(pipelines_dir)


def test_zenml_config_init():
    # in the root initialization should work
    _ = ZenMLConfig(ZENML_ROOT)

    # outside of an initialized repo path
    with pytest.raises(InitializationException):
        _ = ZenMLConfig(os.getcwd())


def test_is_zenml_dir():
    ok_path = ZENML_ROOT

    not_ok_path = os.getcwd()

    assert ZenMLConfig.is_zenml_dir(ok_path)
    assert not ZenMLConfig.is_zenml_dir(not_ok_path)


def test_to_from_config(equal_zenml_configs):
    cfg1 = ZenMLConfig(repo_path=ZENML_ROOT)

    cfg2 = cfg1.from_config(cfg1.to_config(path=ZENML_ROOT))

    assert equal_zenml_configs(cfg1, cfg2, loaded=True)

