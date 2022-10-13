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
"""Implementation of a default materializer registry."""

from typing import TYPE_CHECKING, Any, Dict, Type

from zenml.exceptions import StepInterfaceError
from zenml.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.materializers.base_materializer import BaseMaterializer


class MaterializerRegistry:
    """Matches a Python type to a default materializer."""

    def __init__(self) -> None:
        """Initialize the materializer registry."""
        self.materializer_types: Dict[Type[Any], Type["BaseMaterializer"]] = {}

    def register_materializer_type(
        self, key: Type[Any], type_: Type["BaseMaterializer"]
    ) -> None:
        """Registers a new materializer.

        Args:
            key: Indicates the type of object.
            type_: A BaseMaterializer subclass.
        """
        if key not in self.materializer_types:
            self.materializer_types[key] = type_
            logger.debug(f"Registered materializer {type_} for {key}")
        else:
            logger.debug(
                f"Found existing materializer class for {key}: "
                f"{self.materializer_types[key]}. Skipping registration of "
                f"{type_}."
            )

    def register_and_overwrite_type(
        self, key: Type[Any], type_: Type["BaseMaterializer"]
    ) -> None:
        """Registers a new materializer and also overwrites a default if set.

        Args:
            key: Indicates the type of object.
            type_: A BaseMaterializer subclass.
        """
        self.materializer_types[key] = type_
        logger.debug(f"Registered materializer {type_} for {key}")

    def __getitem__(self, key: Type[Any]) -> Type["BaseMaterializer"]:
        """Get a single materializers based on the key.

        Args:
            key: Indicates the type of object.

        Returns:
            `BaseMaterializer` subclass that was registered for this key.

        Raises:
            StepInterfaceError: If the key (or any of its superclasses) is not
                registered or the key has more than one superclass with
                different default materializers
        """
        # Check whether the type is registered
        if key in self.materializer_types:
            return self.materializer_types[key]

        # If the type is not registered, check for superclasses
        materializers_for_compatible_superclasses = {
            materializer
            for registered_type, materializer in self.materializer_types.items()
            if issubclass(key, registered_type)
        }

        # Make sure that there is only a single materializer
        if len(materializers_for_compatible_superclasses) == 1:
            return materializers_for_compatible_superclasses.pop()
        if len(materializers_for_compatible_superclasses) > 1:
            raise StepInterfaceError(
                f"Type {key} is subclassing more than one type, thus it "
                f"maps to multiple materializers within the materializer "
                f"registry: {materializers_for_compatible_superclasses}. "
                f"Please specify which of these materializers you would "
                f"like to use explicitly in your step.",
                url="https://docs.zenml.io/advanced-guide/pipelines/materializers",
            )
        raise StepInterfaceError(
            f"No materializer registered for class {key}. You can register a "
            f"default materializer for specific types by subclassing "
            f"`BaseMaterializer` and setting its `ASSOCIATED_TYPES` class"
            f" variable.",
            url="https://docs.zenml.io/advanced-guide/pipelines/materializers",
        )

    def get_materializer_types(
        self,
    ) -> Dict[Type[Any], Type["BaseMaterializer"]]:
        """Get all registered materializer types.

        Returns:
            A dictionary of registered materializer types.
        """
        return self.materializer_types

    def is_registered(self, key: Type[Any]) -> bool:
        """Returns if a materializer class is registered for the given type.

        Args:
            key: Indicates the type of object.

        Returns:
            True if a materializer is registered for the given type, False
            otherwise.
        """
        return any(issubclass(key, type_) for type_ in self.materializer_types)


default_materializer_registry = MaterializerRegistry()
