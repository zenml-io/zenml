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
from typing import Any, Dict, Iterable, Optional

from zenml.logger import get_logger
from zenml.models import PipelineSnapshotResponse
from zenml.models.v2.core.pipeline_run import PipelineRunResponse
from zenml.utils.json_utils import pydantic_encoder

logger = get_logger(__name__)


@dataclass
class _ServingState:
    active: bool = False
    request_id: Optional[str] = None
    snapshot_id: Optional[str] = None
    pipeline_parameters: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # Per-request in-memory mode override
    use_in_memory: Optional[bool] = None
    # In-memory data storage for artifacts
    _in_memory_data: Dict[str, Any] = field(default_factory=dict)

    def reset(self) -> None:
        self.active = False
        self.request_id = None
        self.snapshot_id = None
        self.pipeline_parameters.clear()
        self.outputs.clear()
        self.use_in_memory = None
        self._in_memory_data.clear()

    def __str__(self) -> str:
        """String representation of the serving state.

        Returns:
            A string representation of the serving state.
        """
        return (
            f"ServingState(active={self.active}, "
            f"request_id={self.request_id}, snapshot_id={self.snapshot_id}, "
            f"pipeline_parameters={self.pipeline_parameters}, "
            f"outputs={self.outputs}, use_in_memory={self.use_in_memory}, "
            f"_in_memory_data={self._in_memory_data})"
        )

    def __repr__(self) -> str:
        """Representation of the serving state.

        Returns:
            A string representation of the serving state.
        """
        return self.__str__()


# Use contextvars for thread-safe, request-scoped state
_serving_context: contextvars.ContextVar[_ServingState] = (
    contextvars.ContextVar("serving_context", default=_ServingState())
)


def _get_context() -> _ServingState:
    """Get the current serving context state."""
    return _serving_context.get()


def start(
    request_id: str,
    snapshot: PipelineSnapshotResponse,
    parameters: Dict[str, Any],
    use_in_memory: Optional[bool] = None,
) -> None:
    """Initialize serving state for the current request context."""
    state = _ServingState()
    state.active = True
    state.request_id = request_id
    state.snapshot_id = str(snapshot.id)
    state.pipeline_parameters = dict(parameters or {})
    state.outputs = {}
    state.use_in_memory = use_in_memory
    _serving_context.set(state)


def stop() -> None:
    """Clear the serving state for the current request context."""
    state = _get_context()

    # Reset clears all in-memory data and URIs automatically
    state.reset()


def is_active() -> bool:
    """Return whether serving state is active in the current context."""
    return _get_context().active


def get_step_parameters(
    step_name: str, allowed_keys: Optional[Iterable[str]] = None
) -> Dict[str, Any]:
    """Get parameters for a step, optionally filtering by allowed keys.

    This returns only the direct pipeline parameters for the request. When
    ``allowed_keys`` is provided, the result is filtered to those keys.

    Args:
        step_name: The step (invocation id) to fetch parameters for.
        allowed_keys: Optional iterable of keys to filter the parameters by.

    Returns:
        A dictionary of parameters for the step, filtered if requested.
    """
    state = _get_context()
    if allowed_keys is not None:
        allowed = set(allowed_keys)
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


def get_parameter_override(name: str) -> Optional[Any]:
    """Get a parameter override from the current serving context.

    This function allows the orchestrator to check for parameter overrides
    without importing serving-specific modules directly. Only direct
    parameters are supported; nested extraction from complex objects is not
    performed.

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

    # Check direct parameter only
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


def get_use_in_memory() -> Optional[bool]:
    """Get the in-memory mode setting for the current request.

    Returns:
        The in-memory mode setting, or None if no context is active.
    """
    if is_active():
        state = _get_context()
        return state.use_in_memory
    return None


def put_in_memory_data(uri: str, data: Any) -> None:
    """Store data in memory for the given URI.

    Args:
        uri: The artifact URI to store data for.
        data: The data to store in memory.
    """
    if is_active():
        state = _get_context()
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
    run: PipelineRunResponse,
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

    return _process_artifact_outputs(run)


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
                "type": type(value).__name__,
                "note": "Use artifact loading endpoint for large outputs",
            }

        return serialized

    except Exception:
        return {
            "serialization_failed": True,
            "type": type(value).__name__,
            "note": "Use artifact loading endpoint for this output",
        }


def _process_artifact_outputs(run: PipelineRunResponse) -> Dict[str, Any]:
    """Load outputs from artifacts and serialize them safely.

    Args:
        run: Pipeline run response to iterate step outputs.

    Returns:
        Mapping from "step.output" to serialized values.
    """
    from zenml.artifacts.utils import load_artifact_from_response

    outputs: Dict[str, Any] = {}
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
                    "Failed to load artifact for %s.%s: %s",
                    step_name,
                    output_name,
                    e,
                )
    return outputs


def _make_json_safe(value: Any) -> Any:
    """Make value JSON-serializable using ZenML's encoder."""
    try:
        # Test serialization
        json.dumps(value, default=pydantic_encoder)
        return value
    except (TypeError, ValueError, OverflowError):
        # Fallback to truncated string representation
        if isinstance(value, str):
            s = value
        else:
            s = str(value)
        if len(s) <= 1000:
            return s
        # Avoid f-string interpolation cost on huge strings by simple concat
        return s[:1000] + "... [truncated]"
