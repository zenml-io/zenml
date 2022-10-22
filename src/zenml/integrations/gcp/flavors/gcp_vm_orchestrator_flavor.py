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
"""VM orchestrator flavor."""

from typing import TYPE_CHECKING, List, Optional, Type

from zenml.config.base_settings import BaseSettings
from zenml.integrations.gcp import GCP_VM_ORCHESTRATOR_FLAVOR
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsConfigMixin,
)
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor

if TYPE_CHECKING:
    from zenml.integrations.gcp.orchestrators import GCPVMOrchestrator


class GCPVMOrchestratorConfig(
    BaseOrchestratorConfig,
    GoogleCredentialsConfigMixin,
):
    """Configuration for the VM orchestrator.

    Attributes:
        project_id: project ID or project number of the Cloud project you want to use.
        zone: name of the zone to create the instance in. For example: "us-west3-b"
        instance_name: name of the new virtual machine (VM) instance.
        disks: a list of compute_v1.AttachedDisk objects describing the disks
            you want to attach to your new instance.
        network_link: name of the network you want the new instance to use.
            For example: "global/networks/default" represents the network
            named "default", which is created automatically for each project.
        subnetwork_link: name of the subnetwork you want the new instance to use.
            This value uses the following format:
            "regions/{region}/subnetworks/{subnetwork_name}"
        internal_ip: internal IP address you want to assign to the new instance.
            By default, a free address from the pool of available internal IP addresses of
            used subnet will be used.
        external_access: boolean flag indicating if the instance should have an external IPv4
            address assigned.
        external_ipv4: external IPv4 address to be assigned to this instance. If you specify
            an external IP address, it must live in the same region as the zone of the instance.
            This setting requires `external_access` to be set to True to work.
        custom_hostname: Custom hostname of the new VM instance.
            Custom hostnames must conform to RFC 1035 requirements for valid hostnames.
        delete_protection: boolean value indicating if the new virtual machine should be
            protected against deletion or not.
        disk_size_gb: int value indicating size of attached disk in GB.
    """

    project_id: str
    zone: str = "us-west3-b"
    network_link: str = "global/networks/default"
    subnetwork_link: Optional[str] = None
    internal_ip: Optional[str] = None
    external_ipv4: Optional[str] = None
    custom_hostname: Optional[str] = None
    delete_protection: bool = False
    disk_size_gb: int = 10

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        This designation is used to determine if the stack component can be
        used with a local ZenML database or if it requires a remote ZenML
        server.

        Returns:
            True if this config is for a remote component, False otherwise.
        """
        return True


class GCPVMOrchestratorSettings(BaseSettings):
    """Settings for the GCP VM Orchestrator.

    Attributes:
        machine_type: machine type of the VM being created. This value uses the
            following format: "zones/{zone}/machineTypes/{type_name}".
            For example: "zones/europe-west3-c/machineTypes/f1-micro"
        accelerator_types: List of Accelerator type from list:
            "NVIDIA_TESLA_A100", "NVIDIA_TESLA_K80",
            "NVIDIA_TESLA_P4", "NVIDIA_TESLA_P100", "NVIDIA_TESLA_T4", "NVIDIA_TESLA_V100",
            "TPU_V2", "TPU_V3", "TPU_V2_POD", "TPU_V3_POD"
            or one of https://cloud.google.com/ai-platform/training/docs/reference/rest/v1/AcceleratorType.
            If multiple of GPUs required, simply pass in more of the same type. E.g. a value of
            ["NVIDIA_TESLA_A100", "NVIDIA_TESLA_A100", "NVIDIA_TESLA_K80"] will attach 2 x
            NVIDIA_TESLA_A100 and 1 x NVIDIA_TESLA_K80 to the VM.
        preemptible: boolean value indicating if the new instance should be preemptible
            or not.
    """

    machine_type: str = "n1-standard-4"
    accelerator_types: Optional[List[str]] = []
    preemptible: bool = True


class GCPVMOrchestratorFlavor(BaseOrchestratorFlavor):
    """VM Orchestrator flavor."""

    @property
    def name(self) -> str:
        """Name of the orchestrator flavor.

        Returns:
            Name of the orchestrator flavor.
        """
        return GCP_VM_ORCHESTRATOR_FLAVOR

    @property
    def config_class(self) -> Type[GCPVMOrchestratorConfig]:
        """Returns GCPVMOrchestratorConfig config class.

        Returns:
                The config class.
        """
        return GCPVMOrchestratorConfig

    @property
    def implementation_class(self) -> Type["GCPVMOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            Implementation class for this flavor.
        """
        from zenml.integrations.gcp.orchestrators import GCPVMOrchestrator

        return GCPVMOrchestrator
