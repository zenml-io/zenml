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
"""Utilities for the kubernetes related functions.
Internal interface: no backwards compatibility guarantees.
"""

import datetime
import enum
import os
import re
import time
from typing import Callable, Dict, List, Optional

from absl import logging
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config

# Name of the main container that Argo workflow launches. As KFP internally uses
# Argo, container name for the KFP Pod is also the same.
# https://github.com/argoproj/argo/blob/master/workflow/common/common.go#L14
ARGO_MAIN_CONTAINER_NAME = "main"

# Set of environment variables that are set in the KubeFlow Pipelines pods.
KFP_POD_NAME = "KFP_POD_NAME"
KFP_NAMESPACE = "KFP_NAMESPACE"

# Service account with edit ClusterRoleBinding for native orchestration.
TFX_SERVICE_ACCOUNT = "tfx-service-account"


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

    @property
    def is_done(self):
        return self in (self.SUCCEEDED, self.FAILED)


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

    def __init__(self):
        self._config_loaded = False
        self._inside_cluster = False

    @property
    def inside_cluster(self):
        """Whether current environment is inside the kubernetes cluster."""
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
        Raises:
          kubernetes.config.ConfigException: If fails to locate configuration in
              current environment.
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
            # If loading incluster config fails, it means we're not running the code
            # inside Kubernetes cluster. We try to load ~/.kube/config file, or the
            # filename from the KUBECONFIG environment variable.
            # It will raise kubernetes.config.ConfigException if no kube config file
            # is found.
            self._inside_cluster = False
            k8s_config.load_kube_config()

        self._config_loaded = True

    def MakeCoreV1Api(
        self,
    ) -> k8s_client.CoreV1Api:  # pylint: disable=invalid-name
        """Make a kubernetes CoreV1Api client."""
        if not self._config_loaded:
            self._LoadConfig()
        return k8s_client.CoreV1Api()

    def MakeBatchV1Api(
        self,
    ) -> k8s_client.BatchV1Api:  # pylint: disable=invalid-name
        """Make a kubernetes BatchV1Api client."""
        if not self._config_loaded:
            self._LoadConfig()
        return k8s_client.BatchV1Api()


_factory = _KubernetesClientFactory()


def sanitize_pod_name(pod_name: str) -> str:
    pod_name = re.sub(r"[^a-z0-9-]", "-", pod_name.lower())
    pod_name = re.sub(r"^[-]+", "", pod_name)
    return re.sub(r"[-]+", "-", pod_name)


def pod_is_not_pending(resp: k8s_client.V1Pod) -> bool:
    return resp.status.phase != PodPhase.PENDING.value


def pod_is_done(resp: k8s_client.V1Pod) -> bool:
    return PodPhase(resp.status.phase).is_done


def make_core_v1_api() -> k8s_client.CoreV1Api:
    """Make a kubernetes CoreV1Api client."""
    return _factory.MakeCoreV1Api()


def make_batch_v1_api() -> k8s_client.BatchV1Api:
    """Make a kubernetes BatchV1Api client."""
    return _factory.MakeBatchV1Api()


def make_job_object(
    name: str,
    container_image: str,
    command: List[str],
    namespace: str = "default",
    container_name: str = "jobcontainer",
    pod_labels: Optional[Dict[str, str]] = None,
    service_account_name: str = "default",
) -> k8s_client.V1Job:
    """Make a Kubernetes Job object with a single pod.
    See
    https://kubernetes.io/docs/concepts/workloads/controllers/job/#writing-a-job-spec
    Args:
      name: Name of job.
      container_image: Name of container image.
      command: Command to run.
      namespace: Kubernetes namespace to contain this Job.
      container_name: Name of the container.
      pod_labels: Dictionary of metadata labels for the pod.
      service_account_name: Name of the service account for this Job.
    Returns:
      `kubernetes.client.V1Job` object.
    """
    pod_labels = pod_labels or {}
    return k8s_client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=k8s_client.V1ObjectMeta(
            namespace=namespace,
            name=sanitize_pod_name(name),
        ),
        status=k8s_client.V1JobStatus(),
        spec=k8s_client.V1JobSpec(
            template=k8s_client.V1PodTemplateSpec(
                metadata=k8s_client.V1ObjectMeta(labels=pod_labels),
                spec=k8s_client.V1PodSpec(
                    containers=[
                        k8s_client.V1Container(
                            name=container_name,
                            image=container_image,
                            command=command,
                        ),
                    ],
                    service_account_name=service_account_name,
                    restart_policy=RestartPolicy.NEVER.value,
                ),
            )
        ),
    )


def is_inside_cluster() -> bool:
    """Whether current running environment is inside the kubernetes cluster."""
    return _factory.inside_cluster


def is_inside_kfp() -> bool:
    """Whether current running environment is inside the KFP runtime."""
    return (
        is_inside_cluster()
        and KFP_POD_NAME in os.environ
        and KFP_NAMESPACE in os.environ
    )


def get_kfp_namespace() -> str:
    """Get kubernetes namespace for the KFP.
    Raises:
      RuntimeError: If KFP pod cannot be determined from the environment, i.e.
          this program is not running inside the KFP.
    Returns:
      The namespace of the KFP app, to which the pod this program is running on
      belongs.
    """
    try:
        return os.environ[KFP_NAMESPACE]
    except KeyError:
        raise RuntimeError(
            "Cannot determine KFP namespace from the environment."
        )


def get_current_kfp_pod(client: k8s_client.CoreV1Api) -> k8s_client.V1Pod:
    """Get manifest of the KFP pod in which this program is running.
    Args:
      client: A kubernetes CoreV1Api client.
    Raises:
      RuntimeError: If KFP pod cannot be determined from the environment, i.e.
          this program is not running inside the KFP.
    Returns:
      The manifest of the pod this program is running on.
    """
    try:
        namespace = os.environ[KFP_NAMESPACE]
        pod_name = os.environ[KFP_POD_NAME]
        return client.read_namespaced_pod(name=pod_name, namespace=namespace)
    except KeyError:
        raise RuntimeError("Cannot determine KFP pod from the environment.")


def get_pod(
    core_api: k8s_client.CoreV1Api, pod_name: str, namespace: str
) -> Optional[k8s_client.V1Pod]:
    """Get a pod from Kubernetes metadata API.
    Args:
      core_api: Client of Core V1 API of Kubernetes API.
      pod_name: The name of the Pod.
      namespace: The namespace of the Pod.
    Returns:
      The found Pod object. None if it's not found.
    Raises:
      RuntimeError: When it sees unexpected errors from Kubernetes API.
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
    condition_description: str,
    timeout_sec: int = 0,
    exponential_backoff: bool = False,
) -> k8s_client.V1Pod:
    """Wait for a Pod to meet an exit condition.
    Args:
      core_api: Client of Core V1 API of Kubernetes API.
      pod_name: The name of the Pod.
      namespace: The namespace of the Pod.
      exit_condition_lambda: A lambda which will be called intervally to wait for
        a Pod to exit. The function returns True to exit.
      condition_description: The description of the exit condition which will be
        set in the error message if the wait times out.
      timeout_sec: Timeout in seconds to wait for pod to reach exit condition, or
        0 to wait for an unlimited duration. Defaults to unlimited.
      exponential_backoff: Whether to use exponential back off for polling.
        Defaults to False.
    Returns:
      The Pod object which meets the exit condition.
    Raises:
      RuntimeError: when the function times out.
    """
    start_time = datetime.datetime.utcnow()
    # Link to exponential back-off algorithm used here:
    # https://cloud.google.com/storage/docs/exponential-backoff
    backoff_interval = 1
    maximum_backoff = 32
    while True:
        resp = get_pod(core_api, pod_name, namespace)
        logging.info(resp.status.phase)
        if exit_condition_lambda(resp):
            return resp
        elapse_time = datetime.datetime.utcnow() - start_time
        if elapse_time.seconds >= timeout_sec and timeout_sec != 0:
            raise RuntimeError(
                'Pod "%s:%s" does not reach "%s" within %s seconds.'
                % (namespace, pod_name, condition_description, timeout_sec)
            )
        time.sleep(backoff_interval)
        if exponential_backoff and backoff_interval < maximum_backoff:
            backoff_interval *= 2
