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

from zenml.config.base_settings import BaseSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import StackComponentType
from zenml.integrations.runai.client.runai_client import (
    RunAIClient,
    RunAIClientError,
)
from zenml.integrations.runai.constants import (
    MAX_WORKLOAD_NAME_LENGTH,
    is_failure_status,
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
        client = self._get_client()

        image = info.get_image(key=RUNAI_STEP_OPERATOR_DOCKER_IMAGE_KEY)

        project_id, cluster_id = self._resolve_project_and_cluster(client)

        workload_name = self._build_workload_name(info)

        compute = self._build_compute_spec(client, settings)

        env_vars = self._build_environment_variables(
            client, environment, settings.environment_variables
        )

        image_pull_secrets = self._build_image_pull_secrets(client)

        command, args = self._build_command_and_args(entrypoint_command)

        models = client.models
        TrainingCreationRequest = models.TrainingCreationRequest
        TrainingSpecSpec = models.TrainingSpecSpec

        tolerations_list = self._build_tolerations(client, settings)
        labels_list = self._build_labels(client, settings)
        annotations_list = self._build_annotations(client, settings)

        spec_dict: Dict[str, Any] = {
            "image": image,
            "command": command,
            "compute": compute,
            "environmentVariables": env_vars,
        }
        if args:
            spec_dict["args"] = args
        if image_pull_secrets:
            spec_dict["imagePullSecrets"] = image_pull_secrets

        if settings.node_pools:
            spec_dict["nodePools"] = settings.node_pools
        if settings.node_type:
            spec_dict["nodeType"] = settings.node_type
        if settings.preemptibility:
            spec_dict["preemptibility"] = settings.preemptibility
        if settings.priority_class:
            spec_dict["priorityClass"] = settings.priority_class
        if tolerations_list:
            spec_dict["tolerations"] = tolerations_list

        if settings.backoff_limit is not None:
            spec_dict["backoffLimit"] = settings.backoff_limit
        if settings.termination_grace_period_seconds is not None:
            spec_dict["terminationGracePeriodSeconds"] = (
                settings.termination_grace_period_seconds
            )
        if settings.terminate_after_preemption is not None:
            spec_dict["terminateAfterPreemption"] = (
                settings.terminate_after_preemption
            )
        if settings.working_dir:
            spec_dict["workingDir"] = settings.working_dir

        if labels_list:
            spec_dict["labels"] = labels_list
        if annotations_list:
            spec_dict["annotations"] = annotations_list

        training_request = TrainingCreationRequest(
            name=workload_name,
            projectId=project_id,
            clusterId=cluster_id,
            spec=TrainingSpecSpec(**spec_dict),
        )

        try:
            result = client.create_training_workload(training_request)
        except RunAIClientError as exc:
            raise RuntimeError(
                f"Failed to submit step '{info.pipeline_step_name}' to Run:AI: {exc}. "
                "Verify credentials, project name, cluster access, and quota."
            ) from exc

        self._wait_for_completion(client, result.workload_id)
        logger.info("Run:AI step operator job completed.")

    def _get_client(self) -> RunAIClient:
        """Initialize and return a Run:AI client.

        Returns:
            Initialized RunAIClient.
        """
        return RunAIClient(
            client_id=self.config.client_id,
            client_secret=self.config.client_secret.get_secret_value(),
            runai_base_url=self.config.runai_base_url,
        )

    def _resolve_project_and_cluster(
        self, client: RunAIClient
    ) -> Tuple[str, str]:
        """Resolve Run:AI project and cluster IDs.

        Args:
            client: The RunAIClient instance.

        Returns:
            Tuple of (project_id, cluster_id).

        Raises:
            RuntimeError: If project or cluster cannot be resolved.
        """
        try:
            project = client.get_project_by_name(self.config.project_name)
        except RunAIClientError as exc:
            raise RuntimeError(str(exc)) from exc

        cluster_id = project.cluster_id

        if self.config.cluster_name and cluster_id:
            cluster = client.get_cluster_by_id(cluster_id)
            if cluster and cluster.name != self.config.cluster_name:
                logger.warning(
                    f"Configured cluster '{self.config.cluster_name}' "
                    f"does not match project's cluster '{cluster.name}'. "
                    f"Using project's cluster."
                )

        if not cluster_id:
            try:
                if self.config.cluster_name:
                    cluster = client.get_cluster_by_name(
                        self.config.cluster_name
                    )
                    cluster_id = cluster.id
                else:
                    cluster = client.get_first_cluster()
                    cluster_id = cluster.id
            except RunAIClientError as exc:
                raise RuntimeError(str(exc)) from exc

        return project.id, cluster_id

    def _build_workload_name(self, info: "StepRunInfo") -> str:
        """Build a unique workload name for the step.

        Args:
            info: Step run information.

        Returns:
            A valid Run:AI workload name.
        """
        step_name = info.pipeline_step_name.lower().replace("_", "-")
        pipeline_name = info.pipeline.name.lower().replace("_", "-")

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
    ) -> Tuple[List[str], List[str]]:
        """Build the command and arguments for Run:AI.

        ZenML step entrypoints are typically generated as
        `["python", "-m", "zenml.entrypoints.step_entrypoint", ...args...]`.
        We split after the first three tokens to keep the interpreter/module
        invocation intact while passing the remaining tokens as arguments.

        This follows the same pattern as the Kubernetes step operator.

        Args:
            entrypoint_command: The full entrypoint command list.

        Returns:
            Tuple of (command, args) as lists.

        Raises:
            ValueError: If entrypoint_command format is invalid.
        """
        if len(entrypoint_command) < 3:
            raise ValueError(
                f"Expected entrypoint command with at least 3 elements "
                f"(e.g., ['python', '-m', 'module_name']), but got "
                f"{len(entrypoint_command)} elements: {entrypoint_command}"
            )

        command = entrypoint_command[:3]
        args = entrypoint_command[3:]
        return command, args

    def _build_environment_variables(
        self,
        client: RunAIClient,
        base_environment: Dict[str, str],
        additional_vars: Dict[str, str],
    ) -> List[Any]:
        """Build Run:AI environment variables.

        Args:
            client: The RunAIClient instance.
            base_environment: Base environment variables from ZenML.
            additional_vars: Additional environment variables from settings.

        Returns:
            List of Run:AI EnvironmentVariable objects.
        """
        EnvironmentVariable = client.models.EnvironmentVariable

        merged_env = {**base_environment, **additional_vars}

        return [
            EnvironmentVariable(name=key, value=value)
            for key, value in merged_env.items()
        ]

    def _build_compute_spec(
        self, client: RunAIClient, settings: RunAIStepOperatorSettings
    ) -> Any:
        """Build the compute specification for the workload.

        Args:
            client: The RunAIClient instance.
            settings: The step operator settings.

        Returns:
            A SupersetSpecAllOfCompute object.
        """
        SupersetSpecAllOfCompute = client.models.SupersetSpecAllOfCompute
        ExtendedResource = client.models.ExtendedResource

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
        self, client: RunAIClient
    ) -> Optional[List[Any]]:
        """Build image pull secrets for the workload.

        Args:
            client: The RunAIClient instance.

        Returns:
            List of ImagePullSecret objects or None.
        """
        if not self.config.image_pull_secret_name:
            return None

        logger.info(
            f"Using image pull secret '{self.config.image_pull_secret_name}'. "
            f"Ensure this secret exists in your Run:AI project."
        )

        ImagePullSecret = client.models.ImagePullSecret
        return [
            ImagePullSecret(
                name=self.config.image_pull_secret_name, user_credential=False
            )
        ]

    def _build_tolerations(
        self, client: RunAIClient, settings: RunAIStepOperatorSettings
    ) -> Optional[List[Any]]:
        """Build tolerations for scheduling on tainted nodes.

        Args:
            client: The RunAIClient instance.
            settings: The step operator settings.

        Returns:
            List of Toleration objects or None.
        """
        if not settings.tolerations:
            return None

        Toleration = client.models.Toleration

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
        self, client: RunAIClient, settings: RunAIStepOperatorSettings
    ) -> Optional[List[Any]]:
        """Build labels for the workload pod.

        Args:
            client: The RunAIClient instance.
            settings: The step operator settings.

        Returns:
            List of Label objects or None.
        """
        if not settings.labels:
            return None

        Label = client.models.Label
        return [Label(key=k, value=v) for k, v in settings.labels.items()]

    def _build_annotations(
        self, client: RunAIClient, settings: RunAIStepOperatorSettings
    ) -> Optional[List[Any]]:
        """Build annotations for the workload pod.

        Args:
            client: The RunAIClient instance.
            settings: The step operator settings.

        Returns:
            List of Annotation objects or None.
        """
        if not settings.annotations:
            return None

        Annotation = client.models.Annotation
        return [
            Annotation(key=k, value=v) for k, v in settings.annotations.items()
        ]

    def _wait_for_completion(
        self,
        client: RunAIClient,
        workload_id: str,
    ) -> None:
        """Wait for a Run:AI workload to complete.

        Args:
            client: The RunAIClient instance.
            workload_id: The workload ID to wait for.

        Raises:
            RuntimeError: If the workload fails or times out.
        """
        start_time = time.time()
        timeout = self.config.workload_timeout
        retry_count = 0
        max_retries = 3
        base_interval = self.config.monitoring_interval
        missing_status_retries = 0
        max_missing_status_checks = 3

        while True:
            sleep_time = base_interval
            if timeout and (time.time() - start_time) > timeout:
                logger.warning(
                    f"Attempting to stop timed-out workload {workload_id}"
                )
                try:
                    client.delete_training_workload(workload_id)
                except Exception as cleanup_exc:
                    logger.error(
                        f"Failed to cleanup workload {workload_id}: {cleanup_exc}"
                    )
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
                    try:
                        client.delete_training_workload(workload_id)
                    except Exception as cleanup_exc:
                        logger.error(
                            f"Failed to cleanup workload {workload_id}: {cleanup_exc}"
                        )
                    raise RuntimeError(
                        f"Run:AI workload {workload_id} failed with status: {status}"
                    )

                else:
                    missing_status_retries = 0
                    sleep_time = base_interval
            except RunAIClientError as exc:
                retry_count += 1
                if retry_count > max_retries:
                    try:
                        client.delete_training_workload(workload_id)
                    except Exception as cleanup_exc:
                        logger.error(
                            f"Failed to cleanup workload {workload_id}: {cleanup_exc}"
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
