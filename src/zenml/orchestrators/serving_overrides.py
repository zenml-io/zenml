#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Per-request serving overrides for step configuration.

This module provides request-scoped parameter overrides that allow
runtime configuration without mutating immutable Pydantic models.
"""

from contextvars import ContextVar
from typing import Any, Dict

from zenml.logger import get_logger

logger = get_logger(__name__)

# Per-request serving overrides - each request gets its own isolated overrides
_serving_overrides: ContextVar[Dict[str, Dict[str, Any]]] = ContextVar(
    "serving_overrides", default={}
)


def initialize_serving_overrides() -> None:
    """Initialize fresh serving overrides for the current request."""
    _serving_overrides.set({})
    logger.debug("Initialized fresh serving overrides")


def set_step_parameters(step_name: str, parameters: Dict[str, Any]) -> None:
    """Set parameter overrides for a specific step.

    Args:
        step_name: Name of the step to override parameters for
        parameters: Dictionary of parameter_name -> override_value
    """
    overrides = _serving_overrides.get({})
    if step_name not in overrides:
        overrides[step_name] = {}
    overrides[step_name].update(parameters)
    _serving_overrides.set(overrides)

    logger.debug(
        f"Set parameter overrides for step '{step_name}': {list(parameters.keys())}"
    )


def get_step_parameters(step_name: str) -> Dict[str, Any]:
    """Get parameter overrides for a specific step.

    Args:
        step_name: Name of the step to get overrides for

    Returns:
        Dictionary of parameter_name -> override_value, or empty dict if none
    """
    overrides = _serving_overrides.get({})
    return overrides.get(step_name, {})


def clear_serving_overrides() -> None:
    """Clear the serving overrides to free memory."""
    _serving_overrides.set({})
    logger.debug("Cleared serving overrides")


def has_overrides() -> bool:
    """Check if any serving overrides are active.

    Returns:
        True if overrides exist, False otherwise
    """
    overrides = _serving_overrides.get({})
    return bool(overrides)
