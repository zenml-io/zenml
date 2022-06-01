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
from zenml.integrations.kubernetes.orchestrators import kube_utils
from zenml.integrations.kubernetes.orchestrators.kubernetes_entrypoint_configuration import (
    KUBERNETES_JOB_ID_OPTION,
    KubernetesEntrypointConfiguration,
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
        synchronous: If `True`, running a pipeline using this orchestrator will
            block until all steps finished running on Kubernetes.
        skip_local_validations: If `True`, the local validations will be
            skipped.
        skip_cluster_provisioning: If `True`, the k3d cluster provisioning will
            be skipped.
    """

    custom_docker_base_image_name: Optional[str] = None
    kubernetes_context: Optional[str] = None
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

    # @property
    # def root_directory(self) -> str:
    #     """Returns path to the root directory for all files concerning
    #     this orchestrator."""
    #     return os.path.join(
    #         zenml.io.utils.get_global_config_directory(),
    #         "kubernetes",
    #         str(self.uuid),
    #     )

    # @property
    # def pipeline_directory(self) -> str:
    #     """Returns path to a directory in which the kubeflow pipeline files
    #     are stored."""
    #     return os.path.join(self.root_directory, "pipelines")

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
            # environment_vars=self._get_environment_vars_from_secrets(
            #     pipeline.secrets
            # ),
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

        image_name = self.get_docker_image_name(pipeline.name)
        image_name = get_image_digest(image_name) or image_name

        command = KubernetesEntrypointConfiguration.get_entrypoint_command()
        core_api = kube_utils.make_core_v1_api()

        for step in sorted_steps:

            step_name = step.name

            args = KubernetesEntrypointConfiguration.get_entrypoint_arguments(
                step=step,
                pb2_pipeline=pb2_pipeline,
                **{KUBERNETES_JOB_ID_OPTION: run_name},
            )
            pod_name = f"{pipeline_name}-{step_name}-{run_name}"
            pod_name = pod_name.lower().replace("_", "-")  # happy now, k8s?
            pod_manifest = {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": pod_name,
                },
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [
                        {
                            "name": "main",
                            "image": image_name,
                            "command": command,
                            "args": args,
                        }
                    ],
                },
            }

            core_api.create_namespaced_pod(
                namespace="default",  # TODO: don't hardcode
                body=pod_manifest,
            )

            kube_utils.wait_pod(
                core_api,
                pod_name,
                namespace="default",  # TODO: don't hardcode
                exit_condition_lambda=kube_utils.pod_is_done,
                condition_description="done state",
            )

    # @property
    # def _k3d_cluster_name(self) -> str:
    #     """Returns the K3D cluster name."""
    #     return self._get_k3d_cluster_name(self.uuid)

    # def _get_k3d_registry_name(self, port: int) -> str:
    #     """Returns the K3D registry name."""
    #     return f"k3d-zenml-kubernetes-registry.localhost:{port}"

    # @property
    # def _k3d_registry_config_path(self) -> str:
    #     """Returns the path to the K3D registry config yaml."""
    #     return os.path.join(self.root_directory, "k3d_registry.yaml")

    # @property
    # def is_provisioned(self) -> bool:
    #     """Returns if a local k3d cluster for this orchestrator exists."""
    #     if not local_deployment_utils.check_prerequisites(
    #         skip_k3d=self.skip_cluster_provisioning or not self.is_local,
    #         skip_kubectl=self.skip_cluster_provisioning,
    #     ):
    #         # if any prerequisites are missing there is certainly no
    #         # local deployment running
    #         return False

    #     return self.is_cluster_provisioned

    # @property
    # def is_running(self) -> bool:
    #     """Returns if the local k3d cluster for this orchestrator is running.

    #     For remote (i.e. not managed by ZenML) Kubernetes installations,
    #     this always returns True.
    #     """
    #     return self.is_provisioned and self.is_cluster_running

    # @property
    # def is_suspended(self) -> bool:
    #     """Returns if the local k3d cluster is stopped."""
    #     return self.is_provisioned and (
    #         self.skip_cluster_provisioning or not self.is_cluster_running
    #     )

    # @property
    # def is_cluster_provisioned(self) -> bool:
    #     """Returns if the local k3d cluster for this orchestrator is provisioned.

    #     For remote (i.e. not managed by ZenML) Kubeflow Pipelines installations,
    #     this always returns True.
    #     """
    #     if self.skip_cluster_provisioning or not self.is_local:
    #         return True
    #     return local_deployment_utils.k3d_cluster_exists(
    #         cluster_name=self._k3d_cluster_name
    #     )

    # @property
    # def is_cluster_running(self) -> bool:
    #     """Returns if the local k3d cluster of this orchestrator is running."""
    #     if self.skip_cluster_provisioning or not self.is_local:
    #         return True
    #     return local_deployment_utils.k3d_cluster_running(
    #         cluster_name=self._k3d_cluster_name
    #     )

    # def provision(self) -> None:
    #     """Provisions a local Kubernetes deployment."""
    #     if self.skip_cluster_provisioning:
    #         return

    #     if self.is_running:
    #         logger.info(
    #             "Found already existing local Kubernetes deployment. "
    #             "If there are any issues with the existing deployment, please "
    #             "run 'zenml stack down --yes' to delete it."
    #         )
    #         return

    #     if not local_deployment_utils.check_prerequisites():
    #         raise ProvisioningError(
    #             "Unable to provision local Kubernetes deployment: "
    #             "Please install 'k3d' and 'kubectl' and try again."
    #         )

    #     container_registry = Repository().active_stack.container_registry

    #     # should not happen, because the stack validation takes care of this,
    #     # but just in case
    #     assert container_registry is not None

    #     fileio.makedirs(self.root_directory)

    #     if not self.is_local:
    #         # don't provision any resources if using a remote installation
    #         return

    #     logger.info("Provisioning local Kubernetes deployment...")

    #     container_registry_port = int(container_registry.uri.split(":")[-1])
    #     container_registry_name = self._get_k3d_registry_name(
    #         port=container_registry_port
    #     )
    #     local_deployment_utils.write_local_registry_yaml(
    #         yaml_path=self._k3d_registry_config_path,
    #         registry_name=container_registry_name,
    #         registry_uri=container_registry.uri,
    #     )

    #     try:
    #         local_deployment_utils.create_k3d_cluster(
    #             cluster_name=self._k3d_cluster_name,
    #             registry_name=container_registry_name,
    #             registry_config_path=self._k3d_registry_config_path,
    #         )
    #         kubernetes_context = self.kubernetes_context

    #         # will never happen, but mypy doesn't know that
    #         assert kubernetes_context is not None

    #         local_deployment_utils.deploy_kubeflow_pipelines(
    #             kubernetes_context=kubernetes_context
    #         )  # TODO: adjust

    #         artifact_store = Repository().active_stack.artifact_store
    #         if isinstance(artifact_store, LocalArtifactStore):
    #             local_deployment_utils.add_hostpath_to_kubeflow_pipelines(
    #                 kubernetes_context=kubernetes_context,
    #                 local_path=artifact_store.path,
    #             )  # TODO: adjust
    #     except Exception as e:
    #         logger.error(e)
    #         logger.error("Unable to spin up local Kubernetes deployment.")

    #         self.list_manual_setup_steps(
    #             container_registry_name, self._k3d_registry_config_path
    #         )
    #         self.deprovision()

    # def deprovision(self) -> None:
    #     """Deprovisions a local Kubernetes deployment."""
    #     if self.skip_cluster_provisioning:
    #         return

    #     if self.is_local:
    #         # don't deprovision any resources if using a remote installation
    #         local_deployment_utils.delete_k3d_cluster(
    #             cluster_name=self._k3d_cluster_name
    #         )

    #         logger.info("Local Kubernetes deployment deprovisioned.")

    #     if fileio.exists(self.log_file):
    #         fileio.remove(self.log_file)

    # def resume(self) -> None:
    #     """Resumes the local k3d cluster."""
    #     if self.is_running:
    #         logger.info("Local Kubernetes deployment already running.")
    #         return

    #     if not self.is_provisioned:
    #         raise ProvisioningError(
    #             "Unable to resume local Kubernetes deployment: No "
    #             "resources provisioned for local deployment."
    #         )

    #     kubernetes_context = self.kubernetes_context

    #     # will never happen, but mypy doesn't know that
    #     assert kubernetes_context is not None

    #     if (
    #         not self.skip_cluster_provisioning
    #         and self.is_local
    #         and not self.is_cluster_running
    #     ):
    #         # don't resume any resources if using a remote installation
    #         local_deployment_utils.start_k3d_cluster(
    #             cluster_name=self._k3d_cluster_name
    #         )

    #         local_deployment_utils.wait_until_kubeflow_pipelines_ready(
    #             kubernetes_context=kubernetes_context
    #         )  # TODO: adjust

    # def suspend(self) -> None:
    #     """Suspends the local k3d cluster."""
    #     if not self.is_provisioned:
    #         logger.info("Local Kubernetes deployment not provisioned.")
    #         return

    #     if (
    #         not self.skip_cluster_provisioning
    #         and self.is_local
    #         and self.is_cluster_running
    #     ):
    #         # don't suspend any resources if using a remote installation
    #         local_deployment_utils.stop_k3d_cluster(
    #             cluster_name=self._k3d_cluster_name
    #         )

    # def _get_environment_vars_from_secrets(
    #     self, secrets: List[str]
    # ) -> Dict[str, str]:
    #     """Get key-value pairs from list of secrets provided by the user.

    #     Args:
    #         secrets: List of secrets provided by the user.

    #     Returns:
    #         A dictionary of key-value pairs.

    #     Raises:
    #         ProvisioningError: If the stack has no secrets manager."""
    #     environment_vars: Dict[str, str] = {}
    #     secret_manager = Repository().active_stack.secrets_manager
    #     if secrets and secret_manager:
    #         for secret in secrets:
    #             secret_schema = secret_manager.get_secret(secret)
    #             environment_vars.update(secret_schema.content)
    #     elif secrets and not secret_manager:
    #         raise ProvisioningError(
    #             "Unable to provision local Kubernetes deployment: "
    #             f"You passed in the following secrets: { ', '.join(secrets) }, "
    #             "however, no secrets manager is registered for the current "
    #             "stack."
    #         )
    #     else:
    #         # No secrets provided by the user.
    #         pass
    #     return environment_vars
