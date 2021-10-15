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

from typing import TYPE_CHECKING, Any, ClassVar, Dict, Type

from zenml.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.materializers.base_materializer import BaseMaterializer


class SpecMaterializerRegistry(object):
    """Matches spec of a step to a materializer."""

    def __init__(self):
        """Materializer types registry."""
        self.materializer_types: ClassVar[
            Dict[str, Type["BaseMaterializer"]]
        ] = {}

    def register_materializer_type(
        self, key: str, type_: Type["BaseMaterializer"]
    ):
        """Registers a new materializer.

        Args:
            key: Name of input or output parameter.
            type_: A BaseMaterializer subclass.
        """
        self.materializer_types[key] = type_
        logger.debug(f"Registered materializer {type_} for {key}")

    def get_materializer_types(
        self,
    ) -> Dict[str, Type["BaseMaterializer"]]:
        """Get all registered materializers."""
        return self.materializer_types

    def get_single_materializer_type(
        self, key: str
    ) -> Type["BaseMaterializer"]:
        """Gets a single pre-registered materializer type based on `key`."""
        if key in self.materializer_types:
            return self.materializer_types[key]
        logger.debug(
            f"Tried to fetch {key} but its not registered. Available keys: "
            f"{self.materializer_types.keys()}"
        )

    def is_registered(self, key: Type[Any]) -> bool:
        """Returns true if key type is registered, else returns False."""
        if key in self.materializer_types:
            return True
        return False
