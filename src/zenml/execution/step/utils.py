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
)

from zenml.config.step_configurations import Step
from zenml.exceptions import RunStoppedException
from zenml.logger import get_logger
from zenml.models import (
    PipelineSnapshotResponse,
)
from zenml.models.v2.core.step_run import StepRunResponse
from zenml.orchestrators.step_launcher import StepLauncher

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step


logger = get_logger(__name__)


def launch_step(
    snapshot: "PipelineSnapshotResponse",
    step: "Step",
    orchestrator_run_id: str,
    retry: bool = False,
) -> StepRunResponse:
    """Launch a step.

    Args:
        snapshot: The snapshot.
        step: The step to run.
        orchestrator_run_id: The orchestrator run ID.
        retry: Whether to retry the step if it fails.

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
        )
        return launcher.launch()

    if not retry:
        step_run = _launch_without_retry()
    else:
        retries = 0
        retry_config = step.config.retry
        max_retries = retry_config.max_retries if retry_config else 0
        delay = retry_config.delay if retry_config else 0
        backoff = retry_config.backoff if retry_config else 1

        while retries <= max_retries:
            try:
                step_run = _launch_without_retry()
            except RunStoppedException:
                # Don't retry if the run was stopped
                raise
            except BaseException:
                retries += 1
                if retries <= max_retries:
                    logger.info(
                        "Sleeping for %d seconds before retrying step `%s`.",
                        delay,
                        step.config.name,
                    )
                    time.sleep(delay)
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
