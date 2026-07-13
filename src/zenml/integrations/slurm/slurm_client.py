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

import re
import shlex
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Literal, Optional, Sequence

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

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        flags |= getattr(os, "O_NOFOLLOW", 0)
        file_descriptor = os.open(remote_path, flags, mode)
        os.fchmod(file_descriptor, mode)
        with os.fdopen(file_descriptor, "w") as f:
            f.write(content)

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
        self,
        script_path: str,
        dependencies: Optional[List[str]] = None,
        dependency_type: Literal["afterok", "afterany"] = "afterok",
    ) -> str:
        """Submit a batch script and return the Slurm job id.

        Args:
            script_path: Path of the sbatch script on the submission host.
            dependencies: Job ids this job must wait for. The job runs only
                after all of them complete successfully (``afterok``); if any
                cannot be satisfied, the job is cancelled rather than left
                pending forever (``--kill-on-invalid-dep``), which propagates a
                failure through the DAG.
            dependency_type: Slurm dependency type to use.

        Returns:
            The Slurm job id.

        Raises:
            ValueError: If any dependency job id is not numeric.
            RuntimeError: If the submission fails.
        """
        command = "sbatch --parsable"
        if dependencies:
            if not all(
                re.fullmatch(r"[0-9]+", job_id) for job_id in dependencies
            ):
                raise ValueError("Slurm dependency job IDs must be numeric.")
            command += (
                f" --dependency={dependency_type}:{':'.join(dependencies)}"
            )
            if dependency_type == "afterok":
                command += " --kill-on-invalid-dep=yes"
        result = self.runner.run(f"{command} {shlex.quote(script_path)}")
        if result.exit_code != 0:
            raise RuntimeError(
                f"`sbatch` failed with exit code {result.exit_code}: "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        # --parsable prints `jobid[;cluster]`
        job_id = result.stdout.strip().split(";")[0]
        if not re.fullmatch(r"[0-9]+", job_id):
            raise RuntimeError(
                f"`sbatch` returned an invalid job ID: {job_id!r}"
            )
        return job_id

    def get_job_states(self, job_ids: Sequence[str]) -> Dict[str, Optional[str]]:
        """Get the queue states of multiple jobs by their IDs.

        Args:
            job_ids: The Slurm job IDs to look up.

        Returns:
            A mapping from job ID to the Slurm job state (e.g. ``PENDING``,
            ``RUNNING``) or ``None`` if the job is no longer known to Slurm.
            Jobs leave the ``squeue`` output once they reach a terminal state,
            so ``None`` means the job finished, failed, or never existed - the
            caller disambiguates via the exit-code sentinel file.

        Raises:
            ValueError: If any job id is not numeric.
            RuntimeError: If ``squeue`` fails.
        """
        job_ids = list(dict.fromkeys(job_ids))
        if not all(re.fullmatch(r"[0-9]+", job_id) for job_id in job_ids):
            raise ValueError("Slurm job IDs must be numeric.")
        states: Dict[str, Optional[str]] = {job_id: None for job_id in job_ids}
        if not job_ids:
            return states

        jobs_arg = ",".join(job_ids)
        result = self.runner.run(
            f"squeue --noheader --format={shlex.quote('%i|%T')} "
            f"--jobs={shlex.quote(jobs_arg)}"
        )
        if result.exit_code != 0:
            if "invalid job id" in result.stderr.lower():
                return states
            raise RuntimeError(
                f"`squeue` failed with exit code {result.exit_code}: "
                f"{result.stderr.strip()}"
            )

        for line in result.stdout.strip().splitlines():
            job_id, separator, state = line.strip().partition("|")
            if separator and job_id in states:
                states[job_id] = state.strip()

        missing_job_ids = [
            job_id for job_id, state in states.items() if state is None
        ]
        if not missing_job_ids:
            return states

        # Completed jobs can disappear from squeue before a shared-filesystem
        # sentinel becomes visible. Slurm keeps them in controller memory for
        # MinJobAge, so scontrol closes that race without requiring sacct.
        missing_jobs_arg = ",".join(missing_job_ids)
        result = self.runner.run(
            "scontrol show job --oneliner "
            f"{shlex.quote(missing_jobs_arg)}"
        )
        if result.exit_code != 0:
            if "invalid job id" in result.stderr.lower():
                return states
            raise RuntimeError(
                f"`scontrol show job` failed with exit code "
                f"{result.exit_code}: {result.stderr.strip()}"
            )
        for line in result.stdout.strip().splitlines():
            job_id_match = re.search(r"(?:^|\s)JobId=([0-9]+)", line)
            state_match = re.search(r"(?:^|\s)JobState=([^\s]+)", line)
            if job_id_match and state_match:
                job_id = job_id_match.group(1)
                if job_id in states:
                    states[job_id] = state_match.group(1)

        return states

    def get_job_state(self, job_id: str) -> Optional[str]:
        """Get the queue state of a job by its ID.

        Args:
            job_id: The Slurm job ID to look up.

        Returns:
            The Slurm job state (e.g. ``PENDING``, ``RUNNING``) or ``None``
            if the job is no longer known to Slurm.
        """
        return self.get_job_states([job_id])[job_id]

    def cancel(self, job_id: str) -> None:
        """Cancel a job by its ID.

        Args:
            job_id: The Slurm job ID to cancel.
        """
        self.cancel_jobs([job_id])

    def cancel_jobs(self, job_ids: Sequence[str]) -> None:
        """Cancel multiple jobs by their IDs.

        Args:
            job_ids: Slurm job IDs to cancel.

        Raises:
            ValueError: If any job id is not numeric.
            RuntimeError: If ``scancel`` fails.
        """
        job_ids = list(dict.fromkeys(job_ids))
        if not all(re.fullmatch(r"[0-9]+", job_id) for job_id in job_ids):
            raise ValueError("Slurm job IDs must be numeric.")
        if not job_ids:
            return

        result = self.runner.run(
            "scancel " + " ".join(shlex.quote(job_id) for job_id in job_ids)
        )
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
