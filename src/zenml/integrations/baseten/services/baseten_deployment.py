"""Implementation of the Baseten deployment service."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import requests

from zenml.services import (
    BaseService,
    ServiceConfig,
    ServiceState,
    ServiceStatus,
    ServiceType,
)
from zenml.services.service import BaseService, ServiceConfig, ServiceStatus
from zenml.services.service_endpoint import (
    BaseServiceEndpoint,
    ServiceEndpointConfig,
    ServiceEndpointProtocol,
    ServiceEndpointStatus,
)
from zenml.services.service_status import ServiceState

logger = logging.getLogger(__name__)

BASETEN_SERVICE_TYPE = ServiceType(
    name="baseten",
    type="model-serving",
    flavor="baseten",
    description="Baseten model deployment service",
)

BASETEN_PREDICTION_URL_PATH = "predict"


class BasetenDeploymentConfig(ServiceConfig):
    """Configuration for a Baseten deployment.

    Attributes:
        model_name: The name of the model.
        model_uri: The URI of the model (Truss directory).
        model_type: The type of model (e.g., sklearn, pytorch).
        model_id: The ID of the model in Baseten (set after deployment).
        deployment_id: The ID of the deployment in Baseten (set after deployment).
        pipeline_name: The name of the pipeline that created the model.
        run_name: The name of the run that created the model.
        pipeline_step_name: The name of the step that created the model.
        root_runtime_path: The root path for runtime files.
    """

    model_name: str
    model_uri: str
    model_type: str
    model_id: Optional[str] = None
    deployment_id: Optional[str] = None
    pipeline_name: Optional[str] = None
    run_name: Optional[str] = None
    pipeline_step_name: Optional[str] = None
    root_runtime_path: Optional[str] = None


class BasetenEndpointConfig(ServiceEndpointConfig):
    """Config for the Baseten endpoint."""

    prediction_url_path: str = "/predict"


class BasetenEndpointStatus(ServiceEndpointStatus):
    """Status for the Baseten endpoint."""

    base_url: Optional[str] = None

    @property
    def uri(self) -> Optional[str]:
        """Get the URI of the service endpoint.

        Returns:
            The URI of the service endpoint or None.
        """
        return self.base_url


class BasetenEndpoint(BaseServiceEndpoint):
    """Endpoint for Baseten deployments."""

    config: BasetenEndpointConfig
    status: BasetenEndpointStatus

    def get_url(self) -> str:
        """Get the URL for the endpoint."""
        if not self.status.uri:
            return ""
        return f"{self.status.uri}{self.config.prediction_url_path}"


class BasetenDeploymentStatus(ServiceStatus):
    """Status of a Baseten deployment."""

    def __init__(self) -> None:
        """Initialize the status."""
        super().__init__(state=ServiceState.INACTIVE)


class BasetenDeploymentService(BaseService):
    """Service for Baseten deployments."""

    SERVICE_TYPE = BASETEN_SERVICE_TYPE

    # Define model fields
    model_id: str
    deployment_id: str

    def __init__(
        self,
        config: ServiceConfig,
        model_id: str,
        deployment_id: str,
        **kwargs: Any,
    ) -> None:
        """Initialize the service.

        Args:
            config: The service configuration.
            model_id: The ID of the deployed model.
            deployment_id: The ID of the deployment.
            **kwargs: Additional keyword arguments.
        """
        # Initialize endpoint with status
        endpoint_config = BasetenEndpointConfig(prediction_url_path="/predict")
        endpoint_status = BasetenEndpointStatus(
            state=ServiceState.ACTIVE,
            last_error="",
            last_update=None,
            protocol=ServiceEndpointProtocol.HTTPS,
            hostname=None,
            port=None,
            base_url=None,
        )
        endpoint = BasetenEndpoint(
            config=endpoint_config, status=endpoint_status
        )

        # Initialize service status
        status = ServiceStatus(
            state=ServiceState.ACTIVE, last_error="", last_update=None
        )

        # Get the UUID from kwargs
        uuid_value = kwargs.get("id", "00000000-0000-0000-0000-000000000000")
        if isinstance(uuid_value, str):
            uuid_value = UUID(uuid_value)

        # Call parent's init with all required fields
        super().__init__(
            config=config,
            endpoint=endpoint,
            status=status,
            uuid=uuid_value,
            model_id=model_id,
            deployment_id=deployment_id,
            **kwargs,
        )

    def get_healthcheck_url(self) -> Optional[str]:
        """Get the healthcheck URL for the service.

        Returns:
            The healthcheck URL.
        """
        return None  # Baseten doesn't provide a healthcheck URL

    def get_prediction_url(self) -> Optional[str]:
        """Get the prediction URL for the service.

        Returns:
            The prediction URL.
        """
        return self.endpoint.get_url()

    def get_logs(self) -> List[str]:
        """Get logs for the service.

        Returns:
            A list of log messages.
        """
        return []

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the status of the service.

        Returns:
            A tuple containing the current state and any error message.
        """
        # For now, we just return a fixed status
        # In a real implementation, we would check the Baseten API
        # to get the actual status of the deployment
        return ServiceState.ACTIVE, ""

    def start(self, timeout: Optional[float] = None) -> None:
        """Start the service.

        Args:
            timeout: The timeout in seconds.
        """
        # Check if we have the required model and deployment IDs
        if not self.model_id or not self.deployment_id:
            logger.warning(
                "Service started without model_id or deployment_id. "
                "Some functionality may be limited."
            )
            return

        # Set up the endpoint URI
        if self.model_id:
            base_url = (
                f"https://model-{self.model_id}.api.baseten.co/production"
            )
            if isinstance(self.endpoint.status, BasetenEndpointStatus):
                self.endpoint.status.base_url = base_url
            logger.info(f"Endpoint URI set to: {base_url}")
        else:
            logger.warning("No model_id available, endpoint URI not set.")

    def stop(self, timeout: int = 300, force: bool = False) -> None:
        """Stop the service.

        Args:
            timeout: The timeout in seconds.
            force: Whether to force stop.
        """
        logger.info(
            f"Stopping service {self.uuid} (timeout={timeout}s, force={force})"
        )
        # The service is stopped by the model deployer
        self.status.state = ServiceState.INACTIVE
        logger.info(f"Service {self.uuid} is now inactive")

    def predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make predictions using the deployed model.

        Args:
            data: The data to make predictions on.

        Returns:
            The predictions.

        Raises:
            RuntimeError: If the service is not active or prediction fails.
        """
        logger.info(f"Making prediction with service {self.uuid}")

        if self.status.state != ServiceState.ACTIVE:
            error_msg = f"Cannot predict: service {self.uuid} is not active"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        prediction_url = self.get_prediction_url()
        if not prediction_url:
            error_msg = f"Cannot predict: no prediction URL available for service {self.uuid}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            logger.debug(f"Sending prediction request with data: {data}")
            response = requests.post(prediction_url, json=data)
            response.raise_for_status()
            predictions = response.json()
            logger.info("Prediction successful")
            logger.debug(f"Received predictions: {predictions}")
            return predictions
        except Exception as e:
            error_msg = f"Prediction failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
