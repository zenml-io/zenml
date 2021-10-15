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
from abc import abstractmethod
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseSettings, Field

from zenml.core.utils import generate_customise_sources
from zenml.logger import get_logger
from zenml.utils import path_utils

logger = get_logger(__name__)


class BaseComponent(BaseSettings):
    """Class definition for the base config.

    The base component class defines the basic serialization / deserialization
    of various components used in ZenML. The logic of the serialization /
    deserialization is as follows:

    * If a `uuid` is passed in, then the object is read from a file, so the
    constructor becomes a query for an object that is assumed to already been
    serialized.
    * If a 'uuid` is NOT passed, then a new object is created with the default
    args (and any other args that are passed), and therefore a fresh
    serialization takes place.
    """

    uuid: Optional[UUID] = Field(default_factory=uuid4)
    _file_suffix = ".json"

    def __init__(self, **values: Any):
        # Here, we insert monkey patch the `customise_sources` function
        #  because we want to dynamically generate the serialization
        #  file path and name.

        if hasattr(self, "uuid"):
            self.__config__.customise_sources = generate_customise_sources(
                self.get_serialization_dir(),
                self.get_serialization_file_name(),
            )
        elif "uuid" in values:
            self.__config__.customise_sources = generate_customise_sources(
                self.get_serialization_dir(),
                f"{str(values['uuid'])}{self._file_suffix}",
            )
        else:
            self.__config__.customise_sources = generate_customise_sources(
                self.get_serialization_dir(),
                self.get_serialization_file_name(),
            )

        # Initialize values from the above sources.
        super().__init__(**values)

    def _dump(self):
        """Dumps all current values to the serialization file."""
        self._create_serialization_file_if_not_exists()
        f = self.get_serialization_full_path()

        path_utils.write_file_contents_as_string(
            f, self.json(indent=2, sort_keys=True)
        )

    def _create_serialization_file_if_not_exists(self):
        """Creates the serialization file if it does not exist."""
        f = self.get_serialization_full_path()
        if not path_utils.file_exists(str(f)):
            path_utils.create_file_if_not_exists(str(f))

    @abstractmethod
    def get_serialization_dir(self) -> str:
        """Return the dir where object is serialized."""

    def get_serialization_file_name(self) -> str:
        """Return the name of the file where object is serialized. This
        has a sane default in cases where uuid is not passed externally, and
        therefore reading from a serialize file is not an option for the table.
        However, we still this function to go through without an exception,
        therefore the sane default."""
        if hasattr(self, "uuid"):
            return f"{str(self.uuid)}{self._file_suffix}"
        else:
            return f"DEFAULT{self._file_suffix}"

    def get_serialization_full_path(self) -> str:
        """Returns the full path of the serialization file."""
        return os.path.join(
            self.get_serialization_dir(), self.get_serialization_file_name()
        )

    def update(self):
        """Persist the current state of the component.

        Calling this will result in a persistent, stateful change in the
        system.
        """
        self._dump()

    def delete(self):
        """Deletes the persisted state of this object."""
        path_utils.rm_file(self.get_serialization_full_path())

    class Config:
        """Configuration of settings."""

        env_prefix = "zenml_"
