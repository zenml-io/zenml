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
"""Client for interacting with a Slurm cluster.

The client wraps the Slurm CLI (``sbatch``, ``squeue``, ``scancel``) behind a
small transport abstraction so the same logic works whether the commands run
locally (the ZenML client already lives on a login node) or over SSH (the
common case: submitting to a remote cluster). A REST transport (``slurmrestd``)
can slot in later without touching the step operator.

Only the CLI surface that is universally available is used: job state is read
from ``squeue`` while a job is queued or running, and from a sentinel exit-code
file written by the job script after it leaves the queue, so the client does
not depend on Slurm accounting (``sacct``) being configured.
"""

import shlex
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from zenml.integrations.slurm.flavors.base import SlurmConnectionConfig

# Slurm job states that mean the job is still on its way to running.
PENDING_STATES = {
    "PENDING",
    "CONFIGURING",
    "REQUEUED",
    "RESIZING",
    "SUSPENDED",
}
# Slurm job states that mean the job is actively running or wrapping up.
RUNNING_STATES = {"RUNNING", "COMPLETING", "STAGE_OUT", "SIGNALING"}


@dataclass
class CommandResult:
    """Result of a command executed on the submission host."""

    exit_code: int
    stdout: str
    stderr: str


class SlurmCommandRunner(ABC):
    """Transport abstraction: run commands and move files to the cluster."""

    @abstractmethod
    def run(self, command: str) -> CommandResult:
        """Run a shell command on the submission host.

        Args:
            command: The shell command to run.

        Returns:
            The command result.
        """

    @abstractmethod
    def put_text(
        self, remote_path: str, content: str, mode: int = 0o600
    ) -> None:
        """Write text content to a file on the submission host.

        Args:
            remote_path: Destination path on the submission host.
            content: The text content to write.
            mode: File permissions. Defaults to owner read/write only, since
                the job script and environment file may hold credentials on a
                shared cluster filesystem.
        """

    @abstractmethod
    def read_text(self, remote_path: str) -> str:
        """Read a text file from the submission host.

        Args:
            remote_path: Path of the file on the submission host.

        Returns:
            The file content.
        """

    def close(self) -> None:
        """Release any resources held by the runner."""


class LocalSlurmCommandRunner(SlurmCommandRunner):
    """Runs Slurm commands as local subprocesses.

    For setups where the ZenML client or orchestrator already runs on a
    cluster login node with the Slurm CLI in ``PATH``.
    """

    def run(self, command: str) -> CommandResult:
        """Run a shell command locally.

        Args:
            command: The shell command to run.

        Returns:
            The command result.
        """
        completed = subprocess.run(  # nosec B602 - commands are built by us
            command,
            shell=True,
            capture_output=True,
            text=True,
        )
        return CommandResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def put_text(
        self, remote_path: str, content: str, mode: int = 0o600
    ) -> None:
        """Write text content to the destination path.

        Args:
            remote_path: Destination path.
            content: The text content to write.
            mode: File permissions to apply.
        """
        import os

        with open(remote_path, "w") as f:
            f.write(content)
        os.chmod(remote_path, mode)

    def read_text(self, remote_path: str) -> str:
        """Read a text file.

        Args:
            remote_path: Path of the file.

        Returns:
            The file content.
        """
        with open(remote_path) as f:
            return f.read()


class SSHSlurmCommandRunner(SlurmCommandRunner):
    """Runs Slurm commands on a remote login node over SSH.

    Reuses the SSH client from the ``ssh`` integration; the config object must
    provide the same connection fields (``hostname``, ``username``, ...).
    """

    def __init__(self, config: "SlurmConnectionConfig") -> None:
        """Initialize the runner with an open SSH connection.

        Args:
            config: The Slurm component config holding SSH connection settings.
        """
        from zenml.integrations.ssh.ssh_client import SSHClient

        # SlurmConnectionConfig inherits SSHConnectionConfigMixin, so the SSH
        # client consumes it directly.
        self._ssh = SSHClient(config)
        self._ssh.__enter__()

    def run(self, command: str) -> CommandResult:
        """Run a shell command on the remote host.

        Args:
            command: The shell command to run.

        Returns:
            The command result.
        """
        result = self._ssh.exec(command)
        return CommandResult(
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def put_text(
        self, remote_path: str, content: str, mode: int = 0o600
    ) -> None:
        """Write text content to a file on the remote host.

        Args:
            remote_path: Destination path on the remote host.
            content: The text content to write.
            mode: File permissions to apply.
        """
        self._ssh.put_text(remote_path, content, mode=mode)

    def read_text(self, remote_path: str) -> str:
        """Read a text file from the remote host.

        Args:
            remote_path: Path of the file on the remote host.

        Returns:
            The file content.
        """
        return self._ssh.read_text(remote_path)

    def close(self) -> None:
        """Close the SSH connection."""
        self._ssh.__exit__(None, None, None)


class SlurmClient:
    """Thin wrapper around the Slurm CLI on top of a command runner."""

    def __init__(self, runner: SlurmCommandRunner) -> None:
        """Initialize the client.

        Args:
            runner: The transport used to reach the submission host.
        """
        self.runner = runner

    def submit(
        self, script_path: str, dependencies: Optional[List[str]] = None
    ) -> str:
        """Submit a batch script and return the Slurm job id.

        Args:
            script_path: Path of the sbatch script on the submission host.
            dependencies: Job ids this job must wait for. The job runs only
                after all of them complete successfully (``afterok``); if any
                cannot be satisfied, the job is cancelled rather than left
                pending forever (``--kill-on-invalid-dep``), which propagates a
                failure through the DAG.

        Returns:
            The Slurm job id.

        Raises:
            RuntimeError: If the submission fails.
        """
        command = "sbatch --parsable"
        if dependencies:
            command += (
                f" --dependency=afterok:{':'.join(dependencies)}"
                " --kill-on-invalid-dep=yes"
            )
        result = self.runner.run(f"{command} {shlex.quote(script_path)}")
        if result.exit_code != 0:
            raise RuntimeError(
                f"`sbatch` failed with exit code {result.exit_code}: "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        # --parsable prints `jobid[;cluster]`
        return result.stdout.strip().split(";")[0]

    def get_job_state(self, job_name: str) -> Optional[str]:
        """Get the queue state of a job by its name.

        Args:
            job_name: The Slurm job name to look up.

        Returns:
            The Slurm job state (e.g. ``PENDING``, ``RUNNING``) or ``None``
            if the job is no longer in the queue. Jobs leave the ``squeue``
            output once they reach a terminal state, so ``None`` means the
            job finished, failed, or never existed - the caller disambiguates
            via the exit-code sentinel file.

        Raises:
            RuntimeError: If ``squeue`` fails.
        """
        result = self.runner.run(
            f"squeue --noheader --format=%T --name {shlex.quote(job_name)}"
        )
        if result.exit_code != 0:
            raise RuntimeError(
                f"`squeue` failed with exit code {result.exit_code}: "
                f"{result.stderr.strip()}"
            )
        state = result.stdout.strip().splitlines()
        return state[0].strip() if state else None

    def cancel(self, job_name: str) -> None:
        """Cancel a job by its name.

        Args:
            job_name: The Slurm job name to cancel.

        Raises:
            RuntimeError: If ``scancel`` fails.
        """
        result = self.runner.run(f"scancel --name {shlex.quote(job_name)}")
        if result.exit_code != 0:
            raise RuntimeError(
                f"`scancel` failed with exit code {result.exit_code}: "
                f"{result.stderr.strip()}"
            )


def build_slurm_client(config: "SlurmConnectionConfig") -> SlurmClient:
    """Build a Slurm client for the transport configured on a component.

    Both the step operator and the orchestrator reach the cluster the same
    way, so they share this factory. The caller owns the returned client and
    must close its ``runner`` when done (``client.runner.close()``).

    Args:
        config: The component config holding the transport and, for the ssh
            transport, the SSH connection settings.

    Returns:
        A Slurm client wrapping a runner for the configured transport.
    """
    from zenml.integrations.slurm.flavors.base import SlurmTransport

    runner: SlurmCommandRunner
    if config.transport == SlurmTransport.LOCAL:
        runner = LocalSlurmCommandRunner()
    else:
        runner = SSHSlurmCommandRunner(config)
    return SlurmClient(runner)
