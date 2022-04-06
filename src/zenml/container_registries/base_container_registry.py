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
from typing import ClassVar

from zenml.enums import StackComponentType
from zenml.stack import StackComponent


class BaseContainerRegistry(StackComponent):
    """Base class for all ZenML container registries.

    Attributes:
        uri: The URI of the container registry.
    """

    uri: str

    # Class Configuration
    TYPE: ClassVar[StackComponentType] = StackComponentType.CONTAINER_REGISTRY
    FLAVOR: ClassVar[str] = "default"
