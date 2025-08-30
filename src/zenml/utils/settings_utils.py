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
from typing import TYPE_CHECKING, Any, Dict, Optional, Sequence, Type

from zenml.config.constants import (
    DOCKER_SETTINGS_KEY,
    RESOURCE_SETTINGS_KEY,
    SERVING_CAPTURE_SETTINGS_KEY,
    SERVING_SETTINGS_KEY,
)
from zenml.config.serving_settings import ServingCaptureSettings
from zenml.enums import StackComponentType

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.stack import Stack, StackComponent
    from zenml.stack.flavor import Flavor

STACK_COMPONENT_REGEX = re.compile(
    "(" + "|".join(StackComponentType.values()) + r")(\..*)?"
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
    from zenml.config.serving_settings import ServingSettings

    return {
        DOCKER_SETTINGS_KEY: DockerSettings,
        RESOURCE_SETTINGS_KEY: ResourceSettings,
        SERVING_SETTINGS_KEY: ServingSettings,
        SERVING_CAPTURE_SETTINGS_KEY: ServingCaptureSettings,
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


def normalize_serving_capture_settings(
    settings: Dict[str, Any],
) -> Optional[ServingCaptureSettings]:
    """Normalize serving capture settings from both new and legacy formats.

    Supports both:
    - New format: settings["serving_capture"] = {"mode": "full", ...}
    - Legacy format: settings["serving"]["capture"] = {"inputs": {...}, ...}

    Args:
        settings: The settings dictionary to normalize

    Returns:
        Normalized ServingCaptureSettings if any capture settings exist, None otherwise
    """
    from zenml.config.serving_settings import ServingCaptureSettings

    # Check for new format first
    if "serving_capture" in settings:
        capture_config = settings["serving_capture"]
        if isinstance(capture_config, ServingCaptureSettings):
            return capture_config
        if isinstance(capture_config, dict):
            return ServingCaptureSettings(**capture_config)
        if isinstance(capture_config, str):
            # Handle bare string mode
            return ServingCaptureSettings(mode=capture_config)
        # Unknown type: return None to satisfy typing
        return None

    # Check for legacy format
    if "serving" in settings and isinstance(settings["serving"], dict):
        serving_config = settings["serving"]
        if "capture" in serving_config and isinstance(
            serving_config["capture"], dict
        ):
            legacy_config = serving_config["capture"]

            # Convert legacy nested structure to flat structure
            normalized = {}

            # Extract global settings
            if "mode" in legacy_config:
                normalized["mode"] = legacy_config["mode"]
            if "sample_rate" in legacy_config:
                normalized["sample_rate"] = legacy_config["sample_rate"]
            if "max_bytes" in legacy_config:
                normalized["max_bytes"] = legacy_config["max_bytes"]
            if "redact" in legacy_config:
                normalized["redact"] = legacy_config["redact"]
            if "retention_days" in legacy_config:
                normalized["retention_days"] = legacy_config["retention_days"]

            # Extract per-value settings
            if "inputs" in legacy_config:
                inputs_config = legacy_config["inputs"]
                if isinstance(inputs_config, dict):
                    # Convert nested input configs to simple mode strings
                    normalized_inputs = {}
                    for param_name, param_config in inputs_config.items():
                        if (
                            isinstance(param_config, dict)
                            and "mode" in param_config
                        ):
                            normalized_inputs[param_name] = param_config[
                                "mode"
                            ]
                        elif isinstance(param_config, str):
                            normalized_inputs[param_name] = param_config
                    if normalized_inputs:
                        normalized["inputs"] = normalized_inputs

            if "outputs" in legacy_config:
                outputs_config = legacy_config["outputs"]
                if isinstance(outputs_config, dict):
                    # Convert nested output configs to simple mode strings
                    normalized_outputs = {}
                    for output_name, output_config in outputs_config.items():
                        if (
                            isinstance(output_config, dict)
                            and "mode" in output_config
                        ):
                            normalized_outputs[output_name] = output_config[
                                "mode"
                            ]
                        elif isinstance(output_config, str):
                            normalized_outputs[output_name] = output_config
                    if normalized_outputs:
                        normalized["outputs"] = normalized_outputs
                elif isinstance(outputs_config, str):
                    # Single string for default output
                    normalized["outputs"] = outputs_config

            if normalized:
                return ServingCaptureSettings(**normalized)

    return None


def get_pipeline_serving_capture_settings(
    settings: Dict[str, Any],
) -> Optional[ServingCaptureSettings]:
    """Get pipeline-level serving capture settings with normalization.

    Args:
        settings: Pipeline settings dictionary

    Returns:
        Normalized ServingCaptureSettings if found, None otherwise
    """
    return normalize_serving_capture_settings(settings)


def get_step_serving_capture_settings(
    settings: Dict[str, Any],
) -> Optional[ServingCaptureSettings]:
    """Get step-level serving capture settings with normalization.

    Args:
        settings: Step settings dictionary

    Returns:
        Normalized ServingCaptureSettings if found, None otherwise
    """
    return normalize_serving_capture_settings(settings)
