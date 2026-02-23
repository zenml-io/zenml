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
"""SSH step operator flavor."""

from typing import TYPE_CHECKING, List, Optional, Type

from pydantic import Field, model_validator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.ssh import SSH_STEP_OPERATOR_FLAVOR
from zenml.step_operators import BaseStepOperatorConfig, BaseStepOperatorFlavor
from zenml.utils.secret_utils import PlainSerializedSecretStr

if TYPE_CHECKING:
    from zenml.integrations.ssh.step_operators import SSHStepOperator


class SSHStepOperatorSettings(BaseSettings):
    """Per-step settings for SSH step operator execution.

    These settings can be configured per-step using the step decorator:

    ```python
    @step(
        step_operator="ssh",
        settings={"step_operator": SSHStepOperatorSettings(
            gpu_indices=[0, 1],
        )}
    )
    def my_training_step():
        ...
    ```

    Attributes:
        gpu_indices: Specific GPU device indices to expose to the container
            via Docker --gpus flag. Acquired locks prevent overlapping use.
        use_gpu_locks: Whether to acquire per-GPU flock locks before running
            the container, preventing concurrent jobs from sharing GPUs.
        docker_run_args: Additional arguments to pass to docker run (do not
            include secrets here as they may appear in process listings).
    """

    gpu_indices: Optional[List[int]] = Field(
        default=None,
        description="GPU device indices to expose inside the container via "
        "Docker --gpus flag. Each index gets an exclusive flock lock when "
        "use_gpu_locks is True. Examples: [0] for single GPU, [0, 2] for "
        "specific GPUs, None for CPU-only execution",
    )
    use_gpu_locks: bool = Field(
        default=True,
        description="Acquire per-GPU-index flock locks on the remote host "
        "before running the container. Prevents concurrent steps from "
        "oversubscribing the same GPU. Only applies when gpu_indices is set",
    )
    docker_run_args: Optional[List[str]] = Field(
        default=None,
        description="Additional arguments for the docker run command. "
        "Inserted before the image name. Do not include secrets here. "
        "Example: ['--shm-size=2g', '--ulimit', 'memlock=-1']",
    )


class SSHStepOperatorConfig(BaseStepOperatorConfig, SSHStepOperatorSettings):
    """Configuration for the SSH step operator.

    Combines connection settings (set once at registration) with per-step
    defaults that individual steps can override via SSHStepOperatorSettings.

    Example registration:
    ```bash
    zenml step-operator register my-gpu-box \\
        --flavor=ssh \\
        --hostname=gpu-server.example.com \\
        --username=ubuntu \\
        --ssh_key_path=~/.ssh/id_ed25519
    ```
    """

    hostname: str = Field(
        description="Hostname or IP address of the remote SSH server. "
        "Must be reachable from the machine running the orchestrator. "
        "Examples: 'gpu-box.internal', '10.0.1.42', 'my-server.example.com'",
    )
    username: str = Field(
        description="SSH username for authentication on the remote host. "
        "This user must have permission to run Docker commands (typically "
        "a member of the 'docker' group). Example: 'ubuntu'",
    )
    port: int = Field(
        default=22,
        ge=1,
        le=65535,
        description="SSH port on the remote host. Standard SSH port is 22",
    )

    ssh_key_path: Optional[str] = Field(
        default=None,
        description="Path to the SSH private key file on the local machine. "
        "Supports RSA, Ed25519, and ECDSA keys. The key may be encrypted "
        "(provide ssh_key_passphrase). "
        "Example: '~/.ssh/id_ed25519'",
    )
    ssh_private_key: Optional[PlainSerializedSecretStr] = Field(
        default=None,
        description="SSH private key content as a string. Use this instead of "
        "ssh_key_path when the key is stored in a ZenML secret rather than "
        "on disk. Supports {{secret.key}} references",
    )
    ssh_key_passphrase: Optional[PlainSerializedSecretStr] = Field(
        default=None,
        description="Passphrase for an encrypted SSH private key. Leave "
        "unset if the key is not encrypted. Supports {{secret.key}} references",
    )

    verify_host_key: bool = Field(
        default=True,
        description="Require the remote host key to be present in "
        "known_hosts. When True (recommended), uses paramiko RejectPolicy "
        "to prevent MITM attacks. Set to False to auto-accept unknown "
        "host keys (less secure, convenient for ephemeral hosts)",
    )
    known_hosts_path: Optional[str] = Field(
        default=None,
        description="Path to a known_hosts file for host key verification. "
        "Defaults to ~/.ssh/known_hosts if not specified. Only used when "
        "verify_host_key is True",
    )

    connection_timeout: float = Field(
        default=10.0,
        gt=0,
        description="Timeout in seconds for establishing the SSH connection. "
        "Increase for high-latency networks. Example: 30.0 for slow links",
    )
    keepalive_interval: int = Field(
        default=30,
        ge=0,
        description="Interval in seconds between SSH keepalive packets. "
        "Prevents long-running training jobs from being killed by idle "
        "connection timeouts. Set to 0 to disable",
    )

    remote_workdir: str = Field(
        default="/tmp/zenml-ssh",
        description="Base directory on the remote host for temporary files "
        "(env-files, wrapper scripts). Created automatically if it does not "
        "exist. Example: '/home/ubuntu/zenml-workdir'",
    )
    gpu_lock_dir: str = Field(
        default="/tmp/zenml-gpu-locks",
        description="Directory on the remote host where per-GPU flock lock "
        "files are created. Each GPU index gets its own lock file "
        "(e.g., gpu-0.lock, gpu-1.lock). Created automatically",
    )
    docker_binary: str = Field(
        default="docker",
        description="Path to the Docker binary on the remote host. Override "
        "if Docker is installed in a non-standard location. "
        "Example: '/usr/local/bin/docker'",
    )

    @model_validator(mode="after")
    def _check_ssh_auth(self) -> "SSHStepOperatorConfig":
        """Validate that at least one SSH authentication method is provided.

        Returns:
            The validated config.

        Raises:
            ValueError: If neither ssh_key_path nor ssh_private_key is set.
        """
        if not self.ssh_key_path and not self.ssh_private_key:
            raise ValueError(
                "SSH authentication requires either 'ssh_key_path' (path to "
                "a private key file) or 'ssh_private_key' (key content, "
                "ideally via a ZenML secret reference) to be set."
            )
        return self

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        Returns:
            True because the SSH step operator always runs remotely.
        """
        return True

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            False because the SSH step operator always runs remotely.
        """
        return False


class SSHStepOperatorFlavor(BaseStepOperatorFlavor):
    """SSH step operator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return SSH_STEP_OPERATOR_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/step_operator/ssh.png"

    @property
    def config_class(self) -> Type[SSHStepOperatorConfig]:
        """Returns SSHStepOperatorConfig config class.

        Returns:
            The config class.
        """
        return SSHStepOperatorConfig

    @property
    def implementation_class(self) -> Type["SSHStepOperator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.ssh.step_operators import SSHStepOperator

        return SSHStepOperator
