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
"""Implementation of a default container registry class."""


from zenml.container_registries.base_container_registry import (
    BaseContainerRegistryFlavor,
)
from zenml.enums import ContainerRegistryFlavor


class DefaultContainerRegistryFlavor(BaseContainerRegistryFlavor):
    """Class for default ZenML container registries."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return ContainerRegistryFlavor.DEFAULT.value
