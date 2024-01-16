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
"""Implementation for the Vertex inference service."""

"""Implementation for the Vertex Deployer service."""

from typing import Any, Dict, Generator, Optional

from pydantic import Field

from zenml.logger import get_logger
from zenml.services.service import BaseDeploymentService, ServiceConfig
from zenml.services.service_status import ServiceStatus
from zenml.services.service_type import ServiceType

logger = get_logger(__name__)


class VertexDeploymentConfig(ServiceConfig):
    """"""

    # Misc args
    env: Dict[str, str] = {}


class VertexDeploymentServiceStatus(ServiceStatus):
    """HF Sagemaker deployment service status."""


class VertexDeploymentService(BaseDeploymentService):
    """A service that represents a Vertex deployment server.

    Attributes:
        config: service configuration.
        status: service status.
    """

    SERVICE_TYPE = ServiceType(
        name="vertex-deployment",
        type="model-serving",
        flavor="gcp",
        description="Vertex deployment service.",
    )

    config: VertexDeploymentConfig
    status: VertexDeploymentServiceStatus = Field(
        default_factory=lambda: VertexDeploymentServiceStatus()
    )

    @property
    def endpoint_name(self) -> str:
        """Get the name of the endpoint from sagemaker.

        It should return the one that uniquely corresponds to this service instance.

        Returns:
            The endpoint name of the deployed predictor.
        """
        return f"zenml-{str(self.uuid)}"

    def provision(self) -> None:
        """Provision or update remote Vertex deployment instance.

        This should then match the current configuration.
        """
        raise NotImplementedError()

    def deprovision(self, force: bool = False) -> None:
        """Deprovision the remote Vertex deployment instance.

        Args:
            force: if True, the remote deployment instance will be
                forcefully deprovisioned.
        """
        raise NotImplementedError()

    def get_logs(
        self,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get the logs of a Vertex model deployment.

        Args:
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that can be accessed to get the service logs.
        """
        raise NotImplementedError()

    @property
    def prediction_url(self) -> Optional[str]:
        """The prediction URI exposed by the prediction service.

        Returns:
            The prediction URI exposed by the prediction service, or None if
            the service is not yet ready.
        """
        raise NotImplementedError()

    def predict(self, request: str) -> Any:
        """Make a prediction using the service.

        Args:
            request: a numpy array representing the request

        Returns:
            A numpy array representing the prediction returned by the service.

        Raises:
            Exception: if the service is not yet ready.
            ValueError: if the prediction_url is not set.
        """
        raise NotImplementedError()
