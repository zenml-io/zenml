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
"""SSH orchestrator implementation."""

import os
import shlex
import signal
import subprocess
import threading
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Type,
    cast,
)
from uuid import UUID

import yaml

from zenml.config.base_settings import BaseSettings
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.enums import ExecutionMode, ExecutionStatus, StackComponentType
from zenml.integrations.ssh.flavors.ssh_orchestrator_flavor import (
    SSHOrchestratorConfig,
    SSHOrchestratorSettings,
)
from zenml.integrations.ssh.ssh_client import SSHClient
from zenml.integrations.ssh.utils import (
    build_compose_gpu_deploy,
    build_docker_run_command,
    build_mount_mappings,
    prepare_remote_workdir,
)
from zenml.logger import get_logger
from zenml.orchestrators import ContainerizedOrchestrator, SubmissionResult
from zenml.orchestrators import utils as orchestrator_utils
from zenml.stack import StackValidator
from zenml.step_operators.step_operator_entrypoint_configuration import (
    StepOperatorEntrypointConfiguration,
)

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import (
        PipelineRunResponse,
        PipelineSnapshotResponse,
        StepRunResponse,
    )
    from zenml.stack import Stack

logger = get_logger(__name__)

ENV_ZENML_SSH_RUN_ID = "ZENML_SSH_ORCHESTRATOR_RUN_ID"


class SSHOrchestrator(ContainerizedOrchestrator):
    """Orchestrator that runs pipelines on a remote host via SSH + Docker."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the SSH orchestrator.

        Args:
            *args: Forwarded to the base orchestrator.
            **kwargs: Forwarded to the base orchestrator.
        """
        super().__init__(*args, **kwargs)
        # Isolated-step subprocesses keyed by step_run_id. Only populated
        # inside the remote orchestrator container (dynamic path); the lock
        # guards concurrent submit/poll/stop from the dynamic runner's
        # thread pool.
        self._step_procs: Dict[UUID, "subprocess.Popen[bytes]"] = {}
        self._stopped_step_ids: set[UUID] = set()
        self._step_procs_lock = threading.Lock()

    @property
    def config(self) -> SSHOrchestratorConfig:
        """The orchestrator config.

        Returns:
            The orchestrator config.
        """
        return cast(SSHOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the SSH orchestrator.

        Returns:
            The settings class.
        """
        return SSHOrchestratorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack can run containerized pipelines.

        Returns:
            A stack validator requiring a container registry and image
            builder.
        """
        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            }
        )

    @property
    def supported_execution_modes(self) -> List[ExecutionMode]:
        """Execution modes supported by this orchestrator.

        Returns:
            The supported execution modes.
        """
        return [
            ExecutionMode.FAIL_FAST,
            ExecutionMode.STOP_ON_FAILURE,
            ExecutionMode.CONTINUE_ON_FAILURE,
        ]

    def get_orchestrator_run_id(self) -> str:
        """The run id, read from the execution environment.

        Returns:
            The orchestrator run id.

        Raises:
            RuntimeError: If called outside the remote execution environment
                (the env var is only set inside the launched containers).
        """
        try:
            return os.environ[ENV_ZENML_SSH_RUN_ID]
        except KeyError:
            raise RuntimeError(
                f"Unable to read run id: environment variable "
                f"{ENV_ZENML_SSH_RUN_ID} is not set. This is only available "
                "inside the remote execution environment."
            )

    def _remote_run_directory(self, run_id: str) -> str:
        """Get the remote run directory for a pipeline launch.

        Args:
            run_id: The orchestrator run id.

        Returns:
            The remote directory for the launch files.
        """
        return f"{self.config.remote_workdir}/pipeline-runs/{run_id}"

    def _prepare_remote_dir(
        self, ssh: SSHClient, remote_dir: str, stack: "Stack"
    ) -> None:
        """Run preflight checks and prepare the remote run directory.

        Args:
            ssh: The open SSH connection.
            remote_dir: The remote directory for this launch.
            stack: The stack used for this submission.
        """
        cleanup_command = None
        if self.config.cleanup_old_files:
            runs_dir = f"{self.config.remote_workdir}/pipeline-runs"
            cleanup_command = (
                f"find {shlex.quote(runs_dir)} -type d "
                "-ctime +7 -exec rm -rf {} +"
            )
        prepare_remote_workdir(
            ssh=ssh,
            docker_binary=self.config.docker_binary,
            workdir=remote_dir,
            minimum_free_disk_gb=self.config.minimum_free_disk_gb,
            cleanup_command=cleanup_command,
            container_registry=(
                stack.container_registry
                if self.config.authenticate_docker
                else None
            ),
        )

    def _launch_compose(
        self,
        *,
        run_id: str,
        compose: Dict[str, Any],
        stack: "Stack",
    ) -> None:
        """Write and run a Compose file on the remote host.

        Args:
            run_id: The orchestrator run id (used as the remote directory).
            compose: The Compose definition.
            stack: The stack used for this submission.

        Raises:
            RuntimeError: If a remote command fails.
        """
        remote_dir = self._remote_run_directory(run_id)
        compose_yaml = yaml.dump(
            compose, default_flow_style=False, sort_keys=False
        )
        docker = self.config.docker_binary

        with SSHClient(self.config) as ssh:
            self._prepare_remote_dir(ssh, remote_dir, stack)
            ssh.put_text(f"{remote_dir}/docker-compose.yml", compose_yaml)
            up = ssh.exec(
                f"cd {shlex.quote(remote_dir)} && "
                f"{shlex.quote(docker)} compose up -d"
            )
            if up.exit_code != 0:
                raise RuntimeError(
                    f"`docker compose up` failed on "
                    f"{self.config.hostname}: {up.stderr or up.stdout}"
                )
        logger.info(
            "Submitted pipeline to %s (remote compose dir: %s).",
            self.config.hostname,
            remote_dir,
        )

    def _launch_container(
        self,
        *,
        run_id: str,
        image: str,
        entrypoint: List[str],
        command: List[str],
        environment: Dict[str, str],
        stack: "Stack",
        settings: SSHOrchestratorSettings,
    ) -> None:
        """Launch a single detached container on the remote host via docker run.

        Args:
            run_id: The orchestrator run id (used as the remote directory).
            image: The orchestrator image to run.
            entrypoint: The container entrypoint command.
            command: Arguments passed to the entrypoint.
            environment: Environment variables for the container.
            stack: The stack used for this submission.
            settings: The orchestrator settings for this submission.

        Raises:
            RuntimeError: If a remote command fails.
        """
        remote_dir = self._remote_run_directory(run_id)
        container_name = f"{run_id}-orchestrator"
        env_file = f"{remote_dir}/orchestrator.env"

        # Isolated steps run as subprocesses inside this container, so it
        # carries the GPU access and bind mounts on behalf of all of them.
        run_command = build_docker_run_command(
            docker_binary=self.config.docker_binary,
            image=image,
            args=list(entrypoint[1:]) + list(command),
            container_name=container_name,
            env_file=env_file,
            network="host",
            entrypoint=entrypoint[0],
            gpu_indices=settings.gpu_indices,
            mounts=settings.mounts,
            extra_args=settings.docker_run_args,
        )

        with SSHClient(self.config) as ssh:
            self._prepare_remote_dir(ssh, remote_dir, stack)
            # docker --env-file reads literal KEY=VALUE lines; keep the file
            # private since it carries the ZenML store credentials.
            env_lines = "".join(
                f"{key}={value}\n" for key, value in environment.items()
            )
            ssh.put_text(env_file, env_lines, mode=0o600)
            run = ssh.exec(run_command)
            if run.exit_code != 0:
                raise RuntimeError(
                    f"`docker run` failed on {self.config.hostname}: "
                    f"{run.stderr or run.stdout}"
                )
            # docker has read the --env-file at container start, so remove it
            # immediately: it carries the ZenML store API token and must not
            # be left on the remote host.
            ssh.exec(f"rm -f {shlex.quote(env_file)}")
        logger.info(
            "Submitted dynamic pipeline to %s (container: %s).",
            self.config.hostname,
            container_name,
        )

    def _step_service(
        self,
        snapshot: "PipelineSnapshotResponse",
        step_name: str,
        step: "Step",
        run_id: str,
        step_environment: Dict[str, str],
    ) -> Dict[str, Any]:
        """Build the Compose service for a single static-pipeline step.

        Args:
            snapshot: The pipeline snapshot.
            step_name: The step (invocation) name.
            step: The step configuration.
            run_id: The orchestrator run id.
            step_environment: The step's environment variables.

        Returns:
            A Compose service definition.
        """
        settings = cast(SSHOrchestratorSettings, self.get_settings(step))
        env = dict(step_environment)
        env[ENV_ZENML_SSH_RUN_ID] = run_id

        service: Dict[str, Any] = {
            "image": self.get_image(snapshot=snapshot, step_name=step_name),
            "container_name": f"{snapshot.id}-{step_name}",
            "network_mode": "host",
            "entrypoint": StepEntrypointConfiguration.get_entrypoint_command(),
            "command": StepEntrypointConfiguration.get_entrypoint_arguments(
                step_name=step_name, snapshot_id=snapshot.id
            ),
            "environment": env,
        }

        volumes = build_mount_mappings(settings.mounts)
        if volumes:
            service["volumes"] = volumes
        if settings.gpu_indices:
            service["deploy"] = build_compose_gpu_deploy(settings.gpu_indices)
        if step.spec.upstream_steps:
            service["depends_on"] = {
                f"{snapshot.id}-{upstream}": {
                    "condition": "service_completed_successfully"
                }
                for upstream in step.spec.upstream_steps
            }
        return service

    def submit_pipeline(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        base_environment: Dict[str, str],
        step_environments: Dict[str, Dict[str, str]],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submit a static pipeline as a remote Docker Compose DAG.

        Args:
            snapshot: The pipeline snapshot.
            stack: The active stack.
            base_environment: Environment shared by all steps (unused; the
                per-step environments already include it).
            step_environments: Per-step environment variables.
            placeholder_run: The placeholder run for the pipeline.

        Returns:
            None

        Raises:
            RuntimeError: If the pipeline has a schedule, which is not
                supported.
        """
        if snapshot.schedule:
            raise RuntimeError(
                "The SSH orchestrator does not support scheduled pipelines. "
                "Remove the schedule and trigger the pipeline directly (e.g. "
                "from your own cron job or CI), or use an orchestrator that "
                "supports scheduling."
            )
        assert placeholder_run is not None
        run_id = str(placeholder_run.id)
        services = {
            f"{snapshot.id}-{step_name}": self._step_service(
                snapshot=snapshot,
                step_name=step_name,
                step=step,
                run_id=run_id,
                step_environment=step_environments[step_name],
            )
            for step_name, step in snapshot.step_configurations.items()
        }
        self._launch_compose(
            run_id=run_id,
            compose={"services": services},
            stack=stack,
        )
        return None

    def submit_dynamic_pipeline(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submit a dynamic pipeline by launching the orchestrator image.

        Args:
            snapshot: The pipeline snapshot.
            stack: The active stack.
            environment: Environment variables for the orchestrator
                container.
            placeholder_run: The placeholder run for the pipeline.

        Returns:
            None

        Raises:
            RuntimeError: If the dynamic pipeline has a schedule, which is not
                supported.
        """
        from zenml.pipelines.dynamic.entrypoint_configuration import (
            DynamicPipelineEntrypointConfiguration,
        )

        if snapshot.schedule:
            raise RuntimeError(
                "The SSH orchestrator does not support scheduled pipelines. "
                "Remove the schedule and trigger the pipeline directly (e.g. "
                "from your own cron job or CI), or use an orchestrator that "
                "supports scheduling."
            )

        assert placeholder_run is not None

        run_id = str(placeholder_run.id)
        env = dict(environment)
        env[ENV_ZENML_SSH_RUN_ID] = run_id
        settings = cast(SSHOrchestratorSettings, self.get_settings(snapshot))
        self._launch_container(
            run_id=run_id,
            image=self.get_image(snapshot=snapshot),
            settings=settings,
            entrypoint=(
                DynamicPipelineEntrypointConfiguration.get_entrypoint_command()
            ),
            command=(
                DynamicPipelineEntrypointConfiguration.get_entrypoint_arguments(
                    snapshot_id=snapshot.id,
                    run_id=run_id,
                )
            ),
            environment=env,
            stack=stack,
        )
        return None

    def submit_isolated_step(
        self, step_run_info: "StepRunInfo", environment: Dict[str, str]
    ) -> None:
        """Launch one isolated step as a subprocess.

        Args:
            step_run_info: The step run information.
            environment: Environment variables for the step process.
        """
        command, args = orchestrator_utils.get_step_entrypoint_command(
            invocation_id=step_run_info.pipeline_step_name,
            config=step_run_info.config,
            entrypoint_config_class=StepOperatorEntrypointConfiguration,
            snapshot_id=step_run_info.snapshot.id,
            step_run_id=str(step_run_info.step_run_id),
        )
        logger.info(
            "Launching isolated step `%s` as a subprocess.",
            step_run_info.pipeline_step_name,
        )
        # start_new_session puts the child in its own process group so
        # stop_isolated_step can signal the whole subtree.
        process = subprocess.Popen(
            command + args,
            env={**os.environ, **environment},
            start_new_session=True,
        )
        with self._step_procs_lock:
            self._step_procs[step_run_info.step_run_id] = process
            self._stopped_step_ids.discard(step_run_info.step_run_id)

    def get_isolated_step_status(
        self, step_run: "StepRunResponse"
    ) -> ExecutionStatus:
        """Report the status of an isolated step subprocess.

        Args:
            step_run: The step run to check.

        Returns:
            The execution status.
        """
        with self._step_procs_lock:
            process = self._step_procs.get(step_run.id)
            stopped = step_run.id in self._stopped_step_ids
        if process is None:
            return ExecutionStatus.RUNNING
        return_code = process.poll()
        if return_code is None:
            return ExecutionStatus.RUNNING
        if stopped:
            return ExecutionStatus.STOPPED
        if return_code == 0:
            return ExecutionStatus.COMPLETED
        return ExecutionStatus.FAILED

    def stop_isolated_step(self, step_run: "StepRunResponse") -> None:
        """Terminate an isolated step subprocess (preemption / fail-fast).

        Args:
            step_run: The step run to stop.
        """
        with self._step_procs_lock:
            process = self._step_procs.get(step_run.id)
            if process is None or process.poll() is not None:
                return
            self._stopped_step_ids.add(step_run.id)
        try:
            pgid = os.getpgid(process.pid)
        except ProcessLookupError:
            return
        os.killpg(pgid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(pgid, signal.SIGKILL)
            process.wait()
