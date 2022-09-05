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
"""Runtime option utility functions."""
import re
from typing import TYPE_CHECKING, Dict, Sequence, Type

from zenml.config.constants import (
    DOCKER_CONFIGURATION_KEY,
    RESOURCE_CONFIGURATION_KEY,
)
from zenml.enums import StackComponentType

if TYPE_CHECKING:
    from zenml.config.base_runtime_options import BaseRuntimeOptions
    from zenml.stack import StackComponent

STACK_COMPONENT_REGEX = re.compile(
    "(" + "|".join(StackComponentType.values()) + ")\..*"
)


def get_runtime_options_key_for_stack_component(
    stack_component: "StackComponent",
) -> str:
    """Gets the runtime options key for a stack component.

    Args:
        stack_component: The stack component for which to get the key.

    Returns:
        The runtime options key for the stack component.
    """
    return f"{stack_component.TYPE}.{stack_component.name}"


def is_valid_runtime_option_key(key: str) -> bool:
    """Checks whether a runtime option key is valid.

    Args:
        key: The key to check.

    Returns:
        If the key is valid.
    """
    return is_universal_runtime_option_key(
        key
    ) or is_stack_component_runtime_option_key(key)


def is_stack_component_runtime_option_key(key: str) -> bool:
    """Checks whether a runtime option key refers to a stack component.

    Args:
        key: The key to check.

    Returns:
        If the key refers to a stack component.
    """
    return bool(STACK_COMPONENT_REGEX.fullmatch(key))


def is_universal_runtime_option_key(key: str) -> bool:
    """Checks whether the key refers to a universal runtime option.

    Args:
        key: The key to check.

    Returns:
        If the key refers to a universal runtime option.
    """
    return key in get_universal_runtime_options()


def get_universal_runtime_options() -> Dict[str, Type["BaseRuntimeOptions"]]:
    """Returns all universal runtime options.

    Returns:
        Dictionary mapping universal runtime option keys to their type.
    """
    from zenml.config import DockerConfiguration, ResourceConfiguration

    return {
        DOCKER_CONFIGURATION_KEY: DockerConfiguration,
        RESOURCE_CONFIGURATION_KEY: ResourceConfiguration,
    }


def validate_runtime_option_keys(runtime_option_keys: Sequence[str]) -> None:
    """Validates runtime option keys.

    Args:
        runtime_option_keys: The keys to validate.

    Raises:
        ValueError: If any key is invalid.
    """
    for key in runtime_option_keys:
        if not is_valid_runtime_option_key(key):
            raise ValueError(f"Invalid runtime option key: {key}")
