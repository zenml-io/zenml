"""Implementation of the Baseten model deployer."""

import os
import subprocess
import time
import traceback
import random
from typing import Any, ClassVar, Dict, List, Optional, Type, Union, cast
from uuid import UUID, uuid4

import requests

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
            uuid=id,  # Pass the id parameter explicitly
            config=config,
            endpoint=endpoint,
            status=status,
        )

        return service

    def _get_model_by_name(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get a model by name using the Baseten API.

        Args:
            model_name: The name of the model to find.

        Returns:
            The model information or None if not found.

        Raises:
            RuntimeError: If the API request fails.
        """
        api_key = self.config.baseten_api_key
        if not api_key:
            raise RuntimeError("No Baseten API key found")

        # Use the API base URL, not the app URL
        api_host = "https://api.baseten.co"
        headers = {"Authorization": f"Api-Key {api_key}"}
        
        # Get all models
        url = f"{api_host}/v1/models"
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            models = response.json().get("models", [])
            
            # Find the model with the matching name
            for model in models:
                if model.get("name") == model_name:
                    return model
                    
            return None
        except Exception as e:
            raise RuntimeError(f"Failed to get model by name: {str(e)}")

    def _get_model_by_id(self, model_id: str) -> Dict[str, Any]:
        """Get a model by ID using the Baseten API.

        Args:
            model_id: The ID of the model to get.

        Returns:
            The model information.

        Raises:
            RuntimeError: If the API request fails.
        """
        api_key = self.config.baseten_api_key
        if not api_key:
            raise RuntimeError("No Baseten API key found")

        # Use the API base URL, not the app URL
        api_host = "https://api.baseten.co"
        headers = {"Authorization": f"Api-Key {api_key}"}
        
        # Get the model by ID
        url = f"{api_host}/v1/models/{model_id}"
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise RuntimeError(f"Failed to get model by ID: {str(e)}")

    def _get_model_deployment_url(self, model_id: str) -> str:
        """Get the deployment URL for a model.

        Args:
            model_id: The ID of the model.

        Returns:
            The deployment URL.

        Raises:
            RuntimeError: If the API request fails.
        """
        # For Baseten, the prediction URL follows a standard format
        return f"https://model.baseten.co/models/{model_id}/predict"

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
                    f"Found existing service: {existing_services[0].uuid}"
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

        # Get the remote name from config
        remote = self.config.remote or "default"

        try:
            # Import the Truss SDK
            import truss as truss_sdk
            
            # Set up authentication
            truss_sdk.login(api_key=baseten_api_key)
            
            # Build deployment options
            push_kwargs = {
                "target_directory": truss_dir,
                "model_name": config.name,
                "remote": remote,  # Use the remote from config
            }
            
            # Deploy the model
            logger.info(f"Deploying model to Baseten with options: {push_kwargs}")
            
            try:
                # Deploy the model using the SDK
                deployment = truss_sdk.push(**push_kwargs)
                
                # Extract model and deployment IDs
                model_id = deployment.model_id
                deployment_id = deployment.model_deployment_id
                
                logger.info(f"Model deployed with ID: {model_id}, deployment ID: {deployment_id}")
                
                # Wait for deployment to be active with a timeout
                # Note: The SDK's wait_for_active() method has its own timeout which might be shorter
                # than what we want, so we'll handle timeouts gracefully
                logger.info("Waiting for deployment to be active...")
                try:
                    is_active = deployment.wait_for_active()
                    if not is_active:
                        logger.warning("Deployment did not become active within SDK timeout, but will continue")
                except Exception as wait_error:
                    # If the wait times out or fails for any reason, we'll still continue
                    # since the model might still be deploying and could become active later
                    logger.warning(f"Error while waiting for deployment to be active: {wait_error}")
                    logger.warning("Continuing with deployment process despite wait error")
                
                # Get the deployment URL
                endpoint_url = self._get_model_deployment_url(model_id)
                logger.info(f"Deployment URL: {endpoint_url}")
                
                # Create service with the extracted info
                service = self._create_deployment_service(
                    id=id,
                    config=config,
                    model_id=model_id,
                    endpoint_url=endpoint_url,
                )
                
                # Register the service in ZenML
                client = Client()
                
                # Create the service using the client's create_service method
                service_response = client.create_service(
                    config=service.config.model_dump(),
                    service_type=self.SERVICE_TYPE,
                    model_version_id=None,  # Add model version ID if needed
                    service_source=f"{service.__class__.__module__}.{service.__class__.__name__}",
                    service_name=service.config.service_name,
                    prediction_url=service.get_prediction_url(),
                    health_check_url=service.get_healthcheck_url(),
                    admin_state=service.admin_state,
                    status=service.status.model_dump() if service.status else None,
                    endpoint=service.endpoint.model_dump() if service.endpoint else None,
                    id=service.uuid,  # Use uuid instead of id
                )
                
                # Check the actual status using our own method which uses the Baseten API directly
                logger.info("Checking deployment status via Baseten API...")
                max_retries = timeout // 10  # Check every 10 seconds
                retry_delay = 10
                
                for attempt in range(max_retries):
                    try:
                        state, error = service.check_status()
                        
                        if state == ServiceState.ACTIVE:
                            logger.info("Deployment is ready and active")
                            service._update_status(state, "")
                            break
                        elif state == ServiceState.ERROR:
                            logger.error(f"Deployment failed: {error}")
                            service._update_status(state, error)
                            # Don't raise an exception here, as the model might still be usable
                        else:
                            if attempt < max_retries - 1:
                                logger.info(
                                    f"Deployment not ready yet (state: {state}), retrying in {retry_delay}s..."
                                )
                                service._update_status(state, error or "")
                                time.sleep(retry_delay)
                            else:
                                logger.warning(
                                    f"Deployment status check timed out after {timeout}s. Last state: {state}, error: {error}"
                                )
                                # Don't raise an exception, as the model might still become active later
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Failed to check deployment status: {e}, retrying in {retry_delay}s..."
                            )
                            time.sleep(retry_delay)
                        else:
                            logger.warning(f"Failed to verify deployment status: {str(e)}")
                            # Don't raise an exception, as the model might still be usable
                
                # Update the service in ZenML with the latest status
                client.update_service(
                    id=service.uuid,  # Use uuid instead of id
                    status=service.status.model_dump() if service.status else None,
                    endpoint=service.endpoint.model_dump() if service.endpoint else None,
                    prediction_url=service.get_prediction_url(),
                    health_check_url=service.get_healthcheck_url(),
                )
                
                return service
                
            except Exception as e:
                # If the SDK approach fails, fall back to the CLI approach
                logger.warning(f"SDK deployment failed: {str(e)}, falling back to CLI approach")
                
                # Deploy to Baseten with CLI command
                cmd = [
                    "truss",
                    "push",
                    truss_dir,
                    "--wait",
                    "--model-name",
                    config.name,
                    "--remote",  # Explicitly specify the remote
                    remote,  # Use the remote from config
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
                
                proc = subprocess.run(cmd, capture_output=True, text=True)
                logger.debug(f"Command stdout: {proc.stdout}")
                logger.debug(f"Command stderr: {proc.stderr}")
                
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"Failed to deploy to Baseten:\nStdout: {proc.stdout}\nStderr: {proc.stderr}"
                    )
                
                # Parse the output to extract the model ID
                model_id = None
                for line in proc.stdout.split("\n"):
                    if "Model ID:" in line:
                        model_id = line.split("Model ID:")[1].strip()
                        break
                
                if not model_id:
                    raise RuntimeError("Failed to extract model ID from deployment output")
                
                logger.info(f"Extracted model ID: {model_id}")
                
                # Get the deployment URL
                endpoint_url = self._get_model_deployment_url(model_id)
                logger.info(f"Deployment URL: {endpoint_url}")
                
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
                            logger.error(f"Deployment failed: {error}")
                            service._update_status(state, error)
                            # Don't raise an exception here, as the model might still be usable
                        else:
                            if attempt < max_retries - 1:
                                logger.info(
                                    f"Deployment not ready yet (state: {state}), retrying in {retry_delay}s..."
                                )
                                service._update_status(state, error or "")
                                time.sleep(retry_delay)
                            else:
                                logger.warning(
                                    f"Deployment status check timed out after {timeout}s. Last state: {state}, error: {error}"
                                )
                                # Don't raise an exception, as the model might still become active later
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Failed to check deployment status: {e}, retrying in {retry_delay}s..."
                            )
                            time.sleep(retry_delay)
                        else:
                            logger.warning(f"Failed to verify deployment status: {str(e)}")
                            # Don't raise an exception, as the model might still be usable
                
                # Register the service in ZenML
                client = Client()
                
                # Create the service using the client's create_service method
                service_response = client.create_service(
                    config=service.config.model_dump(),
                    service_type=self.SERVICE_TYPE,
                    model_version_id=None,  # Add model version ID if needed
                    service_source=f"{service.__class__.__module__}.{service.__class__.__name__}",
                    service_name=service.config.service_name,
                    prediction_url=service.get_prediction_url(),
                    health_check_url=service.get_healthcheck_url(),
                    admin_state=service.admin_state,
                    status=service.status.model_dump() if service.status else None,
                    endpoint=service.endpoint.model_dump() if service.endpoint else None,
                    id=service.uuid,  # Use uuid instead of id
                )
                
                return service

        except Exception as e:
            # Ensure we update status to ERROR if anything goes wrong
            logger.error(f"Deployment failed: {str(e)}")
            logger.error(traceback.format_exc())

            # Try to clean up any partial deployment if possible
            try:
                if 'model_id' in locals() and model_id:
                    logger.warning(
                        f"Attempting to clean up failed deployment for model {model_id}"
                    )
                    # Clean up using Baseten API
                    self._delete_model(model_id)
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up deployment: {cleanup_error}")

            # Re-raise with more context
            if isinstance(e, RuntimeError):
                raise
            else:
                raise RuntimeError(f"Deployment failed: {str(e)}")

    def _delete_model(self, model_id: str) -> None:
        """Delete a model using the Baseten API.

        Args:
            model_id: The ID of the model to delete.

        Raises:
            RuntimeError: If the API request fails.
        """
        api_key = self.config.baseten_api_key
        if not api_key:
            raise RuntimeError("No Baseten API key found")

        # Use the API base URL, not the app URL
        api_host = "https://api.baseten.co"
        headers = {"Authorization": f"Api-Key {api_key}"}
        
        # Delete the model
        url = f"{api_host}/v1/models/{model_id}"
        
        try:
            response = requests.delete(url, headers=headers, timeout=30)
            response.raise_for_status()
            logger.info(f"Successfully deleted model {model_id}")
        except Exception as e:
            raise RuntimeError(f"Failed to delete model: {str(e)}")

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
        logger.info(f"Stopping service {service.uuid}")
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
        logger.info(f"Starting service {service.uuid}")
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
        logger.info(f"Deleting service {service.uuid}")
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
