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

The Slurm job ID is persisted as step-run metadata for exact status lookups and
cancellation. Once a job leaves the queue, a sentinel exit-code file written by
the job script disambiguates success from failure without requiring Slurm
accounting (``sacct``).
"""

import shlex
from typing import TYPE_CHECKING, Dict, List, Optional, cast
from uuid import UUID

from zenml.config.base_settings import BaseSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import ExecutionStatus
from zenml.integrations.slurm.flavors.slurm_step_operator_flavor import (
    SlurmStepOperatorConfig,
    SlurmStepOperatorSettings,
)
from zenml.integrations.slurm.slurm_client import (
    PENDING_STATES,
    RUNNING_STATES,
    SlurmCommandRunner,
    build_slurm_client,
)
from zenml.integrations.slurm.slurm_job import (
    CANCELLED_FILE,
    DOCKER_CONFIG_DIR,
    ENROOT_CONFIG_DIR,
    ENV_FILE,
    EXIT_CODE_FILE,
    OUTPUT_FILE,
    REGISTRY_AUTH_FILE,
    REQUIRED_COMPONENTS,
    build_container_command,
    build_registry_auth,
    build_sbatch_script,
    serialize_environment,
    stage_and_submit,
    validate_remote_stack,
)
from zenml.logger import get_logger
from zenml.orchestrators.publish_utils import publish_step_run_metadata
from zenml.stack import StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.metadata.metadata_types import MetadataType
    from zenml.models import PipelineSnapshotBase, StepRunResponse

logger = get_logger(__name__)

SLURM_STEP_OPERATOR_DOCKER_IMAGE_KEY = "slurm_step_operator"
SLURM_JOB_ID_METADATA_KEY = "slurm_job_id"
SLURM_STATE_METADATA_KEY = "slurm_state"

_JOB_NAME_PREFIX = "zenml"


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

        Returns:
            A stack validator.
        """
        return StackValidator(
            required_components=REQUIRED_COMPONENTS,
            custom_validation_function=validate_remote_stack,
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
            Exception: Re-raised after cancelling the job and cleaning up
                staged credentials if submission or metadata publication fails.
        """
        image = info.get_image(key=SLURM_STEP_OPERATOR_DOCKER_IMAGE_KEY)
        run_dir = self._run_dir(info.step_run_id)
        env_file = f"{run_dir}/{ENV_FILE}"
        settings = cast(SlurmStepOperatorSettings, self.get_settings(info))
        use_gpu = bool(info.config.resource_settings.gpu_count)

        env_content = serialize_environment(
            environment, runtime=self.config.container_runtime
        )
        from zenml.client import Client

        container_registry = Client().active_stack.container_registry
        assert container_registry is not None
        registry_auth = build_registry_auth(
            runtime=self.config.container_runtime,
            run_dir=run_dir,
            registry_uri=container_registry.config.uri,
            credentials=container_registry.credentials,
        )
        container_command = build_container_command(
            runtime=self.config.container_runtime,
            image=image,
            entrypoint_command=entrypoint_command,
            env_file=env_file,
            env_keys=sorted(environment),
            use_gpu=use_gpu,
            settings=settings,
            registry_auth=registry_auth,
        )
        script = build_sbatch_script(
            job_name=self._job_name(info.step_run_id),
            run_dir=run_dir,
            container_command=container_command,
            resources=info.config.resource_settings,
            settings=settings,
            sensitive_paths=registry_auth.sensitive_paths,
        )

        client = build_slurm_client(self.config)
        job_id: Optional[str] = None
        try:
            job_id = stage_and_submit(
                client,
                run_dir,
                env_content,
                script,
                extra_files=registry_auth.files,
            )
            metadata: Dict[str, "MetadataType"] = {
                SLURM_JOB_ID_METADATA_KEY: job_id
            }
            publish_step_run_metadata(
                step_run_id=info.step_run_id,
                step_run_metadata={self.id: metadata},
            )
            info.step_run.run_metadata.update(metadata)
            logger.info(
                "Submitted step `%s` as Slurm job `%s` (job name `%s`).",
                info.pipeline_step_name,
                job_id,
                self._job_name(info.step_run_id),
            )
        except Exception:
            if job_id is not None:
                try:
                    client.cancel(job_id)
                except Exception:
                    logger.warning(
                        "Failed to cancel Slurm job `%s` after step metadata "
                        "publication failed.",
                        job_id,
                    )
                self._cleanup_sensitive_files(client.runner, run_dir)
            raise
        finally:
            client.runner.close()

    def get_status(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Get the status of a step run from the Slurm queue.

        Args:
            step_run: The step run to get the status of.

        Returns:
            The execution status of the step run.
        """
        job_id = step_run.run_metadata.get(SLURM_JOB_ID_METADATA_KEY)
        if job_id is None:
            logger.warning(
                "No Slurm job ID recorded for step `%s`.", step_run.id
            )
            return ExecutionStatus.FAILED
        run_dir = self._run_dir(step_run.id)
        client = build_slurm_client(self.config)
        runner = client.runner
        try:
            state = client.get_job_state(str(job_id))
            if state in PENDING_STATES:
                return ExecutionStatus.QUEUED
            if state in RUNNING_STATES:
                return ExecutionStatus.RUNNING
            if state == "COMPLETED":
                return ExecutionStatus.COMPLETED
            if state is not None:
                # Cancellation and failure states can linger in the queue
                # output briefly before the job is purged from it.
                self._publish_terminal_state(step_run, state)
                if state.startswith("CANCEL"):
                    return ExecutionStatus.CANCELLED
                return ExecutionStatus.FAILED

            # The job is no longer queued: the sentinel file written by the
            # job script's EXIT trap holds the outcome.
            try:
                runner.read_text(f"{run_dir}/{CANCELLED_FILE}")
            except Exception:
                pass
            else:
                return ExecutionStatus.CANCELLED

            try:
                exit_code = runner.read_text(
                    f"{run_dir}/{EXIT_CODE_FILE}"
                ).strip()
            except Exception:
                logger.warning(
                    "Slurm job `%s` for step `%s` is no longer known to "
                    "Slurm and did not write an exit-code sentinel.",
                    job_id,
                    step_run.id,
                )
                return ExecutionStatus.FAILED

            if exit_code == "0":
                return ExecutionStatus.COMPLETED

            self._log_failure_output(runner, run_dir)
            return ExecutionStatus.FAILED
        finally:
            runner.close()

    def _publish_terminal_state(
        self, step_run: "StepRunResponse", state: str
    ) -> None:
        """Record the raw Slurm terminal state as step metadata.

        A scheduler-level kill (``TIMEOUT``, ``NODE_FAIL``,
        ``OUT_OF_MEMORY``, ``PREEMPTED``) never runs the job's EXIT trap,
        so the sentinel-based status collapses it into a plain failure.
        The raw state is the only signal that distinguishes an
        infrastructure kill from a step that ran and exited non-zero.

        Args:
            step_run: The step run the state belongs to.
            state: The Slurm terminal state as reported by the queue.
        """
        if SLURM_STATE_METADATA_KEY in step_run.run_metadata:
            return
        try:
            publish_step_run_metadata(
                step_run_id=step_run.id,
                step_run_metadata={self.id: {SLURM_STATE_METADATA_KEY: state}},
            )
        except Exception as e:
            logger.warning(
                "Failed to publish Slurm terminal state `%s` for step "
                "`%s`: %s",
                state,
                step_run.id,
                e,
            )

    def cancel(self, step_run: "StepRunResponse") -> None:
        """Cancel the Slurm job of a step run.

        Args:
            step_run: The step run to cancel.
        """
        client = build_slurm_client(self.config)
        try:
            job_id = step_run.run_metadata.get(SLURM_JOB_ID_METADATA_KEY)
            if job_id is None:
                logger.warning(
                    "No Slurm job ID recorded for step `%s`.", step_run.id
                )
                return
            client.cancel(str(job_id))
            run_dir = self._run_dir(step_run.id)
            client.runner.put_text(
                f"{run_dir}/{CANCELLED_FILE}", "1\n", mode=0o600
            )
            self._cleanup_sensitive_files(client.runner, run_dir)
        finally:
            client.runner.close()

    def cleanup_step_submission(self, step_run: "StepRunResponse") -> None:
        """Remove the per-run directory after the step has finished.

        The credential-bearing env file is already scrubbed by the job's EXIT
        trap; this removes the remaining job script, output and sentinel.

        Args:
            step_run: The finished step run.
        """
        run_dir = self._run_dir(step_run.id)
        client = build_slurm_client(self.config)
        try:
            client.runner.run(f"rm -rf -- {shlex.quote(run_dir)}")
        except Exception as e:
            logger.warning(
                "Failed to clean up Slurm run directory `%s`: %s", run_dir, e
            )
        finally:
            client.runner.close()

    def _log_failure_output(
        self, runner: SlurmCommandRunner, run_dir: str
    ) -> None:
        """Log the tail of a failed job's output file.

        Args:
            runner: The command runner to read the output with.
            run_dir: The per-run staging directory on the cluster.
        """
        result = runner.run(f"tail -n 50 {shlex.quote(run_dir)}/{OUTPUT_FILE}")
        if result.exit_code == 0 and result.stdout.strip():
            logger.error(
                "Tail of the failed Slurm job output:\n%s", result.stdout
            )

    @staticmethod
    def _cleanup_sensitive_files(
        runner: SlurmCommandRunner, run_dir: str
    ) -> None:
        """Remove credential-bearing files for a submitted step.

        Args:
            runner: Command runner used to remove the files.
            run_dir: Per-step staging directory.
        """
        paths = [
            f"{run_dir}/{ENV_FILE}",
            f"{run_dir}/{REGISTRY_AUTH_FILE}",
            f"{run_dir}/{DOCKER_CONFIG_DIR}",
            f"{run_dir}/{ENROOT_CONFIG_DIR}",
        ]
        runner.run(
            "rm -rf -- " + " ".join(shlex.quote(path) for path in paths)
        )
