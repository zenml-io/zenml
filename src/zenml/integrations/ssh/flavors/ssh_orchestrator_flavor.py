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
"""SSH orchestrator flavor."""

from typing import TYPE_CHECKING, Dict, List, Optional, Type

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.integrations.ssh import SSH_ORCHESTRATOR_FLAVOR
from zenml.integrations.ssh.flavors.ssh_base_flavor import (
    SSHConnectionConfigMixin,
)
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor

if TYPE_CHECKING:
    from zenml.integrations.ssh.orchestrators import SSHOrchestrator


class SSHOrchestratorSettings(BaseSettings):
    """Settings for the SSH orchestrator."""

    mounts: Dict[str, str] = Field(
        default_factory=dict,
        description="Host-path to container-path bind mounts applied to "
        "every step container. Keys are absolute paths on the remote host, "
        "values are absolute paths inside the container. Example: "
        "{'/data/datasets': '/datasets'}",
    )
    gpu_enabled: bool = Field(
        default=True,
        description="Enable NVIDIA GPU access for each step container "
        "(--gpus all). Set to False for CPU-only pipelines",
    )
    docker_run_args: Optional[List[str]] = Field(
        default=None,
        description="Additional arguments for the docker run command, "
        "inserted before the image name.",
    )


class SSHOrchestratorConfig(
    BaseOrchestratorConfig, SSHConnectionConfigMixin, SSHOrchestratorSettings
):
    """Configuration for the SSH orchestrator."""

    container_registry_autologin: bool = Field(
        default=False,
        description="Run `docker login` on the remote host using the "
        "submitted stack's container registry credentials before launching, so "
        "private images can be pulled",
    )
    cleanup_old_files: bool = Field(
        default=True,
        description="Remove pipeline launch files (Compose files) on the "
        "remote host once they are older than 7 days",
    )
    minimum_free_disk_gb: float = Field(
        default=5.0,
        ge=0,
        description="Pre-flight guard that fails a submission if the "
        "remote_workdir filesystem has less free disk than this (in GB). Set "
        "to 0 to disable the check. Example: 10.0 for image-heavy pipelines",
    )

    @property
    def is_remote(self) -> bool:
        """Whether the orchestrator runs the pipeline remotely.

        Returns:
            True
        """
        return True

    @property
    def is_local(self) -> bool:
        """Whether the orchestrator runs the pipeline locally.

        Returns:
            False
        """
        return False

    @property
    def is_schedulable(self) -> bool:
        """Whether the orchestrator supports scheduled pipeline runs.

        Returns:
            False.
        """
        return False


class SSHOrchestratorFlavor(BaseOrchestratorFlavor):
    """SSH orchestrator flavor."""

    @property
    def name(self) -> str:
        """Flavor name.

        Returns:
            The flavor name.
        """
        return SSH_ORCHESTRATOR_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A URL to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A URL to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A URL to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/ssh.png"

    @property
    def config_class(self) -> Type[SSHOrchestratorConfig]:
        """Config class for the base orchestrator flavor.

        Returns:
            The config class.
        """
        return SSHOrchestratorConfig

    @property
    def implementation_class(self) -> Type["SSHOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            Implementation class for this flavor.
        """
        from zenml.integrations.ssh.orchestrators import SSHOrchestrator

        return SSHOrchestrator
