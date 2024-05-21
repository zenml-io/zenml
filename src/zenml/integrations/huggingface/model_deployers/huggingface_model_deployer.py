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
"""Implementation of the Hugging Face Model Deployer."""

from typing import ClassVar, Dict, Optional, Tuple, Type, cast
from uuid import UUID

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_handler
from zenml.client import Client
from zenml.integrations.huggingface import HUGGINGFACE_SERVICE_ARTIFACT
from zenml.integrations.huggingface.flavors.huggingface_model_deployer_flavor import (
    HuggingFaceModelDeployerConfig,
    HuggingFaceModelDeployerFlavor,
)
from zenml.integrations.huggingface.services.huggingface_deployment import (
    HuggingFaceDeploymentService,
    HuggingFaceServiceConfig,
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


class HuggingFaceModelDeployer(BaseModelDeployer):
    """Hugging Face endpoint model deployer."""

    NAME: ClassVar[str] = "HuggingFace"
    FLAVOR: ClassVar[Type[BaseModelDeployerFlavor]] = (
        HuggingFaceModelDeployerFlavor
    )

    @property
    def config(self) -> HuggingFaceModelDeployerConfig:
        """Config class for the Hugging Face Model deployer settings class.

        Returns:
            The configuration.
        """
        return cast(HuggingFaceModelDeployerConfig, self._config)

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
                "The Hugging Face model deployer requires either a secret name"
                " or a token to be present in the stack."
            )

        return StackValidator(
            custom_validation_function=_validate_if_secret_or_token_is_present,
        )

    def _create_new_service(
        self, id: UUID, timeout: int, config: HuggingFaceServiceConfig
    ) -> HuggingFaceDeploymentService:
        """Creates a new Hugging FaceDeploymentService.

        Args:
            id: the UUID of the model to be deployed with Hugging Face model deployer.
            timeout: the timeout in seconds to wait for the Hugging Face inference endpoint
                to be provisioned and successfully started or updated.
            config: the configuration of the model to be deployed with Hugging Face model deployer.

        Returns:
            The HuggingFaceServiceConfig object that can be used to interact
            with the Hugging Face inference endpoint.
        """
        # create a new service for the new model
        service = HuggingFaceDeploymentService(uuid=id, config=config)

        logger.info(
            f"Creating an artifact {HUGGINGFACE_SERVICE_ARTIFACT} with service instance attached as metadata."
            " If there's an active pipeline and/or model this artifact will be associated with it."
        )
        service.start(timeout=timeout)
        return service

    def _clean_up_existing_service(
        self,
        timeout: int,
        force: bool,
        existing_service: HuggingFaceDeploymentService,
    ) -> None:
        """Stop existing services.

        Args:
            timeout: the timeout in seconds to wait for the Hugging Face
                deployment to be stopped.
            force: if True, force the service to stop
            existing_service: Existing Hugging Face deployment service
        """
        # stop the older service
        existing_service.stop(timeout=timeout, force=force)

    def perform_deploy_model(
        self,
        id: UUID,
        config: ServiceConfig,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Create a new Hugging Face deployment service or update an existing one.

        This should serve the supplied model and deployment configuration.

        Args:
            id: the UUID of the model to be deployed with Hugging Face.
            config: the configuration of the model to be deployed with Hugging Face.
            timeout: the timeout in seconds to wait for the Hugging Face endpoint
                to be provisioned and successfully started or updated. If set
                to 0, the method will return immediately after the Hugging Face
                server is provisioned, without waiting for it to fully start.

        Returns:
            The ZenML Hugging Face deployment service object that can be used to
            interact with the remote Hugging Face inference endpoint server.
        """
        with track_handler(AnalyticsEvent.MODEL_DEPLOYED) as analytics_handler:
            config = cast(HuggingFaceServiceConfig, config)
            # create a new HuggingFaceDeploymentService instance
            service = self._create_new_service(
                id=id, timeout=timeout, config=config
            )
            logger.info(
                f"Creating a new Hugging Face inference endpoint service: {service}"
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
        service = cast(HuggingFaceDeploymentService, service)
        self._clean_up_existing_service(
            existing_service=service, timeout=timeout, force=force
        )

    @staticmethod
    def get_model_server_info(  # type: ignore[override]
        service_instance: "HuggingFaceDeploymentService",
    ) -> Dict[str, Optional[str]]:
        """Return implementation specific information that might be relevant to the user.

        Args:
            service_instance: Instance of a HuggingFaceDeploymentService

        Returns:
            Model server information.
        """
        return {
            "PREDICTION_URL": service_instance.get_prediction_url(),
            "HEALTH_CHECK_URL": service_instance.get_healthcheck_url(),
        }
