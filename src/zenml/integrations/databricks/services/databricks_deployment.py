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
"""Implementation of the Databricks Deployment service."""

from typing import Any, Dict, Generator, Optional, Tuple

from databricks.sdk import WorkspaceClient as DatabricksClient
from databricks.sdk.service.serving import (
    EndpointCoreConfigInput,
    EndpointStateConfigUpdate,
    EndpointStateReady,
    EndpointTag,
    ServedModelInput,
    ServingEndpointDetailed,
)
from pydantic import Field

from zenml.client import Client
from zenml.integrations.databricks.flavors.databricks_model_deployer_flavor import (
    DatabricksBaseConfig,
)
from zenml.integrations.databricks.utils.databricks_utils import (
    sanitize_labels,
)
from zenml.logger import get_logger
from zenml.services import ServiceState, ServiceStatus, ServiceType
from zenml.services.service import BaseDeploymentService, ServiceConfig

logger = get_logger(__name__)

POLLING_TIMEOUT = 1200
UUID_SLICE_LENGTH: int = 8


class DatabricksDeploymentConfig(DatabricksBaseConfig, ServiceConfig):
    """Databricks service configurations."""

    model_uri: str

    def get_databricks_deployment_labels(self) -> Dict[str, str]:
        """Generate labels for the Databricks deployment from the service configuration.

        These labels are attached to the Databricks deployment resource
        and may be used as label selectors in lookup operations.

        Returns:
            The labels for the Databricks deployment.
        """
        labels = {}
        if self.pipeline_name:
            labels["zenml.pipeline_name"] = self.pipeline_name
        if self.pipeline_step_name:
            labels["zenml.pipeline_step_name"] = self.pipeline_step_name
        if self.model_name:
            labels["zenml.model_name"] = self.model_name
        if self.model_uri:
            labels["zenml.model_uri"] = self.model_uri
        sanitize_labels(labels)
        return labels


class DatabricksServiceStatus(ServiceStatus):
    """Databricks service status."""


class DatabricksDeploymentService(BaseDeploymentService):
    """Databricks model deployment service.

    Attributes:
        SERVICE_TYPE: a service type descriptor with information describing
            the Databricks deployment service class
        config: service configuration
    """

    SERVICE_TYPE = ServiceType(
        name="databricks-deployment",
        type="model-serving",
        flavor="databricks",
        description="Databricks inference endpoint prediction service",
    )
    config: DatabricksDeploymentConfig
    status: DatabricksServiceStatus = Field(
        default_factory=lambda: DatabricksServiceStatus()
    )

    def __init__(self, config: DatabricksDeploymentConfig, **attrs: Any):
        """Initialize the Databricks deployment service.

        Args:
            config: service configuration
            attrs: additional attributes to set on the service
        """
        super().__init__(config=config, **attrs)

    def get_client_id_and_secret(self) -> Tuple[str, str]:
        """Get the Databricks client id and secret.

        Raises:
            ValueError: If client id and secret are not found.

        Returns:
            Databricks client id and secret.
        """
        client = Client()
        client_id = None
        client_secret = None
        if self.config.secret_name:
            secret = client.get_secret(self.config.secret_name)
            client_id = secret.secret_values["client_id"]
            client_secret = secret.secret_values["client_secret"]
        else:
            from zenml.integrations.databricks.model_deployers.databricks_model_deployer import (
                DatabricksModelDeployer,
            )

            model_deployer = client.active_stack.model_deployer
            if not isinstance(model_deployer, DatabricksModelDeployer):
                raise ValueError(
                    "DatabricksModelDeployer is not active in the stack."
                )
            client_id = model_deployer.config.client_id or None
            client_secret = model_deployer.config.client_secret or None
        if not client_id:
            raise ValueError("Client id not found.")
        if not client_secret:
            raise ValueError("Client secret not found.")
        if not self.config.host:
            raise ValueError("Host not found.")
        return client_id, client_secret

    def _get_databricks_deployment_labels(self) -> Dict[str, str]:
        """Generate the labels for the Databricks deployment from the service configuration.

        Returns:
            The labels for the Databricks deployment.
        """
        labels = self.config.get_databricks_deployment_labels()
        labels["zenml.service_uuid"] = str(self.uuid)
        sanitize_labels(labels)
        return labels

    @property
    def databricks_client(self) -> DatabricksClient:
        """Get the deployed Databricks inference endpoint.

        Returns:
            databricks inference endpoint.
        """
        return DatabricksClient(
            host=self.config.host,
            client_id=self.get_client_id_and_secret()[0],
            client_secret=self.get_client_id_and_secret()[1],
        )

    @property
    def databricks_endpoint(self) -> ServingEndpointDetailed:
        """Get the deployed Hugging Face inference endpoint.

        Returns:
            Huggingface inference endpoint.
        """
        return self.databricks_client.serving_endpoints.get(
            name=self._generate_an_endpoint_name(),
        )

    @property
    def prediction_url(self) -> Optional[str]:
        """The prediction URI exposed by the prediction service.

        Returns:
            The prediction URI exposed by the prediction service, or None if
            the service is not yet ready.
        """
        return self.databricks_endpoint.endpoint_url if self.is_running else None

    def provision(self) -> None:
        """Provision or update remote Databricks deployment instance.

        Raises:
            Exception: If any unexpected error while creating inference endpoint.
        """
        try:
            tags = []
            for key, value in self._get_databricks_deployment_labels().items():
                tags.append(EndpointTag(key=key, value=value))
            # Attempt to create and wait for the inference endpoint
            databricks_endpoint = self.databricks_client.serving_endpoints.create_and_wait(
                name=self._generate_an_endpoint_name(),
                config=EndpointCoreConfigInput(
                    served_models=ServedModelInput(
                        model_name=self.config.model_name,
                        model_version=self.config.model_version,
                        scale_to_zero_enabled=self.config.scale_to_zero_enabled,
                        workload_type=self.config.workload_type,
                        workload_size=self.config.workload_size,
                    ),
                ),
                tags=tags,
            )

        except Exception as e:
            self.status.update_state(
                new_state=ServiceState.ERROR, error=str(e)
            )
            # Catch-all for any other unexpected errors
            raise Exception(
                f"An unexpected error occurred while provisioning the Databricks inference endpoint: {e}"
            )

        # Check if the endpoint URL is available after provisioning
        if databricks_endpoint.endpoint_url:
            logger.info(
                f"Databricks inference endpoint successfully deployed and available. Endpoint URL: {databricks_endpoint.endpoint_url}"
            )
        else:
            logger.error(
                "Failed to start Databricks inference endpoint service: No URL available, please check the Databricks console for more details."
            )

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the the current operational state of the Databricks deployment.

        Returns:
            The operational state of the Databricks deployment and a message
            providing additional information about that state (e.g. a
            description of the error, if one is encountered).
        """
        try:
            status = self.databricks_endpoint.state or None
            if status.ready == EndpointStateReady.READY:
                return (ServiceState.ACTIVE, "")
            elif (
                status.config_update == EndpointStateConfigUpdate.UPDATE_FAILED
            ):
                return (
                    ServiceState.ERROR,
                    "Databricks Inference Endpoint deployment update failed",
                )
            elif status == EndpointStateConfigUpdate.IN_PROGRESS:
                return (ServiceState.PENDING_STARTUP, "")
            return (ServiceState.PENDING_STARTUP, "")
        except Exception as e:
            return (
                ServiceState.INACTIVE,
                f"Databricks Inference Endpoint deployment is inactive or not found: {e}",
            )

    def deprovision(self, force: bool = False) -> None:
        """Deprovision the remote Databricks deployment instance.

        Args:
            force: if True, the remote deployment instance will be
                forcefully deprovisioned.
        """
        try:
            self.databricks_client.serving_endpoints.delete(
                name=self._generate_an_endpoint_name()
            )
        except Exception:
            logger.error(
                "Databricks Inference Endpoint is deleted or cannot be found."
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
                "Databricks endpoint inference service is not running. "
                "Please start the service before making predictions."
            )
        if self.prediction_url is not None:
            pass
        else:
            # TODO: Add support for all different supported tasks
            raise NotImplementedError(
                "Tasks other than text-generation is not implemented."
            )
        return ""

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
            "Databricks Endpoints provides access to the logs of your Endpoints through the UI in the `Logs` tab of your Endpoint"
        )

        def log_generator() -> Generator[str, bool, None]:
            logs = self.databricks_client.serving_endpoints.logs(
                name=self._generate_an_endpoint_name(),
                served_model_name=self.config.model_name,
            )

            # Split the logs into lines
            log_lines = logs.split("\n")

            # Apply tail if specified
            if tail is not None:
                log_lines = log_lines[-tail:]

            for line in log_lines:
                yield line

            # If follow is True, continuously check for new logs
            if follow:
                while True:
                    new_logs = self.databricks_client.serving_endpoints.logs(
                        name=self._generate_an_endpoint_name(),
                        served_model_name=self.config.model_name,
                    )
                    new_lines = new_logs.split("\n")

                    # Only yield new lines
                    for line in new_lines[len(log_lines) :]:
                        yield line

                    log_lines = new_lines

                    # Check if we should continue
                    should_continue = yield
                    if not should_continue:
                        break

        return log_generator()

    def _generate_an_endpoint_name(self) -> str:
        """Generate a unique name for the Databricks Inference Endpoint.

        Returns:
            A unique name for the Databricks Inference Endpoint.
        """
        return (
            f"{self.config.service_name}-{str(self.uuid)[:UUID_SLICE_LENGTH]}"
        )
