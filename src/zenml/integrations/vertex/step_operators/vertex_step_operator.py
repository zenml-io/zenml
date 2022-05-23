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
"""Code heavily inspired by TFX Implementation:
https://github.com/tensorflow/tfx/blob/master/tfx/extensions/
google_cloud_ai_platform/training_clients.py"""

import time
from typing import ClassVar, List, Optional, Tuple

from google.auth import credentials as auth_credentials
from google.auth import default, load_credentials_from_file
from google.cloud import aiplatform
from pydantic import validator as property_validator

from zenml import __version__
from zenml.enums import StackComponentType
from zenml.integrations.vertex import VERTEX_STEP_OPERATOR_FLAVOR
from zenml.integrations.vertex.constants import (
    CONNECTION_ERROR_RETRY_LIMIT,
    POLLING_INTERVAL_IN_SECONDS,
    VERTEX_ENDPOINT_SUFFIX,
    VERTEX_JOB_STATES_COMPLETED,
    VERTEX_JOB_STATES_FAILED,
)
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator
from zenml.utils import docker_utils
from zenml.utils.source_utils import get_source_root_path

logger = get_logger(__name__)


class VertexStepOperator(BaseStepOperator):
    """Step operator to run a step on Vertex AI.

    This class defines code that can set up a Vertex AI environment and run the
    ZenML entrypoint command in it.

    Attributes:
        region: Region name, e.g., `europe-west1`.
        project: [Optional] GCP project name. If left None, inferred from the
            environment.
        accelerator_type: [Optional] Accelerator type from list: https://cloud.google.com/vertex-ai/docs/reference/rest/v1/MachineSpec#AcceleratorType
        accelerator_count: [Optional] Defines number of accelerators to be
            used for the job.
        machine_type: [Optional] Machine type specified here: https://cloud.google.com/vertex-ai/docs/training/configure-compute#machine-types
        base_image: [Optional] Base image for building the custom job container.
        encryption_spec_key_name: [Optional]: Encryption spec key name.
        service_account_path: [Optional]: Path to service account file
            specifying credentials of the GCP user. If not provided, falls back
            to Default Credentials.
    """

    region: str
    project: Optional[str] = None
    accelerator_type: Optional[str] = None
    accelerator_count: int = 0
    machine_type: str = "n1-standard-4"
    base_image: Optional[str] = None

    # customer managed encryption key resource name
    # will be applied to all Vertex AI resources if set
    encryption_spec_key_name: Optional[str] = None

    # path to google service account
    # environment default credentials used if not set
    service_account_path: Optional[str] = None

    # Class configuration
    FLAVOR: ClassVar[str] = VERTEX_STEP_OPERATOR_FLAVOR

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack contains a container registry."""

        def _ensure_local_orchestrator(stack: Stack) -> Tuple[bool, str]:
            # For now this only works on local orchestrator and GCP artifact
            #  store
            return (
                (
                    stack.orchestrator.FLAVOR == "local"
                    and stack.artifact_store.FLAVOR == "gcp"
                ),
                "Only local orchestrator and GCP artifact store are currently "
                "supported",
            )

        return StackValidator(
            required_components={StackComponentType.CONTAINER_REGISTRY},
            custom_validation_function=_ensure_local_orchestrator,
        )

    @property_validator("accelerator_type")
    def validate_accelerator_enum(cls, accelerator_type: Optional[str]) -> None:
        accepted_vals = list(
            aiplatform.gapic.AcceleratorType.__members__.keys()
        )
        if accelerator_type and accelerator_type.upper() not in accepted_vals:
            raise ValueError(
                f"Accelerator must be one of the following: {accepted_vals}"
            )

    def _get_authentication(
        self,
    ) -> Tuple[Optional[auth_credentials.Credentials], Optional[str]]:
        if self.service_account_path:
            credentials, project_id = load_credentials_from_file(
                self.service_account_path
            )
        else:
            credentials, project_id = default()
        return credentials, project_id

    def _build_and_push_docker_image(
        self,
        pipeline_name: str,
        requirements: List[str],
        entrypoint_command: List[str],
    ) -> str:
        repo = Repository()
        container_registry = repo.active_stack.container_registry

        if not container_registry:
            raise RuntimeError("Missing container registry")

        registry_uri = container_registry.uri.rstrip("/")
        image_name = f"{registry_uri}/zenml-vertex:{pipeline_name}"

        docker_utils.build_docker_image(
            build_context_path=get_source_root_path(),
            image_name=image_name,
            entrypoint=" ".join(entrypoint_command),
            requirements=set(requirements),
            base_image=self.base_image,
        )
        container_registry.push_image(image_name)
        return docker_utils.get_image_digest(image_name) or image_name

    def launch(
        self,
        pipeline_name: str,
        run_name: str,
        requirements: List[str],
        entrypoint_command: List[str],
    ) -> None:
        """Launches a step on Vertex AI.

        Args:
            pipeline_name: Name of the pipeline which the step to be executed
                is part of.
            run_name: Name of the pipeline run which the step to be executed
                is part of.
            entrypoint_command: Command that executes the step.
            requirements: List of pip requirements that must be installed
                inside the step operator environment.
        """
        job_labels = {"source": f"zenml-{__version__.replace('.', '_')}"}

        # Step 1: Authenticate with Google
        credentials, project_id = self._get_authentication()
        if self.project:
            if self.project != project_id:
                logger.warning(
                    f"Authenticated with project {project_id}, but this "
                    f"operator is configured to use project {self.project}."
                )
        else:
            self.project = project_id

        # Step 2: Build and push image
        image_name = self._build_and_push_docker_image(
            pipeline_name=pipeline_name,
            requirements=requirements,
            entrypoint_command=entrypoint_command,
        )

        # Step 3: Launch the job
        # The AI Platform services require regional API endpoints.
        client_options = {"api_endpoint": self.region + VERTEX_ENDPOINT_SUFFIX}
        # Initialize client that will be used to create and send requests.
        # This client only needs to be created once, and can be reused for multiple requests.
        client = aiplatform.gapic.JobServiceClient(
            credentials=credentials, client_options=client_options
        )
        custom_job = {
            "display_name": run_name,
            "job_spec": {
                "worker_pool_specs": [
                    {
                        "machine_spec": {
                            "machine_type": self.machine_type,
                            "accelerator_type": self.accelerator_type,
                            "accelerator_count": self.accelerator_count
                            if self.accelerator_type
                            else 0,
                        },
                        "replica_count": 1,
                        "container_spec": {
                            "image_uri": image_name,
                            "command": [],
                            "args": [],
                        },
                    }
                ]
            },
            "labels": job_labels,
            "encryption_spec": {"kmsKeyName": self.encryption_spec_key_name}
            if self.encryption_spec_key_name
            else {},
        }
        logger.debug("Vertex AI Job=%s", custom_job)

        parent = f"projects/{self.project}/locations/{self.region}"
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
