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
from typing import List, Optional
from uuid import UUID

from zenml.enums import StackComponentType
from zenml.services import BaseService, ServiceConfig
from zenml.stack import StackComponent


class BaseModelDeployer(StackComponent, ABC):
    """Base class for all ZenML model deployers."""

    @abstractmethod
    def deploy_model(
        self,
        config: ServiceConfig,
        replace: bool,
        timeout: int,
    ) -> BaseService:
        """Abstract method to deploy a model.

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
            config: Custom Service configuration parameters for the model
                deployer. Can include the pipeline name, the run id, the step
                name, the model name, the model uri, the model type etc.
            replace: If True, it will replace any existing model server instances
                that serve the same model. If False, it does not replace any
                existing model server instance.
            timeout: The maximum time in seconds to wait for the model server
                to start serving the model.

        Returns:
            The deployment Service object.
        """

    @abstractmethod
    def find_model_server(
        self,
        running: bool = True,
        pipeline_name: Optional[str] = None,
        pipeline_run_id: Optional[str] = None,
        pipeline_step_name: Optional[str] = None,
        model_name: Optional[str] = None,
        model_uri: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> List[BaseService]:
        """Abstract method to find one or more a model servers that match the
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
            model_type: Type/format of the deployed model.

        Returns:
            One or more Service objects representing model servers that match
            the input search criteria.
        """

    @abstractmethod
    def stop_model_server(self, uuid: UUID) -> None:
        """Abstract method to stop a model server.

        Args:
            uuid: The UUID of the model server to stop.
        """

    @abstractmethod
    def start_model_server(self, uuid: UUID) -> None:
        """Abstract method to start a model server.

        Args:
            uuid: The UUID of the model server to start.
        """

    @abstractmethod
    def delete_model_server(self, uuid: UUID) -> None:
        """Abstract method to delete a model server.

        Args:
            uuid: The UUID of the model server to delete.
        """
