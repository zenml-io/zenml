"""Thread-safe runtime context for serving.

This module provides request-scoped state for serving invocations using
contextvars to ensure thread safety and proper request isolation. Each
serving request gets its own isolated context that doesn't interfere
with concurrent requests.

It also provides parameter override functionality for the orchestrator
to access serving parameters without tight coupling.
"""

import contextvars
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Set

from zenml.logger import get_logger
from zenml.models import PipelineDeploymentResponse
from zenml.utils.json_utils import pydantic_encoder

logger = get_logger(__name__)


@dataclass
class _ServingState:
    active: bool = False
    request_id: Optional[str] = None
    deployment_id: Optional[str] = None
    pipeline_parameters: Dict[str, Any] = field(default_factory=dict)
    param_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # Track in-memory artifact URIs created during this request
    in_memory_uris: Set[str] = field(default_factory=set)
    # Per-request in-memory mode override
    use_in_memory: Optional[bool] = None
    # In-memory data storage for artifacts
    _in_memory_data: Dict[str, Any] = field(default_factory=dict)

    def reset(self) -> None:
        self.active = False
        self.request_id = None
        self.deployment_id = None
        self.pipeline_parameters.clear()
        self.param_overrides.clear()
        self.outputs.clear()
        self.in_memory_uris.clear()
        self.use_in_memory = None
        self._in_memory_data.clear()


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
    use_in_memory: Optional[bool] = None,
) -> None:
    """Initialize serving state for the current request context."""
    state = _ServingState()
    state.active = True
    state.request_id = request_id
    state.deployment_id = str(deployment.id)
    state.pipeline_parameters = dict(parameters or {})
    state.param_overrides = {}  # No longer used, simplified
    state.outputs = {}
    state.use_in_memory = use_in_memory
    _serving_context.set(state)


def stop() -> None:
    """Clear the serving state for the current request context."""
    state = _get_context()

    # Best-effort cleanup of in-memory artifacts associated with this request
    if state.in_memory_uris:
        try:
            # Local import to avoid any import cycles at module import time
            from zenml.deployers.serving import _in_memory_registry as reg

            for uri in list(state.in_memory_uris):
                try:
                    reg.del_object(uri)
                except Exception:
                    # Ignore cleanup failures; memory will be reclaimed on process exit
                    pass
        except Exception:
            # If registry module isn't available for some reason, skip cleanup
            pass

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


def note_in_memory_uri(uri: str) -> None:
    """Record an in-memory artifact URI for cleanup at request end.

    Args:
        uri: The artifact URI saved to the in-memory registry.
    """
    state = _get_context()
    if not state.active:
        return
    if uri:
        state.in_memory_uris.add(uri)


def get_outputs() -> Dict[str, Dict[str, Any]]:
    """Return the outputs for all steps in the current context.

    Returns:
        A dictionary of outputs for all steps.
    """
    return dict(_get_context().outputs)


def get_parameter_override(name: str) -> Optional[Any]:
    """Get a parameter override from the current serving context.

    This function allows the orchestrator to check for parameter overrides
    without importing serving-specific modules directly.

    Args:
        name: Parameter name to look up

    Returns:
        Parameter value if found, None otherwise
    """
    if not is_active():
        return None

    state = _get_context()
    pipeline_params = state.pipeline_parameters
    if not pipeline_params:
        return None

    # Direct parameter lookup - pass parameters as-is
    return pipeline_params.get(name)


def should_use_in_memory() -> bool:
    """Check if the current request should use in-memory mode.

    Returns:
        True if in-memory mode is enabled for this request.
    """
    if is_active():
        state = _get_context()
        return state.use_in_memory is True
    return False


def put_in_memory_data(uri: str, data: Any) -> None:
    """Store data in memory for the given URI.

    Args:
        uri: The artifact URI to store data for.
        data: The data to store in memory.
    """
    if is_active():
        state = _get_context()
        state.in_memory_uris.add(uri)
        state._in_memory_data[uri] = data


def get_in_memory_data(uri: str) -> Any:
    """Get data from memory for the given URI.

    Args:
        uri: The artifact URI to retrieve data for.

    Returns:
        The stored data, or None if not found.
    """
    if is_active():
        state = _get_context()
        return state._in_memory_data.get(uri)
    return None


def has_in_memory_data(uri: str) -> bool:
    """Check if data exists in memory for the given URI.

    Args:
        uri: The artifact URI to check.

    Returns:
        True if data exists in memory for the URI.
    """
    if is_active():
        state = _get_context()
        return uri in state._in_memory_data
    return False


def process_outputs(
    runtime_outputs: Optional[Dict[str, Dict[str, Any]]],
    run: Any,  # PipelineRunResponse
    enforce_size_limits: bool = True,
    max_output_size_mb: int = 1,
) -> Dict[str, Any]:
    """Process outputs using fast path when available, slow path as fallback.

    Args:
        runtime_outputs: In-memory outputs from runtime context (fast path)
        run: Pipeline run response for artifact loading (slow path)
        enforce_size_limits: Whether to enforce size limits (disable for in-memory mode)
        max_output_size_mb: Maximum output size in MB

    Returns:
        Processed outputs ready for JSON response
    """
    if runtime_outputs:
        return _process_runtime_outputs(
            runtime_outputs, enforce_size_limits, max_output_size_mb
        )

    logger.debug("Using slow artifact loading fallback")
    return _load_outputs_from_artifacts(run)


def _process_runtime_outputs(
    runtime_outputs: Dict[str, Dict[str, Any]],
    enforce_size_limits: bool,
    max_output_size_mb: int,
) -> Dict[str, Any]:
    """Process in-memory outputs with optional size limits."""
    return {
        f"{step_name}.{output_name}": _serialize_output(
            value, enforce_size_limits, max_output_size_mb
        )
        for step_name, step_outputs in runtime_outputs.items()
        for output_name, value in step_outputs.items()
    }


def _serialize_output(
    value: Any, enforce_size_limits: bool, max_output_size_mb: int
) -> Any:
    """Serialize a single output value with error handling."""
    try:
        serialized = _make_json_safe(value)

        if not enforce_size_limits:
            return serialized

        # Check size limits only if enforced
        max_size_bytes = max(1, min(max_output_size_mb, 100)) * 1024 * 1024
        if isinstance(serialized, str) and len(serialized) > max_size_bytes:
            return {
                "data_too_large": True,
                "size_estimate": f"{len(serialized) // 1024}KB",
                "max_size_mb": max_size_bytes // (1024 * 1024),
                "type_name": type(value).__name__,
                "note": "Use artifact loading endpoint for large outputs",
            }

        return serialized

    except Exception:
        return {
            "serialization_failed": True,
            "type_name": type(value).__name__,
            "note": "Use artifact loading endpoint for this output",
        }


def _make_json_safe(value: Any) -> Any:
    """Make value JSON-serializable using ZenML's encoder."""
    try:
        # Test serialization
        json.dumps(value, default=pydantic_encoder)
        return value
    except (TypeError, ValueError, OverflowError):
        # Fallback to truncated string representation
        str_value = str(value)
        return (
            str_value
            if len(str_value) <= 1000
            else f"{str_value[:1000]}... [truncated]"
        )


def _load_outputs_from_artifacts(run: Any) -> Dict[str, Any]:
    """Load outputs from artifacts (slow fallback path)."""
    from zenml.artifacts.utils import load_artifact_from_response

    outputs = {}

    for step_name, step_run in (run.steps or {}).items():
        if not step_run or not step_run.outputs:
            continue

        for output_name, artifacts in step_run.outputs.items():
            if not artifacts:
                continue

            try:
                value = load_artifact_from_response(artifacts[0])
                if value is not None:
                    outputs[f"{step_name}.{output_name}"] = _make_json_safe(
                        value
                    )
            except Exception as e:
                logger.debug(
                    f"Failed to load artifact for {step_name}.{output_name}: {e}"
                )
