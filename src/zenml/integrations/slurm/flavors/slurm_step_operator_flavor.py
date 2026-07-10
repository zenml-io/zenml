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
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from pydantic import Field, model_validator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.slurm import SLURM_STEP_OPERATOR_FLAVOR
from zenml.integrations.ssh.flavors.base import SSHConnectionConfigMixin
from zenml.step_operators.base_step_operator import (
    BaseStepOperatorConfig,
    BaseStepOperatorFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.slurm.step_operators import SlurmStepOperator


class SlurmTransport(str, Enum):
    """How the client reaches the Slurm submission host."""

    SSH = "ssh"
    LOCAL = "local"


class SlurmContainerRuntime(str, Enum):
    """Container runtime used to run the step image on the compute node.

    Slurm compute nodes rarely have a Docker daemon (no root), so the ZenML
    step image is run with a rootless HPC container runtime by default.
    """

    APPTAINER = "apptainer"
    SINGULARITY = "singularity"
    PYXIS = "pyxis"
    DOCKER = "docker"


class SlurmStepOperatorSettings(BaseSettings):
    """Settings for the Slurm step operator.

    These map onto ``sbatch`` directives / container-run flags and can be
    overridden per step.
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
    container_mounts: Dict[str, str] = Field(
        default_factory=dict,
        description="Host-path to container-path bind mounts applied to the "
        "step container, e.g. to expose a shared scratch filesystem. "
        "Example: {'/scratch/user': '/scratch'}",
    )
    container_run_args: List[str] = Field(
        default_factory=list,
        description="Additional arguments passed to the container runtime "
        "command (apptainer/singularity/docker/srun), as an escape hatch. "
        "Example: ['--writable-tmpfs']",
    )


class SlurmStepOperatorConfig(
    BaseStepOperatorConfig,
    SSHConnectionConfigMixin,
    SlurmStepOperatorSettings,
):
    """Configuration for the Slurm step operator.

    Inherits the SSH connection fields (``ssh_key_path``, ``ssh_private_key``,
    ``port``, ``connection_timeout``, ...) from the ssh integration's
    connection mixin, so the same ``SSHClient`` consumes this config directly
    and the fields never drift out of sync.
    """

    transport: SlurmTransport = Field(
        default=SlurmTransport.SSH,
        description="How to reach the Slurm submission host: 'ssh' connects "
        "to a remote login/controller node, 'local' runs sbatch directly and "
        "requires the client to already run on the cluster. Example: 'ssh'",
    )
    container_runtime: SlurmContainerRuntime = Field(
        default=SlurmContainerRuntime.APPTAINER,
        description="Runtime used to run the step's Docker image on the "
        "compute node: 'apptainer' or 'singularity' (rootless, pulls "
        "`docker://` images; the safe HPC default), 'pyxis' (NVIDIA "
        "enroot/pyxis via `srun --container-image`), or 'docker' (only where "
        "a Docker daemon is available). Example: 'apptainer'",
    )
    workdir: str = Field(
        description="Directory on the cluster used to stage the job script, "
        "the environment file and the job output/exit-code sentinel, ideally "
        "on a filesystem shared between the submission host and the compute "
        "nodes. The step's code is not staged here; it lives in the container "
        "image. Example: '/shared/zenml-runs'",
    )
    # The connection mixin requires hostname/username, but the `local`
    # transport does not use SSH, so these are relaxed to optional (the
    # ignore below) and enforced for the `ssh` transport in the validator.
    hostname: Optional[str] = Field(  # type: ignore[assignment]
        default=None,
        description="Hostname or IP address of the Slurm login/controller "
        "node, required for the 'ssh' transport. Example: "
        "'login.cluster.example.com'",
    )
    username: Optional[str] = Field(  # type: ignore[assignment]
        default=None,
        description="SSH username on the login node, required for the 'ssh' "
        "transport. Example: 'mlops'",
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
