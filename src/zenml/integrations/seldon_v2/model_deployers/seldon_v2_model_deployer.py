#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Implementation of the Seldon V2 Model Deployer."""

import json
import re
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Dict, List, Optional, Type, cast
from uuid import UUID

from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.integrations.seldon.secret_schemas.secret_schemas import (
    SeldonAzureSecretSchema,
    SeldonGSSecretSchema,
    SeldonS3SecretSchema,
)
from zenml.integrations.seldon_v2.flavors.seldon_v2_model_deployer_flavor import (
    SeldonV2ModelDeployerConfig,
    SeldonV2ModelDeployerFlavor,
)
from zenml.integrations.seldon_v2.seldon_v2_client import SeldonV2Client
from zenml.integrations.seldon_v2.services.seldon_deployment import (
    SeldonV2ModelConfig,
    SeldonV2ModelService,
)
from zenml.logger import get_logger
from zenml.model_deployers import BaseModelDeployer, BaseModelDeployerFlavor
from zenml.secret.base_secret import BaseSecretSchema
from zenml.services.service import BaseService, ServiceConfig
from zenml.stack import StackValidator
from zenml.utils.analytics_utils import AnalyticsEvent, event_handler

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

DEFAULT_SELDON_V2_MODEL_START_STOP_TIMEOUT = 300


class SeldonV2ModelDeployer(BaseModelDeployer):
    """Seldon Core V2 V2 model deployer stack component implementation."""

    NAME: ClassVar[str] = "Seldon Core V2"
    FLAVOR: ClassVar[
        Type[BaseModelDeployerFlavor]
    ] = SeldonV2ModelDeployerFlavor

    _client: Optional[SeldonV2Client] = None

    @property
    def config(self) -> SeldonV2ModelDeployerConfig:
        """Returns the `SeldonV2ModelDeployerConfig` config.

        Returns:
            The configuration.
        """
        return cast(SeldonV2ModelDeployerConfig, self._config)

    @property
    def validator(self) -> Optional[StackValidator]:
        """Ensures there is a container registry and image builder in the stack.

        Returns:
            A `StackValidator` instance.
        """
        return StackValidator(
            required_components={
                StackComponentType.IMAGE_BUILDER,
            }
        )

    @staticmethod
    def get_model_server_info(  # type: ignore[override]
        service_instance: "SeldonV2ModelService",
    ) -> Dict[str, Optional[str]]:
        """Return implementation specific information that might be relevant to the user.

        Args:
            service_instance: Instance of a SeldonV2ModelService

        Returns:
            Model server information.
        """
        return {
            "PREDICTION_URL": service_instance.prediction_url,
            "model_uri": service_instance.config.model_uri,
            "name": service_instance.config.name,
        }

    @property
    def seldon_v2_client(self) -> SeldonV2Client:
        """Get the Seldon Core V2 V2 client associated with this model deployer.

        Returns:
            The Seldon Core V2 V2 client.

        Raises:
            RuntimeError: If the Kubernetes namespace is not configured when
                using a service connector to deploy models with Seldon Core V2 V2.
        """
        from kubernetes import client as k8s_client

        # Refresh the client also if the connector has expired
        if self._client and not self.connector_has_expired():
            return self._client

        connector = self.get_connector()
        kube_client: Optional[k8s_client.ApiClient] = None
        if connector:
            if not self.config.kubernetes_namespace:
                raise RuntimeError(
                    "The Kubernetes namespace must be explicitly configured in "
                    "the stack component when using a service connector to "
                    "deploy models with Seldon Core V2."
                )
            kube_client = connector.connect()
            if not isinstance(kube_client, k8s_client.ApiClient):
                raise RuntimeError(
                    f"Expected a k8s_client.ApiClient while trying to use the "
                    f"linked connector, but got {type(kube_client)}."
                )

        self._client = SeldonV2Client(
            context=self.config.kubernetes_context,
            namespace=self.config.kubernetes_namespace,
            kube_client=kube_client,
        )

        return self._client

    @property
    def kubernetes_secret_name(self) -> str:
        """Get the Kubernetes secret name associated with this model deployer.

        If a pre-existing Kubernetes secret is configured for this model
        deployer, that name is returned to be used by all Seldon Core V2
        models associated with this model deployer.

        Otherwise, a Kubernetes secret name is generated based on the ID of
        the active artifact store. The reason for this is that the same model
        deployer may be used to deploy models in combination with different
        artifact stores at the same time, and each artifact store may require
        different credentials to be accessed.

        Returns:
            The name of a Kubernetes secret to be used with Seldon Core V2
            models.
        """
        if self.config.kubernetes_secret_name:
            return self.config.kubernetes_secret_name

        artifact_store = Client().active_stack.artifact_store

        return (
            re.sub(
                r"[^0-9a-zA-Z-]+",
                "-",
                f"zenml-seldon-core-{artifact_store.id}",
            )
            .strip("-")
            .lower()
        )

    def _create_or_update_kubernetes_secret(self) -> Optional[str]:
        """Create or update the Kubernetes secret used to access the artifact store.

        Uses the information stored in the ZenML secret configured for the model deployer.

        Returns:
            The name of the Kubernetes secret that was created or updated, or
            None if no secret was configured.

        Raises:
            RuntimeError: if the secret cannot be created or updated.
        """
        # if a Kubernetes secret was explicitly configured in the model
        # deployer, use that instead of creating a new one
        if self.config.kubernetes_secret_name:
            logger.warning(
                "Your Seldon Core V2 V2 model deployer is configured to use a "
                "pre-existing Kubernetes secret that holds credentials needed "
                "to access the artifact store. The authentication method is "
                "deprecated and will be removed in a future release. Please "
                "remove this attribute by running `zenml model-deployer "
                f"remove-attribute {self.name} --kubernetes_secret_name` and "
                "configure credentials for the artifact store stack component "
                "instead. The Seldon Core V2 V2 model deployer will use those "
                "credentials to authenticate to the artifact store "
                "automatically."
            )

            return self.config.kubernetes_secret_name

        # if a ZenML secret reference was configured in the model deployer,
        # create a Kubernetes secret from that
        if self.config.secret:
            logger.warning(
                "Your Seldon Core V2 V2 model deployer is configured to use a "
                "ZenML secret that holds credentials needed to access the "
                "artifact store. The recommended authentication method is to "
                "configure credentials for the artifact store stack component "
                "instead. The Seldon Core V2 model deployer will use those "
                "credentials to authenticate to the artifact store "
                "automatically."
            )

            try:
                zenml_secret = Client().get_secret_by_name_and_scope(
                    name=self.config.secret,
                )
            except KeyError as e:
                raise RuntimeError(
                    f"The ZenML secret '{self.config.secret}' specified in the "
                    f"Seldon Core V2 Model Deployer configuration was not found "
                    f"in the secrets store: {e}."
                )

            self.seldon_v2_client.create_or_update_secret(
                self.kubernetes_secret_name, zenml_secret.secret_values
            )

        else:
            # if no ZenML secret was configured, try to convert the credentials
            # configured for the artifact store, if any are included, into
            # the format expected by Seldon Core V2
            converted_secret = self._convert_artifact_store_secret()

            self.seldon_v2_client.create_or_update_secret(
                self.kubernetes_secret_name, converted_secret.content
            )

        return self.kubernetes_secret_name

    def _convert_artifact_store_secret(self) -> BaseSecretSchema:
        """Convert the credentials configured for the artifact store into a ZenML secret.

        Returns:
            The ZenML secret.

        Raises:
            RuntimeError: if the credentials cannot be converted.
        """
        artifact_store = Client().active_stack.artifact_store

        zenml_secret: BaseSecretSchema

        if artifact_store.flavor == "s3":
            from zenml.integrations.s3.artifact_stores import S3ArtifactStore

            assert isinstance(artifact_store, S3ArtifactStore)

            (
                aws_access_key_id,
                aws_secret_access_key,
                aws_session_token,
            ) = artifact_store.get_credentials()

            if aws_access_key_id and aws_secret_access_key:
                # Convert the credentials into the format expected by Seldon
                # Core
                zenml_secret = SeldonS3SecretSchema(
                    name="",
                    rclone_config_s3_access_key_id=aws_access_key_id,
                    rclone_config_s3_secret_access_key=aws_secret_access_key,
                    rclone_config_s3_session_token=aws_session_token,
                )
                if (
                    artifact_store.config.client_kwargs
                    and "endpoint_url" in artifact_store.config.client_kwargs
                ):
                    zenml_secret.rclone_config_s3_endpoint = (
                        artifact_store.config.client_kwargs["endpoint_url"]
                    )
                    # Assume minio is the provider if endpoint is set
                    zenml_secret.rclone_config_s3_provider = "Minio"

                return zenml_secret

            logger.warning(
                "No credentials are configured for the active S3 artifact "
                "store. The Seldon Core V2 V2 model deployer will assume an "
                "implicit form of authentication is available in the "
                "target Kubernetes cluster, but the served model may not "
                "be able to access the model artifacts."
            )

            # Assume implicit in-cluster IAM authentication
            return SeldonS3SecretSchema(
                name="", rclone_config_s3_env_auth=True
            )

        elif artifact_store.flavor == "gcp":
            from zenml.integrations.gcp.artifact_stores import GCPArtifactStore

            assert isinstance(artifact_store, GCPArtifactStore)

            gcp_credentials = artifact_store.get_credentials()

            if gcp_credentials:
                # Convert the credentials into the format expected by Seldon
                # Core
                if isinstance(gcp_credentials, dict):
                    if gcp_credentials.get("type") == "service_account":
                        return SeldonGSSecretSchema(
                            name="",
                            rclone_config_gs_service_account_credentials=json.dumps(
                                gcp_credentials
                            ),
                        )
                    elif gcp_credentials.get("type") == "authorized_user":
                        return SeldonGSSecretSchema(
                            name="",
                            rclone_config_gs_client_id=gcp_credentials.get(
                                "client_id"
                            ),
                            rclone_config_gs_client_secret=gcp_credentials.get(
                                "client_secret"
                            ),
                            rclone_config_gs_token=json.dumps(
                                dict(
                                    refresh_token=gcp_credentials.get(
                                        "refresh_token"
                                    )
                                )
                            ),
                        )
                else:
                    # Connector token-based authentication
                    return SeldonGSSecretSchema(
                        name="",
                        rclone_config_gs_token=json.dumps(
                            dict(
                                access_token=gcp_credentials.token,
                            )
                        ),
                    )

            logger.warning(
                "No credentials are configured for the active GCS artifact "
                "store. The Seldon Core V2 model deployer will assume an "
                "implicit form of authentication is available in the "
                "target Kubernetes cluster, but the served model may not "
                "be able to access the model artifacts."
            )
            return SeldonGSSecretSchema(
                name="", rclone_config_gs_anonymous=False
            )

        elif artifact_store.flavor == "azure":
            from zenml.integrations.azure.artifact_stores import (
                AzureArtifactStore,
            )

            assert isinstance(artifact_store, AzureArtifactStore)

            azure_credentials = artifact_store.get_credentials()

            if azure_credentials:
                # Convert the credentials into the format expected by Seldon
                # Core
                if azure_credentials.connection_string is not None:
                    try:
                        # We need to extract the account name and key from the
                        # connection string
                        tokens = azure_credentials.connection_string.split(";")
                        token_dict = dict(
                            [token.split("=", maxsplit=1) for token in tokens]
                        )
                        account_name = token_dict["AccountName"]
                        account_key = token_dict["AccountKey"]
                    except (KeyError, ValueError) as e:
                        raise RuntimeError(
                            "The Azure connection string configured for the "
                            "artifact store expected format."
                        ) from e

                    return SeldonAzureSecretSchema(
                        name="",
                        rclone_config_az_account=account_name,
                        rclone_config_az_key=account_key,
                    )

                if azure_credentials.sas_token is not None:
                    return SeldonAzureSecretSchema(
                        name="",
                        rclone_config_az_sas_url=azure_credentials.sas_token,
                    )

                if (
                    azure_credentials.account_name is not None
                    and azure_credentials.account_key is not None
                ):
                    return SeldonAzureSecretSchema(
                        name="",
                        rclone_config_az_account=azure_credentials.account_name,
                        rclone_config_az_key=azure_credentials.account_key,
                    )

                if (
                    azure_credentials.client_id is not None
                    and azure_credentials.client_secret is not None
                    and azure_credentials.tenant_id is not None
                    and azure_credentials.account_name is not None
                ):
                    return SeldonAzureSecretSchema(
                        name="",
                        rclone_config_az_client_id=azure_credentials.client_id,
                        rclone_config_az_client_secret=azure_credentials.client_secret,
                        rclone_config_az_tenant=azure_credentials.tenant_id,
                    )

            logger.warning(
                "No credentials are configured for the active Azure "
                "artifact store. The Seldon Core V2 model deployer will "
                "assume an implicit form of authentication is available "
                "in the target Kubernetes cluster, but the served model "
                "may not be able to access the model artifacts."
            )
            return SeldonAzureSecretSchema(
                name="", rclone_config_az_env_auth=True
            )

        raise RuntimeError(
            "The Seldon Core V2 model deployer doesn't know how to configure "
            f"credentials automatically for the `{artifact_store.flavor}` "
            "active artifact store flavor. "
            "Please use one of the supported artifact stores (S3, GCP or "
            "Azure) or specify a ZenML secret in the model deployer "
            "configuration that holds the credentials required to access "
            "the model artifacts."
        )

    def _delete_kubernetes_secret(self, secret_name: str) -> None:
        """Delete a Kubernetes secret associated with this model deployer.

        Do this if no Seldon Core V2 models are using it. The only exception
        is if the secret name is the one pre-configured in the model deployer
        configuration.

        Args:
            secret_name: The name of the Kubernetes secret to delete.
        """
        if secret_name == self.config.kubernetes_secret_name:
            return

        # fetch all the Seldon Core V2 models that currently
        # configured to use this secret
        services = self.find_model_server()
        for service in services:
            config = cast(SeldonV2ModelConfig, service.config)
            if config.secret_name == secret_name:
                return
        self.seldon_v2_client.delete_secret(secret_name)

    def deploy_model(
        self,
        config: ServiceConfig,
        replace: bool = False,
        timeout: int = DEFAULT_SELDON_V2_MODEL_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Create a new Seldon Core V2 model or update an existing one.

        # noqa: DAR402

        This should serve the supplied model and model configuration.

        This method has two modes of operation, depending on the `replace`
        argument value:

          * if `replace` is False, calling this method will create a new Seldon
            Core model server to reflect the model and other configuration
            parameters specified in the supplied Seldon model `config`.

          * if `replace` is True, this method will first attempt to find an
            existing Seldon Core V2 model that is *equivalent* to the supplied
            configuration parameters. Two or more Seldon Core V2 models are
            considered equivalent if they have the same `pipeline_name`,
            `pipeline_step_name` and `name` configuration parameters. To
            put it differently, two Seldon Core V2 models are equivalent if
            they serve versions of the same model deployed by the same pipeline
            step. If an equivalent Seldon Core V2 model is found, it will be
            updated in place to reflect the new configuration parameters. This
            allows an existing Seldon Core V2 model to retain its prediction
            URL while performing a rolling update to serve a new model version.

        Callers should set `replace` to True if they want a continuous model
        model workflow that doesn't spin up a new Seldon Core V2 model
        server for each new model version. If multiple equivalent Seldon Core V2
        models are found, the most recently created model is selected
        to be updated and the others are deleted.

        Args:
            config: the configuration of the model to be deployed with Seldon.
                Core
            replace: set this flag to True to find and update an equivalent
                Seldon Core V2 model server with the new model instead of
                starting a new model server.
            timeout: the timeout in seconds to wait for the Seldon Core V2 server
                to be provisioned and successfully started or updated. If set
                to 0, the method will return immediately after the Seldon Core V2
                server is provisioned, without waiting for it to fully start.

        Returns:
            The ZenML Seldon Core V2 model service object that can be used to
            interact with the remote Seldon Core V2 server.

        Raises:
            SeldonClientError: if a Seldon Core V2 client error is encountered
                while provisioning the Seldon Core V2 model server.
            RuntimeError: if `timeout` is set to a positive value that is
                exceeded while waiting for the Seldon Core V2 model server
                to start, or if an operational failure is encountered before
                it reaches a ready state.
        """
        with event_handler(
            event=AnalyticsEvent.MODEL_DEPLOYED, v2=True
        ) as analytics_handler:
            config = cast(SeldonV2ModelConfig, config)
            service = None

            # if replace is True, find equivalent Seldon Core V2 models
            if replace is True:
                equivalent_services = self.find_model_server(
                    running=False,
                    pipeline_name=config.pipeline_name,
                    pipeline_step_name=config.pipeline_step_name,
                    model_name=config.name,
                )

                for equivalent_service in equivalent_services:
                    if service is None:
                        # keep the most recently created service
                        service = equivalent_service
                    else:
                        try:
                            # delete the older services and don't wait for
                            # them to be deprovisioned
                            service.stop()
                        except RuntimeError:
                            # ignore errors encountered while stopping old
                            # services
                            pass

            # if a custom Kubernetes secret is not explicitly specified in the
            # SeldonV2ModelConfig, try to create one from the ZenML secret
            # configured for the model deployer
            config.secret_name = (
                config.secret_name
                or self._create_or_update_kubernetes_secret()
            )

            if service:
                # update an equivalent service in place
                service.update(config)
                logger.info(
                    f"Updating an existing Seldon model service: {service}"
                )
            else:
                # create a new service
                service = SeldonV2ModelService(config=config)
                logger.info(f"Creating a new Seldon model service: {service}")

            # start the service which in turn provisions the Seldon Core V2
            # model server and waits for it to reach a ready state
            service.start(timeout=timeout)

            # Add telemetry with metadata that gets the stack metadata and
            # differentiates between pure model and custom code models
            stack = Client().active_stack
            stack_metadata = {
                component_type.value: component.flavor
                for component_type, component in stack.components.items()
            }
            analytics_handler.metadata = {
                "store_type": Client().zen_store.type.value,
                **stack_metadata,
            }

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
        requirements: Optional[List[str]] = None,
    ) -> List[BaseService]:
        """Find one or more Seldon Core V2 model services that match the given criteria.

        The Seldon Core V2 model services that meet the search criteria are
        returned sorted in descending order of their creation time (i.e. more
        recent models first).

        Args:
            running: if true, only running services will be returned.
            service_uuid: the UUID of the Seldon Core V2 service that was
                originally used to create the Seldon Core V2 model resource.
            pipeline_name: name of the pipeline that the deployed model was part
                of.
            run_name: Name of the pipeline run which the deployed model was
                part of.
            pipeline_step_name: the name of the pipeline model model step
                that deployed the model.
            model_name: the name of the deployed model.
            model_type: the type of the deployed model.
            model_uri: URI of the deployed model.
            requirements: the requirements of the deployed model as a list of
                strings.

        Returns:
            One or more Seldon Core V2 service objects representing Seldon Core V2
            model servers that match the input search criteria.
        """
        # Use a Seldon model service configuration to compute the labels
        config = SeldonV2ModelConfig(
            pipeline_name=pipeline_name or "",
            run_name=run_name or "",
            pipeline_run_id=run_name or "",
            pipeline_step_name=pipeline_step_name or "",
            name=model_name or "",
            model_uri=model_uri or "",
            requirements=requirements or [],
        )
        labels = config.get_seldon_model_labels()
        if service_uuid:
            # the service UUID is not a label covered by the Seldon
            # model service configuration, so we need to add it
            # separately
            labels["zenml.service_uuid"] = str(service_uuid)

        models = self.seldon_v2_client.find_models(labels=labels)
        # sort the models in descending order of their creation time
        models.sort(
            key=lambda model: datetime.strptime(
                model.metadata.creationTimestamp,
                "%Y-%m-%dT%H:%M:%SZ",
            )
            if model.metadata.creationTimestamp
            else datetime.min,
            reverse=True,
        )

        services: List[BaseService] = []
        for model in models:
            # recreate the Seldon model service object from the Seldon
            # model resource
            service = SeldonV2ModelService.create_from_model(model=model)
            if running and not service.is_running:
                # skip non-running services
                continue
            services.append(service)

        return services

    def stop_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_SELDON_V2_MODEL_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Stop a Seldon Core V2 model server.

        Args:
            uuid: UUID of the model server to stop.
            timeout: timeout in seconds to wait for the service to stop.
            force: if True, force the service to stop.

        Raises:
            NotImplementedError: stopping Seldon Core V2 model servers is not
                supported.
        """
        raise NotImplementedError(
            "Stopping Seldon Core V2 model servers is not implemented. Try "
            "deleting the Seldon Core V2 model server instead."
        )

    def start_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_SELDON_V2_MODEL_START_STOP_TIMEOUT,
    ) -> None:
        """Start a Seldon Core V2 model model server.

        Args:
            uuid: UUID of the model server to start.
            timeout: timeout in seconds to wait for the service to become
                active. . If set to 0, the method will return immediately after
                provisioning the service, without waiting for it to become
                active.

        Raises:
            NotImplementedError: since we don't support starting Seldon Core V2
                model servers
        """
        raise NotImplementedError(
            "Starting Seldon Core V2 model servers is not implemented"
        )

    def delete_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_SELDON_V2_MODEL_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Delete a Seldon Core V2 model model server.

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

        service = services[0]

        assert isinstance(service, SeldonV2ModelService)
        service.stop(timeout=timeout, force=force)

        if service.config.secret_name:
            # delete the Kubernetes secret used to store the authentication
            # information for the Seldon Core V2 model server storage initializer
            # if no other Seldon Core V2 model servers are using it
            self._delete_kubernetes_secret(service.config.secret_name)
