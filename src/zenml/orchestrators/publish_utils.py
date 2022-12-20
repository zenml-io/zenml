#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Utilities to publish pipeline and step runs."""

from datetime import datetime
from typing import TYPE_CHECKING, Dict, List

from zenml.client import Client
from zenml.enums import ExecutionStatus
from zenml.models.pipeline_run_models import (
    PipelineRunResponseModel,
    PipelineRunUpdateModel,
)
from zenml.models.step_run_models import (
    StepRunResponseModel,
    StepRunUpdateModel,
)

if TYPE_CHECKING:
    from uuid import UUID

    from zenml.models.artifact_models import ArtifactRequestModel


def publish_output_artifacts(
    output_artifacts: Dict[str, "ArtifactRequestModel"]
) -> Dict[str, "UUID"]:
    """Publishes the given output artifacts.

    Args:
        output_artifacts: The output artifacts to register.

    Returns:
        The IDs of the registered output artifacts.
    """
    output_artifact_ids = {}
    client = Client()
    for name, artifact_model in output_artifacts.items():
        artifact_response = client.zen_store.create_artifact(artifact_model)
        output_artifact_ids[name] = artifact_response.id
    return output_artifact_ids


def publish_successful_step_run(
    step_run_id: "UUID", output_artifact_ids: Dict[str, "UUID"]
) -> "StepRunResponseModel":
    """Publishes a successful step run.

    Args:
        step_run_id: The ID of the step run to update.
        output_artifact_ids: The output artifact IDs for the step run.

    Returns:
        The updated step run.
    """
    return Client().zen_store.update_run_step(
        step_run_id=step_run_id,
        step_run_update=StepRunUpdateModel(
            status=ExecutionStatus.COMPLETED,
            end_time=datetime.utcnow(),
            output_artifacts=output_artifact_ids,
        ),
    )


def publish_failed_step_run(step_run_id: "UUID") -> "StepRunResponseModel":
    """Publishes a failed step run.

    Args:
        step_run_id: The ID of the step run to update.

    Returns:
        The updated step run.
    """
    return Client().zen_store.update_run_step(
        step_run_id=step_run_id,
        step_run_update=StepRunUpdateModel(
            status=ExecutionStatus.FAILED,
            end_time=datetime.utcnow(),
        ),
    )


def publish_failed_pipeline_run(
    pipeline_run_id: "UUID",
) -> "PipelineRunResponseModel":
    """Publishes a failed pipeline run.

    Args:
        pipeline_run_id: The ID of the pipeline run to update.

    Returns:
        The updated pipeline run.
    """
    return Client().zen_store.update_run(
        run_id=pipeline_run_id,
        run_update=PipelineRunUpdateModel(
            status=ExecutionStatus.FAILED,
            end_time=datetime.utcnow(),
        ),
    )


def get_pipeline_run_status(
    step_statuses: List[ExecutionStatus], num_steps: int
) -> ExecutionStatus:
    """Gets the pipeline run status for the given step statuses.

    Args:
        step_statuses: The status of steps in this run.
        num_steps: The total amount of steps in this run.

    Returns:
        The run status.
    """
    if ExecutionStatus.FAILED in step_statuses:
        return ExecutionStatus.FAILED
    if (
        ExecutionStatus.RUNNING in step_statuses
        or len(step_statuses) < num_steps
    ):
        return ExecutionStatus.RUNNING

    return ExecutionStatus.COMPLETED


def update_pipeline_run_status(pipeline_run: PipelineRunResponseModel) -> None:
    """Updates the status of the current pipeline run.

    Args:
        pipeline_run: The model of the current pipeline run.
    """
    assert pipeline_run.num_steps is not None
    steps_in_current_run = Client().zen_store.list_run_steps(
        run_id=pipeline_run.id
    )
    new_status = get_pipeline_run_status(
        step_statuses=[step_run.status for step_run in steps_in_current_run],
        num_steps=pipeline_run.num_steps,
    )

    if new_status != pipeline_run.status:
        run_update = PipelineRunUpdateModel(status=new_status)
        if new_status in {ExecutionStatus.COMPLETED, ExecutionStatus.FAILED}:
            run_update.end_time = datetime.utcnow()

        Client().zen_store.update_run(
            run_id=pipeline_run.id, run_update=run_update
        )
