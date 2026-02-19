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
"""Dynamic pipeline execution utilities."""

import time
from typing import TYPE_CHECKING, Generic, TypeVar
from uuid import UUID

from zenml.client import Client
from zenml.enums import ExecutionStatus
from zenml.logger import get_logger
from zenml.models import ArtifactVersionResponse, StepRunResponse

if TYPE_CHECKING:
    from zenml.execution.pipeline.dynamic.outputs import (
        OutputArtifact,
        StepRunOutputs,
    )

logger = get_logger(__name__)


T = TypeVar("T")


class _Unmapped(Generic[T]):
    """Wrapper class for inputs that should not be mapped over."""

    def __init__(self, value: T):
        """Initialize the wrapper.

        Args:
            value: The value to wrap.
        """
        self.value = value


def unmapped(value: T) -> _Unmapped[T]:
    """Helper function to pass an input without mapping over it.

    Wrap any step input with this function and then pass it to `step.map(...)`
    to pass the full value to all steps.

    Args:
        value: The value to wrap.

    Returns:
        The wrapped value.
    """
    return _Unmapped(value)


def wait_for_step_run_to_finish(step_run_id: UUID) -> "StepRunResponse":
    """Wait until a step run is finished.

    Args:
        step_run_id: The ID of the step run.

    Returns:
        The finished step run.
    """
    sleep_interval = 1
    max_sleep_interval = 64

    while True:
        step_run = Client().zen_store.get_run_step(step_run_id)

        if step_run.status != ExecutionStatus.RUNNING:
            return step_run

        logger.debug(
            "Waiting for step run with ID %s to finish (current status: %s)",
            step_run_id,
            step_run.status,
        )
        time.sleep(sleep_interval)
        if sleep_interval < max_sleep_interval:
            sleep_interval *= 2


def get_latest_step_run(
    pipeline_run_id: UUID, invocation_id: str, hydrate: bool = False
) -> "StepRunResponse":
    """Get the latest step run for a step.

    Args:
        pipeline_run_id: The ID of the pipeline run.
        invocation_id: The invocation ID of the step.
        hydrate: Whether to hydrate the step run.

    Raises:
        RuntimeError: If no step run exists for the given invocation ID.

    Returns:
        The latest step run.
    """
    step_runs = Client().list_run_steps(
        pipeline_run_id=pipeline_run_id,
        name=invocation_id,
        exclude_retried=True,
        size=1,
        hydrate=hydrate,
    )

    if not step_runs:
        raise RuntimeError(
            f"Step `{invocation_id}` not found in pipeline run "
            f"`{pipeline_run_id}`."
        )

    return step_runs.items[0]


def wait_for_step_to_finish(
    pipeline_run_id: UUID, step_name: str
) -> "StepRunResponse":
    """Wait until a step is finished.

    Args:
        pipeline_run_id: The ID of the pipeline run.
        step_name: The name of the step.

    Returns:
        The finished step run.
    """
    sleep_interval = 1
    max_sleep_interval = 64

    while True:
        step_run = get_latest_step_run(
            pipeline_run_id, step_name, hydrate=False
        )
        # If a step is in `retrying` status, another step run will be
        # created and we will try to pick it up in the next iteration.
        if step_run.status not in {
            ExecutionStatus.RUNNING,
            ExecutionStatus.RETRYING,
        }:
            return step_run

        logger.debug(
            "Waiting for step `%s` to finish (current status: %s)",
            step_name,
            step_run.status,
        )

        time.sleep(sleep_interval)
        if sleep_interval < max_sleep_interval:
            sleep_interval *= 2


def load_step_run_outputs(step_run_id: UUID) -> "StepRunOutputs":
    """Load the outputs of a step run.

    Args:
        step_run_id: The ID of the step run.

    Returns:
        The outputs of the step run.
    """
    from zenml.execution.pipeline.dynamic.outputs import OutputArtifact

    step_run = Client().zen_store.get_run_step(step_run_id)

    def _convert_output_artifact(
        output_name: str, artifact: "ArtifactVersionResponse"
    ) -> "OutputArtifact":
        return OutputArtifact(
            output_name=output_name,
            step_name=step_run.name,
            **artifact.model_dump(),
        )

    output_artifacts = step_run.regular_outputs
    if len(output_artifacts) == 0:
        return None
    elif len(output_artifacts) == 1:
        name, artifact = next(iter(output_artifacts.items()))
        return _convert_output_artifact(output_name=name, artifact=artifact)
    else:
        # Make sure we return them in the same order as they're defined in the
        # step configuration, as we don't enforce any ordering in the DB.
        return tuple(
            _convert_output_artifact(
                output_name=name, artifact=output_artifacts[name]
            )
            for name in step_run.config.outputs.keys()
        )
