# Copyright 2019 Google LLC. All Rights Reserved.
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

# Minor parts of the `prepare_or_run_pipeline()` method of this file are
# inspired by the kubeflow dag runner implementation of tfx
"""Implementation of the Kubeflow orchestrator."""
import os
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast
from uuid import UUID

import kfp
import requests
import urllib3
from kfp import dsl
from kfp.compiler import Compiler as KFPCompiler
from kfp_server_api.exceptions import ApiException
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config

from zenml.artifact_stores import LocalArtifactStore
from zenml.client import Client
from zenml.config.base_settings import BaseSettings
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    ENV_ZENML_LOCAL_STORES_PATH,
    ORCHESTRATOR_DOCKER_IMAGE_KEY,
)
from zenml.container_registries.base_container_registry import (
    BaseContainerRegistry,
)
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.enums import StackComponentType
from zenml.environment import Environment
from zenml.exceptions import ProvisioningError
from zenml.integrations.kubeflow.flavors.kubeflow_orchestrator_flavor import (
    DEFAULT_KFP_UI_PORT,
    KubeflowOrchestratorConfig,
    KubeflowOrchestratorSettings,
)
from zenml.integrations.kubeflow.orchestrators import local_deployment_utils
from zenml.integrations.kubeflow.orchestrators.local_deployment_utils import (
    KFP_VERSION,
)
from zenml.integrations.kubeflow.utils import apply_pod_settings
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.stack import StackValidator
from zenml.stack.stack_component import StackComponent
from zenml.utils import io_utils, networking_utils
from zenml.utils.pipeline_docker_image_builder import PipelineDockerImageBuilder

if TYPE_CHECKING:
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.stack import Stack
    from zenml.steps import ResourceSettings


logger = get_logger(__name__)

KFP_POD_LABELS = {
    "add-pod-env": "true",
    "pipelines.kubeflow.org/pipeline-sdk-type": "zenml",
}

ENV_KFP_RUN_ID = "KFP_RUN_ID"


class KubeflowOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines using Kubeflow."""

    @property
    def config(self) -> KubeflowOrchestratorConfig:
        """Returns the `KubeflowOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(KubeflowOrchestratorConfig, self._config)

    @staticmethod
    def _get_k3d_cluster_name(uuid: UUID) -> str:
        """Returns the k3d cluster name corresponding to the orchestrator UUID.

        Args:
            uuid: The UUID of the orchestrator.

        Returns:
            The k3d cluster name.
        """
        # k3d only allows cluster names with up to 32 characters; use the
        # first 8 chars of the orchestrator UUID as identifier
        return f"zenml-kubeflow-{str(uuid)[:8]}"

    @staticmethod
    def _get_k3d_kubernetes_context(uuid: UUID) -> str:
        """Gets the k3d kubernetes context.

        Args:
            uuid: The UUID of the orchestrator.

        Returns:
            The name of the kubernetes context associated with the k3d
                cluster managed locally by ZenML corresponding to the orchestrator UUID.
        """
        return f"k3d-{KubeflowOrchestrator._get_k3d_cluster_name(uuid)}"

    @property
    def kubernetes_context(self) -> str:
        """Gets the kubernetes context associated with the orchestrator.

        This sets the default `kubernetes_context` value to the value that is
        used to create the locally managed k3d cluster, if not explicitly set.

        Returns:
            The kubernetes context associated with the orchestrator.
        """
        if self.config.kubernetes_context:
            return self.config.kubernetes_context
        return self._get_k3d_kubernetes_context(self.id)

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
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Kubeflow orchestrator.

        Returns:
            The settings class.
        """
        return KubeflowOrchestratorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack contains a container registry.

        Also check that requirements are met for local components.

        Returns:
            A `StackValidator` instance.
        """

        def _validate_local_requirements(stack: "Stack") -> Tuple[bool, str]:

            container_registry = stack.container_registry

            # should not happen, because the stack validation takes care of
            # this, but just in case
            assert container_registry is not None

            if (
                self.config.container_registry_name is not None
                and container_registry.name
                != self.config.container_registry_name
            ):
                return (
                    False,
                    f"Configured container registry component name "
                    f"'{self.config.container_registry_name}' does not "
                    f"match the one in the active stack: "
                    f"'{self.config.container_registry_name}'",
                )

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
            elif active_context and self.kubernetes_context != active_context:
                logger.warning(
                    f"The Kubernetes context '{self.kubernetes_context}' "
                    f"configured for the Kubeflow orchestrator is not the "
                    f"same as the active context in the local Kubernetes "
                    f"configuration. If this is not deliberate, you should "
                    f"update the orchestrator's `kubernetes_context` field by "
                    f"running:\n\n"
                    f"  `zenml orchestrator update {self.name} "
                    f"--kubernetes_context={active_context}`\n"
                    f"To list all configured contexts, run:\n\n"
                    f"  `kubectl config get-contexts`\n"
                    f"To set the active context to be the same as the one "
                    f"configured in the Kubeflow orchestrator and silence "
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

            if not self.config.skip_local_validations and not self.is_local:

                # if the orchestrator is not running in a local k3d cluster,
                # we cannot have any other local components in our stack,
                # because we cannot mount the local path into the container.
                # This may result in problems when running the pipeline, because
                # the local components will not be available inside the
                # Kubeflow containers.

                # go through all stack components and identify those that
                # advertise a local path where they persist information that
                # they need to be available when running pipelines.
                for stack_comp in stack.components.values():
                    local_path = stack_comp.local_path
                    if not local_path:
                        continue
                    return False, (
                        f"The Kubeflow orchestrator is configured to run "
                        f"pipelines in a remote Kubernetes cluster designated "
                        f"by the '{self.kubernetes_context}' configuration "
                        f"context, but the '{stack_comp.name}' "
                        f"{stack_comp.type.value} is a local stack component "
                        f"and will not be available in the Kubeflow pipeline "
                        f"step.\nPlease ensure that you always use non-local "
                        f"stack components with a remote Kubeflow orchestrator, "
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
                        f"The Kubeflow orchestrator is configured to run "
                        f"pipelines in a remote Kubernetes cluster designated "
                        f"by the '{self.kubernetes_context}' configuration "
                        f"context, but the '{container_registry.name}' "
                        f"container registry URI "
                        f"'{container_registry.config.uri}' "
                        f"points to a local container registry. Please ensure "
                        f"that you always use non-local stack components with "
                        f"a remote Kubeflow orchestrator, otherwise you will "
                        f"run into problems. You should use a flavor of "
                        f"container registry other than "
                        f"'{container_registry.flavor}'.\n"
                        + silence_local_validations_msg
                    )

            if not self.config.skip_local_validations and self.is_local:

                # if the orchestrator is local, the container registry must
                # also be local.
                if not container_registry.config.is_local:
                    return False, (
                        f"The Kubeflow orchestrator is configured to run "
                        f"pipelines in a local k3d Kubernetes cluster "
                        f"designated by the '{self.kubernetes_context}' "
                        f"configuration context, but the container registry "
                        f"URI '{container_registry.config.uri}' doesn't "
                        f"match the expected format 'localhost:$PORT'. "
                        f"The local Kubeflow orchestrator only works with a "
                        f"local container registry because it cannot "
                        f"currently authenticate to external container "
                        f"registries. You should use a flavor of container "
                        f"registry other than '{container_registry.flavor}'.\n"
                        + silence_local_validations_msg
                    )

            return True, ""

        return StackValidator(
            required_components={StackComponentType.CONTAINER_REGISTRY},
            custom_validation_function=_validate_local_requirements,
        )

    @property
    def is_local(self) -> bool:
        """Checks if the KFP orchestrator is running locally.

        Returns:
            `True` if the KFP orchestrator is running locally (i.e. in
            the local k3d cluster managed by ZenML).
        """
        return self.kubernetes_context == self._get_k3d_kubernetes_context(
            self.id
        )

    @property
    def root_directory(self) -> str:
        """Path to the root directory for all files concerning this orchestrator.

        Returns:
            Path to the root directory.
        """
        return os.path.join(
            io_utils.get_global_config_directory(),
            "kubeflow",
            str(self.id),
        )

    @property
    def pipeline_directory(self) -> str:
        """Returns path to a directory in which the kubeflow pipeline files are stored.

        Returns:
            Path to the pipeline directory.
        """
        return os.path.join(self.root_directory, "pipelines")

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
        docker_image_builder = PipelineDockerImageBuilder()
        repo_digest = docker_image_builder.build_and_push_docker_image(
            deployment=deployment, stack=stack
        )
        deployment.add_extra(ORCHESTRATOR_DOCKER_IMAGE_KEY, repo_digest)

    def _configure_container_op(
        self,
        container_op: dsl.ContainerOp,
        settings: KubeflowOrchestratorSettings,
    ) -> None:
        """Makes changes in place to the configuration of the container op.

        Configures persistent mounted volumes for each stack component that
        writes to a local path. Adds some labels to the container_op and applies
        some functions to ir.

        Args:
            container_op: The kubeflow container operation to configure.
            settings: Orchestrator settings for this step.
        """
        volumes: Dict[str, k8s_client.V1Volume] = {}

        stack = Client().active_stack

        if self.is_local:
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
                "in kubeflow pipelines container.",
                local_stores_path,
            )

            if sys.platform == "win32":
                # File permissions are not checked on Windows. This if clause
                # prevents mypy from complaining about unused 'type: ignore'
                # statements
                pass
            else:
                # Run KFP containers in the context of the local UID/GID
                # to ensure that the artifact and metadata stores can be shared
                # with the local pipeline runs.
                container_op.container.security_context = (
                    k8s_client.V1SecurityContext(
                        run_as_user=os.getuid(),
                        run_as_group=os.getgid(),
                    )
                )
                logger.debug(
                    "Setting security context UID and GID to local user/group "
                    "in kubeflow pipelines container."
                )

            container_op.container.add_env_variable(
                k8s_client.V1EnvVar(
                    name=ENV_ZENML_LOCAL_STORES_PATH,
                    value=local_stores_path,
                )
            )

        container_op.add_pvolumes(volumes)

        # Add some pod labels to the container_op
        for k, v in KFP_POD_LABELS.items():
            container_op.add_pod_label(k, v)

        if settings.pod_settings:
            apply_pod_settings(
                container_op=container_op, settings=settings.pod_settings
            )

        # Disable caching in KFP v1 only works like this, replace by the second
        # line in the future
        container_op.execution_options.caching_strategy.max_cache_staleness = (
            "P0D"
        )
        # container_op.set_caching_options(enable_caching=False)

    @staticmethod
    def _configure_container_resources(
        container_op: dsl.ContainerOp,
        resource_settings: "ResourceSettings",
    ) -> None:
        """Adds resource requirements to the container.

        Args:
            container_op: The kubeflow container operation to configure.
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
        deployment: "PipelineDeployment",
        stack: "Stack",
    ) -> Any:
        """Creates a kfp yaml file.

        This functions as an intermediary representation of the pipeline which
        is then deployed to the kubeflow pipelines instance.

        How it works:
        -------------
        Before this method is called the `prepare_pipeline_deployment()`
        method builds a docker image that contains the code for the
        pipeline, all steps the context around these files.

        Based on this docker image a callable is created which builds
        container_ops for each step (`_construct_kfp_pipeline`).
        To do this the entrypoint of the docker image is configured to
        run the correct step within the docker image. The dependencies
        between these container_ops are then also configured onto each
        container_op by pointing at the downstream steps.

        This callable is then compiled into a kfp yaml file that is used as
        the intermediary representation of the kubeflow pipeline.

        This file, together with some metadata, runtime configurations is
        then uploaded into the kubeflow pipelines cluster for execution.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.

        Raises:
            RuntimeError: If trying to run a pipeline in a notebook environment.
        """
        # First check whether the code running in a notebook
        if Environment.in_notebook():
            raise RuntimeError(
                "The Kubeflow orchestrator cannot run pipelines in a notebook "
                "environment. The reason is that it is non-trivial to create "
                "a Docker image of a notebook. Please consider refactoring "
                "your notebook cells into separate scripts in a Python module "
                "and run the code outside of a notebook when using this "
                "orchestrator."
            )

        assert stack.container_registry
        image_name = deployment.pipeline.extra[ORCHESTRATOR_DOCKER_IMAGE_KEY]
        if self.is_local and stack.container_registry.config.is_local:
            image_name = f"k3d-zenml-kubeflow-registry.{image_name}"

        # Create a callable for future compilation into a dsl.Pipeline.
        def _construct_kfp_pipeline() -> None:
            """Create a container_op for each step.

            This should contain the name of the docker image and configures the
            entrypoint of the docker image to run the step.

            Additionally, this gives each container_op information about its
            direct downstream steps.

            If this callable is passed to the `_create_and_write_workflow()`
            method of a KFPCompiler all dsl.ContainerOp instances will be
            automatically added to a singular dsl.Pipeline instance.
            """
            # Dictionary of container_ops index by the associated step name
            step_name_to_container_op: Dict[str, dsl.ContainerOp] = {}

            for step_name, step in deployment.steps.items():
                # The command will be needed to eventually call the python step
                # within the docker container
                command = StepEntrypointConfiguration.get_entrypoint_command()

                # The arguments are passed to configure the entrypoint of the
                # docker container when the step is called.
                arguments = (
                    StepEntrypointConfiguration.get_entrypoint_arguments(
                        step_name=step_name,
                    )
                )

                # Create a container_op - the kubeflow equivalent of a step. It
                # contains the name of the step, the name of the docker image,
                # the command to use to run the step entrypoint
                # (e.g. `python -m zenml.entrypoints.step_entrypoint`)
                # and the arguments to be passed along with the command. Find
                # out more about how these arguments are parsed and used
                # in the base entrypoint `run()` method.
                container_op = dsl.ContainerOp(
                    name=step.config.name,
                    image=image_name,
                    command=command,
                    arguments=arguments,
                )

                settings = cast(
                    KubeflowOrchestratorSettings, self.get_settings(step)
                )
                self._configure_container_op(
                    container_op=container_op,
                    settings=settings,
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
                step_name_to_container_op[step.config.name] = container_op

        orchestrator_run_name = get_orchestrator_run_name(
            pipeline_name=deployment.pipeline.name
        )

        # Get a filepath to use to save the finished yaml to
        fileio.makedirs(self.pipeline_directory)
        pipeline_file_path = os.path.join(
            self.pipeline_directory, f"{orchestrator_run_name}.yaml"
        )

        # write the argo pipeline yaml
        KFPCompiler()._create_and_write_workflow(
            pipeline_func=_construct_kfp_pipeline,
            pipeline_name=deployment.pipeline.name,
            package_path=pipeline_file_path,
        )
        logger.info(
            "Writing Kubeflow workflow definition to `%s`.", pipeline_file_path
        )

        # using the kfp client uploads the pipeline to kubeflow pipelines and
        # runs it there
        self._upload_and_run_pipeline(
            deployment=deployment,
            pipeline_file_path=pipeline_file_path,
            run_name=orchestrator_run_name,
        )

    def _upload_and_run_pipeline(
        self,
        deployment: "PipelineDeployment",
        pipeline_file_path: str,
        run_name: str,
    ) -> None:
        """Tries to upload and run a KFP pipeline.

        Args:
            deployment: The pipeline deployment.
            pipeline_file_path: Path to the pipeline definition file.
            run_name: The Kubeflow run name.

        Raises:
            RuntimeError: If Kubeflow API returns an error.
        """
        pipeline_name = deployment.pipeline.name
        settings = cast(
            KubeflowOrchestratorSettings, self.get_settings(deployment)
        )
        user_namespace = settings.user_namespace

        try:
            logger.info(
                "Running in kubernetes context '%s'.",
                self.kubernetes_context,
            )

            # upload the pipeline to Kubeflow and start it

            client = self._get_kfp_client(settings=settings)
            if deployment.schedule:
                try:
                    experiment = client.get_experiment(
                        pipeline_name, namespace=user_namespace
                    )
                    logger.info(
                        "A recurring run has already been created with this "
                        "pipeline. Creating new recurring run now.."
                    )
                except (ValueError, ApiException):
                    experiment = client.create_experiment(
                        pipeline_name, namespace=user_namespace
                    )
                    logger.info(
                        "Creating a new recurring run for pipeline '%s'.. ",
                        pipeline_name,
                    )
                logger.info(
                    "You can see all recurring runs under the '%s' experiment.",
                    pipeline_name,
                )

                interval_seconds = (
                    deployment.schedule.interval_second.seconds
                    if deployment.schedule.interval_second
                    else None
                )
                result = client.create_recurring_run(
                    experiment_id=experiment.id,
                    job_name=run_name,
                    pipeline_package_path=pipeline_file_path,
                    enable_caching=False,
                    cron_expression=deployment.schedule.cron_expression,
                    start_time=deployment.schedule.utc_start_time,
                    end_time=deployment.schedule.utc_end_time,
                    interval_second=interval_seconds,
                    no_catchup=not deployment.schedule.catchup,
                )

                logger.info("Started recurring run with ID '%s'.", result.id)
            else:
                logger.info(
                    "No schedule detected. Creating a one-off pipeline run.."
                )
                try:
                    result = client.create_run_from_pipeline_package(
                        pipeline_file_path,
                        arguments={},
                        run_name=run_name,
                        enable_caching=False,
                        namespace=user_namespace,
                    )
                except ApiException:
                    raise RuntimeError(
                        f"Failed to create {run_name} on kubeflow! "
                        "Please check stack component settings and configuration!"
                    )

                logger.info(
                    "Started one-off pipeline run with ID '%s'.", result.run_id
                )

                if settings.synchronous:
                    client.wait_for_run_completion(
                        run_id=result.run_id, timeout=settings.timeout
                    )
        except urllib3.exceptions.HTTPError as error:
            logger.warning(
                f"Failed to upload Kubeflow pipeline: %s. "
                f"Please make sure your kubernetes config is present and the "
                f"{self.kubernetes_context} kubernetes context is configured "
                f"correctly.",
                error,
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
            return os.environ[ENV_KFP_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_KFP_RUN_ID}."
            )

    def _get_kfp_client(
        self,
        settings: KubeflowOrchestratorSettings,
    ) -> kfp.Client:
        """Creates a KFP client instance.

        Args:
            settings: Settings which can be used to
                configure the client instance.

        Returns:
            A KFP client instance.
        """
        client_args = {
            "kube_context": self.config.kubernetes_context,
        }

        client_args.update(settings.client_args)

        # The host and namespace are stack component configurations that refer
        # to the Kubeflow deployment. We don't want these overwritten on a
        # run by run basis by user settings
        client_args["host"] = self.config.kubeflow_hostname
        client_args["namespace"] = self.config.kubeflow_namespace

        # Handle username and password, ignore the case if one is passed and not the other
        # Also do not attempt to get cookie if cookie is already passed in client_args
        if settings.client_username and settings.client_password:
            # If cookie is already set, then ignore
            if "cookie" in client_args:
                logger.warning(
                    "Cookie already set in `client_args`, ignoring `client_username` and `client_password`..."
                )
            else:
                session_cookie = self._get_session_cookie(
                    username=settings.client_username,
                    password=settings.client_password,
                )

                client_args["cookies"] = session_cookie

        return kfp.Client(**client_args)

    @property
    def _pid_file_path(self) -> str:
        """Returns path to the daemon PID file.

        Returns:
            Path to the daemon PID file.
        """
        return os.path.join(self.root_directory, "kubeflow_daemon.pid")

    @property
    def log_file(self) -> str:
        """Path of the daemon log file.

        Returns:
            Path of the daemon log file.
        """
        return os.path.join(self.root_directory, "kubeflow_daemon.log")

    @property
    def _k3d_cluster_name(self) -> str:
        """Returns the K3D cluster name.

        Returns:
            The K3D cluster name.
        """
        return self._get_k3d_cluster_name(self.id)

    def _get_k3d_registry_name(self, port: int) -> str:
        """Returns the K3D registry name.

        Args:
            port: Port of the registry.

        Returns:
            The registry name.
        """
        return f"k3d-zenml-kubeflow-registry.localhost:{port}"

    @property
    def _k3d_registry_config_path(self) -> str:
        """Returns the path to the K3D registry config yaml.

        Returns:
            str: Path to the K3D registry config yaml.
        """
        return os.path.join(self.root_directory, "k3d_registry.yaml")

    def _get_kfp_ui_daemon_port(self) -> int:
        """Port to use for the KFP UI daemon.

        Returns:
            Port to use for the KFP UI daemon.
        """
        port = self.config.kubeflow_pipelines_ui_port
        if port == DEFAULT_KFP_UI_PORT and not networking_utils.port_available(
            port
        ):
            # if the user didn't specify a specific port and the default
            # port is occupied, fallback to a random open port
            port = networking_utils.find_available_port()
        return port

    def _get_session_cookie(self, username: str, password: str) -> str:
        """Gets session cookie from username and password.

        Args:
            username: Username for kubeflow host.
            password: Password for kubeflow host.

        Raises:
            RuntimeError: If the cookie fetching failed.

        Returns:
            Cookie with the prefix `authsession=`.
        """
        if self.config.kubeflow_hostname is None:
            raise RuntimeError(
                "You must configure the Kubeflow orchestrator "
                "with the `kubeflow_hostname` parameter which usually ends "
                "with `/pipeline` (e.g. `https://mykubeflow.com/pipeline`). "
                "Please update the current kubeflow orchestrator with: "
                f"`zenml orchestrator update {self.name} "
                "--kubeflow_hostname=<MY_KUBEFLOW_HOST>`"
            )

        # Get cookie
        logger.info(
            f"Attempting to fetch session cookie from {self.config.kubeflow_hostname} "
            "with supplied username and password..."
        )
        session = requests.Session()
        try:
            response = session.get(self.config.kubeflow_hostname)
            response.raise_for_status()
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            raise RuntimeError(
                f"Error while trying to fetch kubeflow cookie: {e}"
            )

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"login": username, "password": password}
        try:
            response = session.post(response.url, headers=headers, data=data)
            response.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            raise RuntimeError(
                f"Error while trying to fetch kubeflow cookie: {errh}"
            )
        cookie_dict = session.cookies.get_dict()  # type: ignore[no-untyped-call]

        if "authservice_session" not in cookie_dict:
            raise RuntimeError("Invalid username and/or password!")

        logger.info("Session cookie fetched successfully!")

        return "authservice_session=" + str(cookie_dict["authservice_session"])

    def list_manual_setup_steps(
        self, container_registry_name: str, container_registry_path: str
    ) -> None:
        """Logs manual steps needed to setup the Kubeflow local orchestrator.

        Args:
            container_registry_name: Name of the container registry.
            container_registry_path: Path to the container registry.
        """
        if not self.is_local:
            # Make sure we're not telling users to deploy Kubeflow on their
            # remote clusters
            logger.warning(
                "This Kubeflow orchestrator is configured to use a non-local "
                f"Kubernetes context {self.kubernetes_context}. Manually "
                f"deploying Kubeflow Pipelines is only possible for local "
                f"Kubeflow orchestrators."
            )
            return

        global_config_dir_path = io_utils.get_global_config_directory()
        kubeflow_commands = [
            f"> k3d cluster create {self._k3d_cluster_name} --image {local_deployment_utils.K3S_IMAGE_NAME} --registry-create {container_registry_name} --registry-config {container_registry_path} --volume {global_config_dir_path}:{global_config_dir_path}\n",
            f"> kubectl --context {self.kubernetes_context} apply -k github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref={KFP_VERSION}&timeout=5m",
            f"> kubectl --context {self.kubernetes_context} wait --timeout=60s --for condition=established crd/applications.app.k8s.io",
            f"> kubectl --context {self.kubernetes_context} apply -k github.com/kubeflow/pipelines/manifests/kustomize/env/platform-agnostic-pns?ref={KFP_VERSION}&timeout=5m",
            f"> kubectl --context {self.kubernetes_context} --namespace kubeflow port-forward svc/ml-pipeline-ui {self.config.kubeflow_pipelines_ui_port}:80",
        ]

        logger.info(
            "If you wish to spin up this Kubeflow local orchestrator manually, "
            "please enter the following commands:\n"
        )
        logger.info("\n".join(kubeflow_commands))

    @property
    def skip_ui_daemon_provisioning(self) -> bool:
        """Whether the UI daemon provisioning should be skipped.

        If a hostname is configured, the UI is already accessible using this
        host and we don't need to port-forward the UI.

        Returns:
            Whether the UI daemon provisioning should be skipped.
        """
        if self.config.kubeflow_hostname:
            return True

        return self.config.skip_ui_daemon_provisioning

    @property
    def is_provisioned(self) -> bool:
        """Returns if a local k3d cluster for this orchestrator exists.

        Returns:
            True if a local k3d cluster exists, False otherwise.
        """
        if not local_deployment_utils.check_prerequisites(
            skip_k3d=self.config.skip_cluster_provisioning or not self.is_local,
            skip_kubectl=self.config.skip_cluster_provisioning
            and self.skip_ui_daemon_provisioning,
        ):
            # if any prerequisites are missing there is certainly no
            # local deployment running
            return False

        return self.is_cluster_provisioned

    @property
    def is_running(self) -> bool:
        """Checks if the local k3d cluster and UI daemon are both running.

        Returns:
            True if the local k3d cluster and UI daemon for this orchestrator are both running.
        """
        return (
            self.is_provisioned
            and self.is_cluster_running
            and self.is_daemon_running
        )

    @property
    def is_suspended(self) -> bool:
        """Checks if the local k3d cluster and UI daemon are both stopped.

        Returns:
            True if the cluster and daemon for this orchestrator are both stopped, False otherwise.
        """
        return (
            self.is_provisioned
            and (
                self.config.skip_cluster_provisioning
                or not self.is_cluster_running
            )
            and (self.skip_ui_daemon_provisioning or not self.is_daemon_running)
        )

    @property
    def is_cluster_provisioned(self) -> bool:
        """Returns if the local k3d cluster for this orchestrator is provisioned.

        For remote (i.e. not managed by ZenML) Kubeflow Pipelines installations,
        this always returns True.

        Returns:
            True if the local k3d cluster is provisioned, False otherwise.
        """
        if self.config.skip_cluster_provisioning or not self.is_local:
            return True
        return local_deployment_utils.k3d_cluster_exists(
            cluster_name=self._k3d_cluster_name
        )

    @property
    def is_cluster_running(self) -> bool:
        """Returns if the local k3d cluster for this orchestrator is running.

        For remote (i.e. not managed by ZenML) Kubeflow Pipelines installations,
        this always returns True.

        Returns:
            True if the local k3d cluster is running, False otherwise.
        """
        if self.config.skip_cluster_provisioning or not self.is_local:
            return True
        return local_deployment_utils.k3d_cluster_running(
            cluster_name=self._k3d_cluster_name
        )

    @property
    def is_daemon_running(self) -> bool:
        """Returns if the local Kubeflow UI daemon for this orchestrator is running.

        Returns:
            True if the daemon is running, False otherwise.
        """
        if self.skip_ui_daemon_provisioning:
            return True

        if sys.platform != "win32":
            from zenml.utils.daemon import check_if_daemon_is_running

            return check_if_daemon_is_running(self._pid_file_path)
        else:
            return True

    def provision(self) -> None:
        """Provisions a local Kubeflow Pipelines deployment.

        Raises:
            ProvisioningError: If the provisioning fails.
        """
        if self.config.skip_cluster_provisioning:
            return

        if self.is_running:
            logger.info(
                "Found already existing local Kubeflow Pipelines deployment. "
                "If there are any issues with the existing deployment, please "
                "run 'zenml stack down --force' to delete it."
            )
            return

        if not local_deployment_utils.check_prerequisites():
            raise ProvisioningError(
                "Unable to provision local Kubeflow Pipelines deployment: "
                "Please install 'k3d' and 'kubectl' and try again."
            )

        if self.config.container_registry_name is None:
            container_registry = Client().active_stack.container_registry
        else:
            container_registry_model = Client().get_stack_component(
                component_type=StackComponentType.CONTAINER_REGISTRY,
                name_id_or_prefix=self.config.container_registry_name,
            )

            # should not happen, because the stack validation takes care of
            # this, but just in case
            assert container_registry_model is not None

            container_registry = cast(
                BaseContainerRegistry,
                StackComponent.from_model(container_registry_model),
            )

        # should not happen, because the stack validation takes care of this,
        # but just in case
        assert container_registry is not None

        fileio.makedirs(self.root_directory)

        if not self.is_local:
            # don't provision any resources if using a remote KFP installation
            return

        logger.info("Provisioning local Kubeflow Pipelines deployment...")

        container_registry_port = int(
            container_registry.config.uri.split(":")[-1]
        )
        container_registry_name = self._get_k3d_registry_name(
            port=container_registry_port
        )
        local_deployment_utils.write_local_registry_yaml(
            yaml_path=self._k3d_registry_config_path,
            registry_name=container_registry_name,
            registry_uri=container_registry.config.uri,
        )

        try:
            local_deployment_utils.create_k3d_cluster(
                cluster_name=self._k3d_cluster_name,
                registry_name=container_registry_name,
                registry_config_path=self._k3d_registry_config_path,
            )
            kubernetes_context = self.kubernetes_context

            # will never happen, but mypy doesn't know that
            assert kubernetes_context is not None

            local_deployment_utils.deploy_kubeflow_pipelines(
                kubernetes_context=kubernetes_context
            )

            artifact_store = Client().active_stack.artifact_store
            if isinstance(artifact_store, LocalArtifactStore):
                local_deployment_utils.add_hostpath_to_kubeflow_pipelines(
                    kubernetes_context=kubernetes_context,
                    local_path=artifact_store.path,
                )
        except Exception as e:
            logger.error(e)
            logger.error(
                "Unable to spin up local Kubeflow Pipelines deployment."
            )

            self.list_manual_setup_steps(
                container_registry_name, self._k3d_registry_config_path
            )
            self.deprovision()

    def deprovision(self) -> None:
        """Deprovisions a local Kubeflow Pipelines deployment."""
        if self.config.skip_cluster_provisioning:
            return

        if not self.skip_ui_daemon_provisioning and self.is_daemon_running:
            local_deployment_utils.stop_kfp_ui_daemon(
                pid_file_path=self._pid_file_path
            )

        if self.is_local:
            # don't deprovision any resources if using a remote KFP installation
            local_deployment_utils.delete_k3d_cluster(
                cluster_name=self._k3d_cluster_name
            )

            logger.info("Local kubeflow pipelines deployment deprovisioned.")

        if fileio.exists(self.log_file):
            fileio.remove(self.log_file)

    def resume(self) -> None:
        """Resumes the local k3d cluster.

        Raises:
            ProvisioningError: If the k3d cluster is not provisioned.
        """
        if self.is_running:
            logger.info("Local kubeflow pipelines deployment already running.")
            return

        if not self.is_provisioned:
            raise ProvisioningError(
                "Unable to resume local kubeflow pipelines deployment: No "
                "resources provisioned for local deployment."
            )

        kubernetes_context = self.kubernetes_context

        # will never happen, but mypy doesn't know that
        assert kubernetes_context is not None

        if (
            not self.config.skip_cluster_provisioning
            and self.is_local
            and not self.is_cluster_running
        ):
            # don't resume any resources if using a remote KFP installation
            local_deployment_utils.start_k3d_cluster(
                cluster_name=self._k3d_cluster_name
            )

            local_deployment_utils.wait_until_kubeflow_pipelines_ready(
                kubernetes_context=kubernetes_context
            )

        if not self.is_daemon_running:
            local_deployment_utils.start_kfp_ui_daemon(
                pid_file_path=self._pid_file_path,
                log_file_path=self.log_file,
                port=self._get_kfp_ui_daemon_port(),
                kubernetes_context=kubernetes_context,
            )

    def suspend(self) -> None:
        """Suspends the local k3d cluster."""
        if not self.is_provisioned:
            logger.info("Local kubeflow pipelines deployment not provisioned.")
            return

        if not self.skip_ui_daemon_provisioning and self.is_daemon_running:
            local_deployment_utils.stop_kfp_ui_daemon(
                pid_file_path=self._pid_file_path
            )

        if (
            not self.config.skip_cluster_provisioning
            and self.is_local
            and self.is_cluster_running
        ):
            # don't suspend any resources if using a remote KFP installation
            local_deployment_utils.stop_k3d_cluster(
                cluster_name=self._k3d_cluster_name
            )
