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
"""Refreshing the status of a pipeline run."""

from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.models import PipelineRunResponse, PipelineRunUpdate
from zenml.orchestrators.base_orchestrator import BaseOrchestrator


def refresh_run_status(run: PipelineRunResponse) -> None:
    """Function to refresh the status of a pipeline.

    Args:
        run: The run to refresh.

    Raises:
        ValueError: If the stack of the run response is None.
    """
    # Check the stack
    if run.stack is None:
        raise ValueError(
            "The pipeline run response does not have a stack. It may have been "
            "deleted or you might not have access to it."
        )

    # Create the orchestrator instance
    component_model = run.stack.components[StackComponentType.ORCHESTRATOR][0]
    orchestrator = BaseOrchestrator.from_model(component_model=component_model)

    # Fetch the status
    status = orchestrator.fetch_status(run=run)

    # If it is different from the current status, update it
    if status != run.status:
        client = Client()
        client.zen_store.update_run(
            run_id=run.id,
            run_update=PipelineRunUpdate(status=status),
        )
