# Copyright 2020 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utilities for Kubernetes related functions.

Internal interface: no backwards compatibility guarantees.
Adjusted from https://github.com/tensorflow/tfx/blob/master/tfx/utils/kube_utils.py.
"""

import datetime
import enum
import re
import time
from typing import Any, Callable, Dict, Optional, TypeVar, cast

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException

from zenml.integrations.kubernetes.orchestrators.manifest_utils import (
    build_cluster_role_binding_manifest_for_service_account,
    build_mysql_deployment_manifest,
    build_mysql_service_manifest,
    build_namespace_manifest,
    build_persistent_volume_claim_manifest,
    build_persistent_volume_manifest,
    build_service_account_manifest,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


class PodPhase(enum.Enum):
    """Phase of the Kubernetes Pod.

    Pod phases are defined in
    https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-phase.
    """

    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"


class RestartPolicy(enum.Enum):
    """Restart policy of the Kubernetes Pod container.

    Restart policies are defined in
    https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#restart-policy
    """

    ALWAYS = "Always"
    ON_FAILURE = "OnFailure"
    NEVER = "Never"


class PersistentVolumeAccessMode(enum.Enum):
    """Access mode of the Kubernetes Persistent Volume.

    Access modes are defined in
    https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes
    """

    READ_WRITE_ONCE = "ReadWriteOnce"
    READ_ONLY_MANY = "ReadOnlyMany"
    READ_WRITE_MANY = "ReadWriteMany"


class _KubernetesClientFactory:
    """Factory class for creating kubernetes API client."""

    def __init__(self) -> None:
        self._config_loaded = False
        self._inside_cluster = False

    @property
    def inside_cluster(self) -> bool:
        """Whether current environment is inside the kubernetes cluster.

        Returns:
            bool: True if inside the cluster else False.
        """
        if not self._config_loaded:
            self._LoadConfig()
        return self._inside_cluster

    def _LoadConfig(self) -> None:  # pylint: disable=invalid-name
        """Load the kubernetes client config.

        Depending on the environment (whether it is inside the running kubernetes
        cluster or remote host), different location will be searched for the config
        file. The loaded config will be used as a default value for the clients this
        factory is creating.
        If config is already loaded, it is a no-op.
        """
        try:
            # If this code is running inside Kubernetes Pod, service account admission
            # controller [1] sets volume mounts in which the service account tokens
            # and certificates exists, and it can be loaded using
            # `load_incluster_config()`.
            #
            # [1]
            # https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/#service-account-admission-controller
            self._inside_cluster = True
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            # If loading config in cluster fails, it means we're not running the code
            # inside Kubernetes cluster. We try to load `~/.kube/config` file, or the
            # filename from the KUBECONFIG environment variable.
            # It will raise `kubernetes.config.ConfigException` if no config file
            # is found.
            self._inside_cluster = False
            k8s_config.load_kube_config()

        self._config_loaded = True

    def MakeCoreV1Api(
        self,
    ) -> k8s_client.CoreV1Api:  # pylint: disable=invalid-name
        """Make a kubernetes `CoreV1Api` client.

        Returns:
            `CoreV1Api` client.
        """
        if not self._config_loaded:
            self._LoadConfig()
        return k8s_client.CoreV1Api()

    def MakeBatchV1Api(
        self,
    ) -> k8s_client.BatchV1Api:  # pylint: disable=invalid-name
        """Make a Kubernetes `BatchV1Api` client.

        Returns:
            `BatchV1Api` client.
        """
        if not self._config_loaded:
            self._LoadConfig()
        return k8s_client.BatchV1Api()


_factory = _KubernetesClientFactory()


def sanitize_pod_name(pod_name: str) -> str:
    """Sanitize pod names so they conform to kubernetes pod naming convention.

    Args:
        pod_name (str): Arbitrary input pod name.

    Returns:
        str: Sanitized pod name.
    """
    pod_name = re.sub(r"[^a-z0-9-]", "-", pod_name.lower())
    pod_name = re.sub(r"^[-]+", "", pod_name)
    return re.sub(r"[-]+", "-", pod_name)


def pod_is_not_pending(pod: k8s_client.V1Pod) -> bool:
    """Check if pod status is not 'Pending'.

    Args:
        pod (k8s_client.V1Pod): kubernetes pod.

    Returns:
        bool: False if the pod status is 'Pending' else True.
    """
    return pod.status.phase != PodPhase.PENDING.value  # type: ignore[no-any-return]


def pod_failed(pod: k8s_client.V1Pod) -> bool:
    """Check if pod status is 'Failed'.

    Args:
        pod (k8s_client.V1Pod): kubernetes pod.

    Returns:
        bool: True if pod status is 'Failed' else False.
    """
    return pod.status.phase == PodPhase.FAILED.value  # type: ignore[no-any-return]


def pod_is_done(pod: k8s_client.V1Pod) -> bool:
    """Check if pod status is 'Succeeded'.

    Args:
        pod (k8s_client.V1Pod): kubernetes pod.

    Returns:
        bool: True if pod status is 'Succeeded' else False.
    """
    return pod.status.phase == PodPhase.SUCCEEDED.value  # type: ignore[no-any-return]


def make_core_v1_api() -> k8s_client.CoreV1Api:
    """Make a kubernetes `CoreV1Api` client.

    Returns:
        `CoreV1Api` client.
    """
    return _factory.MakeCoreV1Api()


def make_batch_v1_api() -> k8s_client.BatchV1Api:
    """Make a kubernetes `BatchV1Api` client.

    Returns:
        `BatchV1Api` client.
    """
    return _factory.MakeBatchV1Api()


def is_inside_cluster() -> bool:
    """Whether current running environment is inside the kubernetes cluster.

    Returns:
        bool: True if inside Kubernetes cluster else False.
    """
    return _factory.inside_cluster


def get_pod(
    core_api: k8s_client.CoreV1Api, pod_name: str, namespace: str
) -> Optional[k8s_client.V1Pod]:
    """Get a pod from Kubernetes metadata API.

    Args:
        core_api: Client of `CoreV1Api` of Kubernetes API.
        pod_name: The name of the Pod.
        namespace: The namespace of the Pod.

    Raises:
        RuntimeError: When it sees unexpected errors from Kubernetes API.

    Returns:
        The found Pod object. None if it's not found.
    """
    try:
        return core_api.read_namespaced_pod(name=pod_name, namespace=namespace)
    except k8s_client.rest.ApiException as e:
        if e.status != 404:
            raise RuntimeError(
                "Unknown error! \nReason: %s\nBody: %s" % (e.reason, e.body)
            )
        return None


def wait_pod(
    core_api: k8s_client.CoreV1Api,
    pod_name: str,
    namespace: str,
    exit_condition_lambda: Callable[[k8s_client.V1Pod], bool],
    timeout_sec: int = 0,
    exponential_backoff: bool = False,
    stream_logs: bool = False,
) -> k8s_client.V1Pod:
    """Wait for a Pod to meet an exit condition.

    Args:
        core_api: Client of `CoreV1Api` of Kubernetes API.
        pod_name: The name of the Pod.
        namespace: The namespace of the Pod.
        exit_condition_lambda: A lambda
            which will be called periodically to wait for a Pod to exit. The
            function returns True to exit.
        timeout_sec: Timeout in seconds to wait for pod to reach exit
            condition, or 0 to wait for an unlimited duration.
            Defaults to unlimited.
        exponential_backoff: Whether to use exponential back off for polling.
            Defaults to False.
        stream_logs: Whether to stream the pod logs to
            `zenml.logger.info()`. Defaults to False.

    Raises:
        RuntimeError: when the function times out.

    Returns:
        The Pod object which meets the exit condition.
    """
    start_time = datetime.datetime.utcnow()

    # Link to exponential back-off algorithm used here:
    # https://cloud.google.com/storage/docs/exponential-backoff
    backoff_interval = 1
    maximum_backoff = 32

    logged_lines = 0

    while True:
        resp = get_pod(core_api, pod_name, namespace)

        # Stream logs to `zenml.logger.info()`.
        # TODO: can we do this without parsing all logs every time?
        if stream_logs and pod_is_not_pending(resp):
            response = core_api.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
            )
            logs = response.splitlines()
            if len(logs) > logged_lines:
                for line in logs[logged_lines:]:
                    logger.info(line)
                logged_lines = len(logs)

        # Raise an error if the pod failed.
        if pod_failed(resp):
            raise RuntimeError(f"Pod `{namespace}:{pod_name}` failed.")

        # Check if pod is in desired state (e.g. finished / running / ...).
        if exit_condition_lambda(resp):
            return resp

        # Check if wait timed out.
        elapse_time = datetime.datetime.utcnow() - start_time
        if elapse_time.seconds >= timeout_sec and timeout_sec != 0:
            raise RuntimeError(
                f"Waiting for pod `{namespace}:{pod_name}` timed out after "
                f"{timeout_sec} seconds."
            )

        # Wait (using exponential backoff).
        time.sleep(backoff_interval)
        if exponential_backoff and backoff_interval < maximum_backoff:
            backoff_interval *= 2


FuncT = TypeVar("FuncT", bound=Callable[..., Any])


def _if_not_exists(create_fn: FuncT) -> FuncT:
    """Wrap a kubernetes function to handle creation if already exists.

    Args:
        create_fn: kubernetes function to be wrapped.

    Returns:
        Wrapped kubernetes function.
    """

    def create_if_not_exists(*args: Any, **kwargs: Any) -> None:
        try:
            create_fn(*args, **kwargs)
        except ApiException as exc:
            if exc.status != 409:
                raise
            logger.debug(
                f"Didn't execute {create_fn.__name__} because already exists."
            )

    return cast(FuncT, create_if_not_exists)


def create_cluster_role_binding(body: Dict[str, Any]) -> None:
    """Create a k8s cluster role binding.

    Args:
        body: Manifest for creating a cluster role binding.
    """
    with k8s_client.ApiClient() as api_client:
        api_instance = k8s_client.RbacAuthorizationV1Api(api_client)
        api_instance.create_cluster_role_binding(body=body)


def create_deployment(body: Dict[str, Any], namespace: str = "default") -> None:
    """Create a k8s deployment.

    Args:
        body: Manifest for creating a deployment.
        namespace: Kubernetes namespace. Defaults to "default".
    """
    with k8s_client.ApiClient() as api_client:
        api_instance = k8s_client.AppsV1Api(api_client)
        api_instance.create_namespaced_deployment(
            namespace=namespace, body=body
        )


def create_edit_service_account(
    core_api: k8s_client.CoreV1Api,
    service_account_name: str,
    namespace: str = "default",
    cluster_role_binding_name: str = "zenml-edit",
) -> None:
    """Create a new k8s service account with "edit" rights.

    Args:
        core_api: Client of Core V1 API of Kubernetes API.
        service_account_name: Name of the service account.
        namespace: Kubernetes namespace. Defaults to "default".
        cluster_role_binding_name: Name of the cluster role binding.
            Defaults to "zenml-edit".
    """
    crb_manifest = build_cluster_role_binding_manifest_for_service_account(
        name=cluster_role_binding_name,
        role_name="edit",
        service_account_name=service_account_name,
        namespace=namespace,
    )
    _if_not_exists(create_cluster_role_binding)(body=crb_manifest)

    sa_manifest = build_service_account_manifest(
        name=service_account_name, namespace=namespace
    )
    _if_not_exists(core_api.create_namespaced_service_account)(
        namespace=namespace,
        body=sa_manifest,
    )


def create_namespace(core_api: k8s_client.CoreV1Api, namespace: str) -> None:
    """Create a k8s namespace.

    Args:
        core_api: Client of Core V1 API of Kubernetes API.
        namespace: Kubernetes namespace. Defaults to "default".
    """
    manifest = build_namespace_manifest(namespace)
    _if_not_exists(core_api.create_namespace)(body=manifest)


def create_mysql_deployment(
    core_api: k8s_client.CoreV1Api,
    namespace: str = "default",
    storage_capacity: str = "10Gi",
    deployment_name: str = "mysql",
    service_name: str = "mysql",
    volume_name: str = "mysql-pv-volume",
    volume_claim_name: str = "mysql-pv-claim",
) -> None:
    """Create a k8s deployment with a MySQL database running on it.

    Args:
        core_api: Client of Core V1 API of Kubernetes API.
        namespace: Kubernetes namespace. Defaults to "default".
        storage_capacity: Storage capacity of the database. Defaults to `"10Gi"`.
        deployment_name: Name of the deployment. Defaults to "mysql".
        service_name: Name of the service. Defaults to "mysql".
        volume_name: Name of the persistent volume.
            Defaults to `"mysql-pv-volume"`.
        volume_claim_name: Name of the persistent volume claim.
            Defaults to `"mysql-pv-claim"`.
    """
    pvc_manifest = build_persistent_volume_claim_manifest(
        name=volume_claim_name,
        namespace=namespace,
        storage_request=storage_capacity,
    )
    _if_not_exists(core_api.create_namespaced_persistent_volume_claim)(
        namespace=namespace,
        body=pvc_manifest,
    )
    pv_manifest = build_persistent_volume_manifest(
        name=volume_name, storage_capacity=storage_capacity
    )
    _if_not_exists(core_api.create_persistent_volume)(body=pv_manifest)
    deployment_manifest = build_mysql_deployment_manifest(
        name=deployment_name,
        namespace=namespace,
        pv_claim_name=volume_claim_name,
    )
    _if_not_exists(create_deployment)(
        body=deployment_manifest, namespace=namespace
    )
    service_manifest = build_mysql_service_manifest(
        name=service_name, namespace=namespace
    )
    _if_not_exists(core_api.create_namespaced_service)(
        namespace=namespace, body=service_manifest
    )
