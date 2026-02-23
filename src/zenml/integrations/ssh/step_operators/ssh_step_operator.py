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
"""

import uuid
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, cast

from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import StackComponentType
from zenml.integrations.ssh.flavors import (
    SSHStepOperatorConfig,
    SSHStepOperatorSettings,
)
from zenml.integrations.ssh.remote_docker import (
    build_remote_wrapper_script,
    normalize_gpu_indices,
    serialize_env_for_docker_env_file,
)
from zenml.integrations.ssh.ssh_utils import (
    RemoteCommandResult,
    SSHClient,
    SSHConnectionConfig,
)
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineSnapshotBase

logger = get_logger(__name__)

SSH_STEP_OPERATOR_DOCKER_IMAGE_KEY = "ssh_step_operator"


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

    def launch(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Execute a step on the remote host via SSH + Docker.

        This method blocks until the remote container completes (or fails).

        Args:
            info: The step run information.
            entrypoint_command: The entrypoint command for the step.
            environment: Environment variables for the step container.

        Raises:
            RuntimeError: If the remote command fails.
        """
        settings = cast(SSHStepOperatorSettings, self.get_settings(info))
        image_name = info.get_image(key=SSH_STEP_OPERATOR_DOCKER_IMAGE_KEY)

        # Normalize GPU indices if specified
        gpu_indices: Optional[List[int]] = None
        if settings.gpu_indices is not None:
            gpu_indices = normalize_gpu_indices(settings.gpu_indices)

        # Generate unique paths for this step run
        run_id = str(uuid.uuid4())[:8]
        remote_workdir = self.config.remote_workdir
        env_file_path = f"{remote_workdir}/env-{run_id}"
        script_path = f"{remote_workdir}/run-{run_id}.sh"

        # Serialize environment to env-file format
        env_content = serialize_env_for_docker_env_file(environment)

        # Generate the wrapper script
        script_content = build_remote_wrapper_script(
            image=image_name,
            entrypoint_command=entrypoint_command,
            env_file_path=env_file_path,
            gpu_lock_dir=self.config.gpu_lock_dir,
            gpu_indices=gpu_indices,
            use_gpu_locks=settings.use_gpu_locks,
            docker_binary=self.config.docker_binary,
            extra_docker_run_args=settings.docker_run_args,
        )

        conn_config = self._build_ssh_connection_config()

        logger.info(
            "Connecting to %s:%d to execute step '%s' using image %s",
            self.config.hostname,
            self.config.port,
            info.pipeline_step_name,
            image_name,
        )
        if gpu_indices:
            logger.info(
                "GPU indices: %s (locking: %s)",
                gpu_indices,
                settings.use_gpu_locks,
            )

        with SSHClient(conn_config) as ssh:
            # Preflight: verify remote tools exist
            self._run_preflight_checks(ssh)

            # Create remote workdir
            ssh.exec(f"mkdir -p {remote_workdir}")

            # Upload env-file and wrapper script
            ssh.put_text(env_file_path, env_content, mode=0o600)
            ssh.put_text(script_path, script_content, mode=0o700)

            # Pull the Docker image
            logger.info("Pulling image %s on remote host...", image_name)
            pull_result = ssh.exec(
                f"{self.config.docker_binary} pull {image_name}",
                stream=True,
                get_pty=True,
                combine_stderr=True,
            )
            if pull_result.exit_code != 0:
                raise RuntimeError(
                    f"Failed to pull Docker image '{image_name}' on "
                    f"{self.config.hostname}. Check that the remote host "
                    "can reach the container registry and that credentials "
                    "are configured.\n"
                    f"Exit code: {pull_result.exit_code}"
                )

            # Execute the wrapper script (blocks until completion)
            logger.info("Running step '%s'...", info.pipeline_step_name)
            run_result = ssh.exec(
                f"bash {script_path}",
                stream=True,
                get_pty=True,
                combine_stderr=True,
            )

            if run_result.exit_code != 0:
                raise RuntimeError(
                    f"Step '{info.pipeline_step_name}' failed on remote "
                    f"host {self.config.hostname} with exit code "
                    f"{run_result.exit_code}. Check the logs above for "
                    "details."
                )

        logger.info(
            "Step '%s' completed successfully on %s.",
            info.pipeline_step_name,
            self.config.hostname,
        )
