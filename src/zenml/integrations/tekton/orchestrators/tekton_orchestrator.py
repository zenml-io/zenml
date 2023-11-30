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
"""Implementation of the Tekton orchestrator."""
import os
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast

import yaml
from kfp import dsl
from kfp_tekton.compiler import TektonCompiler
from kfp_tekton.compiler.pipeline_utils import TektonPipelineConf
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config

from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    ENV_ZENML_LOCAL_STORES_PATH,
)
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.enums import StackComponentType
from zenml.environment import Environment
from zenml.integrations.kubeflow.utils import apply_pod_settings
from zenml.integrations.tekton.flavors.tekton_orchestrator_flavor import (
    TektonOrchestratorConfig,
    TektonOrchestratorSettings,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.stack import StackValidator
from zenml.utils import io_utils

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.models import PipelineDeploymentResponse
    from zenml.stack import Stack
    from zenml.steps import ResourceSettings


logger = get_logger(__name__)

ENV_ZENML_TEKTON_RUN_ID = "ZENML_TEKTON_RUN_ID"


class TektonOrchestrator(ContainerizedOrchestrator):
    """Orchestrator responsible for running pipelines using Tekton."""

    _k8s_client: Optional[k8s_client.ApiClient] = None

    @property
    def kube_client(self) -> k8s_client.ApiClient:
        """Getter for the Kubernetes API client.

        Returns:
            The Kubernetes API client.

        Raises:
            RuntimeError: if the Kubernetes connector behaves unexpectedly.
        """
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
            k8s_config.load_kube_config(context=self.config.kubernetes_context)
            self._k8s_client = k8s_client.ApiClient()

        return self._k8s_client

    @property
    def config(self) -> TektonOrchestratorConfig:
        """Returns the `TektonOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(TektonOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Tekton orchestrator.

        Returns:
            The settings class.
        """
        return TektonOrchestratorSettings

    def get_kubernetes_contexts(self) -> Tuple[List[str], Optional[str]]:
        """Get the list of configured Kubernetes contexts and the active context.

        Returns:
            A tuple containing the list of configured Kubernetes contexts and
            the active context.
        """
        try:
            contexts, active_context = k8s_config.list_kube_config_contexts()
        except k8s_config.config_exception.ConfigException:
            return [], None

        context_names = [c["name"] for c in contexts]
        active_context_name = active_context["name"]
        return context_names, active_context_name

    @property
    def validator(self) -> Optional[StackValidator]:
        """Ensures a stack with only remote components and a container registry.

        Returns:
            A `StackValidator` instance.
        """

        def _validate(stack: "Stack") -> Tuple[bool, str]:
            container_registry = stack.container_registry

            # should not happen, because the stack validation takes care of
            # this, but just in case
            assert container_registry is not None

            kubernetes_context = self.config.kubernetes_context
            connector = self.get_connector()
            msg = f"'{self.name}' Tekton orchestrator error: "

            if not connector:
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
                        f"configured for the Tekton orchestrator is not "
                        f"the same as the active context in the local "
                        f"Kubernetes configuration. If this is not deliberate,"
                        f" you should update the orchestrator's "
                        f"`kubernetes_context` field by running:\n\n"
                        f"  `zenml orchestrator update {self.name} "
                        f"--kubernetes_context={active_context}`\n"
                        f"To list all configured contexts, run:\n\n"
                        f"  `kubectl config get-contexts`\n"
                        f"To set the active context to be the same as the one "
                        f"configured in the Tekton orchestrator and "
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
                # Tekton containers.

                # go through all stack components and identify those that
                # advertise a local path where they persist information that
                # they need to be available when running pipelines.
                for stack_comp in stack.components.values():
                    local_path = stack_comp.local_path
                    if not local_path:
                        continue
                    return False, (
                        f"{msg}the Tekton orchestrator is configured to run "
                        f"pipelines in a remote Kubernetes cluster, but the "
                        f"'{stack_comp.name}' {stack_comp.type.value} is a "
                        f"local stack component and will not be available in "
                        f"the Tekton pipeline step.\n"
                        f"Please ensure that you always use non-local "
                        f"stack components with a remote Tekton orchestrator, "
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
                        f"{msg}the Tekton orchestrator is configured to run "
                        f"pipelines in a remote Kubernetes cluster, but the "
                        f"'{container_registry.name}' container registry URI "
                        f"'{container_registry.config.uri}' "
                        f"points to a local container registry. Please ensure "
                        f"that you always use non-local stack components with "
                        f"a remote Tekton orchestrator, otherwise you will "
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
            custom_validation_function=_validate,
        )

    def _configure_container_op(
        self,
        container_op: dsl.ContainerOp,
    ) -> None:
        """Makes changes in place to the configuration of the container op.

        Configures persistent mounted volumes for each stack component that
        writes to a local path.

        Args:
            container_op: The Tekton container operation to configure.
        """
        volumes: Dict[str, k8s_client.V1Volume] = {}

        stack = Client().active_stack

        if self.config.is_local:
            stack.check_local_paths()

            local_stores_path = GlobalConfiguration().local_stores_path

            host_path = k8s_client.V1HostPathVolumeSource(
                path=local_stores_path, type="Directory"
            )

            volumes[local_stores_path] = k8s_client.V1Volume(
                name="local-stores",
                host_path=host_path,
            )
            logger.debug(
                "Adding host path volume for the local ZenML stores (path: %s) "
                "in Tekton pipelines container.",
                local_stores_path,
            )

            if sys.platform == "win32":
                # File permissions are not checked on Windows. This if clause
                # prevents mypy from complaining about unused 'type: ignore'
                # statements
                pass
            else:
                # Run KFP containers in the context of the local UID/GID
                # to ensure that the local stores can be shared
                # with the local pipeline runs.
                container_op.container.security_context = (
                    k8s_client.V1SecurityContext(
                        run_as_user=os.getuid(),
                        run_as_group=os.getgid(),
                    )
                )
                logger.debug(
                    "Setting security context UID and GID to local user/group "
                    "in Tekton pipelines container."
                )

            container_op.container.add_env_variable(
                k8s_client.V1EnvVar(
                    name=ENV_ZENML_LOCAL_STORES_PATH,
                    value=local_stores_path,
                )
            )

        container_op.add_pvolumes(volumes)

    @staticmethod
    def _configure_container_resources(
        container_op: dsl.ContainerOp,
        resource_settings: "ResourceSettings",
    ) -> None:
        """Adds resource requirements to the container.

        Args:
            container_op: The container operation to configure.
            resource_settings: The resource settings to use for this
                container.
        """
        if resource_settings.cpu_count is not None:
            container_op = container_op.set_cpu_limit(
                str(resource_settings.cpu_count)
            )

        if resource_settings.gpu_count is not None:
            container_op = container_op.set_gpu_limit(
                resource_settings.gpu_count
            )

        if resource_settings.memory is not None:
            memory_limit = resource_settings.memory[:-1]
            container_op = container_op.set_memory_limit(memory_limit)

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
    ) -> Any:
        """Runs the pipeline on Tekton.

        This function first compiles the ZenML pipeline into a Tekton yaml
        and then applies this configuration to run the pipeline.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.

        Raises:
            RuntimeError: If you try to run the pipelines in a notebook
                environment.
        """
        # First check whether the code running in a notebook
        if Environment.in_notebook():
            raise RuntimeError(
                "The Tekton orchestrator cannot run pipelines in a notebook "
                "environment. The reason is that it is non-trivial to create "
                "a Docker image of a notebook. Please consider refactoring "
                "your notebook cells into separate scripts in a Python module "
                "and run the code outside of a notebook when using this "
                "orchestrator."
            )

        assert stack.container_registry

        orchestrator_run_name = get_orchestrator_run_name(
            pipeline_name=deployment.pipeline_configuration.name
        )

        def _construct_kfp_pipeline() -> None:
            """Create a container_op for each step.

            This should contain the name of the docker image and configures the
            entrypoint of the docker image to run the step.

            Additionally, this gives each container_op information about its
            direct downstream steps.
            """
            # Dictionary of container_ops index by the associated step name
            step_name_to_container_op: Dict[str, dsl.ContainerOp] = {}

            for step_name, step in deployment.step_configurations.items():
                image = self.get_image(
                    deployment=deployment, step_name=step_name
                )

                command = StepEntrypointConfiguration.get_entrypoint_command()
                arguments = (
                    StepEntrypointConfiguration.get_entrypoint_arguments(
                        step_name=step_name, deployment_id=deployment.id
                    )
                )

                container_op = dsl.ContainerOp(
                    name=step_name,
                    image=image,
                    command=command,
                    arguments=arguments,
                )

                settings = cast(
                    TektonOrchestratorSettings, self.get_settings(step)
                )
                self._configure_container_op(
                    container_op=container_op,
                )

                if settings.pod_settings:
                    apply_pod_settings(
                        container_op=container_op,
                        settings=settings.pod_settings,
                    )

                container_op.container.add_env_variable(
                    k8s_client.V1EnvVar(
                        name=ENV_ZENML_TEKTON_RUN_ID,
                        value="$(context.pipelineRun.name)",
                    )
                )

                for key, value in environment.items():
                    container_op.container.add_env_variable(
                        k8s_client.V1EnvVar(
                            name=key,
                            value=value,
                        )
                    )

                if self.requires_resources_in_orchestration_environment(step):
                    self._configure_container_resources(
                        container_op=container_op,
                        resource_settings=step.config.resource_settings,
                    )

                # Find the upstream container ops of the current step and
                # configure the current container op to run after them
                for upstream_step_name in step.spec.upstream_steps:
                    upstream_container_op = step_name_to_container_op[
                        upstream_step_name
                    ]
                    container_op.after(upstream_container_op)

                # Update dictionary of container ops with the current one
                step_name_to_container_op[step_name] = container_op

        # Get a filepath to use to save the finished yaml to
        fileio.makedirs(self.pipeline_directory)
        pipeline_file_path = os.path.join(
            self.pipeline_directory, f"{orchestrator_run_name}.yaml"
        )

        # Set the run name, which Tekton reads from this attribute of the
        # pipeline function
        setattr(
            _construct_kfp_pipeline,
            "_component_human_name",
            orchestrator_run_name,
        )
        pipeline_config = TektonPipelineConf()
        pipeline_config.add_pipeline_label(
            "pipelines.kubeflow.org/cache_enabled", "false"
        )
        TektonCompiler().compile(
            _construct_kfp_pipeline,
            pipeline_file_path,
            tekton_pipeline_conf=pipeline_config,
        )
        logger.info(
            "Writing Tekton workflow definition to `%s`.", pipeline_file_path
        )

        if deployment.schedule:
            logger.warning(
                "The Tekton Orchestrator currently does not support the "
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )

        kubernetes_context = self.config.kubernetes_context
        if kubernetes_context:
            logger.info(
                "Running Tekton pipeline in kubernetes context '%s' and "
                "namespace '%s'.",
                kubernetes_context,
                self.config.kubernetes_namespace,
            )
        elif self.connector:
            connector = self.get_connector()
            assert connector is not None
            logger.info(
                "Running Tekton pipeline with Kubernetes credentials from "
                "connector '%s'.",
                connector.name or str(connector),
            )

        # Read the Tekton pipeline resource from the generated YAML file
        with open(pipeline_file_path, "r") as f:
            tekton_resource = yaml.safe_load(f)

        # Upload the Tekton pipeline to the Kubernetes cluster
        custom_objects_api = k8s_client.CustomObjectsApi(self.kube_client)

        try:
            logger.debug("Creating Tekton resource ...")
            response = custom_objects_api.create_namespaced_custom_object(
                group=tekton_resource["apiVersion"].split("/")[0],
                version=tekton_resource["apiVersion"].split("/")[1],
                namespace=self.config.kubernetes_namespace,
                plural=tekton_resource["kind"].lower() + "s",
                body=tekton_resource,
            )
            logger.debug("Tekton API response: %s", response)
        except k8s_client.rest.ApiException as e:
            logger.error("Exception when creating Tekton resource: %s", str(e))
            raise RuntimeError(
                f"Failed to upload Tekton pipeline: {str(e)}. "
                f"Please make sure your Kubernetes cluster is running and "
                f"accessible.",
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
            return os.environ[ENV_ZENML_TEKTON_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_TEKTON_RUN_ID}."
            )

    @property
    def root_directory(self) -> str:
        """Returns path to the root directory for all files concerning this orchestrator.

        Returns:
            Path to the root directory.
        """
        return os.path.join(
            io_utils.get_global_config_directory(),
            "tekton",
            str(self.id),
        )

    @property
    def pipeline_directory(self) -> str:
        """Path to a directory in which the Tekton pipeline files are stored.

        Returns:
            Path to the pipeline directory.
        """
        return os.path.join(self.root_directory, "pipelines")

    @property
    def _pid_file_path(self) -> str:
        """Returns path to the daemon PID file.

        Returns:
            Path to the daemon PID file.
        """
        return os.path.join(self.root_directory, "tekton_daemon.pid")

    @property
    def log_file(self) -> str:
        """Path of the daemon log file.

        Returns:
            Path of the daemon log file.
        """
        return os.path.join(self.root_directory, "tekton_daemon.log")
