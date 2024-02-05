#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Implementation of the Huggingface Model Deployer."""

from typing import ClassVar, Dict, List, Optional, Type, cast
from uuid import UUID

from huggingface_hub import InferenceEndpoint, list_inference_endpoints

from zenml.artifacts.utils import log_artifact_metadata, save_artifact
from zenml.client import Client
from zenml.integrations.huggingface import HUGGINGFACE_SERVICE_ARTIFACT
from zenml.integrations.huggingface.flavors.huggingface_model_deployer_flavor import (
    HuggingFaceModelDeployerConfig,
    HuggingFaceModelDeployerFlavor,
    HuggingFaceModelDeployerSettings,
)
from zenml.integrations.huggingface.services.huggingface_deployment import (
    HuggingFaceDeploymentService,
    HuggingFaceServiceConfig,
)
from zenml.logger import get_logger
from zenml.model_deployers import BaseModelDeployer
from zenml.model_deployers.base_model_deployer import (
    DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    BaseModelDeployerFlavor,
)
from zenml.services import BaseService, ServiceConfig, ServiceRegistry

logger = get_logger(__name__)

ZENM_ENDPOINT_PREFIX: str = "zenml-"
UUID_SLICE_LENGTH: int = 8


class HuggingFaceModelDeployer(BaseModelDeployer):
    """Huggingface endpoint model deployer."""

    NAME: ClassVar[str] = "HuggingFace"
    FLAVOR: ClassVar[
        Type[BaseModelDeployerFlavor]
    ] = HuggingFaceModelDeployerFlavor

    @property
    def config(self) -> HuggingFaceModelDeployerConfig:
        """Config class for the Huggingface Model deployer settings class.

        Returns:
            The configuration.
        """
        return cast(HuggingFaceModelDeployerConfig, self._config)

    @property
    def settings_class(self) -> Type[HuggingFaceModelDeployerSettings]:
        """Settings class for the Huggingface Model deployer settings class.

        Returns:
            The settings class.
        """
        return HuggingFaceModelDeployerSettings

    @property
    def deployed_endpoints(self) -> List[InferenceEndpoint]:
        """Get list of deployed endpoint from Huggingface.

        Returns:
            List of deployed endpoints.
        """
        return list_inference_endpoints(
            token=self.config.token,
            namespace=self.config.namespace,
        )

    def modify_endpoint_name(
        self, endpoint_name: str, artifact_version: str
    ) -> str:
        """Modify endpoint name by adding suffix and prefix.

        It adds a prefix "zenml-" if not present and a suffix
        of first 8 characters of uuid.

        Args:
            endpoint_name : Name of the endpoint
            artifact_version: Name of the artifact version

        Returns:
            Modified endpoint name with added prefix and suffix
        """
        # Add zenml prefix if it does not start with ZENM_ENDPOINT_PREFIX
        if not endpoint_name.startswith(ZENM_ENDPOINT_PREFIX):
            endpoint_name = ZENM_ENDPOINT_PREFIX + endpoint_name

        endpoint_name += artifact_version
        return endpoint_name

    def _create_new_service(
        self, timeout: int, config: HuggingFaceServiceConfig
    ) -> HuggingFaceDeploymentService:
        """Creates a new HuggingFaceDeploymentService.

        Args:
            timeout: the timeout in seconds to wait for the Huggingface inference endpoint
                to be provisioned and successfully started or updated.
            config: the configuration of the model to be deployed with Huggingface model deployer.

        Returns:
            The HuggingFaceServiceConfig object that can be used to interact
            with the Huggingface inference endpoint.
        """
        # create a new service for the new model
        service = HuggingFaceDeploymentService(config)

        # Use first 8 characters of UUID as artifact version
        # Add same 8 characters as suffix to endpoint name
        service_metadata = service.dict()
        service_metadata["uuid"] = str(service_metadata["uuid"])
        artifact_version = service_metadata["uuid"][:UUID_SLICE_LENGTH]

        service.config.endpoint_name = self.modify_endpoint_name(
            service.config.endpoint_name, artifact_version
        )

        logger.info(
            f"Creating an artifact {HUGGINGFACE_SERVICE_ARTIFACT} with service instance attached as metadata."
            " If there's an active pipeline and/or model this artifact will be associated with it."
        )

        save_artifact(
            service,
            HUGGINGFACE_SERVICE_ARTIFACT,
            version=artifact_version,
            is_deployment_artifact=True,
        )

        log_artifact_metadata(
            artifact_name=HUGGINGFACE_SERVICE_ARTIFACT,
            artifact_version=artifact_version,
            metadata={HUGGINGFACE_SERVICE_ARTIFACT: service_metadata},
        )

        service.start(timeout=timeout)
        return service

    def _clean_up_existing_service(
        self,
        timeout: int,
        force: bool,
        existing_service: HuggingFaceDeploymentService,
    ) -> None:
        """Stop existing services.

        Args:
            timeout: the timeout in seconds to wait for the Huggingface
                deployment to be stopped.
            force: if True, force the service to stop
            existing_service: Existing Huggingface deployment service
        """
        # stop the older service
        existing_service.stop(timeout=timeout, force=force)

    def deploy_model(
        self,
        config: ServiceConfig,
        replace: bool = True,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Create a new Huggingface deployment service or update an existing one.

        This should serve the supplied model and deployment configuration.

        Args:
            config: the configuration of the model to be deployed with Huggingface.
                Core
            replace: set this flag to True to find and update an equivalent
                Huggingface deployment server with the new model instead of
                starting a new deployment server.
            timeout: the timeout in seconds to wait for the Huggingface endpoint
                to be provisioned and successfully started or updated. If set
                to 0, the method will return immediately after the Huggingface
                server is provisioned, without waiting for it to fully start.

        Returns:
            The ZenML Huggingface deployment service object that can be used to
            interact with the remote Huggingface inference endpoint server.
        """
        config = cast(HuggingFaceServiceConfig, config)
        service = None

        # if replace is True, remove all existing services
        if replace:
            existing_services = self.find_model_server(
                pipeline_name=config.pipeline_name,
                pipeline_step_name=config.pipeline_step_name,
            )

            for existing_service in existing_services:
                if service is None:
                    # keep the most recently created service
                    service = cast(
                        HuggingFaceDeploymentService, existing_service
                    )
                try:
                    # delete the older services and don't wait for them to
                    # be deprovisioned
                    self._clean_up_existing_service(
                        existing_service=cast(
                            HuggingFaceDeploymentService, existing_service
                        ),
                        timeout=timeout,
                        force=True,
                    )
                except RuntimeError:
                    # ignore errors encountered while stopping old services
                    pass

        if service:
            # update an equivalent service in place
            logger.info(
                f"Updating an existing Huggingface deployment service: {service}"
            )

            service_metadata = service.dict()
            artifact_version = str(service_metadata["uuid"])[
                :UUID_SLICE_LENGTH
            ]
            config.endpoint_name = self.modify_endpoint_name(
                config.endpoint_name, artifact_version
            )

            service.stop(timeout=timeout, force=True)
            service.update(config)
            service.start(timeout=timeout)
        else:
            # create a new HuggingFaceDeploymentService instance
            service = self._create_new_service(timeout, config)
            logger.info(
                f"Creating a new huggingface inference endpoint service: {service}"
            )

        return cast(BaseService, service)

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
        """Find one or more Huggingface model services that match the given criteria.

        Args:
            running: if true, only running services will be returned.
            service_uuid: the UUID of the Huggingface service that was
                originally used to create the Huggingface deployment resource.
            pipeline_name: name of the pipeline that the deployed model was part
                of.
            run_name: Name of the pipeline run which the deployed model was
                part of.
            pipeline_step_name: the name of the pipeline model deployment step
                that deployed the model.
            model_name: the name of the deployed model.
            model_uri: URI of the deployed model.
            model_type: the Huggingface server implementation used to serve
                the model

        Raises:
            TypeError: _description_

        Returns:
            One or more Huggingface service objects representing Huggingface
            model servers that match the input search criteria.
        """
        # Use a Huggingface deployment service configuration to compute the labels
        config = HuggingFaceServiceConfig(
            pipeline_name=pipeline_name or "",
            run_name=run_name or "",
            pipeline_run_id=run_name or "",
            pipeline_step_name=pipeline_step_name or "",
            model_name=model_name or "",
            model_uri=model_uri or "",
            implementation=model_type or "",
        )

        services: List[BaseService] = []

        # Find all services that match input criteria
        for endpoint in self.deployed_endpoints:
            if endpoint.name.startswith("zenml-"):
                artifact_version = endpoint.name[-8:]
                # If service_uuid is supplied, fetch service for that uuid
                if (
                    service_uuid is not None
                    and str(service_uuid)[:8] != artifact_version
                ):
                    continue

                # Fetch the saved metadata artifact from zenml server to recreate service
                client = Client()
                try:
                    service_artifact = client.get_artifact_version(
                        HUGGINGFACE_SERVICE_ARTIFACT, artifact_version
                    )
                    hf_deployment_service_dict = service_artifact.run_metadata[
                        HUGGINGFACE_SERVICE_ARTIFACT
                    ].value

                    existing_service = (
                        ServiceRegistry().load_service_from_dict(
                            hf_deployment_service_dict
                        )
                    )

                    if not isinstance(
                        existing_service, HuggingFaceDeploymentService
                    ):
                        raise TypeError(
                            f"Expected service type HuggingFaceDeploymentService but got "
                            f"{type(existing_service)} instead"
                        )

                    existing_service.update_status()
                    if self._matches_search_criteria(existing_service, config):
                        if not running or existing_service.is_running:
                            services.append(
                                cast(BaseService, existing_service)
                            )

                # if endpoint is provisioned externally
                # we do not have saved artifact for it.
                except KeyError:
                    logger.error(
                        f"No key found for endpoint {endpoint.name} provisioned externally"
                    )

        return services

    def _matches_search_criteria(
        self,
        existing_service: HuggingFaceDeploymentService,
        config: HuggingFaceServiceConfig,
    ) -> bool:
        """Returns true if a service matches the input criteria.

        If any of the values in the input criteria are None, they are ignored.
        This allows listing services just by common pipeline names or step
        names, etc.

        Args:
            existing_service: The materialized Service instance derived from
                the config of the older (existing) service
            config: The HuggingFaceServiceConfig object passed to the
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
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
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
        self, uuid: UUID, timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT
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
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
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
            service = cast(HuggingFaceDeploymentService, existing_services[0])
            self._clean_up_existing_service(
                existing_service=service, timeout=timeout, force=force
            )

    def get_model_server_info(
        self,
        service_instance: "HuggingFaceDeploymentService",
    ) -> Dict[str, Optional[str]]:
        """Return implementation specific information that might be relevant to the user.

        Args:
            service_instance: Instance of a HuggingFaceDeploymentService

        Returns:
            Model server information.
        """
        return {
            "PREDICTION_URL": service_instance.prediction_url,
        }
