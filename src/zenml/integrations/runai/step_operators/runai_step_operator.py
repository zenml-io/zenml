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
"""Run:AI step operator implementation."""

import random
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast

from runai.models.annotation import Annotation
from runai.models.environment_variable import EnvironmentVariable
from runai.models.extended_resource import ExtendedResource
from runai.models.image_pull_secret import ImagePullSecret
from runai.models.label import Label
from runai.models.superset_spec_all_of_compute import SupersetSpecAllOfCompute
from runai.models.toleration import Toleration
from runai.models.training_creation_request import TrainingCreationRequest
from runai.models.training_spec_spec import TrainingSpecSpec

from zenml.config.base_settings import BaseSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import StackComponentType
from zenml.integrations.runai.client.runai_client import (
    RunAIClient,
    RunAIClientError,
    RunAIWorkloadNotFoundError,
)
from zenml.integrations.runai.constants import (
    MAX_WORKLOAD_NAME_LENGTH,
    is_failure_status,
    is_pending_status,
    is_success_status,
)
from zenml.integrations.runai.flavors.runai_step_operator_flavor import (
    RunAIStepOperatorConfig,
    RunAIStepOperatorSettings,
)
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineSnapshotBase

logger = get_logger(__name__)

RUNAI_STEP_OPERATOR_DOCKER_IMAGE_KEY = "runai_step_operator"


class RunAIStepOperator(BaseStepOperator):
    """Step operator to run individual steps on Run:AI.

    This step operator enables selective GPU offloading by running
    individual pipeline steps on Run:AI clusters.

    Example usage:
    ```python
    @step(step_operator="runai")
    def train_model(data):
        # GPU-intensive training runs on Run:AI
        ...

    ```
    """

    _client: Optional[RunAIClient] = None

    @property
    def client(self) -> RunAIClient:
        """Get or create the Run:AI client.

        The client is cached for reuse across multiple calls.

        Returns:
            The RunAIClient instance.
        """
        if self._client is None:
            self._client = RunAIClient(
                client_id=self.config.client_id.get_secret_value(),
                client_secret=self.config.client_secret.get_secret_value(),
                runai_base_url=self.config.runai_base_url,
            )
        return self._client

    @property
    def config(self) -> RunAIStepOperatorConfig:
        """Returns the step operator config.

        Returns:
            The configuration.
        """
        return cast(RunAIStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type[BaseSettings]]:
        """Settings class for the Run:AI step operator.

        Returns:
            The settings class.
        """
        return RunAIStepOperatorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack.

        Returns:
            A validator that checks that the stack contains a remote container
            registry and a remote artifact store.
        """

        def _validate_remote_components(stack: Stack) -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The Run:AI step operator runs code remotely and "
                    "needs to write files into the artifact store, but the "
                    f"artifact store `{stack.artifact_store.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote artifact store when using the Run:AI "
                    "step operator."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The Run:AI step operator runs code remotely and "
                    "needs to push/pull Docker images, but the "
                    f"container registry `{container_registry.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote container registry when using the "
                    "Run:AI step operator."
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
    ) -> List[BuildConfiguration]:
        """Gets the Docker builds required for the component.

        Args:
            snapshot: The pipeline snapshot for which to get the builds.

        Returns:
            The required Docker builds.
        """
        builds = []
        for step_name, step in snapshot.step_configurations.items():
            if step.config.uses_step_operator(self.name):
                build = BuildConfiguration(
                    key=RUNAI_STEP_OPERATOR_DOCKER_IMAGE_KEY,
                    settings=step.config.docker_settings,
                    step_name=step_name,
                )
                builds.append(build)

        return builds

    def launch(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Launches a step on Run:AI as a training workload.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables to set in the step operator
                environment.

        Raises:
            RuntimeError: If workload submission or execution fails.
        """
        settings = cast(RunAIStepOperatorSettings, self.get_settings(info))

        image = info.get_image(key=RUNAI_STEP_OPERATOR_DOCKER_IMAGE_KEY)

        project_id, cluster_id = self._resolve_project_and_cluster()

        workload_name = self._build_workload_name(info)

        compute = self._build_compute_spec(settings)

        env_vars = self._build_environment_variables(environment)

        image_pull_secrets = self._build_image_pull_secrets()

        command, args = self._build_command_and_args(entrypoint_command)

        tolerations_list = self._build_tolerations(settings)
        labels_list = self._build_labels(settings)
        annotations_list = self._build_annotations(settings)

        try:
            training_request = TrainingCreationRequest(
                name=workload_name,
                project_id=project_id,
                cluster_id=cluster_id,
                spec=TrainingSpecSpec(
                    image=image,
                    command=command,
                    compute=compute,
                    environment_variables=env_vars,
                    args=args,
                    image_pull_secrets=image_pull_secrets,
                    node_pools=settings.node_pools,
                    node_type=settings.node_type,
                    preemptibility=settings.preemptibility,
                    priority_class=settings.priority_class,
                    tolerations=tolerations_list,
                    backoff_limit=settings.backoff_limit,
                    termination_grace_period_seconds=(
                        settings.termination_grace_period_seconds
                    ),
                    terminate_after_preemption=settings.terminate_after_preemption,
                    working_dir=settings.working_dir,
                    labels=labels_list,
                    annotations=annotations_list,
                ),
            )
        except Exception as exc:
            raise RunAIClientError(
                "Failed to build Run:AI training request "
                f"({type(exc).__name__}): {exc}"
            ) from exc

        info.force_write_logs()

        try:
            result = self.client.create_training_workload(training_request)
            logger.info(
                "Submitted step '%s' to Run:AI as workload '%s' (ID: %s)",
                info.pipeline_step_name,
                result.workload_name,
                result.workload_id,
            )
        except RunAIClientError as exc:
            raise RuntimeError(
                f"Failed to submit step '{info.pipeline_step_name}' to Run:AI: {exc}. "
                "Verify credentials, project name, cluster access, and quota."
            ) from exc

        self._wait_for_completion(self.client, result.workload_id, settings)
        logger.info("Run:AI step operator job completed.")

    def _resolve_project_and_cluster(self) -> Tuple[str, str]:
        """Resolve Run:AI project and cluster IDs.

        Returns:
            Tuple of (project_id, cluster_id).

        Raises:
            RuntimeError: If project or cluster cannot be resolved.
        """
        try:
            project = self.client.get_project_by_name(self.config.project_name)
        except RunAIClientError as exc:
            raise RuntimeError(str(exc)) from exc

        cluster_id = project.cluster_id

        if self.config.cluster_name and cluster_id:
            cluster = self.client.get_cluster_by_id(cluster_id)
            if cluster.name != self.config.cluster_name:
                logger.warning(
                    f"Configured cluster '{self.config.cluster_name}' "
                    f"does not match project's cluster '{cluster.name}'. "
                    f"Using project's cluster."
                )

        if not cluster_id:
            try:
                if self.config.cluster_name:
                    cluster = self.client.get_cluster_by_name(
                        self.config.cluster_name
                    )
                    cluster_id = cluster.id
                else:
                    cluster = self.client.get_first_cluster()
                    cluster_id = cluster.id
            except RunAIClientError as exc:
                raise RuntimeError(str(exc)) from exc

        return project.id, cluster_id

    def _sanitize_name_component(self, name: str) -> str:
        """Sanitize a name component for Kubernetes DNS label compliance.

        Args:
            name: The name component to sanitize.

        Returns:
            A sanitized string with only lowercase alphanumeric chars and hyphens.
        """
        import re

        sanitized = name.lower()
        sanitized = re.sub(r"[^a-z0-9-]", "-", sanitized)
        sanitized = re.sub(r"-+", "-", sanitized)
        return sanitized.strip("-")

    def _build_workload_name(self, info: "StepRunInfo") -> str:
        """Build a unique workload name for the step.

        Run:AI workload names must be valid Kubernetes DNS labels:
        lowercase, start with letter, alphanumeric and hyphens only.

        Args:
            info: Step run information.

        Returns:
            A unique workload name string conforming to Run:AI naming requirements.
        """
        step_name = self._sanitize_name_component(info.pipeline_step_name)
        pipeline_name = self._sanitize_name_component(info.pipeline.name)

        base_name = f"zenml-{pipeline_name}-{step_name}"

        if base_name and not base_name[0].isalpha():
            base_name = f"z{base_name}"

        run_id_suffix = str(info.run_id)[:8]
        timestamp = datetime.now(timezone.utc).strftime("%H%M%S%f")[:9]

        identifier_len = len(run_id_suffix) + len(timestamp) + 2
        max_base_len = MAX_WORKLOAD_NAME_LENGTH - identifier_len
        base_name = base_name[:max_base_len].rstrip("-")

        return f"{base_name}-{run_id_suffix}-{timestamp}"

    def _build_command_and_args(
        self, entrypoint_command: List[str]
    ) -> Tuple[str, Optional[str]]:
        """Build the command and arguments for Run:AI.

        Run:AI expects the command and args as strings (not lists). We keep
        the interpreter/module invocation intact for the command and join
        remaining tokens as the args string.

        Args:
            entrypoint_command: The full entrypoint command list.

        Returns:
            Tuple of (command, args) as strings. The args value is None when
            there are no extra tokens.

        Raises:
            ValueError: If entrypoint_command format is invalid.
        """
        if len(entrypoint_command) < 3:
            raise ValueError(
                f"Expected entrypoint command with at least 3 elements "
                f"(e.g., ['python', '-m', 'module_name']), but got "
                f"{len(entrypoint_command)} elements: {entrypoint_command}"
            )

        command_tokens = entrypoint_command[:3]
        args_tokens = entrypoint_command[3:]

        command = " ".join(command_tokens)
        args = " ".join(args_tokens) if args_tokens else None
        return command, args

    def _build_environment_variables(
        self, environment: Dict[str, str]
    ) -> Optional[List[EnvironmentVariable]]:
        """Build environment variables for the Run:AI workload.

        Args:
            environment: Mapping of environment variable names to values.

        Returns:
            List of EnvironmentVariable objects or None.
        """
        if not environment:
            return None

        return [
            EnvironmentVariable(name=name, value=str(value))
            for name, value in environment.items()
        ]

    def _build_compute_spec(
        self, settings: RunAIStepOperatorSettings
    ) -> SupersetSpecAllOfCompute:
        """Build the compute specification for the workload.

        Args:
            settings: The step operator settings.

        Returns:
            The Run:AI compute specification object.
        """
        extended_resources_list = None
        if settings.extended_resources:
            extended_resources_list = [
                ExtendedResource(resource=k, quantity=v)
                for k, v in settings.extended_resources.items()
            ]

        return SupersetSpecAllOfCompute(
            gpu_devices_request=settings.gpu_devices_request,
            gpu_portion_request=settings.gpu_portion_request,
            gpu_request_type=settings.gpu_request_type,
            gpu_memory_request=settings.gpu_memory_request,
            gpu_portion_limit=settings.gpu_portion_limit,
            gpu_memory_limit=settings.gpu_memory_limit,
            cpu_core_request=settings.cpu_core_request,
            cpu_core_limit=settings.cpu_core_limit,
            cpu_memory_request=settings.cpu_memory_request,
            cpu_memory_limit=settings.cpu_memory_limit,
            large_shm_request=settings.large_shm_request,
            extended_resources=extended_resources_list,
        )

    def _build_image_pull_secrets(
        self,
    ) -> Optional[List[ImagePullSecret]]:
        """Build image pull secrets for the workload.

        Returns:
            List of ImagePullSecret objects or None.
        """
        if not self.config.image_pull_secret_name:
            return None

        logger.info(
            f"Using image pull secret '{self.config.image_pull_secret_name}'. "
            f"Ensure this secret exists in your Run:AI project."
        )

        return [
            ImagePullSecret(
                name=self.config.image_pull_secret_name, user_credential=False
            )
        ]

    def _build_tolerations(
        self, settings: RunAIStepOperatorSettings
    ) -> Optional[List[Toleration]]:
        """Build tolerations for scheduling on tainted nodes.

        Args:
            settings: The step operator settings.

        Returns:
            List of Toleration objects or None.
        """
        if not settings.tolerations:
            return None

        tolerations_list = []
        for t in settings.tolerations:
            toleration_dict: Dict[str, Any] = {}
            if "key" in t:
                toleration_dict["key"] = t["key"]
            if "operator" in t:
                toleration_dict["operator"] = t["operator"]
            if "value" in t:
                toleration_dict["value"] = t["value"]
            if "effect" in t:
                toleration_dict["effect"] = t["effect"]
            tolerations_list.append(Toleration(**toleration_dict))

        return tolerations_list

    def _build_labels(
        self, settings: RunAIStepOperatorSettings
    ) -> Optional[List[Label]]:
        """Build labels for the workload pod.

        Args:
            settings: The step operator settings.

        Returns:
            List of Label objects or None.
        """
        if not settings.labels:
            return None

        return [Label(name=k, value=v) for k, v in settings.labels.items()]

    def _build_annotations(
        self, settings: RunAIStepOperatorSettings
    ) -> Optional[List[Annotation]]:
        """Build annotations for the workload pod.

        Args:
            settings: The step operator settings.

        Returns:
            List of Annotation objects or None.
        """
        if not settings.annotations:
            return None

        return [
            Annotation(name=k, value=v)
            for k, v in settings.annotations.items()
        ]

    def _cleanup_workload(
        self, client: RunAIClient, workload_id: str, reason: str
    ) -> None:
        """Stop a Run:AI workload and optionally delete it.

        Args:
            client: The RunAIClient instance.
            workload_id: The workload ID to stop.
            reason: Reason for cleanup (for logging).
        """
        manual_cleanup_hint = (
            "Open "
            f"{self.config.runai_base_url} and navigate to Workloads > "
            f"Training to clean up workload '{workload_id}'."
        )
        logger.info(f"Stopping workload {workload_id}: {reason}")
        try:
            client.suspend_training_workload(workload_id)
        except Exception as suspend_exc:
            logger.error(
                f"Failed to stop workload {workload_id}: {suspend_exc}. "
                f"{manual_cleanup_hint}"
            )

        if not self.config.delete_on_failure:
            logger.info(
                f"Preserving workload {workload_id} after failure "
                f"(delete_on_failure=False). Reason: {reason}. "
                f"{manual_cleanup_hint}"
            )
            return

        logger.info(f"Deleting workload {workload_id}: {reason}")
        try:
            client.delete_training_workload(workload_id)
        except Exception as delete_exc:
            logger.error(
                f"Failed to delete workload {workload_id}: {delete_exc}. "
                f"{manual_cleanup_hint}"
            )

    def _wait_for_completion(
        self,
        client: RunAIClient,
        workload_id: str,
        settings: RunAIStepOperatorSettings,
    ) -> None:
        """Wait for a Run:AI workload to complete.

        Args:
            client: The RunAIClient instance.
            workload_id: The workload ID to wait for.
            settings: The step operator settings.

        Raises:
            RuntimeError: If the workload fails or times out.
        """
        start_time = time.time()
        timeout = settings.workload_timeout
        pending_timeout = settings.pending_timeout
        retry_count = 0
        max_retries = 3
        base_interval = self.config.monitoring_interval
        missing_status_retries = 0
        max_missing_status_checks = 3
        pending_start_time: Optional[float] = None

        while True:
            sleep_time = base_interval
            if timeout and (time.time() - start_time) > timeout:
                self._cleanup_workload(client, workload_id, "timeout")
                raise RuntimeError(
                    f"Run:AI workload {workload_id} timed out after {timeout} seconds"
                )

            try:
                status = client.get_training_workload_status(workload_id)
                retry_count = 0

                if status is None:
                    missing_status_retries += 1
                    if missing_status_retries > max_missing_status_checks:
                        raise RuntimeError(
                            "Run:AI workload "
                            f"{workload_id} is missing or returned no status "
                            f"after {max_missing_status_checks} checks. The "
                            "workload might have been deleted or failed to "
                            "start."
                        )

                    logger.warning(
                        "No status returned for Run:AI workload %s "
                        "(attempt %d/%d); retrying.",
                        workload_id,
                        missing_status_retries,
                        max_missing_status_checks,
                    )
                    sleep_time = base_interval
                elif status and is_success_status(status):
                    missing_status_retries = 0
                    return

                elif status and is_failure_status(status):
                    missing_status_retries = 0
                    self._cleanup_workload(
                        client, workload_id, f"failed with status: {status}"
                    )
                    raise RuntimeError(
                        f"Run:AI workload {workload_id} failed with status: {status}"
                    )

                else:
                    missing_status_retries = 0
                    if status and is_pending_status(status):
                        if pending_start_time is None:
                            pending_start_time = time.time()
                        if (
                            pending_timeout
                            and (time.time() - pending_start_time)
                            > pending_timeout
                        ):
                            self._cleanup_workload(
                                client,
                                workload_id,
                                f"pending timeout after {pending_timeout} seconds",
                            )
                            raise RuntimeError(
                                "Run:AI workload "
                                f"{workload_id} exceeded pending timeout of "
                                f"{pending_timeout} seconds"
                            )
                    else:
                        pending_start_time = None
                    sleep_time = base_interval
            except RunAIWorkloadNotFoundError as exc:
                retry_count = 0
                missing_status_retries += 1
                if missing_status_retries > max_missing_status_checks:
                    raise RuntimeError(
                        "Run:AI workload "
                        f"{workload_id} was not found after "
                        f"{max_missing_status_checks} checks. The workload "
                        "might have been deleted or failed to start."
                    ) from exc

                logger.warning(
                    "Run:AI workload %s not found (attempt %d/%d); retrying.",
                    workload_id,
                    missing_status_retries,
                    max_missing_status_checks,
                )
                sleep_time = base_interval
            except RunAIClientError as exc:
                retry_count += 1
                if retry_count > max_retries:
                    self._cleanup_workload(
                        client, workload_id, "max retries exceeded"
                    )
                    raise RuntimeError(
                        f"Failed to check status after {max_retries} retries: {exc}"
                    )

                sleep_time = min(base_interval * (2**retry_count), 300)
                sleep_time += random.uniform(0, 0.1 * sleep_time)
                logger.warning(
                    f"Status check failed (retry {retry_count}/{max_retries}): {exc}"
                )

            time.sleep(sleep_time)
