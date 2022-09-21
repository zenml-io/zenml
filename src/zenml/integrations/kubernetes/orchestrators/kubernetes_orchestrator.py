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

from typing import TYPE_CHECKING, Any, ClassVar, List, Optional, Tuple

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config

from zenml.constants import ORCHESTRATOR_DOCKER_IMAGE_KEY
from zenml.enums import StackComponentType
from zenml.environment import Environment
from zenml.integrations.kubernetes import KUBERNETES_ORCHESTRATOR_FLAVOR
from zenml.integrations.kubernetes.orchestrators import kube_utils
from zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator_entrypoint_configuration import (
    KubernetesOrchestratorEntrypointConfiguration,
)
from zenml.integrations.kubernetes.orchestrators.manifest_utils import (
    build_cron_job_manifest,
    build_pod_manifest,
)
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.stack import StackValidator
from zenml.utils import deprecation_utils
from zenml.utils.pipeline_docker_image_builder import PipelineDockerImageBuilder

if TYPE_CHECKING:
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.stack import Stack

logger = get_logger(__name__)


class KubernetesOrchestrator(BaseOrchestrator, PipelineDockerImageBuilder):
    """Orchestrator for running ZenML pipelines using native Kubernetes.

    Attributes:
        custom_docker_base_image_name: Name of a Docker image that should be
            used as the base for the image that will be run on Kubernetes pods.
            If no custom image is given, a basic image of the active ZenML
            version will be used.
            **Note**: This image needs to have ZenML installed,
            otherwise the pipeline execution will fail. For that reason, you
            might want to extend the ZenML Docker images found here:
            https://hub.docker.com/r/zenmldocker/zenml/
        kubernetes_context: Optional name of a Kubernetes context to run
            pipelines in. If not set, the current active context will be used.
            You can find the active context by running `kubectl config
            current-context`.
        kubernetes_namespace: Name of the Kubernetes namespace to be used.
            If not provided, `zenml` namespace will be used.
        synchronous: If `True`, running a pipeline using this orchestrator will
            block until all steps finished running on Kubernetes.
        skip_config_loading: If `True`, don't load the Kubernetes context and
            clients. This is only useful for unit testing.
    """

    custom_docker_base_image_name: Optional[str] = None
    kubernetes_context: Optional[str] = None
    kubernetes_namespace: str = "zenml"
    synchronous: bool = False
    skip_config_loading: bool = False
    _k8s_core_api: k8s_client.CoreV1Api = None
    _k8s_batch_api: k8s_client.BatchV1beta1Api = None
    _k8s_rbac_api: k8s_client.RbacAuthorizationV1Api = None

    FLAVOR: ClassVar[str] = KUBERNETES_ORCHESTRATOR_FLAVOR

    _deprecation_validator = deprecation_utils.deprecate_pydantic_attributes(
        ("custom_docker_base_image_name", "docker_parent_image")
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the Pydantic object the Kubernetes clients.

        Args:
            *args: The positional arguments to pass to the Pydantic object.
            **kwargs: The keyword arguments to pass to the Pydantic object.
        """
        super().__init__(*args, **kwargs)
        self._initialize_k8s_clients()

    def _initialize_k8s_clients(self) -> None:
        """Initialize the Kubernetes clients."""
        if self.skip_config_loading:
            return
        kube_utils.load_kube_config(context=self.kubernetes_context)
        self._k8s_core_api = k8s_client.CoreV1Api()
        self._k8s_batch_api = k8s_client.BatchV1beta1Api()
        self._k8s_rbac_api = k8s_client.RbacAuthorizationV1Api()

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

            if not self.skip_config_loading:
                contexts, active_context = self.get_kubernetes_contexts()
                if self.kubernetes_context not in contexts:
                    return False, (
                        f"Could not find a Kubernetes context named "
                        f"'{self.kubernetes_context}' in the local Kubernetes "
                        f"configuration. Please make sure that the Kubernetes "
                        f"cluster is running and that the kubeconfig file is "
                        f"configured correctly. To list all configured "
                        f"contexts, run:\n\n"
                        f"  `kubectl config get-contexts`\n"
                    )
                if self.kubernetes_context != active_context:
                    logger.warning(
                        f"The Kubernetes context '{self.kubernetes_context}' "
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
                        f"{self.kubernetes_context}`\n"
                    )

            # Check that all stack components are non-local.
            for stack_comp in stack.components.values():
                if stack_comp.local_path:
                    return False, (
                        f"The Kubernetes orchestrator currently only supports "
                        f"remote stacks, but the '{stack_comp.name}' "
                        f"{stack_comp.TYPE.value} is a local component. "
                        f"Please make sure to only use non-local stack "
                        f"components with a Kubernetes orchestrator."
                    )

            # if the orchestrator is remote, the container registry must
            # also be remote.
            if container_registry.is_local:
                return False, (
                    f"The Kubernetes orchestrator requires a remote container "
                    f"registry, but the '{container_registry.name}' container "
                    f"registry of your active stack points to a local URI "
                    f"'{container_registry.uri}'. Please make sure stacks "
                    f"with a Kubernetes orchestrator always contain remote "
                    f"container registries."
                )

            return True, ""

        return StackValidator(
            required_components={StackComponentType.CONTAINER_REGISTRY},
            custom_validation_function=_validate_local_requirements,
        )

    def prepare_pipeline_deployment(
        self,
        deployment: "PipelineDeployment",
        stack: "Stack",
    ) -> None:
        """Build a Docker image and push it to the container registry.

        Args:
            deployment: The pipeline deployment configuration.
            stack: The stack on which the pipeline will be deployed.
        """
        repo_digest = self.build_and_push_docker_image(
            deployment=deployment, stack=stack
        )
        deployment.add_extra(ORCHESTRATOR_DOCKER_IMAGE_KEY, repo_digest)

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeployment",
        stack: "Stack",
    ) -> Any:
        """Runs the pipeline in Kubernetes.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.

        Raises:
            RuntimeError: If trying to run from a Jupyter notebook.
        """
        # First check whether the code is running in a notebook.
        if Environment.in_notebook():
            raise RuntimeError(
                "The Kubernetes orchestrator cannot run pipelines in a notebook "
                "environment. The reason is that it is non-trivial to create "
                "a Docker image of a notebook. Please consider refactoring "
                "your notebook cells into separate scripts in a Python module "
                "and run the code outside of a notebook when using this "
                "orchestrator."
            )

        for step in deployment.steps.values():
            if self.requires_resources_in_orchestration_environment(step):
                logger.warning(
                    "Specifying step resources is not yet supported for "
                    "the Kubernetes orchestrator, ignoring resource "
                    "configuration for step %s.",
                    step.config.name,
                )

        run_name = deployment.run_name
        pipeline_name = deployment.pipeline.name
        pod_name = kube_utils.sanitize_pod_name(run_name)

        # Get Docker image name (for all pods).
        image_name = deployment.pipeline.extra[ORCHESTRATOR_DOCKER_IMAGE_KEY]

        # Build entrypoint command and args for the orchestrator pod.
        # This will internally also build the command/args for all step pods.
        command = (
            KubernetesOrchestratorEntrypointConfiguration.get_entrypoint_command()
        )
        args = KubernetesOrchestratorEntrypointConfiguration.get_entrypoint_arguments(
            run_name=run_name,
            image_name=image_name,
            kubernetes_namespace=self.kubernetes_namespace,
        )

        # Authorize pod to run Kubernetes commands inside the cluster.
        service_account_name = "zenml-service-account"
        kube_utils.create_edit_service_account(
            core_api=self._k8s_core_api,
            rbac_api=self._k8s_rbac_api,
            service_account_name=service_account_name,
            namespace=self.kubernetes_namespace,
        )

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
                run_name=run_name,
                pod_name=pod_name,
                pipeline_name=pipeline_name,
                image_name=image_name,
                command=command,
                args=args,
                service_account_name=service_account_name,
            )
            self._k8s_batch_api.create_namespaced_cron_job(
                body=cron_job_manifest, namespace=self.kubernetes_namespace
            )
            logger.info(
                f"Scheduling Kubernetes run `{pod_name}` with CRON expression "
                f'`"{cron_expression}"`.'
            )
            return

        # Create and run the orchestrator pod.
        pod_manifest = build_pod_manifest(
            run_name=run_name,
            pod_name=pod_name,
            pipeline_name=pipeline_name,
            image_name=image_name,
            command=command,
            args=args,
            service_account_name=service_account_name,
        )
        self._k8s_core_api.create_namespaced_pod(
            namespace=self.kubernetes_namespace,
            body=pod_manifest,
        )

        # Wait for the orchestrator pod to finish and stream logs.
        if self.synchronous:
            logger.info("Waiting for Kubernetes orchestrator pod...")
            kube_utils.wait_pod(
                core_api=self._k8s_core_api,
                pod_name=pod_name,
                namespace=self.kubernetes_namespace,
                exit_condition_lambda=kube_utils.pod_is_done,
                stream_logs=True,
            )
        else:
            logger.info(
                f"Orchestration started asynchronously in pod "
                f"`{self.kubernetes_namespace}:{pod_name}`. "
                f"Run the following command to inspect the logs: "
                f"`kubectl logs {pod_name} -n {self.kubernetes_namespace}`."
            )
