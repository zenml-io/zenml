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
from typing import TYPE_CHECKING, Dict, List, Optional

from zenml.client import Client
from zenml.enums import ExecutionStatus, MetadataResourceTypes
from zenml.models import (
    PipelineRunResponse,
    PipelineRunUpdate,
    RunMetadataResource,
    StepRunResponse,
    StepRunUpdate,
)
from zenml.utils.time_utils import utc_now

if TYPE_CHECKING:
    from uuid import UUID

    from zenml.metadata.metadata_types import MetadataType


def publish_successful_step_run(
    step_run_id: "UUID", output_artifact_ids: Dict[str, List["UUID"]]
) -> "StepRunResponse":
    """Publishes a successful step run.

    Args:
        step_run_id: The ID of the step run to update.
        output_artifact_ids: The output artifact IDs for the step run.

    Returns:
        The updated step run.
    """
    return Client().zen_store.update_run_step(
        step_run_id=step_run_id,
        step_run_update=StepRunUpdate(
            status=ExecutionStatus.COMPLETED,
            end_time=utc_now(),
            outputs=output_artifact_ids,
        ),
    )


def publish_step_run_status_update(
    step_run_id: "UUID",
    status: "ExecutionStatus",
    end_time: Optional[datetime] = None,
) -> "StepRunResponse":
    """Publishes a step run update.

    Args:
        step_run_id: ID of the step run.
        status: New status of the step run.
        end_time: New end time of the step run.

    Returns:
        The updated step run.

    Raises:
        ValueError: If the end time is set for a non-finished step run.
    """
    from zenml.client import Client

    if end_time is not None and not status.is_finished:
        raise ValueError("End time cannot be set for a non-finished step run.")

    step_run = Client().zen_store.update_run_step(
        step_run_id=step_run_id,
        step_run_update=StepRunUpdate(
            status=status,
            end_time=end_time,
        ),
    )

    return step_run


def publish_failed_step_run(step_run_id: "UUID") -> "StepRunResponse":
    """Publishes a failed step run.

    Args:
        step_run_id: The ID of the step run to update.

    Returns:
        The updated step run.
    """
    return publish_step_run_status_update(
        step_run_id=step_run_id,
        status=ExecutionStatus.FAILED,
        end_time=utc_now(),
    )


def publish_failed_pipeline_run(
    pipeline_run_id: "UUID",
) -> "PipelineRunResponse":
    """Publishes a failed pipeline run.

    Args:
        pipeline_run_id: The ID of the pipeline run to update.

    Returns:
        The updated pipeline run.
    """
    return Client().zen_store.update_run(
        run_id=pipeline_run_id,
        run_update=PipelineRunUpdate(
            status=ExecutionStatus.FAILED,
            end_time=utc_now(),
        ),
    )


def publish_pipeline_run_status_update(
    pipeline_run_id: "UUID",
    status: ExecutionStatus,
    end_time: Optional[datetime] = None,
) -> "PipelineRunResponse":
    """Publishes a pipeline run status update.

    Args:
        pipeline_run_id: The ID of the pipeline run to update.
        status: The new status for the pipeline run.
        end_time: The end time for the pipeline run. If None, will be set to current time
            for finished statuses.

    Returns:
        The updated pipeline run.
    """
    if end_time is None and status.is_finished:
        end_time = utc_now()

    return Client().zen_store.update_run(
        run_id=pipeline_run_id,
        run_update=PipelineRunUpdate(
            status=status,
            end_time=end_time,
        ),
    )


def get_pipeline_run_status(
    run_status: ExecutionStatus,
    step_statuses: List[ExecutionStatus],
    num_steps: int,
) -> ExecutionStatus:
    """Gets the pipeline run status for the given step statuses.

    Args:
        run_status: The status of the run.
        step_statuses: The status of steps in this run.
        num_steps: The total amount of steps in this run.

    Returns:
        The run status.
    """
    # STOPPING state
    if run_status == ExecutionStatus.STOPPING:
        if all(status.is_finished for status in step_statuses):
            return ExecutionStatus.STOPPED
        else:
            return ExecutionStatus.STOPPING

    # If there is a stopped step, the run is stopped or stopping
    if ExecutionStatus.STOPPED in step_statuses:
        if all(status.is_finished for status in step_statuses):
            return ExecutionStatus.STOPPED
        else:
            return ExecutionStatus.STOPPING

    # Otherwise, if there is a failed step, the run is failed
    elif (
        ExecutionStatus.FAILED in step_statuses
        or run_status == ExecutionStatus.FAILED
    ):
        return ExecutionStatus.FAILED

    # If there is a running step, the run is running
    elif (
        ExecutionStatus.RUNNING in step_statuses
        or ExecutionStatus.RETRYING in step_statuses
    ):
        return ExecutionStatus.RUNNING

    # If there are less steps than the total number of steps, it is running
    elif len(step_statuses) < num_steps:
        return ExecutionStatus.RUNNING

    # Any other state is completed
    else:
        return ExecutionStatus.COMPLETED


def publish_pipeline_run_metadata(
    pipeline_run_id: "UUID",
    pipeline_run_metadata: Dict["UUID", Dict[str, "MetadataType"]],
) -> None:
    """Publishes the given pipeline run metadata.

    Args:
        pipeline_run_id: The ID of the pipeline run.
        pipeline_run_metadata: A dictionary mapping stack component IDs to the
            metadata they created.
    """
    client = Client()
    for stack_component_id, metadata in pipeline_run_metadata.items():
        client.create_run_metadata(
            metadata=metadata,
            resources=[
                RunMetadataResource(
                    id=pipeline_run_id, type=MetadataResourceTypes.PIPELINE_RUN
                )
            ],
            stack_component_id=stack_component_id,
        )


def publish_step_run_metadata(
    step_run_id: "UUID",
    step_run_metadata: Dict["UUID", Dict[str, "MetadataType"]],
) -> None:
    """Publishes the given step run metadata.

    Args:
        step_run_id: The ID of the step run.
        step_run_metadata: A dictionary mapping stack component IDs to the
            metadata they created.
    """
    client = Client()
    for stack_component_id, metadata in step_run_metadata.items():
        client.create_run_metadata(
            metadata=metadata,
            resources=[
                RunMetadataResource(
                    id=step_run_id, type=MetadataResourceTypes.STEP_RUN
                )
            ],
            stack_component_id=stack_component_id,
        )


def publish_schedule_metadata(
    schedule_id: "UUID",
    schedule_metadata: Dict["UUID", Dict[str, "MetadataType"]],
) -> None:
    """Publishes the given schedule metadata.

    Args:
        schedule_id: The ID of the schedule.
        schedule_metadata: A dictionary mapping stack component IDs to the
            metadata they created.
    """
    client = Client()
    for stack_component_id, metadata in schedule_metadata.items():
        client.create_run_metadata(
            metadata=metadata,
            resources=[
                RunMetadataResource(
                    id=schedule_id, type=MetadataResourceTypes.SCHEDULE
                )
            ],
            stack_component_id=stack_component_id,
        )
