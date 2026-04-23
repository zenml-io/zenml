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
"""Implementation of the Modal orchestrator."""

import os
import time
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, cast
from uuid import uuid4

import modal

from zenml.config.resource_settings import ByteUnit
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.enums import ExecutionMode, StackComponentType
from zenml.integrations.modal.flavors import (
    ModalOrchestratorConfig,
    ModalOrchestratorSettings,
)
from zenml.integrations.modal.utils import (
    build_registry_image,
    build_registry_secret,
    get_gpu_values,
)
from zenml.logger import get_logger
from zenml.orchestrators import ContainerizedOrchestrator, SubmissionResult
from zenml.stack import Stack, StackValidator
from zenml.utils import string_utils

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_configurations import Step
    from zenml.models import PipelineRunResponse, PipelineSnapshotResponse

logger = get_logger(__name__)

ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID = "ZENML_MODAL_ORCHESTRATOR_RUN_ID"


class ModalOrchestrator(ContainerizedOrchestrator):
    """Orchestrator that runs each pipeline step as a Modal sandbox."""

    @property
    def config(self) -> ModalOrchestratorConfig:
        """Returns the ``ModalOrchestratorConfig``.

        Returns:
            The configuration.
        """
        return cast(ModalOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Modal orchestrator.

        Returns:
            The settings class.
        """
        return ModalOrchestratorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack supports remote execution on Modal.

        Returns:
            A ``StackValidator`` that requires a container registry, an image
            builder, and rejects local artifact stores / container registries.
        """

        def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The Modal orchestrator runs steps remotely and needs to "
                    "write files into the artifact store, but the artifact "
                    f"store `{stack.artifact_store.name}` of the active "
                    "stack is local. Please ensure that your stack contains "
                    "a remote artifact store when using the Modal "
                    "orchestrator."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The Modal orchestrator runs steps remotely and needs "
                    "to push/pull Docker images, but the container registry "
                    f"`{container_registry.name}` of the active stack is "
                    "local. Please ensure that your stack contains a remote "
                    "container registry when using the Modal orchestrator."
                )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_remote_components,
        )

    def get_orchestrator_run_id(self) -> str:
        """Returns the active orchestrator run id.

        Raises:
            RuntimeError: If the environment variable specifying the run id
                is not set.

        Returns:
            The orchestrator run id.
        """
        try:
            return os.environ[ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID}."
            )

    @property
    def supported_execution_modes(self) -> List[ExecutionMode]:
        """Supported execution modes for this orchestrator.

        Returns:
            Execution modes supported by the Modal orchestrator.
        """
        return [
            ExecutionMode.FAIL_FAST,
            ExecutionMode.STOP_ON_FAILURE,
            ExecutionMode.CONTINUE_ON_FAILURE,
        ]

    def submit_pipeline(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        base_environment: Dict[str, str],
        step_environments: Dict[str, Dict[str, str]],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submits a pipeline to the Modal orchestrator.

        Args:
            snapshot: The pipeline snapshot to submit.
            stack: The stack the pipeline will run on.
            base_environment: Base environment shared by all steps.
            step_environments: Per-step environment variables.
            placeholder_run: An optional placeholder run for the snapshot.

        Raises:
            RuntimeError: If the container registry has no credentials, or
                if the pipeline run has one or more failed steps.

        Returns:
            Optional submission result.
        """
        if snapshot.schedule:
            logger.warning(
                "The Modal orchestrator does not support schedules. The "
                "`schedule` will be ignored and the pipeline will be run "
                "immediately."
            )

        container_registry = stack.container_registry
        assert container_registry is not None

        if docker_creds := container_registry.credentials:
            docker_username, docker_password = docker_creds
        else:
            raise RuntimeError(
                "No Docker credentials found for the container registry."
            )
        registry_secret = build_registry_secret(
            docker_username, docker_password
        )

        orchestrator_run_id = str(uuid4())
        app = modal.App.lookup(
            f"zenml-pipeline-{snapshot.id}"[:64], create_if_missing=True
        )

        entrypoint_command = (
            StepEntrypointConfiguration.get_entrypoint_command()
        )
        execution_mode = snapshot.pipeline_configuration.execution_mode
        failed_steps: List[str] = []
        skipped_steps: List[str] = []
        start_time = time.time()

        for step_name, step in snapshot.step_configurations.items():
            if (
                execution_mode == ExecutionMode.STOP_ON_FAILURE
                and failed_steps
            ):
                logger.warning(
                    "Skipping step %s due to the failed step(s): %s "
                    "(Execution mode %s)",
                    step_name,
                    ", ".join(failed_steps),
                    execution_mode,
                )
                skipped_steps.append(step_name)
                continue

            if failed_upstream_steps := [
                fs for fs in failed_steps if fs in step.spec.upstream_steps
            ]:
                logger.warning(
                    "Skipping step %s due to failure in upstream step(s): "
                    "%s (Execution mode %s)",
                    step_name,
                    ", ".join(failed_upstream_steps),
                    execution_mode,
                )
                skipped_steps.append(step_name)
                continue

            if skipped_upstream_steps := [
                fs for fs in skipped_steps if fs in step.spec.upstream_steps
            ]:
                logger.warning(
                    "Skipping step %s due to the skipped upstream step(s): "
                    "%s (Execution mode %s)",
                    step_name,
                    ", ".join(skipped_upstream_steps),
                    execution_mode,
                )
                skipped_steps.append(step_name)
                continue

            if not self._run_step_on_modal(
                app=app,
                registry_secret=registry_secret,
                snapshot=snapshot,
                step_name=step_name,
                step=step,
                step_environment=step_environments[step_name],
                orchestrator_run_id=orchestrator_run_id,
                entrypoint_command=entrypoint_command,
                execution_mode=execution_mode,
            ):
                failed_steps.append(step_name)

        if failed_steps:
            raise RuntimeError(
                "Pipeline run has failed due to failure in step(s): "
                f"{', '.join(failed_steps)}"
            )

        run_duration = time.time() - start_time
        logger.info(
            "Pipeline run has finished in `%s`.",
            string_utils.get_human_readable_time(run_duration),
        )
        return None

    def _run_step_on_modal(
        self,
        app: "modal.App",
        registry_secret: "modal.secret._Secret",
        snapshot: "PipelineSnapshotResponse",
        step_name: str,
        step: "Step",
        step_environment: Dict[str, str],
        orchestrator_run_id: str,
        entrypoint_command: List[str],
        execution_mode: ExecutionMode,
    ) -> bool:
        """Runs a single step as a Modal sandbox and waits for completion.

        Args:
            app: The Modal app that owns all sandboxes for this pipeline run.
            registry_secret: Modal secret carrying container-registry creds.
            snapshot: The pipeline snapshot.
            step_name: Name of the step to run.
            step: The step configuration.
            step_environment: Environment variables for this step.
            orchestrator_run_id: The pipeline-level orchestrator run id.
            entrypoint_command: Base entrypoint command (list of argv tokens).
            execution_mode: Pipeline-level execution mode.

        Raises:
            RuntimeError: In ``FAIL_FAST`` mode when the step fails.

        Returns:
            ``True`` if the step completed successfully, ``False`` otherwise.
        """
        image_name = self.get_image(snapshot=snapshot, step_name=step_name)

        step_environment = dict(step_environment)
        step_environment[ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID] = (
            orchestrator_run_id
        )

        arguments = StepEntrypointConfiguration.get_entrypoint_arguments(
            step_name=step_name, snapshot_id=snapshot.id
        )
        full_command = [*entrypoint_command, *arguments]

        settings = cast(ModalOrchestratorSettings, self.get_settings(step))
        resource_settings = step.config.resource_settings
        gpu_values = get_gpu_values(settings.gpu, resource_settings)
        memory_mb = resource_settings.get_memory(ByteUnit.MB)
        memory_int = int(memory_mb) if memory_mb is not None else None

        zenml_image = build_registry_image(
            image_name=image_name,
            registry_secret=registry_secret,
            environment=step_environment,
        )

        logger.info("Submitting step `%s` to Modal...", step_name)
        sandbox = modal.Sandbox.create(
            "bash",
            "-c",
            " ".join(full_command),
            app=app,
            image=zenml_image,
            gpu=gpu_values,
            cpu=resource_settings.cpu_count,
            memory=memory_int,
            cloud=settings.cloud,
            region=settings.region,
            timeout=86400,  # 24h, the max Modal allows
        )
        logger.info(
            "Step `%s` running on Modal sandbox `%s`.",
            step_name,
            sandbox.object_id,
        )

        for line in sandbox.stdout:
            logger.info(line.rstrip("\n"))

        sandbox.wait()
        return_code = sandbox.returncode

        if return_code == 0:
            return True

        error_msg = (
            f"Step `{step_name}` failed on Modal "
            f"(sandbox `{sandbox.object_id}`, exit code {return_code})."
        )
        if execution_mode == ExecutionMode.FAIL_FAST:
            raise RuntimeError(error_msg)
        logger.error(error_msg)
        return False
