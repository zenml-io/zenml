#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Implementation of the Vertex AI Deployment service."""

import re
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, cast

from google.api_core import exceptions, retry
from google.cloud import aiplatform
from pydantic import BaseModel, Field, PrivateAttr

from zenml.client import Client
from zenml.integrations.gcp.flavors.vertex_base_config import (
    VertexAIEndpointConfig,
)
from zenml.logger import get_logger
from zenml.services import ServiceState, ServiceStatus, ServiceType
from zenml.services.service import BaseDeploymentService, ServiceConfig

logger = get_logger(__name__)

# Constants
POLLING_TIMEOUT = 1800  # 30 minutes
RETRY_DEADLINE = 600  # 10 minutes
UUID_SLICE_LENGTH: int = 8

# Retry configuration for transient errors
retry_config = retry.Retry(
    initial=1.0,  # Initial delay in seconds
    maximum=60.0,  # Maximum delay
    multiplier=2.0,  # Delay multiplier
    deadline=RETRY_DEADLINE,
    predicate=retry.if_transient_error,
)


def sanitize_vertex_label(value: str) -> str:
    """Sanitize a label value to comply with Vertex AI requirements.

    Args:
        value: The label value to sanitize

    Returns:
        Sanitized label value
    """
    if not value:
        return ""

    # Convert to lowercase
    value = value.lower()
    # Replace any character that's not lowercase letter, number, dash or underscore
    value = re.sub(r"[^a-z0-9\-_]", "-", value)
    # Ensure it starts with a letter/number by prepending 'x' if needed
    if not value[0].isalnum():
        value = f"x{value}"
    # Truncate to 63 chars to stay under limit
    return value[:63]


class VertexDeploymentConfig(VertexAIEndpointConfig, ServiceConfig):
    """Vertex AI service configurations."""

    def get_vertex_deployment_labels(self) -> Dict[str, str]:
        """Generate labels for the VertexAI deployment from the service configuration."""
        labels = self.labels or {}
        labels["managed_by"] = "zenml"
        if self.pipeline_name:
            labels["pipeline-name"] = sanitize_vertex_label(self.pipeline_name)
        if self.pipeline_step_name:
            labels["step-name"] = sanitize_vertex_label(
                self.pipeline_step_name
            )
        if self.model_name:
            labels["model-name"] = sanitize_vertex_label(self.model_name)
        if self.service_name:
            labels["service-name"] = sanitize_vertex_label(self.service_name)
        return labels


class VertexPredictionServiceEndpoint(BaseModel):
    """Vertex AI Prediction Service Endpoint."""

    endpoint_name: str
    deployed_model_id: str
    endpoint_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    state: Optional[str] = None


class VertexServiceStatus(ServiceStatus):
    """Vertex AI service status."""

    endpoint: Optional[VertexPredictionServiceEndpoint] = None


class VertexDeploymentService(BaseDeploymentService):
    """Vertex AI model deployment service."""

    SERVICE_TYPE = ServiceType(
        name="vertex-deployment",
        type="model-serving",
        flavor="vertex",
        description="Vertex AI inference endpoint prediction service",
    )
    config: VertexDeploymentConfig
    status: VertexServiceStatus = Field(
        default_factory=lambda: VertexServiceStatus()
    )
    _project_id: Optional[str] = PrivateAttr(default=None)
    _credentials: Optional[Any] = PrivateAttr(default=None)

    def _initialize_gcp_clients(self) -> None:
        """Initialize GCP clients with consistent credentials."""
        from zenml.integrations.gcp.model_deployers.vertex_model_deployer import (
            VertexModelDeployer,
        )

        model_deployer = cast(
            VertexModelDeployer, Client().active_stack.model_deployer
        )

        # Get credentials from model deployer
        self._credentials, self._project_id = (
            model_deployer._get_authentication()
        )

    def __init__(self, config: VertexDeploymentConfig, **attrs: Any):
        """Initialize the Vertex AI deployment service."""
        super().__init__(config=config, **attrs)
        self._initialize_gcp_clients()

    @property
    def prediction_url(self) -> Optional[str]:
        """The prediction URI exposed by the prediction service."""
        if not self.status.endpoint or not self.status.endpoint.endpoint_url:
            return None

        return f"https://{self.config.location}-aiplatform.googleapis.com/v1/{self.status.endpoint.endpoint_url}"

    def get_endpoints(self) -> List[aiplatform.Endpoint]:
        """Get all endpoints for the current project and location.

        Returns:
            List of Vertex AI endpoints
        """
        try:
            # Use proper filtering and pagination
            return list(
                aiplatform.Endpoint.list(
                    filter='labels.managed_by="zenml"',
                    location=self.config.location,
                    credentials=self._credentials,
                )
            )
        except Exception as e:
            logger.error(f"Failed to list endpoints: {e}")
            return []

    def _generate_endpoint_name(self) -> str:
        """Generate a unique name for the Vertex AI Inference Endpoint.

        Returns:
            Generated endpoint name
        """
        from zenml.integrations.gcp.model_deployers.vertex_model_deployer import (
            VertexModelDeployer,
        )

        # Include tenant ID in name for multi-tenancy support
        model_deployer = cast(
            VertexModelDeployer, Client().active_stack.model_deployer
        )

        # Make name more descriptive and conformant
        sanitized_model_name = sanitize_vertex_label(self.config.model_name)
        return f"{sanitized_model_name}-{model_deployer.id}-{str(self.uuid)[:UUID_SLICE_LENGTH]}"

    def _get_model_id(self, name: str) -> str:
        """Helper to construct a full model ID from a given model name."""
        return f"projects/{self._project_id}/locations/{self.config.location}/models/{name}"

    def _verify_model_exists(self) -> aiplatform.Model:
        """Verify the model exists and return it.

        Returns:
            Vertex AI Model instance

        Raises:
            RuntimeError: If model not found
        """
        try:
            model = aiplatform.Model(
                model_name=self._get_model_id(self.config.model_name),
                location=self.config.location,
                credentials=self._credentials,
            )
            logger.info(f"Found model to deploy: {model.resource_name}")
            return model
        except exceptions.NotFound:
            raise RuntimeError(
                f"Model {self._get_model_id(self.config.model_name)} not found in project {self._project_id}"
            )

    def _deploy_model(self) -> Any:
        """Deploy model to Vertex AI endpoint."""
        # Initialize endpoint
        if self.config.existing_endpoint:
            endpoint = aiplatform.Endpoint(
                endpoint_name=self.config.existing_endpoint,
                project=self._project_id,
                location=self.config.location,
                credentials=self._credentials,
            )
        else:
            endpoint = aiplatform.Endpoint.create(
                display_name=self.config.name,
                project=self._project_id,
                location=self.config.location,
                credentials=self._credentials,
                labels=self.config.get_vertex_deployment_labels(),
            )

        # Prepare deployment configuration
        deploy_kwargs = {
            "model_display_name": self.config.model_name,
            "deployed_model_display_name": self.config.name,
            "sync": False,
        }

        # Add container configuration if specified
        if self.config.container:
            deploy_kwargs.update(
                {
                    "container_image_uri": self.config.container.image_uri,
                    "container_ports": self.config.container.ports,
                    "container_predict_route": self.config.container.predict_route,
                    "container_health_route": self.config.container.health_route,
                    "container_env": self.config.container.env,
                }
            )

        # Add resource configuration if specified
        if self.config.resources:
            deploy_kwargs.update(
                {
                    "machine_type": self.config.resources.machine_type,
                    "min_replica_count": self.config.resources.min_replica_count,
                    "max_replica_count": self.config.resources.max_replica_count,
                    "accelerator_type": self.config.resources.accelerator_type,
                    "accelerator_count": self.config.resources.accelerator_count,
                }
            )

        # Add explanation configuration if specified
        if self.config.explanation:
            deploy_kwargs.update(
                {
                    "explanation_metadata": self.config.explanation.metadata,
                    "explanation_parameters": self.config.explanation.parameters,
                }
            )

        # Add service account if specified
        if self.config.service_account:
            deploy_kwargs["service_account"] = self.config.service_account

        # Add network configuration if specified
        if self.config.network:
            deploy_kwargs["network"] = self.config.network

        # Add encryption key if specified
        if self.config.encryption_spec_key_name:
            deploy_kwargs["encryption_spec_key_name"] = (
                self.config.encryption_spec_key_name
            )

        # Deploy model
        operation = endpoint.deploy(**deploy_kwargs)
        return operation

    def provision(self) -> None:
        """Provision or update remote Vertex AI deployment instance."""
        try:
            # First verify model exists
            model = self._verify_model_exists()

            # Get or create endpoint
            if self.config.existing_endpoint:
                endpoint = aiplatform.Endpoint(
                    endpoint_name=self.config.existing_endpoint,
                    location=self.config.location,
                    credentials=self._credentials,
                )
                logger.info(
                    f"Using existing endpoint: {endpoint.resource_name}"
                )
            else:
                endpoint_name = self._generate_endpoint_name()
                endpoint = aiplatform.Endpoint.create(
                    display_name=endpoint_name,
                    location=self.config.location,
                    encryption_spec_key_name=self.config.encryption_spec_key_name,
                    labels=self.config.get_vertex_deployment_labels(),
                    credentials=self._credentials,
                )
                logger.info(f"Created new endpoint: {endpoint.resource_name}")

            # Deploy model with retries for transient errors
            try:
                deploy_op = self._deploy_model()

                # Wait for deployment
                deploy_op.result(timeout=POLLING_TIMEOUT)

                logger.info(
                    f"Model {model.resource_name} deployed to endpoint {endpoint.resource_name}"
                )
            except Exception as e:
                self.status.update_state(
                    ServiceState.ERROR, f"Deployment failed: {str(e)}"
                )
                raise

            # Update status
            self.status.endpoint = VertexPredictionServiceEndpoint(
                endpoint_name=endpoint.resource_name,
                endpoint_url=endpoint.resource_name,
                deployed_model_id=model.resource_name,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                state="DEPLOYED",
            )
            self.status.update_state(ServiceState.ACTIVE)

            logger.info(
                f"Deployment completed successfully. "
                f"Endpoint: {endpoint.resource_name}"
            )

        except Exception as e:
            error_msg = f"Failed to provision deployment: {str(e)}"
            logger.error(error_msg)
            self.status.update_state(ServiceState.ERROR, error_msg)
            raise RuntimeError(error_msg)

    def deprovision(self, force: bool = False) -> None:
        """Deprovision the Vertex AI deployment.

        Args:
            force: Whether to force deprovision
        """
        if not self.status.endpoint:
            logger.warning("No endpoint to deprovision")
            return

        try:
            endpoint = aiplatform.Endpoint(
                endpoint_name=self.status.endpoint.endpoint_name,
                location=self.config.location,
                credentials=self._credentials,
            )

            # Undeploy model
            endpoint.undeploy_all()

            # Delete endpoint if we created it
            if not self.config.existing_endpoint:
                endpoint.delete()

            logger.info(f"Deprovisioned endpoint: {endpoint.resource_name}")

            self.status.endpoint = None
            self.status.update_state(ServiceState.INACTIVE)

        except Exception as e:
            error_msg = f"Failed to deprovision deployment: {str(e)}"
            if not force:
                logger.error(error_msg)
                self.status.update_state(ServiceState.ERROR, error_msg)
                raise RuntimeError(error_msg)
            else:
                logger.warning(
                    f"Error during forced deprovision (ignoring): {error_msg}"
                )
                self.status.update_state(ServiceState.INACTIVE)

    def start_deployment(
        self, timeout: int = POLLING_TIMEOUT
    ) -> aiplatform.Endpoint:
        """Start the Vertex AI deployment and wait until it's ready.

        This method initiates the deployment (via a helper, e.g. _deploy_model()) and then
        blocks until the underlying operation is completed using wait().

        Args:
            timeout: Maximum time (in seconds) to wait for deployment readiness.

        Returns:
            The deployed Vertex AI Endpoint object.

        Raises:
            RuntimeError: If the deployment operation fails.
        """
        try:
            # _deploy_model() is assumed to initiate deployment and return an operation object.
            # The operation object has a wait() method.
            operation = (
                self._deploy_model()
            )  # <-- your deployment call; adjust as needed
            logger.info(
                "Deployment operation initiated. Waiting for deployment to be ready..."
            )
            operation.wait(timeout=timeout)

            # After waiting, retrieve the endpoint object.
            endpoint = aiplatform.Endpoint(
                endpoint_name=operation.resource.name,
                location=self.config.location,
                credentials=self._credentials,
            )

            self.status.endpoint = endpoint
            self.status.update_state(ServiceState.ACTIVE)
            logger.info(
                f"Deployment is ready at endpoint: {endpoint.resource_name}"
            )
            return endpoint
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            self.status.update_state(ServiceState.ERROR, str(e))
            raise RuntimeError(f"Deployment failed: {e}")

    def get_logs(
        self,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Retrieve logs for the Vertex AI deployment (not supported).

        Yields:
            Log entries as strings, but logs are not supported for Vertex AI.
        """
        logger.warning("Logs are not supported for Vertex AI")
        yield from ()

    def check_status(self) -> None:
        """Check the status of the deployment (no-op implementation)."""
        return

    @property
    def is_running(self) -> bool:
        """Check if the service is running."""
        self.update_status()
        return self.status.state == ServiceState.ACTIVE
