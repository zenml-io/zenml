"""Thread-safe runtime context for serving.

This module provides request-scoped state for serving invocations using
contextvars to ensure thread safety and proper request isolation. Each
serving request gets its own isolated context that doesn't interfere
with concurrent requests.

It also provides parameter override functionality for the orchestrator
to access serving parameters without tight coupling.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Type

from zenml.logger import get_logger
from zenml.models import PipelineDeploymentResponse

logger = get_logger(__name__)


@dataclass
class _ServingState:
    active: bool = False
    request_id: Optional[str] = None
    deployment_id: Optional[str] = None
    pipeline_parameters: Dict[str, Any] = field(default_factory=dict)
    param_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def reset(self) -> None:
        self.active = False
        self.request_id = None
        self.deployment_id = None
        self.pipeline_parameters.clear()
        self.param_overrides.clear()
        self.outputs.clear()


# Use contextvars for thread-safe, request-scoped state
_serving_context: contextvars.ContextVar[_ServingState] = (
    contextvars.ContextVar("serving_context", default=_ServingState())
)


def _get_context() -> _ServingState:
    """Get the current serving context state."""
    return _serving_context.get()


def start(
    request_id: str,
    deployment: PipelineDeploymentResponse,
    parameters: Dict[str, Any],
) -> None:
    """Initialize serving state for the current request context."""
    state = _ServingState()
    state.active = True
    state.request_id = request_id
    state.deployment_id = str(deployment.id)
    state.pipeline_parameters = dict(parameters or {})
    state.param_overrides = {}  # No longer used, simplified
    state.outputs = {}
    _serving_context.set(state)


def stop() -> None:
    """Clear the serving state for the current request context."""
    state = _get_context()
    state.reset()


def is_active() -> bool:
    """Return whether serving state is active in the current context."""
    return _get_context().active


def get_step_parameters(
    step_name: str, allowed_keys: Optional[Iterable[str]] = None
) -> Dict[str, Any]:
    """Get parameters for a step, optionally filtering by allowed keys.

    This checks for any precomputed overrides for the given step name as a
    future extension point. If no overrides are present, it falls back to the
    request's pipeline parameters. When ``allowed_keys`` is provided, the
    result is filtered to those keys.

    Args:
        step_name: The step (invocation id) to fetch parameters for.
        allowed_keys: Optional iterable of keys to filter the parameters by.

    Returns:
        A dictionary of parameters for the step, filtered if requested.
    """
    state = _get_context()
    if allowed_keys is not None:
        allowed = set(allowed_keys)
        pre = state.param_overrides.get(step_name, {})
        if pre:
            return {k: v for k, v in pre.items() if k in allowed}
        return {
            k: v for k, v in state.pipeline_parameters.items() if k in allowed
        }
    # No filtering requested: return a copy to avoid accidental mutation
    return dict(state.pipeline_parameters)


def record_step_outputs(step_name: str, outputs: Dict[str, Any]) -> None:
    """Record raw outputs for a step by invocation id.

    Args:
        step_name: The name of the step to record the outputs for.
        outputs: A dictionary of outputs to record.
    """
    state = _get_context()
    if not state.active:
        return
    if not outputs:
        return
    state.outputs.setdefault(step_name, {}).update(outputs)


def get_outputs() -> Dict[str, Dict[str, Any]]:
    """Return the outputs for all steps in the current context.

    Returns:
        A dictionary of outputs for all steps.
    """
    return dict(_get_context().outputs)


def get_parameter_override(
    name: str, annotation: Optional[Type[Any]] = None
) -> Optional[Any]:
    """Get a parameter override from the current serving context.

    This function allows the orchestrator to check for parameter overrides
    without importing serving-specific modules directly.

    Args:
        name: Parameter name to look up
        annotation: Type annotation for the parameter (used for validation)

    Returns:
        Parameter value if found, None otherwise
    """
    if not is_active():
        return None

    state = _get_context()
    pipeline_params = state.pipeline_parameters
    if not pipeline_params:
        return None

    # First try direct match
    if name in pipeline_params:
        value = pipeline_params[name]
        return _validate_parameter_type(value, annotation, name)

    # Try to extract from Pydantic models using model_dump
    for param_name, param_value in pipeline_params.items():
        try:
            from pydantic import BaseModel

            if isinstance(param_value, BaseModel):
                # Use model_dump to safely get all fields as dict
                model_dict = param_value.model_dump()
                if name in model_dict:
                    extracted_value = model_dict[name]
                    logger.debug(
                        f"Extracted {name}={extracted_value} from {param_name}"
                    )
                    return _validate_parameter_type(
                        extracted_value, annotation, name
                    )
        except Exception:
            # Skip this parameter if extraction fails
            continue

    return None


def _validate_parameter_type(
    value: Any, annotation: Optional[Type[Any]], param_name: str
) -> Any:
    """Validate parameter value against type annotation.

    Args:
        value: The parameter value to validate
        annotation: Expected type annotation
        param_name: Parameter name for logging

    Returns:
        The validated value
    """
    if annotation is None:
        return value

    try:
        # For basic type validation, check if value is instance of annotation
        if hasattr(annotation, "__origin__"):
            # Handle generic types like Optional[str], List[int], etc.
            # For now, just return the value as complex type validation
            # would require more sophisticated logic
            return value
        elif isinstance(annotation, type):
            # Simple type check for basic types
            if not isinstance(value, annotation):
                logger.debug(
                    f"Parameter {param_name} type mismatch: expected {annotation}, "
                    f"got {type(value)}. Using value as-is."
                )
        return value
    except Exception:
        # If validation fails, log and return original value
        logger.debug(
            f"Type validation failed for parameter {param_name}, using value as-is"
        )
        return value
