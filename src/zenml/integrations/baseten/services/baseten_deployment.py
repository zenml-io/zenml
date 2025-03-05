"""Implementation of the Baseten deployment service."""

import logging
import os
import random
import time
from typing import Any, Dict, Generator, Optional, Tuple

import requests
from pydantic import ConfigDict

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

    @property
    def baseten_model_id(self) -> Optional[str]:
        """Get the Baseten model ID.

        Returns:
            The Baseten model ID or None if not available.
        """
        return self.config.baseten_id

    @property
    def deployment_id(self) -> Optional[str]:
        """Get the Baseten deployment ID.

        Returns:
            The Baseten deployment ID or None if not available.
        """
        return self.config.baseten_deployment_id

    def get_prediction_url(self) -> Optional[str]:
        """Get the prediction URL for the service.

        Returns:
            The prediction URL or None if not available.
        """
        return self.prediction_url

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
            api_key = self._get_api_key()
            api_host = "https://api.baseten.co"  # Use the API base URL
            headers = {"Authorization": f"Api-Key {api_key}"}
            url = f"{api_host}/v1/models/{self.config.baseten_id}/deployments/{self.config.baseten_deployment_id}"

            # Add retry logic with exponential backoff for API requests
            max_retries = 3
            retry_delay = 1  # starting delay in seconds
            last_exception = None

            for retry in range(max_retries):
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()
                    deployment = response.json()
                    break
                except requests.RequestException as e:
                    last_exception = e
                    if retry < max_retries - 1:
                        # Exponential backoff with jitter
                        sleep_time = retry_delay * (2**retry) + (
                            0.1 * random.random()
                        )
                        logger.warning(
                            f"API request failed, retrying in {sleep_time:.1f}s: {e}"
                        )
                        time.sleep(sleep_time)
                    else:
                        # All retries failed
                        return (
                            ServiceState.ERROR,
                            f"Failed to check deployment status after {max_retries} retries: {str(last_exception)}",
                        )

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

            # Build detailed status message
            status_details = [f"Deployment status: {baseten_status}"]

            # Include more deployment details if available
            if "active_replica_count" in deployment:
                status_details.append(
                    f"Active replicas: {deployment['active_replica_count']}"
                )

            if "desired_replica_count" in deployment:
                status_details.append(
                    f"Desired replicas: {deployment['desired_replica_count']}"
                )

            error = ", ".join(status_details)

            # Update the service status in ZenML
            current_state = self.status.state if self.status else None
            if current_state != state:
                self._update_status(
                    state, "" if state == ServiceState.ACTIVE else error
                )

            return state, "" if state == ServiceState.ACTIVE else error

        except Exception as e:
            error_msg = f"Failed to check deployment status: {str(e)}"
            self._update_status(ServiceState.ERROR, error_msg)
            return (ServiceState.ERROR, error_msg)

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

    def _get_api_host(self) -> str:
        """Get the Baseten API host from the config file.

        Returns:
            The API host, defaulting to https://app.baseten.co if not found.
        """
        try:
            import configparser

            config = configparser.ConfigParser()
            config.read(os.path.expanduser("~/.trussrc"))
            return config["default"].get(
                "remote_url", "https://app.baseten.co"
            )
        except Exception:
            # Default to standard Baseten URL if not found
            return "https://app.baseten.co"

    def start(self, timeout: int = 300) -> None:
        """Start the service.

        Args:
            timeout: The timeout in seconds.

        Note:
            In Baseten, models are automatically started when deployed.
            This method activates the deployment if it was deactivated.

        Raises:
            RuntimeError: If the service fails to start.
        """
        if not self.config.baseten_id or not self.config.baseten_deployment_id:
            raise RuntimeError("No Baseten model/deployment ID available")

        # Update status to DEPLOYING while we're starting
        self._update_status(ServiceState.DEPLOYING, "Activating deployment...")

        try:
            # Call Baseten API to activate the deployment
            api_key = self._get_api_key()
            api_host = "https://api.baseten.co"  # Use the API base URL
            headers = {"Authorization": f"Api-Key {api_key}"}
            url = f"{api_host}/v1/models/{self.config.baseten_id}/deployments/{self.config.baseten_deployment_id}/activate"
            response = requests.post(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Poll until the service is active or timeout
            logger.info(
                f"Waiting for deployment to become active (timeout: {timeout}s)..."
            )
            start_time = time.time()
            poll_interval = 5  # seconds

            while time.time() - start_time < timeout:
                state, error = self.check_status()

                if state == ServiceState.ACTIVE:
                    logger.info("Deployment is now active")
                    self._update_status(state, "")
                    return
                elif state == ServiceState.ERROR:
                    self._update_status(state, error)
                    raise RuntimeError(f"Failed to start deployment: {error}")
                else:
                    remaining = timeout - int(time.time() - start_time)
                    logger.info(
                        f"Deployment not active yet (state: {state}), waiting... ({remaining}s remaining)"
                    )
                    time.sleep(poll_interval)

            # If we get here, we timed out
            self._update_status(
                ServiceState.ERROR,
                f"Timed out waiting for deployment to become active after {timeout}s",
            )
            raise RuntimeError(
                f"Timed out waiting for deployment to become active after {timeout}s"
            )

        except requests.RequestException as e:
            error_msg = f"Failed to start deployment: {str(e)}"
            self._update_status(ServiceState.ERROR, error_msg)
            raise RuntimeError(error_msg)

    def stop(self, timeout: int = 300, force: bool = False) -> None:
        """Stop the service.

        Args:
            timeout: The timeout in seconds.
            force: Whether to force stop the service.

        Note:
            In Baseten, this deactivates the deployment.

        Raises:
            RuntimeError: If the service fails to stop and force=False.
        """
        if not self.config.baseten_id or not self.config.baseten_deployment_id:
            raise RuntimeError("No Baseten model/deployment ID available")

        # Only attempt to stop if the service is running or in an error state
        current_state = self.status.state if self.status else None
        if current_state not in [ServiceState.ACTIVE, ServiceState.ERROR]:
            logger.info(
                f"Service is already stopped or stopping (state: {current_state})"
            )
            return

        # Update status to show we're stopping
        self._update_status(
            ServiceState.STOPPING, "Deactivating deployment..."
        )

        try:
            # Call Baseten API to deactivate the deployment
            api_key = self._get_api_key()
            api_host = "https://api.baseten.co"  # Use the API base URL
            headers = {"Authorization": f"Api-Key {api_key}"}
            url = f"{api_host}/v1/models/{self.config.baseten_id}/deployments/{self.config.baseten_deployment_id}/deactivate"
            response = requests.post(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Poll until the service is inactive or timeout
            logger.info(
                f"Waiting for deployment to become inactive (timeout: {timeout}s)..."
            )
            start_time = time.time()
            poll_interval = 5  # seconds

            while time.time() - start_time < timeout:
                state, error = self.check_status()

                if state == ServiceState.INACTIVE:
                    logger.info("Deployment is now inactive")
                    self._update_status(state, "")
                    return
                elif state == ServiceState.ERROR and not force:
                    self._update_status(state, error)
                    raise RuntimeError(f"Failed to stop deployment: {error}")
                else:
                    remaining = timeout - int(time.time() - start_time)
                    logger.info(
                        f"Deployment not inactive yet (state: {state}), waiting... ({remaining}s remaining)"
                    )
                    time.sleep(poll_interval)

            # If we get here, we timed out
            error_msg = f"Timed out waiting for deployment to become inactive after {timeout}s"
            if force:
                logger.warning(f"{error_msg} (force=True, continuing anyway)")
                self._update_status(
                    ServiceState.INACTIVE,
                    "Forced inactive state after timeout",
                )
            else:
                self._update_status(ServiceState.ERROR, error_msg)
                raise RuntimeError(error_msg)

        except requests.RequestException as e:
            error_msg = f"Failed to stop deployment: {str(e)}"
            if force:
                logger.warning(f"{error_msg} (force=True, continuing anyway)")
                self._update_status(
                    ServiceState.INACTIVE, "Forced inactive state after error"
                )
            else:
                self._update_status(ServiceState.ERROR, error_msg)
                raise RuntimeError(error_msg)

    def delete(self, timeout: int = 300, force: bool = False) -> None:
        """Delete the service.

        Args:
            timeout: The timeout in seconds.
            force: Whether to force delete the service.

        Raises:
            RuntimeError: If the service fails to delete and force=False.
        """
        if not self.config.baseten_id or not self.config.baseten_deployment_id:
            logger.info(
                "No Baseten model/deployment ID available, nothing to delete"
            )
            self._update_status(ServiceState.TERMINATED)
            return

        # Update status to show we're deleting
        self._update_status(ServiceState.DELETING, "Deleting deployment...")

        try:
            # First try to deactivate the deployment to avoid deletion errors
            current_state, _ = self.check_status()
            if current_state == ServiceState.ACTIVE:
                logger.info("Deactivating deployment before deletion...")
                try:
                    self.stop(timeout=timeout // 2, force=True)
                except Exception as e:
                    if not force:
                        raise RuntimeError(
                            f"Failed to deactivate deployment before deletion: {str(e)}"
                        )
                    logger.warning(
                        f"Failed to deactivate deployment before deletion: {str(e)}"
                    )

            # Call Baseten API to delete the deployment
            api_key = self._get_api_key()
            api_host = "https://api.baseten.co"  # Use the API base URL
            headers = {"Authorization": f"Api-Key {api_key}"}
            url = f"{api_host}/v1/models/{self.config.baseten_id}/deployments/{self.config.baseten_deployment_id}"
            response = requests.delete(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Update service status
            self._update_status(ServiceState.TERMINATED)

            # Remove from ZenML services registry
            try:
                from zenml.client import Client

                client = Client()
                client.delete_service(self.uuid)
                logger.info(f"Removed service {self.uuid} from ZenML registry")
            except Exception as e:
                logger.warning(
                    f"Failed to remove service from ZenML registry: {str(e)}"
                )

        except requests.RequestException as e:
            error_msg = f"Failed to delete deployment: {str(e)}"
            if force:
                logger.warning(f"{error_msg} (force=True, continuing anyway)")
                self._update_status(
                    ServiceState.TERMINATED, "Forced termination after error"
                )

                # Remove from ZenML services registry even if Baseten deletion failed
                try:
                    from zenml.client import Client

                    client = Client()
                    client.delete_service(self.uuid)
                    logger.info(
                        f"Removed service {self.uuid} from ZenML registry"
                    )
                except Exception as registry_error:
                    logger.warning(
                        f"Failed to remove service from ZenML registry: {str(registry_error)}"
                    )
            else:
                self._update_status(ServiceState.ERROR, error_msg)
                raise RuntimeError(error_msg)

    def predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a prediction using the service.

        Args:
            data: The input data for prediction.

        Returns:
            The prediction results.

        Raises:
            RuntimeError: If the service is not running or prediction fails.
        """
        # Check if service is active and refresh status if needed
        if not self.status or self.status.state != ServiceState.ACTIVE:
            state, error = self.check_status()
            if state != ServiceState.ACTIVE:
                # If not active, try to start the service
                logger.info(
                    f"Service not active (state: {state}), attempting to start..."
                )
                self.start()

        # Double-check that service is running
        if not self.is_running:
            raise RuntimeError(
                f"Service is not running (state: {self.status.state if self.status else 'unknown'})"
            )

        prediction_url = self.prediction_url
        if not prediction_url:
            raise RuntimeError("No prediction URL available")

        try:
            # Make prediction request with retry logic
            max_retries = 3
            retry_delay = 1  # starting delay in seconds
            last_exception = None

            for retry in range(max_retries):
                try:
                    response = requests.post(
                        prediction_url, json=data, timeout=60
                    )
                    response.raise_for_status()
                    return response.json()
                except requests.RequestException as e:
                    last_exception = e
                    if retry < max_retries - 1:
                        # Exponential backoff with jitter
                        sleep_time = retry_delay * (2**retry) + (
                            0.1 * random.random()
                        )
                        logger.warning(
                            f"Prediction request failed, retrying in {sleep_time:.1f}s: {e}"
                        )
                        time.sleep(sleep_time)
                    else:
                        # All retries failed
                        raise RuntimeError(
                            f"Prediction failed after {max_retries} retries: {str(last_exception)}"
                        )

        except Exception as e:
            # Check if this might be due to service state
            try:
                state, _ = self.check_status()
                if state != ServiceState.ACTIVE:
                    raise RuntimeError(
                        f"Prediction failed: service is not active (state: {state})"
                    )
            except Exception:
                pass  # Fall back to the original error

            raise RuntimeError(f"Prediction failed: {str(e)}")

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

            # Create service - use id parameter instead of uuid
            service = cls(
                uuid=model.id,  # This is the key change - use uuid instead of id
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
