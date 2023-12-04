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

from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    ENV_ZENML_LOCAL_STORES_PATH,
    METADATA_ORCHESTRATOR_URL,
)
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.enums import StackComponentType
from zenml.environment import Environment
from zenml.integrations.kubeflow.flavors.kubeflow_orchestrator_flavor import (
    KubeflowOrchestratorConfig,
    KubeflowOrchestratorSettings,
)
from zenml.integrations.kubeflow.utils import apply_pod_settings
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType, Uri
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.stack import StackValidator
from zenml.utils import io_utils, settings_utils

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse
    from zenml.stack import Stack
    from zenml.steps import ResourceSettings


logger = get_logger(__name__)

KFP_POD_LABELS = {
    "add-pod-env": "true",
    "pipelines.kubeflow.org/pipeline-sdk-type": "zenml",
}

ENV_KFP_RUN_ID = "KFP_RUN_ID"


class KubeClientKFPClient(kfp.Client):  # type: ignore[misc]
    """KFP client initialized from a Kubernetes client.

    This is a workaround for the fact that the native KFP client does not
    support initialization from an existing Kubernetes client.
    """

    def __init__(
        self, client: k8s_client.ApiClient, *args: Any, **kwargs: Any
    ) -> None:
        """Initializes the KFP client from a Kubernetes client.

        Args:
            client: pre-configured Kubernetes client.
            args: standard KFP client positional arguments.
            kwargs: standard KFP client keyword arguments.
        """
        self._k8s_client = client
        super().__init__(*args, **kwargs)

    def _load_config(self, *args: Any, **kwargs: Any) -> Any:
        """Loads the KFP configuration.

        Initializes the KFP configuration from the Kubernetes client.

        Args:
            args: standard KFP client positional arguments.
            kwargs: standard KFP client keyword arguments.

        Returns:
            The KFP configuration.
        """
        from kfp_server_api.configuration import Configuration

        kube_config = self._k8s_client.configuration

        host = (
            kube_config.host
            + "/"
            + self.KUBE_PROXY_PATH.format(kwargs.get("namespace", "kubeflow"))
        )

        config = Configuration(
            host=host,
            api_key=kube_config.api_key,
            api_key_prefix=kube_config.api_key_prefix,
            username=kube_config.username,
            password=kube_config.password,
            discard_unknown_keys=kube_config.discard_unknown_keys,
        )

        # Extra attributes not present in the Configuration constructor
        keys = ["ssl_ca_cert", "cert_file", "key_file", "verify_ssl"]
        for key in keys:
            if key in kube_config.__dict__:
                setattr(config, key, getattr(kube_config, key))

        return config


class KubeflowOrchestrator(ContainerizedOrchestrator):
    """Orchestrator responsible for running pipelines using Kubeflow."""

    @property
    def config(self) -> KubeflowOrchestratorConfig:
        """Returns the `KubeflowOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(KubeflowOrchestratorConfig, self._config)

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
    def settings_class(self) -> Type[KubeflowOrchestratorSettings]:
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
        msg = f"'{self.name}' Kubeflow orchestrator error: "

        def _validate_kube_context(
            kubernetes_context: str,
        ) -> Tuple[bool, str]:
            contexts, active_context = self.get_kubernetes_contexts()

            if kubernetes_context and kubernetes_context not in contexts:
                if not self.config.is_local:
                    return False, (
                        f"{msg}could not find a Kubernetes context named "
                        f"'{kubernetes_context}' in the local Kubernetes "
                        f"configuration. Please make sure that the Kubernetes "
                        f"cluster is running and that the kubeconfig file is "
                        f"configured correctly. To list all configured "
                        f"contexts, run:\n\n"
                        f"  `kubectl config get-contexts`\n"
                    )
            elif (
                kubernetes_context
                and active_context
                and kubernetes_context != active_context
            ):
                logger.warning(
                    f"{msg}the Kubernetes context '{kubernetes_context}' "  # nosec
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
                    f"{kubernetes_context}`\n"
                )

            return True, ""

        def _validate_local_requirements(stack: "Stack") -> Tuple[bool, str]:
            container_registry = stack.container_registry

            # should not happen, because the stack validation takes care of
            # this, but just in case
            assert container_registry is not None

            kubernetes_context = self.config.kubernetes_context
            connector = self.get_connector()

            if not connector:
                if (
                    not kubernetes_context
                    and not self.config.kubeflow_hostname
                ):
                    return False, (
                        f"{msg}the Kubeflow orchestrator is incompletely "
                        "configured. For a multi-tenant Kubeflow deployment, "
                        "you must set the `kubeflow_hostname` attribute in the "
                        "orchestrator configuration. For a single-tenant "
                        "deployment, you must either set the "
                        "`kubernetes_context` attribute in the orchestrator "
                        "configuration to the name of the Kubernetes config "
                        "context pointing to the cluster where you would like "
                        "to run pipelines or link this stack component to a "
                        "Kubernetes cluster via a service connector (see the "
                        "'zenml orchestrator connect' CLI command)."
                    )

                if kubernetes_context:
                    valid, err = _validate_kube_context(kubernetes_context)
                    if not valid:
                        return False, err

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
                # This may result in problems when running the pipeline,
                # because the local components will not be available inside the
                # Kubeflow containers.

                # go through all stack components and identify those that
                # advertise a local path where they persist information that
                # they need to be available when running pipelines.
                for stack_comp in stack.components.values():
                    local_path = stack_comp.local_path
                    if not local_path:
                        continue
                    return False, (
                        f"{msg}the Kubeflow orchestrator is configured to run "
                        f"pipelines in a remote Kubernetes cluster but the "
                        f"'{stack_comp.name}' {stack_comp.type.value} is a "
                        "local stack component and will not be available in "
                        "the Kubeflow pipeline step.\n"
                        "Please ensure that you always use non-local "
                        f"stack components with a remote Kubeflow "
                        f"orchestrator, otherwise you may run into pipeline "
                        f"execution problems. You should use a flavor of "
                        f"{stack_comp.type.value} other than "
                        f"'{stack_comp.flavor}'.\n"
                        + silence_local_validations_msg
                    )

                # if the orchestrator is remote, the container registry must
                # also be remote.
                if container_registry.config.is_local:
                    return False, (
                        f"{msg}the Kubeflow orchestrator is configured to run "
                        f"pipelines in a remote Kubernetes cluster, but the "
                        f"'{container_registry.name}' container registry URI "
                        f"'{container_registry.config.uri}' "
                        f"points to a local container registry. Please ensure "
                        f"that you always use non-local stack components with "
                        f"a remote Kubeflow orchestrator, otherwise you will "
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
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
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
            environment: Environment variables to set in the orchestration
                environment.

        Raises:
            RuntimeError: If trying to run a pipeline in a notebook
                environment.
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

            for step_name, step in deployment.step_configurations.items():
                image = self.get_image(
                    deployment=deployment, step_name=step_name
                )

                # The command will be needed to eventually call the python step
                # within the docker container
                command = StepEntrypointConfiguration.get_entrypoint_command()

                # The arguments are passed to configure the entrypoint of the
                # docker container when the step is called.
                arguments = (
                    StepEntrypointConfiguration.get_entrypoint_arguments(
                        step_name=step_name, deployment_id=deployment.id
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
                    name=step_name,
                    image=image,
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

                for key, value in environment.items():
                    container_op.container.add_env_variable(
                        k8s_client.V1EnvVar(
                            name=key,
                            value=value,
                        )
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

        orchestrator_run_name = get_orchestrator_run_name(
            pipeline_name=deployment.pipeline_configuration.name
        )

        # Get a filepath to use to save the finished yaml to
        fileio.makedirs(self.pipeline_directory)
        pipeline_file_path = os.path.join(
            self.pipeline_directory, f"{orchestrator_run_name}.yaml"
        )

        # write the argo pipeline yaml
        KFPCompiler()._create_and_write_workflow(
            pipeline_func=_construct_kfp_pipeline,
            pipeline_name=deployment.pipeline_configuration.name,
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
        deployment: "PipelineDeploymentResponse",
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
        pipeline_name = deployment.pipeline_configuration.name
        settings = cast(
            KubeflowOrchestratorSettings, self.get_settings(deployment)
        )
        user_namespace = settings.user_namespace

        kubernetes_context = self.config.kubernetes_context
        try:
            if kubernetes_context:
                logger.info(
                    "Running in kubernetes context '%s'.",
                    kubernetes_context,
                )
            elif self.config.kubeflow_hostname:
                logger.info(
                    "Running on Kubeflow deployment '%s'.",
                    self.config.kubeflow_hostname,
                )
            elif self.connector:
                logger.info(
                    "Running with Kubernetes credentials from connector '%s'.",
                    str(self.connector),
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
                        "Please check stack component settings and "
                        "configuration!"
                    )

                logger.info(
                    "Started one-off pipeline run with ID '%s'.", result.run_id
                )

                if settings.synchronous:
                    client.wait_for_run_completion(
                        run_id=result.run_id, timeout=settings.timeout
                    )
        except urllib3.exceptions.HTTPError as error:
            if kubernetes_context:
                msg = (
                    f"Please make sure your kubernetes config is present and "
                    f"the '{kubernetes_context}' kubernetes context is "
                    "configured correctly."
                )
            elif self.connector:
                msg = (
                    f"Please check that the '{self.connector}' connector "
                    f"linked to this component is configured correctly with "
                    "valid credentials."
                )
            else:
                msg = ""

            logger.warning(
                f"Failed to upload Kubeflow pipeline: {error}. {msg}",
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

        Raises:
            RuntimeError: If the linked Kubernetes connector behaves
                unexpectedly.
        """
        connector = self.get_connector()
        client_args = settings.client_args.copy()

        # The kube_context, host and namespace are stack component
        # configurations that refer to the Kubeflow deployment. We don't want
        # these overwritten on a run by run basis by user settings
        client_args["namespace"] = self.config.kubeflow_namespace

        if connector:
            client = connector.connect()
            if not isinstance(client, k8s_client.ApiClient):
                raise RuntimeError(
                    f"Expected a k8s_client.ApiClient while trying to use the "
                    f"linked connector, but got {type(client)}."
                )

            kfp_client = KubeClientKFPClient(
                client=client,
                **client_args,
            )

            return kfp_client

        elif self.config.kubernetes_context:
            client_args["kube_context"] = self.config.kubernetes_context

        elif self.config.kubeflow_hostname:
            client_args["host"] = self.config.kubeflow_hostname

            # Handle username and password, ignore the case if one is passed and
            # not the other. Also do not attempt to get cookie if cookie is
            # already passed in client_args
            if settings.client_username and settings.client_password:
                # If cookie is already set, then ignore
                if "cookie" in client_args:
                    logger.warning(
                        "Cookie already set in `client_args`, ignoring "
                        "`client_username` and `client_password`..."
                    )
                else:
                    session_cookie = self._get_session_cookie(
                        username=settings.client_username,
                        password=settings.client_password,
                    )

                    client_args["cookies"] = session_cookie

        return kfp.Client(**client_args)

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

    def get_pipeline_run_metadata(
        self, run_id: UUID
    ) -> Dict[str, "MetadataType"]:
        """Get general component-specific metadata for a pipeline run.

        Args:
            run_id: The ID of the pipeline run.

        Returns:
            A dictionary of metadata.
        """
        hostname = self.config.kubeflow_hostname
        if not hostname:
            return {}

        hostname = hostname.rstrip("/")
        pipeline_suffix = "/pipeline"
        if hostname.endswith(pipeline_suffix):
            hostname = hostname[: -len(pipeline_suffix)]

        run = Client().get_pipeline_run(run_id)

        settings_key = settings_utils.get_stack_component_setting_key(self)
        run_settings = self.settings_class.parse_obj(
            run.config.dict().get(settings_key, self.config)
        )
        user_namespace = run_settings.user_namespace

        if user_namespace:
            run_url = (
                f"{hostname}/_/pipeline/?ns={user_namespace}#"
                f"/runs/details/{self.get_orchestrator_run_id()}"
            )
            return {
                METADATA_ORCHESTRATOR_URL: Uri(run_url),
            }
        else:
            return {
                METADATA_ORCHESTRATOR_URL: Uri(f"{hostname}"),
            }
