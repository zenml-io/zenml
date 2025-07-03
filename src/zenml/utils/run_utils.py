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

from typing import cast

from zenml.enums import ExecutionStatus
from zenml.exceptions import IllegalOperationError
from zenml.models import PipelineRunResponse


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

    # Create the orchestrator instance
    from zenml.enums import StackComponentType
    from zenml.orchestrators.base_orchestrator import BaseOrchestrator
    from zenml.stack.stack_component import StackComponent

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
