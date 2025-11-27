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

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast

from google.cloud import aiplatform

from zenml import __version__
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import StackComponentType
from zenml.integrations.gcp.constants import (
    VERTEX_ENDPOINT_SUFFIX,
)
from zenml.integrations.gcp.flavors.vertex_step_operator_flavor import (
    VertexStepOperatorConfig,
    VertexStepOperatorSettings,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsMixin,
)
from zenml.integrations.gcp.utils import build_job_request, monitor_job
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineSnapshotBase

logger = get_logger(__name__)

VERTEX_DOCKER_IMAGE_KEY = "vertex_step_operator"


class VertexStepOperator(BaseStepOperator, GoogleCredentialsMixin):
    """Step operator to run a step on Vertex AI.

    This class defines code that can set up a Vertex AI environment and run the
    ZenML entrypoint command in it.
    """

    _job_service_client: Optional[aiplatform.gapic.JobServiceClient] = None

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
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_remote_components,
        )

    def get_docker_builds(
        self, snapshot: "PipelineSnapshotBase"
    ) -> List["BuildConfiguration"]:
        """Gets the Docker builds required for the component.

        Args:
            snapshot: The pipeline snapshot for which to get the builds.

        Returns:
            The required Docker builds.
        """
        builds = []
        for step_name, step in snapshot.step_configurations.items():
            if step.config.uses_step_operator(self.name):
                build = BuildConfiguration(
                    key=VERTEX_DOCKER_IMAGE_KEY,
                    settings=step.config.docker_settings,
                    step_name=step_name,
                )
                builds.append(build)

        return builds

    def get_job_service_client(self) -> aiplatform.gapic.JobServiceClient:
        """Get the job service client.

        Returns:
            The job service client.
        """
        if self.connector_has_expired():
            self._job_service_client = None

        if self._job_service_client is None:
            credentials, _ = self._get_authentication()
            client_options = {
                "api_endpoint": self.config.region + VERTEX_ENDPOINT_SUFFIX
            }
            self._job_service_client = aiplatform.gapic.JobServiceClient(
                credentials=credentials, client_options=client_options
            )
        return self._job_service_client

    def launch(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Launches a step on VertexAI.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables to set in the step operator
                environment.
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
        image = info.get_image(key=VERTEX_DOCKER_IMAGE_KEY)

        labels = {"source": f"zenml-{__version__.replace('.', '_')}"}
        job_request = build_job_request(
            display_name=f"{info.run_name}-{info.pipeline_step_name}",
            image=image,
            entrypoint_command=entrypoint_command,
            custom_job_settings=settings,
            resource_settings=info.config.resource_settings,
            environment=environment,
            labels=labels,
            encryption_spec_key_name=self.config.encryption_spec_key_name,
            service_account=self.config.service_account,
            network=self.config.network,
        )
        logger.debug("Vertex AI Job=%s", job_request)

        client = self.get_job_service_client()
        parent = (
            f"projects/{self.gcp_project_id}/locations/{self.config.region}"
        )
        logger.info(
            "Submitting custom job='%s', path='%s' to Vertex AI Training.",
            job_request["display_name"],
            parent,
        )
        info.force_write_logs()
        response = client.create_custom_job(
            parent=parent, custom_job=job_request
        )
        logger.debug("Vertex AI response:", response)

        monitor_job(
            job_id=response.name,
            get_client=self.get_job_service_client,
        )
