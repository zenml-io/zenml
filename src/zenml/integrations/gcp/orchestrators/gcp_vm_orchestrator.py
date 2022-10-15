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

import os
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    cast,
)

import google.cloud.logging
from google.api_core.extended_operation import ExtendedOperation
from google.cloud import compute_v1

from zenml.integrations.gcp import GCP_VM_ORCHESTRATOR_FLAVOR
from zenml.integrations.gcp.flavors.gcp_vm_orchestrator_flavor import (
    GCPVMOrchestratorConfig,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsMixin,
)
from zenml.logger import get_logger
from zenml.orchestrators.vm_orchestrator.base_vm_orchestrator import (
    BaseVMOrchestrator,
    VMInstanceView,
)

logger = get_logger(__name__)


class GCPVMOrchestrator(BaseVMOrchestrator, GoogleCredentialsMixin):

    # Class Configuration
    FLAVOR: ClassVar[str] = GCP_VM_ORCHESTRATOR_FLAVOR

    @property
    def config(self) -> GCPVMOrchestratorConfig:
        """Returns the `VertexOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(GCPVMOrchestratorConfig, self._config)

    @staticmethod
    def _wait_for_extended_operation(
        cls,
        operation: ExtendedOperation,
        verbose_name: str = "operation",
        timeout: int = 300,
    ) -> Any:
        """
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

        Raises:
            This method will raise the exception received from `operation.exception()`
            or RuntimeError if there is no exception set, but there is an `error_code`
            set for the `operation`.

            In case of an operation taking longer than `timeout` seconds to complete,
            a `concurrent.futures.TimeoutError` will be raised.
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
            raise operation.exception() or RuntimeError(operation.error_message)

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
    def delete_instance(project_id: str, zone: str, machine_name: str) -> None:
        """
        Send an instance deletion request to the Compute Engine API and wait for it to complete.

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
        wait_for_extended_operation(operation, "instance deletion")
        logger.info(f"Instance {machine_name} deleted.")
        return

    @staticmethod
    def sanitize_gcp_vm_name(bad_name: str) -> str:
        """Get a good name from a bad name"""
        return bad_name.replace("_", "-")

    @staticmethod
    def get_image_from_family(project: str, family: str) -> compute_v1.Image:
        """
        Retrieve the newest image that is part of a given family in a project.

        Args:
            project: project ID or project number of the Cloud project you want to get image from.
            family: name of the image family you want to get image from.

        Returns:
            An Image object.
        """
        image_client = compute_v1.ImagesClient()
        # List of public operating system (OS) images: https://cloud.google.com/compute/docs/images/os-details
        newest_image = image_client.get_from_family(
            project=project, family=family
        )
        return newest_image

    @staticmethod
    def disk_from_image(
        disk_type: str,
        disk_size_gb: int,
        boot: bool,
        source_image: str,
        auto_delete: bool = True,
    ) -> compute_v1.AttachedDisk:
        """
        Create an AttachedDisk object to be used in VM instance creation. Uses an image as the
        source for the new disk.

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

    def launch_instance(
        self, image_name: str, command: str, arguments: str
    ) -> VMInstanceView:
        """Send an instance creation request to the Compute Engine API and wait
        for it to complete.

        Args:
            image_name: The docker image to run when VM starts.
            c_params: The params to run the docker image with.
            project_id: project ID or project number of the Cloud project you want to use.
            zone: name of the zone to create the instance in. For example: "us-west3-b"
            instance_name: name of the new virtual machine (VM) instance.
            disks: a list of compute_v1.AttachedDisk objects describing the disks
                you want to attach to your new instance.
            machine_type: machine type of the VM being created. This value uses the
                following format: "zones/{zone}/machineTypes/{type_name}".
                For example: "zones/europe-west3-c/machineTypes/f1-micro"
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
            accelerators: a list of AcceleratorConfig objects describing the accelerators that will
                be attached to the new instance.
            preemptible: boolean value indicating if the new instance should be preemptible
                or not.
            custom_hostname: Custom hostname of the new VM instance.
                Custom hostnames must conform to RFC 1035 requirements for valid hostnames.
            delete_protection: boolean value indicating if the new virtual machine should be
                protected against deletion or not.

        Returns:
            A `VMInstanceView` with metadata of launched VM.
        """
        instance_client = compute_v1.InstancesClient()

        # Get the c_params
        c_params = " ".join(command + arguments)

        image = get_image_from_family("gce-uefi-images", family="cos-69-lts")

        disk = disk_from_image(
            f"zones/{self.zone}/diskTypes/pd-ssd",
            disk_size_gb=10,
            boot=True,
            source_image=f"projects/gce-uefi-images/global/images/{image.name}",
            auto_delete=True,
        )

        # Use the network interface provided in the network_link argument.
        network_interface = compute_v1.NetworkInterface()
        network_interface.name = network_link
        if subnetwork_link:
            network_interface.subnetwork = subnetwork_link

        if internal_ip:
            network_interface.network_i_p = internal_ip

        if external_access:
            access = compute_v1.AccessConfig()
            access.type_ = compute_v1.AccessConfig.Type.ONE_TO_ONE_NAT.name
            access.name = "External NAT"
            access.network_tier = access.NetworkTier.PREMIUM.name
            if external_ipv4:
                access.nat_i_p = external_ipv4
            network_interface.access_configs = [access]

        # Collect information into the Instance object.
        instance = compute_v1.Instance()
        instance.name = sanitize_gcp_vm_name("zenml-" + step.name)
        instance.disks = [disk]
        if re.match(
            r"^zones/[a-z\d\-]+/machineTypes/[a-z\d\-]+$", machine_type
        ):
            instance.machine_type = machine_type
        else:
            instance.machine_type = f"zones/{zone}/machineTypes/{machine_type}"

        if accelerators:
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

        if preemptible:
            # Set the preemptible setting
            instance.scheduling = compute_v1.Scheduling()
            instance.scheduling.preemptible = True

        if custom_hostname is not None:
            # Set the custom hostname for the instance
            instance.hostname = custom_hostname

        if delete_protection:
            # Set the delete protection bit
            instance.deletion_protection = True

        # Prepare the request to insert an instance.
        request = compute_v1.InsertInstanceRequest()
        request.zone = zone
        request.project = project_id
        request.instance_resource = instance

        # Wait for the create operation to complete.
        logger.info(f"Creating the {instance_name} instance in {zone}...")

        operation = instance_client.insert(request=request)

        wait_for_extended_operation(operation, "instance creation")

        return instance_client.get(
            project=project_id, zone=zone, instance=instance_name
        )

    def get_instance(self, **kwargs: Any) -> VMInstanceView:
        """Returns the launched instance"""
        pass

    def get_logs_url(self, **kwargs: Any) -> Optional[str]:
        """Returns the logs url if instance is running."""
        instance_client = compute_v1.InstancesClient()
        return instance_client.get(
            project=project_id, zone=zone, instance=instance_name
        )

    def stream_logs(self, seconds_before: int, **kwargs: Any) -> None:
        """Streams logs onto the logger"""
        client = google.cloud.logging.Client()
        time_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        before = datetime.now(timezone.utc) - timedelta(seconds=seconds_before)
        filter_str = (
            f'logName="projects/{project_id}/logs/gcplogs-docker-driver"'
            f' AND timestamp>="{before.strftime(time_format)}"'
        )
        # query and print all matching logs
        for entry in client.list_entries(filter_=filter_str):  # API call(s)
            logger.info(entry.payload["data"])
