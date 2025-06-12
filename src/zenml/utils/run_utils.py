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
"""Utility functions for pipeline runs."""

from typing import cast

from zenml.client import Client
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.logger import get_logger
from zenml.models import PipelineRunUpdate, StepRunUpdate
from zenml.models.v2.core.pipeline_run import PipelineRunResponse
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.stack.stack_component import StackComponent

logger = get_logger(__name__)


def refresh_run_status(
    run: PipelineRunResponse,
    include_step_updates: bool = False,
) -> PipelineRunResponse:
    """Refresh the status of a pipeline run if it is initializing/running.

    Args:
        run: The pipeline run to refresh.
        include_step_updates: Flag deciding whether we should also refresh
            the status of individual steps.

    Returns:
        The refreshed pipeline run.
    """
    # Check if the stack still accessible
    if run.stack is None:
        raise ValueError(
            "The stack that this pipeline run response was executed on"
            "is either not accessible or has been deleted."
        )

    # Check if the orchestrator is still accessible
    orchestrator_list = run.stack.components.get(
        StackComponentType.ORCHESTRATOR, []
    )
    if len(orchestrator_list) == 0:
        raise ValueError(
            "The orchestrator that this pipeline run response was "
            "executed with is either not accessible or has been deleted."
        )

    orchestrator = cast(
        BaseOrchestrator,
        StackComponent.from_model(component_model=orchestrator_list[0]),
    )

    # Fetch the status (and optionally step statuses)
    pipeline_status, step_statuses = orchestrator.fetch_status(
        run=run, include_steps=include_step_updates
    )

    client = Client()

    # Update step statuses
    if include_step_updates:
        assert step_statuses is not None

        for step_name, step_status in step_statuses.items():
            # If the new status is different from the current status, update it
            if step_status != run.steps[step_name].status:
                try:
                    client.zen_store.update_run_step(
                        step_run_id=run.steps[step_name].id,
                        step_run_update=StepRunUpdate(status=step_status),
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to update status for step '{step_name}': {e}"
                    )

    # Update pipeline status
    if pipeline_status != run.status:
        return client.zen_store.update_run(
            run_id=run.id,
            run_update=PipelineRunUpdate(status=pipeline_status),
        )

    return run
