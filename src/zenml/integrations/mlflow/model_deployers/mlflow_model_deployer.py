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
import uuid
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, cast
from uuid import UUID

from pydantic import root_validator

from zenml.constants import (
    DEFAULT_SERVICE_START_STOP_TIMEOUT,
    LOCAL_STORES_DIRECTORY_NAME,
)
from zenml.integrations.mlflow import MLFLOW_MODEL_DEPLOYER_FLAVOR
from zenml.integrations.mlflow.services.mlflow_deployment import (
    MLFlowDeploymentConfig,
    MLFlowDeploymentService,
)
from zenml.io.utils import (
    create_dir_recursive_if_not_exists,
    get_global_config_directory,
)
from zenml.logger import get_logger
from zenml.model_deployers.base_model_deployer import BaseModelDeployer
from zenml.repository import Repository
from zenml.services import ServiceRegistry
from zenml.services.local.local_service import SERVICE_DAEMON_CONFIG_FILE_NAME
from zenml.services.service import BaseService, ServiceConfig

logger = get_logger(__name__)


class MLFlowModelDeployer(BaseModelDeployer):
    """MLflow implementation of the BaseModelDeployer

    Attributes:
        service_path: the path where the local MLflow deployment service
        configuration, PID and log files are stored.
    """

    service_path: str = ""

    # Class Configuration
    FLAVOR: ClassVar[str] = MLFLOW_MODEL_DEPLOYER_FLAVOR

    @root_validator(skip_on_failure=True)
    def set_service_path(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Sets the service_path attribute value according to the component
        UUID."""
        if values.get("service_path"):
            return values

        # not likely to happen, due to Pydantic validation, but mypy complains
        assert "uuid" in values

        values["service_path"] = cls.get_service_path(values["uuid"])
        return values

    @staticmethod
    def get_service_path(uuid: uuid.UUID) -> str:
        """Get the path the path where the local MLflow deployment service
        configuration, PID and log files are stored.

        Args:
            uuid: The UUID of the MLflow model deployer.

        Returns:
            The service path.
        """
        service_path = os.path.join(
            get_global_config_directory(),
            LOCAL_STORES_DIRECTORY_NAME,
            str(uuid),
        )
        create_dir_recursive_if_not_exists(service_path)
        return service_path

    @property
    def local_path(self) -> str:
        """
        Returns the path to the root directory where all configurations for
        MLflow deployment daemon processes are stored.

        Returns:
            The path to the local service root directory.
        """
        return self.service_path

    @staticmethod
    def get_model_server_info(  # type: ignore[override]
        service_instance: "MLFlowDeploymentService",
    ) -> Dict[str, Optional[str]]:
        """Return implementation specific information that might be relevant
        to the user.

        Args:
            service_instance: Instance of a SeldonDeploymentService
        """

        return {
            "PREDICTION_URL": service_instance.endpoint.prediction_url,
            "MODEL_URI": service_instance.config.model_uri,
            "MODEL_NAME": service_instance.config.model_name,
            "SERVICE_PATH": service_instance.status.runtime_path,
            "DAEMON_PID": str(service_instance.status.pid),
        }

    @staticmethod
    def get_active_model_deployer() -> "MLFlowModelDeployer":
        """
        Returns the MLFlowModelDeployer component of the active stack.

        Args:
            None

        Returns:
            The MLFlowModelDeployer component of the active stack.
        """
        model_deployer = Repository(  # type: ignore[call-arg]
            skip_repository_check=True
        ).active_stack.model_deployer

        if not model_deployer or not isinstance(
            model_deployer, MLFlowModelDeployer
        ):
            raise TypeError(
                f"The active stack needs to have an MLflow model deployer "
                f"component registered to be able to deploy models with MLflow. "
                f"You can create a new stack with an MLflow model "
                f"deployer component or update your existing stack to add this "
                f"component, e.g.:\n\n"
                f"  'zenml model-deployer register mlflow --flavor={MLFLOW_MODEL_DEPLOYER_FLAVOR}'\n"
                f"  'zenml stack create stack-name -d mlflow ...'\n"
            )
        return model_deployer

    def deploy_model(
        self,
        config: ServiceConfig,
        replace: bool = False,
        timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Create a new MLflow deployment service or update an existing one to
        serve the supplied model and deployment configuration.

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

        Raises:
            RuntimeError: if `timeout` is set to a positive value that is
                exceeded while waiting for the MLflow deployment server
                to start, or if an operational failure is encountered before
                it reaches a ready state.
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
        service_directory_path = existing_service.status.runtime_path or ""
        shutil.rmtree(service_directory_path)

    # the step will receive a config from the user that mentions the number
    # of workers etc.the step implementation will create a new config using
    # all values from the user and add values like pipeline name, model_uri
    def _create_new_service(
        self, timeout: int, config: MLFlowDeploymentConfig
    ) -> MLFlowDeploymentService:
        """Creates a new MLFlowDeploymentService."""

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
        pipeline_run_id: Optional[str] = None,
        pipeline_step_name: Optional[str] = None,
        model_name: Optional[str] = None,
        model_uri: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> List[BaseService]:
        """Method to find one or more model servers that match the
        given criteria.

        Args:
            running: If true, only running services will be returned.
            service_uuid: The UUID of the service that was originally used
                to deploy the model.
            pipeline_name: Name of the pipeline that the deployed model was part
            of.
            pipeline_run_id: ID of the pipeline run which the deployed model
                was part of.
            pipeline_step_name: The name of the pipeline model deployment step
                that deployed the model.
            model_name: Name of the deployed model.
            model_uri: URI of the deployed model.
            model_type: Type/format of the deployed model. Not used in this
                MLflow case.

        Returns:
            One or more Service objects representing model servers that match
            the input search criteria.
        """

        services = []
        config = MLFlowDeploymentConfig(
            model_name=model_name or "",
            model_uri=model_uri or "",
            pipeline_name=pipeline_name or "",
            pipeline_run_id=pipeline_run_id or "",
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
                    existing_service.update_status()
                    if self._matches_search_criteria(existing_service, config):
                        if not running or existing_service.is_running:
                            services.append(cast(BaseService, existing_service))

        return services

    def _matches_search_criteria(
        self,
        existing_service: MLFlowDeploymentService,
        config: MLFlowDeploymentConfig,
    ) -> bool:
        """Returns true if a service matches the input criteria. If any of
        the values in the input criteria are None, they are ignored. This
        allows listing services just by common pipeline names or step names,
        etc.

        Args:
            existing_service: The materialized Service instance derived from
                the config of the older (existing) service
            config: The MLFlowDeploymentConfig object passed to the
                deploy_model function holding parameters of the new service
                to be created.
        """

        existing_service_config = existing_service.config

        # check if the existing service matches the input criteria
        if (
            (
                not config.pipeline_name
                or existing_service_config.pipeline_name == config.pipeline_name
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
                not config.pipeline_run_id
                or existing_service_config.pipeline_run_id
                == config.pipeline_run_id
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
        """
        # get list of all services
        existing_services = self.find_model_server(service_uuid=uuid)

        # if the service exists, clean it up
        if existing_services:
            service = cast(MLFlowDeploymentService, existing_services[0])
            self._clean_up_existing_service(
                existing_service=service, timeout=timeout, force=force
            )
