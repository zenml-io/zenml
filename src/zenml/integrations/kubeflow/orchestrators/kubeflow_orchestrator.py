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

import os
import re
import sys
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Tuple
from uuid import UUID

import kfp
import urllib3
from kfp import dsl
from kfp.compiler import Compiler as KFPCompiler
from kfp_server_api.exceptions import ApiException
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from pydantic import root_validator
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline

import zenml.io.utils
from zenml.artifact_stores import LocalArtifactStore
from zenml.enums import StackComponentType
from zenml.environment import Environment
from zenml.exceptions import ProvisioningError
from zenml.integrations.kubeflow import KUBEFLOW_ORCHESTRATOR_FLAVOR
from zenml.integrations.kubeflow.orchestrators import (
    local_deployment_utils,
    utils,
)
from zenml.integrations.kubeflow.orchestrators.kubeflow_entrypoint_configuration import (
    METADATA_UI_PATH_OPTION,
    KubeflowEntrypointConfiguration,
)
from zenml.integrations.kubeflow.orchestrators.local_deployment_utils import (
    KFP_VERSION,
)
from zenml.io import fileio
from zenml.io.utils import get_global_config_directory
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.repository import Repository
from zenml.stack import Stack, StackValidator
from zenml.steps import BaseStep
from zenml.utils import networking_utils
from zenml.utils.docker_utils import get_image_digest
from zenml.utils.source_utils import get_source_root_path

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration

logger = get_logger(__name__)

DEFAULT_KFP_UI_PORT = 8080
KFP_POD_LABELS = {
    "add-pod-env": "true",
    "pipelines.kubeflow.org/pipeline-sdk-type": "zenml",
}


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
        kubeflow_hostname: The hostname to use to talk to the Kubeflow Pipelines
            API. If not set, the hostname will be derived from the Kubernetes
            API proxy.
        kubernetes_context: Optional name of a kubernetes context to run
            pipelines in. If not set, the current active context will be used.
            You can find the active context by running `kubectl config
            current-context`.
        synchronous: If `True`, running a pipeline using this orchestrator will
            block until all steps finished running on KFP.
        skip_local_validations: If `True`, the local validations will be
            skipped.
        skip_cluster_provisioning: If `True`, the k3d cluster provisioning will
            be skipped.
        skip_ui_daemon_provisioning: If `True`, provisioning the KFP UI daemon
            will be skipped.
    """

    custom_docker_base_image_name: Optional[str] = None
    kubeflow_pipelines_ui_port: int = DEFAULT_KFP_UI_PORT
    kubeflow_hostname: Optional[str] = None
    kubernetes_context: Optional[str] = None
    synchronous: bool = False
    skip_local_validations: bool = False
    skip_cluster_provisioning: bool = False
    skip_ui_daemon_provisioning: bool = False

    # Class Configuration
    FLAVOR: ClassVar[str] = KUBEFLOW_ORCHESTRATOR_FLAVOR

    @staticmethod
    def _get_k3d_cluster_name(uuid: UUID) -> str:
        """Returns the k3d cluster name corresponding to the orchestrator
        UUID."""
        # k3d only allows cluster names with up to 32 characters; use the
        # first 8 chars of the orchestrator UUID as identifier
        return f"zenml-kubeflow-{str(uuid)[:8]}"

    @staticmethod
    def _get_k3d_kubernetes_context(uuid: UUID) -> str:
        """Returns the name of the kubernetes context associated with the k3d
        cluster managed locally by ZenML corresponding to the orchestrator
        UUID."""
        return f"k3d-{KubeflowOrchestrator._get_k3d_cluster_name(uuid)}"

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

        def _validate_local_requirements(stack: Stack) -> Tuple[bool, str]:

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

            if not self.skip_local_validations and not self.is_local:

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
                        f"{stack_comp.TYPE.value} is a local stack component "
                        f"and will not be available in the Kubeflow pipeline "
                        f"step.\nPlease ensure that you always use non-local "
                        f"stack components with a remote Kubeflow orchestrator, "
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
                        f"The Kubeflow orchestrator is configured to run "
                        f"pipelines in a remote Kubernetes cluster designated "
                        f"by the '{self.kubernetes_context}' configuration "
                        f"context, but the '{container_registry.name}' "
                        f"container registry URI '{container_registry.uri}' "
                        f"points to a local container registry. Please ensure "
                        f"that you always use non-local stack components with "
                        f"a remote Kubeflow orchestrator, otherwise you will "
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
                        f"The Kubeflow orchestrator is configured to run "
                        f"pipelines in a local k3d Kubernetes cluster "
                        f"designated by the '{self.kubernetes_context}' "
                        f"configuration context, but the container registry "
                        f"URI '{container_registry.uri}' doesn't match the "
                        f"expected format 'localhost:$PORT'. "
                        f"The local Kubeflow orchestrator only works with a "
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

        base_image_name = f"zenml-kubeflow:{pipeline_name}"
        container_registry = Repository().active_stack.container_registry

        if container_registry:
            registry_uri = container_registry.uri.rstrip("/")
            return f"{registry_uri}/{base_image_name}"
        else:
            return base_image_name

    @property
    def is_local(self) -> bool:
        """Returns `True` if the KFP orchestrator is running locally (i.e. in
        the local k3d cluster managed by ZenML).
        """
        return self.kubernetes_context == self._get_k3d_kubernetes_context(
            self.uuid
        )

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
        from zenml.utils import docker_utils

        image_name = self.get_docker_image_name(pipeline.name)

        requirements = {*stack.requirements(), *pipeline.requirements}

        logger.debug("Kubeflow docker container requirements: %s", requirements)

        docker_utils.build_docker_image(
            build_context_path=get_source_root_path(),
            image_name=image_name,
            dockerignore_path=pipeline.dockerignore_file,
            requirements=requirements,
            base_image=self.custom_docker_base_image_name,
            environment_vars=self._get_environment_vars_from_secrets(
                pipeline.secrets
            ),
        )

        assert stack.container_registry  # should never happen due to validation
        stack.container_registry.push_image(image_name)

        # Store the docker image digest in the runtime configuration so it gets
        # tracked in the ZenStore
        image_digest = docker_utils.get_image_digest(image_name) or image_name
        runtime_configuration["docker_image"] = image_digest

    @staticmethod
    def _configure_container_op(container_op: dsl.ContainerOp) -> None:
        """Performs a few important changes in place to the configuration of the
        container op.
        Configures persistent mounted volumes for each stack component that
        writes to a local path.
        Adds some labels to the container_op and applies some functions to ir.

        Args:
            container_op: The kubeflow container operation to configure.
        """
        # Path to a metadata file that will be displayed in the KFP UI
        # This metadata file needs to be in a mounted emptyDir to avoid
        # sporadic failures with the (not mature) PNS executor
        # See these links for more information about limitations of PNS +
        # security context:
        # https://www.kubeflow.org/docs/components/pipelines/installation/localcluster-deployment/#deploying-kubeflow-pipelines
        # https://argoproj.github.io/argo-workflows/empty-dir/
        # KFP will switch to the Emissary executor (soon), when this emptyDir
        # mount will not be necessary anymore, but for now it's still in alpha
        # status (https://www.kubeflow.org/docs/components/pipelines/installation/choose-executor/#emissary-executor)
        volumes: Dict[str, k8s_client.V1Volume] = {
            "/outputs": k8s_client.V1Volume(
                name="outputs", empty_dir=k8s_client.V1EmptyDirVolumeSource()
            ),
        }

        stack = Repository().active_stack
        global_cfg_dir = get_global_config_directory()

        # go through all stack components and identify those that advertise
        # a local path where they persist information that they need to be
        # available when running pipelines. For those that do, mount them
        # into the Kubeflow container.
        has_local_repos = False
        for stack_comp in stack.components.values():
            local_path = stack_comp.local_path
            if not local_path:
                continue
            # double-check this convention, just in case it wasn't respected
            # as documented in `StackComponent.local_path`
            if not local_path.startswith(global_cfg_dir):
                raise ValueError(
                    f"Local path {local_path} for component {stack_comp.name} "
                    f"is not in the global config directory ({global_cfg_dir})."
                )
            has_local_repos = True
            host_path = k8s_client.V1HostPathVolumeSource(
                path=local_path, type="Directory"
            )
            volume_name = f"{stack_comp.TYPE.value}-{stack_comp.name}"
            volumes[local_path] = k8s_client.V1Volume(
                name=re.sub(r"[^0-9a-zA-Z-]+", "-", volume_name)
                .strip("-")
                .lower(),
                host_path=host_path,
            )
            logger.debug(
                "Adding host path volume for %s %s (path: %s) "
                "in kubeflow pipelines container.",
                stack_comp.TYPE.value,
                stack_comp.name,
                local_path,
            )
        container_op.add_pvolumes(volumes)

        if has_local_repos:
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

        # Add environment variables for Azure Blob Storage to pod in case they
        # are set locally
        # TODO [ENG-699]: remove this as soon as we implement credential
        #  handling
        for key in [
            "AZURE_STORAGE_ACCOUNT_KEY",
            "AZURE_STORAGE_ACCOUNT_NAME",
            "AZURE_STORAGE_CONNECTION_STRING",
            "AZURE_STORAGE_SAS_TOKEN",
        ]:
            value = os.getenv(key)
            if value:
                container_op.container.add_env_variable(
                    k8s_client.V1EnvVar(name=key, value=value)
                )

        # Add some pod labels to the container_op
        for k, v in KFP_POD_LABELS.items():
            container_op.add_pod_label(k, v)

        # Mounts configmap containing Metadata gRPC server configuration.
        container_op.apply(utils.mount_config_map_op("metadata-grpc-configmap"))

    def prepare_or_run_pipeline(
        self,
        sorted_steps: List[BaseStep],
        pipeline: "BasePipeline",
        pb2_pipeline: Pb2Pipeline,
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        """
        Creates a kfp yaml file as intermediary representation of the
        pipeline which is then deployed to the kubeflow pipelines instance.

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

        image_name = self.get_docker_image_name(pipeline.name)
        image_name = get_image_digest(image_name) or image_name

        # Create a callable for future compilation into a dsl.Pipeline.
        def _construct_kfp_pipeline() -> None:
            """Create a container_op for each step which contains the name
            of the docker image and configures the entrypoint of the docker
            image to run the step.

            Additionally, this gives each container_op information about its
            direct downstream steps.

            If this callable is passed to the `_create_and_write_workflow()`
            method of a KFPCompiler all dsl.ContainerOp instances will be
            automatically added to a singular dsl.Pipeline instance.
            """

            # Dictionary of container_ops index by the associated step name
            step_name_to_container_op: Dict[str, dsl.ContainerOp] = {}

            for step in sorted_steps:
                # The command will be needed to eventually call the python step
                # within the docker container
                command = (
                    KubeflowEntrypointConfiguration.get_entrypoint_command()
                )

                # The arguments are passed to configure the entrypoint of the
                # docker container when the step is called.
                metadata_ui_path = "/outputs/mlpipeline-ui-metadata.json"
                arguments = (
                    KubeflowEntrypointConfiguration.get_entrypoint_arguments(
                        step=step,
                        pb2_pipeline=pb2_pipeline,
                        **{METADATA_UI_PATH_OPTION: metadata_ui_path},
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
                    name=step.name,
                    image=image_name,
                    command=command,
                    arguments=arguments,
                    output_artifact_paths={
                        "mlpipeline-ui-metadata": metadata_ui_path,
                    },
                )

                # Mounts persistent volumes, configmaps and adds labels to the
                # container op
                self._configure_container_op(container_op=container_op)

                # Find the upstream container ops of the current step and
                # configure the current container op to run after them
                upstream_step_names = self.get_upstream_step_names(
                    step=step, pb2_pipeline=pb2_pipeline
                )
                for upstream_step_name in upstream_step_names:
                    upstream_container_op = step_name_to_container_op[
                        upstream_step_name
                    ]
                    container_op.after(upstream_container_op)

                # Update dictionary of container ops with the current one
                step_name_to_container_op[step.name] = container_op

        # Get a filepath to use to save the finished yaml to
        assert runtime_configuration.run_name
        fileio.makedirs(self.pipeline_directory)
        pipeline_file_path = os.path.join(
            self.pipeline_directory, f"{runtime_configuration.run_name}.yaml"
        )

        # write the argo pipeline yaml
        KFPCompiler()._create_and_write_workflow(
            pipeline_func=_construct_kfp_pipeline,
            pipeline_name=pipeline.name,
            package_path=pipeline_file_path,
        )

        # using the kfp client uploads the pipeline to kubeflow pipelines and
        # runs it there
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
            logger.info(
                "Running in kubernetes context '%s'.",
                self.kubernetes_context,
            )

            # upload the pipeline to Kubeflow and start it
            client = kfp.Client(
                host=self.kubeflow_hostname,
                kube_context=self.kubernetes_context,
            )
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
                    interval_second=schedule.interval_second.seconds,
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
                f"Failed to upload Kubeflow pipeline: %s. "
                f"Please make sure your kubernetes config is present and the "
                f"{self.kubernetes_context} kubernetes context is configured "
                f"correctly.",
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
        return self._get_k3d_cluster_name(self.uuid)

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

        global_config_dir_path = zenml.io.utils.get_global_config_directory()
        kubeflow_commands = [
            f"> k3d cluster create {self._k3d_cluster_name} --image {local_deployment_utils.K3S_IMAGE_NAME} --registry-create {container_registry_name} --registry-config {container_registry_path} --volume {global_config_dir_path}:{global_config_dir_path}\n",
            f"> kubectl --context {self.kubernetes_context} apply -k github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref={KFP_VERSION}&timeout=5m",
            f"> kubectl --context {self.kubernetes_context} wait --timeout=60s --for condition=established crd/applications.app.k8s.io",
            f"> kubectl --context {self.kubernetes_context} apply -k github.com/kubeflow/pipelines/manifests/kustomize/env/platform-agnostic-pns?ref={KFP_VERSION}&timeout=5m",
            f"> kubectl --context {self.kubernetes_context} --namespace kubeflow port-forward svc/ml-pipeline-ui {self.kubeflow_pipelines_ui_port}:80",
        ]

        logger.info(
            "If you wish to spin up this Kubeflow local orchestrator manually, "
            "please enter the following commands:\n"
        )
        logger.info("\n".join(kubeflow_commands))

    @property
    def is_provisioned(self) -> bool:
        """Returns if a local k3d cluster for this orchestrator exists."""
        if not local_deployment_utils.check_prerequisites(
            skip_k3d=self.skip_cluster_provisioning or not self.is_local,
            skip_kubectl=self.skip_cluster_provisioning
            and self.skip_ui_daemon_provisioning,
        ):
            # if any prerequisites are missing there is certainly no
            # local deployment running
            return False

        return self.is_cluster_provisioned

    @property
    def is_running(self) -> bool:
        """Returns if the local k3d cluster and the UI daemon for this
        orchestrator are both running."""
        return (
            self.is_provisioned
            and self.is_cluster_running
            and self.is_daemon_running
        )

    @property
    def is_suspended(self) -> bool:
        """Returns if the local k3d cluster and the UI daemon for this
        orchestrator are both stopped."""
        return (
            self.is_provisioned
            and (self.skip_cluster_provisioning or not self.is_cluster_running)
            and (self.skip_ui_daemon_provisioning or not self.is_daemon_running)
        )

    @property
    def is_cluster_provisioned(self) -> bool:
        """Returns if the local k3d cluster for this orchestrator is provisioned.

        For remote (i.e. not managed by ZenML) Kubeflow Pipelines installations,
        this always returns True.
        """
        if self.skip_cluster_provisioning or not self.is_local:
            return True
        return local_deployment_utils.k3d_cluster_exists(
            cluster_name=self._k3d_cluster_name
        )

    @property
    def is_cluster_running(self) -> bool:
        """Returns if the local k3d cluster for this orchestrator is running.

        For remote (i.e. not managed by ZenML) Kubeflow Pipelines installations,
        this always returns True.
        """
        if self.skip_cluster_provisioning or not self.is_local:
            return True
        return local_deployment_utils.k3d_cluster_running(
            cluster_name=self._k3d_cluster_name
        )

    @property
    def is_daemon_running(self) -> bool:
        """Returns if the local Kubeflow UI daemon for this orchestrator is
        running."""
        if self.skip_ui_daemon_provisioning:
            return True

        if sys.platform != "win32":
            from zenml.utils.daemon import check_if_daemon_is_running

            return check_if_daemon_is_running(self._pid_file_path)
        else:
            return True

    def provision(self) -> None:
        """Provisions a local Kubeflow Pipelines deployment."""
        if self.skip_cluster_provisioning:
            return

        if self.is_running:
            logger.info(
                "Found already existing local Kubeflow Pipelines deployment. "
                "If there are any issues with the existing deployment, please "
                "run 'zenml stack down --yes' to delete it."
            )
            return

        if not local_deployment_utils.check_prerequisites():
            raise ProvisioningError(
                "Unable to provision local Kubeflow Pipelines deployment: "
                "Please install 'k3d' and 'kubectl' and try again."
            )

        container_registry = Repository().active_stack.container_registry

        # should not happen, because the stack validation takes care of this,
        # but just in case
        assert container_registry is not None

        fileio.makedirs(self.root_directory)

        if not self.is_local:
            # don't provision any resources if using a remote KFP installation
            return

        logger.info("Provisioning local Kubeflow Pipelines deployment...")

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
            kubernetes_context = self.kubernetes_context

            # will never happen, but mypy doesn't know that
            assert kubernetes_context is not None

            local_deployment_utils.deploy_kubeflow_pipelines(
                kubernetes_context=kubernetes_context
            )

            artifact_store = Repository().active_stack.artifact_store
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
        if self.skip_cluster_provisioning:
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
        """Resumes the local k3d cluster."""
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
            not self.skip_cluster_provisioning
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
            not self.skip_cluster_provisioning
            and self.is_local
            and self.is_cluster_running
        ):
            # don't suspend any resources if using a remote KFP installation
            local_deployment_utils.stop_k3d_cluster(
                cluster_name=self._k3d_cluster_name
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
        environment_vars: Dict[str, str] = {}
        secret_manager = Repository().active_stack.secrets_manager
        if secrets and secret_manager:
            for secret in secrets:
                secret_schema = secret_manager.get_secret(secret)
                environment_vars.update(secret_schema.content)
        elif secrets and not secret_manager:
            raise ProvisioningError(
                "Unable to provision local Kubeflow Pipelines deployment: "
                f"You passed in the following secrets: { ', '.join(secrets) }, "
                "however, no secrets manager is registered for the current "
                "stack."
            )
        else:
            # No secrets provided by the user.
            pass
        return environment_vars
