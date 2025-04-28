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
"""Implementation of the Vertex AI Model Deployer."""

from typing import Any, ClassVar, Dict, Optional, Tuple, Type, cast
from uuid import UUID

from google.cloud import aiplatform

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_handler
from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.integrations.gcp.flavors.vertex_model_deployer_flavor import (
    VertexModelDeployerConfig,
    VertexModelDeployerFlavor,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsMixin,
)
from zenml.integrations.gcp.model_registries.vertex_model_registry import (
    VertexAIModelRegistry,
)
from zenml.integrations.gcp.services.vertex_deployment import (
    VertexDeploymentConfig,
    VertexDeploymentService,
)
from zenml.logger import get_logger
from zenml.model_deployers import BaseModelDeployer
from zenml.model_deployers.base_model_deployer import (
    DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    BaseModelDeployerFlavor,
)
from zenml.services import BaseService, ServiceConfig
from zenml.stack.stack import Stack
from zenml.stack.stack_validator import StackValidator

logger = get_logger(__name__)


class VertexModelDeployer(BaseModelDeployer, GoogleCredentialsMixin):
    """Vertex AI endpoint model deployer."""

    NAME: ClassVar[str] = "Vertex AI"
    FLAVOR: ClassVar[Type["BaseModelDeployerFlavor"]] = (
        VertexModelDeployerFlavor
    )

    @property
    def config(self) -> VertexModelDeployerConfig:
        """Returns the `VertexModelDeployerConfig` config.

        Returns:
            The configuration.
        """
        return cast(VertexModelDeployerConfig, self._config)

    def _init_vertex_client(
        self,
        credentials: Optional[Any] = None,
    ) -> None:
        """Initialize Vertex AI client with proper credentials.

        Args:
            credentials: Optional credentials to use
        """
        if not credentials:
            credentials, project_id = self._get_authentication()

        # Initialize with per-instance credentials
        aiplatform.init(
            project=project_id,
            location=self.config.location,
            credentials=credentials,
        )

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack contains a Vertex AI model registry.

        Returns:
            A StackValidator instance.
        """

        def _validate_stack_requirements(stack: "Stack") -> Tuple[bool, str]:
            """Validates stack requirements.

            Args:
                stack: The stack to validate.

            Returns:
                A tuple of (is_valid, error_message).
            """
            model_registry = stack.model_registry
            if not isinstance(model_registry, VertexAIModelRegistry):
                return False, (
                    "The Vertex AI model deployer requires a Vertex AI model "
                    "registry to be present in the stack. Please add a Vertex AI "
                    "model registry to the stack."
                )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.MODEL_REGISTRY,
            },
            custom_validation_function=_validate_stack_requirements,
        )

    def _create_deployment_service(
        self, id: UUID, timeout: int, config: VertexDeploymentConfig
    ) -> VertexDeploymentService:
        """Creates a new VertexAIDeploymentService.

        Args:
            id: the UUID of the model to be deployed
            timeout: timeout in seconds for deployment operations
            config: deployment configuration

        Returns:
            The VertexDeploymentService instance
        """
        # Create service instance
        service = VertexDeploymentService(uuid=id, config=config)
        logger.info("Creating Vertex AI deployment service with ID %s", id)

        # Start the service
        service.start(timeout=timeout)
        return service

    def perform_deploy_model(
        self,
        id: UUID,
        config: ServiceConfig,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Deploy a model to Vertex AI.

        Args:
            id: the UUID of the service to be created
            config: deployment configuration
            timeout: timeout for deployment operations

        Returns:
            The deployment service instance
        """
        with track_handler(AnalyticsEvent.MODEL_DEPLOYED) as analytics_handler:
            config = cast(VertexDeploymentConfig, config)

            # Create and start deployment service
            service = self._create_deployment_service(
                id=id, config=config, timeout=timeout
            )

            # Track analytics
            client = Client()
            stack = client.active_stack
            stack_metadata = {
                component_type.value: component.flavor
                for component_type, component in stack.components.items()
            }
            analytics_handler.metadata = {
                "store_type": client.zen_store.type.value,
                **stack_metadata,
            }

            return service

    def perform_stop_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> BaseService:
        """Stop a Vertex AI deployment service.

        Args:
            service: The service to stop
            timeout: Timeout for stop operation
            force: Whether to force stop

        Returns:
            The stopped service
        """
        service.stop(timeout=timeout, force=force)
        return service

    def perform_start_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Start a Vertex AI deployment service.

        Args:
            service: The service to start
            timeout: Timeout for start operation

        Returns:
            The started service
        """
        service.start(timeout=timeout)
        return service

    def perform_delete_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Delete a Vertex AI deployment service.

        Args:
            service: The service to delete
            timeout: Timeout for delete operation
            force: Whether to force delete
        """
        service = cast(VertexDeploymentService, service)
        service.stop(timeout=timeout, force=force)

    @staticmethod
    def get_model_server_info(  # type: ignore[override]
        service_instance: "VertexDeploymentService",
    ) -> Dict[str, Optional[str]]:
        """Get information about the deployed model server.

        Args:
            service_instance: The deployment service instance

        Returns:
            Dict containing server information
        """
        return {
            "prediction_url": service_instance.get_prediction_url(),
            "status": service_instance.status.state.value,
        }
