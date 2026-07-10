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
"""Step operator that runs individual steps as Slurm jobs.

The operator is container-free: Slurm compute nodes generally cannot run
Docker, so the step executes inside a user-provided Python environment on the
cluster (``env_setup_command``). Pipeline code is shipped at submission time
as an archive that the job script unpacks into a per-run directory, so no
image build and no artifact-store code upload are required.

Submission is stateless: the Slurm job is named after the step run id, so
status lookups and cancellation work by job name without persisting job ids.
While a job is in the queue, its state comes from ``squeue``; once it leaves
the queue, a sentinel exit-code file written by the job script disambiguates
success from failure, so Slurm accounting (``sacct``) is never required.
"""

import shlex
import tempfile
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, cast
from uuid import UUID

from zenml.config.base_settings import BaseSettings
from zenml.enums import ExecutionStatus
from zenml.integrations.slurm.flavors.slurm_step_operator_flavor import (
    SlurmStepOperatorConfig,
    SlurmStepOperatorSettings,
    SlurmTransport,
)
from zenml.integrations.slurm.slurm_client import (
    PENDING_STATES,
    RUNNING_STATES,
    LocalSlurmCommandRunner,
    SlurmClient,
    SlurmCommandRunner,
    SSHSlurmCommandRunner,
)
from zenml.logger import get_logger
from zenml.step_operators import BaseStepOperator
from zenml.utils import code_utils, source_utils

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import StepRunResponse

logger = get_logger(__name__)

_JOB_NAME_PREFIX = "zenml"
_EXIT_CODE_FILE = "exit_code"
_OUTPUT_FILE = "output.log"


class SlurmStepOperator(BaseStepOperator):
    """Step operator that submits steps as Slurm batch jobs."""

    @property
    def config(self) -> SlurmStepOperatorConfig:
        """Returns the config of this step operator.

        Returns:
            The config.
        """
        return cast(SlurmStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[type[BaseSettings]]:
        """Settings class for this step operator.

        Returns:
            The settings class.
        """
        return SlurmStepOperatorSettings

    def _get_client(self) -> Tuple[SlurmClient, SlurmCommandRunner]:
        """Build a Slurm client for the configured transport.

        Returns:
            The Slurm client and its underlying runner (which the caller is
            responsible for closing).
        """
        runner: SlurmCommandRunner
        if self.config.transport == SlurmTransport.LOCAL:
            runner = LocalSlurmCommandRunner()
        else:
            runner = SSHSlurmCommandRunner(self.config)
        return SlurmClient(runner), runner

    @staticmethod
    def _job_name(step_run_id: UUID) -> str:
        """Deterministic Slurm job name for a step run.

        Args:
            step_run_id: The step run id.

        Returns:
            The Slurm job name.
        """
        return f"{_JOB_NAME_PREFIX}-{step_run_id}"

    def _run_dir(self, step_run_id: UUID) -> str:
        """Per-run staging directory on the cluster.

        Args:
            step_run_id: The step run id.

        Returns:
            The absolute path of the run directory.
        """
        return (
            f"{self.config.workdir.rstrip('/')}/{self._job_name(step_run_id)}"
        )

    def _build_sbatch_script(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
        run_dir: str,
    ) -> str:
        """Render the sbatch job script for a step.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables to set for the step.
            run_dir: The per-run staging directory on the cluster.

        Returns:
            The job script content.
        """
        settings = cast(
            SlurmStepOperatorSettings, self.get_settings(info.step_run)
        )
        resources = info.config.resource_settings

        directives = [
            f"#SBATCH --job-name={self._job_name(info.step_run_id)}",
            f"#SBATCH --output={run_dir}/{_OUTPUT_FILE}",
        ]
        if settings.partition:
            directives.append(f"#SBATCH --partition={settings.partition}")
        if settings.time_limit:
            directives.append(f"#SBATCH --time={settings.time_limit}")
        if settings.account:
            directives.append(f"#SBATCH --account={settings.account}")
        if settings.qos:
            directives.append(f"#SBATCH --qos={settings.qos}")
        if resources.cpu_count:
            directives.append(
                f"#SBATCH --cpus-per-task={int(resources.cpu_count)}"
            )
        if memory_gb := resources.get_memory(unit="GB"):
            directives.append(f"#SBATCH --mem={int(memory_gb)}G")
        if resources.gpu_count:
            directives.append(f"#SBATCH --gres=gpu:{resources.gpu_count}")
        for directive in settings.extra_sbatch_directives:
            directives.append(f"#SBATCH {directive}")

        env_exports = "\n".join(
            f"export {key}={shlex.quote(value)}"
            for key, value in sorted(environment.items())
        )
        command = " ".join(shlex.quote(part) for part in entrypoint_command)

        # The EXIT trap records the job outcome in a sentinel file that
        # `get_status` reads after the job leaves the squeue output, so the
        # operator never depends on Slurm accounting being configured.
        # `set -e` makes environment setup or code extraction failures abort
        # the job (with the failing code captured by the trap) rather than
        # falling through to run the step in a broken environment.
        return f"""#!/bin/bash
{chr(10).join(directives)}

trap 'echo $? > {run_dir}/{_EXIT_CODE_FILE}' EXIT
set -eo pipefail

{self.config.env_setup_command}

{env_exports}

mkdir -p {run_dir}/code
tar -xzf {run_dir}/code.tar.gz -C {run_dir}/code
cd {run_dir}/code
export PYTHONPATH="{run_dir}/code:${{PYTHONPATH:-}}"

{command}
"""

    def submit(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Submit a step as a Slurm batch job and return immediately.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables to set in the step operator
                environment.
        """
        run_dir = self._run_dir(info.step_run_id)
        client, runner = self._get_client()
        try:
            # The run directory holds the code archive, the job script (which
            # contains credentials as env exports) and the job output, so it
            # is created private to the submitting user.
            result = runner.run(
                f"mkdir -p {shlex.quote(run_dir)} "
                f"&& chmod 700 {shlex.quote(run_dir)}"
            )
            if result.exit_code != 0:
                raise RuntimeError(
                    f"Failed to create run directory `{run_dir}` on the "
                    f"cluster: {result.stderr.strip()}"
                )

            with tempfile.NamedTemporaryFile(suffix=".tar.gz") as archive:
                code_archive = code_utils.CodeArchive(
                    root=source_utils.get_source_root()
                )
                code_archive.write_archive(archive)
                archive.flush()
                runner.put_file(archive.name, f"{run_dir}/code.tar.gz")

            script = self._build_sbatch_script(
                info=info,
                entrypoint_command=entrypoint_command,
                environment=environment,
                run_dir=run_dir,
            )
            script_path = f"{run_dir}/job.sh"
            runner.put_text(script, script_path)

            job_id = client.submit(script_path)
            logger.info(
                "Submitted step `%s` as Slurm job `%s` (job name `%s`).",
                info.pipeline_step_name,
                job_id,
                self._job_name(info.step_run_id),
            )
        finally:
            runner.close()

    def get_status(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Get the status of a step run from the Slurm queue.

        Args:
            step_run: The step run to get the status of.

        Returns:
            The execution status of the step run.
        """
        job_name = self._job_name(step_run.id)
        run_dir = self._run_dir(step_run.id)
        client, runner = self._get_client()
        try:
            state = client.get_job_state(job_name)
            if state in PENDING_STATES:
                return ExecutionStatus.QUEUED
            if state in RUNNING_STATES:
                return ExecutionStatus.RUNNING
            if state is not None:
                # Cancellation and failure states can linger in the queue
                # output briefly before the job is purged from it.
                if state.startswith("CANCEL"):
                    return ExecutionStatus.CANCELLED
                return ExecutionStatus.FAILED

            # The job is no longer queued: the sentinel file written by the
            # job script's EXIT trap holds the outcome.
            try:
                exit_code = runner.read_text(
                    f"{run_dir}/{_EXIT_CODE_FILE}"
                ).strip()
            except Exception:
                # No queue entry and no sentinel: the job was cancelled
                # before its trap could run, or never started.
                return ExecutionStatus.CANCELLED

            if exit_code == "0":
                return ExecutionStatus.COMPLETED

            self._log_failure_output(runner, run_dir)
            return ExecutionStatus.FAILED
        finally:
            runner.close()

    def cancel(self, step_run: "StepRunResponse") -> None:
        """Cancel the Slurm job of a step run.

        Args:
            step_run: The step run to cancel.
        """
        client, runner = self._get_client()
        try:
            client.cancel(self._job_name(step_run.id))
        finally:
            runner.close()

    def _log_failure_output(
        self, runner: SlurmCommandRunner, run_dir: str
    ) -> None:
        """Log the tail of a failed job's output file.

        Args:
            runner: The command runner to read the output with.
            run_dir: The per-run staging directory on the cluster.
        """
        result = runner.run(
            f"tail -n 50 {shlex.quote(run_dir)}/{_OUTPUT_FILE}"
        )
        if result.exit_code == 0 and result.stdout.strip():
            logger.error(
                "Tail of the failed Slurm job output:\n%s", result.stdout
            )
