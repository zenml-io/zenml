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

from typing import TYPE_CHECKING, Dict, Optional, Type

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.integrations.ssh import SSH_ORCHESTRATOR_FLAVOR
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor
from zenml.utils.secret_utils import PlainSerializedSecretStr, SecretField

if TYPE_CHECKING:
    from zenml.integrations.ssh.orchestrators import SSHOrchestrator


class SSHOrchestratorSettings(BaseSettings):
    """Per-pipeline/step settings for the SSH orchestrator."""

    mounts: Dict[str, str] = Field(
        default_factory=dict,
        description="Host-path to container-path bind mounts applied to "
        "every step container. Keys are absolute paths on the remote host, "
        "values are absolute paths inside the container. Example: "
        "{'/data/datasets': '/datasets'}",
    )
    gpu_enabled: bool = Field(
        default=True,
        description="Request all NVIDIA GPUs for each step container via the "
        "Compose device reservation. Set to False for CPU-only pipelines on "
        "hosts without the NVIDIA container runtime",
    )


class SSHOrchestratorConfig(BaseOrchestratorConfig, SSHOrchestratorSettings):
    """Configuration for the SSH orchestrator.

    Example registration::

        zenml orchestrator register my-gpu-box \\
            --flavor=ssh \\
            --hostname=gpu-box.example.com \\
            --username=ubuntu \\
            --ssh_key_path=~/.ssh/id_ed25519
    """

    hostname: str = Field(
        description="Hostname or IP address of the remote SSH server. Must "
        "be reachable from the machine submitting the pipeline. Examples: "
        "'gpu-box.internal', '10.0.1.42', 'my-server.example.com'",
    )
    username: Optional[str] = Field(
        default=None,
        description="SSH username for authentication on the remote host. "
        "This user must be able to run Docker (typically a member of the "
        "'docker' group). Required for authentication. Example: 'ubuntu'",
    )
    port: int = Field(
        default=22,
        ge=1,
        le=65535,
        description="SSH port on the remote host. Standard SSH port is 22",
    )
    ssh_key_path: Optional[str] = Field(
        default=None,
        description="Path to the SSH private key file on the submitting "
        "machine. Supports RSA, Ed25519, and ECDSA keys. Example: "
        "'~/.ssh/id_ed25519'",
    )
    ssh_private_key: Optional[PlainSerializedSecretStr] = SecretField(
        default=None,
        description="SSH private key content, used instead of ssh_key_path "
        "when the key is stored in a ZenML secret. Supports {{secret.key}} "
        "references",
    )
    ssh_key_passphrase: Optional[PlainSerializedSecretStr] = SecretField(
        default=None,
        description="Passphrase for an encrypted SSH private key. Leave "
        "unset if the key is not encrypted",
    )
    verify_host_key: bool = Field(
        default=True,
        description="Require the remote host key to be present in "
        "known_hosts (paramiko RejectPolicy). Set to False to auto-accept "
        "unknown host keys (less secure, convenient for ephemeral hosts)",
    )
    known_hosts_path: Optional[str] = Field(
        default=None,
        description="Path to a known_hosts file for host-key verification. "
        "Defaults to ~/.ssh/known_hosts. Only used when verify_host_key is "
        "True",
    )
    connection_timeout: float = Field(
        default=10.0,
        gt=0,
        description="Timeout in seconds for establishing the SSH "
        "connection. Increase for high-latency links. Example: 30.0",
    )
    keepalive_interval: int = Field(
        default=30,
        ge=0,
        description="Interval in seconds between SSH keepalive packets, so "
        "long-running launches survive idle timeouts. Set to 0 to disable",
    )
    remote_workdir: str = Field(
        default="/tmp/zenml-ssh",
        description="Base directory on the remote host's filesystem for "
        "per-run Compose files. Created automatically",
    )
    docker_binary: str = Field(
        default="docker",
        description="Path to the Docker binary on the remote host. Override "
        "if Docker is installed in a non-standard location",
    )
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
            True; the SSH orchestrator always submits to a remote host.
        """
        return True

    @property
    def is_local(self) -> bool:
        """Whether the orchestrator runs the pipeline locally.

        Returns:
            False; the SSH orchestrator always submits to a remote host.
        """
        return False

    @property
    def is_schedulable(self) -> bool:
        """Whether the orchestrator supports scheduled pipeline runs.

        Returns:
            False; the SSH orchestrator does not manage schedules. Trigger
            pipelines directly (e.g. from your own cron job or CI).
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
