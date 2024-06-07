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

import kfp
from kfp import dsl
from kfp.client import Client as KFPClient
from kfp.compiler import KFPCompiler
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config

from zenml.entrypoints import StepEntrypointConfiguration
from zenml.enums import StackComponentType
from zenml.environment import Environment
from zenml.integrations.tekton.flavors.tekton_orchestrator_flavor import (
    TektonOrchestratorConfig,
    TektonOrchestratorSettings,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.stack import StackValidator
from zenml.utils import io_utils, yaml_utils

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.models import PipelineDeploymentResponse
    from zenml.stack import Stack


logger = get_logger(__name__)

ENV_ZENML_TEKTON_RUN_ID = "ZENML_TEKTON_RUN_ID"


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


class TektonOrchestrator(ContainerizedOrchestrator):
    """Orchestrator responsible for running pipelines using Tekton."""

    _k8s_client: Optional[k8s_client.ApiClient] = None

    def _get_kfp_client(
        self,
        settings: TektonOrchestratorSettings,
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
        client_args["namespace"] = self.config.kubernetes_namespace

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

        elif self.config.tekton_hostname:
            client_args["host"] = self.config.tekton_hostname

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
        return KFPClient(**client_args)

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
            msg = f"'{self.name}' Tekton orchestrator error: "

            if not self.connector:
                if not kubernetes_context:
                    return False, (
                        f"{msg}you must either link this stack component to a "
                        "Kubernetes service connector (see the 'zenml "
                        "orchestrator connect' CLI command) or explicitly set "
                        "the `kubernetes_context` attribute to the name of "
                        "the Kubernetes config context pointing to the "
                        "cluster where you would like to run pipelines."
                    )

                contexts, active_context = self.get_kubernetes_contexts()

                if kubernetes_context not in contexts:
                    return False, (
                        f"{msg}could not find a Kubernetes context named "
                        f"'{kubernetes_context}' in the local "
                        "Kubernetes configuration. Please make sure that the "
                        "Kubernetes cluster is running and that the "
                        "kubeconfig file is configured correctly. To list all "
                        "configured contexts, run:\n\n"
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
                # This may result in problems when running the pipeline, "
                # because the local components will not be available inside
                # theTekton containers.

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

    def _create_dynamic_component(
        self,
        image: str,
        command: List[str],
        arguments: List[str],
        component_name: str,
    ) -> dsl.PipelineTask:
        """Creates a dynamic container component for a Tekton pipeline.

        Args:
            image: The image to use for the component.
            command: The command to use for the component.
            arguments: The arguments to use for the component.
            component_name: The name of the component.
        """

        @dsl.container_component
        def dynamic_container_component() -> dsl.ContainerSpec:  # type: ignore
            """Dynamic container component.

            Returns:
                The dynamic container component.
            """
            _component = dsl.ContainerSpec(
                image=image,
                command=command,
                args=arguments,
            )

            _component.__name__ = component_name
            return _component

        return dynamic_container_component

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
        ).replace("_", "-")

        def _create_dynamic_pipeline() -> Any:
            """Create a dynamic pipeline including each step.

            Returns:
                pipeline_func
            """
            step_name_to_dynamic_component: Dict[str, Any] = {}

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
                    TektonOrchestratorSettings, self.get_settings(step)
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
                            "Affinity is set but not supported in Tekton with "
                            "Kubeflow Pipelines 2.x. Ignoring..."
                        )
                    if pod_settings.tolerations:
                        logger.warning(
                            "Tolerations are set but not supported in "
                            "Tekton with Kubeflow Pipelines 2.x. Ignoring..."
                        )
                    if pod_settings.volumes:
                        logger.warning(
                            "Volumes are set but not supported in Tekton with "
                            "Kubeflow Pipelines 2.x. Ignoring..."
                        )
                    if pod_settings.volume_mounts:
                        logger.warning(
                            "Volume mounts are set but not supported in "
                            "Tekton with Kubeflow Pipelines 2.x. Ignoring..."
                        )

                    # apply pod settings
                    for key, value in pod_settings.node_selectors.items():
                        dynamic_component.add_node_selector_constraint(
                            label_name=key, value=value
                        )

                # add resource requirements
                if step.config.resource_settings:
                    if step.config.resource_settings.cpu_count is not None:
                        dynamic_component = dynamic_component.set_cpu_limit(
                            step.config.resource_settings.cpu_count
                        )

                    if step.config.resource_settings.gpu_count is not None:
                        dynamic_component = (
                            dynamic_component.set_accelerator_limit(
                                step.config.resource_settings.gpu_count
                            )
                        )

                    if step.config.resource_settings.memory is not None:
                        memory_limit = step.config.resource_settings.memory[
                            :-1
                        ]
                        dynamic_component = dynamic_component.set_memory_limit(
                            memory_limit
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
                    component().set_caching_options(
                        enable_caching=False
                    ).set_env_variable(
                        name=ENV_ZENML_TEKTON_RUN_ID,
                        value="$(context.pipelineRun.name)",
                    ).after(*upstream_step_components)

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

        KFPCompiler().compile(
            pipeline_func=_create_dynamic_pipeline(),
            package_path=pipeline_file_path,
            pipeline_name=orchestrator_run_name,
        )

        # Let's update the YAML file with the environment variables
        _update_yaml_with_environment(pipeline_file_path, environment)

        logger.info(
            "Writing Tekton workflow definition to `%s`.", pipeline_file_path
        )

        settings = cast(
            TektonOrchestratorSettings, self.get_settings(deployment)
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

        client = self._get_kfp_client(settings=settings)
        client.create_run_from_pipeline_package(
            pipeline_file_path,
            enable_caching=True,
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
        except KeyError as e:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_TEKTON_RUN_ID}."
            ) from e

    @property
    def root_directory(self) -> str:
        """Returns path to the root directory.

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
