#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import os
from uuid import uuid4

import pytest

from zenml.config.global_config import GlobalConfiguration
from zenml.io import fileio


def test_global_config_file_creation(clean_repo):
    """Tests whether a config file gets created when the global
    config object is first instantiated."""
    if fileio.exists(GlobalConfiguration()._config_file()):
        fileio.remove(GlobalConfiguration()._config_file())

    GlobalConfiguration._reset_instance()
    assert fileio.exists(GlobalConfiguration()._config_file())


def test_global_config_user_id_is_immutable(clean_repo):
    """Tests that the global config user id attribute is immutable."""
    with pytest.raises(TypeError):
        GlobalConfiguration().user_id = uuid4()


def test_global_config_returns_value_from_environment_variable(
    mocker, clean_repo
):
    """Tests that global config attributes can be overwritten by environment
    variables."""
    if fileio.exists(GlobalConfiguration()._config_file()):
        fileio.remove(GlobalConfiguration()._config_file())

    GlobalConfiguration()._reset_instance()
    config = GlobalConfiguration()

    # delete the environment variable that is set at the beginning of all tests
    mocker.patch.dict(os.environ, values={}, clear=True)
    assert config.analytics_opt_in is True

    # make sure the environment variable is set, then the global config should
    # return the corresponding value
    mocker.patch.dict(
        os.environ, values={"ZENML_ANALYTICS_OPT_IN": "false"}, clear=True
    )
    assert config.analytics_opt_in is False
