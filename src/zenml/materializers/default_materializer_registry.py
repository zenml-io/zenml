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


class DefaultMaterializerRegistry(object):
    """Matches a python type to a default materializer."""

    materializer_types: ClassVar[Dict[Type[Any], Type["BaseMaterializer"]]] = {}

    @classmethod
    def register_materializer_type(
        cls, key: Type[Any], type_: Type["BaseMaterializer"]
    ):
        """Registers a new materializer.

        Args:
            key: Indicates the type of an object.
            type_: A BaseMaterializer subclass.
        """
        if key not in cls.materializer_types:
            cls.materializer_types[key] = type_
            logger.debug(f"Registered materializer {type_} for {key}")
        else:
            logger.debug(
                f"{key} already registered with "
                f"{cls.materializer_types[key]}. Cannot register {type_}."
            )

    def register_and_overwrite_type(
        self, key: Type[Any], type_: Type["BaseMaterializer"]
    ):
        """Registers a new materializer and also overwrites a default if set.

        Args:
            key: Indicates the type of an object.
            type_: A BaseMaterializer subclass.
        """
        self.materializer_types[key] = type_
        logger.debug(f"Registered materializer {type_} for {key}")

    def get_single_materializer_type(
        self, key: Type[Any]
    ) -> "BaseMaterializer":
        """Get a single materializers based on the key.

        Args:
            key: Indicates the type of an object.

        Returns:
            Instance of a `BaseMaterializer` subclass initialized with the
            artifact of this factory.
        """
        if key in self.materializer_types:
            return self.materializer_types[key]
        else:
            raise KeyError(
                f"Type {key} does not have a default `Materializer`! Please "
                f"specify your own `Materializer`."
            )

    def get_materializer_types(
        self,
    ) -> Dict[Type[Any], Type["BaseMaterializer"]]:
        """Get all registered materializers."""
        return self.materializer_types

    def is_registered(self, key: Type[Any]) -> bool:
        """Returns true if key type is registered, else returns False."""
        if key in self.materializer_types:
            return True
        return False


default_materializer_registry = DefaultMaterializerRegistry()
