#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Zen Server terraform deployer implementation."""

import os
from typing import ClassVar, List, Optional, Tuple, Type, cast

from zenml.enums import ServerProviderType
from zenml.logger import get_logger
from zenml.services import BaseService, ServiceConfig
from zenml.services.service_endpoint import (
    ServiceEndpointConfig,
    ServiceEndpointProtocol,
)
from zenml.services.service_monitor import (
    HTTPEndpointHealthMonitorConfig,
    ServiceEndpointHealthMonitorConfig,
)
from zenml.zen_server.deploy.base_provider import BaseServerProvider
from zenml.zen_server.deploy.deployment import ServerDeploymentConfig
from zenml.zen_server.deploy.docker.docker_zen_server import (
    ZEN_SERVER_HEALTHCHECK_URL_PATH,
)
from zenml.zen_server.deploy.terraform.terraform_zen_server import (
    TERRAFORM_VALUES_FILE_PATH,
    TERRAFORM_ZENML_SERVER_CONFIG_PATH,
    TERRAFORM_ZENML_SERVER_DEFAULT_TIMEOUT,
    TERRAFORM_ZENML_SERVER_RECIPE_ROOT_PATH,
    TerraformServerDeploymentConfig,
    TerraformZenServer,
    TerraformZenServerConfig,
)

logger = get_logger(__name__)


class TerraformServerProvider(BaseServerProvider):
    """Docker ZenML server provider."""

    TYPE: ClassVar[ServerProviderType] = ServerProviderType.TERRAFORM
    CONFIG_TYPE: ClassVar[  # TODO How do I handle individual recipe configs here?
        Type[ServerDeploymentConfig]
    ] = TerraformServerDeploymentConfig

    @classmethod
    def _get_service_configuration(
        cls,
        server_config: ServerDeploymentConfig,
    ) -> Tuple[
        ServiceConfig,
        ServiceEndpointConfig,
        ServiceEndpointHealthMonitorConfig,
    ]:
        """Construct the service configuration from a server deployment configuration.

        Args:
            server_config: server deployment configuration.

        Returns:
            The service configuration.
        """
        assert isinstance(server_config, TerraformServerDeploymentConfig)

        return (
            TerraformZenServerConfig(
                root_runtime_path=TERRAFORM_ZENML_SERVER_CONFIG_PATH,
                singleton=True,
                directory_path=os.path.join(
                    TERRAFORM_ZENML_SERVER_RECIPE_ROOT_PATH, server_config.type
                ),
                log_level=server_config.log_level,
                variables_file_path=TERRAFORM_VALUES_FILE_PATH,
                server=server_config,
            ),
            ServiceEndpointConfig(
                protocol=ServiceEndpointProtocol.HTTP,
                allocate_port=False,
            ),
            HTTPEndpointHealthMonitorConfig(
                healthcheck_uri_path=ZEN_SERVER_HEALTHCHECK_URL_PATH,
                use_head_request=True,
            ),
        )

    def _create_service(
        self,
        config: ServerDeploymentConfig,
        timeout: Optional[int] = None,
    ) -> BaseService:
        """Create, start and return the terraform ZenML server deployment service.

        Args:
            config: The server deployment configuration.
            timeout: The timeout in seconds to wait until the service is
                running.

        Returns:
            The service instance.

        Raises:
            RuntimeError: If a terraform service is already running.
        """
        assert isinstance(config, TerraformServerDeploymentConfig)

        if timeout is None:
            timeout = TERRAFORM_ZENML_SERVER_DEFAULT_TIMEOUT

        existing_service = TerraformZenServer.get_service()
        if existing_service:
            raise RuntimeError(
                f"A terraform ZenML server with name '{existing_service.config.name}' "
                f"is already running. Please stop it first before starting a "
                f"new one."
            )

        (
            service_config,
            endpoint_cfg,
            monitor_cfg,
        ) = self._get_service_configuration(config)

        service = TerraformZenServer(config=service_config)

        service.start(timeout=timeout)
        return service

    def _update_service(
        self,
        service: BaseService,
        config: ServerDeploymentConfig,
        timeout: Optional[int] = None,
    ) -> BaseService:
        """Update the terraform ZenML server deployment service.

        Args:
            service: The service instance.
            config: The new server deployment configuration.
            timeout: The timeout in seconds to wait until the updated service is
                running.

        Returns:
            The updated service instance.
        """
        if timeout is None:
            timeout = TERRAFORM_ZENML_SERVER_DEFAULT_TIMEOUT

        (
            new_config,
            endpoint_cfg,
            monitor_cfg,
        ) = self._get_service_configuration(config)

        service.stop(timeout=timeout)
        service.config = new_config
        service.start(timeout=timeout)

        return service

    def _start_service(
        self,
        service: BaseService,
        timeout: Optional[int] = None,
    ) -> BaseService:
        """Start the terraform ZenML server deployment service.

        Args:
            service: The service instance.
            timeout: The timeout in seconds to wait until the service is
                running.

        Returns:
            The updated service instance.
        """
        if timeout is None:
            timeout = TERRAFORM_ZENML_SERVER_DEFAULT_TIMEOUT

        service.start(timeout=timeout)
        return service

    def _stop_service(
        self,
        service: BaseService,
        timeout: Optional[int] = None,
    ) -> BaseService:
        """Stop the terraform ZenML server deployment service.

        Args:
            service: The service instance.
            timeout: The timeout in seconds to wait until the service is
                stopped.

        Returns:
            The updated service instance.
        """
        if timeout is None:
            timeout = TERRAFORM_ZENML_SERVER_DEFAULT_TIMEOUT

        service.stop(timeout=timeout)
        return service

    def _delete_service(
        self,
        service: BaseService,
        timeout: Optional[int] = None,
    ) -> None:
        """Remove the terraform ZenML server deployment service.

        Args:
            service: The service instance.
            timeout: The timeout in seconds to wait until the service is
                removed.
        """
        assert isinstance(service, TerraformZenServer)

        if timeout is None:
            timeout = TERRAFORM_ZENML_SERVER_DEFAULT_TIMEOUT

        service.stop(timeout)

    def _get_service(self, server_name: str) -> BaseService:
        """Get the terraform ZenML server deployment service.

        Args:
            server_name: The server deployment name.

        Returns:
            The service instance.

        Raises:
            KeyError: If the server deployment is not found.
        """
        service = TerraformZenServer.get_service()
        if service is None:
            raise KeyError("The terraform ZenML server is not deployed.")

        if service.config.name != server_name:
            raise KeyError(
                "The terraform ZenML server is deployed but with a different name."
            )

        return service

    def _list_services(self) -> List[BaseService]:
        """Get all service instances for all deployed ZenML servers.

        Returns:
            A list of service instances.
        """
        service = TerraformZenServer.get_service()
        if service:
            return [service]
        return []

    def _get_deployment_config(
        self, service: BaseService
    ) -> ServerDeploymentConfig:
        """Recreate the server deployment configuration from a service instance.

        Args:
            service: The service instance.

        Returns:
            The server deployment configuration.
        """
        server = cast(TerraformZenServer, service)
        return server.config.server


TerraformServerProvider.register_as_provider()
