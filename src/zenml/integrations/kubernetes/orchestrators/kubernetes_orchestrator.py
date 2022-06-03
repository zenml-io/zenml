"""Kubernetes-native orchestrator."""

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

# Parts of the `prepare_or_run_pipeline()` method of this file are
# inspired by the kubernetes dag runner implementation of tfx

from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Tuple
from uuid import UUID

from kubernetes import config as k8s_config
from pydantic import root_validator
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline

from zenml.enums import StackComponentType
from zenml.environment import Environment
from zenml.integrations.kubernetes import KUBERNETES_ORCHESTRATOR_FLAVOR
from zenml.integrations.kubernetes.orchestrators import tfx_kube_utils
from zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator_entrypoint_configuration import (
    KubernetesOrchestratorEntrypointConfiguration,
)
from zenml.integrations.kubernetes.orchestrators.utils import (
    build_base_pod_manifest,
    update_pod_manifest,
)
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.repository import Repository
from zenml.stack import StackValidator
from zenml.utils.docker_utils import get_image_digest
from zenml.utils.source_utils import get_source_root_path

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.stack import Stack
    from zenml.steps import BaseStep

logger = get_logger(__name__)


class KubernetesOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines using Kubernetes.

    Attributes:
        custom_docker_base_image_name: Name of a docker image that should be
            used as the base for the image that will be run on k8s pods. If no
            custom image is given, a basic image of the active ZenML version
            will be used. **Note**: This image needs to have ZenML installed,
            otherwise the pipeline execution will fail. For that reason, you
            might want to extend the ZenML docker images found here:
            https://hub.docker.com/r/zenmldocker/zenml/
        kubernetes_context: Optional name of a kubernetes context to run
            pipelines in. If not set, the current active context will be used.
            You can find the active context by running `kubectl config
            current-context`.
        kubernetes_namespace: Name of the kubernetes namespace to be used.
            If not provided, `default` namespace will be used.
        synchronous: If `True`, running a pipeline using this orchestrator will
            block until all steps finished running on Kubernetes.
        skip_local_validations: If `True`, the local validations will be
            skipped.
        skip_cluster_provisioning: If `True`, the k3d cluster provisioning will
            be skipped.
    """

    custom_docker_base_image_name: Optional[str] = None
    kubernetes_context: Optional[str] = None
    kubernetes_namespace: str = "default"
    synchronous: bool = False
    skip_local_validations: bool = False
    skip_cluster_provisioning: bool = False

    # Class Configuration
    FLAVOR: ClassVar[str] = KUBERNETES_ORCHESTRATOR_FLAVOR

    @staticmethod
    def _get_k3d_cluster_name(uuid: UUID) -> str:
        """Returns the k3d cluster name corresponding to the orchestrator
        UUID."""
        # k3d only allows cluster names with up to 32 characters; use the
        # first 8 chars of the orchestrator UUID as identifier
        return f"zenml-kubernetes-{str(uuid)[:8]}"

    @staticmethod
    def _get_k3d_kubernetes_context(uuid: UUID) -> str:
        """Returns the name of the kubernetes context associated with the k3d
        cluster managed locally by ZenML corresponding to the orchestrator
        UUID."""
        return f"k3d-{KubernetesOrchestrator._get_k3d_cluster_name(uuid)}"

    @root_validator(skip_on_failure=True)
    def set_default_kubernetes_context(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Pydantic root_validator that sets the default `kubernetes_context`
        value to the value that is used to create the locally managed k3d
        cluster, if not explicitly set.

        Args:
            values: Values passed to the object constructor

        Returns:
            Values passed to the Pydantic constructor
        """
        if not values.get("kubernetes_context"):
            # not likely, due to Pydantic validation, but mypy complains
            assert "uuid" in values
            values["kubernetes_context"] = cls._get_k3d_kubernetes_context(
                values["uuid"]
            )

        return values

    def get_kubernetes_contexts(self) -> Tuple[List[str], str]:
        """Get the list of configured Kubernetes contexts and the active
        context.

        Raises:
            RuntimeError: if the Kubernetes configuration cannot be loaded
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
        """Validates that the stack contains a container registry and that
        requirements are met for local components."""

        def _validate_local_requirements(stack: "Stack") -> Tuple[bool, str]:

            container_registry = stack.container_registry

            # should not happen, because the stack validation takes care of
            # this, but just in case
            assert container_registry is not None

            contexts, active_context = self.get_kubernetes_contexts()

            if self.kubernetes_context not in contexts:
                if not self.is_local:
                    return False, (
                        f"Could not find a Kubernetes context named "
                        f"'{self.kubernetes_context}' in the local Kubernetes "
                        f"configuration. Please make sure that the Kubernetes "
                        f"cluster is running and that the kubeconfig file is "
                        f"configured correctly. To list all configured "
                        f"contexts, run:\n\n"
                        f"  `kubectl config get-contexts`\n"
                    )
            elif self.kubernetes_context != active_context:
                logger.warning(
                    f"The Kubernetes context '{self.kubernetes_context}' "
                    f"configured for the Kubernetes orchestrator is not the "
                    f"same as the active context in the local Kubernetes "
                    f"configuration. If this is not deliberate, you should "
                    f"update the orchestrator's `kubernetes_context` field by "
                    f"running:\n\n"
                    f"  `zenml orchestrator update {self.name} "
                    f"--kubernetes_context={active_context}`\n"
                    f"To list all configured contexts, run:\n\n"
                    f"  `kubectl config get-contexts`\n"
                    f"To set the active context to be the same as the one "
                    f"configured in the Kubernetes orchestrator and silence "
                    f"this warning, run:\n\n"
                    f"  `kubectl config use-context "
                    f"{self.kubernetes_context}`\n"
                )

            silence_local_validations_msg = (
                f"To silence this warning, set the "
                f"`skip_local_validations` attribute to True in the "
                f"orchestrator configuration by running:\n\n"
                f"  'zenml orchestrator update {self.name} "
                f"--skip_local_validations=True'\n"
            )

            if not self.skip_local_validations and not self.is_local:

                # if the orchestrator is not running in a local k3d cluster,
                # we cannot have any other local components in our stack,
                # because we cannot mount the local path into the container.
                # This may result in problems when running the pipeline, because
                # the local components will not be available inside the
                # Kubernetes containers.

                # go through all stack components and identify those that
                # advertise a local path where they persist information that
                # they need to be available when running pipelines.
                for stack_comp in stack.components.values():
                    local_path = stack_comp.local_path
                    if not local_path:
                        continue
                    return False, (
                        f"The Kubernetes orchestrator is configured to run "
                        f"pipelines in a remote Kubernetes cluster designated "
                        f"by the '{self.kubernetes_context}' configuration "
                        f"context, but the '{stack_comp.name}' "
                        f"{stack_comp.TYPE.value} is a local stack component "
                        f"and will not be available in the Kubernetes pipeline "
                        f"step.\nPlease ensure that you always use non-local "
                        f"stack components with a remote Kubernetes orchestrator, "
                        f"otherwise you may run into pipeline execution "
                        f"problems. You should use a flavor of "
                        f"{stack_comp.TYPE.value} other than "
                        f"'{stack_comp.FLAVOR}'.\n"
                        + silence_local_validations_msg
                    )

                # if the orchestrator is remote, the container registry must
                # also be remote.
                if container_registry.is_local:
                    return False, (
                        f"The Kubernetes orchestrator is configured to run "
                        f"pipelines in a remote Kubernetes cluster designated "
                        f"by the '{self.kubernetes_context}' configuration "
                        f"context, but the '{container_registry.name}' "
                        f"container registry URI '{container_registry.uri}' "
                        f"points to a local container registry. Please ensure "
                        f"that you always use non-local stack components with "
                        f"a remote Kubernetes orchestrator, otherwise you will "
                        f"run into problems. You should use a flavor of "
                        f"container registry other than "
                        f"'{container_registry.FLAVOR}'.\n"
                        + silence_local_validations_msg
                    )

            if not self.skip_local_validations and self.is_local:

                # if the orchestrator is local, the container registry must
                # also be local.
                if not container_registry.is_local:
                    return False, (
                        f"The Kubernetes orchestrator is configured to run "
                        f"pipelines in a local k3d Kubernetes cluster "
                        f"designated by the '{self.kubernetes_context}' "
                        f"configuration context, but the container registry "
                        f"URI '{container_registry.uri}' doesn't match the "
                        f"expected format 'localhost:$PORT'. "
                        f"The local Kubernetes orchestrator only works with a "
                        f"local container registry because it cannot "
                        f"currently authenticate to external container "
                        f"registries. You should use a flavor of container "
                        f"registry other than '{container_registry.FLAVOR}'.\n"
                        + silence_local_validations_msg
                    )

            return True, ""

        return StackValidator(
            required_components={StackComponentType.CONTAINER_REGISTRY},
            custom_validation_function=_validate_local_requirements,
        )

    def get_docker_image_name(self, pipeline_name: str) -> str:
        """Returns the full docker image name including registry and tag."""

        base_image_name = f"zenml-kubernetes:{pipeline_name}"
        container_registry = Repository().active_stack.container_registry

        if container_registry:
            registry_uri = container_registry.uri.rstrip("/")
            return f"{registry_uri}/{base_image_name}"
        else:
            return base_image_name

    @property
    def is_local(self) -> bool:
        """Returns `True` if the k8s orchestrator is running locally (i.e. in
        the local k3d cluster managed by ZenML).
        """
        return self.kubernetes_context == self._get_k3d_kubernetes_context(
            self.uuid
        )

    def prepare_pipeline_deployment(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> None:
        """Builds a docker image for the current environment and uploads it to
        a container registry if configured.
        """
        from zenml.utils import docker_utils

        image_name = self.get_docker_image_name(pipeline.name)

        requirements = {*stack.requirements(), *pipeline.requirements}

        logger.debug("Kubernetes container requirements: %s", requirements)

        docker_utils.build_docker_image(
            build_context_path=get_source_root_path(),
            image_name=image_name,
            dockerignore_path=pipeline.dockerignore_file,
            requirements=requirements,
            base_image=self.custom_docker_base_image_name,
        )

        assert stack.container_registry  # should never happen due to validation
        stack.container_registry.push_image(image_name)

        # Store the docker image digest in the runtime configuration so it gets
        # tracked in the ZenStore
        image_digest = docker_utils.get_image_digest(image_name) or image_name
        runtime_configuration["docker_image"] = image_digest

    def prepare_or_run_pipeline(
        self,
        sorted_steps: List["BaseStep"],
        pipeline: "BasePipeline",
        pb2_pipeline: Pb2Pipeline,
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        """"""

        # First check whether the code running in a notebook
        if Environment.in_notebook():
            raise RuntimeError(
                "The Kubernetes orchestrator cannot run pipelines in a notebook "
                "environment. The reason is that it is non-trivial to create "
                "a Docker image of a notebook. Please consider refactoring "
                "your notebook cells into separate scripts in a Python module "
                "and run the code outside of a notebook when using this "
                "orchestrator."
            )

        assert runtime_configuration.run_name, "Run name must be set"

        run_name = runtime_configuration.run_name
        pipeline_name = pipeline.name

        # Get docker image name (for all pods).
        image_name = self.get_docker_image_name(pipeline.name)
        image_name = get_image_digest(image_name) or image_name

        # Get step dependencies, e.g., {"step": ["upstream_step_1", ...], ...}
        step_dependencies = {
            step.name: self.get_upstream_step_names(step, pb2_pipeline)
            for step in sorted_steps
        }

        # Build entrypoint command and args for the orchestrator pod.
        # This will internally also build the command/args for all step pods.
        command = (
            KubernetesOrchestratorEntrypointConfiguration.get_entrypoint_command()
        )
        args = KubernetesOrchestratorEntrypointConfiguration.get_entrypoint_arguments(
            run_name=run_name,
            pipeline_name=pipeline_name,
            image_name=image_name,
            kubernetes_namespace=self.kubernetes_namespace,
            pb2_pipeline=pb2_pipeline,
            sorted_steps=sorted_steps,
            step_dependencies=step_dependencies,
        )

        # Build manifest for the orchestrator pod.
        pod_name = tfx_kube_utils.sanitize_pod_name(run_name)
        pod_manifest = build_base_pod_manifest(
            run_name=run_name,
            pipeline_name=pipeline_name,
            image_name=image_name,
        )
        pod_manifest = update_pod_manifest(
            base_pod_manifest=pod_manifest,
            pod_name=pod_name,
            command=command,
            args=args,
        )
        pod_manifest["spec"]["serviceAccountName"] = "zenml-service-account"

        # Create and run the orchestrator pod.
        core_api = tfx_kube_utils.make_core_v1_api()
        core_api.create_namespaced_pod(
            namespace=self.kubernetes_namespace,
            body=pod_manifest,
        )
        logger.info("Kubernetes orchestrator pod started.")

        # Wait for the orchestrator pod to finish.
        tfx_kube_utils.wait_pod(
            core_api,
            pod_name,
            namespace=self.kubernetes_namespace,
            exit_condition_lambda=tfx_kube_utils.pod_is_done,
            condition_description="done state",
        )
        logger.info("Pipeline run finished.")
