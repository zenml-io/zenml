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
"""Implementation of the KServe Model Deployer."""
import base64
import json
import re
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    cast,
)
from uuid import UUID, uuid4

from kserve import KServeClient, V1beta1InferenceService, constants, utils
from kubernetes import client as k8s_client

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_handler
from zenml.client import Client
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import StackComponentType
from zenml.integrations.kserve.constants import (
    KSERVE_CUSTOM_DEPLOYMENT,
    KSERVE_DOCKER_IMAGE_KEY,
)
from zenml.integrations.kserve.flavors.kserve_model_deployer_flavor import (
    KServeModelDeployerConfig,
    KServeModelDeployerFlavor,
)
from zenml.integrations.kserve.secret_schemas.secret_schemas import (
    KServeAzureSecretSchema,
    KServeGSSecretSchema,
    KServeS3SecretSchema,
)
from zenml.integrations.kserve.services.kserve_deployment import (
    KServeDeploymentConfig,
    KServeDeploymentService,
)
from zenml.logger import get_logger
from zenml.model_deployers import BaseModelDeployer, BaseModelDeployerFlavor
from zenml.secret.base_secret import BaseSecretSchema
from zenml.services.service import BaseService, ServiceConfig
from zenml.stack import StackValidator

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentBase

logger = get_logger(__name__)

DEFAULT_KSERVE_DEPLOYMENT_START_STOP_TIMEOUT = 300


class KubeClientKServeClient(KServeClient):  # type: ignore[misc]
    """KServe client initialized from a Kubernetes client.

    This is a workaround for the fact that the native KServe client does not
    support initialization from an existing Kubernetes client.
    """

    def __init__(
        self, kube_client: k8s_client.ApiClient, *args: Any, **kwargs: Any
    ) -> None:
        """Initializes the KServe client from a Kubernetes client.

        Args:
            kube_client: pre-configured Kubernetes client.
            *args: standard KServe client positional arguments.
            **kwargs: standard KServe client keyword arguments.
        """
        from kubernetes import client

        self.core_api = client.CoreV1Api(kube_client)
        self.app_api = client.AppsV1Api(kube_client)
        self.api_instance = client.CustomObjectsApi(kube_client)


class KServeModelDeployer(BaseModelDeployer):
    """KServe model deployer stack component implementation."""

    NAME: ClassVar[str] = "KServe"
    FLAVOR: ClassVar[Type[BaseModelDeployerFlavor]] = KServeModelDeployerFlavor

    _client: Optional[KServeClient] = None

    @property
    def config(self) -> KServeModelDeployerConfig:
        """Returns the `KServeModelDeployerConfig` config.

        Returns:
            The configuration.
        """
        return cast(KServeModelDeployerConfig, self._config)

    @property
    def validator(self) -> Optional[StackValidator]:
        """Ensures there is a container registry and image builder in the stack.

        Returns:
            A `StackValidator` instance.
        """
        # Log deprecation warning
        logger.warning(
            "The KServe model deployer is deprecated and is no longer "
            "being maintained by the ZenML core team. If you are looking for a "
            "scalable Kubernetes-based model deployment solution, consider "
            "using Seldon instead: "
            "https://docs.zenml.io/stacks-and-components/component-guide/model-deployers/seldon",
        )
        return StackValidator(
            required_components={
                StackComponentType.IMAGE_BUILDER,
            }
        )

    @staticmethod
    def get_model_server_info(  # type: ignore[override]
        service_instance: "KServeDeploymentService",
    ) -> Dict[str, Optional[str]]:
        """Return implementation specific information on the model server.

        Args:
            service_instance: KServe deployment service object

        Returns:
            A dictionary containing the model server information.
        """
        return {
            "PREDICTION_URL": service_instance.prediction_url,
            "PREDICTION_HOSTNAME": service_instance.prediction_hostname,
            "MODEL_URI": service_instance.config.model_uri,
            "MODEL_NAME": service_instance.config.model_name,
            "KSERVE_INFERENCE_SERVICE": service_instance.crd_name,
        }

    @property
    def kserve_client(self) -> KServeClient:
        """Get the KServe client associated with this model deployer.

        Returns:
            The KServeclient.

        Raises:
            RuntimeError: If the Kubernetes namespace is not configured in the
                stack component when using a service connector to deploy models
                with KServe.
        """
        # Refresh the client also if the connector has expired
        if self._client and not self.connector_has_expired():
            return self._client

        connector = self.get_connector()
        if connector:
            if not self.config.kubernetes_namespace:
                raise RuntimeError(
                    "The Kubernetes namespace must be explicitly configured in "
                    "the stack component when using a service connector to "
                    "deploy models with KServe."
                )
            client = connector.connect()
            if not isinstance(client, k8s_client.ApiClient):
                raise RuntimeError(
                    f"Expected a k8s_client.ApiClient while trying to use the "
                    f"linked connector, but got {type(client)}."
                )
            self._client = KubeClientKServeClient(
                kube_client=client,
            )
        else:
            self._client = KServeClient(
                context=self.config.kubernetes_context,
            )
        return self._client

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
            if step.config.extra.get(KSERVE_CUSTOM_DEPLOYMENT, False) is True:
                build = BuildConfiguration(
                    key=KSERVE_DOCKER_IMAGE_KEY,
                    settings=step.config.docker_settings,
                    step_name=step_name,
                )
                builds.append(build)

        return builds

    def deploy_model(
        self,
        config: ServiceConfig,
        replace: bool = False,
        timeout: int = DEFAULT_KSERVE_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Create a new KServe deployment or update an existing one.

        This method has two modes of operation, depending on the `replace`
        argument value:

          * if `replace` is False, calling this method will create a new KServe
            deployment server to reflect the model and other configuration
            parameters specified in the supplied KServe deployment `config`.

          * if `replace` is True, this method will first attempt to find an
            existing KServe deployment that is *equivalent* to the supplied
            configuration parameters. Two or more KServe deployments are
            considered equivalent if they have the same `pipeline_name`,
            `pipeline_step_name` and `model_name` configuration parameters. To
            put it differently, two KServe deployments are equivalent if
            they serve versions of the same model deployed by the same pipeline
            step. If an equivalent KServe deployment is found, it will be
            updated in place to reflect the new configuration parameters. This
            allows an existing KServe deployment to retain its prediction
            URL while performing a rolling update to serve a new model version.

        Callers should set `replace` to True if they want a continuous model
        deployment workflow that doesn't spin up a new KServe deployment
        server for each new model version. If multiple equivalent KServe
        deployments are found, the most recently created deployment is selected
        to be updated and the others are deleted.

        Args:
            config: the configuration of the model to be deployed with KServe.
            replace: set this flag to True to find and update an equivalent
                KServeDeployment server with the new model instead of
                starting a new deployment server.
            timeout: the timeout in seconds to wait for the KServe server
                to be provisioned and successfully started or updated. If set
                to 0, the method will return immediately after the KServe
                server is provisioned, without waiting for it to fully start.

        Returns:
            The ZenML KServe deployment service object that can be used to
            interact with the remote KServe server.

        Raises:
            RuntimeError: if the KServe deployment server could not be stopped.
        """
        with track_handler(AnalyticsEvent.MODEL_DEPLOYED) as analytics_handler:
            config = cast(KServeDeploymentConfig, config)
            service = None

            # if replace is True, find equivalent KServe deployments
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
                            # delete the older services and don't wait for
                            # them to be deprovisioned
                            service.stop()
                        except RuntimeError as e:
                            raise RuntimeError(
                                "Failed to stop the KServe deployment "
                                "server:\n",
                                f"{e}\n",
                                "Please stop it manually and try again.",
                            )

            if service:
                # Reuse the service account and secret from the existing
                # service.
                assert isinstance(service, KServeDeploymentService)
                config.k8s_service_account = service.config.k8s_service_account
                config.k8s_secret = service.config.k8s_secret

            # configure the credentials for the KServe model server
            self._create_or_update_kserve_credentials(config)
            if service:
                # update an equivalent service in place
                service.update(config)
                logger.info(
                    f"Updating an existing KServe deployment service: {service}"
                )
            else:
                # create a new service
                service = KServeDeploymentService(config=config)
                logger.info(
                    f"Creating a new KServe deployment service: {service}"
                )

            # start the service which in turn provisions the KServe
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
                "is_custom_code_deployment": config.container is not None,
            }
        return service

    def get_kserve_deployments(
        self, labels: Dict[str, str]
    ) -> List[V1beta1InferenceService]:
        """Get a list of KServe deployments that match the supplied labels.

        Args:
            labels: a dictionary of labels to match against KServe deployments.

        Returns:
            A list of KServe deployments that match the supplied labels.

        Raises:
            RuntimeError: if an operational failure is encountered while
        """
        label_selector = (
            ",".join(f"{k}={v}" for k, v in labels.items()) if labels else None
        )

        namespace = (
            self.config.kubernetes_namespace
            or utils.get_default_target_namespace()
        )

        try:
            response = (
                self.kserve_client.api_instance.list_namespaced_custom_object(
                    constants.KSERVE_GROUP,
                    constants.KSERVE_V1BETA1_VERSION,
                    namespace,
                    constants.KSERVE_PLURAL,
                    label_selector=label_selector,
                )
            )
        except k8s_client.rest.ApiException as e:
            raise RuntimeError(
                "Exception when retrieving KServe inference services\
                %s\n"
                % e
            )

        # TODO[CRITICAL]: de-serialize each item into a complete
        #   V1beta1InferenceService object recursively using the OpenApi
        #   schema (this doesn't work right now)
        inference_services: List[V1beta1InferenceService] = []
        for item in response.get("items", []):
            snake_case_item = self._camel_to_snake(item)
            inference_service = V1beta1InferenceService(**snake_case_item)
            inference_services.append(inference_service)
        return inference_services

    def _camel_to_snake(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a camelCase dictionary to snake_case.

        Args:
            obj: a dictionary with camelCase keys

        Returns:
            a dictionary with snake_case keys
        """
        if isinstance(obj, (str, int, float)):
            return obj
        if isinstance(obj, dict):
            assert obj is not None
            new = obj.__class__()
            for k, v in obj.items():
                new[self._convert_to_snake(k)] = self._camel_to_snake(v)
        elif isinstance(obj, (list, set, tuple)):
            assert obj is not None
            new = obj.__class__(self._camel_to_snake(v) for v in obj)
        else:
            return obj
        return new

    def _convert_to_snake(self, k: str) -> str:
        return re.sub(r"(?<!^)(?=[A-Z])", "_", k).lower()

    def find_model_server(
        self,
        running: bool = False,
        service_uuid: Optional[UUID] = None,
        pipeline_name: Optional[str] = None,
        run_name: Optional[str] = None,
        pipeline_step_name: Optional[str] = None,
        model_name: Optional[str] = None,
        model_uri: Optional[str] = None,
        predictor: Optional[str] = None,
    ) -> List[BaseService]:
        """Find one or more KServe model services that match the given criteria.

        Args:
            running: If true, only running services will be returned.
            service_uuid: The UUID of the service that was originally used
                to deploy the model.
            pipeline_name: name of the pipeline that the deployed model was part
                of.
            run_name: name of the pipeline run which the deployed model was
                part of.
            pipeline_step_name: the name of the pipeline model deployment step
                that deployed the model.
            model_name: the name of the deployed model.
            model_uri: URI of the deployed model.
            predictor: the name of the predictor that was used to deploy the model.

        Returns:
            One or more Service objects representing model servers that match
            the input search criteria.
        """
        config = KServeDeploymentConfig(
            pipeline_name=pipeline_name or "",
            run_name=run_name or "",
            pipeline_run_id=run_name or "",
            pipeline_step_name=pipeline_step_name or "",
            model_uri=model_uri or "",
            model_name=model_name or "",
            predictor=predictor or "",
            resources={},
        )
        labels = config.get_kubernetes_labels()

        if service_uuid:
            labels["zenml.service_uuid"] = str(service_uuid)

        deployments = self.get_kserve_deployments(labels=labels)

        services: List[BaseService] = []
        for deployment in deployments:
            # recreate the KServe deployment service object from the KServe
            # deployment resource
            service = KServeDeploymentService.create_from_deployment(
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
        timeout: int = DEFAULT_KSERVE_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Stop a KServe model server.

        Args:
            uuid: UUID of the model server to stop.
            timeout: timeout in seconds to wait for the service to stop.
            force: if True, force the service to stop.

        Raises:
            NotImplementedError: stopping on KServe model servers is not
                supported.
        """
        raise NotImplementedError(
            "Stopping KServe model servers is not implemented. Try "
            "deleting the KServe model server instead."
        )

    def start_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_KSERVE_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> None:
        """Start a KServe model deployment server.

        Args:
            uuid: UUID of the model server to start.
            timeout: timeout in seconds to wait for the service to become
                active. . If set to 0, the method will return immediately after
                provisioning the service, without waiting for it to become
                active.

        Raises:
            NotImplementedError: since we don't support starting KServe
                model servers
        """
        raise NotImplementedError(
            "Starting KServe model servers is not implemented"
        )

    def delete_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_KSERVE_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Delete a KServe model deployment server.

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
        service.stop(timeout=timeout, force=force)
        assert isinstance(service, KServeDeploymentService)
        if service.config.k8s_service_account:
            self.delete_k8s_service_account(service.config.k8s_service_account)
        if service.config.k8s_secret:
            self.delete_k8s_secret(service.config.k8s_secret)

    def _create_or_update_kserve_credentials(
        self, config: KServeDeploymentConfig
    ) -> None:
        """Create or update the KServe credentials used to access the artifact store.

        The way KServe allows configured credentials to be passed to the
        model servers is a bit convoluted:

          * we need to create a Kubernetes secret object with credentials
            in the correct format supported by KServe (only AWS, GCP, Azure are
            supported)
          * we need to create a Kubernetes service account object that
            references the secret object
          * we need to use the service account object in the KServe
            deployment configuration

        This method will use a random name for every model server. This ensures
        that we can create multiple KServe deployments with different
        credentials without running into naming conflicts.

        If a ZenML secret is not explicitly configured for the model deployment
        or the model deployer, this method attempts to fetch credentials from
        the active artifact store and convert them into the appropriate secret
        format expected by KServe.

        Args:
            config: KServe deployment configuration.

        Raises:
            RuntimeError: if the configured secret object is not found.
        """
        secret_name = config.secret_name or self.config.secret

        if secret_name:
            if config.secret_name:
                secret_source = "model deployment"
            else:
                secret_source = "Model Deployer"

            logger.warning(
                f"Your KServe {secret_source} is configured to use a "
                f"ZenML secret `{secret_name}` that holds credentials needed "
                "to access the artifact store. The recommended authentication "
                "method is to configure credentials for the artifact store "
                "stack component instead. The KServe model deployer will use "
                "those credentials to authenticate to the artifact store "
                "automatically."
            )

            try:
                zenml_secret = Client().get_secret_by_name_and_scope(
                    secret_name
                )
            except KeyError as e:
                raise RuntimeError(
                    f"The ZenML secret '{secret_name}' specified in the "
                    f"KServe {secret_source} configuration was not found "
                    f"in the secrets store: {e}."
                )

            credentials = zenml_secret.secret_values

        else:
            # if no secret is configured, try to fetch credentials from the
            # active artifact store and convert them into the appropriate format
            # expected by KServe
            converted_secret = self._convert_artifact_store_secret()

            if not converted_secret:
                # If a secret and service account were previously configured, we
                # need to delete them before we can proceed
                if config.k8s_service_account:
                    self.delete_k8s_service_account(config.k8s_service_account)
                    config.k8s_service_account = None
                if config.k8s_secret:
                    self.delete_k8s_secret(config.k8s_secret)
                    config.k8s_secret = None
                return

            credentials = converted_secret.get_values()

        # S3 credentials are special because part of them need to be passed
        # as annotations
        annotations: Dict[str, str] = {}
        if "aws_access_key_id" in credentials:
            if credentials.get("s3_region"):
                annotations[
                    "serving.kubeflow.org/s3-region"
                ] = credentials.pop("s3_region")
            if credentials.get("s3_endpoint"):
                annotations[
                    "serving.kubeflow.org/s3-endpoint"
                ] = credentials.pop("s3_endpoint")
            if credentials.get("s3_use_https"):
                annotations[
                    "serving.kubeflow.org/s3-usehttps"
                ] = credentials.pop("s3_use_https")
            if credentials.get("s3_verify_ssl"):
                annotations[
                    "serving.kubeflow.org/s3-verifyssl"
                ] = credentials.pop("s3_verify_ssl")

        # Convert all keys to uppercase
        credentials = {k.upper(): v for k, v in credentials.items()}

        # The GCP credentials need to use a specific key name
        if "GOOGLE_APPLICATION_CREDENTIALS" in credentials:
            credentials[
                "gcloud-application-credentials.json"
            ] = credentials.pop("GOOGLE_APPLICATION_CREDENTIALS")

        # Create or update the Kubernetes secret object
        config.k8s_secret = self.create_or_update_k8s_secret(
            name=config.k8s_secret,
            annotations=annotations,
            secret_values=credentials,
        )

        # Create or update the Kubernetes service account object
        config.k8s_service_account = self.create_or_update_k8s_service_account(
            name=config.k8s_service_account,
            secret_name=config.k8s_secret,
        )

    def _convert_artifact_store_secret(self) -> Optional[BaseSecretSchema]:
        """Convert the credentials configured for the artifact store into a ZenML secret.

        Returns:
            The KServe credentials in the format expected by KServe or None if
            no credentials are configured for the artifact store or if they
            cannot be converted into the KServe format.
        """
        artifact_store = Client().active_stack.artifact_store

        zenml_secret: BaseSecretSchema

        if artifact_store.flavor == "s3":
            from zenml.integrations.s3.artifact_stores import S3ArtifactStore

            assert isinstance(artifact_store, S3ArtifactStore)

            (
                aws_access_key_id,
                aws_secret_access_key,
                _,
            ) = artifact_store.get_credentials()

            if aws_access_key_id and aws_secret_access_key:
                # Convert the credentials into the format expected by KServe
                zenml_secret = KServeS3SecretSchema(
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                )
                if artifact_store.config.client_kwargs:
                    if "endpoint_url" in artifact_store.config.client_kwargs:
                        zenml_secret.s3_endpoint = str(
                            artifact_store.config.client_kwargs["endpoint_url"]
                        )
                    if "region_name" in artifact_store.config.client_kwargs:
                        zenml_secret.s3_region = str(
                            artifact_store.config.client_kwargs["region_name"]
                        )
                    if "use_ssl" in artifact_store.config.client_kwargs:
                        zenml_secret.s3_use_https = str(
                            artifact_store.config.client_kwargs["use_ssl"]
                        )

                return zenml_secret

            logger.warning(
                "No credentials are configured for the active S3 artifact "
                "store. The KServe model deployer will assume an "
                "implicit form of authentication is available in the "
                "target Kubernetes cluster, but the served model may not "
                "be able to access the model artifacts."
            )

            # Assume implicit in-cluster IAM authentication
            return None

        elif artifact_store.flavor == "gcp":
            from zenml.integrations.gcp.artifact_stores import GCPArtifactStore

            assert isinstance(artifact_store, GCPArtifactStore)

            gcp_credentials = artifact_store.get_credentials()

            if gcp_credentials:
                # Convert the credentials into the format expected by KServe
                return KServeGSSecretSchema(
                    google_application_credentials=json.dumps(gcp_credentials),
                )

            logger.warning(
                "No credentials are configured for the active GCS artifact "
                "store. The KServe model deployer will assume an "
                "implicit form of authentication is available in the "
                "target Kubernetes cluster, but the served model may not "
                "be able to access the model artifacts."
            )
            return None

        elif artifact_store.flavor == "azure":
            from zenml.integrations.azure.artifact_stores import (
                AzureArtifactStore,
            )

            assert isinstance(artifact_store, AzureArtifactStore)

            azure_credentials = artifact_store.get_credentials()

            if azure_credentials:
                # Convert the credentials into the format expected by KServe
                if (
                    azure_credentials.client_id is not None
                    and azure_credentials.client_secret is not None
                    and azure_credentials.tenant_id is not None
                ):
                    return KServeAzureSecretSchema(
                        azure_client_id=azure_credentials.client_id,
                        azure_client_secret=azure_credentials.client_secret,
                        azure_tenant_id=azure_credentials.tenant_id,
                    )
                else:
                    logger.warning(
                        "The KServe model deployer could not use the "
                        "credentials currently configured in the active Azure "
                        "artifact store because it only supports service "
                        "principal Azure credentials. "
                        "Please configure Azure principal credentials for your "
                        "artifact store or specify a custom ZenML secret in "
                        "the model deployer configuration that holds the "
                        "credentials required to access the model artifacts. "
                        "The KServe model deployer will assume an implicit "
                        "form of authentication is available in the target "
                        "Kubernetes cluster, but the served model "
                        "may not be able to access the model artifacts."
                    )

                    return None

            logger.warning(
                "No credentials are configured for the active Azure "
                "artifact store. The Seldon Core model deployer will "
                "assume an implicit form of authentication is available "
                "in the target Kubernetes cluster, but the served model "
                "may not be able to access the model artifacts."
            )
            return None

        logger.warning(
            "The KServe model deployer doesn't know how to configure "
            f"credentials automatically for the `{artifact_store.flavor}` "
            "active artifact store flavor. "
            "Please use one of the supported artifact stores (S3 or GCP) "
            "or specify a ZenML secret in the model deployer "
            "configuration that holds the credentials required to access "
            "the model artifacts. The KServe model deployer will "
            "assume an implicit form of authentication is available "
            "in the target Kubernetes cluster, but the served model "
            "may not be able to access the model artifacts."
        )

        return None

    def create_or_update_k8s_secret(
        self,
        name: Optional[str] = None,
        secret_values: Dict[str, Any] = {},
        annotations: Dict[str, str] = {},
    ) -> str:
        """Create or update a Kubernetes Secret resource.

        Args:
            name: the name of the Secret resource to create. If not
                specified, a random name will be generated.
            secret_values: secret key-values that should be
                stored in the Secret resource.
            annotations: optional annotations to add to the Secret resource.

        Returns:
            The name of the created Secret resource.

        Raises:
            RuntimeError: if an unknown error occurs during the creation of
                the secret.
        """
        name = name or f"zenml-kserve-{uuid4().hex}"

        try:
            logger.debug(f"Creating Secret resource: {name}")

            core_api = k8s_client.CoreV1Api()

            secret_data = {
                k: base64.b64encode(str(v).encode("utf-8")).decode("ascii")
                for k, v in secret_values.items()
                if v is not None
            }

            secret = k8s_client.V1Secret(
                metadata=k8s_client.V1ObjectMeta(
                    name=name,
                    labels={"app": "zenml"},
                    annotations=annotations,
                ),
                type="Opaque",
                data=secret_data,
            )

            try:
                # check if the secret is already present
                core_api.read_namespaced_secret(
                    name=name,
                    namespace=self.config.kubernetes_namespace,
                )
                # if we got this far, the secret is already present, update it
                # in place
                response = core_api.replace_namespaced_secret(
                    name=name,
                    namespace=self.config.kubernetes_namespace,
                    body=secret,
                )
            except k8s_client.rest.ApiException as e:
                if e.status != 404:
                    # if an error other than 404 is raised here, treat it
                    # as an unexpected error
                    raise RuntimeError(
                        "Exception when reading Secret resource: %s", str(e)
                    )
                response = core_api.create_namespaced_secret(
                    namespace=self.config.kubernetes_namespace,
                    body=secret,
                )
            logger.debug("Kubernetes API response: %s", response)
        except k8s_client.rest.ApiException as e:
            raise RuntimeError(
                "Exception when creating Secret resource %s", str(e)
            )

        return name

    def delete_k8s_secret(
        self,
        name: str,
    ) -> None:
        """Delete a Kubernetes Secret resource managed by ZenML.

        Args:
            name: the name of the Kubernetes Secret resource to delete.

        Raises:
            RuntimeError: if an unknown error occurs during the removal
                of the secret.
        """
        try:
            logger.debug(f"Deleting Secret resource: {name}")

            core_api = k8s_client.CoreV1Api()

            response = core_api.delete_namespaced_secret(
                name=name,
                namespace=self.config.kubernetes_namespace,
            )
            logger.debug("Kubernetes API response: %s", response)
        except k8s_client.rest.ApiException as e:
            if e.status == 404:
                # the secret is no longer present, nothing to do
                return
            raise RuntimeError(
                f"Exception when deleting Secret resource {name}: {e}"
            )

    def create_or_update_k8s_service_account(
        self, name: Optional[str] = None, secret_name: Optional[str] = None
    ) -> str:
        """Create or update a Kubernetes ServiceAccount resource with a secret managed by ZenML.

        Args:
            name: the name of the ServiceAccount resource to create. If not
                specified, a random name will be generated.
            secret_name: the name of a secret to attach to the ServiceAccount.

        Returns:
            The name of the created ServiceAccount resource.

        Raises:
            RuntimeError: if an unknown error occurs during the creation of
                the service account.
        """
        name = name or f"zenml-kserve-{uuid4().hex}"

        service_account = k8s_client.V1ServiceAccount(
            metadata=k8s_client.V1ObjectMeta(
                name=name,
            ),
        )

        if secret_name:
            service_account.secrets = [
                k8s_client.V1ObjectReference(kind="Secret", name=secret_name)
            ]

        core_api = k8s_client.CoreV1Api()

        try:
            # check if the service account is already present
            core_api.read_namespaced_service_account(
                name=name,
                namespace=self.config.kubernetes_namespace,
            )
            # if we got this far, the service account is already present, update
            # it in place
            core_api.replace_namespaced_service_account(
                name=name,
                namespace=self.config.kubernetes_namespace,
                body=service_account,
            )
        except k8s_client.rest.ApiException as e:
            if e.status != 404:
                # if an error other than 404 is raised here, treat it
                # as an unexpected error
                raise RuntimeError(
                    "Exception when reading ServiceAccount resource: %s",
                    str(e),
                )
            core_api.create_namespaced_service_account(
                namespace=self.config.kubernetes_namespace,
                body=service_account,
            )

        return name

    def delete_k8s_service_account(
        self,
        name: str,
    ) -> None:
        """Delete a Kubernetes ServiceAccount resource managed by ZenML.

        Args:
            name: the name of the Kubernetes ServiceAccount resource to delete.

        Raises:
            RuntimeError: if an unknown error occurs during the removal
                of the service account.
        """
        try:
            logger.debug(f"Deleting ServiceAccount resource: {name}")

            core_api = k8s_client.CoreV1Api()

            response = core_api.delete_namespaced_service_account(
                name=name,
                namespace=self.config.kubernetes_namespace,
            )
            logger.debug("Kubernetes API response: %s", response)
        except k8s_client.rest.ApiException as e:
            if e.status == 404:
                # the service account is no longer present, nothing to do
                return
            raise RuntimeError(
                f"Exception when deleting ServiceAccount resource {name}: {e}"
            )
