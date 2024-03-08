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
"""Implementation of the Hugging Face Deployment service."""

import os
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
    """Hugging Face service configurations.

    Attributes:
        model_name: the name of the model.
    """

    model_name: str = "default"


class HuggingFaceServiceStatus(ServiceStatus):
    """Hugging Face service status."""


class HuggingFaceDeploymentService(BaseDeploymentService):
    """Hugging Face model deployment service.

    Attributes:
        SERVICE_TYPE: a service type descriptor with information describing
            the Hugging Face deployment service class
        config: service configuration
    """

    SERVICE_TYPE = ServiceType(
        name="huggingface-deployment",
        type="model-serving",
        flavor="huggingface",
        description="Hugging Face inference endpoint prediction service",
    )
    config: HuggingFaceServiceConfig
    status: HuggingFaceServiceStatus = Field(
        default_factory=lambda: HuggingFaceServiceStatus()
    )

    def __init__(self, config: HuggingFaceServiceConfig, **attrs: Any):
        """Initialize the Hugging Face deployment service.

        Args:
            config: service configuration
            attrs: additional attributes to set on the service
        """
        super().__init__(config=config, **attrs)

    @property
    def hf_endpoint(self) -> InferenceEndpoint:
        """Get the deployed Hugging Face inference endpoint.

        Returns:
            Huggingface inference endpoint.
        """
        return get_inference_endpoint(
            name=self.config.endpoint_name,
            token=os.environ.get("HF_TOKEN"),
            namespace=self.config.namespace or os.environ.get("HF_NAMESPACE"),
        )

    @property
    def prediction_url(self) -> Any:
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
        """Get the Hugging Face InferenceClient from Inference Endpoint.

        Returns:
            Hugging Face inference client.
        """
        return self.hf_endpoint.client

    def provision(self) -> None:
        """Provision or update remote Hugging Face deployment instance.

        Raises:
            Exception: If any unexpected error while creating inference endpoint.
        """
        try:
            # Attempt to create and wait for the inference endpoint
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
                token=os.environ.get("HF_TOKEN"),
                namespace=self.config.namespace
                or os.environ.get("HF_NAMESPACE"),
            ).wait(timeout=POLLING_TIMEOUT)

            # Check if the endpoint URL is available after provisioning
            if self.hf_endpoint.url is not None:
                logger.info(
                    "Hugging Face inference endpoint successfully deployed."
                )
            else:
                logger.error(
                    "Failed to start Hugging Face inference endpoint service: No URL available."
                )

        except Exception as e:
            self.status.update_state(
                new_state=ServiceState.ERROR, error=str(e)
            )
            # Catch-all for any other unexpected errors
            raise Exception(
                f"An unexpected error occurred while provisioning the Hugging Face inference endpoint: {e}"
            )

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the the current operational state of the Hugging Face deployment.

        Returns:
            The operational state of the Hugging Face deployment and a message
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
                "Hugging Face Inference Endpoint deployment is available",
            )

        elif self.hf_endpoint.status == InferenceEndpointStatus.SCALED_TO_ZERO:
            return (
                ServiceState.ACTIVE,
                "Hugging Face Inference Endpoint deployment is scaled to zero",
            )

        elif self.hf_endpoint.status == InferenceEndpointStatus.FAILED:
            return (
                ServiceState.ERROR,
                "Hugging Face Inference Endpoint deployment failed: ",
            )

        elif self.hf_endpoint.status == InferenceEndpointStatus.PENDING:
            return (
                ServiceState.PENDING_STARTUP,
                "Hugging Face Inference Endpoint deployment is being created: ",
            )
        return (
            ServiceState.PENDING_STARTUP,
            "Hugging Face Inference Endpoint deployment is being created: ",
        )

    def deprovision(self, force: bool = False) -> None:
        """Deprovision the remote Hugging Face deployment instance.

        Args:
            force: if True, the remote deployment instance will be
                forcefully deprovisioned.
        """
        try:
            self.hf_endpoint.delete()
        except HfHubHTTPError:
            logger.error(
                "Hugging Face Inference Endpoint is deleted or cannot be found."
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
                "Hugging Face endpoint inference service is not running. "
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
            "Hugging Face Endpoints provides access to the logs of "
            "your Endpoints through the UI in the “Logs” tab of your Endpoint"
        )
        return  # type: ignore
