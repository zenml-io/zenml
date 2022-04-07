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
import os
import shutil
from typing import List, Optional
from uuid import UUID

from zenml.logger import get_logger
from zenml.constants import (
    DEFAULT_SERVICE_START_STOP_TIMEOUT,
    LOCAL_STORES_DIRECTORY_NAME,
)
from zenml.enums import ModelDeployerFlavor, StackComponentType
from zenml.integrations.mlflow.services.mlflow_deployment import (
    MLFlowDeploymentConfig,
    MLFlowDeploymentService,
)
from zenml.io.utils import get_global_config_directory
from zenml.model_deployers.base_model_deployer import BaseModelDeployer
from zenml.services import ServiceRegistry
from zenml.services.local.local_service import SERVICE_DAEMON_CONFIG_FILE_NAME
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)

logger = get_logger(__name__)


@register_stack_component_class(
    component_type=StackComponentType.MODEL_DEPLOYER,
    component_flavor=ModelDeployerFlavor.MLFLOW,
)
class MLFlowModelDeployer(BaseModelDeployer):
    """MLflow implementation of the BaseModelDeployer"""

    @property
    def type(self) -> StackComponentType:
        """The component type."""
        return StackComponentType.MODEL_DEPLOYER

    @property
    def flavor(self) -> ModelDeployerFlavor:
        """The model deployer flavor."""
        return ModelDeployerFlavor.MLFLOW

    def deploy_model(
        self,
        config: MLFlowDeploymentConfig,
        replace: bool = False,
        timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT,
    ) -> MLFlowDeploymentService:
        """

        We assume that the deployment decision is made at the step level and
        here we have to delete any older services that are running and start
        a new one.

        This method interacts with external serving platforms that manage services.
        In the case of MLflow, we need to look into the local filesystem at a location
        where the configuration for the service is stored. Retrieving that, we can
        check if there's any service that was created for the existing model and
        can return that or create one depending on the value of replace.

        - Detect if there is an existing model server instance running serving
        one or more previous versions of the same model
        - Deploy the model to the serving platform or update the existing model
        server instance to include the new model version
        - Return a Service object that is a representation of the external model
        server instance. The Service must implement basic operational state
        tracking and lifecycle management operations for the model server (e.g.
        start, stop, etc.)

        Args:
            replace: If true, the existing services will be replaced with the new one.
            config: The MLFlowDeploymentConfig object holding the parameters for the
                new service to be created.
            timeout: The timeout in seconds for the service to start.

        Returns:
            The MLFlowDeploymentService object.
        """

        # if replace is True, remove all existing services
        if replace is True:
            existing_services = self.find_model_server(
                pipeline_name=config.pipeline_name,
                pipeline_step_name=config.pipeline_step_name,
                model_name=config.model_name,
            )

            for service in existing_services:
                self._clean_up_existing_service(
                    timeout=timeout, force=True, existing_service=service
                )

        # create a new MLFlowDeploymentService instance
        return self._create_new_service(timeout, config)

    def _clean_up_existing_service(
        self,
        timeout: int,
        force: bool,
        existing_service: MLFlowDeploymentService,
    ) -> None:
        # stop the older service
        existing_service.stop(timeout=timeout, force=force)

        # delete the old configuration file
        service_directory_path = existing_service.status.runtime_path
        shutil.rmtree(service_directory_path)

    # the step will receive a config from the user that mentions the number
    # of workers etc.the step implementation will create a new config using
    # all values from the user and add values like pipeline name, model_uri
    def _create_new_service(
        self, timeout: int, config: MLFlowDeploymentConfig
    ) -> MLFlowDeploymentService:
        """Creates a new MLFlowDeploymentService."""

        # set the root runtime path with the stack component's UUID
        config.root_runtime_path = os.path.join(
            get_global_config_directory(),
            LOCAL_STORES_DIRECTORY_NAME,
            str(self.uuid),
        )
        # create a new service for the new model
        service = MLFlowDeploymentService(config)
        service.start(timeout=timeout)

        return service

    def find_model_server(
        self,
        running: bool = True,
        pipeline_name: Optional[str] = None,
        pipeline_run_id: Optional[str] = None,
        pipeline_step_name: Optional[str] = None,
        model_name: Optional[str] = None,
        model_uri: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> List[MLFlowDeploymentService]:
        """Method to find one or more model servers that match the
        given criteria.

        Args:
            running: If true, only running services will be returned.
            pipeline_name: Name of the pipeline that the deployed model was part
            of.
            pipeline_run_id: ID of the pipeline run which the deployed model was part of.
            pipeline_step_name: The name of the pipeline model deployment step that
                deployed the model.
            model_name: Name of the deployed model.
            model_uri: URI of the deployed model.
            model_type: Type/format of the deployed model. Not used in this MLflow
                case.

        Returns:
            One or more Service objects representing model servers that match
            the input search criteria.
        """

        services = []
        config = MLFlowDeploymentConfig(
            model_name=model_name,
            model_uri=model_uri,
            pipeline_name=pipeline_name,
            pipeline_run_id=pipeline_run_id,
            pipeline_step_name=pipeline_step_name,
        )

        # path where the services for this deployer are stored
        services_path = os.path.join(
            get_global_config_directory(),
            LOCAL_STORES_DIRECTORY_NAME,
            str(self.uuid),
        )

        # find all services that match the input criteria
        for root, dirs, files in os.walk(services_path):
            for file in files:
                if file == SERVICE_DAEMON_CONFIG_FILE_NAME:
                    service_config_path = os.path.join(root, file)
                    logger.info(
                        "Loading service daemon configuration from %s",
                        service_config_path,
                    )
                    existing_service_config = None
                    with open(service_config_path, "r") as f:
                        existing_service_config = f.read()
                    existing_service = ServiceRegistry().load_service_from_json(
                        existing_service_config
                    )
                    if not isinstance(
                        existing_service, MLFlowDeploymentService
                    ):
                        raise TypeError(
                            f"Expected service type MLFlowDeploymentService but got "
                            f"{type(existing_service)} instead"
                        )
                    if self._matches_search_criteria(existing_service, config):
                        if running:
                            if existing_service.is_running:
                                services.append(existing_service)
                        else:
                            services.append(existing_service)

        return services

    def _matches_search_criteria(
        self,
        existing_service: MLFlowDeploymentService,
        config: MLFlowDeploymentConfig,
    ) -> bool:
        """Returns true if a service matches the input criteria. If any of the values in
            the input criteria are None, they are ignored. This allows listing services
            just by common pipeline names or step names, etc.

        Args:
            existing_service: The materialized Service instance derived from the config
            of the older (existing) service
            config: The MLFlowDeploymentConfig object passed to the deploy_model function holding
            parameters of the new service to be created."""

        existing_service_config = existing_service.config

        # check if the existing service matches the input criteria
        if (
            (
                not existing_service_config.pipeline_name
                or existing_service_config.pipeline_name == config.pipeline_name
            )
            and (
                not existing_service_config.model_name
                or existing_service_config.model_name == config.model_name
            )
            and (
                not existing_service_config.pipeline_step_name
                or existing_service_config.pipeline_step_name
                == config.pipeline_step_name
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
        existing_services = self.find_model_server()

        # if uuid of service matches input uuid, stop the service
        for service in existing_services:
            if service.uuid == uuid:
                service.stop(timeout=timeout, force=force)
                break

    def start_model_server(
        self, uuid: UUID, timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT
    ) -> None:
        """Method to start a model server.

        Args:
            uuid: UUID of the model server to start.
        """
        # get list of all services
        existing_services = self.find_model_server()

        # if uuid of service matches input uuid, start the service
        for service in existing_services:
            if service.uuid == uuid:
                service.start(timeout=timeout)
                break

    def delete_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Method to delete all configuration of a model server.

        Args:
            uuid: UUID of the model server to delete.
        """
        # get list of all services
        existing_services = self.find_model_server()

        # if uuid of service matches input uuid, clean up the service
        for service in existing_services:
            if service.uuid == uuid:
                self._clean_up_existing_service(
                    existing_service=service, timeout=timeout, force=force
                )
                break
