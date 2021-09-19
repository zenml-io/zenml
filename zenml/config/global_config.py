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
"""Global config for the ZenML installation."""
import os
from typing import Text
from uuid import uuid4

import click

from zenml import constants
from zenml.config.base_config import BaseConfig
from zenml.config.constants import GLOBAL_CONFIG_NAME
from zenml.config.utils import define_yaml_config_settings_source
from zenml.logger import get_logger
from zenml.version import __version__

logger = get_logger(__name__)


class GlobalConfig(BaseConfig):
    """Class definition for the global config.

    Defines global data such as unique user ID and whether they opted in
    for analytics.
    """

    user_id: str = str(uuid4())
    analytics_opt_in: bool = True

    @staticmethod
    def get_config_dir() -> Text:
        """Gets the global config dir for installed package."""
        return click.get_app_dir(constants.APP_NAME)

    @staticmethod
    def get_config_file_name() -> Text:
        """Gets the global config dir for installed package."""
        return GLOBAL_CONFIG_NAME

    class Config:
        """Configuration of settings."""

        env_prefix = "zenml_"

        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            return (
                init_settings,
                # using a version-pinned folder avoids conflicts when
                #  upgrading zenml versions.
                define_yaml_config_settings_source(
                    os.path.join(__version__, GlobalConfig.get_config_dir()),
                    GLOBAL_CONFIG_NAME,
                ),
                env_settings,
            )
