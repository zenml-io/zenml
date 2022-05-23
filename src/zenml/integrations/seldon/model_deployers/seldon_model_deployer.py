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

import re
from datetime import datetime
from typing import ClassVar, Dict, List, Optional, cast
from uuid import UUID

from zenml.integrations.seldon import SELDON_MODEL_DEPLOYER_FLAVOR
from zenml.integrations.seldon.seldon_client import SeldonClient
from zenml.integrations.seldon.services.seldon_deployment import (
    SeldonDeploymentConfig,
    SeldonDeploymentService,
)
from zenml.logger import get_logger
from zenml.model_deployers.base_model_deployer import BaseModelDeployer
from zenml.repository import Repository
from zenml.secrets_managers import BaseSecretsManager
from zenml.services.service import BaseService, ServiceConfig

logger = get_logger(__name__)

DEFAULT_SELDON_DEPLOYMENT_START_STOP_TIMEOUT = 300


class SeldonModelDeployer(BaseModelDeployer):
    """Seldon Core model deployer stack component implementation.

    Attributes:
        kubernetes_context: the Kubernetes context to use to contact the remote
            Seldon Core installation. If not specified, the current
            configuration is used. Depending on where the Seldon model deployer
            is being used, this can be either a locally active context or an
            in-cluster Kubernetes configuration (if running inside a pod).
        kubernetes_namespace: the Kubernetes namespace where the Seldon Core
            deployment servers are provisioned and managed by ZenML. If not
            specified, the namespace set in the current configuration is used.
            Depending on where the Seldon model deployer is being used, this can
            be either the current namespace configured in the locally active
            context or the namespace in the context of which the pod is running
            (if running inside a pod).
        base_url: the base URL of the Kubernetes ingress used to expose the
            Seldon Core deployment servers.
        secret: the name of a ZenML secret containing the credentials used by
            Seldon Core storage initializers to authenticate to the Artifact
            Store (i.e. the storage backend where models are stored - see
            https://docs.seldon.io/projects/seldon-core/en/latest/servers/overview.html#handling-credentials).
    """

    # Class Configuration
    FLAVOR: ClassVar[str] = SELDON_MODEL_DEPLOYER_FLAVOR

    kubernetes_context: Optional[str]
    kubernetes_namespace: Optional[str]
    base_url: str
    secret: Optional[str]

    # private attributes
    _client: Optional[SeldonClient] = None

    @staticmethod
    def get_model_server_info(  # type: ignore[override]
        service_instance: "SeldonDeploymentService",
    ) -> Dict[str, Optional[str]]:
        """ "Return implementation specific information that might be relevant
        to the user.

        Args:
            service_instance: Instance of a SeldonDeploymentService
        """

        return {
            "PREDICTION_URL": service_instance.prediction_url,
            "MODEL_URI": service_instance.config.model_uri,
            "MODEL_NAME": service_instance.config.model_name,
            "SELDON_DEPLOYMENT": service_instance.seldon_deployment_name,
        }

    @staticmethod
    def get_active_model_deployer() -> "SeldonModelDeployer":
        """Get the Seldon Core model deployer registered in the active stack.

        Returns:
            The Seldon Core model deployer registered in the active stack.
        Raises:
            TypeError: if the Seldon Core model deployer is not available.
        """
        model_deployer = Repository(  # type: ignore [call-arg]
            skip_repository_check=True
        ).active_stack.model_deployer
        if not model_deployer or not isinstance(
            model_deployer, SeldonModelDeployer
        ):
            raise TypeError(
                f"The active stack needs to have a Seldon Core model deployer "
                f"component registered to be able to deploy models with Seldon "
                f"Core. You can create a new stack with a Seldon Core model "
                f"deployer component or update your existing stack to add this "
                f"component, e.g.:\n\n"
                f"  'zenml model-deployer register seldon --flavor={SELDON_MODEL_DEPLOYER_FLAVOR} "
                f"--kubernetes_context=context-name --kubernetes_namespace="
                f"namespace-name --base_url=https://ingress.cluster.kubernetes'\n"
                f"  'zenml stack create stack-name -d seldon ...'\n"
            )
        return model_deployer

    @property
    def seldon_client(self) -> SeldonClient:
        """Get the Seldon Core client associated with this model deployer.

        Returns:
            The Seldon Core client.

        Raises:
            SeldonClientError: if the Kubernetes client configuration cannot be
                found.
        """
        if not self._client:
            self._client = SeldonClient(
                context=self.kubernetes_context,
                namespace=self.kubernetes_namespace,
            )
        return self._client

    @property
    def kubernetes_secret_name(self) -> Optional[str]:
        """Get the Kubernetes secret name associated with this model deployer.

        If a secret is configured for this model deployer, a corresponding
        Kubernetes secret is created in the remote cluster to be used
        by Seldon Core storage initializers to authenticate to the Artifact
        Store. This method returns the unique name that is used for this secret.

        Returns:
            The Seldon Core Kubernetes secret name, or None if no secret is
            configured.
        """
        if not self.secret:
            return None
        return (
            re.sub(r"[^0-9a-zA-Z-]+", "-", f"zenml-seldon-core-{self.secret}")
            .strip("-")
            .lower()
        )

    def _create_or_update_kubernetes_secret(self) -> Optional[str]:
        """Create or update a Kubernetes secret with the information stored in
        the ZenML secret configured for the model deployer.

        Returns:
            The name of the Kubernetes secret that was created or updated, or
            None if no secret was configured.

        Raises:
            SeldonClientError: if the secret cannot be created or updated.
        """
        # if a ZenML secret was configured in the model deployer,
        # create a Kubernetes secret as a means to pass this information
        # to the Seldon Core deployment
        if self.secret:

            secret_manager = Repository(  # type: ignore [call-arg]
                skip_repository_check=True
            ).active_stack.secrets_manager

            if not secret_manager or not isinstance(
                secret_manager, BaseSecretsManager
            ):
                raise RuntimeError(
                    f"The active stack doesn't have a secret manager component. "
                    f"The ZenML secret specified in the Seldon Core Model "
                    f"Deployer configuration cannot be fetched: {self.secret}."
                )

            try:
                zenml_secret = secret_manager.get_secret(self.secret)
            except KeyError:
                raise RuntimeError(
                    f"The ZenML secret '{self.secret}' specified in the "
                    f"Seldon Core Model Deployer configuration was not found "
                    f"in the active stack's secret manager."
                )

            # should never happen, just making mypy happy
            assert self.kubernetes_secret_name is not None
            self.seldon_client.create_or_update_secret(
                self.kubernetes_secret_name, zenml_secret
            )

        return self.kubernetes_secret_name

    def _delete_kubernetes_secret(self) -> None:
        """Delete the Kubernetes secret associated with this model deployer
        if no Seldon Core deployments are using it.

        Raises:
            SeldonClientError: if the secret cannot be deleted.
        """
        if self.kubernetes_secret_name:

            # fetch all the Seldon Core deployments that currently
            # configured to use this secret
            services = self.find_model_server()
            for service in services:
                config = cast(SeldonDeploymentConfig, service.config)
                if config.secret_name == self.kubernetes_secret_name:
                    return
            self.seldon_client.delete_secret(self.kubernetes_secret_name)

    def deploy_model(
        self,
        config: ServiceConfig,
        replace: bool = False,
        timeout: int = DEFAULT_SELDON_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Create a new Seldon Core deployment or update an existing one to
        serve the supplied model and deployment configuration.

        This method has two modes of operation, depending on the `replace`
        argument value:

          * if `replace` is False, calling this method will create a new Seldon
            Core deployment server to reflect the model and other configuration
            parameters specified in the supplied Seldon deployment `config`.

          * if `replace` is True, this method will first attempt to find an
            existing Seldon Core deployment that is *equivalent* to the supplied
            configuration parameters. Two or more Seldon Core deployments are
            considered equivalent if they have the same `pipeline_name`,
            `pipeline_step_name` and `model_name` configuration parameters. To
            put it differently, two Seldon Core deployments are equivalent if
            they serve versions of the same model deployed by the same pipeline
            step. If an equivalent Seldon Core deployment is found, it will be
            updated in place to reflect the new configuration parameters. This
            allows an existing Seldon Core deployment to retain its prediction
            URL while performing a rolling update to serve a new model version.

        Callers should set `replace` to True if they want a continuous model
        deployment workflow that doesn't spin up a new Seldon Core deployment
        server for each new model version. If multiple equivalent Seldon Core
        deployments are found, the most recently created deployment is selected
        to be updated and the others are deleted.

        Args:
            config: the configuration of the model to be deployed with Seldon.
                Core
            replace: set this flag to True to find and update an equivalent
                Seldon Core deployment server with the new model instead of
                starting a new deployment server.
            timeout: the timeout in seconds to wait for the Seldon Core server
                to be provisioned and successfully started or updated. If set
                to 0, the method will return immediately after the Seldon Core
                server is provisioned, without waiting for it to fully start.

        Returns:
            The ZenML Seldon Core deployment service object that can be used to
            interact with the remote Seldon Core server.

        Raises:
            SeldonClientError: if a Seldon Core client error is encountered
                while provisioning the Seldon Core deployment server.
            RuntimeError: if `timeout` is set to a positive value that is
                exceeded while waiting for the Seldon Core deployment server
                to start, or if an operational failure is encountered before
                it reaches a ready state.
        """
        config = cast(SeldonDeploymentConfig, config)
        service = None

        # if a custom Kubernetes secret is not explicitly specified in the
        # SeldonDeploymentConfig, try to create one from the ZenML secret
        # configured for the model deployer
        config.secret_name = (
            config.secret_name or self._create_or_update_kubernetes_secret()
        )

        # if replace is True, find equivalent Seldon Core deployments
        if replace is True:
            equivalent_services = self.find_model_server(
                running=False,
                pipeline_name=config.pipeline_name,
                pipeline_step_name=config.pipeline_step_name,
                model_name=config.model_name,
            )

            for equivalent_service in equivalent_services:
                if service is None:
                    # keep the most recently created service
                    service = equivalent_service
                else:
                    try:
                        # delete the older services and don't wait for them to
                        # be deprovisioned
                        service.stop()
                    except RuntimeError:
                        # ignore errors encountered while stopping old services
                        pass

        if service:
            # update an equivalent service in place
            service.update(config)
            logger.info(
                f"Updating an existing Seldon deployment service: {service}"
            )
        else:
            # create a new service
            service = SeldonDeploymentService(config=config)
            logger.info(f"Creating a new Seldon deployment service: {service}")

        # start the service which in turn provisions the Seldon Core
        # deployment server and waits for it to reach a ready state
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
        """Find one or more Seldon Core model services that match th given
        criteria.

        The Seldon Core deployment services that meet the search criteria are
        returned sorted in descending order of their creation time (i.e. more
        recent deployments first).

        Args:
            running: if true, only running services will be returned.
            service_uuid: the UUID of the Seldon Core service that was originally used
                to create the Seldon Core deployment resource.
            pipeline_name: name of the pipeline that the deployed model was part
                of.
            pipeline_run_id: ID of the pipeline run which the deployed model was
                part of.
            pipeline_step_name: the name of the pipeline model deployment step
                that deployed the model.
            model_name: the name of the deployed model.
            model_uri: URI of the deployed model.
            model_type: the Seldon Core server implementation used to serve
                the model

        Returns:
            One or more Seldon Core service objects representing Seldon Core
            model servers that match the input search criteria.
        """
        # Use a Seldon deployment service configuration to compute the labels
        config = SeldonDeploymentConfig(
            pipeline_name=pipeline_name or "",
            pipeline_run_id=pipeline_run_id or "",
            pipeline_step_name=pipeline_step_name or "",
            model_name=model_name or "",
            model_uri=model_uri or "",
            implementation=model_type or "",
        )
        labels = config.get_seldon_deployment_labels()
        if service_uuid:
            # the service UUID is not a label covered by the Seldon
            # deployment service configuration, so we need to add it
            # separately
            labels["zenml.service_uuid"] = str(service_uuid)

        deployments = self.seldon_client.find_deployments(labels=labels)
        # sort the deployments in descending order of their creation time
        deployments.sort(
            key=lambda deployment: datetime.strptime(
                deployment.metadata.creationTimestamp,
                "%Y-%m-%dT%H:%M:%SZ",
            )
            if deployment.metadata.creationTimestamp
            else datetime.min,
            reverse=True,
        )

        services: List[BaseService] = []
        for deployment in deployments:
            # recreate the Seldon deployment service object from the Seldon
            # deployment resource
            service = SeldonDeploymentService.create_from_deployment(
                deployment=deployment
            )
            if running and not service.is_running:
                # skip non-running services
                continue
            services.append(service)

        return services

    def stop_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_SELDON_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Stop a Seldon Core model server.

        Args:
            uuid: UUID of the model server to stop.
            timeout: timeout in seconds to wait for the service to stop.
            force: if True, force the service to stop.
        """
        raise NotImplementedError(
            "Stopping Seldon Core model servers is not implemented. Try "
            "deleting the Seldon Core model server instead."
        )

    def start_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_SELDON_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> None:
        """Start a Seldon Core model deployment server.

        Args:
            uuid: UUID of the model server to start.
            timeout: timeout in seconds to wait for the service to become
                active. . If set to 0, the method will return immediately after
                provisioning the service, without waiting for it to become
                active.
        """
        raise NotImplementedError(
            "Starting Seldon Core model servers is not implemented"
        )

    def delete_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_SELDON_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Delete a Seldon Core model deployment server.

        Args:
            uuid: UUID of the model server to delete.
            timeout: timeout in seconds to wait for the service to stop. If
                set to 0, the method will return immediately after
                deprovisioning the service, without waiting for it to stop.
            force: if True, force the service to stop.
        """
        services = self.find_model_server(service_uuid=uuid)
        if len(services) == 0:
            return
        services[0].stop(timeout=timeout, force=force)

        # if this is the last Seldon Core model server, delete the Kubernetes
        # secret used to store the authentication information for the Seldon
        # Core model server storage initializer
        self._delete_kubernetes_secret()
