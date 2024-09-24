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

import os
from typing import Any, Optional

from pydantic import (
    BaseModel,
    ValidationError,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    model_validator,
)

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
    _config_file_timestamp: Optional[float] = None

    @model_validator(mode="wrap")
    @classmethod
    def config_validator(
        cls,
        data: Any,
        handler: ValidatorFunctionWrapHandler,
        info: ValidationInfo,
    ) -> "FileSyncModel":
        """Wrap model validator to infer the config_file during initialization.

        Args:
            data: The raw data that is provided before the validation.
            handler: The actual validation function pydantic would use for the
                built-in validation function.
            info: The context information during the execution of this
                validation function.

        Returns:
            the actual instance after the validation

        Raises:
            ValidationError: if you try to validate through a JSON string. You
                need to provide a config_file path when you create a
                FileSyncModel.
        """
        # Disable json validation
        if info.mode == "json":
            raise ValidationError(
                "You can not instantiate filesync models using the JSON mode."
            )

        if isinstance(data, dict):
            # Assert that the config file is defined
            assert (
                "config_file" in data
            ), "You have to provide a path for the configuration file."

            config_file = data.pop("config_file")

            # Load the current values and update with new values
            config_dict = {}
            if fileio.exists(config_file):
                config_dict = yaml_utils.read_yaml(config_file)
            config_dict.update(data)

            # Execute the regular validation
            model = handler(config_dict)

            assert isinstance(model, cls)

            # Assign the private attribute and save the config
            model._config_file = config_file
            model.write_config()

        else:
            # If the raw value is not a dict, apply proper validation.
            model = handler(data)

            assert isinstance(model, cls)

        return model

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
        yaml_utils.write_yaml(self._config_file, self.model_dump(mode="json"))
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
