#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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

from click import get_app_dir
from click.testing import CliRunner

from zenml.cli.config import opt_in, opt_out
from zenml.config.constants import GLOBAL_CONFIG_NAME
from zenml.config.global_config import GlobalConfig
from zenml.constants import APP_NAME
from zenml.utils.yaml_utils import read_json


def read_global_config():
    """Read the global config file"""
    config_file = os.path.join(get_app_dir(APP_NAME), GLOBAL_CONFIG_NAME)
    return read_json(str(config_file))


def get_analytics_opt_in_status():
    """Get the analytics opt-in status"""
    gc = GlobalConfig()
    return gc.analytics_opt_in


def set_analytics_opt_in_status(status: bool):
    """Set the analytics opt-in status"""
    gc = GlobalConfig()
    gc.analytics_opt_in = status
    gc.update()


def test_analytics_opt_in_amends_global_config():
    """Check to make sure that analytics opt-in amends global config"""
    pre_test_status = get_analytics_opt_in_status()
    runner = CliRunner()
    result = runner.invoke(opt_in)
    assert result.exit_code == 0
    assert read_global_config()["analytics_opt_in"]
    set_analytics_opt_in_status(pre_test_status)


def test_analytics_opt_out_amends_global_config():
    """Check to make sure that analytics opt-out amends global config"""
    pre_test_status = get_analytics_opt_in_status()
    runner = CliRunner()
    result = runner.invoke(opt_out)
    assert result.exit_code == 0
    assert not read_global_config()["analytics_opt_in"]
    set_analytics_opt_in_status(pre_test_status)


# test logging verbosity raises KeyError when it's not a real level

# test metadata register command actually registers a new metadata store
# test metadata list actually lists newly created metadata stores
# test metadata delete actually deletes newly created metadata stores
# test artifact register command actually registers a new artifact store
# test artifact list actually lists newly created artifact stores
# test artifact delete actually deletes newly created artifact stores
# test orchestrator register command actually registers a new orchestrator
# test orchestrator list actually lists newly created orchestrators
# test orchestrator delete actually deletes newly created orchestrators
# test orchestrator up actually spins up our orchestrator
# test orchestrator down actually shuts down our orchestrator
