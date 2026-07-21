#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Implementation of the vLLM Kubernetes Inference Server Service."""

import os
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    List,
    Optional,
    Tuple,
    cast,
)

from kubernetes import client as k8s_client
from pydantic import Field

from zenml.enums import KubernetesServiceType, ServiceState
from zenml.integrations.kubernetes import kube_utils
from zenml.integrations.kubernetes.k8s_applier import ResourceInventoryItem
from zenml.integrations.kubernetes.manifest_utils import add_pod_settings
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.integrations.kubernetes.serialization_utils import (
    normalize_resource_to_dict,
)
from zenml.integrations.vllm.flavors.vllm_kubernetes_model_deployer_flavor import (
    DEFAULT_VLLM_IMAGE,
)
from zenml.integrations.vllm.services.vllm_deployment import (
    VLLM_HEALTHCHECK_URL_PATH,
    VLLM_PREDICTION_URL_PATH,
    VLLMEngineArgs,
)
from zenml.logger import get_logger
from zenml.models.v2.misc.service import ServiceType
from zenml.services.service import BaseDeploymentService, ServiceConfig
from zenml.services.service_status import ServiceStatus

if TYPE_CHECKING:
    from zenml.integrations.vllm.model_deployers.vllm_kubernetes_model_deployer import (
        KubernetesVLLMModelDeployer,
    )

logger = get_logger(__name__)


VLLM_FIELD_MANAGER = "zenml-vllm-deployer"
VLLM_CONTAINER_NAME = "vllm"
VLLM_HF_TOKEN_ENV_VAR = "HF_TOKEN"
VLLM_HF_TOKEN_SECRET_KEY = "token"
VLLM_HEALTH_PROBE_PATH = f"/{VLLM_HEALTHCHECK_URL_PATH}"
SHM_VOLUME_NAME = "shm"
SHM_VOLUME_MOUNT_PATH = "/dev/shm"
POD_FAILURE_REASONS = {"CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"}


def _build_container_args(
    engine_args: VLLMEngineArgs,
    port: int,
    extra_serve_args: List[str],
) -> List[str]:
    """Build vLLM OpenAI server CLI args from engine arguments.

    Args:
        engine_args: vLLM engine arguments.
        port: Port the server listens on inside the container.
        extra_serve_args: Additional CLI args appended verbatim.

    Returns:
        CLI args for the vLLM OpenAI API server entrypoint.
    """
    args = [
        "--model",
        engine_args.model,
        "--port",
        str(port),
        "--host",
        "0.0.0.0",
    ]
    if engine_args.tokenizer:
        args += ["--tokenizer", engine_args.tokenizer]
    if engine_args.served_model_name:
        served_model_names = (
            engine_args.served_model_name
            if isinstance(engine_args.served_model_name, list)
            else [engine_args.served_model_name]
        )
        args += ["--served-model-name", *served_model_names]
    if engine_args.trust_remote_code:
        args.append("--trust-remote-code")
    if engine_args.tokenizer_mode:
        args += ["--tokenizer-mode", engine_args.tokenizer_mode]
    if engine_args.dtype:
        args += ["--dtype", engine_args.dtype]
    if engine_args.revision:
        args += ["--revision", engine_args.revision]
    args += extra_serve_args
    return args


def _build_probe(
    port: int,
    initial_delay_seconds: int,
    period_seconds: int,
    timeout_seconds: int,
    failure_threshold: int,
) -> k8s_client.V1Probe:
    """Build an HTTP GET probe against the vLLM health endpoint.

    Args:
        port: Port the health endpoint listens on.
        initial_delay_seconds: Delay before the first probe.
        period_seconds: Interval between probes.
        timeout_seconds: Timeout for each probe.
        failure_threshold: Consecutive failures before the probe fails.

    Returns:
        The configured probe.
    """
    return k8s_client.V1Probe(
        http_get=k8s_client.V1HTTPGetAction(
            path=VLLM_HEALTH_PROBE_PATH, port=port
        ),
        initial_delay_seconds=initial_delay_seconds,
        period_seconds=period_seconds,
        timeout_seconds=timeout_seconds,
        failure_threshold=failure_threshold,
    )


def _resources_with_mirrored_gpu_requests(
    resources: Dict[str, Dict[str, str]],
) -> Dict[str, Dict[str, str]]:
    """Mirror a configured GPU limit into the resource requests.

    Kubernetes requires requests to equal limits for extended resources
    like `nvidia.com/gpu`, so a config that only sets a GPU limit would
    otherwise leave the pod unschedulable.

    Args:
        resources: Native Kubernetes resource requests and limits.

    Returns:
        The resources with the GPU limit mirrored into requests.
    """
    gpu_limit = resources.get("limits", {}).get("nvidia.com/gpu")
    if not gpu_limit:
        return resources

    requests = dict(resources.get("requests", {}))
    requests.setdefault("nvidia.com/gpu", gpu_limit)
    merged = dict(resources)
    merged["requests"] = requests
    return merged


def _pod_container_name(pod: k8s_client.V1Pod) -> str:
    """Name of a pod's primary container, or the default vLLM container name.

    Args:
        pod: Pod to inspect.

    Returns:
        The container name.
    """
    return (
        pod.spec.containers[0].name
        if pod.spec and pod.spec.containers
        else VLLM_CONTAINER_NAME
    )


def build_vllm_deployment_manifest(
    name: str,
    namespace: str,
    image: str,
    replicas: int,
    port: int,
    engine_args: VLLMEngineArgs,
    extra_serve_args: List[str],
    labels: Dict[str, str],
    resources: Dict[str, Dict[str, str]],
    shm_size: Optional[str],
    env: Dict[str, str],
    hf_secret_name: Optional[str],
    pod_settings: Optional[KubernetesPodSettings],
) -> Dict[str, Any]:
    """Build the manifest for the vLLM Deployment.

    Args:
        name: Name of the Deployment.
        namespace: Namespace to deploy into.
        image: Container image to run.
        replicas: Number of pod replicas.
        port: Port the vLLM server listens on.
        engine_args: vLLM engine arguments used to build the container args.
        extra_serve_args: Additional CLI args appended to the container args.
        labels: Labels applied to the Deployment and its pod template.
        resources: Native Kubernetes resource requests and limits.
        shm_size: Size limit of the `/dev/shm` volume. No volume is added
            if unset.
        env: Environment variables set on the container.
        hf_secret_name: Name of the secret holding the Hugging Face token.
            No `HF_TOKEN` variable is added if unset.
        pod_settings: Additional pod configuration merged into the pod spec.

    Returns:
        The Deployment manifest.
    """
    env_vars = [
        k8s_client.V1EnvVar(name=key, value=value)
        for key, value in env.items()
    ]
    if hf_secret_name:
        env_vars.append(
            k8s_client.V1EnvVar(
                name=VLLM_HF_TOKEN_ENV_VAR,
                value_from=k8s_client.V1EnvVarSource(
                    secret_key_ref=k8s_client.V1SecretKeySelector(
                        name=hf_secret_name,
                        key=VLLM_HF_TOKEN_SECRET_KEY,
                    )
                ),
            )
        )

    volumes = []
    volume_mounts = []
    if shm_size:
        volumes.append(
            k8s_client.V1Volume(
                name=SHM_VOLUME_NAME,
                empty_dir=k8s_client.V1EmptyDirVolumeSource(
                    medium="Memory", size_limit=shm_size
                ),
            )
        )
        volume_mounts.append(
            k8s_client.V1VolumeMount(
                name=SHM_VOLUME_NAME, mount_path=SHM_VOLUME_MOUNT_PATH
            )
        )

    container = k8s_client.V1Container(
        name=VLLM_CONTAINER_NAME,
        image=image,
        args=_build_container_args(
            engine_args=engine_args,
            port=port,
            extra_serve_args=extra_serve_args,
        ),
        ports=[k8s_client.V1ContainerPort(container_port=port)],
        env=env_vars,
        volume_mounts=volume_mounts,
        readiness_probe=_build_probe(
            port=port,
            initial_delay_seconds=10,
            period_seconds=10,
            timeout_seconds=5,
            failure_threshold=60,
        ),
        liveness_probe=_build_probe(
            port=port,
            initial_delay_seconds=600,
            period_seconds=10,
            timeout_seconds=5,
            failure_threshold=3,
        ),
    )

    pod_labels = dict(labels)
    pod_metadata = k8s_client.V1ObjectMeta(labels=pod_labels)
    pod_spec = k8s_client.V1PodSpec(containers=[container], volumes=volumes)

    merged_resources = dict(resources)
    if pod_settings:
        # The service config's resources take precedence over
        # `pod_settings.resources` per top-level key. The merged result,
        # with GPU limits mirrored into requests, is applied to the
        # container once below, after `add_pod_settings` has applied the
        # rest of the pod settings.
        for key in ("requests", "limits"):
            if pod_settings.resources.get(key):
                merged_resources[key] = {
                    **merged_resources.get(key, {}),
                    **pod_settings.resources[key],
                }

        add_pod_settings(
            pod_spec=pod_spec,
            settings=pod_settings,
            substitutions={"{{ image }}": image},
        )
        if pod_settings.labels:
            pod_labels.update(pod_settings.labels)
        if pod_settings.annotations:
            pod_metadata.annotations = pod_settings.annotations

    mirrored_resources = _resources_with_mirrored_gpu_requests(
        merged_resources
    )
    if mirrored_resources:
        container.resources = k8s_client.V1ResourceRequirements(
            requests=mirrored_resources.get("requests"),
            limits=mirrored_resources.get("limits"),
        )

    deployment = k8s_client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=k8s_client.V1ObjectMeta(
            name=name, namespace=namespace, labels=labels
        ),
        spec=k8s_client.V1DeploymentSpec(
            replicas=replicas,
            selector=k8s_client.V1LabelSelector(match_labels=labels),
            template=k8s_client.V1PodTemplateSpec(
                metadata=pod_metadata, spec=pod_spec
            ),
        ),
    )

    return cast(
        Dict[str, Any],
        k8s_client.ApiClient().sanitize_for_serialization(deployment),
    )


def build_vllm_service_manifest(
    name: str,
    namespace: str,
    port: int,
    service_type: KubernetesServiceType,
    selector_labels: Dict[str, str],
    labels: Dict[str, str],
) -> Dict[str, Any]:
    """Build the manifest for the vLLM Service.

    Args:
        name: Name of the Service.
        namespace: Namespace to deploy into.
        port: Port exposed by the Service and forwarded to the pod.
        service_type: Kubernetes Service type.
        selector_labels: Labels used to select the target pods.
        labels: Labels applied to the Service itself.

    Returns:
        The Service manifest.
    """
    service = k8s_client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=k8s_client.V1ObjectMeta(
            name=name, namespace=namespace, labels=labels
        ),
        spec=k8s_client.V1ServiceSpec(
            type=service_type,
            selector=selector_labels,
            ports=[k8s_client.V1ServicePort(port=port, target_port=port)],
        ),
    )
    return cast(
        Dict[str, Any],
        k8s_client.ApiClient().sanitize_for_serialization(service),
    )


class VLLMKubernetesServiceConfig(VLLMEngineArgs, ServiceConfig):
    """vLLM Kubernetes service configuration.

    Attributes:
        namespace: Kubernetes namespace to deploy into. Resolved from the
            deployer configuration when unset.
        image: Container image running the vLLM OpenAI server. Resolved
            from the deployer configuration when unset.
        port: Port the vLLM OpenAI server listens on inside the container,
            and the port exposed by the Service.
        service_type: Type of Kubernetes Service used to expose the vLLM
            server. Resolved from the deployer configuration when unset.
        replicas: Number of pod replicas for the Deployment.
        resources: Native Kubernetes resource requests and limits for the
            container. GPU limits are mirrored into requests automatically,
            since Kubernetes requires the two to match for extended
            resources.
        pod_settings: Additional pod configuration merged into the
            generated pod spec, for volumes, affinity, tolerations, and
            other settings not modeled as dedicated fields.
        hf_token: Hugging Face access token injected into the container as
            `HF_TOKEN` through a managed secret.
        existing_hf_secret: Name of an existing Kubernetes secret to use
            instead of `hf_token`. Must contain the token under a `token`
            key.
        env: Additional environment variables set on the vLLM container.
        extra_serve_args: Additional CLI args appended to the vLLM OpenAI
            server args, for engine options not modeled as dedicated
            fields.
        shm_size: Size limit of the `/dev/shm` volume mounted into the
            container. No volume is mounted if unset.
    """

    namespace: Optional[str] = Field(
        default=None,
        description="Kubernetes namespace to deploy into.",
    )
    image: Optional[str] = Field(
        default=None,
        description="Container image running the vLLM OpenAI server.",
    )
    port: int = Field(
        default=8000,
        description="Port the vLLM OpenAI server listens on.",
    )
    service_type: Optional[KubernetesServiceType] = Field(
        default=None,
        description="Type of Kubernetes Service used to expose the vLLM server.",
    )
    replicas: int = Field(
        default=1,
        description="Number of pod replicas for the Deployment.",
    )
    resources: Dict[str, Dict[str, str]] = Field(
        default_factory=dict,
        description="Native Kubernetes resource requests and limits for the container.",
    )
    pod_settings: Optional[KubernetesPodSettings] = Field(
        default=None,
        description="Additional pod configuration merged into the generated pod spec.",
    )
    hf_token: Optional[str] = Field(
        default=None,
        description="Hugging Face access token injected into the container through a managed secret.",
    )
    existing_hf_secret: Optional[str] = Field(
        default=None,
        description="Name of an existing Kubernetes secret to use instead of `hf_token`.",
    )
    env: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional environment variables set on the vLLM container.",
    )
    extra_serve_args: List[str] = Field(
        default_factory=list,
        description="Additional CLI args appended to the vLLM OpenAI server args.",
    )
    shm_size: Optional[str] = Field(
        default="2Gi",
        description="Size limit of the `/dev/shm` volume mounted into the container.",
    )


class VLLMKubernetesServiceStatus(ServiceStatus):
    """vLLM Kubernetes service status."""


class VLLMKubernetesDeploymentService(BaseDeploymentService):
    """A service that represents a vLLM inference server running on Kubernetes.

    Attributes:
        config: service configuration.
        status: service status.
    """

    SERVICE_TYPE = ServiceType(
        name="vllm-kubernetes-deployment",
        type="model-serving",
        flavor="vllm-kubernetes",
        description="vLLM Inference prediction service running on Kubernetes",
    )

    config: VLLMKubernetesServiceConfig
    status: VLLMKubernetesServiceStatus = Field(
        default_factory=lambda: VLLMKubernetesServiceStatus()
    )

    def _get_deployer(self) -> "KubernetesVLLMModelDeployer":
        """Get the active Kubernetes vLLM model deployer.

        Returns:
            The active Kubernetes vLLM model deployer.
        """
        from zenml.integrations.vllm.model_deployers.vllm_kubernetes_model_deployer import (
            KubernetesVLLMModelDeployer,
        )

        return cast(
            "KubernetesVLLMModelDeployer",
            KubernetesVLLMModelDeployer.get_active_model_deployer(),
        )

    @property
    def namespace(self) -> str:
        """Kubernetes namespace this service is deployed to.

        Returns:
            The configured namespace, or the deployer's configured
            `kubernetes_namespace` if unset.
        """
        return (
            self.config.namespace
            or self._get_deployer().config.kubernetes_namespace
        )

    @property
    def image(self) -> str:
        """Container image running the vLLM OpenAI server.

        Returns:
            The configured image, the deployer's configured `default_image`
            if unset, or `DEFAULT_VLLM_IMAGE` if no deployer is resolvable.
        """
        if self.config.image:
            return self.config.image
        try:
            return self._get_deployer().config.default_image
        except TypeError:
            return DEFAULT_VLLM_IMAGE

    @property
    def service_type(self) -> KubernetesServiceType:
        """Kubernetes Service type used to expose the vLLM server.

        Returns:
            The configured Service type, the deployer's configured
            `default_service_type` if unset, or
            `KubernetesServiceType.CLUSTER_IP` if no deployer is resolvable.
        """
        if self.config.service_type:
            return self.config.service_type
        try:
            return self._get_deployer().config.default_service_type
        except TypeError:
            return KubernetesServiceType.CLUSTER_IP

    @property
    def deployment_name(self) -> str:
        """Name of the Kubernetes Deployment for this service.

        Returns:
            The sanitized Deployment name.
        """
        return kube_utils.sanitize_label(f"vllm-{self.uuid}")

    @property
    def service_name(self) -> str:
        """Name of the Kubernetes Service for this service.

        Returns:
            The sanitized Service name.
        """
        return self.deployment_name

    @property
    def hf_secret_name(self) -> str:
        """Name of the managed secret holding the Hugging Face token.

        Returns:
            The sanitized secret name.
        """
        return kube_utils.sanitize_label(f"vllm-hf-{self.uuid}")

    @property
    def _labels(self) -> Dict[str, str]:
        """Labels identifying the Kubernetes resources owned by this service.

        Returns:
            The label dictionary.
        """
        return {
            "managed-by": "zenml",
            "zenml-service-uuid": str(self.uuid),
        }

    def _resolve_hf_secret_name(self) -> Optional[str]:
        """Resolve the name of the secret holding the Hugging Face token.

        Returns:
            The secret name, or `None` if neither `hf_token` nor
            `existing_hf_secret` is configured.
        """
        if self.config.hf_token:
            return self.hf_secret_name
        return self.config.existing_hf_secret

    def provision(self) -> None:
        """Provision or update the vLLM Kubernetes Deployment and Service."""
        deployer = self._get_deployer()
        core_api = k8s_client.CoreV1Api(deployer.get_kube_client())

        kube_utils.create_namespace(
            core_api=core_api, namespace=self.namespace
        )

        if self.config.hf_token:
            kube_utils.create_or_update_secret(
                core_api=core_api,
                namespace=self.namespace,
                secret_name=self.hf_secret_name,
                data={VLLM_HF_TOKEN_SECRET_KEY: self.config.hf_token},
            )

        labels = self._labels
        manifests = [
            build_vllm_deployment_manifest(
                name=self.deployment_name,
                namespace=self.namespace,
                image=self.image,
                replicas=self.config.replicas,
                port=self.config.port,
                engine_args=self.config,
                extra_serve_args=self.config.extra_serve_args,
                labels=labels,
                resources=self.config.resources,
                shm_size=self.config.shm_size,
                env=self.config.env,
                hf_secret_name=self._resolve_hf_secret_name(),
                pod_settings=self.config.pod_settings,
            ),
            build_vllm_service_manifest(
                name=self.service_name,
                namespace=self.namespace,
                port=self.config.port,
                service_type=self.service_type,
                selector_labels=labels,
                labels=labels,
            ),
        ]

        deployer.k8s_applier.provision(
            manifests,
            default_namespace=self.namespace,
            field_manager=VLLM_FIELD_MANAGER,
            force=True,
        )

    def _list_pods(
        self, core_api: k8s_client.CoreV1Api
    ) -> List[k8s_client.V1Pod]:
        """List the pods belonging to this service's Deployment.

        Args:
            core_api: Kubernetes Core V1 API client.

        Returns:
            The pods matching the service's label selector.
        """
        label_selector = ",".join(
            f"{key}={value}" for key, value in self._labels.items()
        )
        pod_list = core_api.list_namespaced_pod(
            namespace=self.namespace, label_selector=label_selector
        )
        return cast(List[k8s_client.V1Pod], pod_list.items)

    def _get_pod_failure_message(
        self, pods: List[k8s_client.V1Pod]
    ) -> Optional[str]:
        """Look for pod-level failure conditions among the deployment's pods.

        Args:
            pods: The deployment's pods.

        Returns:
            A failure message if a pod is crash-looping or failing to pull
            its image. `None` otherwise.
        """
        for pod in pods:
            container_name = _pod_container_name(pod)
            container_status = kube_utils.get_container_status(
                pod, container_name
            )
            if (
                container_status
                and container_status.waiting
                and container_status.waiting.reason in POD_FAILURE_REASONS
            ):
                return kube_utils.get_pod_failure_details(pod, container_name)

        return None

    def _get_pod_pending_message(
        self, pods: List[k8s_client.V1Pod]
    ) -> Optional[str]:
        """Look for pod-level pending details among the deployment's pods.

        Args:
            pods: The deployment's pods.

        Returns:
            Pending details, such as an `Unschedulable` condition, if a pod
            is not yet running. `None` otherwise.
        """
        for pod in pods:
            container_name = _pod_container_name(pod)
            pending_message = kube_utils.get_pod_pending_details(
                pod, container_name
            )
            if pending_message:
                return pending_message

        return None

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the current operational state of the vLLM Kubernetes Deployment.

        Returns:
            The operational state of the Deployment and a message providing
            additional information about that state.
        """
        deployer = self._get_deployer()
        applier = deployer.k8s_applier

        deployment = applier.get_resource(
            name=self.deployment_name,
            namespace=self.namespace,
            kind="Deployment",
            api_version="apps/v1",
        )
        if deployment is None:
            return (ServiceState.INACTIVE, "")

        deployment_dict = normalize_resource_to_dict(deployment)
        status = deployment_dict.get("status") or {}
        spec = deployment_dict.get("spec") or {}
        desired_replicas = spec.get("replicas", 0)
        available_replicas = status.get("availableReplicas", 0)

        conditions = {
            condition.get("type"): condition
            for condition in status.get("conditions") or []
        }
        progressing = conditions.get("Progressing", {})
        if progressing.get("reason") == "ProgressDeadlineExceeded":
            return (
                ServiceState.ERROR,
                progressing.get(
                    "message",
                    f"Deployment '{self.deployment_name}' rollout stuck.",
                ),
            )

        core_api = k8s_client.CoreV1Api(deployer.get_kube_client())
        pods = self._list_pods(core_api)
        pod_failure_message = self._get_pod_failure_message(pods)
        if pod_failure_message:
            return (ServiceState.ERROR, pod_failure_message)

        if desired_replicas and available_replicas >= desired_replicas:
            return (
                ServiceState.ACTIVE,
                f"vLLM deployment '{self.deployment_name}' is available",
            )

        # An unschedulable pod may still be scheduled once the cluster
        # autoscaler adds a node, so this stays PENDING_STARTUP instead of
        # ERROR. ProgressDeadlineExceeded above is the signal for a rollout
        # that is no longer transient.
        pod_pending_message = self._get_pod_pending_message(pods)
        return (
            ServiceState.PENDING_STARTUP,
            pod_pending_message
            or f"vLLM deployment '{self.deployment_name}' is starting up",
        )

    def deprovision(self, force: bool = False) -> None:
        """Deprovision the vLLM Kubernetes Deployment, Service, and secret.

        Args:
            force: if True, the remote deployment instance will be
                forcefully deprovisioned.
        """
        deployer = self._get_deployer()

        inventory = [
            ResourceInventoryItem(
                api_version="v1",
                kind="Service",
                namespace=self.namespace,
                name=self.service_name,
            ),
            ResourceInventoryItem(
                api_version="apps/v1",
                kind="Deployment",
                namespace=self.namespace,
                name=self.deployment_name,
            ),
        ]
        if self.config.hf_token:
            inventory.append(
                ResourceInventoryItem(
                    api_version="v1",
                    kind="Secret",
                    namespace=self.namespace,
                    name=self.hf_secret_name,
                )
            )

        deployer.k8s_applier.delete_from_inventory(
            inventory=inventory, propagation_policy="Foreground"
        )

    def get_logs(
        self,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get the logs of the vLLM Kubernetes deployment.

        Args:
            follow: if True, the logs will be streamed as they are written.
            tail: only retrieve the last NUM lines of log output.

        Yields:
            A generator that can be accessed to get the service logs.
        """
        deployer = self._get_deployer()
        core_api = k8s_client.CoreV1Api(deployer.get_kube_client())

        pods = self._list_pods(core_api)
        if not pods:
            return

        pod_name = pods[0].metadata.name

        if follow:
            response = core_api.read_namespaced_pod_log(
                name=pod_name,
                namespace=self.namespace,
                follow=True,
                tail_lines=tail,
                _preload_content=False,
            )
            for line in response:
                yield (
                    line.decode("utf-8").rstrip()
                    if isinstance(line, bytes)
                    else str(line).rstrip()
                )
        else:
            response = core_api.read_namespaced_pod_log(
                name=pod_name,
                namespace=self.namespace,
                tail_lines=tail,
                _preload_content=False,
            )
            logs = response.data.decode("utf-8")
            for line in logs.split("\n"):
                if line:
                    yield line

    def _resolve_service_url(self) -> Optional[str]:
        """Resolve the base URL of the underlying Kubernetes Service.

        Returns:
            The base URL, or `None` if the Service resource does not exist
            yet or has no resolvable address.
        """
        deployer = self._get_deployer()
        service = deployer.k8s_applier.get_resource(
            name=self.service_name,
            namespace=self.namespace,
            kind="Service",
            api_version="v1",
        )
        if service is None:
            return None

        core_api = k8s_client.CoreV1Api(deployer.get_kube_client())
        return kube_utils.build_service_url(
            core_api=core_api, service=service, namespace=self.namespace
        )

    @property
    def service_url(self) -> Optional[str]:
        """Base URL of the underlying Kubernetes Service.

        Returns:
            The base URL, or `None` if the service is not running or the
            Service resource has no resolvable address.
        """
        if not self.is_running:
            return None
        return self._resolve_service_url()

    @property
    def prediction_url(self) -> Optional[str]:
        """The prediction URI exposed by the vLLM Kubernetes service.

        Returns:
            The prediction URI, or `None` if the service is not yet ready.
        """
        base_url = self.service_url
        if base_url is None:
            return None
        return os.path.join(base_url, VLLM_PREDICTION_URL_PATH)

    @property
    def healthcheck_url(self) -> Optional[str]:
        """The healthcheck URI exposed by the vLLM Kubernetes service.

        Returns:
            The healthcheck URI, or `None` if the service is not yet ready.
        """
        base_url = self.service_url
        if base_url is None:
            return None
        return os.path.join(base_url, VLLM_HEALTHCHECK_URL_PATH)

    def predict(self, data: Any) -> Any:
        """Make a prediction using the service.

        Args:
            data: Prompt to run inference on.

        Raises:
            Exception: if the service is not running.

        Returns:
            The prediction result.
        """
        prediction_url = self.prediction_url
        if prediction_url is None:
            raise Exception(
                "vLLM Inference service is not running. "
                "Please start the service before making predictions."
            )

        from openai import OpenAI

        client = OpenAI(api_key="EMPTY", base_url=prediction_url)
        models = client.models.list()
        model = models.data[0].id
        return client.completions.create(model=model, prompt=data)
