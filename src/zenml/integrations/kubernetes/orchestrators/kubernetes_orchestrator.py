# Copyright 2022 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
#
# Parts of the `prepare_or_run_pipeline()` method of this file are
# inspired by the Kubernetes dag runner implementation of tfx
"""Kubernetes-native orchestrator."""

import os
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    cast,
)

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config

from zenml.config.base_settings import BaseSettings
from zenml.enums import StackComponentType
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
    KubernetesOrchestratorConfig,
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.orchestrators import kube_utils
from zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator_entrypoint_configuration import (
    KubernetesOrchestratorEntrypointConfiguration,
)
from zenml.integrations.kubernetes.orchestrators.manifest_utils import (
    build_cron_job_manifest,
    build_pod_manifest,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.logger import get_logger
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.stack import StackValidator

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse
    from zenml.stack import Stack

logger = get_logger(__name__)

ENV_ZENML_KUBERNETES_RUN_ID = "ZENML_KUBERNETES_RUN_ID"


class KubernetesOrchestrator(ContainerizedOrchestrator):
    """Orchestrator for running ZenML pipelines using native Kubernetes."""

    _k8s_client: Optional[k8s_client.ApiClient] = None

    def get_kube_client(
        self, incluster: Optional[bool] = None
    ) -> k8s_client.ApiClient:
        """Getter for the Kubernetes API client.

        Args:
            incluster: Whether to use the in-cluster config or not. Overrides
                the `incluster` setting in the config.

        Returns:
            The Kubernetes API client.

        Raises:
            RuntimeError: if the Kubernetes connector behaves unexpectedly.
        """
        if incluster is None:
            incluster = self.config.incluster

        if incluster:
            kube_utils.load_kube_config(
                incluster=incluster,
                context=self.config.kubernetes_context,
            )
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
                incluster=incluster,
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

    @property
    def _k8s_rbac_api(self) -> k8s_client.RbacAuthorizationV1Api:
        """Getter for the Kubernetes RBAC API client.

        Returns:
            The Kubernetes RBAC API client.
        """
        return k8s_client.RbacAuthorizationV1Api(self.get_kube_client())

    @property
    def config(self) -> KubernetesOrchestratorConfig:
        """Returns the `KubernetesOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(KubernetesOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Kubernetes orchestrator.

        Returns:
            The settings class.
        """
        return KubernetesOrchestratorSettings

    def get_kubernetes_contexts(self) -> Tuple[List[str], str]:
        """Get list of configured Kubernetes contexts and the active context.

        Raises:
            RuntimeError: if the Kubernetes configuration cannot be loaded.

        Returns:
            context_name: List of configured Kubernetes contexts
            active_context_name: Name of the active Kubernetes context.
        """
        try:
            contexts, active_context = k8s_config.list_kube_config_contexts()
        except k8s_config.config_exception.ConfigException as e:
            raise RuntimeError(
                "Could not load the Kubernetes configuration"
            ) from e

        context_names = [c["name"] for c in contexts]
        active_context_name = active_context["name"]
        return context_names, active_context_name

    @property
    def validator(self) -> Optional[StackValidator]:
        """Defines the validator that checks whether the stack is valid.

        Returns:
            Stack validator.
        """

        def _validate_local_requirements(stack: "Stack") -> Tuple[bool, str]:
            """Validates that the stack contains no local components.

            Args:
                stack: The stack.

            Returns:
                Whether the stack is valid or not.
                An explanation why the stack is invalid, if applicable.
            """
            container_registry = stack.container_registry

            # should not happen, because the stack validation takes care of
            # this, but just in case
            assert container_registry is not None

            kubernetes_context = self.config.kubernetes_context
            msg = f"'{self.name}' Kubernetes orchestrator error: "

            if not self.connector:
                if not kubernetes_context:
                    return False, (
                        f"{msg}you must either link this stack component to a "
                        "Kubernetes service connector (see the 'zenml "
                        "orchestrator connect' CLI command) or explicitly set "
                        "the `kubernetes_context` attribute to the name of the "
                        "Kubernetes config context pointing to the cluster "
                        "where you would like to run pipelines."
                    )

                contexts, active_context = self.get_kubernetes_contexts()

                if kubernetes_context not in contexts:
                    return False, (
                        f"{msg}could not find a Kubernetes context named "
                        f"'{kubernetes_context}' in the local "
                        "Kubernetes configuration. Please make sure that the "
                        "Kubernetes cluster is running and that the kubeconfig "
                        "file is configured correctly. To list all configured "
                        "contexts, run:\n\n"
                        "  `kubectl config get-contexts`\n"
                    )
                if kubernetes_context != active_context:
                    logger.warning(
                        f"{msg}the Kubernetes context '{kubernetes_context}' "  # nosec
                        f"configured for the Kubernetes orchestrator is not "
                        f"the same as the active context in the local "
                        f"Kubernetes configuration. If this is not deliberate,"
                        f" you should update the orchestrator's "
                        f"`kubernetes_context` field by running:\n\n"
                        f"  `zenml orchestrator update {self.name} "
                        f"--kubernetes_context={active_context}`\n"
                        f"To list all configured contexts, run:\n\n"
                        f"  `kubectl config get-contexts`\n"
                        f"To set the active context to be the same as the one "
                        f"configured in the Kubernetes orchestrator and "
                        f"silence this warning, run:\n\n"
                        f"  `kubectl config use-context "
                        f"{kubernetes_context}`\n"
                    )

            silence_local_validations_msg = (
                f"To silence this warning, set the "
                f"`skip_local_validations` attribute to True in the "
                f"orchestrator configuration by running:\n\n"
                f"  'zenml orchestrator update {self.name} "
                f"--skip_local_validations=True'\n"
            )

            if (
                not self.config.skip_local_validations
                and not self.config.is_local
            ):
                # if the orchestrator is not running in a local k3d cluster,
                # we cannot have any other local components in our stack,
                # because we cannot mount the local path into the container.
                # This may result in problems when running the pipeline, because
                # the local components will not be available inside the
                # kubernetes containers.

                # go through all stack components and identify those that
                # advertise a local path where they persist information that
                # they need to be available when running pipelines.
                for stack_comp in stack.components.values():
                    if stack_comp.local_path is None:
                        continue
                    return False, (
                        f"{msg}the Kubernetes orchestrator is configured to "
                        f"run pipelines in a remote Kubernetes cluster but the "
                        f"'{stack_comp.name}' {stack_comp.type.value} "
                        f"is a local stack component "
                        f"and will not be available in the Kubernetes pipeline "
                        f"step.\nPlease ensure that you always use non-local "
                        f"stack components with a remote Kubernetes orchestrator, "
                        f"otherwise you may run into pipeline execution "
                        f"problems. You should use a flavor of "
                        f"{stack_comp.type.value} other than "
                        f"'{stack_comp.flavor}'.\n"
                        + silence_local_validations_msg
                    )

                # if the orchestrator is remote, the container registry must
                # also be remote.
                if container_registry.config.is_local:
                    return False, (
                        f"{msg}the Kubernetes orchestrator is configured to "
                        "run pipelines in a remote Kubernetes cluster but the "
                        f"'{container_registry.name}' container registry URI "
                        f"'{container_registry.config.uri}' "
                        f"points to a local container registry. Please ensure "
                        f"that you always use non-local stack components with "
                        f"a remote Kubernetes orchestrator, otherwise you will "
                        f"run into problems. You should use a flavor of "
                        f"container registry other than "
                        f"'{container_registry.flavor}'.\n"
                        + silence_local_validations_msg
                    )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_local_requirements,
        )

    @classmethod
    def apply_default_resource_requests(
        cls,
        memory: str,
        cpu: Optional[str] = None,
        pod_settings: Optional[KubernetesPodSettings] = None,
    ) -> KubernetesPodSettings:
        """Applies default resource requests to a pod settings object.

        Args:
            memory: The memory resource request.
            cpu: The CPU resource request.
            pod_settings: The pod settings to update. A new one will be created
                if not provided.

        Returns:
            The new or updated pod settings.
        """
        resources = {
            "requests": {"memory": memory},
        }
        if cpu:
            resources["requests"]["cpu"] = cpu
        if not pod_settings:
            pod_settings = KubernetesPodSettings(resources=resources)
        elif not pod_settings.resources:
            # We can't update the pod settings in place (because it's a frozen
            # pydantic model), so we have to create a new one.
            pod_settings = KubernetesPodSettings(
                **pod_settings.model_dump(exclude_unset=True),
                resources=resources,
            )
        else:
            set_requests = pod_settings.resources.get("requests", {})
            resources["requests"].update(set_requests)
            pod_settings.resources["requests"] = resources["requests"]

        return pod_settings

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
    ) -> Any:
        """Runs the pipeline in Kubernetes.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.

        Raises:
            RuntimeError: If the Kubernetes orchestrator is not configured.
        """
        for step_name, step in deployment.step_configurations.items():
            if self.requires_resources_in_orchestration_environment(step):
                logger.warning(
                    "Specifying step resources is not yet supported for "
                    "the Kubernetes orchestrator, ignoring resource "
                    "configuration for step %s.",
                    step_name,
                )

        pipeline_name = deployment.pipeline_configuration.name
        orchestrator_run_name = get_orchestrator_run_name(pipeline_name)
        pod_name = kube_utils.sanitize_pod_name(orchestrator_run_name)

        assert stack.container_registry

        # Get Docker image for the orchestrator pod
        try:
            image = self.get_image(deployment=deployment)
        except KeyError:
            # If no generic pipeline image exists (which means all steps have
            # custom builds) we use a random step image as all of them include
            # dependencies for the active stack
            pipeline_step_name = next(iter(deployment.step_configurations))
            image = self.get_image(
                deployment=deployment, step_name=pipeline_step_name
            )

        # Build entrypoint command and args for the orchestrator pod.
        # This will internally also build the command/args for all step pods.
        command = KubernetesOrchestratorEntrypointConfiguration.get_entrypoint_command()
        args = KubernetesOrchestratorEntrypointConfiguration.get_entrypoint_arguments(
            run_name=orchestrator_run_name,
            deployment_id=deployment.id,
            kubernetes_namespace=self.config.kubernetes_namespace,
        )

        settings = cast(
            KubernetesOrchestratorSettings, self.get_settings(deployment)
        )

        # Authorize pod to run Kubernetes commands inside the cluster.
        service_account_name = self._get_service_account_name(settings)

        # Schedule as CRON job if CRON schedule is given.
        if deployment.schedule:
            if not deployment.schedule.cron_expression:
                raise RuntimeError(
                    "The Kubernetes orchestrator only supports scheduling via "
                    "CRON jobs, but the run was configured with a manual "
                    "schedule. Use `Schedule(cron_expression=...)` instead."
                )
            cron_expression = deployment.schedule.cron_expression
            cron_job_manifest = build_cron_job_manifest(
                cron_expression=cron_expression,
                run_name=orchestrator_run_name,
                pod_name=pod_name,
                pipeline_name=pipeline_name,
                image_name=image,
                command=command,
                args=args,
                service_account_name=service_account_name,
                privileged=False,
                pod_settings=settings.orchestrator_pod_settings,
                env=environment,
                mount_local_stores=self.config.is_local,
            )

            self._k8s_batch_api.create_namespaced_cron_job(
                body=cron_job_manifest,
                namespace=self.config.kubernetes_namespace,
            )
            logger.info(
                f"Scheduling Kubernetes run `{pod_name}` with CRON expression "
                f'`"{cron_expression}"`.'
            )
            return

        # We set some default minimum resource requests for the orchestrator pod
        # here if the user has not specified any, because the orchestrator pod
        # takes up some memory resources itself and, if not specified, the pod
        # will be scheduled on any node regardless of available memory and risk
        # negatively impacting or even crashing the node due to memory pressure.
        orchestrator_pod_settings = self.apply_default_resource_requests(
            memory="400Mi",
            cpu="100m",
            pod_settings=settings.orchestrator_pod_settings,
        )

        # Create and run the orchestrator pod.
        pod_manifest = build_pod_manifest(
            run_name=orchestrator_run_name,
            pod_name=pod_name,
            pipeline_name=pipeline_name,
            image_name=image,
            command=command,
            args=args,
            privileged=False,
            pod_settings=orchestrator_pod_settings,
            service_account_name=service_account_name,
            env=environment,
            mount_local_stores=self.config.is_local,
        )

        self._k8s_core_api.create_namespaced_pod(
            namespace=self.config.kubernetes_namespace,
            body=pod_manifest,
        )

        # Wait for the orchestrator pod to finish and stream logs.
        if settings.synchronous:
            logger.info("Waiting for Kubernetes orchestrator pod...")
            kube_utils.wait_pod(
                kube_client_fn=self.get_kube_client,
                pod_name=pod_name,
                namespace=self.config.kubernetes_namespace,
                exit_condition_lambda=kube_utils.pod_is_done,
                timeout_sec=settings.timeout,
                stream_logs=True,
            )
        else:
            logger.info(
                f"Orchestration started asynchronously in pod "
                f"`{self.config.kubernetes_namespace}:{pod_name}`. "
                f"Run the following command to inspect the logs: "
                f"`kubectl logs {pod_name} -n {self.config.kubernetes_namespace}`."
            )

    def _get_service_account_name(
        self, settings: KubernetesOrchestratorSettings
    ) -> str:
        """Returns the service account name to use for the orchestrator pod.

        If the user has not specified a service account name in the settings,
        we create a new service account with the required permissions.

        Args:
            settings: The orchestrator settings.

        Returns:
            The service account name.
        """
        if settings.service_account_name:
            return settings.service_account_name
        else:
            service_account_name = "zenml-service-account"
            kube_utils.create_edit_service_account(
                core_api=self._k8s_core_api,
                rbac_api=self._k8s_rbac_api,
                service_account_name=service_account_name,
                namespace=self.config.kubernetes_namespace,
            )
            return service_account_name

    def get_orchestrator_run_id(self) -> str:
        """Returns the active orchestrator run id.

        Raises:
            RuntimeError: If the environment variable specifying the run id
                is not set.

        Returns:
            The orchestrator run id.
        """
        try:
            return os.environ[ENV_ZENML_KUBERNETES_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_KUBERNETES_RUN_ID}."
            )
