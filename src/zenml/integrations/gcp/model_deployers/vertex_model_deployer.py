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

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_handler
from zenml.client import Client
from zenml.integrations.gcp import VERTEX_SERVICE_ARTIFACT
from zenml.integrations.gcp.flavors.vertex_model_deployer_flavor import (
    VertexModelDeployerConfig,
    VertexModelDeployerFlavor,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsMixin,
)
from zenml.integrations.gcp.services.vertex_deployment import (
    VertexDeploymentService,
    VertexServiceConfig,
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
    """Vertex implementation of the BaseModelDeployer."""

    @property
    def config(self) -> VertexModelDeployerConfig:
        """Config class for the Vertex AI Model deployer settings class.

        Returns:
            The configuration.
        """
        return cast(VertexModelDeployerConfig, self._config)

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack.

        Returns:
            A validator that checks that the stack contains a remote artifact
            store.
        """

        def _validate_if_secret_or_token_is_present(
            stack: "Stack",
        ) -> Tuple[bool, str]:
            """Check if secret or token is present in the stack.

            Args:
                stack: The stack to validate.

            Returns:
                A tuple with a boolean indicating whether the stack is valid
                and a message describing the validation result.
            """
            return bool(self.config.token or self.config.secret_name), (
                "The Vertex AI model deployer requires either a secret name"
                " or a token to be present in the stack."
            )

        return StackValidator(
            custom_validation_function=_validate_if_secret_or_token_is_present,
        )

    def _create_new_service(
        self, id: UUID, timeout: int, config: VertexServiceConfig
    ) -> VertexDeploymentService:
        """Creates a new VertexDeploymentService.

        Args:
            id: the UUID of the model to be deployed with Vertex AI model deployer.
            timeout: the timeout in seconds to wait for the Vertex AI inference endpoint
                to be provisioned and successfully started or updated.
            config: the configuration of the model to be deployed with Vertex AI model deployer.

        Returns:
            The VertexServiceConfig object that can be used to interact
            with the Vertex AI inference endpoint.
        """
        # create a new service for the new model
        service = VertexDeploymentService(uuid=id, config=config)

        logger.info(
            f"Creating an artifact {VERTEX_SERVICE_ARTIFACT} with service instance attached as metadata."
            " If there's an active pipeline and/or model this artifact will be associated with it."
        )
        service.start(timeout=timeout)
        return service

    def _clean_up_existing_service(
        self,
        timeout: int,
        force: bool,
        existing_service: VertexDeploymentService,
    ) -> None:
        """Stop existing services.

        Args:
            timeout: the timeout in seconds to wait for the Vertex AI
                deployment to be stopped.
            force: if True, force the service to stop
            existing_service: Existing Vertex AI deployment service
        """
        # stop the older service
        existing_service.stop(timeout=timeout, force=force)

    def perform_deploy_model(
        self,
        id: UUID,
        config: ServiceConfig,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Create a new Vertex AI deployment service or update an existing one.

        This should serve the supplied model and deployment configuration.

        Args:
            id: the UUID of the model to be deployed with Vertex AI.
            config: the configuration of the model to be deployed with Vertex AI.
            timeout: the timeout in seconds to wait for the Vertex AI endpoint
                to be provisioned and successfully started or updated. If set
                to 0, the method will return immediately after the Vertex AI
                server is provisioned, without waiting for it to fully start.

        Returns:
            The ZenML Vertex AI deployment service object that can be used to
            interact with the remote Vertex AI inference endpoint server.
        """
        with track_handler(AnalyticsEvent.MODEL_DEPLOYED) as analytics_handler:
            config = cast(VertexServiceConfig, config)
            # create a new VertexDeploymentService instance
            service = self._create_new_service(
                id=id, timeout=timeout, config=config
            )
            logger.info(
                f"Creating a new Vertex AI inference endpoint service: {service}"
            )
            # Add telemetry with metadata that gets the stack metadata and
            # differentiates between pure model and custom code deployments
            stack = Client().active_stack
            stack_metadata = {
                component_type.value: component.flavor
                for component_type, component in stack.components.items()
            }
            analytics_handler.metadata = {
                "store_type": Client().zen_store.type.value,
                **stack_metadata,
            }

        return service

    def perform_stop_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> BaseService:
        """Method to stop a model server.

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
        """Method to start a model server.

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
        """Method to delete all configuration of a model server.

        Args:
            service: The service to delete.
            timeout: Timeout in seconds to wait for the service to stop.
            force: If True, force the service to stop.
        """
        service = cast(VertexDeploymentService, service)
        self._clean_up_existing_service(
            existing_service=service, timeout=timeout, force=force
        )

    @staticmethod
    def get_model_server_info(  # type: ignore[override]
        service_instance: "VertexDeploymentService",
    ) -> Dict[str, Optional[str]]:
        """Return implementation specific information that might be relevant to the user.

        Args:
            service_instance: Instance of a VertexDeploymentService

        Returns:
            Model server information.
        """
        return {
            "PREDICTION_URL": service_instance.get_prediction_url(),
            "HEALTH_CHECK_URL": service_instance.get_healthcheck_url(),
        }
