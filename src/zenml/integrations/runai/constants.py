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

from zenml.enums import DeploymentStatus, ExecutionStatus

# Workload name constraints
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


# Mapping from Run:AI status to ZenML ExecutionStatus
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

# Sets for quick status classification
_TERMINAL_STATUSES = frozenset(
    {
        RunAIWorkloadStatus.SUCCEEDED,
        RunAIWorkloadStatus.COMPLETED,
        RunAIWorkloadStatus.SUCCESS,
        RunAIWorkloadStatus.FAILED,
        RunAIWorkloadStatus.ERROR,
        RunAIWorkloadStatus.STOPPED,
    }
)

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


def is_terminal_status(status: str) -> bool:
    """Check if a Run:AI status is terminal (workload finished).

    Args:
        status: The Run:AI workload status string.

    Returns:
        True if the status indicates the workload has finished.
    """
    try:
        return RunAIWorkloadStatus(status.lower()) in _TERMINAL_STATUSES
    except ValueError:
        return False


def is_success_status(status: str) -> bool:
    """Check if a Run:AI status indicates success.

    Args:
        status: The Run:AI workload status string.

    Returns:
        True if the status indicates successful completion.
    """
    try:
        return RunAIWorkloadStatus(status.lower()) in _SUCCESS_STATUSES
    except ValueError:
        return False


def is_failure_status(status: str) -> bool:
    """Check if a Run:AI status indicates failure.

    Args:
        status: The Run:AI workload status string.

    Returns:
        True if the status indicates failure.
    """
    try:
        return RunAIWorkloadStatus(status.lower()) in _FAILURE_STATUSES
    except ValueError:
        return False


def map_runai_status_to_execution_status(runai_status: str) -> ExecutionStatus:
    """Maps Run:AI workload status to ZenML ExecutionStatus.

    Args:
        runai_status: The Run:AI workload status string.

    Returns:
        The corresponding ZenML ExecutionStatus.
    """
    if not runai_status:
        return ExecutionStatus.RUNNING

    try:
        status_enum = RunAIWorkloadStatus(runai_status.lower())
        return RUNAI_STATUS_TO_EXECUTION_STATUS.get(
            status_enum, ExecutionStatus.RUNNING
        )
    except ValueError:
        return ExecutionStatus.RUNNING


class RunAIInferenceStatus(str, Enum):
    """Run:AI inference workload status values."""

    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING = "running"
    FAILED = "failed"
    ERROR = "error"
    STOPPED = "stopped"
    DEGRADED = "degraded"


RUNAI_INFERENCE_STATUS_TO_DEPLOYMENT_STATUS = {
    RunAIInferenceStatus.PENDING: DeploymentStatus.PENDING,
    RunAIInferenceStatus.INITIALIZING: DeploymentStatus.PENDING,
    RunAIInferenceStatus.RUNNING: DeploymentStatus.RUNNING,
    RunAIInferenceStatus.FAILED: DeploymentStatus.ERROR,
    RunAIInferenceStatus.ERROR: DeploymentStatus.ERROR,
    RunAIInferenceStatus.STOPPED: DeploymentStatus.ABSENT,
    RunAIInferenceStatus.DEGRADED: DeploymentStatus.ERROR,
}


def map_runai_inference_status_to_deployment_status(
    runai_status: str,
) -> DeploymentStatus:
    """Maps Run:AI inference workload status to ZenML DeploymentStatus.

    Args:
        runai_status: The Run:AI inference workload status string.

    Returns:
        The corresponding ZenML DeploymentStatus.
    """
    if not runai_status:
        return DeploymentStatus.UNKNOWN

    try:
        status_enum = RunAIInferenceStatus(runai_status.lower())
        return RUNAI_INFERENCE_STATUS_TO_DEPLOYMENT_STATUS.get(
            status_enum, DeploymentStatus.UNKNOWN
        )
    except ValueError:
        return DeploymentStatus.UNKNOWN
