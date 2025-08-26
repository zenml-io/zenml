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
"""Thread-safe serving context management using contextvars."""

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Dict, Generator, Optional
from uuid import uuid4

from zenml.logger import get_logger

logger = get_logger(__name__)

# Thread-safe serving context variable
# This replaces the dangerous global monkey patching in DirectExecutionEngine
serving_step_context_var: ContextVar[Optional["ServingStepContext"]] = (
    ContextVar("serving_step_context", default=None)
)

# Job-level context for tracking execution across steps
serving_job_context_var: ContextVar[Optional["ServingJobContext"]] = (
    ContextVar("serving_job_context", default=None)
)


class ServingStepContext:
    """Thread-safe step context for serving scenarios.

    This provides a minimal implementation of step context functionality
    without the overhead of the full ZenML context system. Each step
    execution gets its own context that's isolated from other concurrent
    executions.
    """

    def __init__(self, step_name: str, job_id: Optional[str] = None):
        """Initialize serving step context.

        Args:
            step_name: Name of the step being executed
            job_id: Optional job ID for tracking across steps
        """
        self.step_name = step_name
        self.job_id = job_id or str(uuid4())
        self._metadata: Dict[str, Any] = {}
        self._created_at = None

    def add_output_metadata(self, metadata: Dict[str, Any]) -> None:
        """Add metadata for step outputs (stored in context for serving).

        Args:
            metadata: Metadata to add
        """
        self._metadata.update(metadata)
        logger.debug(f"Step '{self.step_name}' metadata: {metadata}")

    def get_output_artifact_uri(
        self, output_name: Optional[str] = None
    ) -> str:
        """Get output artifact URI (mock for serving).

        Args:
            output_name: Name of the output

        Returns:
            Mock URI for serving context
        """
        return f"serving://{self.job_id}/{self.step_name}/{output_name or 'output'}"

    @property
    def step_run_info(self):
        """Mock step run info for compatibility."""
        return None

    @property
    def pipeline_run(self):
        """Mock pipeline run for compatibility."""
        return None

    @property
    def step_run(self):
        """Mock step run for compatibility."""
        return None


class ServingJobContext:
    """Job-level context for tracking pipeline execution in serving."""

    def __init__(self, job_id: str, parameters: Dict[str, Any]):
        """Initialize serving job context.

        Args:
            job_id: Unique identifier for this job
            parameters: Pipeline parameters for this execution
        """
        self.job_id = job_id
        self.parameters = parameters
        self.step_contexts: Dict[str, ServingStepContext] = {}
        self.current_step: Optional[str] = None

    def get_step_context(self, step_name: str) -> ServingStepContext:
        """Get or create step context for the given step.

        Args:
            step_name: Name of the step

        Returns:
            Step context for the given step
        """
        if step_name not in self.step_contexts:
            self.step_contexts[step_name] = ServingStepContext(
                step_name=step_name, job_id=self.job_id
            )
        return self.step_contexts[step_name]


@contextmanager
def serving_step_context(
    step_name: str, job_id: Optional[str] = None
) -> Generator[ServingStepContext, None, None]:
    """Context manager for thread-safe step execution in serving.

    This replaces the dangerous monkey-patching approach with proper
    contextvars that are isolated per thread/task.

    Args:
        step_name: Name of the step being executed
        job_id: Optional job ID for cross-step tracking

    Yields:
        ServingStepContext for this step execution
    """
    # Get or create job context
    job_context = serving_job_context_var.get()
    if not job_context and job_id:
        # Create new job context if none exists
        job_context = ServingJobContext(job_id=job_id, parameters={})

    # Create step context
    if job_context:
        step_context = job_context.get_step_context(step_name)
        job_context.current_step = step_name
    else:
        step_context = ServingStepContext(step_name=step_name, job_id=job_id)

    # Set context variables
    job_token = None
    if job_context:
        job_token = serving_job_context_var.set(job_context)
    step_token = serving_step_context_var.set(step_context)

    try:
        logger.debug(f"Entering serving step context: {step_name}")
        yield step_context
    finally:
        logger.debug(f"Exiting serving step context: {step_name}")
        # Reset context variables
        serving_step_context_var.reset(step_token)
        if job_token:
            serving_job_context_var.reset(job_token)


@contextmanager
def serving_job_context(
    job_id: str, parameters: Dict[str, Any]
) -> Generator[ServingJobContext, None, None]:
    """Context manager for job-level serving context.

    Args:
        job_id: Unique job identifier
        parameters: Pipeline parameters

    Yields:
        ServingJobContext for this job
    """
    context = ServingJobContext(job_id=job_id, parameters=parameters)
    token = serving_job_context_var.set(context)

    try:
        logger.debug(f"Entering serving job context: {job_id}")
        yield context
    finally:
        logger.debug(f"Exiting serving job context: {job_id}")
        serving_job_context_var.reset(token)


def get_serving_step_context() -> Optional[ServingStepContext]:
    """Get the current serving step context if available.

    Returns:
        Current ServingStepContext or None if not in serving context
    """
    return serving_step_context_var.get()


def get_serving_job_context() -> Optional[ServingJobContext]:
    """Get the current serving job context if available.

    Returns:
        Current ServingJobContext or None if not in serving context
    """
    return serving_job_context_var.get()


def is_serving_context() -> bool:
    """Check if we're currently in a serving context.

    Returns:
        True if in serving context, False otherwise
    """
    return serving_step_context_var.get() is not None
