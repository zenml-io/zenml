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
"""Implementation of the Vertex AI Deployment service."""

import re
from typing import Any, Dict, Generator, List, Optional, Tuple

from google.api_core import exceptions
from google.cloud import aiplatform
from pydantic import BaseModel, Field

from zenml.client import Client
from zenml.integrations.gcp.flavors.vertex_model_deployer_flavor import (
    VertexBaseConfig,
)
from zenml.logger import get_logger
from zenml.services import ServiceState, ServiceStatus, ServiceType
from zenml.services.service import BaseDeploymentService, ServiceConfig

logger = get_logger(__name__)

POLLING_TIMEOUT = 1200
UUID_SLICE_LENGTH: int = 8


def sanitize_labels(labels: Dict[str, str]) -> None:
    """Update the label values to be valid Kubernetes labels.

    See:
    https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#syntax-and-character-set

    Args:
        labels: the labels to sanitize.
    """
    for key, value in labels.items():
        # Kubernetes labels must be alphanumeric, no longer than
        # 63 characters, and must begin and end with an alphanumeric
        # character ([a-z0-9A-Z])
        labels[key] = re.sub(r"[^0-9a-zA-Z-_\.]+", "_", value)[:63].strip(
            "-_."
        )


class VertexAIDeploymentConfig(VertexBaseConfig, ServiceConfig):
    """Vertex AI service configurations."""

    def get_vertex_deployment_labels(self) -> Dict[str, str]:
        """Generate labels for the VertexAI deployment from the service configuration.

        These labels are attached to the VertexAI deployment resource
        and may be used as label selectors in lookup operations.

        Returns:
            The labels for the VertexAI deployment.
        """
        labels = {}
        if self.pipeline_name:
            labels["zenml_pipeline_name"] = self.pipeline_name
        if self.pipeline_step_name:
            labels["zenml_pipeline_step_name"] = self.pipeline_step_name
        if self.model_name:
            labels["zenml_model_name"] = self.model_name
        sanitize_labels(labels)
        return labels


class VertexPredictionServiceEndpoint(BaseModel):
    """Vertex AI Prediction Service Endpoint."""

    endpoint_name: str
    endpoint_url: Optional[str] = None


class VertexServiceStatus(ServiceStatus):
    """Vertex AI service status."""

    endpoint: Optional[VertexPredictionServiceEndpoint] = None


class VertexDeploymentService(BaseDeploymentService):
    """Vertex AI model deployment service.

    Attributes:
        SERVICE_TYPE: a service type descriptor with information describing
            the Vertex AI deployment service class
        config: service configuration
    """

    SERVICE_TYPE = ServiceType(
        name="vertex-deployment",
        type="model-serving",
        flavor="vertex",
        description="Vertex AI inference endpoint prediction service",
    )
    config: VertexAIDeploymentConfig
    status: VertexServiceStatus = Field(
        default_factory=lambda: VertexServiceStatus()
    )

    def __init__(self, config: VertexAIDeploymentConfig, **attrs: Any):
        """Initialize the Vertex AI deployment service.

        Args:
            config: service configuration
            attrs: additional attributes to set on the service
        """
        super().__init__(config=config, **attrs)

    @property
    def prediction_url(self) -> Optional[str]:
        """The prediction URI exposed by the prediction service.

        Returns:
            The prediction URI exposed by the prediction service, or None if
            the service is not yet ready.
        """
        return (
            self.status.endpoint.endpoint_url if self.status.endpoint else None
        )

    def get_endpoints(self) -> List[aiplatform.Endpoint]:
        """Get all endpoints for the current project and location."""
        return aiplatform.Endpoint.list()

    def _generate_endpoint_name(self) -> str:
        """Generate a unique name for the Vertex AI Inference Endpoint.

        Returns:
            A unique name for the Vertex AI Inference Endpoint.
        """
        return f"{self.config.model_name}-{str(self.uuid)[:UUID_SLICE_LENGTH]}"

    def provision(self) -> None:
        """Provision or update remote Vertex AI deployment instance."""
        from zenml.integrations.gcp.model_deployers.vertex_model_deployer import (
            VertexModelDeployer,
        )

        zenml_client = Client()
        model_deployer = zenml_client.active_stack.model_deployer
        if isinstance(model_deployer, VertexModelDeployer):
            model_deployer.setup_aiplatform()
        else:
            raise ValueError("Model deployer is not VertexModelDeployer")
        try:
            breakpoint()
            model = aiplatform.Model(
                model_name=self.config.model_name,
                version=self.config.model_version,
            )
            breakpoint()
            endpoint = aiplatform.Endpoint.create(
                display_name=self._generate_endpoint_name()
            )
            breakpoint()
            endpoint.deploy(
                model=model,
                machine_type=self.config.machine_type,
                min_replica_count=self.config.min_replica_count,
                max_replica_count=self.config.max_replica_count,
                accelerator_type=self.config.accelerator_type,
                accelerator_count=self.config.accelerator_count,
                service_account=self.config.service_account,
                network=self.config.network,
                encryption_spec_key_name=self.config.encryption_spec_key_name,
                explanation_metadata=self.config.explanation_metadata,
                explanation_parameters=self.config.explanation_parameters,
                sync=True,
            )
            breakpoint()
            self.status.endpoint = VertexPredictionServiceEndpoint(
                endpoint_name=endpoint.resource_name,
                endpoint_url=endpoint.resource_name,
            )
            self.status.update_state(ServiceState.ACTIVE)

            logger.info(
                f"Vertex AI inference endpoint successfully deployed. "
                f"Endpoint: {endpoint.resource_name}"
            )

        except Exception as e:
            self.status.update_state(
                new_state=ServiceState.ERROR, error=str(e)
            )
            raise RuntimeError(
                f"An error occurred while provisioning the Vertex AI inference endpoint: {e}"
            )

    def deprovision(self, force: bool = False) -> None:
        """Deprovision the remote Vertex AI deployment instance.

        Args:
            force: if True, the remote deployment instance will be
                forcefully deprovisioned.
        """
        if self.status.endpoint:
            try:
                endpoint = aiplatform.Endpoint(
                    endpoint_name=self.status.endpoint.endpoint_name
                )
                endpoint.undeploy_all()
                endpoint.delete(force=force)
                self.status.endpoint = None
                self.status.update_state(ServiceState.INACTIVE)
                logger.info(
                    f"Vertex AI Inference Endpoint {self.status.endpoint.endpoint_name} has been deprovisioned."
                )
            except exceptions.NotFound:
                logger.warning(
                    f"Vertex AI Inference Endpoint {self.status.endpoint.endpoint_name} not found. It may have been already deleted."
                )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to deprovision Vertex AI Inference Endpoint: {e}"
                )

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the current operational state of the Vertex AI deployment.

        Returns:
            The operational state of the Vertex AI deployment and a message
            providing additional information about that state.
        """
        if not self.status.endpoint:
            return ServiceState.INACTIVE, "Endpoint not provisioned"

        try:
            endpoint = aiplatform.Endpoint(
                endpoint_name=self.status.endpoint.endpoint_name
            )
            deployments = endpoint.list_deployments()

            if not deployments:
                return ServiceState.INACTIVE, "No active deployments"

            # Check the state of all deployments
            for deployment in deployments:
                if deployment.state == "ACTIVE":
                    return ServiceState.ACTIVE, "Deployment is active"
                elif deployment.state == "DEPLOYING":
                    return (
                        ServiceState.PENDING_STARTUP,
                        "Deployment is in progress",
                    )
                elif deployment.state in ["FAILED", "DELETING"]:
                    return (
                        ServiceState.ERROR,
                        f"Deployment is in {deployment.state} state",
                    )

            return ServiceState.INACTIVE, "No active deployments found"

        except exceptions.NotFound:
            return ServiceState.INACTIVE, "Endpoint not found"
        except Exception as e:
            return ServiceState.ERROR, f"Error checking status: {str(e)}"

    def predict(self, instances: List[Any]) -> List[Any]:
        """Make a prediction using the service.

        Args:
            instances: List of instances to predict.

        Returns:
            The prediction results.

        Raises:
            Exception: if the service is not running or prediction fails.
        """
        if not self.is_running:
            raise Exception(
                "Vertex AI endpoint inference service is not running. "
                "Please start the service before making predictions."
            )

        if not self.status.endpoint:
            raise Exception("Endpoint information is missing.")

        try:
            endpoint = aiplatform.Endpoint(
                endpoint_name=self.status.endpoint.endpoint_name
            )
            response = endpoint.predict(instances=instances)
            return response.predictions
        except Exception as e:
            raise RuntimeError(f"Prediction failed: {str(e)}")

    def get_logs(
        self, follow: bool = False, tail: Optional[int] = None
    ) -> Generator[str, bool, None]:
        """Retrieve the service logs.

        Args:
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that can be accessed to get the service logs.
        """
        logger.info(
            "Vertex AI Endpoints provides access to the logs through "
            "Cloud Logging. Please check the Google Cloud Console for detailed logs."
        )
        yield "Logs are available in Google Cloud Console."

    @property
    def is_running(self) -> bool:
        """Check if the service is running.

        Returns:
            True if the service is in the ACTIVE state, False otherwise.
        """
        state, _ = self.check_status()
        return state == ServiceState.ACTIVE
