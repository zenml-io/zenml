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
"""Implementation of the vLLM Inference Server Service."""

import os
from typing import Any, List, Optional, Union

from zenml.constants import DEFAULT_LOCAL_SERVICE_IP_ADDRESS
from zenml.logger import get_logger
from zenml.services import (
    HTTPEndpointHealthMonitor,
    HTTPEndpointHealthMonitorConfig,
    LocalDaemonService,
    LocalDaemonServiceConfig,
    LocalDaemonServiceEndpoint,
    LocalDaemonServiceEndpointConfig,
    ServiceEndpointProtocol,
    ServiceType,
)
from zenml.services.service import BaseDeploymentService

logger = get_logger(__name__)


VLLM_PREDICTION_URL_PATH = "v1"
VLLM_HEALTHCHECK_URL_PATH = "health"


class VLLMDeploymentEndpointConfig(LocalDaemonServiceEndpointConfig):
    """vLLM deployment service configuration.

    Attributes:
        prediction_url_path: URI subpath for prediction requests
    """

    prediction_url_path: str


class BentoMLDeploymentEndpoint(LocalDaemonServiceEndpoint):
    """A service endpoint exposed by the vLLM deployment daemon.

    Attributes:
        config: service endpoint configuration
    """

    config: VLLMDeploymentEndpointConfig
    monitor: HTTPEndpointHealthMonitor

    @property
    def prediction_url(self) -> Optional[str]:
        """Gets the prediction URL for the endpoint.

        Returns:
            the prediction URL for the endpoint
        """
        uri = self.status.uri
        if not uri:
            return None
        return os.path.join(uri, self.config.prediction_url_path)


class VLLMServiceConfig(LocalDaemonServiceConfig):
    """vLLM service configurations."""

    model: str
    port: int
    host: Optional[str] = None
    blocking: bool = True
    # If unspecified, model name or path will be used.
    tokenizer: Optional[str] = None
    served_model_name: Optional[Union[str, List[str]]] = None
    # Trust remote code from huggingface.
    trust_remote_code: Optional[bool] = False
    # ['auto', 'slow', 'mistral']
    tokenizer_mode: Optional[str] = "auto"
    # ['auto', 'half', 'float16', 'bfloat16', 'float', 'float32']
    dtype: Optional[str] = "auto"
    # The specific model version to use. It can be a branch name, a tag name, or a commit id.
    # If unspecified, will use the default version.
    revision: Optional[str] = None


class VLLMDeploymentService(LocalDaemonService, BaseDeploymentService):
    """vLLM Inference Server Deployment Service."""

    SERVICE_TYPE = ServiceType(
        name="vllm-deployment",
        type="model-serving",
        flavor="vllm",
        description="vLLM Inference prediction service",
    )
    config: VLLMServiceConfig
    endpoint: BentoMLDeploymentEndpoint

    def __init__(self, config: VLLMServiceConfig, **attrs: Any):
        """Initialize the vLLM deployment service.

        Args:
            config: service configuration
            attrs: additional attributes to set on the service
        """
        if isinstance(config, VLLMServiceConfig) and "endpoint" not in attrs:
            endpoint = BentoMLDeploymentEndpoint(
                config=VLLMDeploymentEndpointConfig(
                    protocol=ServiceEndpointProtocol.HTTP,
                    port=config.port,
                    ip_address=config.host or DEFAULT_LOCAL_SERVICE_IP_ADDRESS,
                    prediction_url_path=VLLM_PREDICTION_URL_PATH,
                ),
                monitor=HTTPEndpointHealthMonitor(
                    config=HTTPEndpointHealthMonitorConfig(
                        healthcheck_uri_path=VLLM_HEALTHCHECK_URL_PATH,
                    )
                ),
            )
            attrs["endpoint"] = endpoint
        super().__init__(config=config, **attrs)

    def run(self) -> None:
        """Start the service."""
        logger.info(
            "Starting vLLM inference server service as blocking "
            "process... press CTRL+C once to stop it."
        )

        self.endpoint.prepare_for_start()

        import uvloop
        from vllm.entrypoints.openai.api_server import run_server
        from vllm.entrypoints.openai.cli_args import make_arg_parser
        from vllm.utils import FlexibleArgumentParser

        try:
            parser = make_arg_parser(FlexibleArgumentParser())
            args = parser.parse_args()
            # Override port with the available port
            self.config.port = self.endpoint.status.port
            # Update the arguments in place
            args.__dict__.update(self.config.model_dump())
            uvloop.run(run_server(args=args))
        except KeyboardInterrupt:
            logger.info("Stopping vLLM prediction service...")

    @property
    def prediction_url(self) -> Optional[str]:
        """Gets the prediction URL for the endpoint.

        Returns:
            the prediction URL for the endpoint
        """
        if not self.is_running:
            return None
        return self.endpoint.prediction_url_path

    def predict(self, data: "Any") -> "Any":
        """Make a prediction using the service.

        Args:
            data: data to make a prediction on

        Returns:
            The prediction result.

        Raises:
            Exception: if the service is not running
            ValueError: if the prediction endpoint is unknown.
        """
        if not self.is_running:
            raise Exception(
                "vLLM Inference service is not running. "
                "Please start the service before making predictions."
            )
        if self.endpoint.prediction_url is not None:
            from openai import OpenAI

            client = OpenAI(
                api_key="EMPTY",
                base_url=self.endpoint.prediction_url,
            )
            models = client.models.list()
            model = models.data[0].id
            result = client.completions.create(model=model, prompt=data)
            # TODO: We can add support for client.chat.completions.create
        else:
            raise ValueError("No endpoint known for prediction.")
        return result
