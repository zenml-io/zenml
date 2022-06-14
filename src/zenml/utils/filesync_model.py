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
"""Filesync utils for ZenML."""

import json
import os
from typing import Any, Optional

from pydantic import BaseModel

from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import yaml_utils

logger = get_logger(__name__)


class FileSyncModel(BaseModel):
    """Pydantic model synchronized with a configuration file.

    Use this class as a base Pydantic model that is automatically synchronized
    with a configuration file on disk.

    This class overrides the __setattr__ and __getattr__ magic methods to
    ensure that the FileSyncModel instance acts as an in-memory cache of the
    information stored in the associated configuration file.
    """

    _config_file: str
    _config_file_timestamp: Optional[float]

    def __init__(self, config_file: str, **kwargs: Any) -> None:
        """Create a FileSyncModel instance synchronized with a configuration file on disk.

        Args:
            config_file: configuration file path. If the file exists, the model
                will be initialized with the values from the file.
            **kwargs: additional keyword arguments to pass to the Pydantic model
                constructor. If supplied, these values will override those
                loaded from the configuration file.
        """
        config_dict = {}
        if fileio.exists(config_file):
            config_dict = yaml_utils.read_yaml(config_file)

        self._config_file = config_file
        self._config_file_timestamp = None

        config_dict.update(kwargs)
        super(FileSyncModel, self).__init__(**config_dict)

        # write the configuration file to disk, to reflect new attributes
        # and schema changes
        self.write_config()

    def __setattr__(self, key: str, value: Any) -> None:
        """Sets an attribute on the model and persists it in the configuration file.

        Args:
            key: attribute name.
            value: attribute value.
        """
        super(FileSyncModel, self).__setattr__(key, value)
        if key.startswith("_"):
            return
        self.write_config()

    def __getattribute__(self, key: str) -> Any:
        """Gets an attribute value for a specific key.

        Args:
            key: attribute name.

        Returns:
            attribute value.
        """
        if not key.startswith("_") and key in self.__dict__:
            self.load_config()
        return super(FileSyncModel, self).__getattribute__(key)

    def write_config(self) -> None:
        """Writes the model to the configuration file."""
        config_dict = json.loads(self.json())
        yaml_utils.write_yaml(self._config_file, config_dict)
        self._config_file_timestamp = os.path.getmtime(self._config_file)

    def load_config(self) -> None:
        """Loads the model from the configuration file on disk."""
        if not fileio.exists(self._config_file):
            return

        # don't reload the configuration if the file hasn't
        # been updated since the last load
        file_timestamp = os.path.getmtime(self._config_file)
        if file_timestamp == self._config_file_timestamp:
            return

        if self._config_file_timestamp is not None:
            logger.info(f"Reloading configuration file {self._config_file}")

        # refresh the model from the configuration file values
        config_dict = yaml_utils.read_yaml(self._config_file)
        for key, value in config_dict.items():
            super(FileSyncModel, self).__setattr__(key, value)

        self._config_file_timestamp = file_timestamp

    class Config:
        """Pydantic configuration class."""

        # all attributes with leading underscore are private and therefore
        # are mutable and not included in serialization
        underscore_attrs_are_private = True
