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


from click import get_app_dir
from click.testing import CliRunner

from zenml.cli.config import opt_in, opt_out
from zenml.config.constants import GLOBAL_CONFIG_NAME
from zenml.constants import APP_NAME
from zenml.utils.yaml_utils import read_json


def read_global_config():
    """Read the global config file"""
    config_file = get_app_dir(APP_NAME) + "/" + GLOBAL_CONFIG_NAME
    read_json(config_file)


def test_analytics_opt_in_amends_global_config():
    """Check to make sure that analytics opt-in amends global config"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(opt_in)
        assert result.exit_code == 0
        # TODO: [LOW] create a test environment to test this
        # assert read_global_config()["analytics_opt_in"] is True


def test_analytics_opt_out_amends_global_config():
    """Check to make sure that analytics opt-out amends global config"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(opt_out)
        assert result.exit_code == 0
        # TODO: [LOW] create a test environment to test this
        # assert read_global_config()["analytics_opt_in"] is False
