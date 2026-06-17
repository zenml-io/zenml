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
"""SSH orchestrator implementation.

Runs ZenML pipelines on a remote Linux host over SSH + Docker Compose.

Two execution paths:

* **Static pipelines** — one Compose service per step, wired together with
  ``depends_on`` (``service_completed_successfully``); the remote
  ``docker compose up`` runs the whole DAG. This mirrors the legacy HyperAI
  orchestrator.
* **Dynamic pipelines** — a single Compose service launches the *orchestrator
  image*, which runs ZenML's dynamic runner. That runner calls back into
  :meth:`SSHOrchestrator.submit_isolated_step`, which launches each isolated
  step as a **subprocess** (not a thread) so individual steps can be
  independently resource-accounted and preempted (resource pools).
"""

import os
import re
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
from zenml.integrations.ssh.ssh_utils import SSHClient, SSHConnectionConfig
from zenml.logger import get_logger
from zenml.orchestrators import ContainerizedOrchestrator, SubmissionResult
from zenml.orchestrators import utils as orchestrator_utils
from zenml.stack import StackValidator
from zenml.step_operators.step_operator_entrypoint_configuration import (
    StepOperatorEntrypointConfiguration,
)

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import (
        PipelineRunResponse,
        PipelineSnapshotResponse,
        StepRunResponse,
    )
    from zenml.stack import Stack

logger = get_logger(__name__)

ENV_ZENML_SSH_RUN_ID = "ZENML_SSH_ORCHESTRATOR_RUN_ID"

# Compose service GPU reservation: request all NVIDIA GPUs for the container.
_NVIDIA_GPU_DEPLOY = {
    "resources": {
        "reservations": {
            "devices": [{"driver": "nvidia", "capabilities": ["gpu"]}]
        }
    }
}

# Allow only absolute POSIX/Windows paths in bind mounts so settings can't
# inject extra Compose/shell tokens.
_MOUNT_PATH_PATTERN = re.compile(r"^(/[^:\n]*|[A-Za-z]:\\[^:\n]*)$")


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

    def supported_execution_modes(self) -> List[ExecutionMode]:
        """Execution modes supported by this orchestrator.

        Returns:
            The supported execution modes. Isolated steps run as separate
            processes that ``stop_isolated_step`` can terminate, so all
            modes (including fail-fast) are supported.
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

    # ------------------------------------------------------------------
    # SSH / Compose launch (client side)
    # ------------------------------------------------------------------

    def _build_ssh_connection_config(self) -> SSHConnectionConfig:
        """Build an SSHConnectionConfig from the orchestrator config.

        Returns:
            The SSH connection configuration.
        """
        private_key: Optional[str] = None
        if self.config.ssh_private_key is not None:
            private_key = self.config.ssh_private_key.get_secret_value()

        passphrase: Optional[str] = None
        if self.config.ssh_key_passphrase is not None:
            passphrase = self.config.ssh_key_passphrase.get_secret_value()

        return SSHConnectionConfig(
            hostname=self.config.hostname,
            port=self.config.port,
            username=self.config.username,
            ssh_key_path=self.config.ssh_key_path,
            ssh_private_key=private_key,
            ssh_key_passphrase=passphrase,
            verify_host_key=self.config.verify_host_key,
            known_hosts_path=self.config.known_hosts_path,
            connection_timeout=self.config.connection_timeout,
            keepalive_interval=self.config.keepalive_interval,
        )

    @staticmethod
    def _validate_mount_path(path: str) -> str:
        """Validate a bind-mount path against injection.

        Args:
            path: The host or container path.

        Returns:
            The validated path.

        Raises:
            RuntimeError: If the path is not a plain absolute path.
        """
        if not _MOUNT_PATH_PATTERN.match(path):
            raise RuntimeError(
                f"Invalid mount path {path!r}: only absolute POSIX or "
                "Windows paths without ':' are allowed."
            )
        return path

    def _gpu_enabled(self) -> bool:
        """Whether GPU reservations should be added to services.

        Returns:
            The configured GPU flag.
        """
        return self.config.gpu_enabled_in_container

    def _docker_login(self, ssh: SSHClient) -> None:
        """Log the remote Docker into the active container registry.

        Args:
            ssh: The open SSH connection.

        Raises:
            RuntimeError: If the remote `docker login` fails.
        """
        from zenml.client import Client

        registry = Client().active_stack.container_registry
        if registry is None or not registry.credentials:
            return
        username, password = registry.credentials
        docker = self.config.docker_binary
        # --password-stdin avoids the password in argv; echo still exposes it
        # in the remote process list briefly, which the registry owner
        # accepts by opting into autologin.
        command = (
            f"echo {shlex.quote(password)} | "
            f"{shlex.quote(docker)} login -u {shlex.quote(username)} "
            f"--password-stdin {shlex.quote(registry.config.uri)}"
        )
        result = ssh.exec(command)
        if result.exit_code != 0:
            raise RuntimeError(
                f"`docker login` failed on {self.config.hostname}: "
                f"{result.stderr or result.stdout}"
            )

    def _launch_compose(self, run_id: str, compose: Dict[str, Any]) -> None:
        """Write and run a Compose file on the remote host.

        Args:
            run_id: The orchestrator run id (used as the remote directory).
            compose: The Compose definition.

        Raises:
            RuntimeError: If a remote command fails.
        """
        conn = self._build_ssh_connection_config()
        remote_dir = f"{self.config.remote_workdir}/{run_id}"
        compose_yaml = yaml.dump(
            compose, default_flow_style=False, sort_keys=False
        )
        docker = self.config.docker_binary

        with SSHClient(conn) as ssh:
            mkdir = ssh.exec(f"mkdir -p {shlex.quote(remote_dir)}")
            if mkdir.exit_code != 0:
                raise RuntimeError(
                    f"Failed to create remote directory {remote_dir} on "
                    f"{self.config.hostname}: {mkdir.stderr}"
                )
            ssh.put_text(f"{remote_dir}/docker-compose.yml", compose_yaml)
            if self.config.container_registry_autologin:
                self._docker_login(ssh)
            up = ssh.exec(
                f"cd {shlex.quote(remote_dir)} && "
                f"{shlex.quote(docker)} compose up -d"
            )
            if up.exit_code != 0:
                raise RuntimeError(
                    f"`docker compose up` failed on {self.config.hostname}: "
                    f"{up.stderr or up.stdout}"
                )
        logger.info(
            "Submitted pipeline to %s (remote compose dir: %s).",
            self.config.hostname,
            remote_dir,
        )

    def _step_service(
        self,
        snapshot: "PipelineSnapshotResponse",
        step_name: str,
        step: Any,
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

        volumes = [
            f"{self._validate_mount_path(host)}:"
            f"{self._validate_mount_path(container)}"
            for host, container in settings.mounts_from_to.items()
        ]
        if volumes:
            service["volumes"] = volumes
        if settings.gpu_enabled_in_container:
            service["deploy"] = _NVIDIA_GPU_DEPLOY
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
            ``None`` (submit-only; the remote DAG runs detached).
        """
        run_id = (
            str(placeholder_run.id) if placeholder_run else str(snapshot.id)
        )
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
        self._launch_compose(run_id, {"services": services})
        return None

    def submit_dynamic_pipeline(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submit a dynamic pipeline by launching the orchestrator image.

        A single Compose service runs the orchestrator image with the
        dynamic-pipeline entrypoint. That container runs ZenML's dynamic
        runner, which calls back into :meth:`submit_isolated_step` for each
        isolated step.

        Args:
            snapshot: The pipeline snapshot.
            stack: The active stack.
            environment: Environment variables for the orchestrator
                container.
            placeholder_run: The placeholder run for the pipeline.

        Returns:
            ``None`` (submit-only; the orchestrator container runs detached).
        """
        from zenml.pipelines.dynamic.entrypoint_configuration import (
            DynamicPipelineEntrypointConfiguration,
        )

        run_id = (
            str(placeholder_run.id) if placeholder_run else str(snapshot.id)
        )
        env = dict(environment)
        env[ENV_ZENML_SSH_RUN_ID] = run_id

        service: Dict[str, Any] = {
            "image": self.get_image(snapshot=snapshot),
            "container_name": f"{snapshot.id}-orchestrator",
            "network_mode": "host",
            "entrypoint": (
                DynamicPipelineEntrypointConfiguration.get_entrypoint_command()
            ),
            "command": (
                DynamicPipelineEntrypointConfiguration.get_entrypoint_arguments(
                    snapshot_id=snapshot.id,
                    run_id=placeholder_run.id if placeholder_run else None,
                )
            ),
            "environment": env,
        }
        # Isolated steps run as subprocesses inside this container, so it
        # needs GPU access on behalf of all of them.
        if self._gpu_enabled():
            service["deploy"] = _NVIDIA_GPU_DEPLOY

        self._launch_compose(run_id, {"services": {"orchestrator": service}})
        return None

    # ------------------------------------------------------------------
    # Isolated steps (runs inside the remote orchestrator container)
    # ------------------------------------------------------------------

    def submit_isolated_step(
        self, step_run_info: "StepRunInfo", environment: Dict[str, str]
    ) -> None:
        """Launch one isolated step as a subprocess.

        Runs inside the remote orchestrator container. A subprocess (not a
        thread) is used so the step is an independently killable OS process
        — required for resource-pool preemption and fail-fast.

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

    def get_isolated_step_status(
        self, step_run: "StepRunResponse"
    ) -> ExecutionStatus:
        """Report the status of an isolated step subprocess.

        Args:
            step_run: The step run to check.

        Returns:
            The execution status. Returns ``RUNNING`` for steps this
            instance didn't launch (e.g. after a restart) so the base wait
            loop falls back to the server-reported status.
        """
        with self._step_procs_lock:
            process = self._step_procs.get(step_run.id)
        if process is None:
            return ExecutionStatus.RUNNING
        return_code = process.poll()
        if return_code is None:
            return ExecutionStatus.RUNNING
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
        try:
            pgid = os.getpgid(process.pid)
        except ProcessLookupError:
            return
        os.killpg(pgid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(pgid, signal.SIGKILL)
