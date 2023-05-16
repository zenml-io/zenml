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
from pathlib import Path
from typing import ClassVar, Dict, List, Optional, Type, cast
from uuid import UUID

from zenml.config.global_config import GlobalConfiguration
from zenml.constants import DEFAULT_SERVICE_START_STOP_TIMEOUT
from zenml.integrations.bentoml.constants import BENTOML_DEFAULT_PORT
from zenml.integrations.bentoml.flavors.bentoml_model_deployer_flavor import (
    BentoMLModelDeployerConfig,
    BentoMLModelDeployerFlavor,
)
from zenml.integrations.bentoml.services.bentoml_deployment import (
    BentoMLDeploymentConfig,
    BentoMLDeploymentService,
)
from zenml.logger import get_logger
from zenml.model_deployers import BaseModelDeployer, BaseModelDeployerFlavor
from zenml.services import ServiceRegistry
from zenml.services.local.local_service import SERVICE_DAEMON_CONFIG_FILE_NAME
from zenml.services.service import BaseService, ServiceConfig
from zenml.utils.io_utils import create_dir_recursive_if_not_exists

logger = get_logger(__name__)


class BentoMLModelDeployer(BaseModelDeployer):
    """BentoML model deployer stack component implementation."""

    NAME: ClassVar[str] = "BentoML"
    FLAVOR: ClassVar[
        Type[BaseModelDeployerFlavor]
    ] = BentoMLModelDeployerFlavor

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
    def get_model_server_info(  # type: ignore[override]
        service_instance: "BentoMLDeploymentService",
    ) -> Dict[str, Optional[str]]:
        """Return implementation specific information on the model server.

        Args:
            service_instance: BentoML deployment service object

        Returns:
            A dictionary containing the model server information.
        """
        predictions_apis_urls = ""
        if service_instance.prediction_apis_urls is not None:
            predictions_apis_urls = ", ".join(
                [
                    api
                    for api in service_instance.prediction_apis_urls
                    if api is not None
                ]
            )

        return {
            "PREDICTION_URL": service_instance.prediction_url,
            "BENTO_TAG": service_instance.config.bento,
            "MODEL_NAME": service_instance.config.model_name,
            "MODEL_URI": service_instance.config.model_uri,
            "BENTO_URI": service_instance.config.bento_uri,
            "SERVICE_PATH": service_instance.status.runtime_path,
            "DAEMON_PID": str(service_instance.status.pid),
            "PREDICTION_APIS_URLS": predictions_apis_urls,
        }

    def deploy_model(
        self,
        config: ServiceConfig,
        replace: bool = False,
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
        config = cast(BentoMLDeploymentConfig, config)
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
                    service = cast(BentoMLDeploymentService, existing_service)
                try:
                    # delete the older services and don't wait for them to
                    # be deprovisioned
                    self._clean_up_existing_service(
                        existing_service=cast(
                            BentoMLDeploymentService, existing_service
                        ),
                        timeout=timeout,
                        force=True,
                    )
                except RuntimeError:
                    # ignore errors encountered while stopping old services
                    pass
        if service:
            logger.info(
                f"Updating an existing BentoML deployment service: {service}"
            )

            # set the root runtime path with the stack component's UUID
            config.root_runtime_path = self.local_path
            service.stop(timeout=timeout, force=True)
            service.update(config)
            service.start(timeout=timeout)
        else:
            # create a new BentoMLDeploymentService instance
            service = self._create_new_service(timeout, config)
            logger.info(f"Created a new BentoML deployment service: {service}")

        return cast(BaseService, service)

    def _clean_up_existing_service(
        self,
        timeout: int,
        force: bool,
        existing_service: BentoMLDeploymentService,
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
        self, timeout: int, config: BentoMLDeploymentConfig
    ) -> BentoMLDeploymentService:
        """Creates a new BentoMLDeploymentService.

        Args:
            timeout: the timeout in seconds to wait for the BentoML http server
                to be provisioned and successfully started or updated.
            config: the configuration of the model to be deployed with BentoML.

        Returns:
            The BentoMLDeploymentService object that can be used to interact
            with the BentoML model server.
        """
        # set the root runtime path with the stack component's UUID
        config.root_runtime_path = self.local_path
        # create a new service for the new model
        service = BentoMLDeploymentService(config)
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
            model_type: Type/format of the deployed model. Not used in this
                BentoML case.

        Returns:
            One or more Service objects representing model servers that match
            the input search criteria.

        Raises:
            TypeError: if any of the input arguments are of an invalid type.
        """
        services = []
        config = BentoMLDeploymentConfig(
            model_name=model_name or "",
            bento="",
            port=BENTOML_DEFAULT_PORT,
            model_uri=model_uri or "",
            working_dir="",
            pipeline_name=pipeline_name or "",
            pipeline_run_id=run_name or "",
            run_name=run_name or "",
            pipeline_step_name=pipeline_step_name or "",
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
                        existing_service, BentoMLDeploymentService
                    ):
                        raise TypeError(
                            f"Expected service type BentoMLDeploymentService but got "
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
        existing_service: BentoMLDeploymentService,
        config: BentoMLDeploymentConfig,
    ) -> bool:
        """Returns true if a service matches the input criteria.

        If any of the values in the input criteria are None, they are ignored.
        This allows listing services just by common pipeline names or step
        names, etc.

        Args:
            existing_service: The materialized Service instance derived from
                the config of the older (existing) service
            config: The BentoMlDeploymentConfig object passed to the
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
            service = cast(BentoMLDeploymentService, existing_services[0])
            self._clean_up_existing_service(
                existing_service=service, timeout=timeout, force=force
            )
