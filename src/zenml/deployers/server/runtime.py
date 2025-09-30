#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Thread-safe runtime context for deployments.

This module provides request-scoped state for deployment invocations using
contextvars to ensure thread safety and proper request isolation. Each
deployment request gets its own isolated context that doesn't interfere
with concurrent requests.

It also provides parameter override functionality for the orchestrator
to access deployment parameters without tight coupling.
"""

import contextvars
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from zenml.models import PipelineSnapshotResponse


class _DeploymentState(BaseModel):
    model_config = {"extra": "forbid"}

    active: bool = False
    skip_artifact_materialization: bool = False
    request_id: Optional[str] = None
    snapshot_id: Optional[str] = None
    pipeline_parameters: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    # In-memory data storage for artifacts
    in_memory_data: Dict[str, Any] = Field(default_factory=dict)

    def reset(self) -> None:
        """Reset the deployment state."""
        self.active = False
        self.request_id = None
        self.snapshot_id = None
        self.pipeline_parameters = {}
        self.outputs = {}
        self.skip_artifact_materialization = False
        self.in_memory_data = {}


_deployment_context: contextvars.ContextVar[_DeploymentState] = (
    contextvars.ContextVar("deployment_context", default=_DeploymentState())
)


def _get_context() -> _DeploymentState:
    """Get the current deployment context state.

    Returns:
        The current deployment context state.
    """
    return _deployment_context.get()


def start(
    request_id: str,
    snapshot: PipelineSnapshotResponse,
    parameters: Dict[str, Any],
    skip_artifact_materialization: bool = False,
) -> None:
    """Initialize deployment state for the current request context.

    Args:
        request_id: The ID of the request.
        snapshot: The snapshot to deploy.
        parameters: The parameters to deploy.
        skip_artifact_materialization: Whether to skip artifact materialization.
    """
    state = _DeploymentState()
    state.active = True
    state.request_id = request_id
    state.snapshot_id = str(snapshot.id)
    state.pipeline_parameters = parameters
    state.outputs = {}
    state.skip_artifact_materialization = skip_artifact_materialization
    _deployment_context.set(state)


def stop() -> None:
    """Clear the deployment state for the current request context."""
    state = _get_context()
    state.reset()


def is_active() -> bool:
    """Return whether deployment state is active in the current context.

    Returns:
        True if the deployment state is active in the current context, False otherwise.
    """
    return _get_context().active


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


def should_skip_artifact_materialization() -> bool:
    """Check if the current request should skip artifact materialization.

    Returns:
        True if artifact materialization is skipped for this request.
    """
    if is_active():
        state = _get_context()
        return state.skip_artifact_materialization
    return False


def put_in_memory_data(uri: str, data: Any) -> None:
    """Store data in memory for the given URI.

    Args:
        uri: The artifact URI to store data for.
        data: The data to store in memory.
    """
    if is_active():
        state = _get_context()
        state.in_memory_data[uri] = data


def get_in_memory_data(uri: str) -> Any:
    """Get data from memory for the given URI.

    Args:
        uri: The artifact URI to retrieve data for.

    Returns:
        The stored data, or None if not found.
    """
    if is_active():
        state = _get_context()
        return state.in_memory_data[uri]
    return None
