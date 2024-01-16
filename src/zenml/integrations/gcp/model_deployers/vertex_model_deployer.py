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
from typing import ClassVar, List, Optional, Type, cast
from uuid import UUID

from zenml.constants import DEFAULT_SERVICE_START_STOP_TIMEOUT
from zenml.integrations.gcp.flavors.vertex_model_deployer_flavor import (
    VertexModelDeployerConfig,
    VertexModelDeployerFlavor,
)
from zenml.logger import get_logger
from zenml.model_deployers import BaseModelDeployer, BaseModelDeployerFlavor
from zenml.services.service import BaseService, ServiceConfig

logger = get_logger(__name__)


class VertexModelDeployer(BaseModelDeployer):
    """Vertex AI model deployer stack component implementation."""

    NAME: ClassVar[str] = "VertexAI"
    FLAVOR: ClassVar[Type[BaseModelDeployerFlavor]] = VertexModelDeployerFlavor

    _service_path: Optional[str] = None

    @property
    def config(self) -> VertexModelDeployerConfig:
        """Returns the `BentoMLModelDeployerConfig` config.

        Returns:
            The configuration.
        """
        return cast(VertexModelDeployerConfig, self._config)

    def deploy_model(
        self,
        config: ServiceConfig,
        replace: bool = False,
        timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Create a new Vertex deployment service or update an existing one.

        This should serve the supplied model and deployment configuration.

        This method has two modes of operation, depending on the `replace`
        argument value:

          * if `replace` is False, calling this method will create a new BentoML
            deployment server to reflect the model and other configuration
            parameters specified in the supplied BentoML service `config`.

          * if `replace` is True, this method will first attempt to find an
            existing BentoML deployment service that is *equivalent* to the
            supplied configuration parameters. Two or more BentoML deployment
            services are considered equivalent if they have the same
            `pipeline_name`, `pipeline_step_name` and `model_name` configuration
            parameters. To put it differently, two BentoML deployment services
            are equivalent if they serve versions of the same model deployed by
            the same pipeline step. If an equivalent BentoML deployment is found,
            it will be updated in place to reflect the new configuration
            parameters.

        Callers should set `replace` to True if they want a continuous model
        deployment workflow that doesn't spin up a new BentoML deployment
        server for each new model version. If multiple equivalent BentoML
        deployment servers are found, one is selected at random to be updated
        and the others are deleted.

        Args:
            config: the configuration of the model to be deployed with BentoML.
            replace: set this flag to True to find and update an equivalent
                BentoML deployment server with the new model instead of
                creating and starting a new deployment server.
            timeout: the timeout in seconds to wait for the BentoML server
                to be provisioned and successfully started or updated. If set
                to 0, the method will return immediately after the BentoML
                server is provisioned, without waiting for it to fully start.

        Returns:
            The ZenML BentoML deployment service object that can be used to
            interact with the BentoML model http server.
        """
        raise NotImplementedError()

    def find_model_server(
        self,
        running: bool = False,
        service_uuid: Optional[UUID] = None,
        pipeline_name: Optional[str] = None,
        run_name: Optional[str] = None,
        pipeline_step_name: Optional[str] = None,
        model_name: Optional[str] = None,
        model_uri: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> List[BaseService]:
        """Finds one or more model servers that match the given criteria.

        Args:
            running: If true, only running services will be returned.
            service_uuid: The UUID of the service that was originally used
                to deploy the model.
            pipeline_name: Name of the pipeline that the deployed model was part
                of.
            run_name: ID of the pipeline run which the deployed model
                was part of.
            pipeline_step_name: The name of the pipeline model deployment step
                that deployed the model.
            model_name: Name of the deployed model.
            model_uri: URI of the deployed model.
            model_type: Type/format of the deployed model.

        Returns:
            One or more Service objects representing model servers that match
            the input search criteria.

        Raises:
            TypeError: if any of the input arguments are of an invalid type.
        """
        raise NotImplementedError()

    def stop_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Method to stop a model server.

        Args:
            uuid: UUID of the model server to stop.
            timeout: Timeout in seconds to wait for the service to stop.
            force: If True, force the service to stop.
        """
        raise NotImplementedError()

    def start_model_server(
        self, uuid: UUID, timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT
    ) -> None:
        """Method to start a model server.

        Args:
            uuid: UUID of the model server to start.
            timeout: Timeout in seconds to wait for the service to start.
        """
        raise NotImplementedError()

    def delete_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Method to delete all configuration of a model server.

        Args:
            uuid: UUID of the model server to delete.
            timeout: Timeout in seconds to wait for the service to stop.
            force: If True, force the service to stop.
        """
        raise NotImplementedError()
