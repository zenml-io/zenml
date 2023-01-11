#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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

import pytest
from click.testing import CliRunner

from zenml.cli.config import opt_in, opt_out, set_logging_verbosity
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import ZENML_LOGGING_VERBOSITY
from zenml.utils import yaml_utils

NOT_LOGGING_LEVELS = ["abc", "my_cat_is_called_aria", "pipeline123"]


def read_global_config():
    """Read the global config file"""
    return yaml_utils.read_yaml(GlobalConfiguration()._config_file())


def test_analytics_opt_in_amends_global_config():
    """Check to make sure that analytics opt-in amends global config"""
    pre_test_status = GlobalConfiguration().analytics_opt_in
    runner = CliRunner()
    result = runner.invoke(opt_in)
    assert result.exit_code == 0
    assert read_global_config()["analytics_opt_in"]
    GlobalConfiguration().analytics_opt_in = pre_test_status


def test_analytics_opt_out_amends_global_config():
    """Check to make sure that analytics opt-out amends global config"""
    pre_test_status = GlobalConfiguration().analytics_opt_in
    runner = CliRunner()
    result = runner.invoke(opt_out)
    assert result.exit_code == 0
    assert not read_global_config()["analytics_opt_in"]
    GlobalConfiguration().analytics_opt_in = pre_test_status


@pytest.mark.parametrize("not_a_level", NOT_LOGGING_LEVELS)
def test_set_logging_verbosity_stops_when_not_real_level(
    not_a_level: str,
) -> None:
    """Check that set_logging_verbosity doesn't run when no real level"""
    pre_test_logging_status = ZENML_LOGGING_VERBOSITY
    runner = CliRunner()
    result = runner.invoke(set_logging_verbosity, [not_a_level])
    os.environ["ZENML_LOGGING_VERBOSITY"] = pre_test_logging_status
    assert result.exit_code == 2
