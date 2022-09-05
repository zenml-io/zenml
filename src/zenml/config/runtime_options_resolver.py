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
"""Class for resolving runtime options."""
from typing import TYPE_CHECKING, Type, TypeVar

from pydantic import ValidationError

from zenml.exceptions import RuntimeOptionsResolvingError
from zenml.utils import runtime_options_utils

if TYPE_CHECKING:
    from zenml.config.base_runtime_options import BaseRuntimeOptions
    from zenml.stack import Stack

    T = TypeVar("T", bound="BaseRuntimeOptions")


class RuntimeOptionsResolver:
    """Class for resolving runtime options."""

    def __init__(self, key: str, options: "BaseRuntimeOptions"):
        """Checks if the runtime options key is valid.

        Args:
            key: Runtime options key.
            options: The runtime options.

        Raises:
            RuntimeOptionsResolvingError: If the runtime options key is invalid.
        """
        if not runtime_options_utils.is_valid_runtime_option_key(key):
            raise RuntimeOptionsResolvingError(
                f"Invalid runtime options key: {key}."
            )

        self._key = key
        self._options = options

    def resolve(self, stack: "Stack") -> "BaseRuntimeOptions":
        """Resolves runtime options for the given stack.

        Args:
            stack: The stack for which to resolve the runtime options.

        Returns:
            The resolved runtime options.
        """
        if runtime_options_utils.is_universal_runtime_option_key(self._key):
            target_class = self._resolve_universal_runtime_options_class()
        else:
            target_class = self._resolve_stack_component_runtime_option_class(
                stack=stack
            )

        return self._convert_runtime_options(target_class=target_class)

    def _resolve_universal_runtime_options_class(
        self,
    ) -> Type["BaseRuntimeOptions"]:
        """Resolves universal runtime options.

        Returns:
            The resolved runtime options.
        """
        return runtime_options_utils.get_universal_runtime_options()[self._key]

    def _resolve_stack_component_runtime_option_class(
        self, stack: "Stack"
    ) -> Type["BaseRuntimeOptions"]:
        """Resolves stack component runtime options with the given stack.

        Args:
            stack: The stack to use for resolving.

        Raises:
            RuntimeOptionsResolvingError: If the resolving failed.

        Returns:
            The resolved runtime options.
        """
        runtime_options_class = stack.runtime_option_classes.get(self._key)
        if not runtime_options_class:
            raise RuntimeOptionsResolvingError(
                f"Failed to resolve runtime options for key {self._key}: "
                "No runtime options for this key exist in the stack. "
                "Available runtime options: "
                f"{set(stack.runtime_option_classes)}"
            )

        return runtime_options_class

    def _convert_runtime_options(self, target_class: Type["T"]) -> "T":
        """Converts the runtime options to their correct class.

        Args:
            target_class: The correct runtime options class.

        Raises:
            RuntimeOptionsResolvingError: If the conversion failed.

        Returns:
            The converted runtime options.
        """
        options_dict = self._options.dict()
        try:
            return target_class(**options_dict)
        except ValidationError:
            raise RuntimeOptionsResolvingError(
                f"Failed to convert options `{options_dict}` to expected class "
                f"{target_class}."
            )
