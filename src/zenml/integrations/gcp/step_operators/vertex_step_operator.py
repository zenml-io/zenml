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
"""Implementation of a VertexAI step operator.

Code heavily inspired by TFX Implementation:
https://github.com/tensorflow/tfx/blob/master/tfx/extensions/
google_cloud_ai_platform/training_clients.py
"""

import time
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Type, cast

from google.cloud import aiplatform

from zenml import __version__
from zenml.enums import StackComponentType
from zenml.integrations.gcp.constants import (
    CONNECTION_ERROR_RETRY_LIMIT,
    POLLING_INTERVAL_IN_SECONDS,
    VERTEX_ENDPOINT_SUFFIX,
    VERTEX_JOB_STATES_COMPLETED,
    VERTEX_JOB_STATES_FAILED,
)
from zenml.integrations.gcp.flavors.vertex_step_operator_flavor import (
    VertexStepOperatorConfig,
    VertexStepOperatorSettings,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsMixin,
)
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator
from zenml.utils.pipeline_docker_image_builder import PipelineDockerImageBuilder

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.config.step_run_info import StepRunInfo

logger = get_logger(__name__)

VERTEX_DOCKER_IMAGE_DIGEST_KEY = "vertex_docker_image"


def validate_accelerator_type(accelerator_type: Optional[str] = None) -> None:
    """Validates that the accelerator type is valid.

    Args:
        accelerator_type: The accelerator type to validate.

    Raises:
        ValueError: If the accelerator type is not valid.
    """
    accepted_vals = list(aiplatform.gapic.AcceleratorType.__members__.keys())
    if accelerator_type and accelerator_type.upper() not in accepted_vals:
        raise ValueError(
            f"Accelerator must be one of the following: {accepted_vals}"
        )


class VertexStepOperator(BaseStepOperator, GoogleCredentialsMixin):
    """Step operator to run a step on Vertex AI.

    This class defines code that can set up a Vertex AI environment and run the
    ZenML entrypoint command in it.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the step operator and validates the accelerator type.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)

    @property
    def config(self) -> VertexStepOperatorConfig:
        """Returns the `VertexStepOperatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(VertexStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Vertex step operator.

        Returns:
            The settings class.
        """
        return VertexStepOperatorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack.

        Returns:
            A validator that checks that the stack contains a remote container
            registry and a remote artifact store.
        """

        def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The Vertex step operator runs code remotely and "
                    "needs to write files into the artifact store, but the "
                    f"artifact store `{stack.artifact_store.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote artifact store when using the Vertex "
                    "step operator."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The Vertex step operator runs code remotely and "
                    "needs to push/pull Docker images, but the "
                    f"container registry `{container_registry.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote container registry when using the "
                    "Vertex step operator."
                )

            return True, ""

        return StackValidator(
            required_components={StackComponentType.CONTAINER_REGISTRY},
            custom_validation_function=_validate_remote_components,
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
        steps_to_run = [
            step
            for step in deployment.steps.values()
            if step.config.step_operator == self.name
        ]
        if not steps_to_run:
            return
        docker_image_builder = PipelineDockerImageBuilder()
        image_digest = docker_image_builder.build_and_push_docker_image(
            deployment=deployment,
            stack=stack,
        )
        for step in steps_to_run:
            step.config.extra[VERTEX_DOCKER_IMAGE_DIGEST_KEY] = image_digest

    def launch(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
    ) -> None:
        """Launches a step on VertexAI.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.

        Raises:
            RuntimeError: If the run fails.
            ConnectionError: If the run fails due to a connection error.
        """
        resource_settings = info.config.resource_settings
        if resource_settings.cpu_count or resource_settings.memory:
            logger.warning(
                "Specifying cpus or memory is not supported for "
                "the Vertex step operator. If you want to run this step "
                "operator on specific resources, you can do so by configuring "
                "a different machine_type type like this: "
                "`zenml step-operator update %s "
                "--machine_type=<MACHINE_TYPE>`",
                self.name,
            )
        settings = cast(VertexStepOperatorSettings, self.get_settings(info))
        validate_accelerator_type(settings.accelerator_type)

        job_labels = {"source": f"zenml-{__version__.replace('.', '_')}"}

        # Step 1: Authenticate with Google
        credentials, project_id = self._get_authentication()
        if self.config.project:
            if self.config.project != project_id:
                logger.warning(
                    "Authenticated with project `%s`, but this orchestrator is "
                    "configured to use the project `%s`.",
                    project_id,
                    self.config.project,
                )
        else:
            self.config.project = project_id

        image_name = info.config.extra[VERTEX_DOCKER_IMAGE_DIGEST_KEY]

        # Step 3: Launch the job
        # The AI Platform services require regional API endpoints.
        client_options = {
            "api_endpoint": self.config.region + VERTEX_ENDPOINT_SUFFIX
        }
        # Initialize client that will be used to create and send requests.
        # This client only needs to be created once, and can be reused for multiple requests.
        client = aiplatform.gapic.JobServiceClient(
            credentials=credentials, client_options=client_options
        )
        accelerator_count = (
            resource_settings.gpu_count or settings.accelerator_count
        )
        custom_job = {
            "display_name": info.run_name,
            "job_spec": {
                "worker_pool_specs": [
                    {
                        "machine_spec": {
                            "machine_type": settings.machine_type,
                            "accelerator_type": settings.accelerator_type,
                            "accelerator_count": accelerator_count
                            if settings.accelerator_type
                            else 0,
                        },
                        "replica_count": 1,
                        "container_spec": {
                            "image_uri": image_name,
                            "command": entrypoint_command,
                            "args": [],
                        },
                    }
                ]
            },
            "labels": job_labels,
            "encryption_spec": {
                "kmsKeyName": self.config.encryption_spec_key_name
            }
            if self.config.encryption_spec_key_name
            else {},
        }
        logger.debug("Vertex AI Job=%s", custom_job)

        parent = (
            f"projects/{self.config.project}/locations/{self.config.region}"
        )
        logger.info(
            "Submitting custom job='%s', path='%s' to Vertex AI Training.",
            custom_job["display_name"],
            parent,
        )
        response = client.create_custom_job(
            parent=parent, custom_job=custom_job
        )
        logger.debug("Vertex AI response:", response)

        # Step 4: Monitor the job

        # Monitors the long-running operation by polling the job state
        # periodically, and retries the polling when a transient connectivity
        # issue is encountered.
        #
        # Long-running operation monitoring:
        #   The possible states of "get job" response can be found at
        #   https://cloud.google.com/ai-platform/training/docs/reference/rest/v1/projects.jobs#State
        #   where SUCCEEDED/FAILED/CANCELED are considered to be final states.
        #   The following logic will keep polling the state of the job until
        #   the job enters a final state.
        #
        # During the polling, if a connection error was encountered, the GET
        # request will be retried by recreating the Python API client to
        # refresh the lifecycle of the connection being used. See
        # https://github.com/googleapis/google-api-python-client/issues/218
        # for a detailed description of the problem. If the error persists for
        # _CONNECTION_ERROR_RETRY_LIMIT consecutive attempts, the function
        # will raise ConnectionError.
        retry_count = 0
        job_id = response.name

        while response.state not in VERTEX_JOB_STATES_COMPLETED:
            time.sleep(POLLING_INTERVAL_IN_SECONDS)
            try:
                response = client.get_custom_job(name=job_id)
                retry_count = 0
            # Handle transient connection error.
            except ConnectionError as err:
                if retry_count < CONNECTION_ERROR_RETRY_LIMIT:
                    retry_count += 1
                    logger.warning(
                        "ConnectionError (%s) encountered when polling job: "
                        "%s. Trying to recreate the API client.",
                        err,
                        job_id,
                    )
                    # Recreate the Python API client.
                    client = aiplatform.gapic.JobServiceClient(
                        client_options=client_options
                    )
                else:
                    logger.error(
                        "Request failed after %s retries.",
                        CONNECTION_ERROR_RETRY_LIMIT,
                    )
                    raise

            if response.state in VERTEX_JOB_STATES_FAILED:
                err_msg = (
                    "Job '{}' did not succeed.  Detailed response {}.".format(
                        job_id, response
                    )
                )
                logger.error(err_msg)
                raise RuntimeError(err_msg)

        # Cloud training complete
        logger.info("Job '%s' successful.", job_id)
