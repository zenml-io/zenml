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

import os
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Tuple

import kfp
from google.api_core import exceptions as google_exceptions
from google.cloud import aiplatform
from kfp import dsl
from kfp.v2 import dsl as dslv2
from kfp.v2.compiler import Compiler as KFPV2Compiler

from zenml.enums import StackComponentType
from zenml.integrations.vertex import VERTEX_ORCHESTRATOR_FLAVOR
from zenml.integrations.vertex.orchestrators.vertex_entrypoint_configuration import (
    VERTEX_JOB_ID_OPTION,
    VertexEntrypointConfiguration,
)
from zenml.io import fileio
from zenml.io.utils import get_global_config_directory
from zenml.logger import get_logger
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.repository import Repository
from zenml.stack.stack_validator import StackValidator
from zenml.utils.docker_utils import get_image_digest
from zenml.utils.source_utils import get_source_root_path

if TYPE_CHECKING:
    from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline

    from zenml.pipelines.base_pipeline import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.stack import Stack
    from zenml.steps import BaseStep


logger = get_logger(__name__)


def _clean_pipeline_name(pipeline_name: str) -> str:
    """Clean pipeline name to be a valid Vertex AI Pipeline name.

    Arguments:
        pipeline_name: pipeline name to be cleaned.

    Returns:
        Cleaned pipeline name.
    """
    return pipeline_name.replace("_", "-").lower()


class VertexOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines on Vertex AI.

    Attributes:
        custom_docker_base_image_name: Name of the Docker image that should be
            used as the base for the image that will be used to execute each of
            the steps. If no custom base image is given, a basic image of the active
            ZenML version will be used. **Note**: This image needs to have ZenML
            installed, otherwise the pipeline execution will fail. For that reason,
            might want to extend the ZenML Docker images found here:
            https://hub.docker.com/r/zenmldocker/zenml/
        project: GCP project name. If `None`, the project will be inferred from
            the environment.
        location: Name of GCP region where the pipeline job will be executed.
            Vertex AI Pipelines is available in the following regions:
            https://cloud.google.com/vertex-ai/docs/general/locations#feature-availability
        pipeline_root: a Google Cloud Storage path that will be used by the Vertex
            AI Pipelines.
        encryption_spec_key_name: The Cloud KMS resource identifier of the customer
            managed encryption key used to protect the job. Has the form:
            `projects/my-project/locations/my-region/keyRings/my-kr/cryptoKeys/my-key`.
            The key needs to be in the same region as where the compute resource
            is created.
        synchronous: If `True`, running a pipeline using this orchestrator will
            block until all steps finished running on Vertex AI Pipelines service.
    """

    custom_docker_base_image_name: Optional[str] = None
    project: Optional[str] = None
    location: str
    pipeline_root: str
    labels: Dict[str, str] = {}
    encryption_spec_key_name: Optional[str] = None
    synchronous: bool = False

    FLAVOR: ClassVar[str] = VERTEX_ORCHESTRATOR_FLAVOR

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack contains a container registry and that the
        artifact store and metadata store used are not local."""

        def _validate_stack_requirements(stack: "Stack") -> Tuple[bool, str]:
            """Validates that all the stack components are not local."""

            # Validate that the container registry is not local.
            container_registry = stack.container_registry
            if container_registry.is_local:
                return False, (
                    f"The Vertex orchestrator does not support local container registries. "
                    f"You should replace the component '{container_registry.name}' "
                    f"{container_registry.TYPE.value} to a remote one."
                )

            # Validate that the rest of the components are not local.
            for stack_comp in stack.components.values():
                local_path = stack_comp.local_path
                if not local_path:
                    continue
                return False, (
                    f"The '{stack_comp.name}' {stack_comp.TYPE.value} is a local "
                    f"stack component. The Vertex AI Pipelines orchestrator requires "
                    f"that all the components in the stack used to execute the "
                    f"pipeline have to be not local, because there is no way for "
                    f"Vertex to connect to your local machine. You should use a "
                    f"flavor of {stack_comp.TYPE.value} other than '{stack_comp.FLAVOR}'."
                )
            return True, ""

        return StackValidator(
            required_components={StackComponentType.CONTAINER_REGISTRY},
            custom_validation_function=_validate_stack_requirements,
        )

    def get_docker_image_name(self, pipeline_name: str) -> str:
        """Returns the full docker image name including registry and tag."""

        base_image_name = f"zenml-vertex:{pipeline_name}"
        container_registry = Repository().active_stack.container_registry

        if container_registry:
            registry_uri = container_registry.uri.rstrip("/")
            return f"{registry_uri}/{base_image_name}"

        return base_image_name

    @property
    def root_directory(self) -> str:
        """Returns path to the root directory for all files concerning this orchestrator."""
        return os.path.join(
            get_global_config_directory(), "vertex", str(self.uuid)
        )

    @property
    def pipeline_directory(self) -> str:
        """Returns path to a directory in which the kubeflow pipelines files are
        stored."""
        return os.path.join(self.root_directory, "pipelines")

    def prepare_pipeline_deployment(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> None:
        """Build a Docker image for the current environment and uploads it to a
        container registry if configured."""
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

    def prepare_or_run_pipeline(
        self,
        sorted_steps: List["BaseStep"],
        pipeline: "BasePipeline",
        pb2_pipeline: "Pb2Pipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        """Creates a KFP JSON pipeline as intermediary representation of the pipeline
        which is then deployed to Vertex AI Pipelines service.

        How it works:
        -------------
        Before this method is called the `prepare_pipeline_deployment()` method
        builds a Docker image that contains the code for the pipeline, all steps
        the context around these files.

        Based on this Docker image a callable is created which builds container_ops
        for each step (`_construct_kfp_pipeline`). The function `kfp.components.load_component_from_text`
        is used to create the `ContainerOp`, because using the `dsl.ContainerOp`
        class directly is deprecated when using the Kubeflow SDK v2. The step
        entrypoint command with the entrypoint arguments is the command that will
        be executed by the container created using the previously created Docker
        image.

        This callable is then compiled into a JSON file that is used as the intermediary
        representation of the Kubeflow pipeline.

        This file then is submitted to the Vertex AI Pipelines service for execution.
        """

        image_name = self.get_docker_image_name(pipeline.name)
        image_name = get_image_digest(image_name) or image_name

        def _construct_kfp_pipeline() -> None:
            """Create a `ContainerOp` for each step which contains the name
            of the Docker image and configures the entrypoint of the Docker
            image to run the step.

            Additionally, this gives each `ContainerOp` information about its
            direct downstream steps.

            If this callable is passed to the `compile()` method of `KFPV2Compiler`
            all `dsl.ContainerOp` instances will be automatically added to a singular
            `dsl.Pipeline` instance.
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

                # Create the `ContainerOp` for the step. Using the `dsl.ContainerOp`
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
            "Compiling pipeline using Kubeflow SDK V2 compiler and saving it to %s",
            pipeline_file_path,
        )
        KFPV2Compiler().compile(
            pipeline_func=_construct_kfp_pipeline,
            package_path=pipeline_file_path,
            pipeline_name=_clean_pipeline_name(pipeline.name),
        )

        # Using the Google Cloud AIPlatform client, upload and execute the pipeline
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

        # Warn the user that the scheduling is not available using the Vertex Orchestrator
        if runtime_configuration.schedule:
            logger.warning(
                "Pipeline scheduling configuration was provided, but Vertex AI Pipelines "
                "do not have capabilities for scheduling yet."
            )

        # Instantiate the Vertex AI Pipelines job
        run = aiplatform.PipelineJob(
            display_name=pipeline_name,
            template_path=pipeline_file_path,
            job_id=job_id,
            pipeline_root=self.pipeline_root,
            parameter_values=None,
            enable_caching=enable_cache,
            encryption_spec_key_name=self.encryption_spec_key_name,
            labels=self.labels,
            credentials=None,
            project=self.project,
            location=self.location,
        )

        logger.info(
            "Submitting pipeline job with job_id `%s` to Vertex AI Pipelines service.",
            job_id,
        )

        # Submit the job to Vertex AI Pipelines service.
        try:
            run.submit()
            logger.info(
                "View the Vertex AI Pipelines job at %s", run._dashboard_uri()
            )

            if self.synchronous:
                logger.info(
                    "Waiting for the Vertex AI Pipelines job to finish..."
                )
                run.wait()

        except google_exceptions.ClientError as e:
            logger.warning("Failed to create the Vertex AI Pipeline job: %s", e)
