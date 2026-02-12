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
import random
import re
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, cast

from zenml.config.base_settings import BaseSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import StackComponentType
from zenml.integrations.kubeflow.flavors import (
    KubeflowTrainerStepOperatorConfig,
    KubeflowTrainerStepOperatorSettings,
)
from zenml.integrations.kubeflow.step_operators.kubeflow_trainer_step_operator_entrypoint_configuration import (
    KubeflowTrainerStepOperatorEntrypointConfiguration,
)
from zenml.integrations.kubeflow.step_operators.trainer_job_watcher import (
    wait_for_trainjob_to_finish,
)
from zenml.integrations.kubeflow.step_operators.trainjob_manifest_utils import (
    TRAINJOB_GROUP,
    TRAINJOB_PLURAL,
    TRAINJOB_VERSION,
    build_trainjob_manifest,
)
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator
from zenml.step_operators.step_operator_entrypoint_configuration import (
    StepOperatorEntrypointConfiguration,
)

if TYPE_CHECKING:
    from kubernetes import client as k8s_client

    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineSnapshotBase

logger = get_logger(__name__)

KUBEFLOW_TRAINER_STEP_OPERATOR_DOCKER_IMAGE_KEY = (
    "kubeflow_trainer_step_operator"
)
_TRAINJOB_NAME_SUFFIX = "trainer"
_TRAINJOB_STEP_SEGMENT_MAX_LENGTH = 10


def _sanitize_kubernetes_name(name: str) -> str:
    """Sanitizes a Kubernetes resource name.

    Args:
        name: Name to sanitize.

    Returns:
        Sanitized resource name.
    """
    sanitized = re.sub(r"[^a-z0-9-]", "-", name.lower())
    sanitized = re.sub(r"^-+", "", sanitized)
    sanitized = re.sub(r"-+", "-", sanitized)
    sanitized = sanitized[:63]
    return re.sub(r"-+$", "", sanitized)


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
        try:
            from kubernetes import client as k8s_client
        except ImportError as e:
            raise ImportError(
                "Missing optional dependency `kubernetes`. Install the "
                "`kubeflow` integration dependencies to use the "
                "`kubeflow_trainer` step operator."
            ) from e

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

    def _get_k8s_custom_objects_api(
        self, settings: KubeflowTrainerStepOperatorSettings
    ) -> "k8s_client.CustomObjectsApi":
        """Kubernetes CustomObjectsApi client.

        Returns:
            CustomObjectsApi client.
        """
        from kubernetes import client as k8s_client

        return k8s_client.CustomObjectsApi(self.get_kube_client(settings))

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
            Exception: Any non-404 API exception.
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
        except Exception as e:
            if getattr(e, "status", None) == 404:
                return
            raise

    def launch(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Launches a step using Kubeflow Trainer v2.

        Args:
            info: Step run information.
            entrypoint_command: Command that executes the step entrypoint.
            environment: Environment variables for step execution.
        """
        settings = cast(
            KubeflowTrainerStepOperatorSettings,
            self.get_settings(info),
        )
        custom_objects_api = self._get_k8s_custom_objects_api(settings)

        image_name = settings.image or info.get_image(
            key=KUBEFLOW_TRAINER_STEP_OPERATOR_DOCKER_IMAGE_KEY
        )
        command = entrypoint_command[:3]
        args = entrypoint_command[3:]

        namespace = self._resolve_namespace(settings)
        random_prefix = random.choice("abcdef") + "".join(
            random.choices("0123456789abcdef", k=7)
        )
        # Keep compact to avoid Kubernetes 63-char name limits on derived resources.
        step_segment = _sanitize_kubernetes_name(info.pipeline_step_name)[
            :_TRAINJOB_STEP_SEGMENT_MAX_LENGTH
        ]
        if not step_segment:
            step_segment = "step"
        trainjob_name = _sanitize_kubernetes_name(
            f"{random_prefix}-{step_segment}-{_TRAINJOB_NAME_SUFFIX}"
        )

        labels = {
            "project_id": _sanitize_kubernetes_name(
                str(info.snapshot.project_id)
            ),
            "run_id": _sanitize_kubernetes_name(str(info.run_id)),
            "run_name": _sanitize_kubernetes_name(str(info.run_name)),
            "pipeline": _sanitize_kubernetes_name(info.pipeline.name),
            "step_name": _sanitize_kubernetes_name(info.pipeline_step_name),
        }
        annotations = {
            "zenml.step_operator": str(self.id),
            "zenml.step_name": info.pipeline_step_name,
        }

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

        try:
            wait_for_trainjob_to_finish(
                custom_objects_api=custom_objects_api,
                namespace=namespace,
                name=trainjob_name,
                poll_interval_seconds=settings.poll_interval_seconds,
                timeout_seconds=settings.timeout_seconds,
            )
        finally:
            if settings.delete_trainjob_after_completion:
                self._delete_trainjob(
                    custom_objects_api=custom_objects_api,
                    namespace=namespace,
                    trainjob_name=trainjob_name,
                )
