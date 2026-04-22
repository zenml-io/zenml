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
from typing import (
    TYPE_CHECKING,
    Dict,
    Mapping,
    Optional,
    Sequence,
    Type,
    Union,
)

from zenml.config.constants import (
    DEPLOYMENT_SETTINGS_KEY,
    DOCKER_SETTINGS_KEY,
    RESOURCE_SETTINGS_KEY,
)
from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.models.v2.core.component import ComponentResponse

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.stack import StackComponent
    from zenml.stack.flavor import Flavor

logger = get_logger(__name__)

STACK_COMPONENT_REGEX = re.compile(
    "(" + "|".join(StackComponentType.values()) + r")([.:].+)?"
)


def get_stack_component_setting_key(stack_component: "StackComponent") -> str:
    """Gets the setting key for a stack component.

    Args:
        stack_component: The stack component for which to get the key.

    Returns:
        The setting key for the stack component.
    """
    return f"{stack_component.type}.{stack_component.flavor}"


def get_stack_component_name_setting_key(
    stack_component: Union["StackComponent", ComponentResponse],
) -> str:
    """Gets the canonical name-scoped setting key for a stack component.

    Args:
        stack_component: The stack component for which to get the key.

    Returns:
        The canonical setting key for the stack component.
    """
    return f"{stack_component.type}:{stack_component.name}"


def get_flavor_setting_key(flavor: "Flavor") -> str:
    """Gets the setting key for a flavor.

    Args:
        flavor: The flavor for which to get the key.

    Returns:
        The setting key for the flavor.
    """
    return f"{flavor.type}.{flavor.name}"


def _get_component_flavor(
    component: Union["StackComponent", ComponentResponse],
) -> str:
    """Gets the flavor name for a runtime or response component.

    Args:
        component: The component whose flavor should be returned.

    Returns:
        The component flavor.
    """
    from zenml.stack import StackComponent

    if isinstance(component, StackComponent):
        return component.flavor
    return component.flavor_name


def resolve_stack_component_setting_key(
    key: str,
    components_by_type: Mapping[
        StackComponentType,
        Sequence[Union["StackComponent", ComponentResponse]],
    ],
    legacy: bool = False,
) -> Optional[str]:
    """Resolves a setting selector to a canonical component key.

    For ZenML versions before 0.94.3, the settings keys are normalized to `type.flavor`,
    however, for newer versions, the settings keys are normalized to `type:name`.

    Args:
        key: The user-provided settings key.
        components_by_type: Components grouped by type.
        legacy: Flag to indicate whether to use legacy default settings keys.

    Returns:
        The canonical key for the resolved component. Returns ``None`` if an
        explicit name/flavor selector doesn't match any component.

    Raises:
        ValueError: If the selector resolves ambiguously or if a shortcut key
            cannot be resolved.
    """
    if not is_stack_component_setting_key(key):
        raise ValueError(f"Invalid stack component setting key `{key}`.")

    selector = ""
    if ":" in key:
        component_type_str, selector = key.split(":", 1)
        selector_kind = "name"
    elif "." in key:
        component_type_str, selector = key.split(".", 1)
        selector_kind = "flavor"
    else:
        component_type_str = key
        selector_kind = "shortcut"

    component_type = StackComponentType(component_type_str)
    components = list(components_by_type.get(component_type, []))

    if selector_kind == "shortcut":
        matches = components[:1]
    elif selector_kind == "flavor":
        matches = [
            component
            for component in components
            if _get_component_flavor(component) == selector
        ]
    else:
        matches = [
            component for component in components if component.name == selector
        ]

    if len(matches) != 1:
        if selector_kind == "shortcut":
            raise ValueError(
                "Unable to resolve settings key "
                f"`{key}` because the stack has no default component of type "
                f"{component_type}."
            )
        if len(matches) == 0:
            logger.warning(
                "Ignoring settings key `%s` because it doesn't match any "
                "attached %s component.",
                key,
                component_type.value,
            )
            return None
        raise ValueError(
            "Unable to resolve settings key "
            f"`{key}` because it matched {len(matches)} components."
        )

    if legacy:
        return f"{component_type}.{_get_component_flavor(matches[0])}"
    else:
        return f"{component_type}:{matches[0].name}"


def normalize_stack_component_setting_keys(
    settings: Dict[str, "BaseSettings"],
    components_by_type: Mapping[
        StackComponentType,
        Sequence[Union["StackComponent", ComponentResponse]],
    ],
    legacy: bool = False,
) -> None:
    """Normalizes component settings keys to canonical component keys.

    For ZenML versions before 0.94.3, the settings keys are normalized to `type.flavor`,
    however, for newer versions, the settings keys are normalized to `type:name`.

    Args:
        settings: Settings to normalize in place.
        components_by_type: Components grouped by type.
        legacy: Flag to indicate whether to use legacy default settings keys.

    Raises:
        ValueError: If a selector does not resolve to exactly one component.
    """
    resolved_settings: Dict[str, "BaseSettings"] = {}
    resolved_from: Dict[str, str] = {}
    ignored_keys = []

    for key, component_settings in settings.items():
        if not is_stack_component_setting_key(key):
            continue

        resolved_key = resolve_stack_component_setting_key(
            key=key,
            components_by_type=components_by_type,
            legacy=legacy,
        )
        if resolved_key is None:
            ignored_keys.append(key)
            continue
        if existing_key := resolved_from.get(resolved_key):
            raise ValueError(
                "Duplicate settings provided using the keys "
                f"{existing_key} and {key}. Both refer to {resolved_key}. "
                "Remove settings for one of them to fix this error."
            )

        resolved_from[resolved_key] = key
        resolved_settings[resolved_key] = component_settings

    for key in list(resolved_from.values()):
        settings.pop(key, None)

    for key in ignored_keys:
        settings.pop(key, None)

    settings.update(resolved_settings)


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


def get_general_settings() -> Dict[str, Type["BaseSettings"]]:
    """Returns all general settings.

    Returns:
        Dictionary mapping general settings keys to their type.
    """
    from zenml.config import (
        DeploymentSettings,
        DockerSettings,
        ResourceSettings,
    )

    return {
        DOCKER_SETTINGS_KEY: DockerSettings,
        RESOURCE_SETTINGS_KEY: ResourceSettings,
        DEPLOYMENT_SETTINGS_KEY: DeploymentSettings,
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
                "`<STACK_COMPONENT_TYPE>`, "
                "`<STACK_COMPONENT_TYPE>.<STACK_COMPONENT_FLAVOR>`, or "
                "`<STACK_COMPONENT_TYPE>:<STACK_COMPONENT_NAME>`."
            )
