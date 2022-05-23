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
from typing import ClassVar, Dict, Generator, List, Optional
from uuid import UUID

from zenml.enums import StackComponentType
from zenml.services import BaseService, ServiceConfig
from zenml.stack import StackComponent

DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT = 300


class BaseModelDeployer(StackComponent, ABC):
    """Base class for all ZenML model deployers.

    The model deployer serves three major purposes:

    1. It contains all the stack related configuration attributes required to
    interact with the remote model serving tool, service or platform (e.g.
    hostnames, URLs, references to credentials, other client related
    configuration parameters).

    2. It implements the continuous deployment logic necessary to deploy models
    in a way that updates an existing model server that is already serving a
    previous version of the same model instead of creating a new model server
    for every new model version (see the `deploy_model` abstract method).
    This functionality can be consumed directly from ZenML pipeline steps, but
    it can also be used outside of the pipeline to deploy ad-hoc models. It is
    also usually coupled with a standard model deployer step, implemented by
    each integration, that hides the details of the deployment process away from
    the user.

    3. It acts as a ZenML BaseService registry, where every BaseService instance
    is used as an internal representation of a remote model server (see the
    `find_model_server` abstract method). To achieve this, it must be able to
    re-create the configuration of a BaseService from information that is
    persisted externally, alongside or even part of the remote model server
    configuration itself. For example, for model servers that are implemented as
    Kubernetes resources, the BaseService instances can be serialized and saved
    as Kubernetes resourece annotations. This allows the model deployer to keep
    track of all externally running model servers and to re-create their
    corresponding BaseService instance representations at any given time.
    The model deployer also defines methods that implement basic life-cycle
    management on remote model servers outside the coverage of a pipeline
    (see `stop_model_server`, `start_model_server` and `delete_model_server`).
    """

    # Class configuration
    TYPE: ClassVar[StackComponentType] = StackComponentType.MODEL_DEPLOYER
    FLAVOR: ClassVar[str]

    @abstractmethod
    def deploy_model(
        self,
        config: ServiceConfig,
        replace: bool = False,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
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

    @staticmethod
    @abstractmethod
    def get_model_server_info(
        service: BaseService,
    ) -> Dict[str, Optional[str]]:
        """Give implementation specific way to extract relevant model server
        properties for the user

        Args:
            service: Integration-specific service instance
        """

    @abstractmethod
    def find_model_server(
        self,
        running: bool = False,
        service_uuid: Optional[UUID] = None,
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
            service_uuid: The UUID of the service that was originally used
                to deploy the model.
            pipeline_name: name of the pipeline that the deployed model was part
                of.
            pipeline_run_id: ID of the pipeline run which the deployed model was
                part of.
            pipeline_step_name: the name of the pipeline model deployment step
                that deployed the model.
            model_name: the name of the deployed model.
            model_uri: URI of the deployed model.
            model_type: the implementation specific type/format of the deployed
                model.

        Returns:
            One or more Service objects representing model servers that match
            the input search criteria.
        """

    @abstractmethod
    def stop_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Abstract method to stop a model server.

        This operation should be reversible. A stopped model server should still
        show up in the list of model servers returned by `find_model_server` and
        it should be possible to start it again by calling `start_model_server`.

        Args:
            uuid: UUID of the model server to stop.
            timeout: timeout in seconds to wait for the service to stop. If
                set to 0, the method will return immediately after
                deprovisioning the service, without waiting for it to stop.
            force: if True, force the service to stop.
        """

    @abstractmethod
    def start_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> None:
        """Abstract method to start a model server.

        Args:
            uuid: UUID of the model server to start.
            timeout: timeout in seconds to wait for the service to start. If
                set to 0, the method will return immediately after
                provisioning the service, without waiting for it to become
                active.
        """

    @abstractmethod
    def delete_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Abstract method to delete a model server.

        This operation is irreversable. A deleted model server must no longer
        show up in the list of model servers returned by `find_model_server`.

        Args:
            uuid: UUID of the model server to stop.
            timeout: timeout in seconds to wait for the service to stop. If
                set to 0, the method will return immediately after
                deprovisioning the service, without waiting for it to stop.
            force: if True, force the service to stop.
        """

    def get_model_server_logs(
        self,
        uuid: UUID,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get the logs of a model server.

        Args:
            uuid: UUID of the model server to get the logs of.
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.
        """
        services = self.find_model_server(service_uuid=uuid)
        if len(services) == 0:
            raise RuntimeError(f"No model server found with UUID {uuid}")
        return services[0].get_logs(follow=follow, tail=tail)
