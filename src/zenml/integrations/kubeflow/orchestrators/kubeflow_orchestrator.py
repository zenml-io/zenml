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
import types
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    cast,
)
from uuid import UUID

import kfp
import requests
import urllib3
from kfp import dsl
from kfp.client import Client as KFPClient
from kfp.compiler import Compiler
from kfp_server_api.exceptions import ApiException
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config

from zenml.client import Client
from zenml.config.resource_settings import ResourceSettings
from zenml.constants import (
    METADATA_ORCHESTRATOR_URL,
)
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.enums import StackComponentType
from zenml.environment import Environment
from zenml.integrations.kubeflow.flavors.kubeflow_orchestrator_flavor import (
    KubeflowOrchestratorConfig,
    KubeflowOrchestratorSettings,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType, Uri
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.stack import StackValidator
from zenml.utils import io_utils, settings_utils, yaml_utils

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse
    from zenml.stack import Stack


logger = get_logger(__name__)

KFP_POD_LABELS = {
    "add-pod-env": "true",
    "pipelines.kubeflow.org/pipeline-sdk-type": "zenml",
}

ENV_KFP_RUN_ID = "KFP_RUN_ID"
KFP_ACCELERATOR_NODE_SELECTOR_CONSTRAINT_LABEL = "accelerator"


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
            + self._KUBE_PROXY_PATH.format(kwargs.get("namespace", "kubeflow"))
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

    _k8s_client: Optional[k8s_client.ApiClient] = None
    supports_scheduling: ClassVar[bool] = True

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
            return KubeClientKFPClient(
                client=client,
                **client_args,
            )

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
        return KFPClient(**client_args)

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

            if not self.connector:
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

            if not self.config.is_local:
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

    def _create_dynamic_component(
        self,
        image: str,
        command: List[str],
        arguments: List[str],
        component_name: str,
    ) -> dsl.PipelineTask:
        """Creates a dynamic container component for a Kubeflow pipeline.

        Args:
            image: The image to use for the component.
            command: The command to use for the component.
            arguments: The arguments to use for the component.
            component_name: The name of the component.

        Returns:
            The dynamic container component.
        """

        def dynamic_container_component() -> dsl.ContainerSpec:
            """Dynamic container component.

            Returns:
                The dynamic container component.
            """
            return dsl.ContainerSpec(
                image=image,
                command=command,
                args=arguments,
            )

        # Change the name of the function
        new_container_spec_func = types.FunctionType(
            dynamic_container_component.__code__,
            dynamic_container_component.__globals__,
            name=component_name,
            argdefs=dynamic_container_component.__defaults__,
            closure=dynamic_container_component.__closure__,
        )
        pipeline_task = dsl.container_component(new_container_spec_func)

        return pipeline_task

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
        orchestrator_run_name = get_orchestrator_run_name(
            pipeline_name=deployment.pipeline_configuration.name
        ).replace("_", "-")

        def _create_dynamic_pipeline() -> Any:
            """Create a dynamic pipeline including each step.

            Returns:
                pipeline_func
            """
            step_name_to_dynamic_component: Dict[str, Any] = {}
            node_selector_constraint: Optional[Tuple[str, str]] = None

            for step_name, step in deployment.step_configurations.items():
                image = self.get_image(
                    deployment=deployment,
                    step_name=step_name,
                )
                command = StepEntrypointConfiguration.get_entrypoint_command()
                arguments = (
                    StepEntrypointConfiguration.get_entrypoint_arguments(
                        step_name=step_name,
                        deployment_id=deployment.id,
                    )
                )
                dynamic_component = self._create_dynamic_component(
                    image, command, arguments, step_name
                )
                step_settings = cast(
                    KubeflowOrchestratorSettings, self.get_settings(step)
                )
                pod_settings = step_settings.pod_settings
                if pod_settings:
                    if pod_settings.host_ipc:
                        logger.warning(
                            "Host IPC is set to `True` but not supported in "
                            "this orchestrator. Ignoring..."
                        )
                    if pod_settings.affinity:
                        logger.warning(
                            "Affinity is set but not supported in Kubeflow with "
                            "Kubeflow Pipelines 2.x. Ignoring..."
                        )
                    if pod_settings.tolerations:
                        logger.warning(
                            "Tolerations are set but not supported in "
                            "Kubeflow with Kubeflow Pipelines 2.x. Ignoring..."
                        )
                    if pod_settings.volumes:
                        logger.warning(
                            "Volumes are set but not supported in Kubeflow with "
                            "Kubeflow Pipelines 2.x. Ignoring..."
                        )
                    if pod_settings.volume_mounts:
                        logger.warning(
                            "Volume mounts are set but not supported in "
                            "Kubeflow with Kubeflow Pipelines 2.x. Ignoring..."
                        )

                    # apply pod settings
                    if (
                        KFP_ACCELERATOR_NODE_SELECTOR_CONSTRAINT_LABEL
                        in pod_settings.node_selectors.keys()
                    ):
                        node_selector_constraint = (
                            KFP_ACCELERATOR_NODE_SELECTOR_CONSTRAINT_LABEL,
                            pod_settings.node_selectors[
                                KFP_ACCELERATOR_NODE_SELECTOR_CONSTRAINT_LABEL
                            ],
                        )

                step_name_to_dynamic_component[step_name] = dynamic_component

            @dsl.pipeline(  # type: ignore[misc]
                display_name=orchestrator_run_name,
            )
            def dynamic_pipeline() -> None:
                """Dynamic pipeline."""
                # iterate through the components one by one
                # (from step_name_to_dynamic_component)
                for (
                    component_name,
                    component,
                ) in step_name_to_dynamic_component.items():
                    # for each component, check to see what other steps are
                    # upstream of it
                    step = deployment.step_configurations[component_name]
                    upstream_step_components = [
                        step_name_to_dynamic_component[upstream_step_name]
                        for upstream_step_name in step.spec.upstream_steps
                    ]
                    task = (
                        component()
                        .set_display_name(
                            name=component_name,
                        )
                        .set_caching_options(enable_caching=False)
                        .set_env_variable(
                            name=ENV_KFP_RUN_ID,
                            value=dsl.PIPELINE_JOB_NAME_PLACEHOLDER,
                        )
                        .after(*upstream_step_components)
                    )
                    self._configure_container_resources(
                        task,
                        step.config.resource_settings,
                        node_selector_constraint,
                    )

            return dynamic_pipeline

        def _update_yaml_with_environment(
            yaml_file_path: str, environment: Dict[str, str]
        ) -> None:
            """Updates the env section of the steps in the YAML file with the given environment variables.

            Args:
                yaml_file_path: The path to the YAML file to update.
                environment: A dictionary of environment variables to add.
            """
            pipeline_definition = yaml_utils.read_yaml(pipeline_file_path)

            # Iterate through each component and add the environment variables
            for executor in pipeline_definition["deploymentSpec"]["executors"]:
                if (
                    "container"
                    in pipeline_definition["deploymentSpec"]["executors"][
                        executor
                    ]
                ):
                    container = pipeline_definition["deploymentSpec"][
                        "executors"
                    ][executor]["container"]
                    if "env" not in container:
                        container["env"] = []
                    for key, value in environment.items():
                        container["env"].append({"name": key, "value": value})

            yaml_utils.write_yaml(pipeline_file_path, pipeline_definition)

            print(
                f"Updated YAML file with environment variables at {yaml_file_path}"
            )

        # Get a filepath to use to save the finished yaml to
        fileio.makedirs(self.pipeline_directory)
        pipeline_file_path = os.path.join(
            self.pipeline_directory, f"{orchestrator_run_name}.yaml"
        )

        # write the argo pipeline yaml
        Compiler().compile(
            pipeline_func=_create_dynamic_pipeline(),
            package_path=pipeline_file_path,
            pipeline_name=orchestrator_run_name,
        )

        # Let's update the YAML file with the environment variables
        _update_yaml_with_environment(pipeline_file_path, environment)

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
                    experiment_id=experiment.experiment_id,
                    job_name=run_name,
                    pipeline_package_path=pipeline_file_path,
                    enable_caching=False,
                    cron_expression=deployment.schedule.cron_expression,
                    start_time=deployment.schedule.utc_start_time,
                    end_time=deployment.schedule.utc_end_time,
                    interval_second=interval_seconds,
                    no_catchup=not deployment.schedule.catchup,
                )

                logger.info(
                    "Started recurring run with ID '%s'.",
                    result.recurring_run_id,
                )
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

        cookie_dict: Dict[str, str] = session.cookies.get_dict()  # type: ignore[no-untyped-call]

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
        run_settings = self.settings_class.model_validate(
            run.config.model_dump().get(settings_key, self.config)
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

    def _configure_container_resources(
        self,
        dynamic_component: dsl.PipelineTask,
        resource_settings: "ResourceSettings",
        node_selector_constraint: Optional[Tuple[str, str]] = None,
    ) -> dsl.PipelineTask:
        """Adds resource requirements to the container.

        Args:
            dynamic_component: The dynamic component to add the resource
                settings to.
            resource_settings: The resource settings to use for this
                container.
            node_selector_constraint: Node selector constraint to apply to
                the container.

        Returns:
            The dynamic component with the resource settings applied.
        """
        # Set optional CPU, RAM and GPU constraints for the pipeline
        if resource_settings:
            cpu_limit = resource_settings.cpu_count or None

        if cpu_limit is not None:
            dynamic_component = dynamic_component.set_cpu_limit(str(cpu_limit))

        memory_limit = resource_settings.get_memory() or None
        if memory_limit is not None:
            dynamic_component = dynamic_component.set_memory_limit(
                memory_limit
            )

        gpu_limit = (
            resource_settings.gpu_count
            if resource_settings.gpu_count is not None
            else 0
        )

        if node_selector_constraint:
            (constraint_label, value) = node_selector_constraint
            if gpu_limit is not None and gpu_limit > 0:
                dynamic_component = (
                    dynamic_component.set_accelerator_type(value)
                    .set_accelerator_limit(gpu_limit)
                    .set_gpu_limit(gpu_limit)
                )
            elif constraint_label == "accelerator" and gpu_limit == 0:
                logger.warning(
                    "GPU limit is set to 0 but a GPU type is specified. Ignoring GPU settings."
                )

        return dynamic_component
