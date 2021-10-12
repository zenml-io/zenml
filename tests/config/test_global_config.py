#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import click

from zenml import constants
from zenml.config.constants import GLOBAL_CONFIG_NAME
from zenml.config.global_config import GlobalConfig
from zenml.utils import path_utils, yaml_utils

APP_DIR = click.get_app_dir(constants.APP_NAME)


def test_global_config_file_creation():
    """A simple test to check whether the global config is created."""
    GlobalConfig()

    # Raw config should now exist
    assert path_utils.file_exists(os.path.join(APP_DIR, GLOBAL_CONFIG_NAME))


def test_global_config_persistence():
    """A simple test to check whether the persistence logic works."""
    gc = GlobalConfig()

    # Track old one
    old_analytics_opt_in = gc.analytics_opt_in

    # Toggle it
    gc.analytics_opt_in = not old_analytics_opt_in

    # Initialize new config
    gc = GlobalConfig()

    # It still should be equal to the old value, as we have not saved
    assert old_analytics_opt_in == gc.analytics_opt_in

    # Get raw config
    raw_config = yaml_utils.read_json(os.path.join(APP_DIR, GLOBAL_CONFIG_NAME))
    assert raw_config["analytics_opt_in"] == old_analytics_opt_in
