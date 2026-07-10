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

The step's ZenML Docker image is run on the compute node with a rootless HPC
container runtime (Apptainer/Singularity by default, or NVIDIA Pyxis, or the
Docker daemon where available), so code delivery uses ZenML's standard image
build - no code is shipped by the operator. Submission goes over SSH to a
login node, or via a local ``sbatch`` when the client already runs on the
cluster.

Submission is stateless: the Slurm job is named after the step run id, so
status lookups and cancellation work by job name without persisting job ids.
While a job is in the queue, its state comes from ``squeue``; once it leaves
the queue, a sentinel exit-code file written by the job script disambiguates
success from failure, so Slurm accounting (``sacct``) is never required.

Security: the environment file holds the step's credentials (ZenML store
token, etc.). It is written owner-only (0600) into a per-run directory created
owner-only (0700), passed to the container via ``--env-file`` /
``--container-env`` so the values never appear on a command line visible to
other cluster users, and deleted by the job's EXIT trap the moment the job
ends - even if the orchestrator process dies.
"""

import shlex
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, cast
from uuid import UUID

from zenml.config.base_settings import BaseSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.integrations.slurm.flavors.slurm_step_operator_flavor import (
    SlurmContainerRuntime,
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
from zenml.integrations.ssh.utils import serialize_env_for_docker_env_file
from zenml.logger import get_logger
from zenml.stack import StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineSnapshotBase, StepRunResponse
    from zenml.stack import Stack

logger = get_logger(__name__)

SLURM_STEP_OPERATOR_DOCKER_IMAGE_KEY = "slurm_step_operator"

_JOB_NAME_PREFIX = "zenml"
_EXIT_CODE_FILE = "exit_code"
_ENV_FILE = "env"
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

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validate that the stack meets the operator's requirements.

        The operator runs the step's Docker image on the cluster, so it needs
        a remote container registry and image builder (to build and pull the
        image) and a remote artifact store (the cluster reads inputs and
        writes outputs there).

        Returns:
            A stack validator.
        """

        def _validate_remote_components(
            stack: "Stack",
        ) -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The Slurm step operator runs steps on a remote cluster "
                    "that must read inputs and write outputs to a shared "
                    "artifact store, but the artifact store "
                    f"'{stack.artifact_store.name}' is local. Please use a "
                    "remote artifact store (S3, GCS, Azure Blob, etc.)."
                )

            container_registry = stack.container_registry
            assert container_registry is not None
            if container_registry.config.is_local:
                return False, (
                    "The Slurm step operator runs the step's image on a "
                    "remote cluster, which must pull it from a registry, but "
                    f"the container registry '{container_registry.name}' is "
                    "local. Please use a remote container registry (ECR, GCR, "
                    "ACR, DockerHub, etc.)."
                )
            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_remote_components,
        )

    def get_docker_builds(
        self, snapshot: "PipelineSnapshotBase"
    ) -> List["BuildConfiguration"]:
        """Declare the Docker builds for steps using this operator.

        Args:
            snapshot: The pipeline snapshot.

        Returns:
            One build configuration per step that uses this step operator.
        """
        builds = []
        for step_name, step in snapshot.step_configurations.items():
            if step.config.uses_step_operator(self.name):
                builds.append(
                    BuildConfiguration(
                        key=SLURM_STEP_OPERATOR_DOCKER_IMAGE_KEY,
                        settings=step.config.docker_settings,
                        step_name=step_name,
                    )
                )
        return builds

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

    def _build_container_command(
        self,
        image: str,
        entrypoint_command: List[str],
        env_file: str,
        env_keys: List[str],
        use_gpu: bool,
        settings: SlurmStepOperatorSettings,
    ) -> str:
        """Build the shell snippet that runs the step image on the node.

        Secrets are passed only via the env file (or, for pyxis, via
        ``--container-env`` variable names whose values are sourced from the
        0600 env file), never on the command line.

        Args:
            image: Fully-qualified image reference to run.
            entrypoint_command: The ZenML entrypoint command.
            env_file: Path to the owner-only environment file on the cluster.
            env_keys: Names of the environment variables (for pyxis).
            use_gpu: Whether the step requested GPUs.
            settings: The resolved step settings (mounts, extra run args).

        Returns:
            A shell snippet that runs the container in the foreground.
        """
        entrypoint = " ".join(shlex.quote(p) for p in entrypoint_command)
        extra = " ".join(shlex.quote(a) for a in settings.container_run_args)
        runtime = self.config.container_runtime

        if runtime in (
            SlurmContainerRuntime.APPTAINER,
            SlurmContainerRuntime.SINGULARITY,
        ):
            binary = runtime.value  # "apptainer" or "singularity"
            parts = [binary, "exec"]
            if use_gpu:
                parts.append("--nv")
            parts += ["--env-file", shlex.quote(env_file)]
            for host, container in settings.container_mounts.items():
                parts += ["--bind", shlex.quote(f"{host}:{container}")]
            if extra:
                parts.append(extra)
            parts.append(shlex.quote(f"docker://{image}"))
            return f"{' '.join(parts)} {entrypoint}"

        if runtime == SlurmContainerRuntime.DOCKER:
            parts = ["docker", "run", "--rm"]
            if use_gpu:
                parts += ["--gpus", "all"]
            parts += ["--env-file", shlex.quote(env_file)]
            for host, container in settings.container_mounts.items():
                parts += ["-v", shlex.quote(f"{host}:{container}")]
            if extra:
                parts.append(extra)
            parts.append(shlex.quote(image))
            return f"{' '.join(parts)} {entrypoint}"

        # Pyxis / enroot via srun. `--container-env` takes variable *names*;
        # the values are sourced from the 0600 env file into the job shell,
        # so they are not exposed on the command line.
        srun = ["srun", f"--container-image={shlex.quote(image)}"]
        if settings.container_mounts:
            mounts = ",".join(
                f"{host}:{container}"
                for host, container in settings.container_mounts.items()
            )
            srun.append(f"--container-mounts={shlex.quote(mounts)}")
        if env_keys:
            srun.append(f"--container-env={','.join(env_keys)}")
        if extra:
            srun.append(extra)
        source_env = f"set -a\nsource {shlex.quote(env_file)}\nset +a\n"
        return f"{source_env}{' '.join(srun)} {entrypoint}"

    def _build_sbatch_script(
        self,
        info: "StepRunInfo",
        container_command: str,
        run_dir: str,
    ) -> str:
        """Render the sbatch job script for a step.

        Args:
            info: Information about the step run.
            container_command: The shell snippet that runs the step container.
            run_dir: The per-run staging directory on the cluster.

        Returns:
            The job script content.
        """
        settings = cast(SlurmStepOperatorSettings, self.get_settings(info))
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

        # The EXIT trap records the job outcome in a sentinel file that
        # `get_status` reads after the job leaves the queue (so no dependency
        # on Slurm accounting) and scrubs the credential-bearing env file, so
        # secrets never outlive the job even if the orchestrator dies.
        # `set -e` aborts the job (with the failing code captured) if the
        # container runtime itself fails.
        return f"""#!/bin/bash
{chr(10).join(directives)}

trap 'ec=$?; echo "$ec" > {run_dir}/{_EXIT_CODE_FILE}; rm -f {run_dir}/{_ENV_FILE}' EXIT
set -eo pipefail

{container_command}
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

        Raises:
            RuntimeError: If the run directory cannot be created on the
                cluster.
        """
        image = info.get_image(key=SLURM_STEP_OPERATOR_DOCKER_IMAGE_KEY)
        run_dir = self._run_dir(info.step_run_id)
        env_file = f"{run_dir}/{_ENV_FILE}"
        settings = cast(SlurmStepOperatorSettings, self.get_settings(info))
        use_gpu = bool(info.config.resource_settings.gpu_count)

        env_content = serialize_env_for_docker_env_file(environment)
        container_command = self._build_container_command(
            image=image,
            entrypoint_command=entrypoint_command,
            env_file=env_file,
            env_keys=sorted(environment),
            use_gpu=use_gpu,
            settings=settings,
        )
        script = self._build_sbatch_script(
            info=info, container_command=container_command, run_dir=run_dir
        )

        client, runner = self._get_client()
        try:
            # Create the run directory owner-only: it holds the env file (with
            # credentials), the job script, and the job output. `-m 700` sets
            # the mode atomically on creation, so there is no window where the
            # directory is readable by other cluster users before a chmod.
            result = runner.run(f"mkdir -m 700 -p {shlex.quote(run_dir)}")
            if result.exit_code != 0:
                raise RuntimeError(
                    f"Failed to create run directory `{run_dir}` on the "
                    f"cluster: {result.stderr.strip()}"
                )

            runner.put_text(env_file, env_content, mode=0o600)
            script_path = f"{run_dir}/job.sh"
            runner.put_text(script_path, script, mode=0o700)

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

    def cleanup_step_submission(self, step_run: "StepRunResponse") -> None:
        """Remove the per-run directory after the step has finished.

        The credential-bearing env file is already scrubbed by the job's EXIT
        trap; this removes the remaining job script, output and sentinel.

        Args:
            step_run: The finished step run.
        """
        run_dir = self._run_dir(step_run.id)
        client, runner = self._get_client()
        try:
            runner.run(f"rm -rf {shlex.quote(run_dir)}")
        except Exception as e:
            logger.warning(
                "Failed to clean up Slurm run directory `%s`: %s", run_dir, e
            )
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
