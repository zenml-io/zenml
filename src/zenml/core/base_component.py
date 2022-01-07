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
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseSettings, Field, root_validator

import zenml.io.utils
from zenml.core.utils import generate_customise_sources
from zenml.io import fileio
from zenml.logger import get_logger

logger = get_logger(__name__)
SUPERFLUOUS_OPTIONS_ATTRIBUTE_NAME = "_superfluous_options"


class BaseComponent(BaseSettings):
    """Class definition for the base config.

    The base component class defines the basic serialization / deserialization
    of various components used in ZenML. The logic of the serialization /
    deserialization is as follows:

    * If a `uuid` is passed in, then the object is read from a file, so
      theconstructor becomes a query for an object that is assumed to already
      been serialized.
    * If a 'uuid` is NOT passed, then a new object is created with the default
      args (and any other args that are passed), and therefore a fresh
      serialization takes place.
    """

    uuid: Optional[UUID] = Field(default_factory=uuid4)
    _file_suffix = ".json"
    _superfluous_options: Dict[str, Any] = {}
    _serialization_dir: str

    def __init__(self, serialization_dir: str, **values: Any):
        # Here, we insert monkey patch the `customise_sources` function
        #  because we want to dynamically generate the serialization
        #  file path and name.

        if hasattr(self, "uuid"):
            self.__config__.customise_sources = generate_customise_sources(  # type: ignore[assignment] # noqa
                serialization_dir,
                self.get_serialization_file_name(),
            )
        elif "uuid" in values:
            self.__config__.customise_sources = generate_customise_sources(  # type: ignore[assignment] # noqa
                serialization_dir,
                f"{str(values['uuid'])}{self._file_suffix}",
            )
        else:
            self.__config__.customise_sources = generate_customise_sources(  # type: ignore[assignment] # noqa
                serialization_dir,
                self.get_serialization_file_name(),
            )

        # Initialize values from the above sources.
        super().__init__(**values)
        self._serialization_dir = serialization_dir
        self._save_backup_file_if_required()

    def _save_backup_file_if_required(self) -> None:
        """Saves a backup of the config file if the schema changed."""
        if self._superfluous_options:
            logger.warning(
                "Found superfluous configuration values for class `%s`: %s",
                self.__class__.__name__,
                set(self._superfluous_options),
            )
            config_path = self.get_serialization_full_path()
            if fileio.file_exists(config_path):
                backup_path = config_path + ".backup"
                fileio.copy(config_path, backup_path, overwrite=True)
                logger.warning(
                    "Saving backup configuration to '%s'.", backup_path
                )

            # save the updated file without the extra options
            self.update()

    def _dump(self) -> None:
        """Dumps all current values to the serialization file."""
        self._create_serialization_file_if_not_exists()
        file_path = self.get_serialization_full_path()
        file_content = self.json(
            indent=2,
            sort_keys=True,
            exclude={SUPERFLUOUS_OPTIONS_ATTRIBUTE_NAME},
        )
        zenml.io.utils.write_file_contents_as_string(file_path, file_content)

    def dict(self, **kwargs: Any) -> Dict[str, Any]:
        """Removes private attributes from pydantic dict so they don't get
        stored in our config files."""
        return {
            key: value
            for key, value in super().dict(**kwargs).items()
            if not key.startswith("_")
        }

    def _create_serialization_file_if_not_exists(self) -> None:
        """Creates the serialization file if it does not exist."""
        f = self.get_serialization_full_path()
        if not fileio.file_exists(str(f)):
            fileio.create_file_if_not_exists(str(f))

    def get_serialization_dir(self) -> str:
        """Return the dir where object is serialized."""
        return self._serialization_dir

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
            self._serialization_dir, self.get_serialization_file_name()
        )

    def update(self) -> None:
        """Persist the current state of the component.

        Calling this will result in a persistent, stateful change in the
        system.
        """
        self._dump()

    def delete(self) -> None:
        """Deletes the persisted state of this object."""
        fileio.remove(self.get_serialization_full_path())

    @root_validator(pre=True)
    def check_superfluous_options(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detects superfluous config values (usually read from an existing
        config file after the schema changed) and saves them in the classes
        `_superfluous_options` attribute."""
        field_names = {field.alias for field in cls.__fields__.values()}

        superfluous_options: Dict[str, Any] = {}
        for key in set(values):
            if key not in field_names:
                superfluous_options[key] = values.pop(key)

        values[SUPERFLUOUS_OPTIONS_ATTRIBUTE_NAME] = superfluous_options
        return values

    class Config:
        """Configuration of settings."""

        arbitrary_types_allowed = True
        env_prefix = "zenml_"
        # allow extra options so we can detect legacy configuration files
        extra = "allow"
