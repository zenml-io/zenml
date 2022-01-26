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
from abc import ABC, abstractmethod

from zenml.enums import ArtifactStoreFlavor, StackComponentType
from zenml.stack import StackComponent


class BaseArtifactStore(StackComponent, ABC):
    """Base class for all ZenML artifact stores.

    Attributes:
        path: The root path of the artifact store.
    """

    path: str

    @property
    def type(self) -> StackComponentType:
        """The component type."""
        return StackComponentType.ARTIFACT_STORE

    @property
    @abstractmethod
    def flavor(self) -> ArtifactStoreFlavor:
        """The artifact store flavor."""
