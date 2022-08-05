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

# Minor parts of the `prepare_or_run_pipeline()` method of this file are
# inspired by the kubeflow dag runner implementation of tfx
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, ClassVar, List, Optional

import google.cloud.logging
from google.api_core.extended_operation import ExtendedOperation
from google.cloud import compute_v1
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline

from zenml.integrations.gcp import AWS_VM_ORCHESTRATOR_FLAVOR
from zenml.integrations.gcp.orchestrators.gcp_vm_entrypoint_configuration import (
    RUN_NAME_OPTION,
    AWSVMEntrypointConfiguration,
)
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.repository import Repository
from zenml.utils.docker_utils import get_image_digest
from zenml.utils.source_utils import get_source_root_path

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.stack import Stack
    from zenml.steps import BaseStep

logger = get_logger(__name__)


def stream_logs(
    instance: Any, project_id: str, seconds_before: int = 10
) -> None:
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


def wait_for_extended_operation(
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
            f"Warnings during {verbose_name}:\n", file=sys.stderr, flush=True
        )
        for warning in operation.warnings:
            logger.warning(
                f" - {warning.code}: {warning.message}",
                file=sys.stderr,
                flush=True,
            )

    return result


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


def sanitize_gcp_vm_name(bad_name: str) -> str:
    """Get a good name from a bad name"""
    return bad_name.replace("_", "-")


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
    newest_image = image_client.get_from_family(project=project, family=family)
    return newest_image


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


def wait_for_extended_operation(
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
            f"Warnings during {verbose_name}:\n", file=sys.stderr, flush=True
        )
        for warning in operation.warnings:
            logger.warning(
                f" - {warning.code}: {warning.message}",
                file=sys.stderr,
                flush=True,
            )

    return result


def get_instance(
    project_id: str,
    zone: str,
    instance_name: str,
):
    """_summary_

    Args:
        project_id (str): _description_
        zone (str): _description_
        instance_name (str): _description_
    """
    instance_client = compute_v1.InstancesClient()
    return instance_client.get(
        project=project_id, zone=zone, instance=instance_name
    )


def create_instance(
    image_name: str,
    c_params: str,
    project_id: str,
    zone: str,
    instance_name: str,
    disks: List[compute_v1.AttachedDisk] = "",
    machine_type: str = "n1-standard-1",
    network_link: str = "global/networks/default",
    subnetwork_link: str = None,
    internal_ip: str = None,
    external_access: bool = False,
    external_ipv4: str = None,
    accelerators: List[compute_v1.AcceleratorConfig] = None,
    preemptible: bool = False,
    custom_hostname: str = None,
    delete_protection: bool = False,
) -> compute_v1.Instance:
    """
    Send an instance creation request to the Compute Engine API and wait for it to complete.

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
        Instance object.
    """
    instance_client = compute_v1.InstancesClient()

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
    instance.name = instance_name
    instance.disks = disks
    if re.match(r"^zones/[a-z\d\-]+/machineTypes/[a-z\d\-]+$", machine_type):
        instance.machine_type = machine_type
    else:
        instance.machine_type = f"zones/{zone}/machineTypes/{machine_type}"

    if accelerators:
        instance.guest_accelerators = accelerators

    instance.network_interfaces = [network_interface]

    import os

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


class AWSVMOrchestrator(BaseOrchestrator):
    custom_docker_base_image_name: Optional[str] = None
    project_id: str = "zenml-core"
    zone: str = "europe-west1-b"

    # Class Configuration
    FLAVOR: ClassVar[str] = AWS_VM_ORCHESTRATOR_FLAVOR

    def get_docker_image_name(self, pipeline_name: str) -> str:
        """Returns the full docker image name including registry and tag."""

        base_image_name = f"zenml-gcp-vm:{pipeline_name}"
        container_registry = Repository().active_stack.container_registry

        if container_registry:
            registry_uri = container_registry.uri.rstrip("/")
            return f"{registry_uri}/{base_image_name}"
        else:
            return base_image_name

    def prepare_pipeline_deployment(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> None:
        """Builds a docker image for the current environment and uploads it to
        a container registry if configured.
        """
        from zenml.utils import docker_utils

        image_name = self.get_docker_image_name(pipeline.name)

        requirements = {*stack.requirements(), *pipeline.requirements}

        logger.debug("AWS VM docker image requirements: %s", requirements)

        docker_utils.build_docker_image(
            build_context_path=get_source_root_path(),
            image_name=image_name,
            dockerignore_path=pipeline.dockerignore_file,
            requirements=requirements,
            base_image=self.custom_docker_base_image_name,
        )

        assert stack.container_registry  # should never happen due to validation
        stack.container_registry.push_image(image_name)

        # Store the docker image digest in the runtime configuration so it gets
        # tracked in the ZenStore
        image_digest = docker_utils.get_image_digest(image_name) or image_name
        runtime_configuration["docker_image"] = image_digest

    def prepare_or_run_pipeline(
        self,
        sorted_steps: List["BaseStep"],
        pipeline: "BasePipeline",
        pb2_pipeline: Pb2Pipeline,
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        image_name = self.get_docker_image_name(pipeline.name)
        image_name = get_image_digest(image_name) or image_name

        run_name = runtime_configuration.run_name
        assert run_name

        for step in sorted_steps:
            command = AWSVMEntrypointConfiguration.get_entrypoint_command()
            arguments = AWSVMEntrypointConfiguration.get_entrypoint_arguments(
                step=step,
                pb2_pipeline=pb2_pipeline,
                **{RUN_NAME_OPTION: run_name},
            )

            ###############################################################
            # TODO: Launch a VM with the docker image `image_name` which  #
            # *syncronously executes the `command` with `arguments`       #

            image = get_image_from_family(
                "gce-uefi-images", family="cos-69-lts"
            )

            disk = disk_from_image(
                f"zones/{self.zone}/diskTypes/pd-ssd",
                disk_size_gb=10,
                boot=True,
                source_image=f"projects/gce-uefi-images/global/images/{image.name}",
                auto_delete=True,
            )

            instance = create_instance(
                image_name=image_name,
                c_params=" ".join(command + arguments),
                project_id=self.project_id,
                zone=self.zone,
                instance_name=sanitize_gcp_vm_name("zenml-" + step.name),
                disks=[disk],
                external_access=True,
            )

            logger.info(
                f"Instance {instance.name} is now running the pipeline. Logs will be streamed soon..."
            )
            seconds_wait = 10
            while instance.status == "RUNNING":
                instance = get_instance(
                    self.project_id, self.zone, instance.name
                )
                stream_logs(
                    instance, self.project_id, seconds_before=seconds_wait
                )
                time.sleep(seconds_wait)
            stream_logs(
                instance, self.project_id, seconds_before=seconds_wait * 2
            )
