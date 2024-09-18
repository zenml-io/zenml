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

from typing import ClassVar, Dict, List, Optional, Tuple, Type, cast
from uuid import UUID

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_handler
from zenml.client import Client
from zenml.integrations.gcp import VERTEX_SERVICE_ARTIFACT
from zenml.integrations.gcp.flavors.vertex_model_deployer_flavor import (
    VertexModelDeployerConfig,
    VertexModelDeployerFlavor,
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


class VertexModelDeployer(BaseModelDeployer):
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

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack.

        Returns:
            A validator that checks that the stack contains required GCP components.
        """

        def _validate_gcp_stack(
            stack: "Stack",
        ) -> Tuple[bool, str]:
            """Check if GCP components are properly configured in the stack.

            Args:
                stack: The stack to validate.

            Returns:
                A tuple with a boolean indicating whether the stack is valid
                and a message describing the validation result.
            """
            if not self.config.project_id or not self.config.location:
                return False, (
                    "The Vertex AI model deployer requires a GCP project and "
                    "location to be specified in the configuration."
                )
            return True, "Stack is valid for Vertex AI model deployment."

        return StackValidator(
            custom_validation_function=_validate_gcp_stack,
        )

    def _create_deployment_service(
        self, id: UUID, timeout: int, config: VertexModelDeployerConfig
    ) -> VertexDeploymentService:
        """Creates a new DatabricksDeploymentService.

        Args:
            id: the UUID of the model to be deployed with Databricks model deployer.
            timeout: the timeout in seconds to wait for the Databricks inference endpoint
                to be provisioned and successfully started or updated.
            config: the configuration of the model to be deployed with Databricks model deployer.

        Returns:
            The VertexModelDeployerConfig object that can be used to interact
            with the Databricks inference endpoint.
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
            config = cast(VertexServiceConfig, config)
            service = self._create_deployment_service(id=id, config=config)
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

            # Create a service artifact
            client.create_artifact(
                name=VERTEX_SERVICE_ARTIFACT,
                artifact_store_id=client.active_stack.artifact_store.id,
                producer=service,
            )

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
        service.delete()

    @staticmethod
    def get_model_server_info(
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

    def find_model_server(
        self,
        running: Optional[bool] = None,
        service_uuid: Optional[UUID] = None,
        pipeline_name: Optional[str] = None,
        run_name: Optional[str] = None,
        pipeline_step_name: Optional[str] = None,
        model_name: Optional[str] = None,
        model_uri: Optional[str] = None,
        model_version: Optional[str] = None,
    ) -> List[BaseService]:
        """Find deployed model servers in Vertex AI.

        Args:
            running: Filter by running status.
            service_uuid: Filter by service UUID.
            pipeline_name: Filter by pipeline name.
            run_name: Filter by run name.
            pipeline_step_name: Filter by pipeline step name.
            model_name: Filter by model name.
            model_uri: Filter by model URI.
            model_version: Filter by model version.

        Returns:
            A list of services matching the given criteria.
        """
        client = Client()
        services = client.list_services(
            service_type=VertexDeploymentService.SERVICE_TYPE,
            running=running,
            service_uuid=service_uuid,
            pipeline_name=pipeline_name,
            run_name=run_name,
            pipeline_step_name=pipeline_step_name,
            model_name=model_name,
            model_uri=model_uri,
            model_version=model_version,
        )

        return [
            VertexDeploymentService.from_model(service_model)
            for service_model in services
        ]
