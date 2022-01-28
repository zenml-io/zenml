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

from typing import TYPE_CHECKING, Any, Dict, List, Type

from zenml.exceptions import StepInterfaceError
from zenml.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.artifacts.base_artifact import BaseArtifact


class ArtifactTypeRegistry(object):
    """A registry to keep track of which datatypes map to which artifact
    types"""

    def __init__(self) -> None:
        """Initialization with an empty registry"""
        self._artifact_types: Dict[Type[Any], List[Type["BaseArtifact"]]] = {}

    def register_integration(
        self, key: Type[Any], type_: List[Type["BaseArtifact"]]
    ) -> None:
        """Method to register an integration within the registry

        Args:
            key: any datatype
            type_: the list of artifact type that the given datatypes is
                associated with
        """
        self._artifact_types[key] = type_

    def get_artifact_type(self, key: Type[Any]) -> List[Type["BaseArtifact"]]:
        """Method to extract the list of artifact types given the data type"""
        if key in self._artifact_types:
            return self._artifact_types[key]
        else:
            compatible_superclasses = {
                tuple(self._artifact_types[t])
                for t in self._artifact_types
                if issubclass(key, t)
            }
            if len(compatible_superclasses) == 1:
                return list(compatible_superclasses.pop())
            elif len(compatible_superclasses) > 1:
                raise StepInterfaceError(
                    f"Type {key} is subclassing more than one type and these "
                    f"types map to different materializers. These "
                    f"materializers feature a different list associated "
                    f"artifact types within the registry: "
                    f"{compatible_superclasses}. Please specify which "
                    f"of these artifact types you would like to use "
                    f"explicitly in your step."
                )

        raise StepInterfaceError(
            f"Type {key} does not have a default `Materializer` thus it does "
            f"not have any associated `ArtifactType`s! Please specify your "
            f"own `Materializer`."
        )


# Creating the global registry
type_registry = ArtifactTypeRegistry()
