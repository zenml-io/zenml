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
"""SSH step operator implementation."""

import shlex
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, cast

from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.integrations.ssh.flavors import (
    SSHStepOperatorConfig,
    SSHStepOperatorSettings,
)
from zenml.integrations.ssh.ssh_client import SSHClient
from zenml.integrations.ssh.utils import (
    build_docker_run_command,
    prepare_remote_workdir,
    serialize_env_for_docker_env_file,
)
from zenml.logger import get_logger
from zenml.orchestrators.publish_utils import publish_step_run_metadata
from zenml.stack import StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_run_info import StepRunInfo
    from zenml.metadata.metadata_types import MetadataType
    from zenml.models import PipelineSnapshotBase, StepRunResponse
    from zenml.stack import Stack

logger = get_logger(__name__)

SSH_STEP_OPERATOR_DOCKER_IMAGE_KEY = "ssh_step_operator"

SSH_CONTAINER_NAME_METADATA_KEY = "ssh_container_name"


class SSHStepOperator(BaseStepOperator):
    """Step operator that executes steps on a remote host via SSH + Docker."""

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

    def submit(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Submit a step for asynchronous execution on the remote host.

        Args:
            info: The step run information.
            entrypoint_command: The entrypoint command for the step.
            environment: Environment variables for the step container.

        Raises:
            RuntimeError: If the image pull or container start fails.
        """
        settings = cast(SSHStepOperatorSettings, self.get_settings(info))
        image_name = info.get_image(key=SSH_STEP_OPERATOR_DOCKER_IMAGE_KEY)

        step_run_id = str(info.step_run_id)
        container_name = f"zenml-step-{step_run_id}"[:128]
        remote_workdir = self.config.remote_workdir
        env_file_path = f"{remote_workdir}/env-{step_run_id}"
        env_content = serialize_env_for_docker_env_file(environment)
        docker = shlex.quote(self.config.docker_binary)

        run_command = build_docker_run_command(
            docker_binary=self.config.docker_binary,
            image=image_name,
            args=entrypoint_command,
            container_name=container_name,
            env_file=env_file_path,
            gpu_indices=settings.gpu_indices,
            mounts=settings.mounts,
            extra_args=settings.docker_run_args,
        )

        logger.info(
            "Submitting step '%s' to %s:%d (image: %s, container: %s)",
            info.pipeline_step_name,
            self.config.hostname,
            self.config.port,
            image_name,
            container_name,
        )
        if settings.gpu_indices:
            logger.info("GPU indices: %s", settings.gpu_indices)

        cleanup_command = None
        if self.config.cleanup_old_files:
            cleanup_command = (
                f"find {shlex.quote(remote_workdir)} -maxdepth 1 "
                "-name 'env-*' -ctime +7 -delete"
            )
        container_registry = None
        if self.config.authenticate_docker:
            from zenml.client import Client

            container_registry = Client().active_stack.container_registry

        with SSHClient(self.config) as ssh:
            prepare_remote_workdir(
                ssh=ssh,
                docker_binary=self.config.docker_binary,
                workdir=remote_workdir,
                minimum_free_disk_gb=self.config.minimum_free_disk_gb,
                cleanup_command=cleanup_command,
                container_registry=container_registry,
            )
            ssh.put_text(env_file_path, env_content, mode=0o600)

            pull = ssh.exec(f"{docker} pull {shlex.quote(image_name)}")
            if pull.exit_code != 0:
                ssh.exec(f"rm -f {shlex.quote(env_file_path)}")
                raise RuntimeError(
                    f"Failed to pull image '{image_name}' on "
                    f"{self.config.hostname}: {pull.stderr.strip()}"
                )

            result = ssh.exec(run_command)
            # Docker reads the env-file at container creation; delete it right
            # away so the step's secrets do not linger on the remote host.
            ssh.exec(f"rm -f {shlex.quote(env_file_path)}")
            if result.exit_code != 0:
                raise RuntimeError(
                    f"Failed to start container '{container_name}' on "
                    f"{self.config.hostname}: {result.stderr.strip()}"
                )

        metadata: Dict[str, "MetadataType"] = {
            SSH_CONTAINER_NAME_METADATA_KEY: container_name,
        }
        publish_step_run_metadata(
            step_run_id=info.step_run_id,
            step_run_metadata={self.id: metadata},
        )
        info.step_run.run_metadata.update(metadata)

    def get_status(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Get the execution status of a submitted step.

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
                "No container name recorded for step `%s`", step_run.name
            )
            return ExecutionStatus.FAILED

        docker = shlex.quote(self.config.docker_binary)
        name = shlex.quote(str(container_name))
        with SSHClient(self.config) as ssh:
            result = ssh.exec(
                f"{docker} inspect --format "
                f"'{{{{.State.Status}}}} {{{{.State.ExitCode}}}}' {name}"
            )
            if result.exit_code != 0:
                # The container is gone (never created, or pruned). Without it
                # we cannot prove success, so report FAILED
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
            logger.warning(
                "No container name recorded for step `%s`", step_run.name
            )
            return

        docker = shlex.quote(self.config.docker_binary)
        name = shlex.quote(str(container_name))
        try:
            with SSHClient(self.config) as ssh:
                ssh.exec(f"{docker} stop {name}")
        except Exception:
            logger.warning(
                "Canceling container %s for step `%s` failed.",
                container_name,
                step_run.name,
            )
