#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""In-process execution context."""

import contextvars
from contextlib import nullcontext
from typing import TYPE_CHECKING, Any, ContextManager, Dict, Optional

from zenml.constants import (
    ENV_ZENML_EXECUTION_CONTEXT_STEP_RUN_CACHE_SIZE,
    ENV_ZENML_PREVENT_EXECUTION_CONTEXT_CACHING,
    handle_bool_env_var,
    handle_int_env_var,
)
from zenml.utils import context_utils

if TYPE_CHECKING:
    from zenml.models import PipelineRunResponse, StepRunResponse


class _StepRunCache(Dict[str, "StepRunResponse"]):
    """Step run cache that evicts the oldest entries beyond its size limit."""

    def __init__(self) -> None:
        """Initialize the cache."""
        super().__init__()
        self._max_size = handle_int_env_var(
            ENV_ZENML_EXECUTION_CONTEXT_STEP_RUN_CACHE_SIZE, default=100
        )

    def __setitem__(self, key: str, value: "StepRunResponse") -> None:
        """Set a step run.

        Args:
            key: The step run name.
            value: The step run.
        """
        super().__setitem__(key, value)
        self._evict()

    def update(self, *args: Any, **kwargs: Any) -> None:
        """Update the cache.

        Args:
            *args: Positional arguments for the dict update.
            **kwargs: Keyword arguments for the dict update.
        """
        super().update(*args, **kwargs)
        self._evict()

    def _evict(self) -> None:
        """Evict the oldest entries beyond the size limit."""
        while len(self) > self._max_size:
            del self[next(iter(self))]


class ExecutionContext(context_utils.BaseContext):
    """Execution context."""

    __context_var__ = contextvars.ContextVar("execution_context")

    def __init__(
        self, pipeline_run: Optional["PipelineRunResponse"] = None
    ) -> None:
        """Initialize the execution context.

        Args:
            pipeline_run: The pipeline run to seed the context with.
        """
        super().__init__()
        self.pipeline_run = pipeline_run
        self.step_runs: Dict[str, "StepRunResponse"] = _StepRunCache()


def setup_execution_context(
    pipeline_run: Optional["PipelineRunResponse"] = None,
) -> ContextManager[Any]:
    """Set up an execution context unless disabled via environment variable.

    Args:
        pipeline_run: The pipeline run to seed the context with.

    Returns:
        The execution context or a no-op context manager.
    """
    if handle_bool_env_var(ENV_ZENML_PREVENT_EXECUTION_CONTEXT_CACHING):
        return nullcontext()

    return ExecutionContext(pipeline_run=pipeline_run)


def record_step_run(step_run: "StepRunResponse") -> None:
    """Record a successful step run in the active execution context.

    Args:
        step_run: The step run to record.
    """
    if not step_run.status.is_successful:
        return

    if context := ExecutionContext.get():
        context.step_runs[step_run.name] = step_run
