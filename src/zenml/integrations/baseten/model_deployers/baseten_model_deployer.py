"""Implementation of the Baseten model deployer."""

import os
import subprocess
import time
import traceback
from typing import Any, ClassVar, Dict, List, Optional, Type, Union, cast
from uuid import UUID, uuid4

from zenml.client import Client
from zenml.integrations.baseten.constants import BASETEN_MODEL_DEPLOYER_FLAVOR
from zenml.integrations.baseten.flavors.baseten_model_deployer_flavor import (
    BasetenModelDeployerConfig,
    BasetenModelDeployerFlavor,
)
from zenml.integrations.baseten.services.baseten_deployment import (
    BasetenDeploymentConfig,
    BasetenDeploymentService,
    BasetenEndpoint,
    BasetenEndpointConfig,
    BasetenEndpointStatus,
)
from zenml.logger import get_logger
from zenml.model_deployers import BaseModelDeployer, BaseModelDeployerFlavor
from zenml.services import (
    BaseService,
    ServiceState,
    ServiceStatus,
    ServiceType,
)

logger = get_logger(__name__)

DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT = 300


class BasetenModelDeployer(BaseModelDeployer):
    """Model deployer for Baseten."""

    NAME: ClassVar[str] = BASETEN_MODEL_DEPLOYER_FLAVOR
    FLAVOR: ClassVar[Type[BaseModelDeployerFlavor]] = (
        BasetenModelDeployerFlavor
    )
    SERVICE_TYPE: ClassVar[ServiceType] = ServiceType(
        name="baseten",
        type="model-serving",
        flavor="baseten",
        description="Baseten model deployment service",
    )

    @property
    def config(self) -> BasetenModelDeployerConfig:
        """Returns the config for this model deployer."""
        return cast(BasetenModelDeployerConfig, self._config)

    def _setup_truss_auth(self, api_key: str) -> None:
        """Set up Truss authentication.

        Args:
            api_key: The Baseten API key.

        Raises:
            RuntimeError: If authentication setup fails.
        """
        # Get API host from config, default to standard Baseten URL
        api_host = self.config.api_host or "https://app.baseten.co"

        # Write to ~/.trussrc in INI format
        truss_config = f"""[default]
api_key = {api_key}
remote_provider = baseten
remote_url = {api_host}
"""
        try:
            truss_config_path = os.path.expanduser("~/.trussrc")
            with open(truss_config_path, "w") as f:
                f.write(truss_config)

            logger.info(
                f"Set up Truss authentication with API host: {api_host}"
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to set up Truss authentication: {str(e)}"
            )

    def _create_deployment_service(
        self,
        id: UUID,
        config: BasetenDeploymentConfig,
        model_id: str,
        endpoint_url: str,
    ) -> BasetenDeploymentService:
        """Create a new deployment service.

        Args:
            id: The UUID for the service.
            config: The deployment configuration.
            model_id: The Baseten model ID.
            endpoint_url: The deployment endpoint URL.

        Returns:
            The created deployment service.
        """
        # Update config with model ID
        config.baseten_id = model_id
        config.baseten_deployment_id = (
            model_id  # In Baseten, these are the same
        )

        # Create endpoint
        endpoint = BasetenEndpoint(
            config=BasetenEndpointConfig(),
            status=BasetenEndpointStatus(),
        )
        endpoint.prepare_for_deployment(endpoint_url)

        # Create service status
        status = ServiceStatus(
            state=ServiceState.ACTIVE,
            last_error="",
            last_update=None,
        )

        # Create service
        service = BasetenDeploymentService(
            id=id,
            config=config,
            endpoint=endpoint,
            status=status,
        )

        return service

    def deploy_model(
        self,
        config: Union[Dict[str, Any], BasetenDeploymentConfig],
        replace: bool = True,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        service_type: Optional[ServiceType] = None,
    ) -> BaseService:
        """Deploy a model to Baseten.

        Args:
            config: The deployment configuration.
            replace: Whether to replace an existing deployment.
            timeout: The timeout in seconds.
            service_type: The type of service to create.

        Returns:
            The deployment service.

        Raises:
            RuntimeError: If deployment fails.
        """
        # Convert config dict to BasetenDeploymentConfig if needed
        if isinstance(config, dict):
            config = BasetenDeploymentConfig.from_dict(config)

        # Use the default service type if not specified
        service_type = service_type or self.SERVICE_TYPE

        # Extract key parameters for service lookup
        model_name = config.name
        service_name = config.service_name
        pipeline_name = config.pipeline_name
        pipeline_step_name = config.pipeline_step_name

        # Check for existing services if replace is False
        if not replace:
            # Try to find an existing service by name or other attributes
            existing_services = self.find_model_server(
                service_name=service_name,
                model_name=model_name,
                pipeline_name=pipeline_name,
                pipeline_step_name=pipeline_step_name,
                service_type=service_type,
            )

            if existing_services:
                logger.info(
                    f"Found existing service: {existing_services[0].id}"
                )
                # Verify service status and return it if active
                existing_service = existing_services[0]

                if existing_service.is_running:
                    logger.info("Existing service is running, reusing it")
                    return existing_service

                logger.info(
                    "Existing service is not running, will be replaced"
                )

        # If no existing service or replace=True, create a new service ID
        service_id = uuid4()
        logger.info(f"Creating new service with ID: {service_id}")

        # Delegate to the internal implementation
        return self.perform_deploy_model(
            id=service_id,
            config=config,
            timeout=timeout,
        )

    def perform_deploy_model(
        self,
        id: UUID,
        config: BasetenDeploymentConfig,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BasetenDeploymentService:
        """Internal method to deploy a model to Baseten.

        Args:
            id: The UUID to use for the service.
            config: The deployment configuration.
            timeout: The timeout in seconds.

        Returns:
            The deployment service.

        Raises:
            RuntimeError: If deployment fails.
        """
        logger.info(
            f"Starting deployment with config: {config}, using service ID: {id}"
        )

        # Get API key and set up auth
        baseten_api_key = self.config.baseten_api_key
        if not baseten_api_key:
            raise RuntimeError(
                "No Baseten API key found. Please set it in the model deployer config."
            )
        self._setup_truss_auth(baseten_api_key)

        # Validate Truss directory exists
        truss_dir = config.uri
        if not os.path.exists(truss_dir):
            raise RuntimeError(f"Truss directory not found: {truss_dir}")

        # Deploy to Baseten with improved command
        cmd = [
            "truss",
            "push",
            truss_dir,
            "--wait",
            "--model-name",
            config.name,
        ]

        # Add optional parameters if provided in deployer config
        if self.config.gpu:
            cmd.extend(["--gpu", self.config.gpu])

        if self.config.cpu:
            cmd.extend(["--cpu", self.config.cpu])

        if self.config.memory:
            cmd.extend(["--memory", self.config.memory])

        if self.config.replicas:
            cmd.extend(["--replicas", str(self.config.replicas)])

        # Add environment variables if specified
        if self.config.environment_variables:
            for key, value in self.config.environment_variables.items():
                cmd.extend(["--env", f"{key}={value}"])

        # Log the command, but hide the API key for security
        logger.info(f"Running command: {' '.join(cmd)}")

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            logger.debug(f"Command stdout: {proc.stdout}")
            logger.debug(f"Command stderr: {proc.stderr}")

            if proc.returncode != 0:
                raise RuntimeError(
                    f"Failed to deploy to Baseten:\nStdout: {proc.stdout}\nStderr: {proc.stderr}"
                )

            # Parse deployment info with improved handling
            model_id = None
            endpoint_url = None

            # First try to extract from the command output
            for line in proc.stdout.split("\n"):
                if "Model ID:" in line:
                    model_id = line.split("Model ID:")[1].strip()
                elif "Deployment URL:" in line:
                    endpoint_url = line.split("Deployment URL:")[1].strip()

            # If we couldn't extract the info, try to get it from Baseten API
            if not model_id or not endpoint_url:
                # We could add API lookup here if needed in the future
                raise RuntimeError(
                    "Failed to extract model ID or endpoint from deployment output"
                )

            logger.info(f"Model ID: {model_id}")
            logger.info(f"Endpoint URL: {endpoint_url}")

            # Create service with the extracted info
            service = self._create_deployment_service(
                id=id,
                config=config,
                model_id=model_id,
                endpoint_url=endpoint_url,
            )

            # Wait for deployment to be ready with improved error handling
            logger.info("Waiting for deployment to be ready...")
            max_retries = timeout // 10  # Check every 10 seconds
            retry_delay = 10
            last_state = None
            last_error = None

            for attempt in range(max_retries):
                try:
                    state, error = service.check_status()
                    last_state = state
                    last_error = error

                    if state == ServiceState.ACTIVE:
                        logger.info("Deployment is ready")
                        service._update_status(state, "")
                        break
                    elif state == ServiceState.ERROR:
                        raise RuntimeError(f"Deployment failed: {error}")
                    else:
                        if attempt < max_retries - 1:
                            logger.info(
                                f"Deployment not ready (state: {state}), retrying in {retry_delay}s..."
                            )
                            service._update_status(state, error or "")
                            time.sleep(retry_delay)
                        else:
                            raise RuntimeError(
                                f"Deployment timed out after {timeout}s. Last state: {state}, error: {error}"
                            )
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Failed to check deployment status: {e}, retrying in {retry_delay}s..."
                        )
                        time.sleep(retry_delay)
                    else:
                        service._update_status(ServiceState.ERROR, str(e))
                        raise RuntimeError(
                            f"Failed to verify deployment status: {str(e)}"
                        )

            # Register the service in ZenML
            from zenml.client import Client

            client = Client()
            client.register_service(service)

            return service

        except Exception as e:
            # Ensure we update status to ERROR if anything goes wrong
            logger.error(f"Deployment failed: {str(e)}")
            logger.error(traceback.format_exc())

            # Try to clean up any partial deployment if possible
            try:
                if model_id:
                    logger.warning(
                        f"Attempting to clean up failed deployment for model {model_id}"
                    )
                    # TODO: Add cleanup code using Baseten API if needed
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up deployment: {cleanup_error}")

            # Re-raise with more context
            if isinstance(e, RuntimeError):
                raise
            else:
                raise RuntimeError(f"Deployment failed: {str(e)}")

    def get_model_server_info(
        self,
        service: BasetenDeploymentService,
    ) -> Dict[str, Optional[str]]:
        """Get information about the model server.

        Args:
            service: The service to get information about.

        Returns:
            A dictionary of information about the model server.
        """
        return {
            "name": service.config.name,
            "model_uri": service.config.uri,
            "framework": service.config.framework,
            "pipeline_name": service.config.pipeline_name,
            "run_name": service.config.run_name,
            "pipeline_step_name": service.config.pipeline_step_name,
            "prediction_url": service.prediction_url,
            "status": service.status.state.value,
            "baseten_id": service.config.baseten_id,
        }

    def perform_stop_model(
        self,
        service: BasetenDeploymentService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> BasetenDeploymentService:
        """Stop a model server.

        Args:
            service: The service to stop.
            timeout: Timeout in seconds.
            force: Whether to force stop.

        Returns:
            The updated service.
        """
        logger.info(f"Stopping service {service.id}")
        service.stop(timeout=timeout, force=force)
        return service

    def perform_start_model(
        self,
        service: BasetenDeploymentService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BasetenDeploymentService:
        """Start a model server.

        Args:
            service: The service to start.
            timeout: Timeout in seconds.

        Returns:
            The updated service.
        """
        logger.info(f"Starting service {service.id}")
        service.start(timeout=timeout)
        return service

    def perform_delete_model(
        self,
        service: BasetenDeploymentService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Delete a model server.

        Args:
            service: The service to delete.
            timeout: Timeout in seconds.
            force: Whether to force delete.
        """
        logger.info(f"Deleting service {service.id}")
        service.delete(timeout=timeout, force=force)

    def find_model_server(
        self,
        config: Optional[Dict[str, Any]] = None,
        running: Optional[bool] = None,
        service_uuid: Optional[UUID] = None,
        pipeline_name: Optional[str] = None,
        pipeline_step_name: Optional[str] = None,
        service_name: Optional[str] = None,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        service_type: Optional[ServiceType] = None,
        type: Optional[str] = None,
        flavor: Optional[str] = None,
        pipeline_run_id: Optional[str] = None,
    ) -> List[BasetenDeploymentService]:
        """Find model servers matching the given criteria.

        Args:
            config: Custom Service configuration parameters.
            running: If True, only return running services.
            service_uuid: UUID of the service.
            pipeline_name: Name of the pipeline.
            pipeline_step_name: Name of the pipeline step.
            service_name: Name of the service.
            model_name: Name of the model.
            model_version: Version of the model.
            service_type: Type of the service.
            type: Type of the service (alternative to service_type).
            flavor: The flavor of the model deployer.
            pipeline_run_id: ID of the pipeline run.

        Returns:
            List of matching services.
        """
        client = Client()
        services = []

        try:
            # List all services
            service_list = client.list_services()
            for service in service_list.items:
                if service.service_type != self.SERVICE_TYPE:
                    continue

                # Convert to BasetenDeploymentService
                try:
                    deployment_service = BasetenDeploymentService.from_model(
                        service
                    )
                except ValueError as e:
                    logger.debug(
                        f"Failed to convert service {service.id} to BasetenDeploymentService: {e}"
                    )
                    continue
                except Exception as e:
                    logger.warning(
                        f"Unexpected error converting service {service.id}: {e}"
                    )
                    continue

                # Check if service matches criteria
                if service_uuid and service.id != service_uuid:
                    continue

                # Check config-based criteria
                service_config = deployment_service.config
                if config:
                    try:
                        # Convert config values to strings for comparison
                        config_str = {k: str(v) for k, v in config.items()}
                        service_config_str = {
                            k: str(v)
                            for k, v in service_config.model_dump().items()
                        }
                        if not all(
                            service_config_str.get(k) == v
                            for k, v in config_str.items()
                        ):
                            continue
                    except Exception as e:
                        logger.debug(
                            f"Error comparing config for service {service.id}: {e}"
                        )
                        continue

                if (
                    pipeline_name
                    and service_config.pipeline_name != pipeline_name
                ):
                    continue
                if (
                    pipeline_step_name
                    and service_config.pipeline_step_name != pipeline_step_name
                ):
                    continue
                if (
                    service_name
                    and service_config.service_name != service_name
                ):
                    continue
                if model_name and service_config.name != model_name:
                    continue
                if (
                    model_version
                    and service_config.model_version != model_version
                ):
                    continue
                if running is not None:
                    try:
                        is_running = deployment_service.is_running
                        if running != is_running:
                            continue
                    except Exception as e:
                        logger.debug(
                            f"Error checking running status for service {service.id}: {e}"
                        )
                        continue
                if (
                    pipeline_run_id
                    and service_config.run_name != pipeline_run_id
                ):
                    continue

                # Check service type
                if service_type and service.service_type != service_type:
                    continue
                if type and service.service_type.type != type:
                    continue
                if flavor and flavor != self.FLAVOR.name:
                    continue

                services.append(deployment_service)

        except Exception as e:
            logger.error(f"Error listing services: {e}")

        return services
