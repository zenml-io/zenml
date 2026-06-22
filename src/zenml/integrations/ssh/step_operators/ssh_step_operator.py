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
"""SSH step operator implementation.

Runs ZenML step entrypoints inside Docker containers on a remote Linux
host accessed over SSH, with optional GPU selection.

Supports both the legacy blocking ``launch()`` path and the async
``submit()``/``get_status()``/``cancel()`` contract required for dynamic
pipelines (PR #4515). The container is started detached (``docker run -d``)
and its status is read back with ``docker inspect`` — the Docker daemon is
the single source of truth, so there is no remote helper script to babysit.
"""

import shlex
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, cast

from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.integrations.ssh.flavors import (
    SSHStepOperatorConfig,
    SSHStepOperatorSettings,
)
from zenml.integrations.ssh.remote_docker import (
    build_docker_gpus_flag,
    normalize_gpu_indices,
    serialize_env_for_docker_env_file,
)
from zenml.integrations.ssh.ssh_utils import (
    SSHClient,
    SSHConnectionConfig,
    resolve_ssh_connection_config,
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


class SSHStepOperator(BaseStepOperator):
    """Step operator that executes steps on a remote host via SSH + Docker.

    Connects to a remote Linux host over SSH, pulls the pre-built step
    image, and runs the step entrypoint inside a detached Docker container.
    Status is reported directly by the Docker daemon (``docker inspect``).
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
        """Build an SSHConnectionConfig from the component configuration.

        Returns:
            The SSH connection configuration.
        """
        return resolve_ssh_connection_config(self)

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
        ]
        for command, tool_name, help_text in checks:
            result = ssh.exec(command)
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
        """Submit a step for asynchronous execution on the remote host.

        Pulls the step image and starts a **detached** Docker container
        (``docker run -d``). The container name is recorded as step metadata
        so ``get_status``/``cancel`` can find it; status is read straight from
        the Docker daemon, so there is no remote helper script to babysit.
        Returns immediately once the container is started.

        Args:
            info: The step run information.
            entrypoint_command: The entrypoint command for the step.
            environment: Environment variables for the step container.

        Raises:
            RuntimeError: If the image pull or container start fails.
        """
        settings = cast(SSHStepOperatorSettings, self.get_settings(info))
        image_name = info.get_image(key=SSH_STEP_OPERATOR_DOCKER_IMAGE_KEY)

        gpu_indices: Optional[List[int]] = None
        if settings.gpu_indices is not None:
            gpu_indices = normalize_gpu_indices(settings.gpu_indices)

        step_run_id = str(info.step_run_id)
        container_name = f"zenml-step-{step_run_id}"[:128]
        remote_workdir = self.config.remote_workdir
        env_file_path = f"{remote_workdir}/env-{step_run_id}"
        env_content = serialize_env_for_docker_env_file(environment)
        docker = shlex.quote(self.config.docker_binary)

        run_command = self._build_docker_run_command(
            image=image_name,
            entrypoint_command=entrypoint_command,
            env_file_path=env_file_path,
            container_name=container_name,
            gpu_indices=gpu_indices,
            extra_docker_run_args=settings.docker_run_args,
        )

        conn_config = self._build_ssh_connection_config()
        logger.info(
            "Submitting step '%s' to %s:%d (image: %s, container: %s)",
            info.pipeline_step_name,
            conn_config.hostname,
            conn_config.port,
            image_name,
            container_name,
        )
        if gpu_indices:
            logger.info("GPU indices: %s", gpu_indices)

        with SSHClient(conn_config) as ssh:
            self._run_preflight_checks(ssh)
            ssh.exec(f"mkdir -p {shlex.quote(remote_workdir)}")
            ssh.put_text(env_file_path, env_content, mode=0o600)

            pull = ssh.exec(f"{docker} pull {shlex.quote(image_name)}")
            if pull.exit_code != 0:
                ssh.exec(f"rm -f {shlex.quote(env_file_path)}")
                raise RuntimeError(
                    f"Failed to pull image '{image_name}' on "
                    f"{conn_config.hostname}: {pull.stderr.strip()}"
                )

            result = ssh.exec(run_command)
            # Docker reads the env-file at container creation; delete it right
            # away so the step's secrets do not linger on the remote host.
            ssh.exec(f"rm -f {shlex.quote(env_file_path)}")
            if result.exit_code != 0:
                raise RuntimeError(
                    f"Failed to start container '{container_name}' on "
                    f"{conn_config.hostname}: {result.stderr.strip()}"
                )

        metadata: Dict[str, "MetadataType"] = {
            SSH_CONTAINER_NAME_METADATA_KEY: container_name,
        }
        publish_step_run_metadata(
            step_run_id=info.step_run_id,
            step_run_metadata={self.id: metadata},
        )
        # Mirror to in-memory for immediate access by wait().
        for key, value in metadata.items():
            info.step_run.run_metadata[key] = value

    def _build_docker_run_command(
        self,
        *,
        image: str,
        entrypoint_command: List[str],
        env_file_path: str,
        container_name: str,
        gpu_indices: Optional[List[int]],
        extra_docker_run_args: Optional[List[str]],
    ) -> str:
        """Build the detached ``docker run`` command for a step container.

        Args:
            image: Fully-qualified step image (with registry and tag).
            entrypoint_command: The ZenML step entrypoint argv.
            env_file_path: Remote path to the env-file holding the step env.
            container_name: Deterministic container name.
            gpu_indices: Normalized GPU indices to attach, or None for CPU.
            extra_docker_run_args: Optional extra ``docker run`` arguments.

        Returns:
            The full ``docker run -d`` command string to run over SSH.
        """
        parts: List[str] = [
            shlex.quote(self.config.docker_binary),
            "run",
            "-d",
            "--name",
            shlex.quote(container_name),
            "--env-file",
            shlex.quote(env_file_path),
        ]
        if gpu_indices:
            # The flag value carries its own quotes and is interpreted by the
            # remote shell, e.g. --gpus "device=0,1".
            parts += ["--gpus", build_docker_gpus_flag(gpu_indices)]
        if extra_docker_run_args:
            parts += [shlex.quote(arg) for arg in extra_docker_run_args]
        parts.append(shlex.quote(image))
        parts += [shlex.quote(arg) for arg in entrypoint_command]
        return " ".join(parts)

    def get_status(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Get the execution status of a submitted step.

        Reads the container state with ``docker inspect`` on the remote host.
        The Docker daemon is the source of truth, so a step can never appear
        perpetually "running" after its container has exited.

        Args:
            step_run: The step run to check.

        Returns:
            The current execution status.
        """
        container_name = step_run.run_metadata.get(
            SSH_CONTAINER_NAME_METADATA_KEY
        )
        if container_name is None:
            logger.warning(
                "No SSH container recorded for step run %s; reporting FAILED.",
                step_run.id,
            )
            return ExecutionStatus.FAILED

        docker = shlex.quote(self.config.docker_binary)
        name = shlex.quote(str(container_name))
        conn_config = self._build_ssh_connection_config()
        with SSHClient(conn_config) as ssh:
            result = ssh.exec(
                f"{docker} inspect --format "
                f"'{{{{.State.Status}}}} {{{{.State.ExitCode}}}}' {name}"
            )
            if result.exit_code != 0:
                # The container is gone (never created, or pruned). Without it
                # we cannot prove success, so report FAILED; wait() falls back
                # to the server-side run status.
                logger.debug(
                    "docker inspect failed for container %s: %s",
                    container_name,
                    result.stderr.strip(),
                )
                return ExecutionStatus.FAILED

            state, _, exit_code = result.stdout.strip().partition(" ")
            if state in ("running", "created", "restarting", "paused"):
                return ExecutionStatus.RUNNING
            if state == "exited" and exit_code.strip() == "0":
                return ExecutionStatus.COMPLETED
            return ExecutionStatus.FAILED

    def cancel(self, step_run: "StepRunResponse") -> None:
        """Cancel a submitted step by stopping its Docker container.

        Args:
            step_run: The step run to cancel.
        """
        container_name = step_run.run_metadata.get(
            SSH_CONTAINER_NAME_METADATA_KEY
        )
        if container_name is None:
            logger.debug(
                "No SSH container recorded for step run %s; nothing to cancel.",
                step_run.id,
            )
            return

        docker = shlex.quote(self.config.docker_binary)
        name = shlex.quote(str(container_name))
        conn_config = self._build_ssh_connection_config()
        try:
            with SSHClient(conn_config) as ssh:
                ssh.exec(f"{docker} stop {name}")
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
