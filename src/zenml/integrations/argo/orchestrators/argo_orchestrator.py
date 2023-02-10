#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Implementation of the Argo orchestrator."""
import os
import subprocess
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Type, cast

from hera import (  # type: ignore[attr-defined]
    Env,
    Task,
    Workflow,
    WorkflowService,
)
from kubernetes import config as k8s_config

from zenml.constants import ORCHESTRATOR_DOCKER_IMAGE_KEY
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.enums import StackComponentType
from zenml.environment import Environment
from zenml.integrations.argo.flavors.argo_orchestrator_flavor import (
    ArgoOrchestratorConfig,
    ArgoOrchestratorSettings,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.stack import StackValidator
from zenml.utils import io_utils
from zenml.utils.pipeline_docker_image_builder import (
    PipelineDockerImageBuilder,
)

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.stack import Stack


logger = get_logger(__name__)

ENV_ZENML_ARGO_RUN_ID = "ZENML_ARGO_RUN_ID"


def dummy() -> None:
    """Create dummy function for argo task."""
    print("This function is ignored in favor of the entrypoint.")


class ArgoOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines using Argo."""

    @property
    def config(self) -> ArgoOrchestratorConfig:
        """Returns the `ArgoOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(ArgoOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Argo orchestrator.

        Returns:
            The settings class.
        """
        return ArgoOrchestratorSettings

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

            contexts, _ = self.get_kubernetes_contexts()

            if self.config.kubernetes_context not in contexts:
                return False, (
                    f"Could not find a Kubernetes context named "
                    f"'{self.config.kubernetes_context}' in the local "
                    f"Kubernetes configuration. Please make sure that the "
                    f"Kubernetes cluster is running and that the kubeconfig "
                    f"file is configured correctly. To list all configured "
                    f"contexts, run:\n\n"
                    f"  `kubectl config get-contexts`\n"
                )

            # go through all stack components and identify those that
            # advertise a local path where they persist information that
            # they need to be available when running pipelines.
            for stack_component in stack.components.values():
                local_path = stack_component.local_path
                if local_path is None:
                    continue
                return False, (
                    f"The Argo orchestrator is configured to run "
                    f"pipelines in a remote Kubernetes cluster designated "
                    f"by the '{self.config.kubernetes_context}' configuration "
                    f"context, but the '{stack_component.name}' "
                    f"{stack_component.type.value} is a local stack component "
                    f"and will not be available in the Argo pipeline "
                    f"step.\nPlease ensure that you always use non-local "
                    f"stack components with a Argo orchestrator, "
                    f"otherwise you may run into pipeline execution "
                    f"problems. You should use a flavor of "
                    f"{stack_component.type.value} other than "
                    f"'{stack_component.flavor}'."
                )

            if container_registry.config.is_local:
                return False, (
                    f"The Argo orchestrator is configured to run "
                    f"pipelines in a remote Kubernetes cluster designated "
                    f"by the '{self.config.kubernetes_context}' configuration "
                    f"context, but the '{container_registry.name}' "
                    f"container registry URI '{container_registry.config.uri}' "
                    f"points to a local container registry. Please ensure "
                    f"that you always use non-local stack components with "
                    f"a Argo orchestrator, otherwise you will "
                    f"run into problems. You should use a flavor of "
                    f"container registry other than "
                    f"'{container_registry.flavor}'."
                )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate,
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
        docker_image_builder = PipelineDockerImageBuilder()
        repo_digest = docker_image_builder.build_docker_image(
            deployment=deployment, stack=stack
        )
        deployment.add_extra(ORCHESTRATOR_DOCKER_IMAGE_KEY, repo_digest)

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeployment",
        stack: "Stack",
    ) -> Any:
        """Run the pipeline on Argo.

        This function first compiles the ZenML pipeline into a Argo yaml
        and then applies this configuration to run the pipeline.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.

        Raises:
            RuntimeError: If you try to run the pipelines in a notebook environment.
        """
        # First check whether the code running in a notebook
        if Environment.in_notebook():
            raise RuntimeError(
                "The Argo orchestrator cannot run pipelines in a notebook "
                "environment. The reason is that it is non-trivial to create "
                "a Docker image of a notebook. Please consider refactoring "
                "your notebook cells into separate scripts in a Python module "
                "and run the code outside of a notebook when using this "
                "orchestrator."
            )

        image_name = deployment.pipeline.extra[ORCHESTRATOR_DOCKER_IMAGE_KEY]
        orchestrator_run_name = get_orchestrator_run_name(
            pipeline_name=deployment.pipeline.name
        )

        # Dictionary mapping step names to airflow_operators. This will be needed
        # to configure airflow operator dependencies
        settings = cast(
            ArgoOrchestratorSettings, self.get_settings(deployment)
        )

        with Workflow(
            orchestrator_run_name.replace("_", "-"),
            service=WorkflowService(
                host=f"https://127.0.0.1:{self.config.argo_ui_port}",
                namespace=self.config.kubernetes_namespace,
                token=settings.token,
                verify_ssl=False,
            ),
        ) as w:
            step_name_to_argo_task = {}

            for step_name, step in deployment.steps.items():
                # Create callable that will be used by argo to execute the step
                # within the orchestrated environment
                command = StepEntrypointConfiguration.get_entrypoint_command()
                arguments = (
                    StepEntrypointConfiguration.get_entrypoint_arguments(
                        step_name=step_name,
                    )
                )

                current_task = Task(
                    step_name.replace("_", "-"),
                    dummy,
                    image=image_name,
                    command=command,
                    args=arguments,
                    env=[
                        Env(
                            name=ENV_ZENML_ARGO_RUN_ID,
                            value="{{workflow.uid}}",
                        )
                    ],
                )

                if self.requires_resources_in_orchestration_environment(step):
                    logger.warning(
                        "Specifying step resources is not yet supported for "
                        "the Airflow orchestrator, ignoring resource "
                        "configuration for step %s.",
                        step_name,
                    )

                # Configure the current argo operator to run after all upstream
                # operators finished executing
                step_name_to_argo_task[step_name] = current_task
                for upstream_step_name in step.spec.upstream_steps:
                    step_name_to_argo_task[upstream_step_name] >> current_task

        if deployment.schedule:
            logger.warning(
                "The Argo Orchestrator currently does not support the "
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )

        logger.info(
            "Running Argo pipeline in kubernetes context '%s' and namespace "
            "'%s'.",
            self.config.kubernetes_context,
            self.config.kubernetes_namespace,
        )
        try:
            w.create()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to upload Argo pipeline: {str(e)}. "
                f"Please make sure your kubernetes config is present and the "
                f"{self.config.kubernetes_context} kubernetes context is configured "
                f"correctly.",
            )

    def get_orchestrator_run_id(self) -> str:
        """Return the active orchestrator run id.

        Raises:
            RuntimeError: If the environment variable specifying the run id
                is not set.

        Returns:
            The orchestrator run id.
        """
        try:
            return os.environ[ENV_ZENML_ARGO_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_ARGO_RUN_ID}."
            )

    @property
    def root_directory(self) -> str:
        """Returns path to the root directory for all files concerning this orchestrator.

        Returns:
            Path to the root directory.
        """
        return os.path.join(
            io_utils.get_global_config_directory(),
            "argo",
            str(self.id),
        )

    @property
    def pipeline_directory(self) -> str:
        """Path to a directory in which the Argo pipeline files are stored.

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
        return os.path.join(self.root_directory, "argo_daemon.pid")

    @property
    def log_file(self) -> str:
        """Path of the daemon log file.

        Returns:
            Path of the daemon log file.
        """
        return os.path.join(self.root_directory, "argo_daemon.log")

    @property
    def is_provisioned(self) -> bool:
        """Returns if a local k3d cluster for this orchestrator exists.

        Returns:
            True if a local k3d cluster exists, False otherwise.
        """
        return fileio.exists(self.root_directory)
