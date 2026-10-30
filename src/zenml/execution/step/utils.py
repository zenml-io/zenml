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
"""Step execution utilities."""

import time
from typing import (
    TYPE_CHECKING,
    Optional,
)
from uuid import UUID

from zenml.client import Client
from zenml.config.step_configurations import Step
from zenml.enums import ExecutionStatus, PipelineRunStopMode
from zenml.exceptions import RunStoppedException
from zenml.execution.context import ExecutionContext
from zenml.execution.pipeline.dynamic.run_context import (
    DynamicPipelineRunContext,
)
from zenml.logger import get_logger
from zenml.models import (
    PipelineSnapshotResponse,
)
from zenml.models.v2.core.step_run import StepRunResponse
from zenml.orchestrators.step_launcher import StepLauncher

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step


logger = get_logger(__name__)


def _raise_if_run_stopped(
    run_id: Optional[UUID],
    run_context: Optional[DynamicPipelineRunContext],
) -> None:
    """Interrupt retries when the owning run has a stop request.

    Args:
        run_id: Owning run ID supplied by an active execution context.
        run_context: Optional dynamic context whose runner must observe the stop.

    Raises:
        RunStoppedException: If the owning run is stopping or stopped.
    """
    if run_id is None:
        return
    run = Client().get_pipeline_run(run_id, hydrate=False)
    if run.stop_mode is not None or run.status in {
        ExecutionStatus.STOPPING,
        ExecutionStatus.STOPPED,
    }:
        if run_context:
            run_context.runner.request_stop(
                run.stop_mode or PipelineRunStopMode.IMMEDIATE
            )
        raise RunStoppedException("Pipeline stop requested.")


def launch_step(
    snapshot: "PipelineSnapshotResponse",
    step: "Step",
    orchestrator_run_id: str,
    retry: bool = False,
    remaining_retries: Optional[int] = None,
    wait: bool = True,
) -> StepRunResponse:
    """Launch a step.

    Args:
        snapshot: The snapshot.
        step: The step to run.
        orchestrator_run_id: The orchestrator run ID.
        retry: Whether to retry the step if it fails.
        remaining_retries: The number of remaining retries. If not passed, this
            will be read from the step configuration.
        wait: Whether to wait for the step to complete.

    Raises:
        RunStoppedException: If the run was stopped.
        BaseException: If the step failed all retries.

    Returns:
        The step run response.
    """

    def _launch_without_retry() -> StepRunResponse:
        launcher = StepLauncher(
            snapshot=snapshot,
            step=step,
            orchestrator_run_id=orchestrator_run_id,
            wait=wait,
        )
        return launcher.launch()

    if not retry:
        step_run = _launch_without_retry()
    else:
        run_id = None
        if run_context := DynamicPipelineRunContext.get():
            run_id = run_context.run.id
        elif (
            execution_context := ExecutionContext.get()
        ) and execution_context.pipeline_run:
            run_id = execution_context.pipeline_run.id

        retries = 0
        retry_config = step.config.retry
        if remaining_retries is None:
            max_retries = retry_config.max_retries if retry_config else 0
        else:
            max_retries = remaining_retries
        delay = retry_config.delay if retry_config else 0
        backoff = retry_config.backoff if retry_config else 1

        while retries <= max_retries:
            _raise_if_run_stopped(run_id, run_context)
            try:
                step_run = _launch_without_retry()
            except RunStoppedException:
                # Don't retry if the run was stopped
                raise
            except BaseException:
                # A stop can race the store's attempt creation guard.
                stop_check_failed = False
                try:
                    _raise_if_run_stopped(run_id, run_context)
                except RunStoppedException:
                    raise
                except Exception:
                    stop_check_failed = True
                if stop_check_failed:
                    raise
                retries += 1
                if retries <= max_retries:
                    logger.info(
                        "Sleeping for %d seconds before retrying step `%s`.",
                        delay,
                        step.config.name,
                    )
                    if run_id is None:
                        time.sleep(delay)
                    else:
                        remaining_delay = delay
                        while remaining_delay > 0:
                            _raise_if_run_stopped(run_id, run_context)
                            sleep_seconds = min(1, remaining_delay)
                            time.sleep(sleep_seconds)
                            remaining_delay -= sleep_seconds
                    delay *= backoff
                else:
                    if max_retries > 0:
                        logger.error(
                            "Failed to run step `%s` after %d retries.",
                            step.config.name,
                            max_retries,
                        )
                    raise
            else:
                break

    return step_run
