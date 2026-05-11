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
"""Run:AI integration constants and status mappings."""

from enum import Enum
from typing import Optional

from zenml.enums import ExecutionStatus

MAX_WORKLOAD_NAME_LENGTH = 50


class RunAIWorkloadStatus(str, Enum):
    """Run:AI workload status values."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    COMPLETED = "completed"
    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"
    STOPPED = "stopped"
    STOPPING = "stopping"


RUNAI_STATUS_TO_EXECUTION_STATUS = {
    RunAIWorkloadStatus.PENDING: ExecutionStatus.INITIALIZING,
    RunAIWorkloadStatus.RUNNING: ExecutionStatus.RUNNING,
    RunAIWorkloadStatus.SUCCEEDED: ExecutionStatus.COMPLETED,
    RunAIWorkloadStatus.COMPLETED: ExecutionStatus.COMPLETED,
    RunAIWorkloadStatus.SUCCESS: ExecutionStatus.COMPLETED,
    RunAIWorkloadStatus.FAILED: ExecutionStatus.FAILED,
    RunAIWorkloadStatus.ERROR: ExecutionStatus.FAILED,
    RunAIWorkloadStatus.STOPPED: ExecutionStatus.FAILED,
    RunAIWorkloadStatus.STOPPING: ExecutionStatus.STOPPING,
}

_SUCCESS_STATUSES = frozenset(
    {
        RunAIWorkloadStatus.SUCCEEDED,
        RunAIWorkloadStatus.COMPLETED,
        RunAIWorkloadStatus.SUCCESS,
    }
)

_FAILURE_STATUSES = frozenset(
    {
        RunAIWorkloadStatus.FAILED,
        RunAIWorkloadStatus.ERROR,
        RunAIWorkloadStatus.STOPPED,
    }
)

_PENDING_STATUSES = frozenset({RunAIWorkloadStatus.PENDING})


def _parse_runai_status(status: str) -> Optional[RunAIWorkloadStatus]:
    """Parse a Run:AI status string into a known workload status."""
    if not status:
        return None

    try:
        return RunAIWorkloadStatus(status.lower())
    except ValueError:
        return None


def is_success_status(status: str) -> bool:
    """Check if a Run:AI status indicates success.

    Args:
        status: The Run:AI workload status string.

    Returns:
        True if the status indicates successful completion.
    """
    parsed_status = _parse_runai_status(status)
    return parsed_status in _SUCCESS_STATUSES


def is_failure_status(status: str) -> bool:
    """Check if a Run:AI status indicates failure.

    Args:
        status: The Run:AI workload status string.

    Returns:
        True if the status indicates failure.
    """
    parsed_status = _parse_runai_status(status)
    return parsed_status in _FAILURE_STATUSES


def is_pending_status(status: str) -> bool:
    """Check if a Run:AI status indicates pending scheduling.

    Args:
        status: The Run:AI workload status string.

    Returns:
        True if the status indicates the workload is pending.
    """
    parsed_status = _parse_runai_status(status)
    return parsed_status in _PENDING_STATUSES


def map_runai_status_to_execution_status(runai_status: str) -> ExecutionStatus:
    """Maps Run:AI workload status to ZenML ExecutionStatus.

    Args:
        runai_status: The Run:AI workload status string.

    Returns:
        The corresponding ZenML ExecutionStatus.
    """
    status_enum = _parse_runai_status(runai_status)
    if status_enum is not None:
        return RUNAI_STATUS_TO_EXECUTION_STATUS.get(
            status_enum, ExecutionStatus.RUNNING
        )

    return ExecutionStatus.RUNNING
