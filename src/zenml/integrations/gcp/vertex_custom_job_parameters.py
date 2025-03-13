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

from typing import Optional

from pydantic import BaseModel


class VertexCustomJobParameters(BaseModel):
    """Settings for the Vertex custom job parameters.

    Attributes:
        accelerator_type: Defines which accelerator (GPU, TPU) is used for the
            job. Check out out this table to see which accelerator
            type and count are compatible with your chosen machine type:
            https://cloud.google.com/vertex-ai/docs/training/configure-compute#gpu-compatibility-table.
        accelerator_count: Defines number of accelerators to be used for the
            job. Check out out this table to see which accelerator
            type and count are compatible with your chosen machine type:
            https://cloud.google.com/vertex-ai/docs/training/configure-compute#gpu-compatibility-table.
        machine_type: Machine type specified here
            https://cloud.google.com/vertex-ai/docs/training/configure-compute#machine-types.
        boot_disk_size_gb: Size of the boot disk in GB. (Default: 100)
            https://cloud.google.com/vertex-ai/docs/training/configure-compute#boot_disk_options
        boot_disk_type: Type of the boot disk. (Default: pd-ssd)
            https://cloud.google.com/vertex-ai/docs/training/configure-compute#boot_disk_options
        persistent_resource_id: The ID of the persistent resource to use for the job.
            https://cloud.google.com/vertex-ai/docs/training/persistent-resource-overview
        service_account: Specifies the service account to be used.
    """

    accelerator_type: Optional[str] = None
    accelerator_count: int = 0
    machine_type: str = "n1-standard-4"
    boot_disk_size_gb: int = 100
    boot_disk_type: str = "pd-ssd"
    persistent_resource_id: Optional[str] = None
    service_account: Optional[str] = None
