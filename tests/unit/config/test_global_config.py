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

from zenml.config.global_config import GlobalConfiguration
from zenml.io import fileio


def test_global_config_file_creation(clean_client):
    """Tests whether a config file gets created when the global config object is first instantiated."""
    if fileio.exists(GlobalConfiguration()._config_file):
        fileio.remove(GlobalConfiguration()._config_file)

    GlobalConfiguration._reset_instance()
    assert fileio.exists(GlobalConfiguration()._config_file)


def test_global_config_returns_value_from_environment_variable(
    mocker, clean_client
):
    """Tests that global config attributes can be overwritten by environment variables."""
    config = GlobalConfiguration()

    os.environ["ZENML_ANALYTICS_OPT_IN"] = "true"
    assert config.analytics_opt_in is True

    os.environ["ZENML_ANALYTICS_OPT_IN"] = "false"
    assert config.analytics_opt_in is False
