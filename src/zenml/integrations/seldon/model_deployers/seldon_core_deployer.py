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
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Type, cast

from zenml.enums import ModelDeployerFlavor, StackComponentType
from zenml.environment import Environment
from zenml.model_deployers.base_model_deployer import BaseModelDeployer
from zenml.services import BaseService, ServiceConfig
from zenml.services import load_last_service_from_step
from zenml.stack import StackComponent
from zenml.steps import step_environment, STEP_ENVIRONMENT_NAME
from zenml.steps.step_context import StepContext


class SeldonCoreDeployer(BaseModelDeployer):
    """Seldon Core implementation of the BaseModelDeployer"""

    @property
    def type(self) -> StackComponentType:
        """The component type."""
        return StackComponentType.MODEL_DEPLOYER

    @property
    @abstractmethod
    def flavor(self) -> ModelDeployerFlavor:
        """The model deployer flavor."""

    @abstractmethod
    def deploy_model(
        self,
        pipeline_name: str,
        run_id: str,
        step_name: str,
        model_name: str,
        model_uri: str,
        model_type: str,
        config: ServiceConfig,
        context: StepContext
    ) -> BaseService:
        """

        We assume that the deployment decision is made at the step level and 
        here we have to delete any older services that are running and start 
        a new one.
        
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
            config: Custom Service configuration parameters for the model
                deployer.
            context: The step context.

        Returns:
            The deployment Service object.
        """

        # check if there's an older service running
        step_env = cast(step_environment, Environment()[STEP_ENVIRONMENT_NAME])
        last_service = cast(
            SeldonCoreDeploymentService,
            load_last_service_from_step(
                pipeline_name=step_env.pipeline_name,
                step_name=step_env.step_name,
                step_context=context,
            ),
        )
        if last_service and not isinstance(
            last_service, SeldonCoreDeploymentService
        ):
            raise ValueError(
                f"Last service deployed by step {step_env.step_name} and "
                f"pipeline {step_env.pipeline_name} has invalid type. Expected "
                f"SeldonCoreDeploymentService, found {type(last_service)}."
            )
        
        # stop the service created during the last step run (will be replaced
        # by a new one to serve the new model)
        if last_service:
            last_service.stop(timeout=10)


    @abstractmethod
    def find_model_server(
        self,
        pipeline_name: Optional[str] = None,
        run_id: Optional[str] = None,
        step_name: Optional[str] = None,
        model_name: Optional[str] = None,
        model_uri: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> List[BaseService]:
        """Abstract method to find one or more a model servers that match the
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

    @abstractmethod
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
