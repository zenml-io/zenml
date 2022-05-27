import re

from typing import Any, Dict, Generator, Optional, Tuple
from uuid import UUID
from pydantic import Field, ValidationError
from zenml.services import (
    BaseService,
    ServiceState,
    ServiceType,
    ServiceConfig,
    ServiceStatus,
)
from zenml import __version__

from kubernetes import client as k8s_client
from kserve import (
    KServeClient,
    constants,
    utils,
    V1beta1InferenceService,
    V1beta1InferenceServiceSpec,
    V1beta1PredictorSpec,
    V1beta1TFServingSpec,
    V1beta1ModelSpec,
)


class KServeDeploymentConfig(ServiceConfig):
    """ """

    model_uri: str = ""
    model_name: str = "default"
    predictor: str
    resources: Dict[str, Any]

    @staticmethod
    def sanitize_labels(labels: Dict[str, str]) -> None:
        """Update the label values to be valid Kubernetes labels.

        See: https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#syntax-and-character-set
        """
        for key, value in labels.items():
            # Kubernetes labels must be alphanumeric, no longer than
            # 63 characters, and must begin and end with an alphanumeric
            # character ([a-z0-9A-Z])
            labels[key] = re.sub(r"[^0-9a-zA-Z-_\.]+", "_", value)[:63].strip(
                "-_."
            )

    def get_kubernetes_labels(self) -> Dict[str, str]:
        labels = {}
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
        annotations = {
            "zenml.service_config": self.json(),
            "zenml.version": __version__,
        }
        return annotations

    @classmethod
    def create_from_deployment(
        cls, deployment: V1beta1InferenceService
    ) -> "KServeDeploymentConfig":
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
                f"invalid or incompatible ZenML service configuration: "
                f"{config_data}"
            ) from e
        return service_config


class KServeDeploymentService(BaseService):

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

    @property
    def model_deployer(self) -> "KServeModelDeployer":
        from kserve_deployment.model_deployer import (
            KServeModelDeployer,
        )

        return KServeModelDeployer.get_active_model_deployer()

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the the current operational state of the external service.

        This method should be overridden by subclasses that implement
        concrete service tracking functionality.

        Returns:
            The operational state of the external service and a message
            providing additional information about that state (e.g. a
            description of the error if one is encountered while checking the
            service status).
        """
        model_deployer = self.model_deployer

        client = KServeClient(context=model_deployer.kubernetes_context)
        name = self.crd_name
        try:
            deployment = client.get(
                name=name, namespace=model_deployer.kubernetes_namespace
            )
        except RuntimeError:
            return (ServiceState.INACTIVE, "")

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

    def get_logs(
        self, follow: bool = False, tail: Optional[int] = None
    ) -> Generator[str, bool, None]:
        """Retrieve the service logs.

        This method should be overridden by subclasses that implement
        concrete service tracking functionality.

        Args:
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that can be acccessed to get the service logs.
        """

    @property
    def crd_name(self) -> str:
        return f"zenml-{str(self.uuid)[:8]}"

    def _get_kubernetes_labels(self) -> Dict[str, str]:
        labels = self.config.get_kubernetes_labels()
        labels["zenml.service_uuid"] = str(self.uuid)
        KServeDeploymentConfig.sanitize_labels(labels)
        return labels

    def provision(self) -> None:

        model_deployer = self.model_deployer

        api_version = constants.KSERVE_GROUP + "/" + "v1beta1"

        name = self.crd_name

        isvc = V1beta1InferenceService(
            api_version=api_version,
            kind=constants.KSERVE_KIND,
            metadata=k8s_client.V1ObjectMeta(
                name=name,
                namespace=model_deployer.kubernetes_namespace,
                labels=self._get_kubernetes_labels(),
                annotations=self.config.get_kubernetes_annotations(),
            ),
            spec=V1beta1InferenceServiceSpec(
                predictor=V1beta1PredictorSpec(
                    # TODO: use the configuration predictor attr
                    tensorflow=(
                        V1beta1TFServingSpec(
                            storage_uri=self.config.model_uri,
                            resources=self.config.resources,
                        )
                    ),
                ),
            ),
        )

        client = KServeClient(context=model_deployer.kubernetes_context)

        try:
            client.get(name=name, namespace=model_deployer.kubernetes_namespace)
            # update the existing deployment
            client.replace(
                name, isvc, namespace=model_deployer.kubernetes_namespace
            )
        except RuntimeError:
            client.create(isvc)

    def deprovision(self, force: bool = False) -> None:
        """Deprovisions all resources used by the service."""
        model_deployer = self.model_deployer

        name = self.crd_name
        client = KServeClient(context=model_deployer.kubernetes_context)
        client.delete(name=name, namespace=model_deployer.kubernetes_namespace)

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
