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

from zenml.config.constants import GLOBAL_CONFIG_NAME
from zenml.config.global_config import GlobalConfig
from zenml.io import fileio
from zenml.io.utils import get_global_config_directory

APP_DIR = get_global_config_directory()


def test_global_config_file_creation():
    """A simple test to check whether the global config is created."""
    GlobalConfig()

    # Raw config should now exist
    assert fileio.file_exists(os.path.join(APP_DIR, GLOBAL_CONFIG_NAME))
