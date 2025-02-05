"""Implementation of the Baseten model deployer."""

import os
import subprocess
import time
from typing import Any, ClassVar, Dict, Optional, Type, cast
from uuid import UUID, uuid4

from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.integrations.baseten.constants import BASETEN_MODEL_DEPLOYER_FLAVOR
from zenml.integrations.baseten.flavors.baseten_model_deployer_flavor import (
    BasetenModelDeployerConfig,
    BasetenModelDeployerFlavor,
)
from zenml.integrations.baseten.services.baseten_deployment import (
    BasetenDeploymentConfig,
    BasetenDeploymentService,
)
from zenml.logger import get_logger
from zenml.model_deployers import BaseModelDeployer, BaseModelDeployerFlavor
from zenml.models import ServiceRequest
from zenml.services import BaseService
from zenml.utils import source_utils
from zenml.utils.io_utils import create_dir_recursive_if_not_exists

logger = get_logger(__name__)

DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT = 300


class BasetenModelDeployer(BaseModelDeployer):
    """Model deployer for Baseten."""

    NAME: ClassVar[str] = BASETEN_MODEL_DEPLOYER_FLAVOR
    FLAVOR: ClassVar[Type[BaseModelDeployerFlavor]] = (
        BasetenModelDeployerFlavor
    )

    _service_path: Optional[str] = None

    @property
    def config(self) -> BasetenModelDeployerConfig:
        """Returns the config for this model deployer.

        Returns:
            The config for this model deployer.
        """
        return cast(BasetenModelDeployerConfig, self._config)

    @staticmethod
    def get_service_path(id_: UUID) -> str:
        """Get the path where local Baseten service information is stored.

        Args:
            id_: The ID of the Baseten model deployer.

        Returns:
            The service path.
        """
        service_path = os.path.join(
            GlobalConfiguration().local_stores_path,
            str(id_),
        )
        create_dir_recursive_if_not_exists(service_path)
        return service_path

    @property
    def local_path(self) -> str:
        """Returns the path to the root directory.

        Returns:
            The path to the local service root directory.
        """
        if self._service_path is not None:
            return self._service_path

        if self.config.service_path:
            self._service_path = self.config.service_path
        else:
            self._service_path = self.get_service_path(self.id)

        create_dir_recursive_if_not_exists(self._service_path)
        return self._service_path

    def _setup_truss_config(self, api_key: str) -> None:
        """Set up the Truss configuration file.

        Args:
            api_key: The Baseten API key.
        """
        # Write to ~/.trussrc in INI format
        truss_config = f"""[default]
api_key = {api_key}
remote_provider = baseten
remote_url = https://app.baseten.co
"""
        truss_config_path = os.path.expanduser("~/.trussrc")
        with open(truss_config_path, "w") as f:
            f.write(truss_config)

        logger.info("Created Truss configuration file")

    def _create_truss_config_yaml(
        self, truss_dir: str, model_name: str
    ) -> None:
        """Create the config.yaml file for the Truss.

        Args:
            truss_dir: The Truss directory.
            model_name: The name of the model.
        """
        config = {
            "model_name": model_name,
            "description": f"ZenML deployed model: {model_name}",
            "python_version": "py39",  # Use Python 3.9 as it's stable and widely supported
            "model_class_name": "Model",  # Default model class name
            "requirements": [
                "scikit-learn",  # Add sklearn as a requirement
                "numpy",
            ],
            "resources": {
                "cpu": "1",
                "memory": "2Gi",
                "use_gpu": False,
            },
            "external_package_dirs": [],
        }

        config_path = os.path.join(truss_dir, "config.yaml")
        with open(config_path, "w") as f:
            import yaml

            yaml.dump(config, f, default_flow_style=False)

        logger.info(f"Created Truss config.yaml at {config_path}")

        # Also ensure we have a model.py file with the predict method
        model_dir = os.path.join(truss_dir, "model")
        os.makedirs(model_dir, exist_ok=True)

        model_py_content = '''
import numpy as np
from typing import Dict, Any

class Model:
    def __init__(self, **kwargs):
        self._model = None
        self._model_path = kwargs.get('model_path')

    def load(self):
        """Load the model from the serialized format"""
        import joblib
        self._model = joblib.load(self._model_path)

    def predict(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Predict with the model"""
        if not self._model:
            self.load()
            
        # Extract features from the request
        features = np.array(request["instances"])
        
        # Make prediction
        predictions = self._model.predict(features)
        
        # Return predictions
        return {"predictions": predictions.tolist()}
'''

        model_py_path = os.path.join(model_dir, "model.py")
        with open(model_py_path, "w") as f:
            f.write(model_py_content.strip())

        logger.info(f"Created model.py at {model_py_path}")

    def deploy_model(
        self,
        replace: bool,
        config: Dict[str, Any],
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        service_type: Optional[str] = None,
    ) -> BaseService:
        """Deploy a model to Baseten.

        Args:
            replace: Whether to replace an existing deployment.
            config: Configuration for the deployment.
            timeout: Timeout in seconds.
            service_type: Optional service type.

        Returns:
            The deployment service.

        Raises:
            RuntimeError: If the deployment fails.
        """
        logger.info(
            f"Starting model deployment with config: {config}, replace={replace}"
        )

        # Create a deployment config from the input config
        deployment_config = BasetenDeploymentConfig(
            model_name=config.get("model_name", "zenml_model"),
            model_uri=config.get("model_uri"),
            model_type=config.get("model_type", "sklearn"),
            pipeline_name=config.get("pipeline_name"),
            run_name=config.get("run_name"),
            pipeline_step_name=config.get("pipeline_step_name"),
            root_runtime_path=self.local_path,
        )
        logger.info(f"Created deployment config: {deployment_config}")

        # Call the internal implementation
        return self.perform_deploy_model(
            config=deployment_config,
            replace=replace,
        )

    def perform_deploy_model(
        self,
        config: BasetenDeploymentConfig,
        replace: bool = True,
    ) -> BasetenDeploymentService:
        """Deploy a model to Baseten."""
        logger.info(
            f"Starting model deployment with config: {config}, replace={replace}"
        )

        # Create a new deployment configuration
        deployment_config = BasetenDeploymentConfig(**config.model_dump())
        logger.info(f"Created deployment config: {deployment_config}")

        # Generate a unique ID for the service
        service_id = str(uuid4())
        logger.info(f"Starting deployment with ID {service_id}")

        # Get API key from config or environment
        baseten_api_key = self.config.baseten_api_key
        if not baseten_api_key:
            raise RuntimeError(
                "No Baseten API key found. Please set it in the model deployer config or provide it as a secret."
            )
        logger.info("Found Baseten API key")

        # Set up Truss configuration
        self._setup_truss_config(baseten_api_key)

        # Validate Truss directory
        truss_dir = config.model_uri
        if not truss_dir:
            raise RuntimeError(
                "No Truss directory specified. Please provide a 'model_uri' in the config or step."
            )
        logger.info(f"Using Truss directory: {truss_dir}")

        # Create Truss config.yaml
        self._create_truss_config_yaml(truss_dir, config.model_name)

        # Push to Baseten
        cmd = [
            "truss",
            "push",
            truss_dir,
            "--publish",  # Push as a published deployment
            "--wait",  # Wait for deployment to complete
            "--trusted",  # Allow access to secrets
            "--model-name",
            config.model_name,  # Set the model name
        ]
        logger.info(f"Running command: {' '.join(cmd)}")

        logger.info(f"Deploying model to Baseten: {config.model_name}")
        proc = subprocess.run(cmd, capture_output=True, text=True)

        # Log the full output for debugging
        logger.debug(f"Command stdout: {proc.stdout}")
        logger.debug(f"Command stderr: {proc.stderr}")

        if proc.returncode != 0:
            error_msg = (
                f"Failed to deploy model to Baseten:\nStdout: {proc.stdout}\n"
                f"Stderr: {proc.stderr}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info("Model pushed to Baseten successfully")

        # Wait for a bit to ensure the model is fully deployed
        logger.info("Waiting for model to be fully deployed...")
        time.sleep(10)  # Give Baseten some time to complete the deployment

        # Generate consistent IDs based on service_id and model_name
        model_id = f"{service_id}-{config.model_name}"
        deployment_id = model_id

        logger.info(
            f"Using generated Model ID: {model_id}, Deployment ID: {deployment_id}"
        )

        # Create the service configuration
        service = BasetenDeploymentService(
            id=service_id,
            config=deployment_config,
            model_id=model_id,
            deployment_id=deployment_id,
        )

        # Register the service with ZenML
        client = Client()

        # Check if a service with the same configuration already exists
        existing_services = client.list_services(
            service_name=deployment_config.service_name,
        )
        if existing_services.total > 0 and replace:
            # Delete the existing service
            logger.info(
                f"Deleting existing service {deployment_config.service_name}"
            )
            for existing_service in existing_services.items:
                client.delete_service(existing_service.id)

        # Create the new service request
        service_request = ServiceRequest(
            id=service_id,
            name=deployment_config.service_name,
            service_type=service.SERVICE_TYPE,
            config=deployment_config.model_dump(),
            service_source=source_utils.resolve(service.__class__).import_path,
            status=service.status.model_dump(),
            endpoint=service.endpoint.model_dump()
            if service.endpoint
            else None,
            user=client.active_user.id,
            workspace=client.active_workspace.id,
        )

        try:
            # Register the service with ZenML
            client.zen_store.create_service(service_request)
            logger.info(f"Service {service_id} registered with ZenML")

            # Start the service
            service.start()
            logger.info(f"Service {service_id} started successfully")

            return service

        except Exception as e:
            logger.error(f"Failed to register service with ZenML: {str(e)}")
            # Try to clean up the Baseten deployment if service registration fails
            # TODO: Implement Baseten model deletion
            raise
            return service

        except Exception as e:
            logger.error(f"Failed to register service with ZenML: {str(e)}")
            # Try to clean up the Baseten deployment if service registration fails
            # TODO: Implement Baseten model deletion
            raise

    @staticmethod
    def get_model_server_info(
        service: BaseService,
    ) -> Dict[str, Optional[str]]:
        """Get information about the model server.

        Args:
            service: The service to get information about.

        Returns:
            A dictionary of information about the model server.
        """
        assert isinstance(service, BasetenDeploymentService)
        return {
            "model_name": service.config.model_name,
            "model_uri": service.config.model_uri,
            "model_type": service.config.model_type,
            "pipeline_name": service.config.pipeline_name,
            "run_name": service.config.run_name,
            "pipeline_step_name": service.config.pipeline_step_name,
            "prediction_url": service.prediction_url,
            "status": service.status.state.value,
        }

    def perform_stop_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> BaseService:
        """Stop a model server.

        Args:
            service: The service to stop.
            timeout: Timeout in seconds.
            force: Whether to force stop.

        Returns:
            The updated service.
        """
        logger.info(f"Stopping service {service.uuid}")
        assert isinstance(service, BasetenDeploymentService)
        service.stop(timeout=timeout, force=force)
        logger.info("Service stopped successfully")
        return service

    def perform_start_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Start a model server.

        Args:
            service: The service to start.
            timeout: Timeout in seconds.

        Returns:
            The updated service.
        """
        logger.info(f"Starting service {service.uuid}")
        assert isinstance(service, BasetenDeploymentService)
        service.start(timeout=timeout)
        logger.info("Service started successfully")
        return service

    def perform_delete_model(
        self,
        service: BaseService,
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
        assert isinstance(service, BasetenDeploymentService)

        # TODO: Implement actual deletion of the model in Baseten using their API
        # Currently we only stop the service, but the model remains on Baseten
        service.stop(timeout=timeout, force=force)
        logger.info("Service stopped and marked as deleted successfully")
