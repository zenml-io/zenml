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
from pathlib import Path
from typing import ClassVar, Dict, List, Optional, Type, cast
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
from zenml.services import ServiceRegistry
from zenml.services.local.local_service import SERVICE_DAEMON_CONFIG_FILE_NAME
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
        }

    def deploy_model(
        self,
        config: ServiceConfig,
        replace: bool = False,
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
            config: the configuration of the model to be deployed with MLflow.
            replace: set this flag to True to find and update an equivalent
                MLflow deployment server with the new model instead of
                creating and starting a new deployment server.
            timeout: the timeout in seconds to wait for the MLflow server
                to be provisioned and successfully started or updated. If set
                to 0, the method will return immediately after the MLflow
                server is provisioned, without waiting for it to fully start.

        Returns:
            The ZenML MLflow deployment service object that can be used to
            interact with the MLflow model server.
        """
        config = cast(MLFlowDeploymentConfig, config)
        service = None

        # if replace is True, remove all existing services
        if replace is True:
            existing_services = self.find_model_server(
                pipeline_name=config.pipeline_name,
                pipeline_step_name=config.pipeline_step_name,
                model_name=config.model_name,
            )

            for existing_service in existing_services:
                if service is None:
                    # keep the most recently created service
                    service = cast(MLFlowDeploymentService, existing_service)
                try:
                    # delete the older services and don't wait for them to
                    # be deprovisioned
                    self._clean_up_existing_service(
                        existing_service=cast(
                            MLFlowDeploymentService, existing_service
                        ),
                        timeout=timeout,
                        force=True,
                    )
                except RuntimeError:
                    # ignore errors encountered while stopping old services
                    pass
        if service:
            logger.info(
                f"Updating an existing MLflow deployment service: {service}"
            )

            # set the root runtime path with the stack component's UUID
            config.root_runtime_path = self.local_path
            service.stop(timeout=timeout, force=True)
            service.update(config)
            service.start(timeout=timeout)
        else:
            # create a new MLFlowDeploymentService instance
            service = self._create_new_service(timeout, config)
            logger.info(f"Created a new MLflow deployment service: {service}")

        return cast(BaseService, service)

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
        self, timeout: int, config: MLFlowDeploymentConfig
    ) -> MLFlowDeploymentService:
        """Creates a new MLFlowDeploymentService.

        Args:
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
        service = MLFlowDeploymentService(config)
        service.start(timeout=timeout)

        return service

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
        registry_model_name: Optional[str] = None,
        registry_model_version: Optional[str] = None,
    ) -> List[BaseService]:
        """Finds one or more model servers that match the given criteria.

        Args:
            running: If true, only running services will be returned.
            service_uuid: The UUID of the service that was originally used
                to deploy the model.
            pipeline_name: Name of the pipeline that the deployed model was part
                of.
            run_name: Name of the pipeline run which the deployed model
                was part of.
            pipeline_step_name: The name of the pipeline model deployment step
                that deployed the model.
            model_name: Name of the deployed model.
            model_uri: URI of the deployed model.
            model_type: Type/format of the deployed model. Not used in this
                MLflow case.
            registry_model_name: Name of the registered model that the
                deployed model belongs to.
            registry_model_version: Version of the registered model that
                the deployed model belongs to.

        Returns:
            One or more Service objects representing model servers that match
            the input search criteria.

        Raises:
            TypeError: if any of the input arguments are of an invalid type.
        """
        services = []
        config = MLFlowDeploymentConfig(
            model_name=model_name or "",
            model_uri=model_uri or "",
            pipeline_name=pipeline_name or "",
            pipeline_run_id=run_name or "",
            run_name=run_name or "",
            pipeline_step_name=pipeline_step_name or "",
            registry_model_name=registry_model_name,
            registry_model_version=registry_model_version,
        )

        # find all services that match the input criteria
        for root, _, files in os.walk(self.local_path):
            if service_uuid and Path(root).name != str(service_uuid):
                continue
            for file in files:
                if file == SERVICE_DAEMON_CONFIG_FILE_NAME:
                    service_config_path = os.path.join(root, file)
                    logger.debug(
                        "Loading service daemon configuration from %s",
                        service_config_path,
                    )
                    existing_service_config = None
                    with open(service_config_path, "r") as f:
                        existing_service_config = f.read()
                    existing_service = (
                        ServiceRegistry().load_service_from_json(
                            existing_service_config
                        )
                    )
                    if not isinstance(
                        existing_service, MLFlowDeploymentService
                    ):
                        raise TypeError(
                            f"Expected service type MLFlowDeploymentService but got "
                            f"{type(existing_service)} instead"
                        )
                    existing_service.update_status()
                    if self._matches_search_criteria(existing_service, config):
                        if not running or existing_service.is_running:
                            services.append(
                                cast(BaseService, existing_service)
                            )

        return services

    def _matches_search_criteria(
        self,
        existing_service: MLFlowDeploymentService,
        config: MLFlowDeploymentConfig,
    ) -> bool:
        """Returns true if a service matches the input criteria.

        If any of the values in the input criteria are None, they are ignored.
        This allows listing services just by common pipeline names or step
        names, etc.

        Args:
            existing_service: The materialized Service instance derived from
                the config of the older (existing) service
            config: The MLFlowDeploymentConfig object passed to the
                deploy_model function holding parameters of the new service
                to be created.

        Returns:
            True if the service matches the input criteria.
        """
        existing_service_config = existing_service.config
        # check if the existing service matches the input criteria
        if (
            (
                not config.pipeline_name
                or existing_service_config.pipeline_name
                == config.pipeline_name
            )
            and (
                not config.model_name
                or existing_service_config.model_name == config.model_name
            )
            and (
                not config.pipeline_step_name
                or existing_service_config.pipeline_step_name
                == config.pipeline_step_name
            )
            and (
                not config.run_name
                or existing_service_config.run_name == config.run_name
            )
            and (
                (
                    not config.registry_model_name
                    and not config.registry_model_version
                )
                or (
                    existing_service_config.registry_model_name
                    == config.registry_model_name
                    and existing_service_config.registry_model_version
                    == config.registry_model_version
                )
            )
        ):
            return True

        return False

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
        # get list of all services
        existing_services = self.find_model_server(service_uuid=uuid)

        # if the service exists, stop it
        if existing_services:
            existing_services[0].stop(timeout=timeout, force=force)

    def start_model_server(
        self, uuid: UUID, timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT
    ) -> None:
        """Method to start a model server.

        Args:
            uuid: UUID of the model server to start.
            timeout: Timeout in seconds to wait for the service to start.
        """
        # get list of all services
        existing_services = self.find_model_server(service_uuid=uuid)

        # if the service exists, start it
        if existing_services:
            existing_services[0].start(timeout=timeout)

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
        # get list of all services
        existing_services = self.find_model_server(service_uuid=uuid)

        # if the service exists, clean it up
        if existing_services:
            service = cast(MLFlowDeploymentService, existing_services[0])
            self._clean_up_existing_service(
                existing_service=service, timeout=timeout, force=force
            )
