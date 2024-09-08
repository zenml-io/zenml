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
"""Base class for all ZenML model deployers."""

import contextlib
from abc import ABC, abstractmethod
from typing import (
    Any,
    ClassVar,
    Dict,
    Generator,
    List,
    Optional,
    Type,
    cast,
)
from uuid import UUID

from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.services import BaseService, ServiceConfig
from zenml.services.service import BaseDeploymentService
from zenml.services.service_type import ServiceType
from zenml.stack import StackComponent
from zenml.stack.flavor import Flavor
from zenml.stack.stack_component import StackComponentConfig

logger = get_logger(__name__)

DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT = 300


class BaseModelDeployerConfig(StackComponentConfig):
    """Base config for all model deployers."""


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
    it can also be used outside the pipeline to deploy ad hoc models. It is
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
    as Kubernetes resource annotations. This allows the model deployer to keep
    track of all externally running model servers and to re-create their
    corresponding BaseService instance representations at any given time.
    The model deployer also defines methods that implement basic life-cycle
    management on remote model servers outside the coverage of a pipeline
    (see `stop_model_server`, `start_model_server` and `delete_model_server`).
    """

    NAME: ClassVar[str]
    FLAVOR: ClassVar[Type["BaseModelDeployerFlavor"]]

    @property
    def config(self) -> BaseModelDeployerConfig:
        """Returns the `BaseModelDeployerConfig` config.

        Returns:
            The configuration.
        """
        return cast(BaseModelDeployerConfig, self._config)

    @classmethod
    def get_active_model_deployer(cls) -> "BaseModelDeployer":
        """Get the model deployer registered in the active stack.

        Returns:
            The model deployer registered in the active stack.

        Raises:
            TypeError: if a model deployer is not part of the
                active stack.
        """
        flavor: BaseModelDeployerFlavor = cls.FLAVOR()
        client = Client()
        model_deployer = client.active_stack.model_deployer
        if not model_deployer or not isinstance(model_deployer, cls):
            raise TypeError(
                f"The active stack needs to have a {cls.NAME} model "
                f"deployer component registered to be able deploy models "
                f"with {cls.NAME}. You can create a new stack with "
                f"a {cls.NAME} model deployer component or update your "
                f"active stack to add this component, e.g.:\n\n"
                f"  `zenml model-deployer register {flavor.name} "
                f"--flavor={flavor.name} ...`\n"
                f"  `zenml stack register <STACK-NAME> -d {flavor.name} ...`\n"
                f"  or:\n"
                f"  `zenml stack update -d {flavor.name}`\n\n"
            )

        return model_deployer

    def deploy_model(
        self,
        config: ServiceConfig,
        service_type: ServiceType,
        replace: bool = False,
        continuous_deployment_mode: bool = False,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Deploy a model.

        the deploy_model method is the main entry point for deploying models
        using the model deployer. It is used to deploy a model to a model server
        instance that is running on a remote serving platform or service. The
        method is responsible for detecting if there is an existing model server
        instance running serving one or more previous versions of the same model
        and deploying the model to the serving platform or updating the existing
        model server instance to include the new model version. The method
        returns a Service object that is a representation of the external model
        server instance. The Service object must implement basic operational
        state tracking and lifecycle management operations for the model server
        (e.g. start, stop, etc.).

        Args:
            config: Custom Service configuration parameters for the model
                deployer. Can include the pipeline name, the run id, the step
                name, the model name, the model uri, the model type etc.
            replace: If True, it will replace any existing model server instances
                that serve the same model. If False, it does not replace any
                existing model server instance.
            continuous_deployment_mode: If True, it will replace any existing
                model server instances that serve the same model, regardless of
                the configuration. If False, it will only replace existing model
                server instances that serve the same model if the configuration
                is exactly the same.
            timeout: The maximum time in seconds to wait for the model server
                to start serving the model.
            service_type: The type of the service to deploy. If not provided,
                the default service type of the model deployer will be used.

        Raises:
            RuntimeError: if the model deployment fails.

        Returns:
            The deployment Service object.
        """
        # Instantiate the client
        client = Client()
        if not continuous_deployment_mode:
            # Find existing model server
            services = self.find_model_server(
                config=config.model_dump(),
                service_type=service_type,
            )
            if len(services) > 0:
                logger.info(
                    f"Existing model server found for {config.name or config.model_name} with the exact same configuration. Returning the existing service named {services[0].config.service_name}."
                )
                return services[0]
        else:
            # Find existing model server
            services = self.find_model_server(
                pipeline_name=config.pipeline_name,
                pipeline_step_name=config.pipeline_step_name,
                model_name=config.model_name,
                service_type=service_type,
            )
            if len(services) > 0:
                logger.info(
                    f"Existing model server found for {config.pipeline_name} and {config.pipeline_step_name}, since continuous deployment mode is enabled, replacing the existing service named {services[0].config.service_name}."
                )
                service = services[0]
                self.delete_model_server(service.uuid)
        logger.info(
            f"Deploying model server for {config.model_name} with the following configuration: {config.model_dump()}"
        )
        service_response = client.create_service(
            config=config,
            service_type=service_type,
            model_version_id=get_model_version_id_if_exists(
                config.model_name, config.model_version
            ),
        )
        try:
            service = self.perform_deploy_model(
                id=service_response.id,
                config=config,
                timeout=timeout,
            )
        except Exception as e:
            client.delete_service(service_response.id)
            raise RuntimeError(
                f"Failed to deploy model server for {config.model_name}: {e}"
            ) from e
        # Update the service in store
        client.update_service(
            id=service.uuid,
            name=service.config.service_name,
            service_source=service.model_dump().get("type"),
            admin_state=service.admin_state,
            status=service.status.model_dump(),
            endpoint=service.endpoint.model_dump()
            if service.endpoint
            else None,
            # labels=service.config.get_service_labels()  # TODO: fix labels in services and config
            prediction_url=service.get_prediction_url(),
            health_check_url=service.get_healthcheck_url(),
        )
        return service

    @abstractmethod
    def perform_deploy_model(
        self,
        id: UUID,
        config: ServiceConfig,
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
            id: UUID of the service that was originally used to deploy the model.
            config: Custom Service configuration parameters for the model
                deployer. Can include the pipeline name, the run id, the step
                name, the model name, the model uri, the model type etc.
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
        """Give implementation specific way to extract relevant model server properties for the user.

        Args:
            service: Integration-specific service instance

        Returns:
            A dictionary containing the relevant model server properties.
        """

    def find_model_server(
        self,
        config: Optional[Dict[str, Any]] = None,
        running: Optional[bool] = None,
        service_uuid: Optional[UUID] = None,
        pipeline_name: Optional[str] = None,
        pipeline_step_name: Optional[str] = None,
        service_name: Optional[str] = None,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        service_type: Optional[ServiceType] = None,
        type: Optional[str] = None,
        flavor: Optional[str] = None,
        pipeline_run_id: Optional[str] = None,
    ) -> List[BaseService]:
        """Abstract method to find one or more a model servers that match the given criteria.

        Args:
            running: If true, only running services will be returned.
            service_uuid: The UUID of the service that was originally used
                to deploy the model.
            pipeline_step_name: The name of the pipeline step that was originally used
                to deploy the model.
            pipeline_name: The name of the pipeline that was originally used to deploy
                the model from the model registry.
            model_name: The name of the model that was originally used to deploy
                the model from the model registry.
            model_version: The version of the model that was originally used to
                deploy the model from the model registry.
            service_type: The type of the service to find.
            type: The type of the service to find.
            flavor: The flavor of the service to find.
            pipeline_run_id: The UUID of the pipeline run that was originally used
                to deploy the model.
            config: Custom Service configuration parameters for the model
                deployer. Can include the pipeline name, the run id, the step
                name, the model name, the model uri, the model type etc.
            service_name: The name of the service to find.

        Returns:
            One or more Service objects representing model servers that match
            the input search criteria.
        """
        client = Client()
        service_responses = client.list_services(
            sort_by="desc:created",
            id=service_uuid,
            running=running,
            service_name=service_name,
            pipeline_name=pipeline_name,
            pipeline_step_name=pipeline_step_name,
            model_version_id=get_model_version_id_if_exists(
                model_name, model_version
            ),
            pipeline_run_id=pipeline_run_id,
            config=config,
            type=type or service_type.type if service_type else None,
            flavor=flavor or service_type.flavor if service_type else None,
            hydrate=True,
        )
        services = []
        for service_response in service_responses.items:
            if not service_response.service_source:
                client.delete_service(service_response.id)
                continue
            service = BaseDeploymentService.from_model(service_response)
            service.update_status()
            if service.status.model_dump() != service_response.status:
                client.update_service(
                    id=service.uuid,
                    admin_state=service.admin_state,
                    status=service.status.model_dump(),
                    endpoint=service.endpoint.model_dump()
                    if service.endpoint
                    else None,
                )
            if running and not service.is_running:
                logger.warning(
                    f"Service {service.uuid} is in an unexpected state. "
                    f"Expected running={running}, but found running={service.is_running}."
                )
                continue
            services.append(service)
        return services

    @abstractmethod
    def perform_stop_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> BaseService:
        """Abstract method to stop a model server.

        This operation should be reversible. A stopped model server should still
        show up in the list of model servers returned by `find_model_server` and
        it should be possible to start it again by calling `start_model_server`.

        Args:
            service: The service to stop.
            timeout: timeout in seconds to wait for the service to stop. If
                set to 0, the method will return immediately after
                deprovisioning the service, without waiting for it to stop.
            force: if True, force the service to stop.

        Returns:
            The stopped service.
        """

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

        Raises:
            RuntimeError: if the model server is not found.
        """
        client = Client()
        try:
            service = self.find_model_server(service_uuid=uuid)[0]
            updated_service = self.perform_stop_model(service, timeout, force)
            client.update_service(
                id=updated_service.uuid,
                admin_state=updated_service.admin_state,
                status=updated_service.status.model_dump(),
                endpoint=updated_service.endpoint.model_dump()
                if updated_service.endpoint
                else None,
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to stop model server with UUID {uuid}: {e}"
            ) from e

    @abstractmethod
    def perform_start_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Abstract method to start a model server.

        Args:
            service: The service to start.
            timeout: timeout in seconds to wait for the service to start. If
                set to 0, the method will return immediately after
                provisioning the service, without waiting for it to become
                active.

        Returns:
            The started service.
        """

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

        Raises:
            RuntimeError: if the model server is not found.
        """
        client = Client()
        try:
            service = self.find_model_server(service_uuid=uuid)[0]
            updated_service = self.perform_start_model(service, timeout)
            client.update_service(
                id=updated_service.uuid,
                admin_state=updated_service.admin_state,
                status=updated_service.status.model_dump(),
                endpoint=updated_service.endpoint.model_dump()
                if updated_service.endpoint
                else None,
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to start model server with UUID {uuid}: {e}"
            ) from e

    @abstractmethod
    def perform_delete_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Abstract method to delete a model server.

        This operation is irreversible. A deleted model server must no longer
        show up in the list of model servers returned by `find_model_server`.

        Args:
            service: The service to delete.
            timeout: timeout in seconds to wait for the service to stop. If
                set to 0, the method will return immediately after
                deprovisioning the service, without waiting for it to stop.
            force: if True, force the service to stop.
        """

    def delete_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Abstract method to delete a model server.

        This operation is irreversible. A deleted model server must no longer
        show up in the list of model servers returned by `find_model_server`.

        Args:
            uuid: UUID of the model server to stop.
            timeout: timeout in seconds to wait for the service to stop. If
                set to 0, the method will return immediately after
                deprovisioning the service, without waiting for it to stop.
            force: if True, force the service to stop.

        Raises:
            RuntimeError: if the model server is not found.
        """
        client = Client()
        try:
            service = self.find_model_server(service_uuid=uuid)[0]
            self.perform_delete_model(service, timeout, force)
            client.delete_service(uuid)
        except Exception as e:
            raise RuntimeError(
                f"Failed to delete model server with UUID {uuid}: {e}"
            ) from e

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

        Returns:
            A generator that yields the logs of the model server.

        Raises:
            RuntimeError: if the model server is not found.
        """
        services = self.find_model_server(service_uuid=uuid)
        if len(services) == 0:
            raise RuntimeError(f"No model server found with UUID {uuid}")
        return services[0].get_logs(follow=follow, tail=tail)

    def load_service(
        self,
        service_id: UUID,
    ) -> BaseService:
        """Load a service from a URI.

        Args:
            service_id: The ID of the service to load.

        Returns:
            The loaded service.
        """
        client = Client()
        service = client.get_service(service_id)
        return BaseDeploymentService.from_model(service)


class BaseModelDeployerFlavor(Flavor):
    """Base class for model deployer flavors."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type.

        Returns:
            The flavor type.
        """
        return StackComponentType.MODEL_DEPLOYER

    @property
    def config_class(self) -> Type[BaseModelDeployerConfig]:
        """Returns `BaseModelDeployerConfig` config class.

        Returns:
                The config class.
        """
        return BaseModelDeployerConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type[BaseModelDeployer]:
        """The class that implements the model deployer."""


def get_model_version_id_if_exists(
    model_name: Optional[str],
    model_version: Optional[str],
) -> Optional[UUID]:
    """Get the model version id if it exists.

    Args:
        model_name: The name of the model.
        model_version: The version of the model.

    Returns:
        The model version id if it exists.
    """
    client = Client()
    if model_name:
        with contextlib.suppress(KeyError):
            return client.get_model_version(
                model_name_or_id=model_name,
                model_version_name_or_number_or_id=model_version,
            ).id
    return None
