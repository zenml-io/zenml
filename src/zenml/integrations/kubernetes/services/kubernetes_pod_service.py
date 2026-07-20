#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""A long-running, pod-backed ZenML service for Kubernetes."""

from typing import Dict, Generator, List, Optional, Tuple

from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException
from pydantic import Field

from zenml.enums import ServiceState
from zenml.integrations.kubernetes import kube_utils
from zenml.integrations.kubernetes.manifest_utils import (
    build_job_manifest,
    build_pod_manifest,
    pod_template_manifest_from_pod,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.logger import get_logger
from zenml.models.v2.misc.service import ServiceType
from zenml.services.service import BaseService, ServiceConfig
from zenml.services.service_endpoint import (
    BaseServiceEndpoint,
    ServiceEndpointConfig,
    ServiceEndpointProtocol,
    ServiceEndpointStatus,
)
from zenml.services.service_monitor import BaseServiceEndpointHealthMonitor
from zenml.services.service_status import ServiceStatus

logger = get_logger(__name__)

# Finished jobs (and, by ownership, their pod and service) are garbage
# collected this many seconds after completion. This is the backstop that
# reaps a service whose `deprovision` was never called: a completed pod may
# not linger indefinitely holding onto (GPU) resources.
TTL_SECONDS_AFTER_FINISHED = 600

# The single container built by `build_pod_manifest`.
_MAIN_CONTAINER_NAME = "main"


def build_pod_service_manifest(
    job: k8s_client.V1Job, port: int
) -> k8s_client.V1Service:
    """Headless service giving the service pod stable in-cluster DNS.

    The service is owned by the job, so Kubernetes garbage collection removes
    it together with the job (on deprovision, TTL, or deadline) — teardown
    never depends on service code running.

    Args:
        job: The created job (its uid anchors the owner reference).
        port: The port the service pod listens on.

    Returns:
        The headless service manifest.
    """
    job_name = job.metadata.name
    return k8s_client.V1Service(
        metadata=k8s_client.V1ObjectMeta(
            name=job_name,
            labels=job.metadata.labels,
            owner_references=[
                k8s_client.V1OwnerReference(
                    api_version="batch/v1",
                    kind="Job",
                    name=job_name,
                    uid=job.metadata.uid,
                    controller=False,
                    block_owner_deletion=False,
                )
            ],
        ),
        spec=k8s_client.V1ServiceSpec(
            cluster_ip="None",
            # Kubernetes labels every pod of a job with `job-name`.
            selector={"job-name": job_name},
            ports=[k8s_client.V1ServicePort(name="http", port=port)],
            # The pod must be resolvable during startup, before readiness.
            publish_not_ready_addresses=True,
        ),
    )


def build_service_job_manifest(
    job_name: str,
    pod_template: k8s_client.V1PodTemplateSpec,
    max_lifetime_seconds: int,
    labels: Optional[Dict[str, str]] = None,
) -> k8s_client.V1Job:
    """Build the job manifest backing a Kubernetes pod service.

    The job runs a single pod and never retries it (``backoff_limit=0``): a
    service that crashes should surface as failed, not be silently relaunched.
    ``active_deadline_seconds`` bounds the pod's lifetime even if nothing ever
    calls ``deprovision``; ``ttl_seconds_after_finished`` then reaps the
    finished job and everything it owns.

    Args:
        job_name: Name of the job (also the pod's stable hostname/subdomain).
        pod_template: The pod template running the service command.
        max_lifetime_seconds: Hard upper bound on the pod's lifetime, enforced
            by Kubernetes regardless of whether teardown code ever runs.
        labels: Labels to apply to the job.

    Returns:
        The job manifest.
    """
    return build_job_manifest(
        job_name=job_name,
        pod_template=pod_template,
        backoff_limit=0,
        ttl_seconds_after_finished=TTL_SECONDS_AFTER_FINISHED,
        active_deadline_seconds=max_lifetime_seconds,
        labels=labels,
    )


def pod_is_ready(pod: k8s_client.V1Pod) -> bool:
    """Check whether a pod reports the ``Ready`` condition.

    Args:
        pod: The pod to inspect.

    Returns:
        True if the pod's `Ready` condition is `True`, otherwise False.
    """
    if not pod.status or not pod.status.conditions:
        return False
    for condition in pod.status.conditions:
        if condition.type == "Ready":
            return condition.status == "True"  # type: ignore[no-any-return]
    return False


class KubernetesPodServiceConfig(ServiceConfig):
    """Configuration for a Kubernetes pod service.

    Attributes:
        image: The container image the service pod runs.
        command: The command the service pod's container executes.
        env: Environment variables to set in the service pod's container.
        namespace: The Kubernetes namespace the service resources live in.
        port: The port the service pod listens on.
        cpu_request: Optional CPU resource request for the service pod.
        memory_request: Optional memory resource request for the service pod.
        gpu_count: Optional number of GPUs to request for the service pod.
            GPUs are requested as both a request and a limit, as Kubernetes
            requires for `nvidia.com/gpu`.
        service_account_name: Optional Kubernetes service account the pod runs
            as.
        max_lifetime_seconds: Hard upper bound on the pod's lifetime. Kubernetes
            terminates the pod once this is exceeded even if `deprovision` is
            never called, which is the backstop against leaked long-running
            (GPU) services.
        pod_settings: Optional additional pod settings (node selectors,
            tolerations, volumes, etc.). Resource requests set here take
            precedence over `cpu_request`/`memory_request`/`gpu_count`.
    """

    image: str
    command: List[str]
    env: Dict[str, str] = {}
    namespace: str = "default"
    port: int
    cpu_request: Optional[str] = None
    memory_request: Optional[str] = None
    gpu_count: Optional[int] = None
    service_account_name: Optional[str] = None
    max_lifetime_seconds: int = 86400
    pod_settings: Optional[KubernetesPodSettings] = None


class KubernetesPodServiceEndpoint(BaseServiceEndpoint):
    """In-cluster endpoint exposed by a Kubernetes pod service."""

    config: ServiceEndpointConfig = Field(
        default_factory=ServiceEndpointConfig
    )
    status: ServiceEndpointStatus = Field(
        default_factory=ServiceEndpointStatus
    )
    monitor: Optional[BaseServiceEndpointHealthMonitor] = None


class KubernetesPodService(BaseService):
    """A long-running ZenML service backed by a single Kubernetes pod.

    The service runs one command in one pod, wrapped in a Kubernetes ``Job``,
    and fronted by a headless ``Service`` that gives the pod stable in-cluster
    DNS (`http://<name>.<name>.<namespace>.svc:<port>`, exposed as `url`).

    Teardown philosophy — the point of this service:

        On the happy path the service is torn down by `deprovision`, which
        deletes the job and lets Kubernetes cascade-delete the pod and the
        headless service it owns. But `deprovision` running is never the
        *guarantee*. The guarantee is Kubernetes garbage collection:

          * `active_deadline_seconds` (from `max_lifetime_seconds`) bounds the
            pod's life even if nothing ever calls `deprovision`.
          * `ttl_seconds_after_finished` plus owner references reap the job,
            pod, and service after the pod finishes.

        A leaked service — a client that crashed, a forgotten GPU inference
        server — therefore dies on its own. No cleanup code has to run for the
        resources to go away.

    Because a service carries no stack component (and thus no service
    connector), `provision` must run somewhere Kubernetes credentials are
    available: inside a step pod (in-cluster config) or on a client with a
    kubeconfig.

    Named vs. unnamed services:

        When `config.name` is set, all Kubernetes resource names (and hence
        `url`) derive from it deterministically. The URL is therefore known
        *before* provisioning, so a caller can bake it into a command it
        builds ahead of time (e.g. a `CommandStep` that will call the
        service). The flip side is that the caller owns name uniqueness
        within the namespace: provisioning a second service with the same
        name collides on the Kubernetes resource and fails loudly, which is
        the intended behavior — a name clash is surfaced, not silently
        aliased. Without a name the resource names derive from the service's
        uuid, and the URL only becomes meaningful once the instance exists.
    """

    SERVICE_TYPE = ServiceType(
        name="kubernetes-pod",
        type="k8s",
        flavor="zenml",
        description="A long-running service backed by a single Kubernetes pod.",
    )

    config: KubernetesPodServiceConfig
    status: ServiceStatus = Field(default_factory=ServiceStatus)
    endpoint: Optional[KubernetesPodServiceEndpoint] = None

    _k8s_client: Optional[k8s_client.ApiClient] = None

    @property
    def _resource_name(self) -> str:
        """The shared name of the job, pod hostname/subdomain, and service.

        When the config carries an explicit `name`, the resource name (and
        therefore `url`) is derived deterministically from it, so the endpoint
        is known *before* provisioning. Otherwise it falls back to the
        service's uuid, whose URL only exists once the instance does.

        `BaseService.__init__` fills a blank `config.name` with the class name,
        so a name equal to the class name is treated as "unset" and takes the
        uuid path.

        Returns:
            The Kubernetes resource name for this service instance.
        """
        if self.config.name and self.config.name != type(self).__name__:
            sanitized = kube_utils.sanitize_label(self.config.name)
            if sanitized:
                return f"zenml-svc-{sanitized}"[:63].rstrip("-")
        return f"zenml-svc-{self.uuid.hex[:8]}"

    @property
    def _dns_name(self) -> str:
        """The in-cluster DNS name resolving to the service pod.

        Returns:
            The fully qualified in-cluster DNS name of the service pod.
        """
        name = self._resource_name
        return f"{name}.{name}.{self.config.namespace}.svc"

    @property
    def url(self) -> str:
        """The in-cluster URL at which the service pod is reachable.

        Returns:
            The `http://<dns>:<port>` URL of the service pod.
        """
        return f"http://{self._dns_name}:{self.config.port}"

    def _get_kube_client(self) -> k8s_client.ApiClient:
        """Build (and cache) a Kubernetes API client from the local config.

        A service carries no connector, so the client is built from whatever
        Kubernetes configuration is available where `provision` runs: the
        in-cluster config when running inside a pod, otherwise the local
        kubeconfig.

        Returns:
            The Kubernetes API client.
        """
        if self._k8s_client is not None:
            return self._k8s_client

        if kube_utils.is_inside_kubernetes():
            kube_utils.load_kube_config(incluster=True)
        else:
            kube_utils.load_kube_config()
        self._k8s_client = k8s_client.ApiClient()
        return self._k8s_client

    def _core_api(self) -> k8s_client.CoreV1Api:
        """Get the Kubernetes Core V1 API client.

        Returns:
            The Kubernetes Core V1 API client.
        """
        return k8s_client.CoreV1Api(self._get_kube_client())

    def _batch_api(self) -> k8s_client.BatchV1Api:
        """Get the Kubernetes Batch V1 API client.

        Returns:
            The Kubernetes Batch V1 API client.
        """
        return k8s_client.BatchV1Api(self._get_kube_client())

    def _build_pod_settings(self) -> Optional[KubernetesPodSettings]:
        """Merge the config's resource requests into its pod settings.

        Explicit resource requests in `config.pod_settings` win over the
        `cpu_request`/`memory_request`/`gpu_count` shorthands.

        Returns:
            The pod settings to apply, or None if none are configured.
        """
        requests: Dict[str, str] = {}
        limits: Dict[str, str] = {}
        if self.config.cpu_request:
            requests["cpu"] = self.config.cpu_request
        if self.config.memory_request:
            requests["memory"] = self.config.memory_request
        if self.config.gpu_count:
            gpu = str(self.config.gpu_count)
            requests["nvidia.com/gpu"] = gpu
            limits["nvidia.com/gpu"] = gpu

        if not requests and not limits:
            return self.config.pod_settings

        existing = (
            self.config.pod_settings.resources
            if self.config.pod_settings
            else {}
        )
        resources: Dict[str, Dict[str, str]] = {}
        merged_requests = {**requests, **existing.get("requests", {})}
        merged_limits = {**limits, **existing.get("limits", {})}
        if merged_requests:
            resources["requests"] = merged_requests
        if merged_limits:
            resources["limits"] = merged_limits

        if self.config.pod_settings:
            return self.config.pod_settings.model_copy(
                update={"resources": resources}
            )
        return KubernetesPodSettings(resources=resources)

    def provision(self) -> None:
        """Provision the Kubernetes resources backing the service.

        Creates one job (whose single pod runs the service command) and one
        headless service owned by that job. Everything the service creates is
        owned by the job, so Kubernetes garbage collection reaps it all.
        """
        name = self._resource_name
        namespace = self.config.namespace
        labels = {
            "zenml-service-uuid": kube_utils.sanitize_label_value(
                self.uuid.hex
            ),
        }

        pod_manifest = build_pod_manifest(
            pod_name=None,
            image_name=self.config.image,
            command=self.config.command,
            args=[],
            privileged=False,
            pod_settings=self._build_pod_settings(),
            service_account_name=self.config.service_account_name,
            env=self.config.env,
            labels=labels,
        )
        # `build_pod_manifest` always populates the spec; the stable DNS name
        # the headless service resolves comes from the pod's hostname and
        # subdomain.
        assert pod_manifest.spec is not None
        pod_manifest.spec.hostname = name
        pod_manifest.spec.subdomain = name

        job_manifest = build_service_job_manifest(
            job_name=name,
            pod_template=pod_template_manifest_from_pod(pod_manifest),
            max_lifetime_seconds=self.config.max_lifetime_seconds,
            labels=labels,
        )

        batch_api = self._batch_api()
        core_api = self._core_api()
        kube_utils.create_job(
            batch_api=batch_api,
            namespace=namespace,
            job_manifest=job_manifest,
        )

        # Read the job back to get its uid before anchoring the service's
        # owner reference to it.
        created_job = kube_utils.get_job(
            batch_api=batch_api,
            namespace=namespace,
            job_name=name,
        )
        kube_utils.retry_on_api_exception(core_api.create_namespaced_service)(
            namespace=namespace,
            body=build_pod_service_manifest(created_job, self.config.port),
        )

        endpoint = KubernetesPodServiceEndpoint()
        endpoint.status.protocol = ServiceEndpointProtocol.HTTP
        endpoint.status.hostname = self._dns_name
        endpoint.status.port = self.config.port
        self.endpoint = endpoint

    def deprovision(self, force: bool = False) -> None:
        """Deprovision the service by deleting its job.

        Deletion cascades: the pod and the headless service are owned by the
        job, so Kubernetes garbage collection removes them too. Deleting an
        already-absent job is a no-op.

        Args:
            force: Unused; deletion is always a foreground cascade delete.
        """
        try:
            kube_utils.retry_on_api_exception(
                self._batch_api().delete_namespaced_job,
            )(
                name=self._resource_name,
                namespace=self.config.namespace,
                propagation_policy="Foreground",
            )
        except ApiException as e:
            if e.status != 404:
                raise
            logger.debug(
                "Job `%s` already deleted; nothing to deprovision.",
                self._resource_name,
            )

    def _get_service_pod(self) -> Optional[k8s_client.V1Pod]:
        """Get the pod backing the service, if it exists.

        Returns:
            The service pod, or None if no pod exists yet.
        """
        try:
            pods = kube_utils.retry_on_api_exception(
                self._core_api().list_namespaced_pod,
            )(
                namespace=self.config.namespace,
                label_selector=f"job-name={self._resource_name}",
            )
        except ApiException:
            return None

        if not pods.items:
            return None
        return pods.items[0]

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the operational state of the service pod.

        Returns:
            The operational state and a message describing it.
        """
        pod = self._get_service_pod()
        if pod is None or pod.status is None:
            return ServiceState.INACTIVE, "No pod found for the service."

        phase = pod.status.phase
        reason = pod.status.reason or ""

        if phase == kube_utils.PodPhase.PENDING.value:
            details = (
                kube_utils.get_pod_pending_details(pod, _MAIN_CONTAINER_NAME)
                or reason
                or "Pod is pending."
            )
            return ServiceState.PENDING_STARTUP, details

        if phase == kube_utils.PodPhase.RUNNING.value:
            if pod_is_ready(pod):
                return ServiceState.ACTIVE, "Pod is running and ready."
            return (
                ServiceState.PENDING_STARTUP,
                "Pod is running but not yet ready.",
            )

        if phase == kube_utils.PodPhase.FAILED.value:
            details = (
                kube_utils.get_pod_failure_details(pod, _MAIN_CONTAINER_NAME)
                or reason
                or "Pod failed."
            )
            return ServiceState.ERROR, details

        if phase == kube_utils.PodPhase.SUCCEEDED.value:
            return ServiceState.INACTIVE, "Pod has completed."

        return ServiceState.ERROR, f"Pod is in an unknown phase: {phase}."

    def get_logs(
        self, follow: bool = False, tail: Optional[int] = None
    ) -> Generator[str, bool, None]:
        """Retrieve the logs of the service pod.

        Args:
            follow: If True, stream the logs as they are written.
            tail: If set, only retrieve the last this-many lines.

        Yields:
            Lines of the service pod's logs.
        """
        pod = self._get_service_pod()
        if pod is None or not pod.metadata:
            return

        core_api = self._core_api()
        kwargs: Dict[str, object] = {
            "name": pod.metadata.name,
            "namespace": self.config.namespace,
        }
        if tail is not None:
            kwargs["tail_lines"] = tail

        if follow:
            response = core_api.read_namespaced_pod_log(
                follow=True, _preload_content=False, **kwargs
            )
            buffer = ""
            for chunk in response.stream():
                buffer += chunk.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    yield line
            if buffer:
                yield buffer
        else:
            logs = core_api.read_namespaced_pod_log(**kwargs)
            for line in logs.splitlines():
                yield line
