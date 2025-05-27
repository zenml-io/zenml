#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Skypilot orchestrator base config and settings."""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestratorConfig

logger = get_logger(__name__)


class SkypilotBaseOrchestratorSettings(BaseSettings):
    """Skypilot orchestrator base settings.

    Attributes:
        instance_type: the instance type to use.
        cpus: the number of CPUs required for the task.
            If a str, must be a string of the form `'2'` or `'2+'`, where
            the `+` indicates that the task requires at least 2 CPUs.
        memory: the amount of memory in GiB required. If a
            str, must be a string of the form `'16'` or `'16+'`, where
            the `+` indicates that the task requires at least 16 GB of memory.
        accelerators: the accelerators required. If a str, must be
            a string of the form `'V100'` or `'V100:2'`, where the `:2`
            indicates that the task requires 2 V100 GPUs. If a dict, must be a
            dict of the form `{'V100': 2}` or `{'tpu-v2-8': 1}`.
        accelerator_args: accelerator-specific arguments. For example,
            `{'tpu_vm': True, 'runtime_version': 'tpu-vm-base'}` for TPUs.
        use_spot: whether to use spot instances. If None, defaults to
            False.
        job_recovery: the spot recovery strategy to use for the managed
            spot to recover the cluster from preemption. Refer to
            `recovery_strategy module <https://github.com/skypilot-org/skypilot/blob/master/sky/spot/recovery_strategy.py>`__ # pylint: disable=line-too-long
            for more details.
        region: the region to use.
        zone: the zone to use.
        image_id: the image ID to use. If a str, must be a string
            of the image id from the cloud, such as AWS:
            ``'ami-1234567890abcdef0'``, GCP:
            ``'projects/my-project-id/global/images/my-image-name'``;
            Or, a image tag provided by SkyPilot, such as AWS:
            ``'skypilot:gpu-ubuntu-2004'``. If a dict, must be a dict mapping
            from region to image ID, such as:

            .. code-block:: python

                {
                'us-west1': 'ami-1234567890abcdef0',
                'us-east1': 'ami-1234567890abcdef0'
                }

        disk_size: the size of the OS disk in GiB.
        disk_tier: the disk performance tier to use. If None, defaults to
            ``'medium'``.
        ports: Ports to expose. Could be an integer, a range, or a list of
            integers and ranges. All ports will be exposed to the public internet.
        labels: Labels to apply to instances as key-value pairs. These are
            mapped to cloud-specific implementations (instance tags in AWS,
            instance labels in GCP, etc.)
        any_of: List of candidate resources to try in order of preference based on
            cost (determined by the optimizer).
        ordered: List of candidate resources to try in the specified order.

        cluster_name: name of the cluster to create/reuse.  If None,
            auto-generate a name.
        retry_until_up: whether to retry launching the cluster until it is
            up.
        idle_minutes_to_autostop: automatically stop the cluster after this
            many minute of idleness, i.e., no running or pending jobs in the
            cluster's job queue. Idleness gets reset whenever setting-up/
            running/pending jobs are found in the job queue. Setting this
            flag is equivalent to running
            ``sky.launch(..., detach_run=True, ...)`` and then
            ``sky.autostop(idle_minutes=<minutes>)``. If not set, the cluster
            will not be autostopped.
        down: Tear down the cluster after all jobs finish (successfully or
            abnormally). If --idle-minutes-to-autostop is also set, the
            cluster will be torn down after the specified idle time.
            Note that if errors occur during provisioning/data syncing/setting
            up, the cluster will not be torn down for debugging purposes.
        stream_logs: if True, show the logs in the terminal.
        docker_run_args: Optional arguments to pass to the `docker run` command
            running inside the VM.
        workdir: Working directory to sync to the VM. Synced to ~/sky_workdir.
        task_name: Task name used for display purposes.
        file_mounts: File and storage mounts configuration for remote cluster.
        envs: Environment variables for the task.
        task_settings: Dictionary of arbitrary settings to pass to sky.Task().
            This allows passing future parameters added by SkyPilot without
            requiring updates to ZenML.
        resources_settings: Dictionary of arbitrary settings to pass to
            sky.Resources(). This allows passing future parameters added
            by SkyPilot without requiring updates to ZenML.
        launch_settings: Dictionary of arbitrary settings to pass to
            sky.launch(). This allows passing future parameters added
            by SkyPilot without requiring updates to ZenML.
    """

    # Resources
    instance_type: Optional[str] = None
    cpus: Union[None, int, float, str] = Field(
        default=None, union_mode="left_to_right"
    )
    memory: Union[None, int, float, str] = Field(
        default=None, union_mode="left_to_right"
    )
    accelerators: Union[None, str, Dict[str, int]] = Field(
        default=None, union_mode="left_to_right"
    )
    accelerator_args: Optional[Dict[str, str]] = None
    use_spot: Optional[bool] = None
    job_recovery: Union[None, str, Dict[str, Any]] = Field(
        default=None, union_mode="left_to_right"
    )
    region: Optional[str] = None
    zone: Optional[str] = None
    image_id: Union[Dict[str, str], str, None] = Field(
        default=None, union_mode="left_to_right"
    )
    disk_size: Optional[int] = None
    disk_tier: Optional[Literal["high", "medium", "low", "ultra", "best"]] = (
        None
    )

    # Run settings
    cluster_name: Optional[str] = None
    retry_until_up: bool = False
    idle_minutes_to_autostop: Optional[int] = 30
    down: bool = True
    stream_logs: bool = True
    docker_run_args: List[str] = []

    # Additional SkyPilot features
    ports: Union[None, int, str, List[Union[int, str]]] = Field(
        default=None, union_mode="left_to_right"
    )
    labels: Optional[Dict[str, str]] = None
    any_of: Optional[List[Dict[str, Any]]] = None
    ordered: Optional[List[Dict[str, Any]]] = None
    workdir: Optional[str] = None
    task_name: Optional[str] = None
    file_mounts: Optional[Dict[str, Any]] = None
    envs: Optional[Dict[str, str]] = None

    # Future-proofing settings dictionaries
    task_settings: Dict[str, Any] = {}
    resources_settings: Dict[str, Any] = {}
    launch_settings: Dict[str, Any] = {}


class SkypilotBaseOrchestratorConfig(
    BaseOrchestratorConfig, SkypilotBaseOrchestratorSettings
):
    """Skypilot orchestrator base config.

    Attributes:
        disable_step_based_settings: whether to disable step-based settings.
            If True, the orchestrator will run all steps with the pipeline
            settings in one single VM. If False, the orchestrator will run
            each step with its own settings in separate VMs if provided.
    """

    disable_step_based_settings: bool = False

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return False

    @property
    def supports_client_side_caching(self) -> bool:
        """Whether the orchestrator supports client side caching.

        Returns:
            Whether the orchestrator supports client side caching.
        """
        # The Skypilot orchestrator runs the entire pipeline in a single VM, or
        # starts additional VMs from the root VM. Both of those cases are
        # currently not supported when using client-side caching.
        return False
