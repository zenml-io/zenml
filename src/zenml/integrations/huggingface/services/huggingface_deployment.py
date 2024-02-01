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
"""Implementation of the Huggingface Deployment service."""

from typing import Any, Generator, Optional, Tuple

from huggingface_hub import (
    InferenceClient,
    InferenceEndpoint,
    InferenceEndpointError,
    InferenceEndpointStatus,
    create_inference_endpoint,
    get_inference_endpoint,
)
from huggingface_hub.utils import HfHubHTTPError
from pydantic import Field

from zenml.integrations.huggingface.flavors.huggingface_model_deployer_flavor import (
    HuggingFaceBaseConfig,
)
from zenml.logger import get_logger
from zenml.services import ServiceState, ServiceStatus, ServiceType
from zenml.services.service import BaseDeploymentService, ServiceConfig

logger = get_logger(__name__)

POLLING_TIMEOUT = 1200


class HuggingFaceServiceConfig(HuggingFaceBaseConfig, ServiceConfig):
    """Huggingface service configurations.

    Attributes:
        model_name: the name of the model.
    """

    model_name: str = "default"


class HuggingFaceServiceStatus(ServiceStatus):
    """Huggingface service status."""


class HuggingFaceDeploymentService(BaseDeploymentService):
    """HuggingFace model deployment service.

    Attributes:
        SERVICE_TYPE: a service type descriptor with information describing
            the Huggingface deployment service class
        config: service configuration
    """

    SERVICE_TYPE = ServiceType(
        name="huggingface-deployment",
        type="model-serving",
        flavor="huggingface",
        description="Huggingface inference endpoint prediction service",
    )
    config: HuggingFaceServiceConfig
    status: HuggingFaceServiceStatus = Field(
        default_factory=lambda: HuggingFaceServiceStatus()
    )

    def __init__(self, config: HuggingFaceServiceConfig, **attrs: Any):
        """Initialize the Huggingface deployment service.

        Args:
            config: service configuration
            attrs: additional attributes to set on the service
        """
        super().__init__(config=config, **attrs)

    @property
    def hf_endpoint(self) -> InferenceEndpoint:
        """Get the deployed Huggingface inference endpoint.

        Returns:
            Huggingface inference endpoint.
        """
        return get_inference_endpoint(
            name=self.config.endpoint_name,
            token=self.config.token,
            namespace=self.config.namespace,
        )

    @property
    def prediction_url(self) -> Optional[str]:
        """The prediction URI exposed by the prediction service.

        Returns:
            The prediction URI exposed by the prediction service, or None if
            the service is not yet ready.
        """
        if not self.is_running:
            return None
        return self.hf_endpoint.url

    @property
    def inference_client(self) -> InferenceClient:
        """Get the Huggingface InferenceClient from Inference Endpoint.

        Returns:
            Huggingface inference client.
        """
        return self.hf_endpoint.client

    def provision(self) -> None:
        """Provision or update remote Huggingface deployment instance."""
        _ = create_inference_endpoint(
            name=self.config.endpoint_name,
            repository=self.config.repository,
            framework=self.config.framework,
            accelerator=self.config.accelerator,
            instance_size=self.config.instance_size,
            instance_type=self.config.instance_type,
            region=self.config.region,
            vendor=self.config.vendor,
            account_id=self.config.account_id,
            min_replica=self.config.min_replica,
            max_replica=self.config.max_replica,
            revision=self.config.revision,
            task=self.config.task,
            custom_image=self.config.custom_image,
            type=self.config.endpoint_type,
            namespace=self.config.namespace,
            token=self.config.token,
        ).wait(timeout=POLLING_TIMEOUT)

        if self.hf_endpoint.url is not None:
            logger.info("Huggingface inference endpoint successfully deployed.")
        else:
            logger.info("Failed to start huggingface inference endpoint service...")

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the the current operational state of the HuggingFace deployment.

        Returns:
            The operational state of the HuggingFace deployment and a message
            providing additional information about that state (e.g. a
            description of the error, if one is encountered).
        """
        # TODO: Support all different InferenceEndpointStatus
        try:
            _ = self.hf_endpoint.status
        except (InferenceEndpointError, HfHubHTTPError):
            return (ServiceState.INACTIVE, "")

        if self.hf_endpoint.status == InferenceEndpointStatus.RUNNING:
            return (
                ServiceState.ACTIVE,
                "HuggingFace Inference Endpoint deployment is available",
            )

        if self.hf_endpoint.status == InferenceEndpointStatus.SCALED_TO_ZERO:
            return (
                ServiceState.ACTIVE,
                "HuggingFace Inference Endpoint deployment is scaled to zero",
            )

        if self.hf_endpoint.status == InferenceEndpointStatus.FAILED:
            return (
                ServiceState.ERROR,
                "HuggingFace Inference Endpoint deployment failed: ",
            )

        if self.hf_endpoint.status == InferenceEndpointStatus.PENDING:
            return (
                ServiceState.PENDING_STARTUP,
                "HuggingFace Inference Endpoint deployment is being created: ",
            )

    def deprovision(self, force: bool = False) -> None:
        """Deprovision the remote HuggingFace deployment instance.

        Args:
            force: if True, the remote deployment instance will be
                forcefully deprovisioned.
        """
        try:
            self.hf_endpoint.delete()
        except HfHubHTTPError:
            logger.error(
                "Huggingface Inference Endpoint is deleted or cannot be found."
            )
            pass

    def predict(self, data: "Any", max_new_tokens: int) -> "Any":
        """Make a prediction using the service.

        Args:
            data: input data
            max_new_tokens: Number of new tokens to generate

        Returns:
            The prediction result.

        Raises:
            Exception: if the service is not running
            NotImplementedError: if task is not supported.
        """
        if not self.is_running:
            raise Exception(
                "Huggingface endpoint inference service is not running. "
                "Please start the service before making predictions."
            )
        if self.hf_endpoint.prediction_url is not None:
            if self.hf_endpoint.task == "text-generation":
                result = self.inference_client.task_generation(
                    data, max_new_tokens=max_new_tokens
                )
        else:
            # TODO: Add support for all different supported tasks
            raise NotImplementedError(
                "Tasks other than text-generation is not implemented."
            )
        return result

    def get_logs(
        self, follow: bool = False, tail: int = None
    ) -> Generator[str, bool, None]:
        """Retrieve the service logs.

        Args:
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that can be accessed to get the service logs.
        """
        return super().get_logs(follow, tail)
