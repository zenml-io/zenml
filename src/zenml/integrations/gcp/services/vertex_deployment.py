#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Implementation of the Vertex AI Deployment service."""

from typing import TYPE_CHECKING, Any, Generator, Optional, Tuple, cast

from pydantic import Field

from google.cloud import aiplatform

from zenml.client import Client
from zenml.integrations.gcp.flavors.vertex_model_deployer_flavor import (
    VertexBaseConfig,
)
from zenml.logger import get_logger
from zenml.services import ServiceState, ServiceStatus, ServiceType
from zenml.services.service import BaseDeploymentService, ServiceConfig

if TYPE_CHECKING:
    from google.auth.credentials import Credentials

logger = get_logger(__name__)

POLLING_TIMEOUT = 1200
UUID_SLICE_LENGTH: int = 8


class VertexServiceConfig(VertexBaseConfig, ServiceConfig):
    """Vertex AI service configurations."""


class VertexServiceStatus(ServiceStatus):
    """Vertex AI service status."""


class VertexDeploymentService(BaseDeploymentService):
    """Vertex AI model deployment service.

    Attributes:
        SERVICE_TYPE: a service type descriptor with information describing
            the Vertex AI deployment service class
        config: service configuration
    """

    SERVICE_TYPE = ServiceType(
        name="vertex-deployment",
        type="model-serving",
        flavor="vertex",
        description="Vertex AI inference endpoint prediction service",
    )
    config: VertexServiceConfig
    status: VertexServiceStatus = Field(
        default_factory=lambda: VertexServiceStatus()
    )

    def __init__(self, config: VertexServiceConfig, credentials: Tuple["Credentials", str], **attrs: Any):
        """Initialize the Vertex AI deployment service.

        Args:
            config: service configuration
            attrs: additional attributes to set on the service
        """
        super().__init__(config=config, **attrs)
        self._config = config
        self._project, self._credentials = credentials  # Store credentials as a private attribute
        
    @property
    def config(self) -> VertexServiceConfig:
        """Returns the config of the deployment service.

        Returns:
            The config of the deployment service.
        """
        return cast(VertexServiceConfig, self._config)

    def get_token(self) -> str:
        """Get the Vertex AI token.

        Raises:
            ValueError: If token not found.

        Returns:
            Vertex AI token.
        """
        client = Client()
        token = None
        if self.config.secret_name:
            secret = client.get_secret(self.config.secret_name)
            token = secret.secret_values["token"]
        else:
            from zenml.integrations.gcp.model_deployers.vertex_model_deployer import (
                VertexModelDeployer,
            )

            model_deployer = client.active_stack.model_deployer
            if not isinstance(model_deployer, VertexModelDeployer):
                raise ValueError(
                    "VertexModelDeployer is not active in the stack."
                )
            token = model_deployer.config.token or None
        if not token:
            raise ValueError("Token not found.")
        return token

    @property
    def vertex_model(self) -> aiplatform.Model:
        """Get the deployed Vertex AI inference endpoint.

        Returns:
            Vertex AI inference endpoint.
        """
        return aiplatform.Model(f"projects/{self.__project}/locations/{self.config.location}/models/{self.config.model_id}")

    @property
    def prediction_url(self) -> Optional[str]:
        """The prediction URI exposed by the prediction service.

        Returns:
            The prediction URI exposed by the prediction service, or None if
            the service is not yet ready.
        """
        return self.hf_endpoint.url if self.is_running else None

    def provision(self) -> None:
        """Provision or update remote Vertex AI deployment instance.

        Raises:
            Exception: If any unexpected error while creating inference endpoint.
        """
        try:
            # Attempt to create and wait for the inference endpoint
            vertex_endpoint = self.vertex_model.deploy(
                deployed_model_display_name=self.config.deployed_model_display_name,
                traffic_percentage=self.config.traffic_percentage,
                traffic_split=self.config.traffic_split,
                machine_type=self.config.machine_type,
                min_replica_count=self.config.min_replica_count,
                max_replica_count=self.config.max_replica_count,
                accelerator_type=self.config.accelerator_type,
                accelerator_count=self.config.accelerator_count,
                service_account=self.config.service_account,
                metadata=self.config.metadata,
                deploy_request_timeout=self.config.deploy_request_timeout,
                autoscaling_target_cpu_utilization=self.config.autoscaling_target_cpu_utilization,
                autoscaling_target_accelerator_duty_cycle=self.config.autoscaling_target_accelerator_duty_cycle,
                enable_access_logging=self.config.enable_access_logging,
                disable_container_logging=self.config.disable_container_logging,
                encryption_spec_key_name=self.config.encryption_spec_key_name,
                deploy_request_timeout=self.config.deploy_request_timeout,
            )

        except Exception as e:
            self.status.update_state(
                new_state=ServiceState.ERROR, error=str(e)
            )
            # Catch-all for any other unexpected errors
            raise Exception(
                f"An unexpected error occurred while provisioning the Vertex AI inference endpoint: {e}"
            )

        # Check if the endpoint URL is available after provisioning
        if vertex_endpoint.
            logger.info(
                f"Vertex AI inference endpoint successfully deployed and available. Endpoint URL: {hf_endpoint.url}"
            )
        else:
            logger.error(
                "Failed to start Vertex AI inference endpoint service: No URL available, please check the Vertex AI console for more details."
            )

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the the current operational state of the Vertex AI deployment.

        Returns:
            The operational state of the Vertex AI deployment and a message
            providing additional information about that state (e.g. a
            description of the error, if one is encountered).
        """
        pass

    def deprovision(self, force: bool = False) -> None:
        """Deprovision the remote Vertex AI deployment instance.

        Args:
            force: if True, the remote deployment instance will be
                forcefully deprovisioned.
        """
        try:
            self.vertex_model.undeploy()
        except HfHubHTTPError:
            logger.error(
                "Vertex AI Inference Endpoint is deleted or cannot be found."
            )

    def predict(self, data: "Any", max_new_tokens: int) -> "Any":
        """Make a prediction using the service.

        Args:
            data: input data
            max_new_tokens: Number of new tokens to generate

        Returns:
            The prediction result.

        Raises:
            Exception: if the service is not running
            NotImplementedError: if task is not supported.
        """
        if not self.is_running:
            raise Exception(
                "Vertex AI endpoint inference service is not running. "
                "Please start the service before making predictions."
            )
        if self.prediction_url is not None:
            if self.hf_endpoint.task == "text-generation":
                result = self.inference_client.task_generation(
                    data, max_new_tokens=max_new_tokens
                )
        else:
            # TODO: Add support for all different supported tasks
            raise NotImplementedError(
                "Tasks other than text-generation is not implemented."
            )
        return result

    def get_logs(
        self, follow: bool = False, tail: Optional[int] = None
    ) -> Generator[str, bool, None]:
        """Retrieve the service logs.

        Args:
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that can be accessed to get the service logs.
        """
        logger.info(
            "Vertex AI Endpoints provides access to the logs of "
            "your Endpoints through the UI in the “Logs” tab of your Endpoint"
        )
        return  # type: ignore

    def _generate_an_endpoint_name(self) -> str:
        """Generate a unique name for the Vertex AI Inference Endpoint.

        Returns:
            A unique name for the Vertex AI Inference Endpoint.
        """
        return (
            f"{self.config.service_name}-{str(self.uuid)[:UUID_SLICE_LENGTH]}"
        )