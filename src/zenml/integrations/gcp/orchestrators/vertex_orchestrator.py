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
import re
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Type, cast
from uuid import UUID

import kfp
from google.api_core import exceptions as google_exceptions
from google.cloud import aiplatform
from kfp import dsl
from kfp.v2 import dsl as dslv2
from kfp.v2.compiler import Compiler as KFPV2Compiler

from zenml.constants import (
    METADATA_ORCHESTRATOR_URL,
)
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.enums import StackComponentType
from zenml.integrations.gcp import GCP_ARTIFACT_STORE_FLAVOR
from zenml.integrations.gcp.constants import (
    GKE_ACCELERATOR_NODE_SELECTOR_CONSTRAINT_LABEL,
)
from zenml.integrations.gcp.flavors.vertex_orchestrator_flavor import (
    VertexOrchestratorConfig,
    VertexOrchestratorSettings,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsMixin,
)
from zenml.integrations.kubeflow.utils import apply_pod_settings
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType, Uri
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.stack.stack_validator import StackValidator
from zenml.utils.io_utils import get_global_config_directory

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.models import PipelineDeploymentResponse, ScheduleResponse
    from zenml.stack import Stack
    from zenml.steps import ResourceSettings

logger = get_logger(__name__)
ENV_ZENML_VERTEX_RUN_ID = "ZENML_VERTEX_RUN_ID"


def _clean_pipeline_name(pipeline_name: str) -> str:
    """Clean pipeline name to be a valid Vertex AI Pipeline name.

    Arguments:
        pipeline_name: pipeline name to be cleaned.

    Returns:
        Cleaned pipeline name.
    """
    pipeline_name = pipeline_name.lower()

    # This pattern matches anything that is not a lowercase letter,
    #  a number, or a dash
    pattern = r"[^a-z0-9-]"

    # Replace any characters matching the pattern with a dash
    return re.sub(pattern, "-", pipeline_name)


class VertexOrchestrator(ContainerizedOrchestrator, GoogleCredentialsMixin):
    """Orchestrator responsible for running pipelines on Vertex AI."""

    _pipeline_root: str

    @property
    def config(self) -> VertexOrchestratorConfig:
        """Returns the `VertexOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(VertexOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Vertex orchestrator.

        Returns:
            The settings class.
        """
        return VertexOrchestratorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack contains a container registry.

        Also validates that the artifact store is not local.

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
            if container_registry and container_registry.config.is_local:
                return False, (
                    f"The Vertex orchestrator does not support local "
                    f"container registries. You should replace the component '"
                    f"{container_registry.name}' "
                    f"{container_registry.type.value} to a remote one."
                )

            # Validate that the rest of the components are not local.
            for stack_comp in stack.components.values():
                # For Forward compatibility a list of components is returned,
                # but only the first item is relevant for now
                # TODO: [server] make sure the ComponentModel actually has
                #  a local_path property or implement similar check
                local_path = stack_comp.local_path
                if not local_path:
                    continue
                return False, (
                    f"The '{stack_comp.name}' {stack_comp.type.value} is a "
                    f"local stack component. The Vertex AI Pipelines "
                    f"orchestrator requires that all the components in the "
                    f"stack used to execute the pipeline have to be not local, "
                    f"because there is no way for Vertex to connect to your "
                    f"local machine. You should use a flavor of "
                    f"{stack_comp.type.value} other than '"
                    f"{stack_comp.flavor}'."
                )

            # If the `pipeline_root` has not been defined in the orchestrator
            # configuration, and the artifact store is not a GCP artifact store,
            # then raise an error.
            if (
                not self.config.pipeline_root
                and stack.artifact_store.flavor != GCP_ARTIFACT_STORE_FLAVOR
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
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_stack_requirements,
        )

    @property
    def root_directory(self) -> str:
        """Returns path to the root directory for files for this orchestrator.

        Returns:
            The path to the root directory for all files concerning this
            orchestrator.
        """
        return os.path.join(
            get_global_config_directory(), "vertex", str(self.id)
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
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
    ) -> None:
        """Build a Docker image and push it to the container registry.

        Args:
            deployment: The pipeline deployment configuration.
            stack: The stack on which the pipeline will be deployed.

        Raises:
            ValueError: If `cron_expression` is not in passed Schedule.
        """
        if deployment.schedule:
            if (
                deployment.schedule.catchup
                or deployment.schedule.interval_second
            ):
                logger.warning(
                    "Vertex orchestrator only uses schedules with the "
                    "`cron_expression` property, with optional `start_time` and/or `end_time`. "
                    "All other properties are ignored."
                )
            if deployment.schedule.cron_expression is None:
                raise ValueError(
                    "Property `cron_expression` must be set when passing "
                    "schedule to a Vertex orchestrator."
                )

    def _configure_container_resources(
        self,
        container_op: dsl.ContainerOp,
        resource_settings: "ResourceSettings",
        node_selector_constraint: Optional[Tuple[str, str]] = None,
    ) -> None:
        """Adds resource requirements to the container.

        Args:
            container_op: The kubeflow container operation to configure.
            resource_settings: The resource settings to use for this
                container.
            node_selector_constraint: Node selector constraint to apply to
                the container.
        """
        # Set optional CPU, RAM and GPU constraints for the pipeline

        cpu_limit = resource_settings.cpu_count or self.config.cpu_limit

        if cpu_limit is not None:
            container_op = container_op.set_cpu_limit(str(cpu_limit))

        memory_limit = (
            resource_settings.memory[:-1]
            if resource_settings.memory
            else self.config.memory_limit
        )
        if memory_limit is not None:
            container_op = container_op.set_memory_limit(memory_limit)

        gpu_limit = (
            resource_settings.gpu_count
            if resource_settings.gpu_count is not None
            else self.config.gpu_limit
        )
        if gpu_limit is not None and gpu_limit > 0:
            container_op = container_op.set_gpu_limit(gpu_limit)

        if node_selector_constraint:
            constraint_label, value = node_selector_constraint
            if not (
                constraint_label
                == GKE_ACCELERATOR_NODE_SELECTOR_CONSTRAINT_LABEL
                and gpu_limit == 0
            ):
                container_op.add_node_selector_constraint(
                    constraint_label, value
                )

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
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
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.

        Raises:
            ValueError: If the attribute `pipeline_root` is not set and it
                can be not generated using the path of the artifact store in the
                stack because it is not a
                `zenml.integrations.gcp.artifact_store.GCPArtifactStore`. Also gets
                raised if attempting to schedule pipeline run without using the
                `zenml.integrations.gcp.artifact_store.GCPArtifactStore`.
        """
        orchestrator_run_name = get_orchestrator_run_name(
            pipeline_name=deployment.pipeline_configuration.name
        )
        # If the `pipeline_root` has not been defined in the orchestrator
        # configuration,
        # try to create it from the artifact store if it is a
        # `GCPArtifactStore`.
        if not self.config.pipeline_root:
            artifact_store = stack.artifact_store
            self._pipeline_root = f"{artifact_store.path.rstrip('/')}/vertex_pipeline_root/{deployment.pipeline_configuration.name}/{orchestrator_run_name}"
            logger.info(
                "The attribute `pipeline_root` has not been set in the "
                "orchestrator configuration. One has been generated "
                "automatically based on the path of the `GCPArtifactStore` "
                "artifact store in the stack used to execute the pipeline. "
                "The generated `pipeline_root` is `%s`.",
                self._pipeline_root,
            )
        else:
            self._pipeline_root = self.config.pipeline_root

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
            command = StepEntrypointConfiguration.get_entrypoint_command()
            step_name_to_container_op: Dict[str, dsl.ContainerOp] = {}

            for step_name, step in deployment.step_configurations.items():
                image = self.get_image(
                    deployment=deployment, step_name=step_name
                )
                arguments = (
                    StepEntrypointConfiguration.get_entrypoint_arguments(
                        step_name=step_name, deployment_id=deployment.id
                    )
                )

                # Create the `ContainerOp` for the step. Using the
                # `dsl.ContainerOp`
                # class directly is deprecated when using the Kubeflow SDK v2.
                container_op = kfp.components.load_component_from_text(
                    f"""
                    name: {step_name}
                    implementation:
                        container:
                            image: {image}
                            command: {command + arguments}"""
                )()

                container_op.set_env_variable(
                    name=ENV_ZENML_VERTEX_RUN_ID,
                    value=dslv2.PIPELINE_JOB_NAME_PLACEHOLDER,
                )

                for key, value in environment.items():
                    container_op.set_env_variable(name=key, value=value)

                # Set upstream tasks as a dependency of the current step
                for upstream_step_name in step.spec.upstream_steps:
                    upstream_container_op = step_name_to_container_op[
                        upstream_step_name
                    ]
                    container_op.after(upstream_container_op)

                settings = cast(
                    VertexOrchestratorSettings,
                    self.get_settings(step),
                )
                if settings.pod_settings:
                    apply_pod_settings(
                        container_op=container_op,
                        settings=settings.pod_settings,
                    )

                self._configure_container_resources(
                    container_op=container_op,
                    resource_settings=step.config.resource_settings,
                    node_selector_constraint=settings.node_selector_constraint,
                )
                container_op.set_caching_options(enable_caching=False)

                step_name_to_container_op[step_name] = container_op

        # Save the generated pipeline to a file.
        fileio.makedirs(self.pipeline_directory)
        pipeline_file_path = os.path.join(
            self.pipeline_directory,
            f"{orchestrator_run_name}.json",
        )

        # Compile the pipeline using the Kubeflow SDK V2 compiler that allows
        # to generate a JSON representation of the pipeline that can be later
        # upload to Vertex AI Pipelines service.
        KFPV2Compiler().compile(
            pipeline_func=_construct_kfp_pipeline,
            package_path=pipeline_file_path,
            pipeline_name=_clean_pipeline_name(
                deployment.pipeline_configuration.name
            ),
        )
        logger.info(
            "Writing Vertex workflow definition to `%s`.", pipeline_file_path
        )

        settings = cast(
            VertexOrchestratorSettings, self.get_settings(deployment)
        )

        # Using the Google Cloud AIPlatform client, upload and execute the
        # pipeline
        # on the Vertex AI Pipelines service.
        self._upload_and_run_pipeline(
            pipeline_name=deployment.pipeline_configuration.name,
            pipeline_file_path=pipeline_file_path,
            run_name=orchestrator_run_name,
            settings=settings,
            schedule=deployment.schedule,
        )

    def _upload_and_run_pipeline(
        self,
        pipeline_name: str,
        pipeline_file_path: str,
        run_name: str,
        settings: VertexOrchestratorSettings,
        schedule: Optional["ScheduleResponse"] = None,
    ) -> None:
        """Uploads and run the pipeline on the Vertex AI Pipelines service.

        Args:
            pipeline_name: Name of the pipeline.
            pipeline_file_path: Path of the JSON file containing the compiled
                Kubeflow pipeline (compiled with Kubeflow SDK v2).
            run_name: Orchestrator run name.
            settings: Pipeline level settings for this orchestrator.
            schedule: The schedule the pipeline will run on.
        """
        # We have to replace the hyphens in the run name with underscores
        # and lower case the string, because the Vertex AI Pipelines service
        # requires this format.
        job_id = _clean_pipeline_name(run_name)

        # Get the credentials that would be used to create the Vertex AI
        # Pipelines
        # job.
        credentials, project_id = self._get_authentication()

        # Instantiate the Vertex AI Pipelines job
        run = aiplatform.PipelineJob(
            display_name=pipeline_name,
            template_path=pipeline_file_path,
            job_id=job_id,
            pipeline_root=self._pipeline_root,
            parameter_values=None,
            enable_caching=False,
            encryption_spec_key_name=self.config.encryption_spec_key_name,
            labels=settings.labels,
            credentials=credentials,
            project=project_id,
            location=self.config.location,
        )

        if self.config.workload_service_account:
            logger.info(
                "The Vertex AI Pipelines job workload will be executed "
                "using the `%s` "
                "service account.",
                self.config.workload_service_account,
            )
        if self.config.network:
            logger.info(
                "The Vertex AI Pipelines job will be peered with the `%s` "
                "network.",
                self.config.network,
            )

        try:
            if schedule:
                logger.info(
                    "Scheduling job using native Vertex AI Pipelines scheduling..."
                )
                run.create_schedule(
                    display_name=schedule.name,
                    cron=schedule.cron_expression,
                    start_time=schedule.utc_start_time,
                    end_time=schedule.utc_end_time,
                    service_account=self.config.workload_service_account,
                    network=self.config.network,
                )

            else:
                logger.info(
                    "No schedule detected. Creating one-off Vertex job..."
                )
                logger.info(
                    "Submitting pipeline job with job_id `%s` to Vertex AI Pipelines "
                    "service.",
                    job_id,
                )

                # Submit the job to Vertex AI Pipelines service.

                run.submit(
                    service_account=self.config.workload_service_account,
                    network=self.config.network,
                )
                logger.info(
                    "View the Vertex AI Pipelines job at %s",
                    run._dashboard_uri(),
                )

                if settings.synchronous:
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

    def get_orchestrator_run_id(self) -> str:
        """Returns the active orchestrator run id.

        Raises:
            RuntimeError: If the environment variable specifying the run id
                is not set.

        Returns:
            The orchestrator run id.
        """
        try:
            return os.environ[ENV_ZENML_VERTEX_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_VERTEX_RUN_ID}."
            )

    def get_pipeline_run_metadata(
        self, run_id: UUID
    ) -> Dict[str, "MetadataType"]:
        """Get general component-specific metadata for a pipeline run.

        Args:
            run_id: The ID of the pipeline run.

        Returns:
            A dictionary of metadata.
        """
        run_url = (
            f"https://console.cloud.google.com/vertex-ai/locations/"
            f"{self.config.location}/pipelines/runs/"
            f"{self.get_orchestrator_run_id()}"
        )
        if self.config.project:
            run_url += f"?project={self.config.project}"
        return {
            METADATA_ORCHESTRATOR_URL: Uri(run_url),
        }
