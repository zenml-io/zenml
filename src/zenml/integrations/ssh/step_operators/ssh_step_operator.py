#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""SSH step operator implementation.

Runs ZenML step entrypoints inside Docker containers on a remote Linux
host accessed over SSH, with optional GPU selection and per-GPU mutual
exclusion via flock.

Supports both the legacy blocking ``launch()`` path and the async
``submit()``/``get_status()``/``cancel()`` contract required for dynamic
pipelines (PR #4515).
"""

import json
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, cast

from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.integrations.ssh.flavors import (
    SSHStepOperatorConfig,
    SSHStepOperatorSettings,
)
from zenml.integrations.ssh.remote_docker import (
    build_remote_supervisor_script,
    normalize_gpu_indices,
    serialize_env_for_docker_env_file,
)
from zenml.integrations.ssh.ssh_utils import (
    RemoteCommandResult,
    SSHClient,
    SSHConnectionConfig,
)
from zenml.logger import get_logger
from zenml.orchestrators.publish_utils import publish_step_run_metadata
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_run_info import StepRunInfo
    from zenml.metadata.metadata_types import MetadataType
    from zenml.models import PipelineSnapshotBase, StepRunResponse

logger = get_logger(__name__)

SSH_STEP_OPERATOR_DOCKER_IMAGE_KEY = "ssh_step_operator"

SSH_CONTAINER_NAME_METADATA_KEY = "ssh_container_name"
SSH_STATUS_FILE_METADATA_KEY = "ssh_status_file"
SSH_CANCEL_FILE_METADATA_KEY = "ssh_cancel_file"


class SSHStepOperator(BaseStepOperator):
    """Step operator that executes steps on a remote host via SSH + Docker.

    Connects to a remote Linux host over SSH, pulls the pre-built step
    image, and runs the step entrypoint inside a Docker container.  When
    GPU indices are specified, per-GPU flock locks prevent overlapping
    access to the same physical GPU.
    """

    @property
    def config(self) -> SSHStepOperatorConfig:
        """Get the SSH step operator configuration.

        Returns:
            The SSH step operator configuration.
        """
        return cast(SSHStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Get the settings class for the SSH step operator.

        Returns:
            The SSH step operator settings class.
        """
        return SSHStepOperatorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validate that the stack meets remote execution requirements.

        The SSH step operator needs:
        - A container registry (to push/pull step images)
        - An image builder (to build step images)
        - A remote artifact store (the container cannot access local files)
        - A remote container registry (the remote host must be able to pull)

        Returns:
            A stack validator.
        """

        def _validate_remote_components(
            stack: "Stack",
        ) -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The SSH step operator runs code on a remote host and "
                    "needs to read/write artifacts, but the artifact store "
                    f"'{stack.artifact_store.name}' is local. Please use a "
                    "remote artifact store (S3, GCS, Azure Blob, etc.)."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The SSH step operator runs code on a remote host and "
                    "needs to pull Docker images, but the container registry "
                    f"'{container_registry.name}' is local. Please use a "
                    "remote container registry (ECR, GCR, ACR, DockerHub, "
                    "etc.)."
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
        """Declare Docker builds needed for steps using this operator.

        Args:
            snapshot: The pipeline snapshot.

        Returns:
            A list of Docker build configurations, one per step that uses
            this step operator.
        """
        builds = []
        for step_name, step in snapshot.step_configurations.items():
            if step.config.uses_step_operator(self.name):
                build = BuildConfiguration(
                    key=SSH_STEP_OPERATOR_DOCKER_IMAGE_KEY,
                    settings=step.config.docker_settings,
                    step_name=step_name,
                )
                builds.append(build)
        return builds

    def _build_ssh_connection_config(self) -> SSHConnectionConfig:
        """Build an SSHConnectionConfig from the operator's config.

        Returns:
            The SSH connection configuration.
        """
        # Resolve PlainSerializedSecretStr values to plain strings
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

    def _run_preflight_checks(self, ssh: SSHClient) -> None:
        """Verify the remote host has the required tools installed.

        Args:
            ssh: An active SSH client.

        Raises:
            RuntimeError: If a required tool is missing.
        """
        checks = [
            (
                f"{self.config.docker_binary} --version",
                "Docker",
                "Install Docker on the remote host: "
                "https://docs.docker.com/engine/install/",
            ),
            (
                "command -v flock",
                "flock",
                "Install flock (part of util-linux) on the remote host.",
            ),
        ]
        for command, tool_name, help_text in checks:
            result: RemoteCommandResult = ssh.exec(command)
            if result.exit_code != 0:
                raise RuntimeError(
                    f"Preflight check failed: {tool_name} is not available "
                    f"on {self.config.hostname}. {help_text}\n"
                    f"Command: {command}\n"
                    f"stderr: {result.stderr.strip()}"
                )
            logger.debug(
                "Preflight OK: %s → %s",
                tool_name,
                result.stdout.strip(),
            )

    def submit(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Submit a step for async execution on the remote host.

        Uploads a supervisor script and launches it in the background via
        ``nohup``.  The supervisor handles image pulling, GPU lock
        acquisition, container lifecycle, and status reporting through a
        JSON status file on the remote host.

        Returns immediately after the supervisor is started.

        Args:
            info: The step run information.
            entrypoint_command: The entrypoint command for the step.
            environment: Environment variables for the step container.

        Raises:
            RuntimeError: If the supervisor script fails to start.
        """
        settings = cast(SSHStepOperatorSettings, self.get_settings(info))
        image_name = info.get_image(key=SSH_STEP_OPERATOR_DOCKER_IMAGE_KEY)

        gpu_indices: Optional[List[int]] = None
        if settings.gpu_indices is not None:
            gpu_indices = normalize_gpu_indices(settings.gpu_indices)

        # Deterministic identifiers derived from step_run_id.
        step_run_id = str(info.step_run_id)
        container_name = f"zenml-step-{step_run_id}"[:128]
        remote_workdir = self.config.remote_workdir
        env_file_path = f"{remote_workdir}/env-{step_run_id}"
        script_path = f"{remote_workdir}/supervise-{step_run_id}.sh"
        status_file_path = f"{remote_workdir}/status-{step_run_id}.json"
        cancel_file_path = f"{remote_workdir}/cancel-{step_run_id}"
        log_file_path = f"{remote_workdir}/supervise-{step_run_id}.log"

        env_content = serialize_env_for_docker_env_file(environment)

        script_content = build_remote_supervisor_script(
            image=image_name,
            entrypoint_command=entrypoint_command,
            env_file_path=env_file_path,
            status_file_path=status_file_path,
            cancel_file_path=cancel_file_path,
            container_name=container_name,
            gpu_lock_dir=self.config.gpu_lock_dir,
            gpu_indices=gpu_indices,
            use_gpu_locks=settings.use_gpu_locks,
            docker_binary=self.config.docker_binary,
            extra_docker_run_args=settings.docker_run_args,
        )

        conn_config = self._build_ssh_connection_config()

        logger.info(
            "Submitting step '%s' to %s:%d (image: %s, container: %s)",
            info.pipeline_step_name,
            self.config.hostname,
            self.config.port,
            image_name,
            container_name,
        )
        if gpu_indices:
            logger.info(
                "GPU indices: %s (locking: %s)",
                gpu_indices,
                settings.use_gpu_locks,
            )

        with SSHClient(conn_config) as ssh:
            self._run_preflight_checks(ssh)
            ssh.exec(f"mkdir -p {remote_workdir}")
            ssh.put_text(env_file_path, env_content, mode=0o600)
            ssh.put_text(script_path, script_content, mode=0o700)

            # Launch supervisor in background; capture PID for diagnostics.
            result = ssh.exec(
                f"nohup bash {script_path} > {log_file_path} 2>&1 "
                "< /dev/null & echo $!"
            )
            if result.exit_code != 0:
                raise RuntimeError(
                    f"Failed to start supervisor script on "
                    f"{self.config.hostname}: {result.stderr.strip()}"
                )
            supervisor_pid = result.stdout.strip()
            logger.info(
                "Supervisor started (PID %s) for step '%s' on %s.",
                supervisor_pid,
                info.pipeline_step_name,
                self.config.hostname,
            )

        # Persist metadata for get_status/cancel to recover job identity.
        metadata: Dict[str, "MetadataType"] = {
            SSH_CONTAINER_NAME_METADATA_KEY: container_name,
            SSH_STATUS_FILE_METADATA_KEY: status_file_path,
            SSH_CANCEL_FILE_METADATA_KEY: cancel_file_path,
        }
        publish_step_run_metadata(
            step_run_id=info.step_run_id,
            step_run_metadata={self.id: metadata},
        )
        # Mirror to in-memory for immediate access by wait().
        for key, value in metadata.items():
            info.step_run.run_metadata[key] = value

    def get_status(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Get the execution status of a submitted step.

        Reads the JSON status file written by the remote supervisor script.
        Falls back to ``docker inspect`` if the status file is unavailable.

        Args:
            step_run: The step run to check.

        Returns:
            The current execution status.
        """
        status_file = str(step_run.run_metadata[SSH_STATUS_FILE_METADATA_KEY])
        container_name = str(
            step_run.run_metadata[SSH_CONTAINER_NAME_METADATA_KEY]
        )

        conn_config = self._build_ssh_connection_config()
        with SSHClient(conn_config) as ssh:
            # Primary: read status file written by supervisor.
            try:
                content = ssh.read_text(status_file)
                data = json.loads(content)
                state = data.get("state", "")
                return self._map_state_to_status(state)
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                pass

            # Fallback: query Docker directly.
            result = ssh.exec(
                f"{self.config.docker_binary} inspect "
                f"--format '{{{{.State.Status}}}}' {container_name}"
            )
            if result.exit_code == 0:
                docker_state = result.stdout.strip().strip("'")
                if docker_state == "running":
                    return ExecutionStatus.RUNNING
                if docker_state == "exited":
                    exit_code_result = ssh.exec(
                        f"{self.config.docker_binary} inspect "
                        f"--format '{{{{.State.ExitCode}}}}' "
                        f"{container_name}"
                    )
                    if (
                        exit_code_result.exit_code == 0
                        and exit_code_result.stdout.strip().strip("'") == "0"
                    ):
                        return ExecutionStatus.COMPLETED
                    return ExecutionStatus.FAILED

        return ExecutionStatus.FAILED

    def cancel(self, step_run: "StepRunResponse") -> None:
        """Cancel a submitted step by stopping its Docker container.

        Writes a cancel marker file (so the supervisor records the
        correct final state) and then issues ``docker stop``.

        Args:
            step_run: The step run to cancel.
        """
        container_name = str(
            step_run.run_metadata[SSH_CONTAINER_NAME_METADATA_KEY]
        )
        cancel_file = str(step_run.run_metadata[SSH_CANCEL_FILE_METADATA_KEY])

        conn_config = self._build_ssh_connection_config()
        try:
            with SSHClient(conn_config) as ssh:
                ssh.exec(f"touch {cancel_file}")
                ssh.exec(f"{self.config.docker_binary} stop {container_name}")
        except Exception:
            logger.debug(
                "Best-effort cancel failed for container %s.",
                container_name,
                exc_info=True,
            )

    def launch(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Execute a step on the remote host (blocking legacy path).

        Delegates to ``submit()`` + ``wait()`` to reuse the async
        infrastructure while preserving the blocking call semantics
        expected by static pipelines.

        Args:
            info: The step run information.
            entrypoint_command: The entrypoint command for the step.
            environment: Environment variables for the step container.

        Raises:
            RuntimeError: If the step fails.
        """
        self.submit(info, entrypoint_command, environment)
        status = self.wait(info.step_run)
        if not status.is_successful:
            try:
                self.cancel(info.step_run)
            except Exception:
                logger.debug("Failed to cancel SSH step.", exc_info=True)
            raise RuntimeError(
                f"Step '{info.pipeline_step_name}' failed on remote host "
                f"{self.config.hostname} with status: {status}"
            )
        logger.info(
            "Step '%s' completed successfully on %s.",
            info.pipeline_step_name,
            self.config.hostname,
        )

    @staticmethod
    def _map_state_to_status(state: str) -> ExecutionStatus:
        """Map a supervisor state string to an ExecutionStatus.

        Args:
            state: One of "running", "completed", "failed", "stopped".

        Returns:
            The corresponding ExecutionStatus.
        """
        mapping = {
            "running": ExecutionStatus.RUNNING,
            "completed": ExecutionStatus.COMPLETED,
            "failed": ExecutionStatus.FAILED,
            "stopped": ExecutionStatus.FAILED,
        }
        return mapping.get(state, ExecutionStatus.RUNNING)
