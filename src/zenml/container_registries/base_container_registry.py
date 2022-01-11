#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Base class for all container registries."""

import os
from typing import Any

from zenml.core.base_component import BaseComponent
from zenml.io.utils import get_zenml_config_dir


class BaseContainerRegistry(BaseComponent):
    """Base class for all ZenML container registries."""

    uri: str
    _CONTAINER_REGISTRY_DIR_NAME: str = "container_registries"

    def __init__(self, repo_path: str, **kwargs: Any) -> None:
        """Initializes a BaseContainerRegistry instance.

        Args:
            repo_path: Path to the repository of this container registry.
        """
        serialization_dir = os.path.join(
            get_zenml_config_dir(repo_path),
            self._CONTAINER_REGISTRY_DIR_NAME,
        )
        super().__init__(serialization_dir=serialization_dir, **kwargs)

    class Config:
        """Configuration of settings."""

        env_prefix = "zenml_container_registry_"
