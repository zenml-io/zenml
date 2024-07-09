#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Implementation of the MLflow model deployer."""

import os
import shutil
from typing import ClassVar, Dict, Optional, Type, cast
from uuid import UUID

from zenml.config.global_config import GlobalConfiguration
from zenml.constants import DEFAULT_SERVICE_START_STOP_TIMEOUT
from zenml.integrations.mlflow.flavors.mlflow_model_deployer_flavor import (
    MLFlowModelDeployerConfig,
    MLFlowModelDeployerFlavor,
)
from zenml.integrations.mlflow.services.mlflow_deployment import (
    MLFlowDeploymentConfig,
    MLFlowDeploymentService,
)
from zenml.logger import get_logger
from zenml.model_deployers import BaseModelDeployer, BaseModelDeployerFlavor
from zenml.services.service import BaseService, ServiceConfig
from zenml.utils.io_utils import create_dir_recursive_if_not_exists

logger = get_logger(__name__)


class MLFlowModelDeployer(BaseModelDeployer):
    """MLflow implementation of the BaseModelDeployer."""

    NAME: ClassVar[str] = "MLflow"
    FLAVOR: ClassVar[Type[BaseModelDeployerFlavor]] = MLFlowModelDeployerFlavor

    _service_path: Optional[str] = None

    @property
    def config(self) -> MLFlowModelDeployerConfig:
        """Returns the `MLFlowModelDeployerConfig` config.

        Returns:
            The configuration.
        """
        return cast(MLFlowModelDeployerConfig, self._config)

    @staticmethod
    def get_service_path(id_: UUID) -> str:
        """Get the path where local MLflow service information is stored.

        This includes the deployment service configuration, PID and log files
        are stored.

        Args:
            id_: The ID of the MLflow model deployer.

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

        This is where all configurations for MLflow deployment daemon processes
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
    def get_model_server_info(  # type: ignore[override]
        service_instance: "MLFlowDeploymentService",
    ) -> Dict[str, Optional[str]]:
        """Return implementation specific information relevant to the user.

        Args:
            service_instance: Instance of a SeldonDeploymentService

        Returns:
            A dictionary containing the information.
        """
        return {
            "PREDICTION_URL": service_instance.endpoint.prediction_url,
            "MODEL_URI": service_instance.config.model_uri,
            "MODEL_NAME": service_instance.config.model_name,
            "REGISTRY_MODEL_NAME": service_instance.config.registry_model_name,
            "REGISTRY_MODEL_VERSION": service_instance.config.registry_model_version,
            "SERVICE_PATH": service_instance.status.runtime_path,
            "DAEMON_PID": str(service_instance.status.pid),
            "HEALTH_CHECK_URL": service_instance.endpoint.monitor.get_healthcheck_uri(
                service_instance.endpoint
            ),
        }

    def perform_deploy_model(
        self,
        id: UUID,
        config: ServiceConfig,
        timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Create a new MLflow deployment service or update an existing one.

        This should serve the supplied model and deployment configuration.

        This method has two modes of operation, depending on the `replace`
        argument value:

          * if `replace` is False, calling this method will create a new MLflow
            deployment server to reflect the model and other configuration
            parameters specified in the supplied MLflow service `config`.

          * if `replace` is True, this method will first attempt to find an
            existing MLflow deployment service that is *equivalent* to the
            supplied configuration parameters. Two or more MLflow deployment
            services are considered equivalent if they have the same
            `pipeline_name`, `pipeline_step_name` and `model_name` configuration
            parameters. To put it differently, two MLflow deployment services
            are equivalent if they serve versions of the same model deployed by
            the same pipeline step. If an equivalent MLflow deployment is found,
            it will be updated in place to reflect the new configuration
            parameters.

        Callers should set `replace` to True if they want a continuous model
        deployment workflow that doesn't spin up a new MLflow deployment
        server for each new model version. If multiple equivalent MLflow
        deployment servers are found, one is selected at random to be updated
        and the others are deleted.

        Args:
            id: the ID of the MLflow deployment service to be created or updated.
            config: the configuration of the model to be deployed with MLflow.
            timeout: the timeout in seconds to wait for the MLflow server
                to be provisioned and successfully started or updated. If set
                to 0, the method will return immediately after the MLflow
                server is provisioned, without waiting for it to fully start.

        Returns:
            The ZenML MLflow deployment service object that can be used to
            interact with the MLflow model server.
        """
        config = cast(MLFlowDeploymentConfig, config)
        service = self._create_new_service(
            id=id, timeout=timeout, config=config
        )
        logger.info(f"Created a new MLflow deployment service: {service}")
        return service

    def _clean_up_existing_service(
        self,
        timeout: int,
        force: bool,
        existing_service: MLFlowDeploymentService,
    ) -> None:
        # stop the older service
        existing_service.stop(timeout=timeout, force=force)

        # delete the old configuration file
        if existing_service.status.runtime_path:
            shutil.rmtree(existing_service.status.runtime_path)

    # the step will receive a config from the user that mentions the number
    # of workers etc.the step implementation will create a new config using
    # all values from the user and add values like pipeline name, model_uri
    def _create_new_service(
        self, id: UUID, timeout: int, config: MLFlowDeploymentConfig
    ) -> MLFlowDeploymentService:
        """Creates a new MLFlowDeploymentService.

        Args:
            id: the ID of the MLflow deployment service to be created or updated.
            timeout: the timeout in seconds to wait for the MLflow server
                to be provisioned and successfully started or updated.
            config: the configuration of the model to be deployed with MLflow.

        Returns:
            The MLFlowDeploymentService object that can be used to interact
            with the MLflow model server.
        """
        # set the root runtime path with the stack component's UUID
        config.root_runtime_path = self.local_path
        # create a new service for the new model
        service = MLFlowDeploymentService(uuid=id, config=config)
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
            The service that was stopped.
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
            The service that was started.
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
        service = cast(MLFlowDeploymentService, service)
        self._clean_up_existing_service(
            existing_service=service, timeout=timeout, force=force
        )
