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
from abc import abstractmethod
from typing import Any, Text

from pydantic import BaseSettings

from zenml.config.utils import define_json_config_settings_source
from zenml.logger import get_logger
from zenml.utils import path_utils

logger = get_logger(__name__)


class BaseConfig(BaseSettings):
    """Class definition for the global config.

    Defines global data such as unique user ID and whether they opted in
    for analytics.
    """

    def __init__(self, **data: Any):
        """We persist the attributes in the config file."""
        super().__init__(**data)
        self._dump()

    def __setattr__(self, name, value):
        """We hook into this to persist state as attributes are changed

        This basically means any variable changed through any object of
         this class will result in a persistent, stateful change in the system.
        """
        super().__setattr__(name, value)
        self._dump()

    @staticmethod
    @abstractmethod
    def get_config_dir() -> Text:
        """Return the config dir."""

    @staticmethod
    @abstractmethod
    def get_config_file_name() -> Text:
        """Return the config file name."""

    def _dump(self):
        """Dumps all current values to config."""
        config_path = self.get_config_path()
        if not path_utils.file_exists(str(config_path)):
            path_utils.create_file_if_not_exists(str(config_path))
        path_utils.write_file_contents(
            config_path, self.json(indent=2, sort_keys=True)
        )

    def get_config_path(self) -> Text:
        """Returns the full path of the config file."""
        return os.path.join(self.get_config_dir(), self.get_config_file_name())

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
                define_json_config_settings_source(
                    BaseConfig.get_config_dir(),
                    BaseConfig.get_config_file_name(),
                ),
                env_settings,
            )
