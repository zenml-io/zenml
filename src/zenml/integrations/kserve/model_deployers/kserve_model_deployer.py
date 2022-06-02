from dataclasses import dataclass
import datetime
import json
import re
from typing import Any, ClassVar, Dict, List, Optional, cast
from uuid import UUID

from kserve import (  # type: ignore[import]
    KServeClient,
    V1beta1InferenceService,
    constants,
    utils,
)
from kubernetes import client
from kserve import ApiClient
import six
from zenml.integrations import kserve
from zenml.integrations.kserve import KSERVE_MODEL_DEPLOYER_FLAVOR
from zenml.integrations.kserve.services.kserve_deployment import (
    KServeDeploymentConfig,
    KServeDeploymentService,
)
from zenml.logger import get_logger
from zenml.model_deployers.base_model_deployer import BaseModelDeployer
from zenml.repository import Repository
from zenml.services.service import BaseService, ServiceConfig

logger = get_logger(__name__)

DEFAULT_KSERVE_DEPLOYMENT_START_STOP_TIMEOUT = 300

api = ApiClient()

PRIMITIVE_TYPES = (float, bool, bytes, six.text_type) + six.integer_types
NATIVE_TYPES_MAPPING = {
    'int': int,
    'float': float,
    'str': str,
    'bool': bool,
    'date': datetime.date,
    'datetime': datetime.datetime,
    'object': object,
}

class KServeModelDeployer(BaseModelDeployer):
    """Kserve model deployer stack component implementation.

    Attributes:
        kubernetes_context: the Kubernetes context to use to contact the remote
            Ksere installation. If not specified, the current
            configuration is used. Depending on where the Kserve model deployer
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
    """

    # Class Configuration
    FLAVOR: ClassVar[str] = KSERVE_MODEL_DEPLOYER_FLAVOR

    kubernetes_context: Optional[str]
    kubernetes_namespace: Optional[str]
    base_url: str

    # private attributes
    _client: Optional[KServeClient] = None

    @staticmethod
    def get_model_server_info(  # type: ignore[override]
        service_instance: KServeDeploymentService,
    ) -> Dict[str, Optional[str]]:
        """Return implementation specific information on the model server

        Args:
            service_instance: KServe deployment service object
        """
        return {
            "PREDICTION_URL": service_instance.prediction_url,
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
                f"The active stack needs to have a Kserve model deployer "
                f"component registered to be able to deploy models with Kserve "
                f"You can create a new stack with a Kserve model "
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
        """Get the Kserve client associated with this model deployer.

        Returns:
            The KServeclient.

        Raises:
            KSevrClientError: if the Kubernetes client configuration cannot be
                found.
        """
        if not self._client:
            self._client = KServeClient(
                context=self.kubernetes_context,
            )
        return self._client

    def deploy_model(
        self,
        config: ServiceConfig,
        replace: bool = False,
        timeout: int = DEFAULT_KSERVE_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Create a new Kserve deployment or update an existing one to
        serve the supplied model and deployment configuration.

        This method has two modes of operation, depending on the `replace`
        argument value:

          * if `replace` is False, calling this method will create a new Kserve
            deployment server to reflect the model and other configuration
            parameters specified in the supplied Kserve deployment `config`.

          * if `replace` is True, this method will first attempt to find an
            existing Kserve deployment that is *equivalent* to the supplied
            configuration parameters. Two or more Kserve deployments are
            considered equivalent if they have the same `pipeline_name`,
            `pipeline_step_name` and `model_name` configuration parameters. To
            put it differently, two Kserve deployments are equivalent if
            they serve versions of the same model deployed by the same pipeline
            step. If an equivalent Kserve deployment is found, it will be
            updated in place to reflect the new configuration parameters. This
            allows an existing Kserve deployment to retain its prediction
            URL while performing a rolling update to serve a new model version.

        Callers should set `replace` to True if they want a continuous model
        deployment workflow that doesn't spin up a new Kserve deployment
        server for each new model version. If multiple equivalent Kserve
        deployments are found, the most recently created deployment is selected
        to be updated and the others are deleted.

        Args:
            config: the configuration of the model to be deployed with Kserve.
            replace: set this flag to True to find and update an equivalent
                KServedeployment server with the new model instead of
                starting a new deployment server.
            timeout: the timeout in seconds to wait for the Kserve server
                to be provisioned and successfully started or updated. If set
                to 0, the method will return immediately after the Kserve
                server is provisioned, without waiting for it to fully start.

        Returns:
            The ZenML Kserve deployment service object that can be used to
            interact with the remote Kserve server.

        Raises:
            RuntimeError: if `timeout` is set to a positive value that is
                exceeded while waiting for the Kserve deployment server
                to start, or if an operational failure is encountered before
                it reaches a ready state.
        """
        config = cast(KServeDeploymentConfig, config)
        service = None

        # if replace is True, find equivalent Kserve deployments
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
                f"Updating an existing Kserve deployment service: {service}"
            )
        else:
            # create a new service
            service = KServeDeploymentService(config=config)
            logger.info(f"Creating a new Kserve deployment service: {service}")

        # start the service which in turn provisions the Kserve
        # deployment server and waits for it to reach a ready state
        service.start(timeout=timeout)
        return service

    def get_kserve_deployments(
        self, labels: Dict[str, str]
    ) -> List[V1beta1InferenceService]:
        labels = labels or {}
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
        #   V1beta1InferenceService object recursively using the openapi
        #   schema (this doesn't work right now)

        inference_services: List[V1beta1InferenceService] = []
        for item in response.get("items", []):
            snake_case_item = self._camel_to_snake(item)
            inference_service = V1beta1InferenceService(**snake_case_item)
            inference_services.append(inference_service)
        return inference_services

    def _camel_to_snake(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(obj, (str, int, float)):
            return obj
        if isinstance(obj, dict):
            new = obj.__class__()
            for k, v in obj.items():
                new[self._convert_to_snake(k)] = self._camel_to_snake(v)
        elif isinstance(obj, (list, set, tuple)):
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
        model_type: Optional[str] = None,
        predictor: Optional[str] = None,
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
            # the service UUID is not a label covered by the KServe
            # deployment service configuration, so we need to add it
            # separately
            labels["zenml.service_uuid"] = str(service_uuid)

        deployments = self.get_kserve_deployments(labels=labels)

        # sort the deployments in descending order of their creation time
        # deployments.sort(
        #     key=lambda deployment: datetime.strptime(
        #         deployment.metadata.creationTimestamp,
        #         "%Y-%m-%dT%H:%M:%SZ",
        #     )
        #     if deployment.metadata.creationTimestamp
        #     else datetime.min,
        #     reverse=True,
        # )

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
        raise NotImplementedError("stop_model_server")

    def start_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_KSERVE_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> None:
        raise NotImplementedError("start_model_server")

    def delete_model_server(
        self,
        uuid: UUID,
        timeout: int = DEFAULT_KSERVE_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        services = self.find_model_server(service_uuid=uuid)
        if len(services) == 0:
            return
        services[0].stop(timeout=timeout, force=force)
