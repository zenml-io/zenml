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
"""Vertex utilities."""

import time
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from google.api_core.exceptions import ServerError
from google.cloud import aiplatform

from zenml.integrations.gcp.constants import (
    CONNECTION_ERROR_RETRY_LIMIT,
    POLLING_INTERVAL_IN_SECONDS,
    VERTEX_JOB_STATES_COMPLETED,
    VERTEX_JOB_STATES_FAILED,
)
from zenml.integrations.gcp.vertex_custom_job_parameters import (
    VertexCustomJobParameters,
)
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.config.resource_settings import ResourceSettings

logger = get_logger(__name__)


def validate_accelerator_type(accelerator_type: Optional[str] = None) -> None:
    """Validates that the accelerator type is valid.

    Args:
        accelerator_type: The accelerator type to validate.

    Raises:
        ValueError: If the accelerator type is not valid.
    """
    accepted_vals = list(aiplatform.gapic.AcceleratorType.__members__.keys())
    if accelerator_type and accelerator_type.upper() not in accepted_vals:
        raise ValueError(
            f"Accelerator must be one of the following: {accepted_vals}"
        )


def monitor_job(
    job_id: str,
    get_client: Callable[[], aiplatform.gapic.JobServiceClient],
) -> None:
    """Monitors a job until it is completed.

    Args:
        job_id: The ID of the job to monitor.
        get_client: A function that returns an authenticated job service client.

    Raises:
        RuntimeError: If the job fails.
    """
    retry_count = 0
    client = get_client()

    while True:
        time.sleep(POLLING_INTERVAL_IN_SECONDS)
        # Fetch a fresh client in case the credentials have expired
        client = get_client()

        try:
            response = client.get_custom_job(name=job_id)
            retry_count = 0
        except (ConnectionError, ServerError) as err:
            # Retry on connection errors, see also
            # https://github.com/googleapis/google-api-python-client/issues/218
            if retry_count < CONNECTION_ERROR_RETRY_LIMIT:
                retry_count += 1
                logger.warning(
                    f"Error encountered when polling job "
                    f"{job_id}: {err}\nRetrying...",
                )
                continue
            else:
                logger.exception(
                    "Request failed after %s retries.",
                    CONNECTION_ERROR_RETRY_LIMIT,
                )
                raise RuntimeError(
                    f"Request failed after {CONNECTION_ERROR_RETRY_LIMIT} "
                    f"retries: {err}"
                )
        if response.state in VERTEX_JOB_STATES_FAILED:
            err_msg = f"Job `{job_id}` failed: {response}."
            logger.error(err_msg)
            raise RuntimeError(err_msg)
        if response.state in VERTEX_JOB_STATES_COMPLETED:
            break

    logger.info("Job `%s` successful.", job_id)


def build_job_request(
    display_name: str,
    image: str,
    entrypoint_command: List[str],
    custom_job_settings: VertexCustomJobParameters,
    resource_settings: "ResourceSettings",
    environment: Optional[Dict[str, str]] = None,
    labels: Optional[Dict[str, str]] = None,
    encryption_spec_key_name: Optional[str] = None,
    service_account: Optional[str] = None,
    network: Optional[str] = None,
    reserved_ip_ranges: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a job request.

    Args:
        display_name: The display name of the job.
        image: The image URI of the job.
        entrypoint_command: The entrypoint command of the job.
        custom_job_settings: The custom job settings.
        resource_settings: The resource settings.
        environment: The environment variables.
        labels: The labels.
        encryption_spec_key_name: The encryption spec key name.
        service_account: The service account.
        network: The network.
        reserved_ip_ranges: The reserved IP ranges.

    Returns:
        Job request dictionary.
    """
    environment = environment or {}
    labels = labels or {}

    validate_accelerator_type(custom_job_settings.accelerator_type)

    accelerator_count = (
        resource_settings.gpu_count or custom_job_settings.accelerator_count
    )
    return {
        "display_name": display_name,
        "job_spec": {
            "worker_pool_specs": [
                {
                    "machine_spec": {
                        "machine_type": custom_job_settings.machine_type,
                        "accelerator_type": custom_job_settings.accelerator_type,
                        "accelerator_count": accelerator_count
                        if custom_job_settings.accelerator_type
                        else 0,
                    },
                    "replica_count": 1,
                    "container_spec": {
                        "image_uri": image,
                        "command": entrypoint_command,
                        "args": [],
                        "env": [
                            {"name": key, "value": value}
                            for key, value in environment.items()
                        ],
                    },
                    "disk_spec": {
                        "boot_disk_type": custom_job_settings.boot_disk_type,
                        "boot_disk_size_gb": custom_job_settings.boot_disk_size_gb,
                    },
                }
            ],
            "service_account": service_account,
            "network": network,
            "reserved_ip_ranges": (
                reserved_ip_ranges.split(",") if reserved_ip_ranges else []
            ),
            "persistent_resource_id": custom_job_settings.persistent_resource_id,
        },
        "labels": labels,
        "encryption_spec": {"kmsKeyName": encryption_spec_key_name}
        if encryption_spec_key_name
        else {},
    }
