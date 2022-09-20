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
"""Utility functions for ZenML settings."""
import re
from typing import TYPE_CHECKING, Dict, Sequence, Type

from zenml.config.constants import (
    DOCKER_CONFIGURATION_KEY,
    RESOURCE_CONFIGURATION_KEY,
)
from zenml.enums import StackComponentType

if TYPE_CHECKING:
    from zenml.config.settings import Settings
    from zenml.stack import StackComponent

STACK_COMPONENT_REGEX = re.compile(
    "(" + "|".join(StackComponentType.values()) + ")\..*"
)


def get_settings_key_for_stack_component(
    stack_component: "StackComponent",
) -> str:
    """Gets the settings key for a stack component.

    Args:
        stack_component: The stack component for which to get the key.

    Returns:
        The settings key for the stack component.
    """
    return f"{stack_component.TYPE}.{stack_component.name}"


def is_valid_setting_key(key: str) -> bool:
    """Checks whether a settings key is valid.

    Args:
        key: The key to check.

    Returns:
        If the key is valid.
    """
    return is_universal_setting_key(key) or is_stack_component_setting_key(key)


def is_stack_component_setting_key(key: str) -> bool:
    """Checks whether a settings key refers to a stack component.

    Args:
        key: The key to check.

    Returns:
        If the key refers to a stack component.
    """
    return bool(STACK_COMPONENT_REGEX.fullmatch(key))


def is_universal_setting_key(key: str) -> bool:
    """Checks whether the key refers to a universal setting.

    Args:
        key: The key to check.

    Returns:
        If the key refers to a universal setting.
    """
    return key in get_universal_settings()


def get_universal_settings() -> Dict[str, Type["Settings"]]:
    """Returns all universal settings.

    Returns:
        Dictionary mapping universal settings keys to their type.
    """
    from zenml.config import DockerConfiguration, ResourceConfiguration

    return {
        DOCKER_CONFIGURATION_KEY: DockerConfiguration,
        RESOURCE_CONFIGURATION_KEY: ResourceConfiguration,
    }


def validate_setting_keys(setting_keys: Sequence[str]) -> None:
    """Validates settings keys.

    Args:
        setting_keys: The keys to validate.

    Raises:
        ValueError: If any key is invalid.
    """
    for key in setting_keys:
        if not is_valid_setting_key(key):
            raise ValueError(f"Invalid settings key: {key}")
