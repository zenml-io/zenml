# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
"""Implementation of the ZenML GCP VM orchestrator."""

import os
import re
import sys
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Type, cast

import google.cloud.logging
from google.api_core.extended_operation import ExtendedOperation
from google.cloud import compute_v1

from zenml.enums import VMState
from zenml.integrations.gcp import GCP_VM_ORCHESTRATOR_FLAVOR
from zenml.integrations.gcp.flavors.gcp_vm_orchestrator_flavor import (
    GCPVMOrchestratorConfig,
    GCPVMOrchestratorSettings,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsMixin,
)
from zenml.logger import get_logger
from zenml.orchestrators.vm_orchestrator.base_vm_orchestrator import (
    BaseVMOrchestrator,
    VMInstanceView,
)

if TYPE_CHECKING:
    from google.auth.credentials import Credentials

    from zenml.config.base_settings import BaseSettings
    from zenml.config.pipeline_deployment import PipelineDeployment

logger = get_logger(__name__)


class GCPVMOrchestrator(BaseVMOrchestrator, GoogleCredentialsMixin):
    """GCP VM orchestrator implementation."""

    # Class Configuration
    FLAVOR: ClassVar[str] = GCP_VM_ORCHESTRATOR_FLAVOR

    @property
    def config(self) -> GCPVMOrchestratorConfig:
        """Returns the `VertexOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(GCPVMOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """settings class for the GCP VM orchestrator.

        Returns:
            The settings class.
        """
        return GCPVMOrchestratorSettings

    @staticmethod
    def wait_for_extended_operation(
        operation: ExtendedOperation,
        verbose_name: str = "operation",
        timeout: int = 300,
    ) -> Any:
        """Wait for extended GCP operation.

        # noqa: DAR401

        This method will wait for the extended (long-running) operation to
        complete. If the operation is successful, it will return its result.
        If the operation ends with an error, an exception will be raised.
        If there were any warnings during the execution of the operation
        they will be printed to sys.stderr.

        Args:
            operation: a long-running operation you want to wait on.
            verbose_name: (optional) a more verbose name of the operation,
                used only during error and warning reporting.
            timeout: how long (in seconds) to wait for operation to finish.
                If None, wait indefinitely.

        Returns:
            Whatever the operation.result() returns.
        """
        result = operation.result(timeout=timeout)

        if operation.error_code:
            logger.error(
                f"Error during {verbose_name}: [Code: {operation.error_code}]: {operation.error_message}",
                file=sys.stderr,
                flush=True,
            )
            logger.error(
                f"Operation ID: {operation.name}", file=sys.stderr, flush=True
            )
            raise operation.exception() or RuntimeError(
                operation.error_message
            )

        if operation.warnings:
            logger.warning(
                f"Warnings during {verbose_name}:\n",
                file=sys.stderr,
                flush=True,
            )
            for warning in operation.warnings:
                logger.warning(
                    f" - {warning.code}: {warning.message}",
                    file=sys.stderr,
                    flush=True,
                )

        return result

    @staticmethod
    def sanitize_gcp_vm_name(bad_name: str) -> str:
        """Get a good name from a bad name.

        Args:
            bad_name: Original name of VM.

        Returns:
            A good name.
        """
        return bad_name.replace("_", "-").lower()

    @staticmethod
    def disk_from_image(
        disk_type: str,
        disk_size_gb: int,
        boot: bool,
        source_image: str,
        auto_delete: bool = True,
    ) -> compute_v1.AttachedDisk:
        """Create an AttachedDisk object to be used in VM instance creation.

        Uses an image as the source for the new disk.

        Args:
            disk_type: the type of disk you want to create. This value uses the following format:
                "zones/{zone}/diskTypes/(pd-standard|pd-ssd|pd-balanced|pd-extreme)".
                For example: "zones/us-west3-b/diskTypes/pd-ssd"
            disk_size_gb: size of the new disk in gigabytes
            boot: boolean flag indicating whether this disk should be used as a boot disk of an instance
            source_image: source image to use when creating this disk. You must have read access to this disk. This can be one
                of the publicly available images or an image from one of your projects.
                This value uses the following format: "projects/{project_name}/global/images/{image_name}"
            auto_delete: boolean flag indicating whether this disk should be deleted with the VM that uses it

        Returns:
            AttachedDisk object configured to be created using the specified image.
        """
        boot_disk = compute_v1.AttachedDisk()
        initialize_params = compute_v1.AttachedDiskInitializeParams()
        initialize_params.source_image = source_image
        initialize_params.disk_size_gb = disk_size_gb
        initialize_params.disk_type = disk_type
        boot_disk.initialize_params = initialize_params
        # Remember to set auto_delete to True if you want the disk to be deleted when you delete
        # your VM instance.
        boot_disk.auto_delete = auto_delete
        boot_disk.boot = boot
        return boot_disk

    def _get_credentials(self) -> "Credentials":
        """Get credentials based on supplied authentication info.

        Returns:
            Credentials: Google cloud credentials.
        """
        credentials, project_id = self._get_authentication()
        if self.config.project_id != project_id:
            logger.warning(
                "The orchestrator is configured to run on project: "
                f"{self.config.project_id} but the service account credentials file "
                f"{self.service_account_path} seems to be for project {project_id}. "
                "Ignoring service account project value and using configured value "
                f"{self.config.project_id}..)"
            )
        return credentials

    def _get_instances_client(self) -> compute_v1.InstancesClient:
        """Returns google instances client.

        Returns:
            a `compute_v1.InstancesClient` object from the google internal lib.
        """
        credentials = self._get_credentials()
        return compute_v1.InstancesClient(credentials=credentials)

    def _get_logging_client(self) -> compute_v1.InstancesClient:
        """Returns a google logging client.

        Returns:
            a `google.cloud.logging.Client` object from the google internal lib.
        """
        credentials = self._get_credentials()
        return google.cloud.logging.Client(credentials=credentials)

    def _get_images_client(self) -> compute_v1.InstancesClient:
        """Returns google images client.

        Returns:
            a `compute_v1.ImagesClient` object from the google internal lib.
        """
        credentials = self._get_credentials()
        return compute_v1.ImagesClient(credentials=credentials)

    def delete_instance(
        self, project_id: str, zone: str, machine_name: str
    ) -> None:
        """Send an instance deletion request to the Compute Engine API and wait for it to complete.

        Args:
            project_id: project ID or project number of the Cloud project you want to use.
            zone: name of the zone you want to use. For example: “us-west3-b”
            machine_name: name of the machine you want to delete.
        """
        instance_client = compute_v1.InstancesClient()

        logger.info(f"Deleting {machine_name} from {zone}...")
        operation = instance_client.delete(
            project=project_id, zone=zone, instance=machine_name
        )
        GCPVMOrchestrator.wait_for_extended_operation(
            operation, "instance deletion"
        )
        logger.info(f"Instance {machine_name} deleted.")

    def get_image_from_family(
        self, project: str, family: str
    ) -> compute_v1.Image:
        """Retrieve the newest image that is part of a given family in a project.

        Args:
            project: project ID or project number of the Cloud project you want to get image from.
            family: name of the image family you want to get image from.

        Returns:
            An Image object.
        """
        image_client = self._get_images_client()
        # List of public operating system (OS) images: https://cloud.google.com/compute/docs/images/os-details
        newest_image = image_client.get_from_family(
            project=project, family=family
        )
        return newest_image

    def get_instance_name(self, deployment: "PipelineDeployment") -> str:
        """From pipeline deployment, get name of launched instance.

        Args:
            deployment: Deployment of the pipeline.

        Returns:
            Name of the instance.
        """
        return GCPVMOrchestrator.sanitize_gcp_vm_name(
            "zenml-" + str(deployment.run_name)
        )

    def launch_instance(
        self,
        deployment: "PipelineDeployment",
        image_name: str,
        command: str,
        arguments: str,
    ) -> VMInstanceView:
        """Send an instance creation request to the Compute Engine API and wait for it to complete.

        Args:
            deployment: Deployment of the pipeline.
            image_name: Name of image to be run on VM startup.
            command: Command to be run on VM startup.
            arguments: Arguments to be added to command on VM startup.

        Returns:
            A `VMInstanceView` with metadata of launched VM.
        """
        # Get settings
        settings = cast(
            Optional[GCPVMOrchestratorSettings],
            self.get_settings(deployment) or GCPVMOrchestratorSettings(),
        )

        instance_client = self._get_instances_client()

        # Get the c_params
        c_params = " ".join(command + arguments)

        instance_name = self.get_instance_name(deployment)

        image = self.get_image_from_family(
            "gce-uefi-images", family="cos-69-lts"
        )

        disk = GCPVMOrchestrator.disk_from_image(
            f"zones/{self.config.zone}/diskTypes/pd-ssd",
            disk_size_gb=self.config.disk_size_gb,
            boot=True,
            source_image=f"projects/gce-uefi-images/global/images/{image.name}",
            auto_delete=True,
        )

        # Use the network interface provided in the network_link argument.
        network_interface = compute_v1.NetworkInterface()
        network_interface.name = self.config.network_link
        if self.config.subnetwork_link:
            network_interface.subnetwork = self.config.subnetwork_link

        if self.config.internal_ip:
            network_interface.network_i_p = self.config.internal_ip

        # Always allow external access
        access = compute_v1.AccessConfig()
        access.type_ = compute_v1.AccessConfig.Type.ONE_TO_ONE_NAT.name
        access.name = "External NAT"
        access.network_tier = access.NetworkTier.PREMIUM.name
        if self.config.external_ipv4:
            access.nat_i_p = self.config.external_ipv4
        network_interface.access_configs = [access]

        # Collect information into the Instance object.
        instance = compute_v1.Instance()
        instance.name = instance_name
        instance.disks = [disk]
        if re.match(
            r"^zones/[a-z\d\-]+/machineTypes/[a-z\d\-]+$",
            settings.machine_type,
        ):
            instance.machine_type = settings.machine_type
        else:
            instance.machine_type = f"zones/{self.config.zone}/machineTypes/{settings.machine_type}"

        if settings.accelerator_types:
            # First, check passed in settings and resolve counts.
            accelerator_dict = {}
            for accelerator_type in settings.accelerator_types:
                if accelerator_type not in accelerator_dict:
                    accelerator_dict[accelerator_type] = 0
                accelerator_dict[accelerator_type] += 1

            # Second, create list of `compute_v1.AcceleratorConfig` instances.
            accelerators = []
            for x, y in accelerator_dict.items():
                accelerators.append(
                    compute_v1.AcceleratorConfig(
                        accelerator_type=f"projects/{self.config.project_id}"
                        f"/zones/{self.config.zone}"
                        f"/acceleratorTypes/{x}",
                        accelerator_count=y,
                    )
                )
            instance.guest_accelerators = accelerators

        instance.network_interfaces = [network_interface]

        with open(
            os.path.join(os.path.dirname(__file__), "startup-script.sh"), "r"
        ) as f:
            startup_script = f.read()

        # add metadata
        instance.metadata.items = [
            {"key": "startup-script", "value": startup_script},
            {
                "key": "image_name",
                "value": image_name,
            },
            {
                "key": "container_params",
                "value": c_params,
            },
        ]

        # Allow the instance to access cloud storage and logging.
        instance.service_accounts = [
            {
                "email": "default",
                "scopes": [
                    "https://www.googleapis.com/auth/cloud-platform",
                    "https://www.googleapis.com/auth/sqlservice.admin",
                ],
            }
        ]

        if settings.preemptible:
            # Set the preemptible setting
            instance.scheduling = compute_v1.Scheduling()
            instance.scheduling.preemptible = True

        if self.config.custom_hostname is not None:
            # Set the custom hostname for the instance
            instance.hostname = self.config.custom_hostname

        if self.config.delete_protection:
            # Set the delete protection bit
            instance.deletion_protection = True

        # Prepare the request to insert an instance.
        request = compute_v1.InsertInstanceRequest()
        request.zone = self.config.zone
        request.project = self.config.project_id
        request.instance_resource = instance

        # Wait for the create operation to complete.
        logger.info(
            f"Creating the {instance_name} instance in {self.config.zone}..."
        )

        operation = instance_client.insert(request=request)

        GCPVMOrchestrator.wait_for_extended_operation(
            operation, "instance creation"
        )

        return self.get_instance(deployment)

    def get_instance(self, deployment: "PipelineDeployment") -> VMInstanceView:
        """Returns the launched instance.

        Args:
            deployment: Deployment of the pipeline.

        Returns:
            A `VMInstanceView` with metadata of launched VM.
        """
        instance_name = self.get_instance_name(deployment)
        instance_client = compute_v1.InstancesClient()
        gcp_instance = instance_client.get(
            project=self.config.project_id,
            zone=self.config.zone,
            instance=instance_name,
        )

        return VMInstanceView(
            id=gcp_instance.id,
            name=gcp_instance.name,
            status=VMState.RUNNING
            if gcp_instance.status == "RUNNING"
            else VMState.STOPPED,
        )

    def get_logs_url(self, deployment: "PipelineDeployment") -> Optional[str]:
        """Returns the logs url if instance is running.

        Args:
            deployment: Deployment of the pipeline.

        Returns:
            A string URL.
        """

    def stream_logs(
        self,
        deployment: "PipelineDeployment",
        seconds_before: int,
    ) -> None:
        """Streams logs to the logger.

        Args:
            deployment: Deployment of the pipeline.client.
            seconds_before: How many seconds before to stream logs from.
        """
        client = self._get_logging_client()
        time_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        before = datetime.utcnow() - timedelta(seconds=seconds_before)
        filter_str = (
            f'logName="projects/{self.config.project_id}/logs/gcplogs-docker-driver"'
            f' AND timestamp>="{before.strftime(time_format)}"'
        )
        # query and print all matching logs
        for entry in client.list_entries(filter_=filter_str):  # API call(s)
            if "data" in entry.payload:
                logger.info(entry.payload["data"])
