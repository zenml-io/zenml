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
from typing import Any, Dict, Generator, List, Optional, Tuple, cast

from google.api_core import retry
from google.cloud import aiplatform
from pydantic import Field, PrivateAttr

from zenml.client import Client
from zenml.integrations.gcp.flavors.vertex_base_config import (
    VertexAIEndpointConfig,
)
from zenml.logger import get_logger
from zenml.services import ServiceState, ServiceStatus, ServiceType
from zenml.services.service import BaseDeploymentService, ServiceConfig
from zenml.services.service_endpoint import (
    BaseServiceEndpoint,
    ServiceEndpointConfig,
)

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
        if self.display_name:
            labels["display-name"] = sanitize_vertex_label(
                self.display_name
            ) or sanitize_vertex_label(self.name)
        return labels


class VertexPredictionServiceEndpointConfig(ServiceEndpointConfig):
    """Vertex AI Prediction Service Endpoint."""

    endpoint_name: Optional[str] = None
    deployed_model_id: Optional[str] = None
    endpoint_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    state: Optional[str] = None


class VertexServiceStatus(ServiceStatus):
    """Vertex AI service status."""


class VertexPredictionServiceEndpoint(BaseServiceEndpoint):
    """Vertex AI Prediction Service Endpoint."""

    config: VertexPredictionServiceEndpointConfig


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
        endpoints = self.get_endpoints()
        if not endpoints:
            return None
        endpoint = endpoints[0]
        return f"https://{self.config.location}-aiplatform.googleapis.com/v1/{endpoint.resource_name}"

    def get_endpoints(self) -> List[aiplatform.Endpoint]:
        """Get all endpoints for the current project and location.

        Returns:
            List of Vertex AI endpoints
        """
        try:
            # Use proper filtering and pagination
            display_name = self.config.name or self.config.display_name
            assert display_name is not None
            display_name = sanitize_vertex_label(display_name)
            return list(
                aiplatform.Endpoint.list(
                    filter=f"labels.managed_by=zenml AND labels.display-name={display_name}",
                    project=self._project_id,
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
        # Make name more descriptive and conformant
        sanitized_model_name = sanitize_vertex_label(
            self.config.display_name or self.config.name
        )
        return f"{sanitized_model_name}-{str(self.uuid)[:UUID_SLICE_LENGTH]}"

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
        if self.config.model_name.startswith("projects/"):
            model_name = self.config.model_name
        else:
            model_name = self._get_model_id(self.config.model_name)
        # Remove version suffix if present
        if "@" in model_name:
            model_name = model_name.split("@")[0]
        logger.info(f"Model name: {model_name}")
        logger.info(f"Project ID: {self._project_id}")
        logger.info(f"Location: {self.config.location}")
        logger.info(f"Credentials: {self._credentials}")
        model = aiplatform.Model(
            model_name=model_name,
            project=self._project_id,
            location=self.config.location,
            credentials=self._credentials,
        )
        logger.info(f"Found model to deploy: {model.resource_name}")
        return model

    def _deploy_model(
        self, model: aiplatform.Model, endpoint: aiplatform.Endpoint
    ) -> None:
        """Deploy model to Vertex AI endpoint."""
        # Prepare deployment configuration
        deploy_kwargs = {
            "model": model,
            "deployed_model_display_name": self.config.display_name
            or self.config.name,
            "traffic_percentage": 100,
            "sync": False,
        }
        logger.info(
            f"Deploying model to endpoint with kwargs: {deploy_kwargs}"
        )
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
        logger.info(
            f"Deploying model to endpoint with kwargs: {deploy_kwargs}"
        )
        endpoint.deploy(**deploy_kwargs)

    def provision(self) -> None:
        """Provision or update remote Vertex AI deployment instance."""
        # First verify model exists
        model = self._verify_model_exists()
        logger.info(f"Found model to deploy: {model.resource_name}")

        # Get or create endpoint
        if self.config.existing_endpoint:
            endpoint = aiplatform.Endpoint(
                endpoint_name=self.config.existing_endpoint,
                location=self.config.location,
                credentials=self._credentials,
            )
            logger.info(f"Using existing endpoint: {endpoint.resource_name}")
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
            self._deploy_model(model, endpoint)

            logger.info(
                f"Model {model.resource_name} deployed to endpoint {endpoint.resource_name}"
            )
        except Exception as e:
            self.status.update_state(
                ServiceState.ERROR, f"Deployment failed: {str(e)}"
            )
            raise

        self.status.update_state(ServiceState.ACTIVE)

        logger.info(
            f"Deployment completed successfully. "
            f"Endpoint: {endpoint.resource_name}"
        )

    def deprovision(self, force: bool = False) -> None:
        """Deprovision the Vertex AI deployment.

        Args:
            force: Whether to force deprovision
        """
        endpoints = self.get_endpoints()
        if endpoints:
            try:
                endpoint = endpoints[0]
                endpoint.undeploy_all()
                endpoint.delete()
                logger.info(
                    f"Deprovisioned endpoint: {endpoint.resource_name}"
                )
                self.status.update_state(ServiceState.INACTIVE)
            except Exception as e:
                logger.error(f"Failed to deprovision endpoint: {e}")
                self.status.update_state(
                    ServiceState.ERROR, f"Failed to deprovision endpoint: {e}"
                )
        else:
            try:
                endpoint = aiplatform.Endpoint(
                    endpoint_name=self._generate_endpoint_name(),
                    location=self.config.location,
                    credentials=self._credentials,
                )

                # Undeploy model
                endpoint.undeploy_all()

                # Delete endpoint if we created it
                if not self.config.existing_endpoint:
                    endpoint.delete()

                logger.info(
                    f"Deprovisioned endpoint: {endpoint.resource_name}"
                )

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

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the status of the deployment by validating if an endpoint exists and if it has deployed models.

        Returns:
            A tuple containing the deployment's state and a status message.
        """
        try:
            endpoints = self.get_endpoints()
            if not endpoints:
                return ServiceState.INACTIVE, "No endpoint found."

            endpoint = endpoints[0]
            deployed_models = []
            if hasattr(endpoint, "list_models"):
                try:
                    deployed_models = endpoint.list_models()
                except Exception as e:
                    logger.warning(f"Failed to list models for endpoint: {e}")
            elif hasattr(endpoint, "deployed_models"):
                deployed_models = endpoint.deployed_models or []

            if deployed_models and len(deployed_models) > 0:
                return ServiceState.ACTIVE, ""
            else:
                return (
                    ServiceState.PENDING_STARTUP,
                    "Endpoint deployment is in progress.",
                )
        except Exception as e:
            return ServiceState.ERROR, f"Deployment check failed: {e}"

    @property
    def is_running(self) -> bool:
        """Check if the service is running."""
        self.update_status()
        return self.status.state == ServiceState.ACTIVE
