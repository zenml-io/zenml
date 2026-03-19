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
"""Kubeflow Trainer v2 step operator implementation."""

import os
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast

from kubernetes import client as k8s_client
from kubernetes.client.exceptions import ApiException

from zenml.config.base_settings import BaseSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.integrations.kubeflow.flavors import (
    KubeflowTrainerStepOperatorConfig,
    KubeflowTrainerStepOperatorSettings,
)
from zenml.integrations.kubeflow.step_operators.kubeflow_trainer_step_operator_entrypoint_configuration import (
    KubeflowTrainerStepOperatorEntrypointConfiguration,
)
from zenml.integrations.kubeflow.step_operators.kubeflow_trainer_step_operator_naming_utils import (
    build_trainjob_annotations,
    build_trainjob_labels,
    build_trainjob_name,
    sanitize_kubernetes_name,
)
from zenml.integrations.kubeflow.step_operators.trainer_job_watcher import (
    get_terminal_trainjob_status,
)
from zenml.integrations.kubeflow.step_operators.trainjob_manifest_utils import (
    TRAINJOB_GROUP,
    TRAINJOB_PLURAL,
    TRAINJOB_VERSION,
    build_trainjob_manifest,
)
from zenml.logger import get_logger
from zenml.models import StepRunResponse
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator
from zenml.step_operators.step_operator_entrypoint_configuration import (
    StepOperatorEntrypointConfiguration,
)

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineSnapshotBase

logger = get_logger(__name__)

KUBEFLOW_TRAINER_STEP_OPERATOR_DOCKER_IMAGE_KEY = (
    "kubeflow_trainer_step_operator"
)

_STEP_RUN_ID_LABEL = "zenml.io/step-run-id"


class KubeflowTrainerStepOperator(BaseStepOperator):
    """Step operator to run distributed steps with Kubeflow Trainer v2."""

    _k8s_client: Optional["k8s_client.ApiClient"] = None

    @property
    def config(self) -> KubeflowTrainerStepOperatorConfig:
        """Returns the typed config.

        Returns:
            Typed Kubeflow Trainer config.
        """
        return cast(KubeflowTrainerStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for this step operator.

        Returns:
            The settings class.
        """
        return KubeflowTrainerStepOperatorSettings

    @property
    def entrypoint_config_class(
        self,
    ) -> Type[StepOperatorEntrypointConfiguration]:
        """Entrypoint configuration class for this operator.

        Returns:
            Custom entrypoint config class.
        """
        return KubeflowTrainerStepOperatorEntrypointConfiguration

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates stack compatibility for this step operator.

        Returns:
            A stack validator.
        """

        def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The Kubeflow Trainer step operator runs code remotely and "
                    "needs to write files into the artifact store, but the "
                    f"artifact store `{stack.artifact_store.name}` of the "
                    "active stack is local. Please ensure your stack contains "
                    "a remote artifact store when using this step operator."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The Kubeflow Trainer step operator runs code remotely and "
                    "needs to push/pull Docker images, but the "
                    f"container registry `{container_registry.name}` of the "
                    "active stack is local. Please ensure your stack contains "
                    "a remote container registry when using this step operator."
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
        """Gets Docker builds required by this step operator.

        Args:
            snapshot: Pipeline snapshot.

        Returns:
            Required Docker builds.
        """
        builds = []
        for step_name, step in snapshot.step_configurations.items():
            if step.config.uses_step_operator(self.name):
                build = BuildConfiguration(
                    key=KUBEFLOW_TRAINER_STEP_OPERATOR_DOCKER_IMAGE_KEY,
                    settings=step.config.docker_settings,
                    step_name=step_name,
                )
                builds.append(build)

        return builds

    def get_kube_client(
        self, settings: KubeflowTrainerStepOperatorSettings
    ) -> "k8s_client.ApiClient":
        """Gets a Kubernetes API client.

        Args:
            settings: Step operator settings containing auth configuration.

        Returns:
            Kubernetes API client.

        Raises:
            RuntimeError: If service connector client is unexpected.
        """
        from zenml.integrations.kubernetes import kube_utils

        if settings.incluster:
            kube_utils.load_kube_config(incluster=True)
            self._k8s_client = k8s_client.ApiClient()
            return self._k8s_client

        if self._k8s_client and not self.connector_has_expired():
            return self._k8s_client

        connector = self.get_connector()
        if connector:
            client = connector.connect()
            if not isinstance(client, k8s_client.ApiClient):
                raise RuntimeError(
                    "Expected a k8s_client.ApiClient while trying to use "
                    f"the linked connector, but got {type(client)}."
                )
            self._k8s_client = client
        else:
            kube_utils.load_kube_config(
                context=settings.kubernetes_context,
            )
            self._k8s_client = k8s_client.ApiClient()

        return self._k8s_client

    def _get_custom_objects_api(
        self, settings: KubeflowTrainerStepOperatorSettings
    ) -> "k8s_client.CustomObjectsApi":
        """Kubernetes CustomObjectsApi client.

        Args:
            settings: Step operator settings for auth configuration.

        Returns:
            CustomObjectsApi client.
        """
        return k8s_client.CustomObjectsApi(self.get_kube_client(settings))

    def _get_custom_objects_api_from_config(
        self,
    ) -> "k8s_client.CustomObjectsApi":
        """Kubernetes CustomObjectsApi using component config for auth.

        Returns:
            CustomObjectsApi client.
        """
        return self._get_custom_objects_api(self.config)

    def _resolve_namespace(
        self, settings: KubeflowTrainerStepOperatorSettings
    ) -> str:
        """Resolves namespace for train job resources.

        Args:
            settings: Step operator settings.

        Returns:
            Resolved namespace.
        """
        if not settings.incluster:
            return settings.kubernetes_namespace

        if namespace := os.environ.get("POD_NAMESPACE"):
            return namespace

        service_account_namespace = (
            "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
        )
        if os.path.exists(service_account_namespace):
            with open(service_account_namespace, "r") as namespace_file:
                inferred_namespace = namespace_file.read().strip()
                if inferred_namespace:
                    return inferred_namespace

        return settings.kubernetes_namespace

    def _find_trainjob(
        self, step_run: StepRunResponse
    ) -> Optional[Dict[str, Any]]:
        """Finds a TrainJob by step run ID label.

        API errors are allowed to propagate so the base ``wait()`` can
        fall back to querying the ZenML server for step status.

        Args:
            step_run: The step run to look up.

        Returns:
            The TrainJob resource dict, or None if not found.
        """
        custom_objects_api = self._get_custom_objects_api_from_config()
        namespace = self._resolve_namespace(self.config)
        label_selector = (
            f"{_STEP_RUN_ID_LABEL}="
            f"{sanitize_kubernetes_name(str(step_run.id))}"
        )
        result = custom_objects_api.list_namespaced_custom_object(
            group=TRAINJOB_GROUP,
            version=TRAINJOB_VERSION,
            namespace=namespace,
            plural=TRAINJOB_PLURAL,
            label_selector=label_selector,
        )

        items = result.get("items", [])
        if not items:
            return None
        trainjob: Dict[str, Any] = items[0]
        return trainjob

    def _delete_trainjob(
        self,
        custom_objects_api: "k8s_client.CustomObjectsApi",
        namespace: str,
        trainjob_name: str,
    ) -> None:
        """Deletes a TrainJob while ignoring already-deleted resources.

        Args:
            custom_objects_api: API client used to delete the TrainJob.
            namespace: TrainJob namespace.
            trainjob_name: TrainJob name.

        Raises:
            kubernetes.client.exceptions.ApiException: Any non-404 API error.
        """
        try:
            custom_objects_api.delete_namespaced_custom_object(
                group=TRAINJOB_GROUP,
                version=TRAINJOB_VERSION,
                namespace=namespace,
                plural=TRAINJOB_PLURAL,
                name=trainjob_name,
                body={},
            )
        except ApiException as e:
            if e.status == 404:
                return
            raise

    def submit(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Submits a step as a Kubeflow Trainer v2 TrainJob.

        Creates the TrainJob resource and returns immediately without
        waiting for completion. The framework calls ``wait()`` and
        ``get_status()`` to monitor progress.

        Args:
            info: Step run information.
            entrypoint_command: Command that executes the step entrypoint.
            environment: Environment variables for step execution.
        """
        settings = cast(
            KubeflowTrainerStepOperatorSettings,
            self.get_settings(info),
        )
        custom_objects_api = self._get_custom_objects_api(settings)

        image_name = settings.image or info.get_image(
            key=KUBEFLOW_TRAINER_STEP_OPERATOR_DOCKER_IMAGE_KEY
        )
        command = entrypoint_command[:3]
        args = entrypoint_command[3:]

        namespace = self._resolve_namespace(settings)
        trainjob_name = build_trainjob_name(info.pipeline_step_name)
        labels = build_trainjob_labels(
            project_id=str(info.snapshot.project_id),
            run_id=str(info.run_id),
            run_name=str(info.run_name),
            pipeline_name=info.pipeline.name,
            step_name=info.pipeline_step_name,
            step_run_id=str(info.step_run_id),
        )
        annotations = build_trainjob_annotations(
            operator_id=str(self.id),
            step_name=info.pipeline_step_name,
        )

        if info.config.outputs:
            logger.warning(
                "Step `%s` has %d configured output(s), but only the "
                "primary (rank-0) replica will publish artifacts. "
                "Worker replicas will execute user code without "
                "materializing outputs.",
                info.pipeline_step_name,
                len(info.config.outputs),
            )

        trainjob_manifest = build_trainjob_manifest(
            trainjob_name=trainjob_name,
            image=image_name,
            command=command,
            args=args,
            runtime_ref_name=settings.runtime_ref_name,
            runtime_ref_kind=settings.runtime_ref_kind,
            runtime_ref_api_group=settings.runtime_ref_api_group,
            num_nodes=settings.num_nodes,
            num_proc_per_node=settings.num_proc_per_node,
            resource_settings=info.config.resource_settings,
            environment=environment,
            trainer_env=settings.trainer_env,
            trainer_overrides=settings.trainer_overrides,
            pod_template_overrides=settings.pod_template_overrides,
            labels=labels,
            annotations=annotations,
        )

        logger.info(
            "Submitting Kubeflow Trainer TrainJob `%s` in namespace `%s` for "
            "step `%s`.",
            trainjob_name,
            namespace,
            info.pipeline_step_name,
        )

        info.force_write_logs()
        custom_objects_api.create_namespaced_custom_object(
            group=TRAINJOB_GROUP,
            version=TRAINJOB_VERSION,
            namespace=namespace,
            plural=TRAINJOB_PLURAL,
            body=trainjob_manifest,
        )

    def get_status(self, step_run: StepRunResponse) -> ExecutionStatus:
        """Gets the execution status of a submitted TrainJob.

        Args:
            step_run: The step run to check.

        Returns:
            The current execution status.
        """
        trainjob = self._find_trainjob(step_run)
        if trainjob is None:
            logger.warning(
                "No TrainJob found for step run `%s`.", step_run.id
            )
            return ExecutionStatus.FAILED

        terminal = get_terminal_trainjob_status(trainjob)
        if terminal is None:
            return ExecutionStatus.RUNNING

        is_success, details = terminal
        if is_success:
            return ExecutionStatus.COMPLETED

        logger.warning("TrainJob for step `%s` failed: %s", step_run.id, details)
        return ExecutionStatus.FAILED

    def wait(self, step_run: StepRunResponse) -> ExecutionStatus:
        """Waits for a TrainJob to finish, respecting configured timeout.

        Uses the component's ``poll_interval_seconds`` and
        ``timeout_seconds`` settings instead of the base class's
        hardcoded exponential backoff.

        Args:
            step_run: The step run to wait for.

        Returns:
            The final execution status.

        Raises:
            TimeoutError: If ``timeout_seconds`` is set and exceeded.
        """
        poll_interval = self.config.poll_interval_seconds
        timeout = self.config.timeout_seconds
        start_time = time.time()

        while True:
            try:
                status = self.get_status(step_run)
            except Exception as e:
                logger.error(
                    "Failed to get status of step run `%s`: %s",
                    step_run.id,
                    e,
                )
                from zenml.client import Client

                status = (
                    Client()
                    .get_run_step(step_run.id, hydrate=False)
                    .status
                )

            if status.is_finished or status == ExecutionStatus.RETRYING:
                break

            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    self.cancel(step_run)
                    raise TimeoutError(
                        f"Waiting for TrainJob timed out after "
                        f"{timeout} seconds."
                    )

            logger.debug(
                "Waiting for step run `%s` to finish (status: %s).",
                step_run.id,
                status,
            )
            time.sleep(poll_interval)

        if self.config.delete_trainjob_after_completion:
            self._find_and_delete_trainjob(step_run)

        return status

    def cancel(self, step_run: StepRunResponse) -> None:
        """Cancels a running TrainJob by suspending it.

        Args:
            step_run: The step run to cancel.
        """
        trainjob = self._find_trainjob(step_run)
        if trainjob is None:
            logger.warning(
                "No TrainJob found for step run `%s` to cancel.",
                step_run.id,
            )
            return

        trainjob_name = trainjob.get("metadata", {}).get("name", "")
        namespace = self._resolve_namespace(self.config)
        custom_objects_api = self._get_custom_objects_api_from_config()

        try:
            custom_objects_api.patch_namespaced_custom_object(
                group=TRAINJOB_GROUP,
                version=TRAINJOB_VERSION,
                namespace=namespace,
                plural=TRAINJOB_PLURAL,
                name=trainjob_name,
                body={"spec": {"suspend": True}},
            )
            logger.info("Suspended TrainJob `%s`.", trainjob_name)
        except ApiException as e:
            logger.warning(
                "Failed to suspend TrainJob `%s` (HTTP %s): %s",
                trainjob_name,
                e.status,
                e.reason,
            )

    def _find_and_delete_trainjob(
        self, step_run: StepRunResponse
    ) -> None:
        """Finds and deletes a TrainJob for a step run.

        Args:
            step_run: The step run whose TrainJob should be deleted.
        """
        trainjob = self._find_trainjob(step_run)
        if trainjob is None:
            return

        trainjob_name = trainjob.get("metadata", {}).get("name", "")
        namespace = self._resolve_namespace(self.config)
        custom_objects_api = self._get_custom_objects_api_from_config()

        self._delete_trainjob(
            custom_objects_api=custom_objects_api,
            namespace=namespace,
            trainjob_name=trainjob_name,
        )
