#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Utility functions for the AWS integration."""

from typing import Dict

from zenml.enums import ExecutionStatus


def validate_command_step_environment(
    environment: Dict[str, str],
    size_limit: int,
) -> None:
    """Validate environment variable sizes for a SageMaker command step.

    Args:
        environment: The environment variables to validate.
        size_limit: The maximum allowed length of an environment variable
            value.

    Raises:
        RuntimeError: If an environment variable value exceeds the size limit.
    """
    oversized = {
        key: len(value)
        for key, value in environment.items()
        if len(value) > size_limit
    }
    if oversized:
        details = ", ".join(
            f"`{key}` ({length} characters)"
            for key, length in sorted(oversized.items())
        )
        raise RuntimeError(
            "Unable to run command step. The following environment variables "
            f"exceed the maximum length of {size_limit} characters allowed by "
            f"SageMaker: {details}."
        )


def convert_training_job_status(status: str) -> ExecutionStatus:
    """Converts a training job status to an execution status.

    Args:
        status: The training job status.

    Raises:
        ValueError: If the training job status is unknown.

    Returns:
        The execution status.
    """
    # https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_DescribeTrainingJob.html#sagemaker-DescribeTrainingJob-response-TrainingJobStatus
    if status == "InProgress":
        return ExecutionStatus.RUNNING
    elif status == "Stopping":
        return ExecutionStatus.STOPPING
    elif status == "Completed":
        return ExecutionStatus.COMPLETED
    elif status == "Failed":
        return ExecutionStatus.FAILED
    elif status == "Stopped":
        return ExecutionStatus.STOPPED
    else:
        raise ValueError(f"Unknown training job status: {status}")


def convert_processing_job_status(status: str) -> ExecutionStatus:
    """Converts a processing job status to an execution status.

    Args:
        status: The processing job status.

    Raises:
        ValueError: If the processing job status is unknown.

    Returns:
        The execution status.
    """
    # https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_DescribeProcessingJob.html#sagemaker-DescribeProcessingJob-response-ProcessingJobStatus
    if status == "InProgress":
        return ExecutionStatus.RUNNING
    elif status == "Stopping":
        return ExecutionStatus.STOPPING
    elif status == "Completed":
        return ExecutionStatus.COMPLETED
    elif status == "Failed":
        return ExecutionStatus.FAILED
    else:
        raise ValueError(f"Unknown processing job status: {status}")
