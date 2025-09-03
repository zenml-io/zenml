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
"""Utility functions for runs."""

from typing import TYPE_CHECKING, Optional, cast

from zenml.enums import ExecutionStatus, StackComponentType
from zenml.exceptions import IllegalOperationError
from zenml.logger import get_logger
from zenml.models import PipelineRunResponse, PipelineRunUpdate, StepRunUpdate
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.stack.stack_component import StackComponent

if TYPE_CHECKING:
    from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)


def stop_run(run: PipelineRunResponse, graceful: bool = False) -> None:
    """Stop a pipeline run.

    Args:
        run: The pipeline run to stop.
        graceful: Whether to stop the run gracefully.

    Raises:
        IllegalOperationError: If the run is already stopped or being stopped.
        ValueError: If the stack is not accessible.
    """
    # Check if the stack is still accessible
    if run.stack is None:
        raise ValueError(
            "The stack that this pipeline run response was executed on "
            "is either not accessible or has been deleted."
        )

    # Check if pipeline can be stopped
    if run.status == ExecutionStatus.COMPLETED:
        raise IllegalOperationError(
            "Cannot stop a run that is already completed."
        )

    if run.status == ExecutionStatus.STOPPED:
        raise IllegalOperationError("Run is already stopped.")

    if run.status == ExecutionStatus.STOPPING:
        raise IllegalOperationError("Run is already being stopped.")

    # Check if the stack is still accessible
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

    # Stop the run
    orchestrator.stop_run(run=run, graceful=graceful)


def refresh_run_status(
    run: PipelineRunResponse,
    include_step_updates: bool = False,
    zen_store: Optional["BaseZenStore"] = None,
) -> PipelineRunResponse:
    """Refresh the status of a pipeline run if it is initializing/running.

    Args:
        run: The pipeline run to refresh.
        include_step_updates: Flag deciding whether we should also refresh
            the status of individual steps.
        zen_store: Optional ZenStore to use for updating the run. If not provided,
            the ZenStore will be fetched from the Client. This is mainly useful
            for running inside the ZenML server.

    Returns:
        The refreshed pipeline run.

    Raises:
        ValueError: If the stack or the orchestrator of the run is deleted.
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

    if zen_store is None:
        from zenml.client import Client

        zen_store = Client().zen_store
    else:
        zen_store = zen_store

    # Update step statuses
    if include_step_updates:
        if step_statuses:
            current_steps = run.steps
            for step_name, step_status in step_statuses.items():
                # If step is not in the run yet, skip
                if step_name not in current_steps:
                    continue

                # If the step is already finished, skip
                if current_steps[step_name].status.is_finished:
                    continue

                # Update only if the status has changed
                if step_status != current_steps[step_name].status:
                    try:
                        zen_store.update_run_step(
                            step_run_id=run.steps[step_name].id,
                            step_run_update=StepRunUpdate(status=step_status),
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to update status for step '{step_name}': {e}"
                        )

    # Update pipeline status
    if pipeline_status is not None and pipeline_status != run.status:
        return zen_store.update_run(
            run_id=run.id,
            run_update=PipelineRunUpdate(status=pipeline_status),
        )

    return run
