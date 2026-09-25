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
from typing import (
    TYPE_CHECKING,
    Any,
    ContextManager,
    Dict,
    NamedTuple,
    Optional,
)
from uuid import UUID

from zenml.constants import (
    ENV_ZENML_EXECUTION_CONTEXT_STEP_RUN_CACHE_SIZE,
    ENV_ZENML_PREVENT_EXECUTION_CONTEXT_CACHING,
    handle_bool_env_var,
    handle_int_env_var,
)
from zenml.utils import context_utils
from zenml.utils.dict_utils import BoundedDict

if TYPE_CHECKING:
    from zenml.models import PipelineRunResponse, StepRunResponse


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
        self.step_runs: Dict[str, "StepRunResponse"] = BoundedDict(
            max_size=handle_int_env_var(
                ENV_ZENML_EXECUTION_CONTEXT_STEP_RUN_CACHE_SIZE, default=100
            )
        )


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

    if execution_context := ExecutionContext.get():
        execution_context.step_runs[step_run.name] = step_run


class ActiveRunContext(NamedTuple):
    """IDs of the pipeline run (and step run) the current code runs in."""

    pipeline_run_id: UUID
    step_run_id: Optional[UUID]
    step_name: Optional[str]


def get_active_run_context() -> Optional[ActiveRunContext]:
    """Get the pipeline run and step run the current code is executing in.

    A step context wins over a dynamic pipeline run context: a step of a
    dynamic pipeline can execute while both are active, and code in a step
    should be attributed to that step. Outside of a step, the dynamic
    pipeline run context covers the pipeline function body and run-level
    hooks.

    Returns:
        The active run context, or None if neither a step nor a dynamic
        pipeline run is active.
    """
    from zenml.execution.pipeline.dynamic.run_context import (
        DynamicPipelineRunContext,
    )
    from zenml.steps.step_context import StepContext

    if step_context := StepContext.get():
        return ActiveRunContext(
            pipeline_run_id=step_context.pipeline_run.id,
            step_run_id=step_context.step_run.id,
            step_name=step_context.step_name,
        )

    if run_context := DynamicPipelineRunContext.get():
        return ActiveRunContext(
            pipeline_run_id=run_context.run.id,
            step_run_id=None,
            step_name=None,
        )

    return None
