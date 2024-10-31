"""Implementation of the Vertex AI Deployment service."""

import re
from typing import Any, Dict, Generator, List, Optional, Tuple

from google.api_core import exceptions
from google.cloud import aiplatform
from pydantic import BaseModel, Field

from zenml.client import Client
from zenml.integrations.gcp.flavors.vertex_model_deployer_flavor import (
    VertexBaseConfig,
)
from zenml.logger import get_logger
from zenml.services import ServiceState, ServiceStatus, ServiceType
from zenml.services.service import BaseDeploymentService, ServiceConfig

logger = get_logger(__name__)

# Increase timeout for long-running operations
POLLING_TIMEOUT = (
    1800  # Increased from 1200 to allow for longer deployment times
)
UUID_SLICE_LENGTH: int = 8


def sanitize_labels(labels: Dict[str, str]) -> None:
    """Update the label values to be valid Kubernetes labels.

    See:
    https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#syntax-and-character-set

    Args:
        labels: the labels to sanitize.
    """
    for key, value in labels.items():
        # Kubernetes labels must be alphanumeric, no longer than
        # 63 characters, and must begin and end with an alphanumeric
        # character ([a-z0-9A-Z])
        labels[key] = re.sub(r"[^0-9a-zA-Z-_\.]+", "_", value)[:63].strip(
            "-_."
        )


def sanitize_vertex_label(value: str) -> str:
    """Sanitize a label value to comply with Vertex AI requirements.

    Args:
        value: The label value to sanitize

    Returns:
        Sanitized label value
    """
    # Convert to lowercase
    value = value.lower()
    # Replace any character that's not lowercase letter, number, dash or underscore
    value = re.sub(r"[^a-z0-9\-_]", "-", value)
    # Ensure it starts with a letter/number by prepending 'x' if needed
    if not value[0].isalnum():
        value = f"x{value}"
    # Truncate to 63 chars to stay under limit
    return value[:63]


class VertexAIDeploymentConfig(VertexBaseConfig, ServiceConfig):
    """Vertex AI service configurations."""

    def get_vertex_deployment_labels(self) -> Dict[str, str]:
        """Generate labels for the VertexAI deployment from the service configuration."""
        labels = {
            "managed-by": "zenml",  # Changed from managed_by to managed-by
        }

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
    endpoint_url: Optional[str] = None
    deployed_model_id: Optional[str] = (
        None  # Added to track specific model deployment
    )


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
    config: VertexAIDeploymentConfig
    status: VertexServiceStatus = Field(
        default_factory=lambda: VertexServiceStatus()
    )

    def __init__(self, config: VertexAIDeploymentConfig, **attrs: Any):
        """Initialize the Vertex AI deployment service."""
        super().__init__(config=config, **attrs)

        # Initialize aiplatform with project and location
        from zenml.integrations.gcp.model_deployers.vertex_model_deployer import (
            VertexModelDeployer,
        )

        zenml_client = Client()
        model_deployer = zenml_client.active_stack.model_deployer
        if not isinstance(model_deployer, VertexModelDeployer):
            raise ValueError("Model deployer is not VertexModelDeployer")

        model_deployer.setup_aiplatform()

    @property
    def prediction_url(self) -> Optional[str]:
        """The prediction URI exposed by the prediction service."""
        if not self.status.endpoint or not self.status.endpoint.endpoint_url:
            return None

        # Construct proper prediction URL
        return f"https://{self.config.location}-aiplatform.googleapis.com/v1/{self.status.endpoint.endpoint_url}"

    def get_endpoints(self) -> List[aiplatform.Endpoint]:
        """Get all endpoints for the current project and location."""
        try:
            # Use proper filtering and pagination
            return list(
                aiplatform.Endpoint.list(
                    filter='labels.managed_by="zenml"',
                    location=self.config.location,
                )
            )
        except Exception as e:
            logger.error(f"Failed to list endpoints: {e}")
            return []

    def _generate_endpoint_name(self) -> str:
        """Generate a unique name for the Vertex AI Inference Endpoint."""
        # Make name more descriptive and conformant to Vertex AI naming rules
        sanitized_model_name = re.sub(
            r"[^a-zA-Z0-9-]", "-", self.config.model_name.lower()
        )
        return f"{sanitized_model_name}-{str(self.uuid)[:UUID_SLICE_LENGTH]}"

    def provision(self) -> None:
        """Provision or update remote Vertex AI deployment instance."""
        try:
            if self.config.existing_endpoint:
                # Use the existing endpoint
                endpoint = aiplatform.Endpoint(
                    endpoint_name=self.config.existing_endpoint,
                    location=self.config.location,
                )
                logger.info(
                    f"Using existing Vertex AI inference endpoint: {endpoint.resource_name}"
                )
            else:
                # Create the endpoint
                endpoint_name = self._generate_endpoint_name()
                endpoint = aiplatform.Endpoint.create(
                    display_name=endpoint_name,
                    location=self.config.location,
                    encryption_spec_key_name=self.config.encryption_spec_key_name,
                    labels=self.config.get_vertex_deployment_labels(),
                )
                logger.info(
                    f"Vertex AI inference endpoint created: {endpoint.resource_name}"
                )

            # Then get the model
            model = aiplatform.Model(
                model_name=self.config.model_id,
                location=self.config.location,
            )
            logger.info(
                f"Found existing model to deploy: {model.resource_name} to the endpoint."
            )

            # Deploy the model to the endpoint
            endpoint.deploy(
                model=model,
                deployed_model_display_name=f"{endpoint_name}-deployment",
                machine_type=self.config.machine_type,
                min_replica_count=self.config.min_replica_count,
                max_replica_count=self.config.max_replica_count,
                accelerator_type=self.config.accelerator_type,
                accelerator_count=self.config.accelerator_count,
                service_account=self.config.service_account,
                explanation_metadata=self.config.explanation_metadata,
                explanation_parameters=self.config.explanation_parameters,
                sync=self.config.sync,
            )
            logger.info(
                f"Model {model.resource_name} successfully deployed to endpoint {endpoint.resource_name}"
            )

            # Store both endpoint and deployment information
            self.status.endpoint = VertexPredictionServiceEndpoint(
                endpoint_name=endpoint.resource_name,
                endpoint_url=endpoint.resource_name,
                deployed_model_id=model.resource_name,
            )
            self.status.update_state(ServiceState.PENDING_STARTUP)

            logger.info(
                f"Vertex AI inference endpoint successfully deployed. Pending startup"
                f"Endpoint: {endpoint.resource_name}, "
            )

        except Exception as e:
            self.status.update_state(
                new_state=ServiceState.ERROR,
                error=f"Deployment failed: {str(e)}",
            )
            raise RuntimeError(
                f"An error occurred while provisioning the Vertex AI inference endpoint: {e}"
            )

    def deprovision(self, force: bool = False) -> None:
        """Deprovision the remote Vertex AI deployment instance."""
        if not self.status.endpoint:
            return

        try:
            endpoint = aiplatform.Endpoint(
                endpoint_name=self.status.endpoint.endpoint_name,
                location=self.config.location,
            )

            # First undeploy the specific model if we have its ID
            if self.status.endpoint.deployed_model_id:
                try:
                    endpoint.undeploy(
                        deployed_model_id=self.status.endpoint.deployed_model_id,
                        sync=self.config.sync,
                    )
                except exceptions.NotFound:
                    logger.warning("Deployed model already undeployed")

            # Then delete the endpoint
            endpoint.delete(force=force, sync=self.config.sync)

            self.status.endpoint = None
            self.status.update_state(ServiceState.INACTIVE)

            logger.info("Vertex AI Inference Endpoint has been deprovisioned.")

        except exceptions.NotFound:
            logger.warning(
                "Vertex AI Inference Endpoint not found. It may have been already deleted."
            )
            self.status.update_state(ServiceState.INACTIVE)
        except Exception as e:
            error_msg = (
                f"Failed to deprovision Vertex AI Inference Endpoint: {e}"
            )
            logger.error(error_msg)
            if not force:
                raise RuntimeError(error_msg)

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the current operational state of the Vertex AI deployment."""
        if not self.status.endpoint:
            return ServiceState.INACTIVE, "Endpoint not provisioned"
        try:
            logger.info(
                f"Checking status of Vertex AI Inference Endpoint: {self.status.endpoint.endpoint_name}"
            )
            endpoint = aiplatform.Endpoint(
                endpoint_name=self.status.endpoint.endpoint_name,
                location=self.config.location,
            )

            # Get detailed deployment status
            deployment = None
            if self.status.endpoint.deployed_model_id:
                deployments = [
                    d
                    for d in endpoint.list_models()
                    if d.model == self.status.endpoint.deployed_model_id
                ]
                if deployments:
                    deployment = deployments[0]
                    logger.info(
                        f"Model {self.status.endpoint.deployed_model_id} was deployed to the endpoint"
                    )

            if not deployment:
                logger.warning(
                    "No matching deployment found, endpoint may be inactive or failed to deploy"
                )
                return ServiceState.INACTIVE, "No matching deployment found"

            return ServiceState.ACTIVE, "Deployment is ready"

        except exceptions.NotFound:
            return ServiceState.INACTIVE, "Endpoint not found"
        except Exception as e:
            return ServiceState.ERROR, f"Error checking status: {str(e)}"

    def predict(self, instances: List[Any]) -> List[Any]:
        """Make a prediction using the service."""
        if not self.is_running:
            raise Exception(
                "Vertex AI endpoint inference service is not running. "
                "Please start the service before making predictions."
            )

        if not self.status.endpoint:
            raise Exception("Endpoint information is missing.")

        try:
            endpoint = aiplatform.Endpoint(
                endpoint_name=self.status.endpoint.endpoint_name,
                location=self.config.location,
            )

            # Add proper prediction parameters and handle sync/async
            predictions = endpoint.predict(
                instances=instances,
                deployed_model_id=self.status.endpoint.deployed_model_id.split(
                    "/"
                )[-1],
                timeout=30,  # Add reasonable timeout
            )

            if not predictions:
                raise RuntimeError("No predictions returned")

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise RuntimeError(f"Prediction failed: {str(e)}")

        return [predictions]

    def get_logs(
        self, follow: bool = False, tail: Optional[int] = None
    ) -> Generator[str, bool, None]:
        """Retrieve the service logs."""
        # Note: Could be enhanced to actually fetch logs from Cloud Logging
        logger.info(
            "Vertex AI Endpoints provides access to the logs through "
            "Cloud Logging. Please check the Google Cloud Console for detailed logs. "
            f"Location: {self.config.location}"
        )
        yield "Logs are available in Google Cloud Console."

    @property
    def is_running(self) -> bool:
        """Check if the service is running."""
        self.update_status()
        return self.status.state == ServiceState.ACTIVE
