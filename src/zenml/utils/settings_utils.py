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

from zenml.config.constants import DOCKER_SETTINGS_KEY, RESOURCE_SETTINGS_KEY
from zenml.enums import StackComponentType

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.stack import Stack, StackComponent
    from zenml.stack.flavor import Flavor

STACK_COMPONENT_REGEX = re.compile(
    "(" + "|".join(StackComponentType.values()) + r")\..*"
)


def get_stack_component_setting_key(stack_component: "StackComponent") -> str:
    """Gets the setting key for a stack component.

    Args:
        stack_component: The stack component for which to get the key.

    Returns:
        The setting key for the stack component.
    """
    return f"{stack_component.type}.{stack_component.flavor}"


def get_flavor_setting_key(flavor: "Flavor") -> str:
    """Gets the setting key for a flavor.

    Args:
        flavor: The flavor for which to get the key.

    Returns:
        The setting key for the flavor.
    """
    return f"{flavor.type}.{flavor.name}"


def is_valid_setting_key(key: str) -> bool:
    """Checks whether a settings key is valid.

    Args:
        key: The key to check.

    Returns:
        If the key is valid.
    """
    return is_general_setting_key(key) or is_stack_component_setting_key(key)


def is_stack_component_setting_key(key: str) -> bool:
    """Checks whether a settings key refers to a stack component.

    Args:
        key: The key to check.

    Returns:
        If the key refers to a stack component.
    """
    return bool(STACK_COMPONENT_REGEX.fullmatch(key))


def is_general_setting_key(key: str) -> bool:
    """Checks whether the key refers to a general setting.

    Args:
        key: The key to check.

    Returns:
        If the key refers to a general setting.
    """
    return key in get_general_settings()


def get_stack_component_for_settings_key(
    key: str, stack: "Stack"
) -> "StackComponent":
    """Gets the stack component of a stack for a given settings key.

    Args:
        key: The settings key for which to get the component.
        stack: The stack from which to get the component.

    Raises:
        ValueError: If the key is invalid or the stack does not contain a
            component of the correct flavor.

    Returns:
        The stack component.
    """
    if not is_stack_component_setting_key(key):
        raise ValueError(
            f"Settings key {key} does not refer to a stack component."
        )

    component_type, flavor = key.split(".", 1)
    stack_component = stack.components.get(StackComponentType(component_type))
    if not stack_component or stack_component.flavor != flavor:
        raise ValueError(
            f"Component of type {component_type} in stack {stack} is not "
            f"of the flavor {flavor} specified by the settings key {key}."
        )
    return stack_component


def get_general_settings() -> Dict[str, Type["BaseSettings"]]:
    """Returns all general settings.

    Returns:
        Dictionary mapping general settings keys to their type.
    """
    from zenml.config import DockerSettings, ResourceSettings

    return {
        DOCKER_SETTINGS_KEY: DockerSettings,
        RESOURCE_SETTINGS_KEY: ResourceSettings,
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
            raise ValueError(
                f"Invalid setting key `{key}`. Setting keys can either refer "
                "to general settings (available keys: "
                f"{set(get_general_settings())}) or stack component specific "
                "settings. Stack component specific keys are of the format "
                "`<STACK_COMPONENT_TYPE>.<STACK_COMPONENT_FLAVOR>`."
            )
