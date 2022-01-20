#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
import json
import os
import uuid
from typing import Any, Dict, cast

from pydantic import BaseModel, Field, ValidationError

from zenml.io import fileio
from zenml.io.utils import get_global_config_directory
from zenml.utils import yaml_utils

LEGACY_CONFIG_FILE_NAME = ".zenglobal.json"


class GlobalConfig(BaseModel):
    """Stores global configuration options.

    Configuration options are read from a config file, but can be overwritten
    by environment variables. See `GlobalConfig.__getattribute__` for more
    details.

    Attributes:
        user_id: Unique user id.
        analytics_opt_in: If a user agreed to sending analytics or not.
    """

    user_id: uuid.UUID = Field(default_factory=uuid.uuid4, allow_mutation=False)
    analytics_opt_in: bool = True

    def __init__(self) -> None:
        """Initializes a GlobalConfig object using values from the config file.

        If the config file doesn't exist yet, we try to read values from the
        legacy (ZenML version < 0.6) config file.
        """
        config_values = self._read_config()
        super().__init__(**config_values)

        if not fileio.file_exists(self.config_file()):
            # the config file hasn't been written to disk, make sure to persist
            # the unique user id
            fileio.create_dir_recursive_if_not_exists(self.config_directory())
            self._write_config()

    def __setattr__(self, key: str, value: Any) -> None:
        """Sets an attribute on the global config and persists the new value."""
        super().__setattr__(key, value)
        self._write_config()

    def __getattribute__(self, key: str) -> Any:
        """Gets an attribute value for a specific key.

        If a value for this attribute was specified using an environment
        variable called `ZENML_$(ATTRIBUTE_NAME)` and its value can be parsed
        to the attribute type, the value from this environment variable is
        returned instead.
        """
        value = super().__getattribute__(key)

        environment_variable_name = f"ZENML_{key.upper()}"
        try:
            environment_variable_value = os.environ[environment_variable_name]
            # set the environment variable value to leverage pydantics type
            # conversion and validation
            super().__setattr__(key, environment_variable_value)
            return_value = super().__getattribute__(key)
            # set back the old value as we don't want to permanently store
            # the environment variable value here
            super().__setattr__(key, value)
            return return_value
        except (ValidationError, KeyError, TypeError):
            return value

    def _read_config(self) -> Dict[str, Any]:
        """Reads configuration options from disk.

        If the config file doesn't exist yet, this method falls back to reading
        options from a legacy config file or returns an empty dictionary.
        """
        legacy_config_file = os.path.join(
            GlobalConfig.config_directory(), LEGACY_CONFIG_FILE_NAME
        )

        config_values = {}
        if fileio.file_exists(self.config_file()):
            config_values = cast(
                Dict[str, Any], yaml_utils.read_yaml(self.config_file())
            )
        elif fileio.file_exists(legacy_config_file):
            config_values = cast(
                Dict[str, Any], yaml_utils.read_json(legacy_config_file)
            )

        return config_values

    def _write_config(self) -> None:
        """Writes the global configuration options to disk."""
        yaml_dict = json.loads(self.json())
        yaml_utils.write_yaml(self.config_file(), yaml_dict)

    @staticmethod
    def config_directory() -> str:
        """Path to the global configuration directory."""
        # TODO [ENG-370]: Remove the util method to get global config directory,
        #  the remaining codebase should use `GlobalConfig.config_directory()`
        #  instead.
        return get_global_config_directory()

    @staticmethod
    def config_file() -> str:
        """Path to the file where global configuration options are stored."""
        return os.path.join(GlobalConfig.config_directory(), "config.yaml")

    class Config:
        """Pydantic configuration class."""

        # Validate attributes when assigning them. We need to set this in order
        # to have a mix of mutable and immutable attributes
        validate_assignment = True
        # Ignore extra attributes from configs of previous ZenML versions
        extra = "ignore"
