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
"""Vertex custom job parameter model."""

from typing import Dict, List, Optional

from pydantic import BaseModel


class VertexCustomJobParameters(BaseModel):
    """Parameters for a Vertex AI custom job.

    Attributes:
        replica_count: Number of replicas for distributed training. Default is 1
            for non-distributed training.
        machine_type: Machine type for each replica. Default is 'n1-standard-4'.
        accelerator_type: Type of accelerator to use (e.g., 'NVIDIA_TESLA_T4',
            'NVIDIA_TESLA_A100'). Empty string means no accelerator.
        accelerator_count: Number of accelerators of the specified type to use.
            Default is 1. Ignored if accelerator_type is empty.
        boot_disk_type: Boot disk type. Default is 'pd-ssd'.
        boot_disk_size_gb: Boot disk size in GB. Default is 100.
        timeout: Timeout for the custom job in seconds. Default is '604800s' (7 days).
        restart_job_on_worker_restart: Whether to restart the job if a worker
            restarts. Default is False.
        service_account: Service account to use for the job. If not specified,
            the compute engine default service account is used.
        network: Network to use for the job. If not specified, the default network
            is used.
        persistent_resource_id: ID of the persistent resource to use. Default is
            empty string. If specified, the custom job will run on the persistent
            resource.
        display_name: Display name for the custom job.
        tensorboard: Name of the Tensorboard instance to use for the job.
        enable_web_access: Whether to enable web access for the job.
        reserved_ip_ranges: List of reserved IP ranges for the job.
        nfs_mounts: List of NFS mounts for the job.
        base_output_directory: Base output directory for the job.
        labels: Labels to apply to the job.
        env: Environment variables for the job.
        strategy: Execution strategy for the job. Default is 'STANDARD'.
        max_wait_duration: Maximum wait duration for the job. Default is '86400s' (24 hours).
        reservation_affinity_type: Type of reservation affinity.
        reservation_affinity_key: Key for reservation affinity.
        reservation_affinity_values: Values for reservation affinity.
        encryption_spec_key_name: Cloud KMS key name for encryption.
    """

    replica_count: int = 1
    machine_type: str = "n1-standard-4"
    accelerator_type: str = ""
    accelerator_count: int = 1
    boot_disk_type: str = "pd-ssd"
    boot_disk_size_gb: int = 100
    timeout: str = "604800s"
    restart_job_on_worker_restart: bool = False
    service_account: str = ""
    network: str = ""
    persistent_resource_id: str = ""
    display_name: str = ""
    tensorboard: str = ""
    enable_web_access: bool = False
    reserved_ip_ranges: Optional[List[str]] = None
    nfs_mounts: Optional[List[Dict[str, str]]] = None
    base_output_directory: str = ""
    labels: Optional[Dict[str, str]] = None
    env: Optional[List[Dict[str, str]]] = None
    strategy: str = "STANDARD"
    max_wait_duration: str = "86400s"
    reservation_affinity_type: Optional[str] = None
    reservation_affinity_key: Optional[str] = None
    reservation_affinity_values: Optional[List[str]] = None
    encryption_spec_key_name: str = ""
