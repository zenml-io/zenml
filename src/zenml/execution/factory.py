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
"""Factory to construct a step runtime based on context and capture."""

from zenml.execution.step_runtime import (
    BaseStepRuntime,
    DefaultStepRuntime,
    MemoryStepRuntime,
)


def get_runtime(
    *, serving: bool, memory_only: bool, metrics_enabled: bool = True
) -> BaseStepRuntime:
    """Return a runtime implementation for the given context.

    Args:
        serving: True if executing in serving context.
        memory_only: True if serving should use in-process handoff.
        metrics_enabled: Enable runtime metrics collection (realtime only).

    Returns:
        The runtime implementation.
    """
    if not serving:
        return DefaultStepRuntime()
    if memory_only:
        return MemoryStepRuntime()

    # Import here to avoid circular imports
    from zenml.execution.realtime_runtime import RealtimeStepRuntime

    rt = RealtimeStepRuntime()
    # Gate metrics at the runtime if supported
    if not metrics_enabled:
        try:
            setattr(
                rt, "_metrics_disabled", True
            )  # runtime may optionally read this
        except Exception:
            pass
    return rt
