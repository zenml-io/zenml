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
"""Implementation of the Seldon Model Deployer."""

import json
import re
from typing import TYPE_CHECKING, ClassVar, Dict, List, Optional, Type, cast
from uuid import UUID

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_handler
from zenml.client import Client
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import StackComponentType
from zenml.integrations.seldon.constants import (
    SELDON_CUSTOM_DEPLOYMENT,
    SELDON_DOCKER_IMAGE_KEY,
)
from zenml.integrations.seldon.flavors.seldon_model_deployer_flavor import (
    SeldonModelDeployerConfig,
    SeldonModelDeployerFlavor,
)
from zenml.integrations.seldon.secret_schemas.secret_schemas import (
    SeldonAzureSecretSchema,
    SeldonGSSecretSchema,
    SeldonS3SecretSchema,
)
from zenml.integrations.seldon.seldon_client import SeldonClient
from zenml.integrations.seldon.services.seldon_deployment import (
    SeldonDeploymentConfig,
    SeldonDeploymentService,
)
from zenml.logger import get_logger
from zenml.model_deployers import BaseModelDeployer, BaseModelDeployerFlavor
from zenml.secret.base_secret import BaseSecretSchema
from zenml.services.service import BaseService, ServiceConfig
from zenml.stack import StackValidator

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentBase

logger = get_logger(__name__)

DEFAULT_SELDON_DEPLOYMENT_START_STOP_TIMEOUT = 300


class SeldonModelDeployer(BaseModelDeployer):
    """Seldon Core model deployer stack component implementation."""

    NAME: ClassVar[str] = "Seldon Core"
    FLAVOR: ClassVar[Type[BaseModelDeployerFlavor]] = SeldonModelDeployerFlavor

    _client: Optional[SeldonClient] = None

    @property
    def config(self) -> SeldonModelDeployerConfig:
        """Returns the `SeldonModelDeployerConfig` config.

        Returns:
            The configuration.
        """
        return cast(SeldonModelDeployerConfig, self._config)

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
        service_instance: "SeldonDeploymentService",
    ) -> Dict[str, Optional[str]]:
        """Return implementation specific information that might be relevant to the user.

        Args:
            service_instance: Instance of a SeldonDeploymentService

        Returns:
            Model server information.
        """
        return {
            "PREDICTION_URL": service_instance.prediction_url,
            "MODEL_URI": service_instance.config.model_uri,
            "MODEL_NAME": service_instance.config.model_name,
            "SELDON_DEPLOYMENT": service_instance.seldon_deployment_name,
        }

    @property
    def seldon_client(self) -> SeldonClient:
        """Get the Seldon Core client associated with this model deployer.

        Returns:
            The Seldon Core client.

        Raises:
            RuntimeError: If the Kubernetes namespace is not configured when
                using a service connector to deploy models with Seldon Core.
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
                    "deploy models with Seldon Core."
                )
            kube_client = connector.connect()
            if not isinstance(kube_client, k8s_client.ApiClient):
                raise RuntimeError(
                    f"Expected a k8s_client.ApiClient while trying to use the "
                    f"linked connector, but got {type(kube_client)}."
                )

        self._client = SeldonClient(
            context=self.config.kubernetes_context,
            namespace=self.config.kubernetes_namespace,
            kube_client=kube_client,
        )

        return self._client

    @property
    def kubernetes_secret_name(self) -> str:
        """Get the Kubernetes secret name associated with this model deployer.

        If a pre-existing Kubernetes secret is configured for this model
        deployer, that name is returned to be used by all Seldon Core
        deployments associated with this model deployer.

        Otherwise, a Kubernetes secret name is generated based on the ID of
        the active artifact store. The reason for this is that the same model
        deployer may be used to deploy models in combination with different
        artifact stores at the same time, and each artifact store may require
        different credentials to be accessed.

        Returns:
            The name of a Kubernetes secret to be used with Seldon Core
            deployments.
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

    def get_docker_builds(
        self, deployment: "PipelineDeploymentBase"
    ) -> List["BuildConfiguration"]:
        """Gets the Docker builds required for the component.

        Args:
            deployment: The pipeline deployment for which to get the builds.

        Returns:
            The required Docker builds.
        """
        builds = []
        for step_name, step in deployment.step_configurations.items():
            if step.config.extra.get(SELDON_CUSTOM_DEPLOYMENT, False) is True:
                build = BuildConfiguration(
                    key=SELDON_DOCKER_IMAGE_KEY,
                    settings=step.config.docker_settings,
                    step_name=step_name,
                )
                builds.append(build)

        return builds

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
                "Your Seldon Core model deployer is configured to use a "
                "pre-existing Kubernetes secret that holds credentials needed "
                "to access the artifact store. The authentication method is "
                "deprecated and will be removed in a future release. Please "
                "remove this attribute by running `zenml model-deployer "
                f"remove-attribute {self.name} --kubernetes_secret_name` and "
                "configure credentials for the artifact store stack component "
                "instead. The Seldon Core model deployer will use those "
                "credentials to authenticate to the artifact store "
                "automatically."
            )

            return self.config.kubernetes_secret_name

        # if a ZenML secret reference was configured in the model deployer,
        # create a Kubernetes secret from that
        if self.config.secret:
            logger.warning(
                "Your Seldon Core model deployer is configured to use a "
                "ZenML secret that holds credentials needed to access the "
                "artifact store. The recommended authentication method is to "
                "configure credentials for the artifact store stack component "
                "instead. The Seldon Core model deployer will use those "
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
                    f"Seldon Core Model Deployer configuration was not found "
                    f"in the secrets store: {e}."
                )

            self.seldon_client.create_or_update_secret(
                self.kubernetes_secret_name, zenml_secret.secret_values
            )

        else:
            # if no ZenML secret was configured, try to convert the credentials
            # configured for the artifact store, if any are included, into
            # the format expected by Seldon Core
            converted_secret = self._convert_artifact_store_secret()

            self.seldon_client.create_or_update_secret(
                self.kubernetes_secret_name, converted_secret.get_values()
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
                region_name,
                aws_access_key_id,
                aws_secret_access_key,
                aws_session_token,
            ) = artifact_store.get_credentials()

            if aws_access_key_id and aws_secret_access_key:
                # Convert the credentials into the format expected by Seldon
                # Core
                zenml_secret = SeldonS3SecretSchema(
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
                "store. The Seldon Core model deployer will assume an "
                "implicit form of authentication is available in the "
                "target Kubernetes cluster, but the served model may not "
                "be able to access the model artifacts."
            )

            # Assume implicit in-cluster IAM authentication
            return SeldonS3SecretSchema(rclone_config_s3_env_auth=True)

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
                            rclone_config_gs_service_account_credentials=json.dumps(
                                gcp_credentials
                            ),
                        )
                    elif gcp_credentials.get("type") == "authorized_user":
                        return SeldonGSSecretSchema(
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
                        rclone_config_gs_token=json.dumps(
                            dict(
                                access_token=gcp_credentials.token,
                            )
                        ),
                    )

            logger.warning(
                "No credentials are configured for the active GCS artifact "
                "store. The Seldon Core model deployer will assume an "
                "implicit form of authentication is available in the "
                "target Kubernetes cluster, but the served model may not "
                "be able to access the model artifacts."
            )
            return SeldonGSSecretSchema(rclone_config_gs_anonymous=False)

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
                        rclone_config_az_account=account_name,
                        rclone_config_az_key=account_key,
                    )

                if azure_credentials.sas_token is not None:
                    return SeldonAzureSecretSchema(
                        rclone_config_az_sas_url=azure_credentials.sas_token,
                    )

                if (
                    azure_credentials.account_name is not None
                    and azure_credentials.account_key is not None
                ):
                    return SeldonAzureSecretSchema(
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
                        rclone_config_az_client_id=azure_credentials.client_id,
                        rclone_config_az_client_secret=azure_credentials.client_secret,
                        rclone_config_az_tenant=azure_credentials.tenant_id,
                    )

            logger.warning(
                "No credentials are configured for the active Azure "
                "artifact store. The Seldon Core model deployer will "
                "assume an implicit form of authentication is available "
                "in the target Kubernetes cluster, but the served model "
                "may not be able to access the model artifacts."
            )
            return SeldonAzureSecretSchema(rclone_config_az_env_auth=True)

        raise RuntimeError(
            "The Seldon Core model deployer doesn't know how to configure "
            f"credentials automatically for the `{artifact_store.flavor}` "
            "active artifact store flavor. "
            "Please use one of the supported artifact stores (S3, GCP or "
            "Azure) or specify a ZenML secret in the model deployer "
            "configuration that holds the credentials required to access "
            "the model artifacts."
        )

    def _delete_kubernetes_secret(self, secret_name: str) -> None:
        """Delete a Kubernetes secret associated with this model deployer.

        Do this if no Seldon Core deployments are using it. The only exception
        is if the secret name is the one pre-configured in the model deployer
        configuration.

        Args:
            secret_name: The name of the Kubernetes secret to delete.
        """
        if secret_name == self.config.kubernetes_secret_name:
            return

        # fetch all the Seldon Core deployments that currently
        # configured to use this secret
        services = self.find_model_server()
        for service in services:
            config = cast(SeldonDeploymentConfig, service.config)
            if config.secret_name == secret_name:
                return
        self.seldon_client.delete_secret(secret_name)

    def perform_deploy_model(
        self,
        id: UUID,
        config: ServiceConfig,
        timeout: int = DEFAULT_SELDON_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Create a new Seldon Core deployment or update an existing one.

        # noqa: DAR402

        This should serve the supplied model and deployment configuration.

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
            id: the UUID of the model server to deploy.
            config: the configuration of the model to be deployed with Seldon.
                Core
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
        with track_handler(AnalyticsEvent.MODEL_DEPLOYED) as analytics_handler:
            config = cast(SeldonDeploymentConfig, config)
            # if a custom Kubernetes secret is not explicitly specified in the
            # SeldonDeploymentConfig, try to create one from the ZenML secret
            # configured for the model deployer
            config.secret_name = (
                config.secret_name
                or self._create_or_update_kubernetes_secret()
            )
            # create a new service
            service = SeldonDeploymentService(uuid=id, config=config)
            logger.info(f"Creating a new Seldon deployment service: {service}")

            # start the service which in turn provisions the Seldon Core
            # deployment server and waits for it to reach a ready state
            service.start(timeout=timeout)

            # Add telemetry with metadata that gets the stack metadata and
            # differentiates between pure model and custom code deployments
            stack = Client().active_stack
            stack_metadata = {
                component_type.value: component.flavor
                for component_type, component in stack.components.items()
            }
            analytics_handler.metadata = {
                "store_type": Client().zen_store.type.value,
                **stack_metadata,
                "is_custom_code_deployment": config.is_custom_deployment,
            }

        return service

    def perform_stop_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_SELDON_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> BaseService:
        """Stop a Seldon Core model server.

        Args:
            service: The service to stop.
            timeout: timeout in seconds to wait for the service to stop.
            force: if True, force the service to stop.

        Raises:
            NotImplementedError: stopping Seldon Core model servers is not
                supported.
        """
        raise NotImplementedError(
            "Stopping Seldon Core model servers is not implemented. Try "
            "deleting the Seldon Core model server instead."
        )

    def perform_start_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_SELDON_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Start a Seldon Core model deployment server.

        Args:
            service: The service to start.
            timeout: timeout in seconds to wait for the service to become
                active. . If set to 0, the method will return immediately after
                provisioning the service, without waiting for it to become
                active.

        Raises:
            NotImplementedError: since we don't support starting Seldon Core
                model servers
        """
        raise NotImplementedError(
            "Starting Seldon Core model servers is not implemented"
        )

    def perform_delete_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_SELDON_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Delete a Seldon Core model deployment server.

        Args:
            service: The service to delete.
            timeout: timeout in seconds to wait for the service to stop. If
                set to 0, the method will return immediately after
                deprovisioning the service, without waiting for it to stop.
            force: if True, force the service to stop.
        """
        service = cast(SeldonDeploymentService, service)
        service.stop(timeout=timeout, force=force)

        if service.config.secret_name:
            # delete the Kubernetes secret used to store the authentication
            # information for the Seldon Core model server storage initializer
            # if no other Seldon Core model servers are using it
            self._delete_kubernetes_secret(service.config.secret_name)
