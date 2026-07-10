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
"""Slurm step operator flavor."""

from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Type

from pydantic import Field, model_validator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.slurm import SLURM_STEP_OPERATOR_FLAVOR
from zenml.step_operators.base_step_operator import (
    BaseStepOperatorConfig,
    BaseStepOperatorFlavor,
)
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.slurm.step_operators import SlurmStepOperator


class SlurmTransport(str, Enum):
    """How the client reaches the Slurm submission host."""

    SSH = "ssh"
    LOCAL = "local"


class SlurmStepOperatorSettings(BaseSettings):
    """Settings for the Slurm step operator.

    These map onto ``sbatch`` directives and can be overridden per step.
    """

    partition: Optional[str] = Field(
        default=None,
        description="Slurm partition (queue) to submit the job to, passed as "
        "`--partition`. Uses the cluster's default partition if unset. "
        "Example: 'gpu'",
    )
    time_limit: Optional[str] = Field(
        default=None,
        description="Wall-clock time limit for the job in Slurm time format, "
        "passed as `--time`. Examples: '30:00' (30 minutes), '2:00:00' "
        "(2 hours), '1-12:00:00' (1 day 12 hours). Uses the partition "
        "default if unset",
    )
    account: Optional[str] = Field(
        default=None,
        description="Slurm account to charge the job to, passed as "
        "`--account`. Required on clusters that enforce accounting. "
        "Example: 'ml-research'",
    )
    qos: Optional[str] = Field(
        default=None,
        description="Quality-of-service level for the job, passed as "
        "`--qos`. Example: 'normal'",
    )
    extra_sbatch_directives: List[str] = Field(
        default_factory=list,
        description="Additional raw `#SBATCH` directive lines appended to "
        "the generated job script, as an escape hatch for cluster-specific "
        "options. Example: ['--constraint=a100', '--exclusive']",
    )


class SlurmStepOperatorConfig(
    BaseStepOperatorConfig, SlurmStepOperatorSettings
):
    """Configuration for the Slurm step operator."""

    transport: SlurmTransport = Field(
        default=SlurmTransport.SSH,
        description="How to reach the Slurm submission host: 'ssh' connects "
        "to a remote login/controller node, 'local' runs sbatch directly and "
        "requires the client to already run on the cluster. Example: 'ssh'",
    )
    workdir: str = Field(
        description="Directory on the cluster used to stage job scripts, "
        "code archives and job output, ideally on a filesystem shared "
        "between the submission host and the compute nodes. Example: "
        "'/shared/zenml-runs'",
    )
    env_setup_command: str = Field(
        description="Shell command executed at the start of every job to "
        "activate a Python environment that has zenml and the pipeline "
        "requirements installed. Examples: 'source /shared/venvs/zenml/bin/"
        "activate', 'module load python && conda activate zenml'",
    )
    # SSH connection settings, required for the `ssh` transport. Field names
    # deliberately match the ssh integration's connection mixin so its
    # SSHClient can consume this config directly.
    hostname: Optional[str] = Field(
        default=None,
        description="Hostname or IP address of the Slurm login/controller "
        "node, required for the 'ssh' transport. Example: "
        "'login.cluster.example.com'",
    )
    username: Optional[str] = Field(
        default=None,
        description="SSH username on the login node, required for the 'ssh' "
        "transport. Example: 'mlops'",
    )
    port: int = Field(
        default=22,
        description="SSH port on the login node. Standard SSH port is 22",
    )
    ssh_key_path: Optional[str] = Field(
        default=None,
        description="Path to the SSH private key file on the submitting "
        "machine. Supports RSA, Ed25519, and ECDSA keys",
    )
    ssh_private_key: Optional[str] = SecretField(
        default=None,
        description="SSH private key content, used instead of ssh_key_path "
        "when the key is stored in a ZenML secret. Supports {{secret.key}} "
        "references",
    )
    ssh_key_passphrase: Optional[str] = SecretField(
        default=None,
        description="Passphrase for an encrypted SSH private key. Leave "
        "unset if the key is not encrypted",
    )
    verify_host_key: bool = Field(
        default=True,
        description="Require the remote host key to be present in "
        "known_hosts. Set to False to auto-accept unknown host keys (less "
        "secure, convenient for ephemeral clusters)",
    )
    known_hosts_path: Optional[str] = Field(
        default=None,
        description="Path to a custom known_hosts file used for host key "
        "verification. Uses ~/.ssh/known_hosts if unset",
    )

    @model_validator(mode="after")
    def _validate_transport_requirements(self) -> "SlurmStepOperatorConfig":
        """Validates that the ssh transport has connection details.

        Returns:
            The validated config.

        Raises:
            ValueError: If the ssh transport is selected without a hostname
                or username.
        """
        if self.transport == SlurmTransport.SSH and not (
            self.hostname and self.username
        ):
            raise ValueError(
                "The Slurm step operator with the 'ssh' transport needs "
                "`hostname` and `username` to reach the login node. Set "
                "them, or use transport='local' if the client runs on the "
                "cluster itself."
            )
        return self

    @property
    def is_remote(self) -> bool:
        """Whether this component runs remotely.

        Returns:
            True, since jobs execute on the Slurm cluster.
        """
        return True


class SlurmStepOperatorFlavor(BaseStepOperatorFlavor):
    """Flavor of the Slurm step operator."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return SLURM_STEP_OPERATOR_FLAVOR

    @property
    def display_name(self) -> str:
        """Display name of the flavor.

        Returns:
            The display name of the flavor.
        """
        return "Slurm"

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/step_operator/slurm.png"

    @property
    def config_class(self) -> Type[SlurmStepOperatorConfig]:
        """Config class for this flavor.

        Returns:
            The config class.
        """
        return SlurmStepOperatorConfig

    @property
    def implementation_class(self) -> Type["SlurmStepOperator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.slurm.step_operators import SlurmStepOperator

        return SlurmStepOperator
