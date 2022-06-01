import os
import re
from typing import TYPE_CHECKING, Any, Dict, Generator, Optional, Tuple
from uuid import UUID

from kserve import (  # type: ignore[import]
    KServeClient,
    V1beta1InferenceService,
    V1beta1InferenceServiceSpec,
    V1beta1PredictorExtensionSpec,
    V1beta1PredictorSpec,
    constants,
)
from kubernetes import client as k8s_client
from pydantic import Field, ValidationError

from zenml import __version__
from zenml.services import (
    BaseService,
    ServiceConfig,
    ServiceState,
    ServiceStatus,
    ServiceType,
)
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.integrations.kserve.model_deployers.kserve_model_deployer import (  # noqa
        KServeModelDeployer,
    )

logger = get_logger(__name__)

class KServeDeploymentConfig(ServiceConfig):
    """KServe deployment service configuration.

    Attributes:
        model_uri: URI of the model (or models) to serve.
        model_name: the name of the model. Multiple versions of the same model
            should use the same model name.
        predictor: the KServe predictor used to serve the model.
        replicas: number of replicas to use for the prediction service.
        resources: the Kubernetes resources to allocate for the prediction service.
    """

    model_uri: str = ""
    model_name: str = "default"
    predictor: str
    replicas: int = 1
    resources: Dict[str, Any]

    @staticmethod
    def sanitize_labels(labels: Dict[str, str]) -> None:
        """Update the label values to be valid Kubernetes labels.

        See: https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#syntax-and-character-set
        """
        # TODO[MEDIUM]: Move k8s label sanitization to a common module.
        for key, value in labels.items():
            # Kubernetes labels must be alphanumeric, no longer than
            # 63 characters, and must begin and end with an alphanumeric
            # character ([a-z0-9A-Z])
            labels[key] = re.sub(r"[^0-9a-zA-Z-_\.]+", "_", value)[:63].strip(
                "-_."
            )

    def get_kubernetes_labels(self) -> Dict[str, str]:
        """Generate the labels for the KServe inference service CRD from the
        service configuration.

        These labels are attached to the KServe inference service CRD
        and may be used as label selectors in lookup operations.

        Returns:
            The labels for the KServe inference service CRD.
        """
        # The convention used to differentiate between KServe CRD instances
        # that are managed by ZenML and those that are not is to set the `app`
        # label value to `zenml`.
        labels = {"app": "zenml"}
        if self.pipeline_name:
            labels["zenml.pipeline_name"] = self.pipeline_name
        if self.pipeline_run_id:
            labels["zenml.pipeline_run_id"] = self.pipeline_run_id
        if self.pipeline_step_name:
            labels["zenml.pipeline_step_name"] = self.pipeline_step_name
        if self.model_name:
            labels["zenml.model_name"] = self.model_name
        if self.model_uri:
            labels["zenml.model_uri"] = self.model_uri
        if self.predictor:
            labels["zenml.model_type"] = self.predictor
        self.sanitize_labels(labels)
        return labels

    def get_kubernetes_annotations(self) -> Dict[str, str]:
        """Generate the annotations for the KServe inference service CRD from
        the service configuration.

        The annotations are used to store additional information about the
        KServe ZenML service associated with the deployment that is
        not available in the labels. One annotation particularly important
        is the serialized Service configuration itself, which is used to
        recreate the service configuration from a remote KServe inference
        service CRD.

        Returns:
            The annotations for the KServe inference service CRD.
        """
        annotations = {
            "zenml.service_config": self.json(),
            "zenml.version": __version__,
        }
        return annotations

    @classmethod
    def create_from_deployment(
        cls, deployment: V1beta1InferenceService
    ) -> "KServeDeploymentConfig":
        """Recreate the configuration of a KServe ZenML Service from a deployed
        KServe inference service instance.

        Args:
            deployment: the KServe inference service CRD.

        Returns:
            The KServe ZenML service configuration corresponding to the given
            KServe inference service CRD.

        Raises:
            ValueError: if the given deployment resource does not contain
                the expected annotations or it contains an invalid or
                incompatible KServe ZenML service configuration.
        """
        config_data = deployment.metadata.annotations.get(
            "zenml.service_config"
        )
        if not config_data:
            raise ValueError(
                f"The given deployment resource does not contain a "
                f"'zenml.service_config' annotation: {deployment}"
            )
        try:
            service_config = cls.parse_raw(config_data)
        except ValidationError as e:
            raise ValueError(
                f"The loaded KServe Inference Service resource contains an "
                f"invalid or incompatible KServe ZenML service configuration: "
                f"{config_data}"
            ) from e
        return service_config


class KServeDeploymentService(BaseService):
    """A ZenML service that represents a KServe inference service CRD.

    Attributes:
        config: service configuration.
        status: service status.
    """

    SERVICE_TYPE = ServiceType(
        name="kserve-deployment",
        type="model-serving",
        flavor="kserve",
        description="KServe inference service",
    )

    config: KServeDeploymentConfig = Field(
        default_factory=KServeDeploymentConfig
    )
    status: ServiceStatus = Field(default_factory=ServiceStatus)

    def _get_model_deployer(self) -> "KServeModelDeployer":
        """Get the active KServe model deployer.

        Returns:
            The active KServeModelDeployer.

        Raises:
            TypeError: if a KServe model deployer is not present in the
            active stack.
        """
        from zenml.integrations.kserve.model_deployers.kserve_model_deployer import (
            KServeModelDeployer,
        )

        return KServeModelDeployer.get_active_model_deployer()

    def _get_client(self) -> KServeClient:
        """Get the KServe client from the active KServe model deployer.

        Returns:
            The KServe client.
        """
        return self._get_model_deployer().kserve_client

    def _get_namespace(self) -> Optional[str]:
        """Get the Kubernetes namespace from the active KServe model deployer.

        Returns:
            The Kubernetes namespace, or None, if the default namespace is
            used.
        """
        return self._get_model_deployer().kubernetes_namespace

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the the current operational state of the external KServe
        inference service and translate it into a `ServiceState` value and
        a printable message.

        This method should be overridden by subclasses that implement
        concrete service tracking functionality.

        Returns:
            The operational state of the external service and a message
            providing additional information about that state (e.g. a
            description of the error if one is encountered while checking the
            service status).
        """
        client = self._get_client()
        namespace = self._get_namespace()

        name = self.crd_name
        try:
            deployment = client.get(name=name, namespace=namespace)
        except RuntimeError:
            return (ServiceState.INACTIVE, "")

        # TODO[HIGH]: Implement better operational status checking that also
        #   cover errors
        if "status" not in deployment:
            return (ServiceState.INACTIVE, "No operational status available")
        status = "Unknown"
        for condition in deployment["status"].get("conditions", {}):
            if condition.get("type", "") == "Ready":
                status = condition.get("status", "Unknown")
                if status.lower() == "true":
                    return (
                        ServiceState.ACTIVE,
                        f"Inference service '{name}' is available",
                    )
        return (
            ServiceState.PENDING_STARTUP,
            f"Inference service '{name}' still starting up",
        )

    @property
    def crd_name(self) -> str:
        """Get the name of the KServe inference service CRD that uniquely
        corresponds to this service instance

        Returns:
            The name of the KServe inference service CRD.
        """
        return f"zenml-{str(self.uuid)[:8]}"

    def _get_kubernetes_labels(self) -> Dict[str, str]:
        """Generate the labels for the KServe inference service CRD from the
        service configuration.

        Returns:
            The labels for the KServe inference service.
        """
        labels = self.config.get_kubernetes_labels()
        labels["zenml.service_uuid"] = str(self.uuid)
        KServeDeploymentConfig.sanitize_labels(labels)
        return labels

    @classmethod
    def create_from_deployment(
        cls, deployment: V1beta1InferenceService
    ) -> "KServeDeploymentService":
        config = KServeDeploymentConfig.create_from_deployment(deployment)
        uuid = deployment.metadata.labels.get("zenml.service_uuid")
        if not uuid:
            raise ValueError(
                f"The given deployment resource does not contain a valid "
                f"'zenml.service_uuid' label: {deployment}"
            )
        service = cls(uuid=UUID(uuid), config=config)
        service.update_status()
        return service

    def provision(self) -> None:

        client = self._get_client()
        namespace = self._get_namespace()

        api_version = constants.KSERVE_GROUP + "/" + "v1beta1"
        name = self.crd_name

        # All supported model specs seem to have the same fields
        # so we can use any one of them (see https://kserve.github.io/website/0.8/reference/api/#serving.kserve.io/v1beta1.PredictorExtensionSpec)
        predictor_kwargs = {
            self.config.predictor: V1beta1PredictorExtensionSpec(
                storage_uri=self.config.model_uri,
                resources=self.config.resources,
            )
        }

        isvc = V1beta1InferenceService(
            api_version=api_version,
            kind=constants.KSERVE_KIND,
            metadata=k8s_client.V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=self._get_kubernetes_labels(),
                annotations=self.config.get_kubernetes_annotations(),
            ),
            spec=V1beta1InferenceServiceSpec(
                predictor=V1beta1PredictorSpec(**predictor_kwargs)
            ),
        )

        # TODO[HIGH]: better error handling when provisioning KServe instances
        try:
            client.get(name=name, namespace=namespace)
            # update the existing deployment
            client.replace(name, isvc, namespace=namespace)
        except RuntimeError:
            client.create(isvc)

    def deprovision(self, force: bool = False) -> None:
        """Deprovisions all resources used by the service."""
        client = self._get_client()
        namespace = self._get_namespace()
        name = self.crd_name

        # TODO[HIGH]: catch errors if deleting a KServe instance that is no
        #   longer available
        try:
            client.delete(name=name, namespace=namespace)
        except RuntimeError:
            raise ValueError(
                f"Could not delete KServe instance '{name}' from namespace "
                f"'{namespace}'"
            )

    def _get_deployment_logs(
        self,
        name: str,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get the logs of a Seldon Core deployment resource.

        Args:
            name: the name of the Seldon Core deployment to get logs for.
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that can be acccessed to get the service logs.

        Raises:
            Exception: if an unknown error occurs while fetching
                the logs.
        """
        logger.debug(f"Retrieving logs for InferenceService resource: {name}")
        try:
            response = self._core_api.list_namespaced_pod(
                namespace=self._namespace,
                label_selector=f"kserve-deployment-id={name}",
            )
            logger.debug("Kubernetes API response: %s", response)
            pods = response.items
            if not pods:
                raise Exception(
                    f"The KServe deployment {name} is not currently "
                    f"running: no Kubernetes pods associated with it were found"
                )
            pod = pods[0]
            pod_name = pod.metadata.name

            containers = [c.name for c in pod.spec.containers]
            init_containers = [c.name for c in pod.spec.init_containers]
            container_statuses = {
                c.name: c.started or c.restart_count
                for c in pod.status.container_statuses
            }

            container = "default"
            if container not in containers:
                container = containers[0]
            # some containers might not be running yet and have no logs to show,
            # so we need to filter them out
            if not container_statuses[container]:
                container = init_containers[0]

            logger.info(
                f"Retrieving logs for pod: `{pod_name}` and container "
                f"`{container}` in namespace `{self._namespace}`"
            )
            response = self._core_api.read_namespaced_pod_log(
                name=pod_name,
                namespace=self._namespace,
                container=container,
                follow=follow,
                tail_lines=tail,
                _preload_content=False,
            )
        except k8s_client.rest.ApiException as e:
            logger.error(
                "Exception when fetching logs for InferenceService resource "
                "%s: %s",
                name,
                str(e),
            )
            raise Exception(
                f"Unexpected exception when fetching logs for InferenceService "
                f"resource: {name}"
            ) from e

        try:
            while True:
                line = response.readline().decode("utf-8").rstrip("\n")
                if not line:
                    return
                stop = yield line
                if stop:
                    return
        finally:
            response.release_conn()


    def get_logs(
        self, follow: bool = False, tail: Optional[int] = None
    ) -> Generator[str, bool, None]:
        """Retrieve the logs from the remote KServe inference service instance.

        Args:
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that can be accessed to get the service logs.
        """

        return self._get_deployment_logs(
            self.crd_name,
            follow=follow,
            tail=tail,
        )
        # TODO[HIGH]: Implement KServe log retrieval

    @property
    def prediction_url(self) -> Optional[str]:
        """The prediction URI exposed by the prediction service.

        Returns:
            The prediction URI exposed by the prediction service, or None if
            the service is not yet ready.
        """
        if not self.is_running:
            return None

        # TODO[HIGH]: return correct KServe prediction URLs
        model_deployer = self._get_model_deployer()
        return os.path.join(
            model_deployer.base_url,
            model_deployer.kubernetes_namespace or "",
            self.crd_name,
            "api/v0.1/predictions",
        )
