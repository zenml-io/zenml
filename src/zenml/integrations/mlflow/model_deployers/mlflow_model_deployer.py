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
import json
import os
import shutil
from typing import Optional

from typing import List, Optional

from zenml import logger
from zenml.constants import LOCAL_STORES_DIRECTORY_NAME

from zenml.enums import ModelDeployerFlavor, StackComponentType, ModelDeployerFlavor
from zenml.integrations.mlflow.services.mlflow_deployment import (
    MLFlowDeploymentConfig,
    MLFlowDeploymentService,
)
from zenml.io.utils import get_global_config_directory
from zenml.model_deployers.base_model_deployer import BaseModelDeployer
from zenml.services import (
    BaseService, 
    ServiceRegistry
)
from zenml.services.local.local_service import SERVICE_DAEMON_CONFIG_FILE_NAME
from zenml.stack.stack_component_class_registry import register_stack_component_class


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
    ) -> MLFlowDeploymentService:
        """

        We assume that the deployment decision is made at the step level and 
        here we have to delete any older services that are running and start 
        a new one.

        This method interacts with external serving platforms that manage services. 
        In the case of MLflow, we need to look into the local filesystem at a location
        where the configuration for the service is stored. Retrieving that, we can
        check if there's any service that was created for the existing model and 
        can return that or create one if there isn't any. 
        
        Concrete model deployer subclasses must implement the following
        functionality in this method:
        - Detect if there is an existing model server instance running serving
        one or more previous versions of the same model
        - Deploy the model to the serving platform or update the existing model
        server instance to include the new model version
        - Return a Service object that is a representation of the external model
        server instance. The Service must implement basic operational state
        tracking and lifecycle management operations for the model server (e.g.
        start, stop, etc.)

        Args:
            pipeline_name: Name of the pipeline that the model to be deployed
                is part of.
            run_id: ID of the pipeline run which the model to be deployed
                is part of.
            step_name: The name of the pipeline model deployment step that
                deploys the model.
            model_name: Name of the model to be deployed.
            model_uri: URI of the model to be deployed.
            model_type: Type/format of the model to be deployed.
            config: MLflow deployer config parameters passed from the step for 
            the model deployer.

        Returns:
            The deployment Service object.
        """

        services_path = os.path.join(
            get_global_config_directory(),
            LOCAL_STORES_DIRECTORY_NAME,
            str(self.uuid),
        )
        
        for root, dirs, files in os.walk(services_path):
            for file in files:
                if(file == SERVICE_DAEMON_CONFIG_FILE_NAME):
                    service_config_path = os.path.join(root, file)                    
                    logger.info(
                        "Loading service daemon configuration from %s", service_config_path
                    )
                    old_config = None
                    with open(service_config_path, "r") as f:
                        old_config = f.read()
                    old_service = ServiceRegistry().load_service_from_json(old_config)
                    if not isinstance(old_service, MLFlowDeploymentService):
                        raise TypeError(
                            f"Expected service type MLFlowDeploymentService but got "
                            f"{type(old_service)} instead"
                        )
                    if(self._old_service_exists(old_service, config)):
                        if config.model_uri and config.deploy_decision:
                            # there is a MLflow model associated with this run, so we 
                            # will delete the old service and create a new one
                            self._clean_up_old_service(old_service, config)
                        else:
                            # an MLflow model was not found in the current run, so we simply reuse
                            # the service created during the previous step run
                            return old_service
        
        # if there is no old service and no mlflow model 
        # associated with this run, raise a RuntimeError
        if not config.model_uri:
            raise RuntimeError(
                f"An MLflow model with name `{config.model_name}` was not "
                f"trained in the current pipeline run and no previous "
                f"service was found."
            )

        if config.deploy_decision:
            return self._create_new_service(config)
        else:
            # investigate what to do in this case. For now, returning 
            # a service with inactive state and status.
            return MLFlowDeploymentService()

    
    def _clean_up_old_service(
        old_service: MLFlowDeploymentService,
    ) -> None:
        # stop the older service
        old_service.stop(timeout=old_service.config.timeout)

        # delete the old configuration file
        service_directory_path = old_service.status.runtime_path
        shutil.rmtree(service_directory_path)


    def _old_service_exists(
        self,
        old_service: MLFlowDeploymentService, 
        config: MLFlowDeploymentConfig
    ) -> bool:
        """Returns true if an old service with the same pipeline name,
        step name and model name exists.
        
        Args:
            old_service: The materialized Service instance derived from the config
            of the older (existing) service
            config: The MLFlowDeploymentConfig object passed to the deploy_model function holding 
            parameters of the new service to be created."""
        
        old_config = old_service.config

        if old_config.pipeline_name == config.pipeline_name and \
            old_config.model_name == config.model_name and \
            old_config.step_name == config.step_name:
            return True

        return False
    
    # the step will receive a config from the user that mentions the number of workers etc.
    # the step implementation will create a new config using all values from the user and 
    # add values like pipeline name, model_uri 
    def _create_new_service(
        self, 
        config: MLFlowDeploymentConfig
    ) -> MLFlowDeploymentService:
        """Creates a new MLflowDeploymentService."""

        if not config.model_uri:
            # an MLflow model was not found in the current run, so we simply reuse
            # the service created during the previous step run
            raise RuntimeError(
                f"An MLflow model with name `{config.model_name}` was not "
                f"trained in the current pipeline run and no previous "
                f"service was found."
            )

        # set the uuid in the config
        config.caller_uuid = self.uuid
        # create a new service for the new model
        service = MLFlowDeploymentService(config)
        service.start(timeout=config.timeout)

        return service

        
    def find_model_server(
        self,
        pipeline_name: Optional[str] = None,
        run_id: Optional[str] = None,
        step_name: Optional[str] = None,
        model_name: Optional[str] = None,
        model_uri: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> List[BaseService]:
        """Method to find one or more model servers that match the
        given criteria.

        Args:
            pipeline_name: Name of the pipeline that the deployed model was part
            of.
            run_id: ID of the pipeline run which the deployed model was part of.
            step_name: The name of the pipeline model deployment step that
                deployed the model.
            model_name: Name of the deployed model.
            model_uri: URI of the deployed model.
            model_type: Type/format of the deployed model.

        Returns:
            One or more Service objects representing model servers that match
            the input search criteria.
        """



    def stop_model_server(self) -> None:
        """Abstract method to stop a model server.

        Args:
            ...: The arguments to be passed to the underlying model deployer
                implementation.
        """

    # @abstractmethod
    # def start_model_server(self, ...) -> None:
    #     """Abstract method to start ????? a model server.

    #     Args:
    #         ...: The arguments to be passed to the underlying model deployer
    #             implementation.
    #     """
