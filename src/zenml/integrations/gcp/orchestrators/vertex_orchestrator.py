# Original License:
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

# New License:
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
"""Implementation of the VertexAI orchestrator."""

import os
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Tuple

import kfp
from google.api_core import exceptions as google_exceptions
from google.cloud import aiplatform
from kfp import dsl
from kfp.v2 import dsl as dslv2
from kfp.v2.compiler import Compiler as KFPV2Compiler

from zenml.enums import StackComponentType
from zenml.integrations.gcp import (
    GCP_ARTIFACT_STORE_FLAVOR,
    GCP_VERTEX_ORCHESTRATOR_FLAVOR,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsMixin,
)
from zenml.integrations.gcp.orchestrators.vertex_entrypoint_configuration import (
    VERTEX_JOB_ID_OPTION,
    VertexEntrypointConfiguration,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.repository import Repository
from zenml.stack.stack_validator import StackValidator
from zenml.utils.docker_utils import get_image_digest
from zenml.utils.io_utils import get_global_config_directory
from zenml.utils.source_utils import get_source_root_path

if TYPE_CHECKING:
    from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline

    from zenml.pipelines.base_pipeline import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.stack import Stack
    from zenml.steps import BaseStep, ResourceConfiguration

logger = get_logger(__name__)


def _clean_pipeline_name(pipeline_name: str) -> str:
    """Clean pipeline name to be a valid Vertex AI Pipeline name.

    Arguments:
        pipeline_name: pipeline name to be cleaned.

    Returns:
        Cleaned pipeline name.
    """
    return pipeline_name.replace("_", "-").lower()


class VertexOrchestrator(BaseOrchestrator, GoogleCredentialsMixin):
    """Orchestrator responsible for running pipelines on Vertex AI.

    Attributes:
        custom_docker_base_image_name: Name of the Docker image that should be
            used as the base for the image that will be used to execute each of
            the steps. If no custom base image is given, a basic image of the
            active ZenML version will be used. **Note**: This image needs to
            have ZenML installed, otherwise the pipeline execution will fail.
            For that reason, you might want to extend the ZenML Docker images found
            here: https://hub.docker.com/r/zenmldocker/zenml/
        project: GCP project name. If `None`, the project will be inferred from
            the environment.
        location: Name of GCP region where the pipeline job will be executed.
            Vertex AI Pipelines is available in the following regions:
            https://cloud.google.com/vertex-ai/docs/general/locations#feature
            -availability
        pipeline_root: a Cloud Storage URI that will be used by the Vertex AI
        Pipelines.
            If not provided but the artifact store in the stack used to execute
            the pipeline is a
            `zenml.integrations.gcp.artifact_stores.GCPArtifactStore`,
            then a subdirectory of the artifact store will be used.
        encryption_spec_key_name: The Cloud KMS resource identifier of the
        customer
            managed encryption key used to protect the job. Has the form:
            `projects/<PRJCT>/locations/<REGION>/keyRings/<KR>/cryptoKeys/<KEY>`
            . The key needs to be in the same region as where the compute
            resource is created.
        workload_service_account: the service account for workload run-as
            account. Users submitting jobs must have act-as permission on this
            run-as account.
            If not provided, the default service account will be used.
        network: the full name of the Compute Engine Network to which the job
        should
            be peered. For example, `projects/12345/global/networks/myVPC`
            If not provided, the job will not be peered with any network.
        synchronous: If `True`, running a pipeline using this orchestrator will
            block until all steps finished running on Vertex AI Pipelines
            service.
        cpu_limit: The maximum CPU limit for this operator. This string value
            can be a number (integer value for number of CPUs) as string,
            or a number followed by "m", which means 1/1000. You can specify
            at most 96 CPUs.
            (see. https://cloud.google.com/vertex-ai/docs/pipelines/machine-types)
        memory_limit: The maximum memory limit for this operator. This string
            value can be a number, or a number followed by "K" (kilobyte),
            "M" (megabyte), or "G" (gigabyte). At most 624GB is supported.
        node_selector_constraint: Each constraint is a key-value pair label.
            For the container to be eligible to run on a node, the node must have
            each of the constraints appeared as labels.
            For example a GPU type can be providing by one of the following tuples:
                - ("cloud.google.com/gke-accelerator", "NVIDIA_TESLA_A100")
                - ("cloud.google.com/gke-accelerator", "NVIDIA_TESLA_K80")
                - ("cloud.google.com/gke-accelerator", "NVIDIA_TESLA_P4")
                - ("cloud.google.com/gke-accelerator", "NVIDIA_TESLA_P100")
                - ("cloud.google.com/gke-accelerator", "NVIDIA_TESLA_T4")
                - ("cloud.google.com/gke-accelerator", "NVIDIA_TESLA_V100")
            Hint: the selected region (location) must provide the requested accelerator
            (see https://cloud.google.com/compute/docs/gpus/gpu-regions-zones).
        gpu_limit: The GPU limit (positive number) for the operator.
            For more information about GPU resources, see:
            https://cloud.google.com/vertex-ai/docs/training/configure-compute#specifying_gpus
    """

    custom_docker_base_image_name: Optional[str] = None
    project: Optional[str] = None
    location: str
    pipeline_root: Optional[str] = None
    labels: Dict[str, str] = {}
    encryption_spec_key_name: Optional[str] = None
    workload_service_account: Optional[str] = None
    network: Optional[str] = None
    synchronous: bool = False

    cpu_limit: Optional[str] = None
    memory_limit: Optional[str] = None
    node_selector_constraint: Optional[Tuple[str, str]] = None
    gpu_limit: Optional[int] = None

    _pipeline_root: str

    FLAVOR: ClassVar[str] = GCP_VERTEX_ORCHESTRATOR_FLAVOR

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack contains a container registry.

        Also validates that the artifact store and metadata store used are not
        local.

        Returns:
            A StackValidator instance.
        """

        def _validate_stack_requirements(stack: "Stack") -> Tuple[bool, str]:
            """Validates that all the stack components are not local.

            Args:
                stack: The stack to validate.

            Returns:
                A tuple of (is_valid, error_message).
            """
            # Validate that the container registry is not local.
            container_registry = stack.container_registry
            if container_registry and container_registry.is_local:
                return False, (
                    f"The Vertex orchestrator does not support local "
                    f"container registries. You should replace the component '"
                    f"{container_registry.name}' "
                    f"{container_registry.TYPE.value} to a remote one."
                )

            # Validate that the rest of the components are not local.
            for stack_comp in stack.components.values():
                local_path = stack_comp.local_path
                if not local_path:
                    continue
                return False, (
                    f"The '{stack_comp.name}' {stack_comp.TYPE.value} is a "
                    f"local stack component. The Vertex AI Pipelines "
                    f"orchestrator requires that all the components in the "
                    f"stack used to execute the pipeline have to be not local, "
                    f"because there is no way for Vertex to connect to your "
                    f"local machine. You should use a flavor of "
                    f"{stack_comp.TYPE.value} other than '"
                    f"{stack_comp.FLAVOR}'."
                )

            # If the `pipeline_root` has not been defined in the orchestrator
            # configuration, and the artifact store is not a GCP artifact store,
            # then raise an error.
            if (
                not self.pipeline_root
                and stack.artifact_store.FLAVOR != GCP_ARTIFACT_STORE_FLAVOR
            ):
                return False, (
                    f"The attribute `pipeline_root` has not been set and it "
                    f"cannot be generated using the path of the artifact store "
                    f"because it is not a "
                    f"`zenml.integrations.gcp.artifact_store.GCPArtifactStore`."
                    f" To solve this issue, set the `pipeline_root` attribute "
                    f"manually executing the following command: "
                    f"`zenml orchestrator update {stack.orchestrator.name} "
                    f'--pipeline_root="<Cloud Storage URI>"`.'
                )

            return True, ""

        return StackValidator(
            required_components={StackComponentType.CONTAINER_REGISTRY},
            custom_validation_function=_validate_stack_requirements,
        )

    def get_docker_image_name(self, pipeline_name: str) -> str:
        """Returns the full docker image name including registry and tag.

        Args:
            pipeline_name: The name of the pipeline.

        Returns:
            The full docker image name including registry and tag.
        """
        base_image_name = f"zenml-vertex:{pipeline_name}"
        container_registry = Repository().active_stack.container_registry

        if container_registry:
            registry_uri = container_registry.uri.rstrip("/")
            return f"{registry_uri}/{base_image_name}"

        return base_image_name

    @property
    def root_directory(self) -> str:
        """Returns path to the root directory for files for this orchestrator.

        Returns:
            The path to the root directory for all files concerning this
            orchestrator.
        """
        return os.path.join(
            get_global_config_directory(), "vertex", str(self.uuid)
        )

    @property
    def pipeline_directory(self) -> str:
        """Returns path to directory where kubeflow pipelines files are stored.

        Returns:
            Path to the pipeline directory.
        """
        return os.path.join(self.root_directory, "pipelines")

    def prepare_pipeline_deployment(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> None:
        """Build a Docker image for the current environment.

        This uploads it to a container registry if configured.

        Args:
            pipeline: The pipeline to be deployed.
            stack: The stack that will be used to deploy the pipeline.
            runtime_configuration: The runtime configuration for the pipeline.

        Raises:
            RuntimeError: If the container registry is missing.
        """
        from zenml.utils import docker_utils

        repo = Repository()
        container_registry = repo.active_stack.container_registry

        if not container_registry:
            raise RuntimeError("Missing container registry")

        image_name = self.get_docker_image_name(pipeline.name)

        requirements = {*stack.requirements(), *pipeline.requirements}

        logger.debug(
            "Vertex AI Pipelines service docker container requirements %s",
            requirements,
        )

        docker_utils.build_docker_image(
            build_context_path=get_source_root_path(),
            image_name=image_name,
            dockerignore_path=pipeline.dockerignore_file,
            requirements=requirements,
            base_image=self.custom_docker_base_image_name,
        )
        container_registry.push_image(image_name)

    def _configure_container_resources(
        self,
        container_op: dsl.ContainerOp,
        resource_configuration: "ResourceConfiguration",
    ) -> None:
        """Adds resource requirements to the container.

        Args:
            container_op: The kubeflow container operation to configure.
            resource_configuration: The resource configuration to use for this
                container.
        """
        # Set optional CPU, RAM and GPU constraints for the pipeline
        cpu_limit = resource_configuration.cpu_count or self.cpu_limit
        if cpu_limit is not None:
            container_op = container_op.set_cpu_limit(str(cpu_limit))

        memory_limit = (
            resource_configuration.memory[:-1]
            if resource_configuration.memory
            else self.memory_limit
        )
        if memory_limit is not None:
            container_op = container_op.set_memory_limit(memory_limit)

        if self.node_selector_constraint is not None:
            container_op = container_op.add_node_selector_constraint(
                label_name=self.node_selector_constraint[0],
                value=self.node_selector_constraint[1],
            )

        gpu_limit = resource_configuration.gpu_count or self.gpu_limit
        if gpu_limit is not None:
            container_op = container_op.set_gpu_limit(gpu_limit)

    def prepare_or_run_pipeline(
        self,
        sorted_steps: List["BaseStep"],
        pipeline: "BasePipeline",
        pb2_pipeline: "Pb2Pipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        """Creates a KFP JSON pipeline.

        # noqa: DAR402

        This is an intermediary representation of the pipeline which is then
        deployed to Vertex AI Pipelines service.

        How it works:
        -------------
        Before this method is called the `prepare_pipeline_deployment()` method
        builds a Docker image that contains the code for the pipeline, all steps
        the context around these files.

        Based on this Docker image a callable is created which builds
        container_ops for each step (`_construct_kfp_pipeline`). The function
        `kfp.components.load_component_from_text` is used to create the
        `ContainerOp`, because using the `dsl.ContainerOp` class directly is
        deprecated when using the Kubeflow SDK v2. The step entrypoint command
        with the entrypoint arguments is the command that will be executed by
        the container created using the previously created Docker image.

        This callable is then compiled into a JSON file that is used as the
        intermediary representation of the Kubeflow pipeline.

        This file then is submitted to the Vertex AI Pipelines service for
        execution.

        Args:
            sorted_steps: List of sorted steps.
            pipeline: Zenml Pipeline instance.
            pb2_pipeline: Protobuf Pipeline instance.
            stack: The stack the pipeline was run on.
            runtime_configuration: The Runtime configuration of the current run.

        Raises:
            ValueError: If the attribute `pipeline_root` is not set and it
                can be not generated using the path of the artifact store in the
                stack because it is not a
                `zenml.integrations.gcp.artifact_store.GCPArtifactStore`.
        """
        # If the `pipeline_root` has not been defined in the orchestrator
        # configuration,
        # try to create it from the artifact store if it is a
        # `GCPArtifactStore`.
        if not self.pipeline_root:
            artifact_store = stack.artifact_store
            self._pipeline_root = f"{artifact_store.path.rstrip('/')}/vertex_pipeline_root/{pipeline.name}/{runtime_configuration.run_name}"
            logger.info(
                "The attribute `pipeline_root` has not been set in the "
                "orchestrator configuration. One has been generated "
                "automatically based on the path of the `GCPArtifactStore` "
                "artifact store in the stack used to execute the pipeline. "
                "The generated `pipeline_root` is `%s`.",
                self._pipeline_root,
            )
        else:
            self._pipeline_root = self.pipeline_root

        # Build the Docker image that will be used to run the steps of the
        # pipeline.
        image_name = self.get_docker_image_name(pipeline.name)
        image_name = get_image_digest(image_name) or image_name

        def _construct_kfp_pipeline() -> None:
            """Create a `ContainerOp` for each step.

            This should contain the name of the Docker image and configures the
            entrypoint of the Docker image to run the step.

            Additionally, this gives each `ContainerOp` information about its
            direct downstream steps.

            If this callable is passed to the `compile()` method of
            `KFPV2Compiler` all `dsl.ContainerOp` instances will be
            automatically added to a singular `dsl.Pipeline` instance.
            """
            step_name_to_container_op: Dict[str, dsl.ContainerOp] = {}

            for step in sorted_steps:
                # The command will be needed to eventually call the python step
                # within the docker container
                command = VertexEntrypointConfiguration.get_entrypoint_command()

                # The arguments are passed to configure the entrypoint of the
                # docker container when the step is called.
                arguments = VertexEntrypointConfiguration.get_entrypoint_arguments(
                    step=step,
                    pb2_pipeline=pb2_pipeline,
                    **{VERTEX_JOB_ID_OPTION: dslv2.PIPELINE_JOB_ID_PLACEHOLDER},
                )

                # Create the `ContainerOp` for the step. Using the
                # `dsl.ContainerOp`
                # class directly is deprecated when using the Kubeflow SDK v2.
                container_op = kfp.components.load_component_from_text(
                    f"""
                    name: {step.name}
                    implementation:
                        container:
                            image: {image_name}
                            command: {command + arguments}"""
                )()

                # Set upstream tasks as a dependency of the current step
                upstream_step_names = self.get_upstream_step_names(
                    step=step, pb2_pipeline=pb2_pipeline
                )
                for upstream_step_name in upstream_step_names:
                    upstream_container_op = step_name_to_container_op[
                        upstream_step_name
                    ]
                    container_op.after(upstream_container_op)

                self._configure_container_resources(
                    container_op=container_op,
                    resource_configuration=step.resource_configuration,
                )

                step_name_to_container_op[step.name] = container_op

        # Save the generated pipeline to a file.
        assert runtime_configuration.run_name
        fileio.makedirs(self.pipeline_directory)
        pipeline_file_path = os.path.join(
            self.pipeline_directory,
            f"{runtime_configuration.run_name}.json",
        )

        # Compile the pipeline using the Kubeflow SDK V2 compiler that allows
        # to generate a JSON representation of the pipeline that can be later
        # upload to Vertex AI Pipelines service.
        logger.debug(
            "Compiling pipeline using Kubeflow SDK V2 compiler and saving it "
            "to `%s`",
            pipeline_file_path,
        )
        KFPV2Compiler().compile(
            pipeline_func=_construct_kfp_pipeline,
            package_path=pipeline_file_path,
            pipeline_name=_clean_pipeline_name(pipeline.name),
        )

        # Using the Google Cloud AIPlatform client, upload and execute the
        # pipeline
        # on the Vertex AI Pipelines service.
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
        """Uploads and run the pipeline on the Vertex AI Pipelines service.

        Args:
            pipeline_name: Name of the pipeline.
            pipeline_file_path: Path of the JSON file containing the compiled
                Kubeflow pipeline (compiled with Kubeflow SDK v2).
            runtime_configuration: Runtime configuration of the pipeline run.
            enable_cache: Whether caching is enabled for this pipeline run.
        """
        # We have to replace the hyphens in the pipeline name with underscores
        # and lower case the string, because the Vertex AI Pipelines service
        # requires this format.
        assert runtime_configuration.run_name
        job_id = _clean_pipeline_name(runtime_configuration.run_name)

        # Warn the user that the scheduling is not available using the Vertex
        # Orchestrator
        if runtime_configuration.schedule:
            logger.warning(
                "Pipeline scheduling configuration was provided, but Vertex "
                "AI Pipelines "
                "do not have capabilities for scheduling yet."
            )

        # Get the credentials that would be used to create the Vertex AI
        # Pipelines
        # job.
        credentials, project_id = self._get_authentication()
        if self.project and self.project != project_id:
            logger.warning(
                "Authenticated with project `%s`, but this orchestrator is "
                "configured to use the project `%s`.",
                project_id,
                self.project,
            )

        # If the project was set in the configuration, use it. Otherwise, use
        # the project that was used to authenticate.
        project_id = self.project if self.project else project_id

        # Instantiate the Vertex AI Pipelines job
        run = aiplatform.PipelineJob(
            display_name=pipeline_name,
            template_path=pipeline_file_path,
            job_id=job_id,
            pipeline_root=self._pipeline_root,
            parameter_values=None,
            enable_caching=enable_cache,
            encryption_spec_key_name=self.encryption_spec_key_name,
            labels=self.labels,
            credentials=credentials,
            project=self.project,
            location=self.location,
        )

        logger.info(
            "Submitting pipeline job with job_id `%s` to Vertex AI Pipelines "
            "service.",
            job_id,
        )

        # Submit the job to Vertex AI Pipelines service.
        try:
            if self.workload_service_account:
                logger.info(
                    "The Vertex AI Pipelines job workload will be executed "
                    "using `%s` "
                    "service account.",
                    self.workload_service_account,
                )

            if self.network:
                logger.info(
                    "The Vertex AI Pipelines job will be peered with `%s` "
                    "network.",
                    self.network,
                )

            run.submit(
                service_account=self.workload_service_account,
                network=self.network,
            )
            logger.info(
                "View the Vertex AI Pipelines job at %s", run._dashboard_uri()
            )

            if self.synchronous:
                logger.info(
                    "Waiting for the Vertex AI Pipelines job to finish..."
                )
                run.wait()

        except google_exceptions.ClientError as e:
            logger.warning(
                "Failed to create the Vertex AI Pipelines job: %s", e
            )

        except RuntimeError as e:
            logger.error(
                "The Vertex AI Pipelines job execution has failed: %s", e
            )
