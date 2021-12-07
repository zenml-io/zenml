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
"""Base class for all container registries."""

import os

from zenml.core.base_component import BaseComponent
from zenml.io.fileio import get_zenml_config_dir


class BaseContainerRegistry(BaseComponent):
    """Base class for all ZenML container registries."""

    uri: str
    _CONTAINER_REGISTRY_DIR_NAME: str = "container_registries"

    def get_serialization_dir(self) -> str:
        """Gets the local path where artifacts are stored."""
        return os.path.join(
            get_zenml_config_dir(), self._CONTAINER_REGISTRY_DIR_NAME
        )

    class Config:
        """Configuration of settings."""

        env_prefix = "zenml_container_registry_"
