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
"""Factory to construct a step runtime based on capture policy."""

from typing import Callable, Dict, Optional

from zenml.capture.config import CaptureMode, CapturePolicy
from zenml.execution.step_runtime import (
    BaseStepRuntime,
    DefaultStepRuntime,
    MemoryStepRuntime,
)

# Registry of runtime builders keyed by capture mode
_RUNTIME_REGISTRY: Dict[
    CaptureMode, Callable[[CapturePolicy], BaseStepRuntime]
] = {}


def register_runtime(
    mode: CaptureMode, builder: Callable[[CapturePolicy], BaseStepRuntime]
) -> None:
    """Register a runtime builder for a capture mode."""
    _RUNTIME_REGISTRY[mode] = builder


def get_runtime(policy: Optional[CapturePolicy]) -> BaseStepRuntime:
    """Return a runtime implementation using the registry.

    Falls back to the default runtime if no builder is registered.

    Args:
        policy: The capture policy.

    Returns:
        The runtime implementation.
    """
    policy = policy or CapturePolicy()
    builder = _RUNTIME_REGISTRY.get(policy.mode)
    if builder is None:
        raise ValueError(
            f"No runtime registered for capture mode: {policy.mode}. "
            "Expected one of: "
            + ", ".join(m.name for m in _RUNTIME_REGISTRY.keys())
        )
    return builder(policy)


# Register default builders
def _build_default(_: CapturePolicy) -> BaseStepRuntime:
    """Build the default runtime.

    Args:
        policy: The capture policy.

    Returns:
        The runtime implementation.
    """
    return DefaultStepRuntime()


def _build_realtime(policy: CapturePolicy) -> BaseStepRuntime:
    """Build the realtime runtime.

    Args:
        policy: The capture policy.

    Returns:
        The runtime implementation.
    """
    # Import here to avoid circular imports
    from zenml.execution.realtime_runtime import RealtimeStepRuntime

    # If memory_only flagged, or legacy runs/persistence indicate memory-only, use memory runtime
    memory_only = bool(policy.get_option("memory_only", False))
    runs_opt = str(policy.get_option("runs", "on")).lower()
    persistence = str(policy.get_option("persistence", "async")).lower()
    if (
        memory_only
        or runs_opt in {"off", "false", "0"}
        or persistence in {"memory", "off"}
    ):
        return MemoryStepRuntime()

    ttl = policy.get_option("ttl_seconds")
    max_entries = policy.get_option("max_entries")
    return RealtimeStepRuntime(ttl_seconds=ttl, max_entries=max_entries)


register_runtime(CaptureMode.BATCH, _build_default)
register_runtime(CaptureMode.REALTIME, _build_realtime)
