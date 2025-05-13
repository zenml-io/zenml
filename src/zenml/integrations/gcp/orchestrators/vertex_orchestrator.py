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
import types
import urllib
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    cast,
)
from uuid import UUID

from google.api_core import exceptions as google_exceptions
from google.cloud import aiplatform
from google.cloud.aiplatform.compat.services import (
    pipeline_service_client_v1beta1,
)
from google.cloud.aiplatform.compat.types import pipeline_job_v1beta1
from google.cloud.aiplatform_v1.types import PipelineState
from google.cloud.aiplatform_v1beta1.types.service_networking import (
    PscInterfaceConfig,
)
from google.protobuf import json_format
from google_cloud_pipeline_components.v1.custom_job.utils import (
    create_custom_training_job_from_component,
)
from kfp import dsl
from kfp.compiler import Compiler
from kfp.dsl.base_component import BaseComponent

from zenml.config.resource_settings import ResourceSettings
from zenml.constants import (
    METADATA_ORCHESTRATOR_LOGS_URL,
    METADATA_ORCHESTRATOR_RUN_ID,
    METADATA_ORCHESTRATOR_URL,
)
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.enums import ExecutionStatus, StackComponentType
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
from zenml.integrations.gcp.vertex_custom_job_parameters import (
    VertexCustomJobParameters,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType, Uri
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.stack.stack_validator import StackValidator
from zenml.utils.io_utils import get_global_config_directory

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.models import (
        PipelineDeploymentResponse,
        PipelineRunResponse,
        ScheduleResponse,
    )
    from zenml.stack import Stack

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
                    "`cron_expression` property, with optional `start_time` "
                    "and/or `end_time`. All other properties are ignored."
                )
            if deployment.schedule.cron_expression is None:
                raise ValueError(
                    "Property `cron_expression` must be set when passing "
                    "schedule to a Vertex orchestrator."
                )

    def _create_container_component(
        self,
        image: str,
        command: List[str],
        arguments: List[str],
        component_name: str,
    ) -> BaseComponent:
        """Creates a container component for a Vertex pipeline.

        Args:
            image: The image to use for the component.
            command: The command to use for the component.
            arguments: The arguments to use for the component.
            component_name: The name of the component.

        Returns:
            The container component.
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

        new_container_spec_func = types.FunctionType(
            dynamic_container_component.__code__,
            dynamic_container_component.__globals__,
            name=component_name,
            argdefs=dynamic_container_component.__defaults__,
            closure=dynamic_container_component.__closure__,
        )
        pipeline_task = dsl.container_component(new_container_spec_func)
        return pipeline_task

    def _convert_to_custom_training_job(
        self,
        component: BaseComponent,
        settings: VertexOrchestratorSettings,
        environment: Dict[str, str],
    ) -> BaseComponent:
        """Convert a component to a custom training job component.

        Args:
            component: The component to convert.
            settings: The settings for the custom training job.
            environment: The environment variables to set in the custom
                training job.

        Returns:
            The custom training job component.
        """
        custom_job_parameters = (
            settings.custom_job_parameters or VertexCustomJobParameters()
        )
        if (
            custom_job_parameters.persistent_resource_id
            and not custom_job_parameters.service_account
        ):
            # Persistent resources require an explicit service account, but
            # none was provided in the custom job parameters. We try to fall
            # back to the workload service account.
            custom_job_parameters.service_account = (
                self.config.workload_service_account
            )

        # Create a dictionary of explicit parameters
        params = custom_job_parameters.model_dump(
            exclude_none=True, exclude={"additional_training_job_args"}
        )

        # Remove None values to let defaults be set by the function
        params = {k: v for k, v in params.items() if v is not None}

        # Add environment variables
        params["env"] = [
            {"name": key, "value": value} for key, value in environment.items()
        ]

        # Check if any advanced parameters will override explicit parameters
        if custom_job_parameters.additional_training_job_args:
            overridden_params = set(params.keys()) & set(
                custom_job_parameters.additional_training_job_args.keys()
            )
            if overridden_params:
                logger.warning(
                    f"The following explicit parameters are being overridden by values in "
                    f"additional_training_job_args: {', '.join(overridden_params)}. "
                    f"This may lead to unexpected behavior. Consider using either explicit "
                    f"parameters or additional_training_job_args, but not both for the same parameters."
                )

        # Add any advanced parameters - these will override explicit parameters if provided
        params.update(custom_job_parameters.additional_training_job_args)

        # Add other parameters from orchestrator config if not already in params
        if self.config.network and "network" not in params:
            params["network"] = self.config.network

        if (
            self.config.encryption_spec_key_name
            and "encryption_spec_key_name" not in params
        ):
            params["encryption_spec_key_name"] = (
                self.config.encryption_spec_key_name
            )
        if (
            self.config.workload_service_account
            and "service_account" not in params
        ):
            params["service_account"] = self.config.workload_service_account

        custom_job_component = create_custom_training_job_from_component(
            component_spec=component,
            **params,
        )

        return custom_job_component

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Iterator[Dict[str, MetadataType]]:
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
            placeholder_run: An optional placeholder run for the deployment.

        Raises:
            ValueError: If the attribute `pipeline_root` is not set, and it
                can be not generated using the path of the artifact store in the
                stack because it is not a
                `zenml.integrations.gcp.artifact_store.GCPArtifactStore`. Also gets
                raised if attempting to schedule pipeline run without using the
                `zenml.integrations.gcp.artifact_store.GCPArtifactStore`.

        Yields:
            A dictionary of metadata related to the pipeline run.
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

        def _create_dynamic_pipeline() -> Any:
            """Create a dynamic pipeline including each step.

            Returns:
                pipeline_func
            """
            step_name_to_dynamic_component: Dict[str, BaseComponent] = {}

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
                component = self._create_container_component(
                    image, command, arguments, step_name
                )
                step_settings = cast(
                    VertexOrchestratorSettings, self.get_settings(step)
                )
                pod_settings = step_settings.pod_settings
                if pod_settings:
                    ignored_fields = pod_settings.model_fields_set - {
                        "node_selectors"
                    }
                    if ignored_fields:
                        logger.warning(
                            f"The following pod settings are not supported in "
                            f"Vertex with Vertex Pipelines 2.x and will be "
                            f"ignored: {list(ignored_fields)}."
                        )

                    for key in pod_settings.node_selectors:
                        if (
                            key
                            != GKE_ACCELERATOR_NODE_SELECTOR_CONSTRAINT_LABEL
                        ):
                            logger.warning(
                                "Vertex only allows the %s node selector, "
                                "ignoring the node selector %s.",
                                GKE_ACCELERATOR_NODE_SELECTOR_CONSTRAINT_LABEL,
                                key,
                            )

                step_name_to_dynamic_component[step_name] = component

            environment[ENV_ZENML_VERTEX_RUN_ID] = (
                dsl.PIPELINE_JOB_NAME_PLACEHOLDER
            )

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

                    step_settings = cast(
                        VertexOrchestratorSettings, self.get_settings(step)
                    )

                    use_custom_training_job = (
                        step_settings.custom_job_parameters is not None
                    )

                    if use_custom_training_job:
                        if not step.config.resource_settings.empty:
                            logger.warning(
                                "Ignoring resource settings because "
                                "the step is running as a custom training job. "
                                "Use `custom_job_parameters.machine_type` "
                                "to configure the machine type instead."
                            )
                        if step_settings.node_selector_constraint:
                            logger.warning(
                                "Ignoring node selector constraint because "
                                "the step is running as a custom training job. "
                                "Use `custom_job_parameters.accelerator_type` "
                                "to configure the accelerator type instead."
                            )
                        component = self._convert_to_custom_training_job(
                            component,
                            settings=step_settings,
                            environment=environment,
                        )
                        task = (
                            component()
                            .set_display_name(name=component_name)
                            .set_caching_options(enable_caching=False)
                            .after(*upstream_step_components)
                        )
                    else:
                        task = (
                            component()
                            .set_display_name(
                                name=component_name,
                            )
                            .set_caching_options(enable_caching=False)
                            .after(*upstream_step_components)
                        )
                        for key, value in environment.items():
                            task = task.set_env_variable(name=key, value=value)

                        pod_settings = step_settings.pod_settings

                        node_selector_constraint: Optional[Tuple[str, str]] = (
                            None
                        )
                        if pod_settings and (
                            GKE_ACCELERATOR_NODE_SELECTOR_CONSTRAINT_LABEL
                            in pod_settings.node_selectors.keys()
                        ):
                            node_selector_constraint = (
                                GKE_ACCELERATOR_NODE_SELECTOR_CONSTRAINT_LABEL,
                                pod_settings.node_selectors[
                                    GKE_ACCELERATOR_NODE_SELECTOR_CONSTRAINT_LABEL
                                ],
                            )
                        elif step_settings.node_selector_constraint:
                            node_selector_constraint = (
                                GKE_ACCELERATOR_NODE_SELECTOR_CONSTRAINT_LABEL,
                                step_settings.node_selector_constraint[1],
                            )

                        self._configure_container_resources(
                            dynamic_component=task,
                            resource_settings=step.config.resource_settings,
                            node_selector_constraint=node_selector_constraint,
                        )

            return dynamic_pipeline

        # Save the generated pipeline to a file.
        fileio.makedirs(self.pipeline_directory)
        pipeline_file_path = os.path.join(
            self.pipeline_directory,
            f"{orchestrator_run_name}.json",
        )

        # Compile the pipeline using the Kubeflow SDK V2 compiler that allows
        # to generate a JSON representation of the pipeline that can be later
        # upload to Vertex AI Pipelines service.
        Compiler().compile(
            pipeline_func=_create_dynamic_pipeline(),
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
        # pipeline on the Vertex AI Pipelines service.
        if metadata := self._upload_and_run_pipeline(
            pipeline_name=deployment.pipeline_configuration.name,
            pipeline_file_path=pipeline_file_path,
            run_name=orchestrator_run_name,
            settings=settings,
            schedule=deployment.schedule,
        ):
            yield from metadata

    def _upload_and_run_pipeline(
        self,
        pipeline_name: str,
        pipeline_file_path: str,
        run_name: str,
        settings: VertexOrchestratorSettings,
        schedule: Optional["ScheduleResponse"] = None,
    ) -> Iterator[Dict[str, MetadataType]]:
        """Uploads and run the pipeline on the Vertex AI Pipelines service.

        Args:
            pipeline_name: Name of the pipeline.
            pipeline_file_path: Path of the JSON file containing the compiled
                Kubeflow pipeline (compiled with Kubeflow SDK v2).
            run_name: Orchestrator run name.
            settings: Pipeline level settings for this orchestrator.
            schedule: The schedule the pipeline will run on.

        Raises:
            RuntimeError: If the Vertex Orchestrator fails to provision or any
                other Runtime errors.

        Yields:
            A dictionary of metadata related to the pipeline run.
        """
        # We have to replace the hyphens in the run name with underscores
        # and lower case the string, because the Vertex AI Pipelines service
        # requires this format.
        job_id = _clean_pipeline_name(run_name)

        # Get the credentials that would be used to create the Vertex AI
        # Pipelines job.
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

        if self.config.private_service_connect:
            # The PSC setting isn't yet part of the stable v1 API. We need to
            # temporarily hack the aiplatform.PipelineJob object in two places:
            # * to use the v1beta1 PipelineJob primitive which supports the
            #   psc_interface_config field instead of the v1 PipelineJob
            #   primitive.
            # * to use the v1beta1 PipelineServiceClient instead of the v1
            #   PipelineServiceClient.
            #
            # We achieve the first by converting the v1 PipelineJob to a
            # v1beta1 PipelineJob and the second by replacing the v1
            # PipelineServiceClient with a v1beta1 PipelineServiceClient.
            #
            # TODO: Remove this once the v1 stable API is updated to support
            # the PSC setting.
            pipeline_job_dict = json_format.MessageToDict(
                run._gca_resource._pb, preserving_proto_field_name=True
            )
            run._gca_resource = pipeline_job_v1beta1.PipelineJob(
                **pipeline_job_dict,
                psc_interface_config=PscInterfaceConfig(
                    network_attachment=self.config.private_service_connect,
                ),
            )
            run.api_client = (
                pipeline_service_client_v1beta1.PipelineServiceClient(
                    credentials=run.credentials,
                    client_options={
                        "api_endpoint": run.api_client.api_endpoint,
                    },
                )
            )

        try:
            if schedule:
                logger.info(
                    "Scheduling job using native Vertex AI Pipelines "
                    "scheduling..."
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
                    "Submitting pipeline job with job_id `%s` to Vertex AI "
                    "Pipelines service.",
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

                # Yield metadata based on the generated job object
                yield from self.compute_metadata(run)

                if settings.synchronous:
                    logger.info(
                        "Waiting for the Vertex AI Pipelines job to finish..."
                    )
                    run.wait()
                    logger.info(
                        "Vertex AI Pipelines job completed successfully."
                    )

        except google_exceptions.ClientError as e:
            logger.error("Failed to create the Vertex AI Pipelines job: %s", e)
            raise RuntimeError(
                f"Failed to create the Vertex AI Pipelines job: {e}"
            )
        except RuntimeError as e:
            logger.error(
                "The Vertex AI Pipelines job execution has failed: %s", e
            )
            raise

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
        cpu_limit = None
        if resource_settings:
            cpu_limit = resource_settings.cpu_count or self.config.cpu_limit

        if cpu_limit is not None:
            dynamic_component = dynamic_component.set_cpu_limit(str(cpu_limit))

        memory_limit = (
            resource_settings.memory[:-1]
            if resource_settings.memory
            else self.config.memory_limit
        )
        if memory_limit is not None:
            dynamic_component = dynamic_component.set_memory_limit(
                memory_limit
            )

        gpu_limit = (
            resource_settings.gpu_count
            if resource_settings.gpu_count is not None
            else self.config.gpu_limit
        )

        if node_selector_constraint:
            _, value = node_selector_constraint
            if gpu_limit is not None and gpu_limit > 0:
                dynamic_component = (
                    dynamic_component.set_accelerator_type(value)
                    .set_accelerator_limit(gpu_limit)
                    .set_gpu_limit(gpu_limit)
                )
            else:
                logger.warning(
                    "Accelerator type %s specified, but the GPU limit is not "
                    "set or set to 0. The accelerator type will be ignored. "
                    "To fix this warning, either remove the specified "
                    "accelerator type or set the `gpu_count` using the "
                    "ResourceSettings (https://docs.zenml.io/how-to/advanced-topics/training-with-gpus)."
                )

        return dynamic_component

    def fetch_status(self, run: "PipelineRunResponse") -> ExecutionStatus:
        """Refreshes the status of a specific pipeline run.

        Args:
            run: The run that was executed by this orchestrator.

        Returns:
            the actual status of the pipeline job.

        Raises:
            AssertionError: If the run was not executed by to this orchestrator.
            ValueError: If it fetches an unknown state or if we can not fetch
                the orchestrator run ID.
        """
        # Make sure that the stack exists and is accessible
        if run.stack is None:
            raise ValueError(
                "The stack that the run was executed on is not available "
                "anymore."
            )

        # Make sure that the run belongs to this orchestrator
        assert (
            self.id
            == run.stack.components[StackComponentType.ORCHESTRATOR][0].id
        )

        # Initialize the Vertex client
        credentials, project_id = self._get_authentication()
        aiplatform.init(
            project=project_id,
            location=self.config.location,
            credentials=credentials,
        )

        # Fetch the status of the PipelineJob
        if METADATA_ORCHESTRATOR_RUN_ID in run.run_metadata:
            run_id = run.run_metadata[METADATA_ORCHESTRATOR_RUN_ID]
        elif run.orchestrator_run_id is not None:
            run_id = run.orchestrator_run_id
        else:
            raise ValueError(
                "Can not find the orchestrator run ID, thus can not fetch "
                "the status."
            )
        status = aiplatform.PipelineJob.get(run_id).state

        # Map the potential outputs to ZenML ExecutionStatus. Potential values:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sagemaker/client/describe_pipeline_execution.html#
        if status in [PipelineState.PIPELINE_STATE_UNSPECIFIED]:
            return run.status
        elif status in [
            PipelineState.PIPELINE_STATE_QUEUED,
            PipelineState.PIPELINE_STATE_PENDING,
        ]:
            return ExecutionStatus.INITIALIZING
        elif status in [
            PipelineState.PIPELINE_STATE_RUNNING,
            PipelineState.PIPELINE_STATE_PAUSED,
        ]:
            return ExecutionStatus.RUNNING
        elif status in [PipelineState.PIPELINE_STATE_SUCCEEDED]:
            return ExecutionStatus.COMPLETED

        elif status in [
            PipelineState.PIPELINE_STATE_FAILED,
            PipelineState.PIPELINE_STATE_CANCELLING,
            PipelineState.PIPELINE_STATE_CANCELLED,
        ]:
            return ExecutionStatus.FAILED
        else:
            raise ValueError("Unknown status for the pipeline job.")

    def compute_metadata(
        self, job: aiplatform.PipelineJob
    ) -> Iterator[Dict[str, MetadataType]]:
        """Generate run metadata based on the corresponding Vertex PipelineJob.

        Args:
            job: The corresponding PipelineJob object.

        Yields:
            A dictionary of metadata related to the pipeline run.
        """
        metadata: Dict[str, MetadataType] = {}

        # Orchestrator Run ID
        if run_id := self._compute_orchestrator_run_id(job):
            metadata[METADATA_ORCHESTRATOR_RUN_ID] = run_id

        # URL to the Vertex's pipeline view
        if orchestrator_url := self._compute_orchestrator_url(job):
            metadata[METADATA_ORCHESTRATOR_URL] = Uri(orchestrator_url)

        # URL to the corresponding Logs Explorer page
        if logs_url := self._compute_orchestrator_logs_url(job):
            metadata[METADATA_ORCHESTRATOR_LOGS_URL] = Uri(logs_url)

        yield metadata

    @staticmethod
    def _compute_orchestrator_url(
        job: aiplatform.PipelineJob,
    ) -> Optional[str]:
        """Generate the Orchestrator Dashboard URL upon pipeline execution.

        Args:
            job: The corresponding PipelineJob object.

        Returns:
             the URL to the dashboard view in Vertex.
        """
        try:
            return str(job._dashboard_uri())
        except Exception as e:
            logger.warning(
                f"There was an issue while extracting the pipeline url: {e}"
            )
            return None

    @staticmethod
    def _compute_orchestrator_logs_url(
        job: aiplatform.PipelineJob,
    ) -> Optional[str]:
        """Generate the Logs Explorer URL upon pipeline execution.

        Args:
            job: The corresponding PipelineJob object.

        Returns:
            the URL querying the pipeline logs in Logs Explorer on GCP.
        """
        try:
            base_url = "https://console.cloud.google.com/logs/query"
            query = f"""
             resource.type="aiplatform.googleapis.com/PipelineJob"
             resource.labels.pipeline_job_id="{job.job_id}"
             """
            encoded_query = urllib.parse.quote(query)
            return f"{base_url}?project={job.project}&query={encoded_query}"

        except Exception as e:
            logger.warning(
                f"There was an issue while extracting the logs url: {e}"
            )
            return None

    @staticmethod
    def _compute_orchestrator_run_id(
        job: aiplatform.PipelineJob,
    ) -> Optional[str]:
        """Fetch the Orchestrator Run ID upon pipeline execution.

        Args:
            job: The corresponding PipelineJob object.

        Returns:
            the Execution ID of the run in Vertex.
        """
        try:
            if job.job_id:
                return str(job.job_id)

            return None
        except Exception as e:
            logger.warning(
                f"There was an issue while extracting the pipeline run ID: {e}"
            )
            return None
