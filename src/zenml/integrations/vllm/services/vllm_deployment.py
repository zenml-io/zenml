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

from argparse import Namespace
from typing import Any, Optional

from zenml.logger import get_logger
from zenml.services import (
    LocalDaemonService,
    LocalDaemonServiceConfig,
    ServiceType,
)
from zenml.services.service import BaseDeploymentService

logger = get_logger(__name__)


class VLLMServiceConfig(LocalDaemonServiceConfig):
    """vLLM service configurations."""

    model: str
    tokenizer: Optional[str]
    dtype: str = "auto"
    gpu_memory_utilization: float = 0.90
    tensor_parallel_size: int = 1

    # Note: There are additional parameters such as SSL parameters
    # Ref: https://github.com/vllm-project/vllm/blob/855c8ae2c9a4085b1ebd66d9a978fb23f47f822c/vllm/entrypoints/openai/api_server.py#L546
    host: str = "localhost"
    port: int = 8000

    # # Allow extra args
    # # More vllm args: https://github.com/vllm-project/vllm/blob/7c7714d856eee6fa94aade729b67f00584f72a4c/vllm/engine/arg_utils.py#L82
    # model_config = ConfigDict(extra="allow")


class VLLMDeploymentService(LocalDaemonService, BaseDeploymentService):
    """vLLM Inference Server Deployment Service."""

    SERVICE_TYPE = ServiceType(
        name="vllm-deployment",
        type="model-serving",
        flavor="vllm",
        description="vLLM Inference prediction service",
    )
    config: VLLMServiceConfig

    def __init__(self, config: VLLMServiceConfig, **attrs: Any):
        """Initialize the vLLM deployment service.

        Args:
            config: service configuration
            attrs: additional attributes to set on the service
        """
        super().__init__(config=config, **attrs)

    def run(self) -> None:
        """Start the service."""
        logger.info(
            "Starting vLLM inference server service as blocking "
            "process... press CTRL+C once to stop it."
        )
        args = Namespace(**self.config.model_dump())
        import uvloop
        from vllm.entrypoints.openai.api_server import run_server

        try:
            uvloop.run(run_server(args))
        except KeyboardInterrupt:
            logger.info("Stopping BentoML prediction service...")

    @property
    def prediction_url(self) -> Optional[str]:
        """Gets the prediction URL for the endpoint.

        Returns:
            the prediction URL for the endpoint
        """
        if not self.is_running:
            return None
        return f"http://{self.config.host}:{self.config.port}/v1"

    @property
    def healthcheck_url(self) -> Optional[str]:
        """Gets the healthcheck URL for the endpoint.

        Returns:
            the healthcheck URL for the endpoint
        """
        if not self.is_running:
            return None
        return f"http://{self.config.host}:{self.config.port}/health"

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
        if self.prediction_url is not None:
            from openai import OpenAI

            client = OpenAI(
                api_key="EMPTY",
                base_url=self.prediction_url,
            )
            models = client.models.list()
            model = models.data[0].id
            result = client.completions.create(model=model, prompt=data)
            # TODO: We can add support for client.chat.completions.create
        else:
            raise ValueError("No endpoint known for prediction.")
        return result
