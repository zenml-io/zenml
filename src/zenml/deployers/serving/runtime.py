"""Lightweight global runtime context for serving.

This module provides a minimal global state used during serving invocations to
override step function parameters and to capture in-memory step outputs before
they are materialized. The state is explicitly initialized and cleared for each
request to avoid leaks.

Note: This is intentionally simple and not thread-safe by design. If the
serving app runs with concurrency, a guarding mechanism should be added.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional

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


_STATE = _ServingState()


def start(
    request_id: str,
    deployment: PipelineDeploymentResponse,
    parameters: Dict[str, Any],
) -> None:
    """Initialize global serving state for an invocation."""
    _STATE.reset()
    _STATE.active = True
    _STATE.request_id = request_id
    _STATE.deployment_id = str(deployment.id)
    _STATE.pipeline_parameters = dict(parameters or {})
    _STATE.param_overrides = {}  # No longer used, simplified


def stop() -> None:
    """Clear the global serving state."""
    _STATE.reset()


def is_active() -> bool:
    """Return whether serving state is active."""
    return _STATE.active


def get_param_overrides(step_name: str) -> Dict[str, Any]:
    """Return parameter overrides for a specific step invocation id.

    Args:
        step_name: The name of the step to get the parameter overrides for.

    Returns:
        A dictionary of parameter overrides for the step.
    """
    return _STATE.param_overrides.get(step_name, {})


def get_param_overrides_for(
    step_name: str, allowed_keys: Iterable[str]
) -> Dict[str, Any]:
    """Return overrides limited to allowed keys; fall back to pipeline params.

    If no precomputed overrides exist for the step, fall back to intersecting
    pipeline parameters with the function parameter names (allowed_keys).
    """
    allowed = set(allowed_keys)
    pre = _STATE.param_overrides.get(step_name, {})
    if pre:
        return {k: v for k, v in pre.items() if k in allowed}
    return {
        k: v for k, v in _STATE.pipeline_parameters.items() if k in allowed
    }


def record_step_outputs(step_name: str, outputs: Dict[str, Any]) -> None:
    """Record raw outputs for a step by invocation id.

    Args:
        step_name: The name of the step to record the outputs for.
        outputs: A dictionary of outputs to record.
    """
    if not _STATE.active:
        return
    if not outputs:
        return
    _STATE.outputs.setdefault(step_name, {}).update(outputs)


def get_outputs() -> Dict[str, Dict[str, Any]]:
    """Return the outputs for all steps.

    Args:
        None

    Returns:
        A dictionary of outputs for all steps.
    """
    return dict(_STATE.outputs)
