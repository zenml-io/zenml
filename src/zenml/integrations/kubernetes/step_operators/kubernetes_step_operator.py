

from typing import Any, Dict, List, Optional, Tuple, Type, cast

from kubernetes import client as k8s_client

from zenml.client import Client
from zenml.config.base_settings import BaseSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.config.step_run_info import StepRunInfo
from zenml.enums import StackComponentType
from zenml.integrations.kubernetes.flavors.kubernetes_step_operator import KubernetesStepOperatorConfig, KubernetesStepOperatorSettings
from zenml.integrations.kubernetes.orchestrators import kube_utils
from zenml.integrations.kubernetes.orchestrators.manifest_utils import build_pod_manifest
from zenml.logger import get_logger
from zenml.models.v2.core.pipeline_deployment import PipelineDeploymentBase
from zenml.stack.stack import Stack
from zenml.stack.stack_validator import StackValidator
from zenml.step_operators.base_step_operator import BaseStepOperator

logger = get_logger(__name__)

KUBERNETES_STEP_OPERATOR_DOCKER_IMAGE_KEY = "kubernetes_step_operator_docker_image"

class KubernetesStepOperator(BaseStepOperator):
    """Base class for all ZenML step operators."""

    _k8s_client: Optional[k8s_client.ApiClient] = None

    def get_kube_client(
        self, incluster: Optional[bool] = None
    ) -> k8s_client.ApiClient:
        """Getter for the Kubernetes API client.

        Args:
            incluster: Whether to use the in-cluster config or not. Overrides
                the `incluster` setting in the config.

        Returns:
            The Kubernetes API client.

        Raises:
            RuntimeError: if the Kubernetes connector behaves unexpectedly.
        """
        if incluster is None:
            incluster = self.config.incluster

        if incluster:
            kube_utils.load_kube_config(
                incluster=incluster,
                context=self.config.kubernetes_context,
            )
            self._k8s_client = k8s_client.ApiClient()
            return self._k8s_client

        # Refresh the client also if the connector has expired
        if self._k8s_client and not self.connector_has_expired():
            return self._k8s_client

        connector = self.get_connector()
        if connector:
            client = connector.connect()
            if not isinstance(client, k8s_client.ApiClient):
                raise RuntimeError(
                    f"Expected a k8s_client.ApiClient while trying to use the "
                    f"linked connector, but got {type(client)}."
                )
            self._k8s_client = client
        else:
            kube_utils.load_kube_config(
                incluster=incluster,
                context=self.config.kubernetes_context,
            )
            self._k8s_client = k8s_client.ApiClient()

        return self._k8s_client

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the step operator and validates the accelerator type.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)

    @property
    def config(self) -> KubernetesStepOperatorConfig:
        """Returns the `VertexStepOperatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(KubernetesStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Vertex step operator.

        Returns:
            The settings class.
        """
        return KubernetesStepOperatorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack.

        Returns:
            A validator that checks that the stack contains a remote container
            registry and a remote artifact store.
        """

        def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The Kubernetes step operator runs code remotely and "
                    "needs to write files into the artifact store, but the "
                    f"artifact store `{stack.artifact_store.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote artifact store when using the Vertex "
                    "step operator."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The Kubernetes step operator runs code remotely and "
                    "needs to push/pull Docker images, but the "
                    f"container registry `{container_registry.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote container registry when using the "
                    "Kuebrnetes step operator."
                )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_remote_components,
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
            if step.config.step_operator == self.name:
                build = BuildConfiguration(
                    key=KUBERNETES_STEP_OPERATOR_DOCKER_IMAGE_KEY,
                    settings=step.config.docker_settings,
                    step_name=step_name,
                )
                builds.append(build)

        return builds

    def launch(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Launches a step on VertexAI.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables to set in the step operator
                environment.

        Raises:
            RuntimeError: If the run fails.
        """
        resource_settings = info.config.resource_settings
        if resource_settings.cpu_count or resource_settings.memory:
            logger.warning(
                "Specifying cpus or memory is not supported for "
                "the Vertex step operator. If you want to run this step "
                "operator on specific resources, you can do so by configuring "
                "a different machine_type type like this: "
                "`zenml step-operator update %s "
                "--machine_type=<MACHINE_TYPE>`",
                self.name,
            )
        settings = cast(KubernetesStepOperatorSettings, self.get_settings(info))

        image_name = info.get_image(key=KUBERNETES_STEP_OPERATOR_DOCKER_IMAGE_KEY)

        pod_name = f"{info.run_name}-{info.pipeline_step_name}"

        active_stack = Client().active_stack
        mount_local_stores = active_stack.step_operator.config.is_local

        # Define Kubernetes pod manifest.
        pod_manifest = build_pod_manifest(
            pod_name=pod_name,
            run_name=info.run_name,
            pipeline_name=info.pipeline.name,
            image_name=image_name,
            command=entrypoint_command,
            args=[],
            env=environment,
            privileged=settings.privileged,
            pod_settings=settings.pod_settings,
            service_account_name=settings.step_pod_service_account_name
            or settings.service_account_name,
            mount_local_stores=mount_local_stores,
        )


        kube_client = self.get_kube_client(incluster=self.config.incluster)
        core_api = k8s_client.CoreV1Api(kube_client)

        # Create and run pod.
        core_api.create_namespaced_pod(
            namespace=self.config.kubernetes_namespace,
            body=pod_manifest,
        )

        # Wait for pod to finish.
        logger.info(f"Waiting for pod of step `{info.pipeline_step_name}` to start...")
        kube_utils.wait_pod(
            kube_client_fn=lambda: self.get_kube_client(
                incluster=True
            ),
            pod_name=pod_name,
            namespace=self.config.kubernetes_namespace,
            exit_condition_lambda=kube_utils.pod_is_done,
            stream_logs=True,
        )
        logger.info(f"Pod of step `{info.pipeline_step_name}` completed.")
