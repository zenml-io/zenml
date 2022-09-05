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
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, cast
from uuid import UUID

from kserve import KServeClient, V1beta1InferenceService, constants, utils
from kubernetes import client

from zenml.config.global_config import GlobalConfiguration
from zenml.integrations.kserve import KSERVE_MODEL_DEPLOYER_FLAVOR
from zenml.integrations.kserve.services.kserve_deployment import (
    KServeDeploymentConfig,
    KServeDeploymentService,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.model_deployers.base_model_deployer import BaseModelDeployer
from zenml.repository import Repository
from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager
from zenml.services.service import BaseService, ServiceConfig
from zenml.stack.stack import Stack
from zenml.utils.analytics_utils import AnalyticsEvent, track_event
from zenml.utils.pipeline_docker_image_builder import PipelineDockerImageBuilder

if TYPE_CHECKING:
    from zenml.config.docker_configuration import DockerConfiguration
    from zenml.runtime_configuration import RuntimeConfiguration

logger = get_logger(__name__)

DEFAULT_KSERVE_DEPLOYMENT_START_STOP_TIMEOUT = 300


class KServeModelDeployer(BaseModelDeployer, PipelineDockerImageBuilder):
    """KServe model deployer stack component implementation.

    Attributes:
        kubernetes_context: the Kubernetes context to use to contact the remote
            KServe installation. If not specified, the current
            configuration is used. Depending on where the KServe model deployer
            is being used, this can be either a locally active context or an
            in-cluster Kubernetes configuration (if running inside a pod).
        kubernetes_namespace: the Kubernetes namespace where the KServe
            inference service CRDs are provisioned and managed by ZenML. If not
            specified, the namespace set in the current configuration is used.
            Depending on where the KServe model deployer is being used, this can
            be either the current namespace configured in the locally active
            context or the namespace in the context of which the pod is running
            (if running inside a pod).
        base_url: the base URL of the Kubernetes ingress used to expose the
            KServe inference services.
        secret: the name of the secret containing the credentials for the
            KServe inference services.
    """

    # Class Configuration
    FLAVOR: ClassVar[str] = KSERVE_MODEL_DEPLOYER_FLAVOR

    kubernetes_context: Optional[str]
    kubernetes_namespace: Optional[str]
    base_url: str
    secret: Optional[str]
    custom_domain: Optional[str]
    # private attributes
    _client: Optional[KServeClient] = None

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

    @staticmethod
    def get_active_model_deployer() -> "KServeModelDeployer":
        """Get the KServe model deployer registered in the active stack.

        Returns:
            The KServe model deployer registered in the active stack.

        Raises:
            TypeError: if the KServe model deployer is not available.
        """
        model_deployer = Repository(  # type: ignore [call-arg]
            skip_repository_check=True
        ).active_stack.model_deployer
        if not model_deployer or not isinstance(
            model_deployer, KServeModelDeployer
        ):
            raise TypeError(
                f"The active stack needs to have a KServe model deployer "
                f"component registered to be able to deploy models with KServe "
                f"You can create a new stack with a KServe model "
                f"deployer component or update your existing stack to add this "
                f"component, e.g.:\n\n"
                f"  'zenml model-deployer register kserve --flavor={KSERVE_MODEL_DEPLOYER_FLAVOR} "
                f"--kubernetes_context=context-name --kubernetes_namespace="
                f"namespace-name --base_url=https://ingress.cluster.kubernetes'\n"
                f"  'zenml stack create stack-name -d kserve ...'\n"
            )
        return model_deployer

    @property
    def kserve_client(self) -> KServeClient:
        """Get the KServe client associated with this model deployer.

        Returns:
            The KServeclient.
        """
        if not self._client:
            self._client = KServeClient(
                context=self.kubernetes_context,
            )
        return self._client

    def _set_credentials(self) -> None:
        """Set the credentials for the given service instance.

        Raises:
            RuntimeError: if the credentials are not available.
        """
        secret = self._get_kserve_secret()
        if secret:
            secret_folder = Path(
                GlobalConfiguration().config_directory,
                "kserve-storage",
                str(self.uuid),
            )
            kserve_credentials = {}
            # Handle the secrets attributes
            for key in secret.content.keys():
                content = getattr(secret, key)
                if key == "credentials" and content:
                    fileio.makedirs(str(secret_folder))
                    file_path = Path(secret_folder, f"{key}.json")
                    kserve_credentials["credentials_file"] = str(file_path)
                    with open(file_path, "w") as f:
                        f.write(content)
                    file_path.chmod(0o600)
                # Handle additional params
                else:
                    kserve_credentials[key] = content

            # We need to add the namespace to the kserve_credentials
            kserve_credentials["namespace"] = (
                self.kubernetes_namespace
                or utils.get_default_target_namespace()
            )

            try:
                self.kserve_client.set_credentials(**kserve_credentials)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to set credentials for KServe model deployer: {e}"
                )
            finally:
                if file_path.exists():
                    file_path.unlink()

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
        config = cast(KServeDeploymentConfig, config)
        service = None

        # if the secret is passed in the config, use it to set the credentials
        if config.secret_name:
            self.secret = config.secret_name or self.secret
        self._set_credentials()

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
                        # delete the older services and don't wait for them to
                        # be deprovisioned
                        service.stop()
                    except RuntimeError as e:
                        raise RuntimeError(
                            "Failed to stop the KServe deployment server:\n",
                            f"{e}\n",
                            "Please stop it manually and try again.",
                        )
        if service:
            # update an equivalent service in place
            service.update(config)
            logger.info(
                f"Updating an existing KServe deployment service: {service}"
            )
        else:
            # create a new service
            service = KServeDeploymentService(config=config)
            logger.info(f"Creating a new KServe deployment service: {service}")

        # start the service which in turn provisions the KServe
        # deployment server and waits for it to reach a ready state
        service.start(timeout=timeout)

        # Add telemetry with metadata that gets the stack metadata and
        # differentiates between pure model and custom code deployments
        stack = Repository().active_stack
        stack_metadata = {
            component_type.value: component.FLAVOR
            for component_type, component in stack.components.items()
        }
        metadata = {
            "store_type": Repository().active_profile.store_type.value,
            **stack_metadata,
            "is_custom_code_deployment": config.container is not None,
        }
        track_event(AnalyticsEvent.MODEL_DEPLOYED, metadata=metadata)

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
            self.kubernetes_namespace or utils.get_default_target_namespace()
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
        except client.rest.ApiException as e:
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
        pipeline_run_id: Optional[str] = None,
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
            pipeline_run_id: ID of the pipeline run which the deployed model was
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
            pipeline_run_id=pipeline_run_id or "",
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
        services[0].stop(timeout=timeout, force=force)

    def _get_kserve_secret(self) -> Any:
        """Get the secret object for the KServe deployment.

        Returns:
            The secret object for the KServe deployment.

        Raises:
            RuntimeError: if the secret object is not found or secrets_manager is not set.
        """
        if self.secret:

            secret_manager = Repository(  # type: ignore [call-arg]
                skip_repository_check=True
            ).active_stack.secrets_manager

            if not secret_manager or not isinstance(
                secret_manager, BaseSecretsManager
            ):
                raise RuntimeError(
                    f"The active stack doesn't have a secret manager component. "
                    f"The ZenML secret specified in the KServe Model "
                    f"Deployer configuration cannot be fetched: {self.secret}."
                )
            try:
                secret = secret_manager.get_secret(self.secret)
                return secret
            except KeyError:
                raise RuntimeError(
                    f"The secret `{self.secret}` used for your KServe Model"
                    f"Deployer configuration does not exist in your secrets "
                    f"manager `{secret_manager.name}`."
                )
        return None

    def prepare_custom_deployment_image(
        self,
        pipeline_name: str,
        stack: "Stack",
        docker_configuration: "DockerConfiguration",
        runtime_configuration: "RuntimeConfiguration",
        entrypoint: List[str],
    ) -> str:
        """Prepare the custom deployment image for the KServe deployment.

        This function is called by the deployment step of the pipeline.
        It is responsible for the preparation of the custom deployment image
        either by returning the image name in the case of a remote orchestrator
        or by building a new image if only a local orchestrator is used.

        Args:
            pipeline_name: The pipeline to be deployed.
            stack: The stack to be deployed.
            docker_configuration: The Docker configuration to be used.
            runtime_configuration: The runtime configuration to be used.
            entrypoint: The entrypoint to be used.

        Returns:
            The name of the image to be used for the deployment.
        """
        # verify the flavor of the orchestrator.
        # if the orchestrator is local, then we need to build a docker image with the repo
        # and requirements and push it to the container registry.
        # if the orchestrator is remote, then we can use the same image used to run the pipeline.
        if stack.orchestrator.FLAVOR == "local":
            # more information about stack ..
            custom_docker_image_name = self.build_and_push_docker_image(
                pipeline_name=pipeline_name,
                docker_configuration=docker_configuration,
                stack=stack,
                runtime_configuration=runtime_configuration,
                entrypoint=" ".join(entrypoint),
            )
        else:
            custom_docker_image_name = runtime_configuration["docker_image"]

        return custom_docker_image_name
