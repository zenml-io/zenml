#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Kubernetes step operator implementation."""

import random
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, cast

from kubernetes import client as k8s_client

from zenml.config.base_settings import BaseSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import StackComponentType
from zenml.integrations.kubernetes.constants import (
    STEP_NAME_ANNOTATION_KEY,
    STEP_OPERATOR_ANNOTATION_KEY,
)
from zenml.integrations.kubernetes.flavors import (
    KubernetesStepOperatorConfig,
    KubernetesStepOperatorSettings,
)
from zenml.integrations.kubernetes.orchestrators import (
    kube_utils,
)
from zenml.integrations.kubernetes.orchestrators.manifest_utils import (
    build_job_manifest,
    build_pod_manifest,
    pod_template_manifest_from_pod,
)
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineDeploymentBase

logger = get_logger(__name__)

KUBERNETES_STEP_OPERATOR_DOCKER_IMAGE_KEY = "kubernetes_step_operator"


class KubernetesStepOperator(BaseStepOperator):
    """Step operator to run on Kubernetes."""

    _k8s_client: Optional[k8s_client.ApiClient] = None

    @property
    def config(self) -> KubernetesStepOperatorConfig:
        """Returns the `KubernetesStepOperatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(KubernetesStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Kubernetes step operator.

        Returns:
            The settings class.
        """
        return KubernetesStepOperatorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack.

        Returns:
            A validator that checks that the stack contains a remote container
            registry and a remote artifact store.
        """

        def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The Kubernetes step operator runs code remotely and "
                    "needs to write files into the artifact store, but the "
                    f"artifact store `{stack.artifact_store.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote artifact store when using the Vertex "
                    "step operator."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The Kubernetes step operator runs code remotely and "
                    "needs to push/pull Docker images, but the "
                    f"container registry `{container_registry.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote container registry when using the "
                    "Kubernetes step operator."
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
        self, deployment: "PipelineDeploymentBase"
    ) -> List["BuildConfiguration"]:
        """Gets the Docker builds required for the component.

        Args:
            deployment: The pipeline deployment for which to get the builds.

        Returns:
            The required Docker builds.
        """
        builds = []
        for step_name, step in deployment.step_configurations.items():
            if step.config.uses_step_operator(self.name):
                build = BuildConfiguration(
                    key=KUBERNETES_STEP_OPERATOR_DOCKER_IMAGE_KEY,
                    settings=step.config.docker_settings,
                    step_name=step_name,
                )
                builds.append(build)

        return builds

    def get_kube_client(self) -> k8s_client.ApiClient:
        """Get the Kubernetes API client.

        Returns:
            The Kubernetes API client.

        Raises:
            RuntimeError: If the service connector returns an unexpected client.
        """
        if self.config.incluster:
            kube_utils.load_kube_config(incluster=True)
            self._k8s_client = k8s_client.ApiClient()
            return self._k8s_client

        # Refresh the client also if the connector has expired
        if self._k8s_client and not self.connector_has_expired():
            return self._k8s_client

        connector = self.get_connector()
        if connector:
            client = connector.connect()
            if not isinstance(client, k8s_client.ApiClient):
                raise RuntimeError(
                    f"Expected a k8s_client.ApiClient while trying to use the "
                    f"linked connector, but got {type(client)}."
                )
            self._k8s_client = client
        else:
            kube_utils.load_kube_config(
                context=self.config.kubernetes_context,
            )
            self._k8s_client = k8s_client.ApiClient()

        return self._k8s_client

    @property
    def _k8s_core_api(self) -> k8s_client.CoreV1Api:
        """Getter for the Kubernetes Core API client.

        Returns:
            The Kubernetes Core API client.
        """
        return k8s_client.CoreV1Api(self.get_kube_client())

    @property
    def _k8s_batch_api(self) -> k8s_client.BatchV1Api:
        """Getter for the Kubernetes Batch API client.

        Returns:
            The Kubernetes Batch API client.
        """
        return k8s_client.BatchV1Api(self.get_kube_client())

    def launch(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Launches a step on Kubernetes.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables to set in the step operator
                environment.
        """
        settings = cast(
            KubernetesStepOperatorSettings, self.get_settings(info)
        )
        image_name = info.get_image(
            key=KUBERNETES_STEP_OPERATOR_DOCKER_IMAGE_KEY
        )
        command = entrypoint_command[:3]
        args = entrypoint_command[3:]

        step_labels = {
            "run_id": kube_utils.sanitize_label(str(info.run_id)),
            "run_name": kube_utils.sanitize_label(str(info.run_name)),
            "pipeline": kube_utils.sanitize_label(info.pipeline.name),
            "step_name": kube_utils.sanitize_label(info.pipeline_step_name),
        }
        step_annotations = {
            STEP_NAME_ANNOTATION_KEY: info.pipeline_step_name,
            STEP_OPERATOR_ANNOTATION_KEY: str(self.id),
        }

        # We set some default minimum memory resource requests for the step pod
        # here if the user has not specified any, because the step pod takes up
        # some memory resources itself and, if not specified, the pod will be
        # scheduled on any node regardless of available memory and risk
        # negatively impacting or even crashing the node due to memory pressure.
        pod_settings = kube_utils.apply_default_resource_requests(
            memory="400Mi",
            pod_settings=settings.pod_settings,
        )

        pod_manifest = build_pod_manifest(
            pod_name=None,
            image_name=image_name,
            command=command,
            args=args,
            env=environment,
            privileged=settings.privileged,
            pod_settings=pod_settings,
            service_account_name=settings.service_account_name,
            labels=step_labels,
        )

        job_name = settings.job_name_prefix or ""
        random_prefix = "".join(random.choices("0123456789abcdef", k=8))
        job_name += f"-{random_prefix}-{info.pipeline_step_name}-{info.pipeline.name}-step-operator"
        # The job name will be used as a label on the pods, so we need to make
        # sure it doesn't exceed the label length limit
        job_name = kube_utils.sanitize_label(job_name)

        job_manifest = build_job_manifest(
            job_name=job_name,
            pod_template=pod_template_manifest_from_pod(pod_manifest),
            # The orchestrator already handles retries, so we don't need to
            # retry the step operator job.
            backoff_limit=0,
            ttl_seconds_after_finished=settings.ttl_seconds_after_finished,
            active_deadline_seconds=settings.active_deadline_seconds,
            labels=step_labels,
            annotations=step_annotations,
        )

        kube_utils.create_job(
            batch_api=self._k8s_batch_api,
            namespace=self.config.kubernetes_namespace,
            job_manifest=job_manifest,
        )

        logger.info(
            "Waiting for step operator job `%s` to finish...",
            job_name,
        )
        kube_utils.wait_for_job_to_finish(
            batch_api=self._k8s_batch_api,
            core_api=self._k8s_core_api,
            namespace=self.config.kubernetes_namespace,
            job_name=job_name,
            fail_on_container_waiting_reasons=settings.fail_on_container_waiting_reasons,
            stream_logs=True,
        )
        logger.info("Step operator job completed.")
