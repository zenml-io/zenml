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

from typing import ClassVar, Dict, Optional, Tuple, Type, cast
from uuid import UUID

from google.cloud import aiplatform

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_handler
from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.integrations.gcp import (
    VERTEX_SERVICE_ARTIFACT,
)
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
    VertexAIDeploymentConfig,
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

    def setup_aiplatform(self) -> None:
        """Setup the Vertex AI platform."""
        credentials, project_id = self._get_authentication()
        aiplatform.init(
            project=project_id,
            location=self.config.location,
            credentials=credentials,
        )

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack contains a model registry.

        Also validates that the artifact store is not local.

        Returns:
            A StackValidator instance.
        """

        def _validate_stack_requirements(stack: "Stack") -> Tuple[bool, str]:
            """Validates that all the stack components are not local.

            Args:
                stack: The stack to validate.

            Returns:
                A tuple of (is_valid, error_message).
            """
            # Validate that the container registry is not local.
            model_registry = stack.model_registry
            if not model_registry and isinstance(
                model_registry, VertexAIModelRegistry
            ):
                return False, (
                    "The Vertex AI model deployer requires a Vertex AI model "
                    "registry to be present in the stack. Please add a Vertex AI "
                    "model registry to the stack."
                )

            # Validate that the rest of the components are not local.
            for stack_comp in stack.components.values():
                # For Forward compatibility a list of components is returned,
                # but only the first item is relevant for now
                # TODO: [server] make sure the ComponentModel actually has
                #  a local_path property or implement similar check
                local_path = stack_comp.local_path
                if not local_path:
                    continue
                return False, (
                    f"The '{stack_comp.name}' {stack_comp.type.value} is a "
                    f"local stack component. The Vertex AI Pipelines "
                    f"orchestrator requires that all the components in the "
                    f"stack used to execute the pipeline have to be not local, "
                    f"because there is no way for Vertex to connect to your "
                    f"local machine. You should use a flavor of "
                    f"{stack_comp.type.value} other than '"
                    f"{stack_comp.flavor}'."
                )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.MODEL_REGISTRY,
            },
            custom_validation_function=_validate_stack_requirements,
        )

    def _create_deployment_service(
        self, id: UUID, timeout: int, config: VertexAIDeploymentConfig
    ) -> VertexDeploymentService:
        """Creates a new VertexAIDeploymentService.

        Args:
            id: the UUID of the model to be deployed with Vertex model deployer.
            timeout: the timeout in seconds to wait for the Vertex inference endpoint
                to be provisioned and successfully started or updated.
            config: the configuration of the model to be deployed with Vertex model deployer.

        Returns:
            The VertexModelDeployerConfig object that can be used to interact
            with the Vertex inference endpoint.
        """
        # create a new service for the new model
        service = VertexDeploymentService(uuid=id, config=config)
        logger.info(
            f"Creating an artifact {VERTEX_SERVICE_ARTIFACT} with service instance attached as metadata."
            " If there's an active pipeline and/or model this artifact will be associated with it."
        )
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
            id: the UUID of the service to be created.
            config: the configuration of the model to be deployed.
            timeout: the timeout for the deployment operation.

        Returns:
            The ZenML Vertex AI deployment service object.
        """
        with track_handler(AnalyticsEvent.MODEL_DEPLOYED) as analytics_handler:
            config = cast(VertexAIDeploymentConfig, config)
            service = self._create_deployment_service(
                id=id, config=config, timeout=timeout
            )
            logger.info(
                f"Creating a new Vertex AI deployment service: {service}"
            )
            service.start(timeout=timeout)

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
            service: The service to stop.
            timeout: Timeout in seconds to wait for the service to stop.
            force: If True, force the service to stop.

        Returns:
            The stopped service.
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
            service: The service to start.
            timeout: Timeout in seconds to wait for the service to start.

        Returns:
            The started service.
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
            service: The service to delete.
            timeout: Timeout in seconds to wait for the service to stop.
            force: If True, force the service to stop.
        """
        service = cast(VertexDeploymentService, service)
        service.stop(timeout=timeout, force=force)
        service.stop()

    @staticmethod
    def get_model_server_info(  # type: ignore[override]
        service_instance: "VertexDeploymentService",
    ) -> Dict[str, Optional[str]]:
        """Get information about the deployed model server.

        Args:
            service_instance: The VertexDeploymentService instance.

        Returns:
            A dictionary containing information about the model server.
        """
        return {
            "PREDICTION_URL": service_instance.prediction_url,
            "HEALTH_CHECK_URL": service_instance.get_healthcheck_url(),
        }
