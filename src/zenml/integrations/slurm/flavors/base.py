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
"""Shared configuration for the Slurm step operator and orchestrator.

Both components submit the same kind of Slurm job - the step's Docker image
run on a compute node with an HPC container runtime - so they share the
transport, container-runtime and ``sbatch`` settings defined here.
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import Field, model_validator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.ssh.flavors.base import SSHConnectionConfigMixin


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


class SlurmJobSettings(BaseSettings):
    """Settings shared by every Slurm job ZenML submits.

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


class SlurmConnectionConfig(SSHConnectionConfigMixin):
    """Shared connection/runtime configuration for the Slurm components.

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
    def _validate_transport_requirements(self) -> "SlurmConnectionConfig":
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
                "The Slurm component with the 'ssh' transport needs "
                "`hostname` and `username` to reach the login node. Set "
                "them, or use transport='local' if the client runs on the "
                "cluster itself."
            )
        return self
