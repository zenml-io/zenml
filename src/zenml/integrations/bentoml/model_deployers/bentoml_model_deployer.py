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
"""Implementation of the BentoML Model Deployer."""

import os
import shutil
from typing import ClassVar, Dict, Optional, Type, cast
from uuid import UUID

from zenml.config.global_config import GlobalConfiguration
from zenml.constants import DEFAULT_SERVICE_START_STOP_TIMEOUT
from zenml.integrations.bentoml.flavors.bentoml_model_deployer_flavor import (
    BentoMLModelDeployerConfig,
    BentoMLModelDeployerFlavor,
)
from zenml.integrations.bentoml.services.bentoml_container_deployment import (
    BentoMLContainerDeploymentConfig,
    BentoMLContainerDeploymentService,
)
from zenml.integrations.bentoml.services.bentoml_local_deployment import (
    BentoMLLocalDeploymentConfig,
    BentoMLLocalDeploymentService,
)
from zenml.logger import get_logger
from zenml.model_deployers import BaseModelDeployer, BaseModelDeployerFlavor
from zenml.services.container.container_service import ContainerServiceStatus
from zenml.services.local.local_service import LocalDaemonServiceStatus
from zenml.services.service import BaseService, ServiceConfig
from zenml.utils.io_utils import create_dir_recursive_if_not_exists

logger = get_logger(__name__)


class BentoMLModelDeployer(BaseModelDeployer):
    """BentoML model deployer stack component implementation."""

    NAME: ClassVar[str] = "BentoML"
    FLAVOR: ClassVar[Type[BaseModelDeployerFlavor]] = (
        BentoMLModelDeployerFlavor
    )

    _service_path: Optional[str] = None

    @property
    def config(self) -> BentoMLModelDeployerConfig:
        """Returns the `BentoMLModelDeployerConfig` config.

        Returns:
            The configuration.
        """
        return cast(BentoMLModelDeployerConfig, self._config)

    @staticmethod
    def get_service_path(id_: UUID) -> str:
        """Get the path where local BentoML service information is stored.

        This includes the deployment service configuration, PID and log files
        are stored.

        Args:
            id_: The ID of the BentoML model deployer.

        Returns:
            The service path.
        """
        service_path = os.path.join(
            GlobalConfiguration().local_stores_path,
            str(id_),
        )
        create_dir_recursive_if_not_exists(service_path)
        return service_path

    @property
    def local_path(self) -> str:
        """Returns the path to the root directory.

        This is where all configurations for BentoML deployment daemon processes
        are stored.

        If the service path is not set in the config by the user, the path is
        set to a local default path according to the component ID.

        Returns:
            The path to the local service root directory.
        """
        if self._service_path is not None:
            return self._service_path

        if self.config.service_path:
            self._service_path = self.config.service_path
        else:
            self._service_path = self.get_service_path(self.id)

        create_dir_recursive_if_not_exists(self._service_path)
        return self._service_path

    @staticmethod
    def get_model_server_info(
        service_instance: BaseService,
    ) -> Dict[str, Optional[str]]:
        """Return implementation specific information on the model server.

        Args:
            service_instance: BentoML deployment service object

        Returns:
            A dictionary containing the model server information.

        Raises:
            ValueError: If the service type is not supported.
        """
        if (
            service_instance.SERVICE_TYPE.name
            == "bentoml-container-deployment"
        ):
            service_instance = cast(
                BentoMLContainerDeploymentService, service_instance
            )
        elif service_instance.SERVICE_TYPE.name == "bentoml-local-deployment":
            service_instance = cast(
                BentoMLLocalDeploymentService, service_instance
            )
        else:
            raise ValueError(
                f"Unsupported service type: {service_instance.SERVICE_TYPE.name}"
            )

        predictions_apis_urls = ""
        if service_instance.prediction_apis_urls is not None:  # type: ignore
            predictions_apis_urls = ", ".join(
                [
                    api
                    for api in service_instance.prediction_apis_urls  # type: ignore
                    if api is not None
                ]
            )

        service_config = service_instance.config
        assert isinstance(
            service_config,
            (BentoMLLocalDeploymentConfig, BentoMLContainerDeploymentConfig),
        )

        service_status = service_instance.status
        assert isinstance(
            service_status, (ContainerServiceStatus, LocalDaemonServiceStatus)
        )

        return {
            "HEALTH_CHECK_URL": service_instance.get_healthcheck_url(),
            "PREDICTION_URL": service_instance.get_prediction_url(),
            "BENTO_TAG": service_config.bento_tag,
            "MODEL_NAME": service_config.model_name,
            "MODEL_URI": service_config.model_uri,
            "BENTO_URI": service_config.bento_uri,
            "SERVICE_PATH": service_status.runtime_path,
            "DAEMON_PID": str(service_status.pid)
            if hasattr(service_status, "pid")
            else None,
            "PREDICTION_APIS_URLS": predictions_apis_urls,
        }

    def perform_deploy_model(
        self,
        id: UUID,
        config: ServiceConfig,
        timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Create a new BentoML deployment service or update an existing one.

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
            id: the UUID of the BentoML model deployer.
            config: the configuration of the model to be deployed with BentoML.
            timeout: the timeout in seconds to wait for the BentoML server
                to be provisioned and successfully started or updated. If set
                to 0, the method will return immediately after the BentoML
                server is provisioned, without waiting for it to fully start.

        Returns:
            The ZenML BentoML deployment service object that can be used to
            interact with the BentoML model http server.
        """
        service = self._create_new_service(
            id=id, timeout=timeout, config=config
        )
        logger.info(f"Created a new BentoML deployment service: {service}")
        return service

    def _clean_up_existing_service(
        self,
        timeout: int,
        force: bool,
        existing_service: BaseService,
    ) -> None:
        # stop the older service
        existing_service.stop(timeout=timeout, force=force)

        # assert that the service is either a BentoMLLocalDeploymentService or a BentoMLContainerDeploymentService
        if not isinstance(
            existing_service,
            (BentoMLLocalDeploymentService, BentoMLContainerDeploymentService),
        ):
            raise ValueError(
                f"Unsupported service type: {type(existing_service)}"
            )

        # delete the old configuration file
        if existing_service.status.runtime_path:
            shutil.rmtree(existing_service.status.runtime_path)

    # the step will receive a config from the user that mentions the number
    # of workers etc.the step implementation will create a new config using
    # all values from the user and add values like pipeline name, model_uri
    def _create_new_service(
        self, id: UUID, timeout: int, config: ServiceConfig
    ) -> BaseService:
        """Creates a new BentoMLDeploymentService.

        Args:
            id: the ID of the BentoML deployment service to be created or updated.
            timeout: the timeout in seconds to wait for the BentoML server
                to be provisioned and successfully started or updated.
            config: the configuration of the model to be deployed with BentoML.

        Returns:
            The BentoMLDeploymentService object that can be used to interact
            with the BentoML model server.

        Raises:
            ValueError: If the service type is not supported.
        """
        assert isinstance(
            config,
            (BentoMLLocalDeploymentConfig, BentoMLContainerDeploymentConfig),
        )
        # set the root runtime path with the stack component's UUID
        config.root_runtime_path = self.local_path
        # create a new service for the new model
        # if the config is of type BentoMLLocalDeploymentConfig, create a
        # BentoMLLocalDeploymentService, otherwise create a
        # BentoMLContainerDeploymentService
        service: BaseService
        if isinstance(config, BentoMLLocalDeploymentConfig):
            service = BentoMLLocalDeploymentService(uuid=id, config=config)
        elif isinstance(config, BentoMLContainerDeploymentConfig):
            service = BentoMLContainerDeploymentService(uuid=id, config=config)
        else:
            raise ValueError(f"Unsupported service type: {type(config)}")
        service.start(timeout=timeout)

        return service

    def perform_stop_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT,
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
        timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT,
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
        timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Method to delete all configuration of a model server.

        Args:
            service: The service to delete.
            timeout: Timeout in seconds to wait for the service to stop.
            force: If True, force the service to stop.
        """
        self._clean_up_existing_service(
            existing_service=service, timeout=timeout, force=force
        )
