#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import os
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import kfp
import urllib3
from kfp_server_api.exceptions import ApiException

import zenml.io.utils
from zenml.artifact_stores import LocalArtifactStore
from zenml.enums import OrchestratorFlavor, StackComponentType
from zenml.exceptions import ProvisioningError
from zenml.integrations.kubeflow.orchestrators import local_deployment_utils
from zenml.integrations.kubeflow.orchestrators.kubeflow_dag_runner import (
    KubeflowDagRunner,
    KubeflowDagRunnerConfig,
)
from zenml.integrations.kubeflow.orchestrators.local_deployment_utils import (
    KFP_VERSION,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.repository import Repository
from zenml.stack import StackValidator
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)
from zenml.utils import networking_utils
from zenml.utils.source_utils import get_source_root_path

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.stack import Stack

logger = get_logger(__name__)

DEFAULT_KFP_UI_PORT = 8080


@register_stack_component_class(
    component_type=StackComponentType.ORCHESTRATOR,
    component_flavor=OrchestratorFlavor.KUBEFLOW,
)
class KubeflowOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines using Kubeflow.

    Attributes:
        custom_docker_base_image_name: Name of a docker image that should be
            used as the base for the image that will be run on KFP pods. If no
            custom image is given, a basic image of the active ZenML version
            will be used. **Note**: This image needs to have ZenML installed,
            otherwise the pipeline execution will fail. For that reason, you
            might want to extend the ZenML docker images found here:
            https://hub.docker.com/r/zenmldocker/zenml/
        kubeflow_pipelines_ui_port: A local port to which the KFP UI will be
            forwarded.
        kubernetes_context: Optional name of a kubernetes context to run
            pipelines in. If not set, the current active context will be used.
            You can find the active context by running `kubectl config
            current-context`.
        synchronous: If `True`, running a pipeline using this orchestrator will
            block until all steps finished running on KFP.
    """

    custom_docker_base_image_name: Optional[str] = None
    kubeflow_pipelines_ui_port: int = DEFAULT_KFP_UI_PORT
    kubernetes_context: Optional[str] = None
    synchronous = False
    supports_local_execution = True
    supports_remote_execution = True

    @property
    def flavor(self) -> OrchestratorFlavor:
        """The orchestrator flavor."""
        return OrchestratorFlavor.KUBEFLOW

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack contains a container registry."""
        return StackValidator(
            required_components={StackComponentType.CONTAINER_REGISTRY}
        )

    def get_docker_image_name(self, pipeline_name: str) -> str:
        """Returns the full docker image name including registry and tag."""

        base_image_name = f"zenml-kubeflow:{pipeline_name}"
        container_registry = Repository().active_stack.container_registry

        if container_registry:
            registry_uri = container_registry.uri.rstrip("/")
            return f"{registry_uri}/{base_image_name}"
        else:
            return base_image_name

    @property
    def root_directory(self) -> str:
        """Returns path to the root directory for all files concerning
        this orchestrator."""
        return os.path.join(
            zenml.io.utils.get_global_config_directory(),
            "kubeflow",
            str(self.uuid),
        )

    @property
    def pipeline_directory(self) -> str:
        """Returns path to a directory in which the kubeflow pipeline files
        are stored."""
        return os.path.join(self.root_directory, "pipelines")

    def prepare_pipeline_deployment(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> None:
        """Builds a docker image for the current environment and uploads it to
        a container registry if configured.
        """
        from zenml.utils.docker_utils import (
            build_docker_image,
            push_docker_image,
        )

        image_name = self.get_docker_image_name(pipeline.name)

        requirements = {*stack.requirements(), *pipeline.requirements}

        logger.debug("Kubeflow docker container requirements: %s", requirements)

        build_docker_image(
            build_context_path=get_source_root_path(),
            image_name=image_name,
            dockerignore_path=pipeline.dockerignore_file,
            requirements=requirements,
            base_image=self.custom_docker_base_image_name,
            environment_vars=self._get_environment_vars_from_secrets(
                pipeline.secrets
            ),
        )

        if stack.container_registry:
            push_docker_image(image_name)

    def run_pipeline(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        """Runs a pipeline on Kubeflow Pipelines."""
        # First check whether its running in a notebok
        from zenml.environment import Environment

        if Environment.in_notebook():
            raise RuntimeError(
                "The Kubeflow orchestrator cannot run pipelines in a notebook "
                "environment. The reason is that it is non-trivial to create "
                "a Docker image of a notebook. Please consider refactoring "
                "your notebook cells into separate scripts in a Python module "
                "and run the code outside of a notebook when using this "
                "orchestrator."
            )

        from zenml.utils.docker_utils import get_image_digest

        image_name = self.get_docker_image_name(pipeline.name)
        image_name = get_image_digest(image_name) or image_name

        fileio.make_dirs(self.pipeline_directory)
        pipeline_file_path = os.path.join(
            self.pipeline_directory, f"{pipeline.name}.yaml"
        )
        runner_config = KubeflowDagRunnerConfig(image=image_name)
        runner = KubeflowDagRunner(
            config=runner_config, output_path=pipeline_file_path
        )

        runner.run(
            pipeline=pipeline,
            stack=stack,
            runtime_configuration=runtime_configuration,
        )

        self._upload_and_run_pipeline(
            pipeline_name=pipeline.name,
            pipeline_file_path=pipeline_file_path,
            runtime_configuration=runtime_configuration,
            enable_cache=pipeline.enable_cache,
        )

    def _upload_and_run_pipeline(
        self,
        pipeline_name: str,
        pipeline_file_path: str,
        runtime_configuration: "RuntimeConfiguration",
        enable_cache: bool,
    ) -> None:
        """Tries to upload and run a KFP pipeline.

        Args:
            pipeline_name: Name of the pipeline.
            pipeline_file_path: Path to the pipeline definition file.
            runtime_configuration: Runtime configuration of the pipeline run.
            enable_cache: Whether caching is enabled for this pipeline run.
        """
        try:
            if self.kubernetes_context:
                logger.info(
                    "Running in kubernetes context '%s'.",
                    self.kubernetes_context,
                )

            # upload the pipeline to Kubeflow and start it
            client = kfp.Client(kube_context=self.kubernetes_context)
            if runtime_configuration.schedule:
                try:
                    experiment = client.get_experiment(pipeline_name)
                    logger.info(
                        "A recurring run has already been created with this "
                        "pipeline. Creating new recurring run now.."
                    )
                except (ValueError, ApiException):
                    experiment = client.create_experiment(pipeline_name)
                    logger.info(
                        "Creating a new recurring run for pipeline '%s'.. ",
                        pipeline_name,
                    )
                logger.info(
                    "You can see all recurring runs under the '%s' experiment.'",
                    pipeline_name,
                )

                schedule = runtime_configuration.schedule
                result = client.create_recurring_run(
                    experiment_id=experiment.id,
                    job_name=runtime_configuration.run_name,
                    pipeline_package_path=pipeline_file_path,
                    enable_caching=enable_cache,
                    start_time=schedule.utc_start_time,
                    end_time=schedule.utc_end_time,
                    interval_second=schedule.interval_second,
                    no_catchup=not schedule.catchup,
                )

                logger.info("Started recurring run with ID '%s'.", result.id)
            else:
                logger.info(
                    "No schedule detected. Creating a one-off pipeline run.."
                )
                result = client.create_run_from_pipeline_package(
                    pipeline_file_path,
                    arguments={},
                    run_name=runtime_configuration.run_name,
                    enable_caching=enable_cache,
                )
                logger.info(
                    "Started one-off pipeline run with ID '%s'.", result.run_id
                )

                if self.synchronous:
                    # TODO [ENG-698]: Allow configuration of the timeout as a
                    #  runtime option
                    client.wait_for_run_completion(
                        run_id=result.run_id, timeout=1200
                    )
        except urllib3.exceptions.HTTPError as error:
            logger.warning(
                "Failed to upload Kubeflow pipeline: %s. "
                "Please make sure your kube config is configured and the "
                "current context is set correctly.",
                error,
            )

    @property
    def _pid_file_path(self) -> str:
        """Returns path to the daemon PID file."""
        return os.path.join(self.root_directory, "kubeflow_daemon.pid")

    @property
    def log_file(self) -> str:
        """Path of the daemon log file."""
        return os.path.join(self.root_directory, "kubeflow_daemon.log")

    @property
    def _k3d_cluster_name(self) -> str:
        """Returns the K3D cluster name."""
        # K3D only allows cluster names with up to 32 characters, use the
        # first 8 chars of the orchestrator UUID as identifier
        return f"zenml-kubeflow-{str(self.uuid)[:8]}"

    def _get_k3d_registry_name(self, port: int) -> str:
        """Returns the K3D registry name."""
        return f"k3d-zenml-kubeflow-registry.localhost:{port}"

    @property
    def _k3d_registry_config_path(self) -> str:
        """Returns the path to the K3D registry config yaml."""
        return os.path.join(self.root_directory, "k3d_registry.yaml")

    def _get_kfp_ui_daemon_port(self) -> int:
        """Port to use for the KFP UI daemon."""
        port = self.kubeflow_pipelines_ui_port
        if port == DEFAULT_KFP_UI_PORT and not networking_utils.port_available(
            port
        ):
            # if the user didn't specify a specific port and the default
            # port is occupied, fallback to a random open port
            port = networking_utils.find_available_port()
        return port

    def list_manual_setup_steps(
        self, container_registry_name: str, container_registry_path: str
    ) -> None:
        """Logs manual steps needed to setup the Kubeflow local orchestrator."""
        global_config_dir_path = zenml.io.utils.get_global_config_directory()
        kubeflow_commands = [
            f"> k3d cluster create CLUSTER_NAME --image {local_deployment_utils.K3S_IMAGE_NAME} --registry-create {container_registry_name} --registry-config {container_registry_path} --volume {global_config_dir_path}:{global_config_dir_path}\n",
            f"> kubectl --context CLUSTER_NAME apply -k github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref={KFP_VERSION}&timeout=1m",
            "> kubectl --context CLUSTER_NAME wait --timeout=60s --for condition=established crd/applications.app.k8s.io",
            f"> kubectl --context CLUSTER_NAME apply -k github.com/kubeflow/pipelines/manifests/kustomize/env/platform-agnostic-pns?ref={KFP_VERSION}&timeout=1m",
            f"> kubectl --namespace kubeflow port-forward svc/ml-pipeline-ui {self.kubeflow_pipelines_ui_port}:80",
        ]

        logger.error("Unable to spin up local Kubeflow Pipelines deployment.")
        logger.info(
            "If you wish to spin up this Kubeflow local orchestrator manually, "
            "please enter the following commands (substituting where appropriate):\n"
        )
        logger.info("\n".join(kubeflow_commands))

    @property
    def is_provisioned(self) -> bool:
        """Returns if a local k3d cluster for this orchestrator exists."""
        if not local_deployment_utils.check_prerequisites():
            # if any prerequisites are missing there is certainly no
            # local deployment running
            return False

        return local_deployment_utils.k3d_cluster_exists(
            cluster_name=self._k3d_cluster_name
        )

    @property
    def is_running(self) -> bool:
        """Returns if the local k3d cluster for this orchestrator is running."""
        if not self.is_provisioned:
            return False

        return local_deployment_utils.k3d_cluster_running(
            cluster_name=self._k3d_cluster_name
        )

    def provision(self) -> None:
        """Provisions a local Kubeflow Pipelines deployment."""
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

        container_registry = Repository().active_stack.container_registry
        if not container_registry:
            raise ProvisioningError(
                "Unable to provision local Kubeflow Pipelines deployment: "
                "Missing container registry in current stack."
            )

        if not re.fullmatch(r"localhost:[0-9]{4,5}", container_registry.uri):
            raise ProvisioningError(
                f"Container registry URI '{container_registry.uri}' doesn't "
                f"match the expected format 'localhost:$PORT'. Provisioning "
                f"stack resources only works for local container registries."
            )

        logger.info("Provisioning local Kubeflow Pipelines deployment...")
        fileio.make_dirs(self.root_directory)
        container_registry_port = int(container_registry.uri.split(":")[-1])
        container_registry_name = self._get_k3d_registry_name(
            port=container_registry_port
        )
        local_deployment_utils.write_local_registry_yaml(
            yaml_path=self._k3d_registry_config_path,
            registry_name=container_registry_name,
            registry_uri=container_registry.uri,
        )

        try:
            local_deployment_utils.create_k3d_cluster(
                cluster_name=self._k3d_cluster_name,
                registry_name=container_registry_name,
                registry_config_path=self._k3d_registry_config_path,
            )
            kubernetes_context = f"k3d-{self._k3d_cluster_name}"
            local_deployment_utils.deploy_kubeflow_pipelines(
                kubernetes_context=kubernetes_context
            )

            artifact_store = Repository().active_stack.artifact_store
            if isinstance(artifact_store, LocalArtifactStore):
                local_deployment_utils.add_hostpath_to_kubeflow_pipelines(
                    kubernetes_context=kubernetes_context,
                    local_path=artifact_store.path,
                )

            local_deployment_utils.start_kfp_ui_daemon(
                pid_file_path=self._pid_file_path,
                log_file_path=self.log_file,
                port=self._get_kfp_ui_daemon_port(),
            )
        except Exception as e:
            logger.error(e)
            self.list_manual_setup_steps(
                container_registry_name, self._k3d_registry_config_path
            )
            self.deprovision()

    def deprovision(self) -> None:
        """Deprovisions a local Kubeflow Pipelines deployment."""
        if self.is_running:
            local_deployment_utils.delete_k3d_cluster(
                cluster_name=self._k3d_cluster_name
            )

        local_deployment_utils.stop_kfp_ui_daemon(
            pid_file_path=self._pid_file_path
        )

        if fileio.file_exists(self.log_file):
            fileio.remove(self.log_file)

        logger.info("Local kubeflow pipelines deployment deprovisioned.")

    def resume(self) -> None:
        """Resumes the local k3d cluster."""
        if self.is_running:
            logger.info("Local kubeflow pipelines deployment already running.")
            return

        if not self.is_provisioned:
            raise ProvisioningError(
                "Unable to resume local kubeflow pipelines deployment: No "
                "resources provisioned for local deployment."
            )

        local_deployment_utils.start_k3d_cluster(
            cluster_name=self._k3d_cluster_name
        )

        kubernetes_context = f"k3d-{self._k3d_cluster_name}"
        local_deployment_utils.wait_until_kubeflow_pipelines_ready(
            kubernetes_context=kubernetes_context
        )
        local_deployment_utils.start_kfp_ui_daemon(
            pid_file_path=self._pid_file_path,
            log_file_path=self.log_file,
            port=self._get_kfp_ui_daemon_port(),
        )

    def suspend(self) -> None:
        """Suspends the local k3d cluster."""
        if not self.is_running:
            logger.info("Local kubeflow pipelines deployment not running.")
            return

        local_deployment_utils.stop_k3d_cluster(
            cluster_name=self._k3d_cluster_name
        )
        local_deployment_utils.stop_kfp_ui_daemon(
            pid_file_path=self._pid_file_path
        )

    def _get_environment_vars_from_secrets(
        self, secrets: List[str]
    ) -> Dict[str, str]:
        """Get key-value pairs from list of secrets provided by the user.

        Args:
            secrets: List of secrets provided by the user.

        Returns:
            A dictionary of key-value pairs.

        Raises:
            ProvisioningError: If the stack has no secrets manager."""

        secret_manager = Repository().active_stack.secrets_manager
        if not secret_manager:
            raise ProvisioningError(
                "Unable to provision local Kubeflow Pipelines deployment: "
                "Missing secrets manager in current stack."
            )
        environment_vars: Dict[str, str] = {}
        for secret in secrets:
            environment_vars.update(secret_manager.get_secret(secret))
        return environment_vars
