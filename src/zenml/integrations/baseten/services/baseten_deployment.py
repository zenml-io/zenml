"""Implementation of the Baseten deployment service."""

import logging
from typing import Any, Dict, List, Optional, Tuple, cast, Union, Generator
from uuid import UUID
import os

import requests
from pydantic import ConfigDict, computed_field

from zenml.models import ServiceResponse
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
        name: The name of the model.
        uri: The URI of the model (Truss directory).
        framework: The framework/type of the model (e.g., sklearn).
        baseten_id: The ID of the model in Baseten (set after deployment).
        baseten_deployment_id: The ID of the deployment in Baseten (set after deployment).
        pipeline_name: The name of the pipeline that created the model.
        run_name: The name of the run that created the model.
        pipeline_step_name: The name of the step that created the model.
        root_runtime_path: The root path for runtime files.
        service_name: The name of the service.
    """

    name: str
    uri: str
    framework: str = "sklearn"
    baseten_id: Optional[str] = None
    baseten_deployment_id: Optional[str] = None
    pipeline_name: Optional[str] = None
    run_name: Optional[str] = None
    pipeline_step_name: Optional[str] = None
    root_runtime_path: Optional[str] = None
    service_name: Optional[str] = None

    # Disable all protected namespaces to avoid conflicts
    model_config = ConfigDict(protected_namespaces=())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BasetenDeploymentConfig":
        """Create a config instance from a dictionary.

        Args:
            data: The dictionary to create the config from.

        Returns:
            The created config instance.

        Raises:
            ValueError: If required fields are missing.
        """
        # Create a copy to avoid modifying the input
        data = data.copy()

        # Remove type field if present
        data.pop("type", None)

        # Handle legacy field names
        field_mappings = {
            "model_name": "name",
            "model_uri": "uri",
            "model_type": "framework",
            "model_framework": "framework",
            "model_id": "baseten_id",
            "baseten_model_id": "baseten_id",
            "deployment_id": "baseten_deployment_id",
        }

        # Map legacy fields to new names
        for old_name, new_name in field_mappings.items():
            if old_name in data and new_name not in data:
                data[new_name] = data.pop(old_name)

        # Validate required fields
        required_fields = {"name", "uri"}
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        try:
            return cls(**data)
        except Exception as e:
            raise ValueError(f"Failed to create config from data: {e}") from e


class BasetenEndpointConfig(ServiceEndpointConfig):
    """Config for the Baseten endpoint.

    Attributes:
        prediction_url_path: URI subpath for prediction requests
        healthcheck_url_path: URI subpath for health check requests
    """

    prediction_url_path: str = "/predict"
    healthcheck_url_path: str = "/health"


class BasetenEndpointStatus(ServiceEndpointStatus):
    """Status for the Baseten endpoint.

    Attributes:
        base_url: The base URL of the endpoint
        prediction_url: The full prediction URL
        healthcheck_url: The full healthcheck URL
    """

    base_url: Optional[str] = None
    prediction_url: Optional[str] = None
    healthcheck_url: Optional[str] = None

    @property
    def uri(self) -> Optional[str]:
        """Get the URI of the service endpoint.

        Returns:
            The URI of the service endpoint or None.
        """
        return self.base_url

    @property
    def is_available(self) -> bool:
        """Check if the endpoint is available.

        Returns:
            True if the endpoint has a base URL, False otherwise.
        """
        return self.base_url is not None


class BasetenEndpoint(BaseServiceEndpoint):
    """Endpoint for Baseten deployments.

    Attributes:
        config: The endpoint configuration
        status: The endpoint status
    """

    config: BasetenEndpointConfig
    status: BasetenEndpointStatus

    def prepare_for_deployment(self, base_url: str) -> None:
        """Prepare the endpoint for deployment.

        Args:
            base_url: The base URL of the endpoint.
        """
        self.status.base_url = base_url
        self.status.prediction_url = (
            f"{base_url.rstrip('/')}{self.config.prediction_url_path}"
        )
        self.status.healthcheck_url = (
            f"{base_url.rstrip('/')}{self.config.healthcheck_url_path}"
        )

    def get_prediction_url(self) -> Optional[str]:
        """Get the prediction URL.

        Returns:
            The prediction URL or None if not available.
        """
        return self.status.prediction_url

    def get_healthcheck_url(self) -> Optional[str]:
        """Get the healthcheck URL.

        Returns:
            The healthcheck URL or None if not available.
        """
        return self.status.healthcheck_url


class BasetenDeploymentService(BaseService):
    """Service for Baseten deployments."""

    SERVICE_TYPE = BASETEN_SERVICE_TYPE

    config: BasetenDeploymentConfig
    endpoint: BasetenEndpoint

    @property
    def is_running(self) -> bool:
        """Check if the service is running.

        Returns:
            True if the service is running, False otherwise.
        """
        try:
            state, _ = self.check_status()
            return state == ServiceState.ACTIVE
        except Exception as e:
            logger.warning(f"Failed to check service status: {e}")
            return False

    @property
    def prediction_url(self) -> Optional[str]:
        """Get the prediction URL for the service.

        Returns:
            The prediction URL or None if not available.
        """
        return self.endpoint.get_prediction_url() if self.endpoint else None

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the status of the service.

        Returns:
            A tuple of (ServiceState, error_message).
        """
        if not self.config.baseten_id or not self.config.baseten_deployment_id:
            return (
                ServiceState.INACTIVE,
                "No Baseten model/deployment ID available",
            )

        try:
            # Get deployment status from Baseten API
            headers = {"Authorization": f"Api-Key {self._get_api_key()}"}
            url = f"https://app.baseten.co/api/v1/models/{self.config.baseten_id}/deployments/{self.config.baseten_deployment_id}"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            deployment = response.json()

            # Map Baseten status to ZenML ServiceState
            status_mapping = {
                "BUILDING": ServiceState.DEPLOYING,
                "DEPLOYING": ServiceState.DEPLOYING,
                "DEPLOY_FAILED": ServiceState.ERROR,
                "LOADING_MODEL": ServiceState.DEPLOYING,
                "ACTIVE": ServiceState.ACTIVE,
                "UNHEALTHY": ServiceState.ERROR,
                "BUILD_FAILED": ServiceState.ERROR,
                "BUILD_STOPPED": ServiceState.ERROR,
                "DEACTIVATING": ServiceState.INACTIVE,
                "INACTIVE": ServiceState.INACTIVE,
                "FAILED": ServiceState.ERROR,
                "UPDATING": ServiceState.DEPLOYING,
                "SCALED_TO_ZERO": ServiceState.INACTIVE,
                "WAKING_UP": ServiceState.DEPLOYING,
            }

            baseten_status = deployment.get("status", "FAILED")
            state = status_mapping.get(baseten_status, ServiceState.ERROR)
            error = f"Deployment status: {baseten_status}"

            # Update replica count information if available
            if "active_replica_count" in deployment:
                error += (
                    f" (active replicas: {deployment['active_replica_count']})"
                )

            return state, "" if state == ServiceState.ACTIVE else error

        except requests.RequestException as e:
            return (
                ServiceState.ERROR,
                f"Failed to check deployment status: {str(e)}",
            )

    def _get_api_key(self) -> str:
        """Get the Baseten API key from the config file.

        Returns:
            The API key.

        Raises:
            RuntimeError: If the API key is not found.
        """
        try:
            import configparser

            config = configparser.ConfigParser()
            config.read(os.path.expanduser("~/.trussrc"))
            return config["default"]["api_key"]
        except Exception as e:
            raise RuntimeError(f"Failed to get Baseten API key: {str(e)}")

    def start(self, timeout: int = 300) -> None:
        """Start the service.

        Args:
            timeout: The timeout in seconds.

        Note:
            In Baseten, models are automatically started when deployed.
            This method activates the deployment if it was deactivated.
        """
        if not self.config.baseten_id or not self.config.baseten_deployment_id:
            raise RuntimeError("No Baseten model/deployment ID available")

        try:
            # Call Baseten API to activate the deployment
            headers = {"Authorization": f"Api-Key {self._get_api_key()}"}
            url = f"https://app.baseten.co/api/v1/models/{self.config.baseten_id}/deployments/{self.config.baseten_deployment_id}/activate"
            response = requests.post(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            # Update service status
            state, error = self.check_status()
            self._update_status(state, error)
        except requests.RequestException as e:
            self._update_status(
                ServiceState.ERROR, f"Failed to start deployment: {str(e)}"
            )
            raise RuntimeError(f"Failed to start deployment: {str(e)}")

    def stop(self, timeout: int = 300, force: bool = False) -> None:
        """Stop the service.

        Args:
            timeout: The timeout in seconds.
            force: Whether to force stop the service.

        Note:
            In Baseten, this deactivates the deployment.
        """
        if not self.config.baseten_id or not self.config.baseten_deployment_id:
            raise RuntimeError("No Baseten model/deployment ID available")

        try:
            # Call Baseten API to deactivate the deployment
            headers = {"Authorization": f"Api-Key {self._get_api_key()}"}
            url = f"https://app.baseten.co/api/v1/models/{self.config.baseten_id}/deployments/{self.config.baseten_deployment_id}/deactivate"
            response = requests.post(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            # Update service status
            self._update_status(ServiceState.INACTIVE)
        except requests.RequestException as e:
            self._update_status(
                ServiceState.ERROR, f"Failed to stop deployment: {str(e)}"
            )
            raise RuntimeError(f"Failed to stop deployment: {str(e)}")

    def delete(self, timeout: int = 300, force: bool = False) -> None:
        """Delete the service.

        Args:
            timeout: The timeout in seconds.
            force: Whether to force delete the service.
        """
        if not self.config.baseten_id or not self.config.baseten_deployment_id:
            return

        try:
            # Call Baseten API to delete the deployment
            headers = {"Authorization": f"Api-Key {self._get_api_key()}"}
            url = f"https://app.baseten.co/api/v1/models/{self.config.baseten_id}/deployments/{self.config.baseten_deployment_id}"
            response = requests.delete(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            # Update service status
            self._update_status(ServiceState.TERMINATED)
        except requests.RequestException as e:
            self._update_status(
                ServiceState.ERROR, f"Failed to delete deployment: {str(e)}"
            )
            if not force:
                raise RuntimeError(f"Failed to delete deployment: {str(e)}")

    def predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a prediction using the service.

        Args:
            data: The input data for prediction.

        Returns:
            The prediction results.

        Raises:
            RuntimeError: If the service is not running or prediction fails.
        """
        if not self.is_running:
            raise RuntimeError("Service is not running")

        prediction_url = self.prediction_url
        if not prediction_url:
            raise RuntimeError("No prediction URL available")

        try:
            response = requests.post(prediction_url, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Prediction failed: {str(e)}")

    @classmethod
    def from_model(cls, model: ServiceResponse) -> "BasetenDeploymentService":
        """Create a service instance from a model response.

        Args:
            model: The model response to create the service from.

        Returns:
            The created service instance.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        try:
            # Ensure we have a valid UUID
            if not model.id:
                raise ValueError("Service ID is required")

            # Convert config to BasetenDeploymentConfig
            config = model.config
            if isinstance(config, dict):
                config = BasetenDeploymentConfig.from_dict(config)
            elif isinstance(config, ServiceConfig) and not isinstance(
                config, BasetenDeploymentConfig
            ):
                config = BasetenDeploymentConfig.from_dict(config.model_dump())

            # Create endpoint configuration
            endpoint_config = BasetenEndpointConfig()
            endpoint = BasetenEndpoint(
                config=endpoint_config,
                status=BasetenEndpointStatus(),
            )

            # Set up endpoint if we have the information
            if (
                model.endpoint
                and hasattr(model.endpoint, "status")
                and model.endpoint.status
                and hasattr(model.endpoint.status, "uri")
            ):
                endpoint.prepare_for_deployment(model.endpoint.status.uri)

            # Create service status with safe attribute access
            status = ServiceStatus(
                state=ServiceState(model.status.state)
                if model.status and hasattr(model.status, "state")
                else ServiceState.INACTIVE,
                last_error=model.status.last_error
                if model.status and hasattr(model.status, "last_error")
                else "",
                last_update=model.status.last_update
                if model.status and hasattr(model.status, "last_update")
                else None,
            )

            # Create service
            service = cls(
                id=model.id,
                config=config,
                endpoint=endpoint,
                status=status,
            )

            return service

        except Exception as e:
            # Add more context to the error
            raise ValueError(
                f"Failed to create BasetenDeploymentService from model response: {str(e)}"
            ) from e

    def get_logs(
        self,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get logs from the service.

        Args:
            follow: Whether to follow the logs.
            tail: Number of lines to get from the end of the logs.

        Returns:
            A generator that yields log lines.

        Note:
            Currently not implemented for Baseten as they don't expose logs via API.
        """
        logger.warning("Logs are not available for Baseten deployments")
        return iter([])
