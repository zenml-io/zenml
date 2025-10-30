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
#
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

import enum
import functools
import json
import re
import time
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    TypeVar,
    cast,
)

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException

from zenml.integrations.kubernetes.constants import (
    STEP_NAME_ANNOTATION_KEY,
)
from zenml.integrations.kubernetes.manifest_utils import (
    build_namespace_manifest,
    build_role_binding_manifest_for_service_account,
    build_secret_manifest,
    build_service_account_manifest,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.logger import get_logger
from zenml.utils.time_utils import utc_now

if TYPE_CHECKING:
    from zenml.config.resource_settings import ResourceSettings

logger = get_logger(__name__)

R = TypeVar("R")

MIB_TO_GIB = 1024  # MiB to GiB conversion factor


# This is to fix a bug in the kubernetes client which has some wrong
# client-side validations that means the `on_exit_codes` field is
# unusable. See https://github.com/kubernetes-client/python/issues/2056
class PatchedFailurePolicyRule(k8s_client.V1PodFailurePolicyRule):  # type: ignore[misc]
    """Patched failure policy rule."""

    @property
    def on_pod_conditions(self):  # type: ignore[no-untyped-def]
        """On pod conditions.

        Returns:
            On pod conditions.
        """
        return self._on_pod_conditions

    @on_pod_conditions.setter
    def on_pod_conditions(self, on_pod_conditions):  # type: ignore[no-untyped-def]
        """On pod conditions.

        Args:
            on_pod_conditions: On pod conditions.
        """
        self._on_pod_conditions = on_pod_conditions


k8s_client.V1PodFailurePolicyRule = PatchedFailurePolicyRule
k8s_client.models.V1PodFailurePolicyRule = PatchedFailurePolicyRule


class PodPhase(enum.Enum):
    """Phase of the Kubernetes pod.

    Pod phases are defined in
    https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-phase.
    """

    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"


class JobStatus(enum.Enum):
    """Status of a Kubernetes job."""

    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"


def is_inside_kubernetes() -> bool:
    """Check whether we are inside a Kubernetes cluster or on a remote host.

    Returns:
        True if inside a Kubernetes cluster, else False.
    """
    try:
        k8s_config.load_incluster_config()
        return True
    except k8s_config.ConfigException:
        return False


def load_kube_config(
    incluster: bool = False, context: Optional[str] = None
) -> None:
    """Load the Kubernetes client config.

    Args:
        incluster: Whether to load the in-cluster config.
        context: Name of the Kubernetes context. If not provided, uses the
            currently active context. Will be ignored if `incluster` is True.
    """
    if incluster:
        k8s_config.load_incluster_config()
    else:
        k8s_config.load_kube_config(context=context)


def sanitize_label(label: str) -> str:
    """Sanitize a label for a Kubernetes resource.

    Args:
        label: The label to sanitize.

    Returns:
        The sanitized label.
    """
    # https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#rfc-1035-label-names
    label = re.sub(r"[^a-z0-9-]", "-", label.lower())
    label = re.sub(r"^[-]+", "", label)
    label = re.sub(r"[-]+", "-", label)
    label = label[:63]
    # Remove trailing dashes after truncation to make sure we end with an
    # alphanumeric character
    label = re.sub(r"[-]+$", "", label)

    return label


def pod_is_not_pending(pod: k8s_client.V1Pod) -> bool:
    """Check if pod status is not 'Pending'.

    Args:
        pod: Kubernetes pod.

    Returns:
        False if the pod status is 'Pending' else True.
    """
    return pod.status.phase != PodPhase.PENDING.value  # type: ignore[no-any-return]


def pod_failed(pod: k8s_client.V1Pod) -> bool:
    """Check if pod status is 'Failed'.

    Args:
        pod: Kubernetes pod.

    Returns:
        True if pod status is 'Failed' else False.
    """
    return pod.status.phase == PodPhase.FAILED.value  # type: ignore[no-any-return]


def pod_is_done(pod: k8s_client.V1Pod) -> bool:
    """Check if pod status is 'Succeeded'.

    Args:
        pod: Kubernetes pod.

    Returns:
        True if pod status is 'Succeeded' else False.
    """
    return pod.status.phase == PodPhase.SUCCEEDED.value  # type: ignore[no-any-return]


def get_pod(
    core_api: k8s_client.CoreV1Api, pod_name: str, namespace: str
) -> Optional[k8s_client.V1Pod]:
    """Get a pod from Kubernetes metadata API.

    Args:
        core_api: Client of `CoreV1Api` of Kubernetes API.
        pod_name: The name of the pod.
        namespace: The namespace of the pod.

    Raises:
        RuntimeError: When it sees unexpected errors from Kubernetes API.

    Returns:
        The found pod object. None if it's not found.
    """
    try:
        return retry_on_api_exception(core_api.read_namespaced_pod)(
            name=pod_name, namespace=namespace
        )
    except k8s_client.rest.ApiException as e:
        if e.status == 404:
            return None
        raise RuntimeError from e


def wait_pod(
    kube_client_fn: Callable[[], k8s_client.ApiClient],
    pod_name: str,
    namespace: str,
    exit_condition_lambda: Callable[[k8s_client.V1Pod], bool],
    timeout_sec: int = 0,
    exponential_backoff: bool = False,
    stream_logs: bool = False,
) -> k8s_client.V1Pod:
    """Wait for a pod to meet an exit condition.

    Args:
        kube_client_fn: the kube client fn is a function that is called
            periodically and is used to get a `CoreV1Api` client for
            the Kubernetes API. It should cache the client to avoid
            unnecessary overhead but should also instantiate a new client if
            the previous one is using credentials that are about to expire.
        pod_name: The name of the pod.
        namespace: The namespace of the pod.
        exit_condition_lambda: A lambda
            which will be called periodically to wait for a pod to exit. The
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
        The pod object which meets the exit condition.
    """
    start_time = utc_now()

    # Link to exponential back-off algorithm used here:
    # https://cloud.google.com/storage/docs/exponential-backoff
    backoff_interval = 1
    maximum_backoff = 32

    logged_lines = 0

    while True:
        kube_client = kube_client_fn()
        core_api = k8s_client.CoreV1Api(kube_client)

        resp = get_pod(core_api, pod_name, namespace)

        if resp is None:
            raise RuntimeError(f"Pod `{namespace}:{pod_name}` not found.")

        # Stream logs to `zenml.logger.info()`.
        # TODO: can we do this without parsing all logs every time?
        if stream_logs and pod_is_not_pending(resp):
            try:
                response = core_api.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=namespace,
                    _preload_content=False,
                )
            except ApiException as e:
                logger.error(f"Error reading pod logs: {e}. Retrying...")
            else:
                raw_data = response.data
                decoded_log = raw_data.decode("utf-8", errors="replace")
                logs = decoded_log.splitlines()
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
        elapse_time = utc_now() - start_time
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
    """Wrap a Kubernetes function to handle creation if already exists.

    Args:
        create_fn: Kubernetes function to be wrapped.

    Returns:
        Wrapped Kubernetes function.

    Raises:
        ApiException: If an API error occurs.
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


def create_edit_service_account(
    core_api: k8s_client.CoreV1Api,
    rbac_api: k8s_client.RbacAuthorizationV1Api,
    service_account_name: str,
    namespace: str,
    role_binding_name: str = "zenml-edit",
) -> None:
    """Create a new Kubernetes service account with "edit" rights.

    Args:
        core_api: Client of Core V1 API of Kubernetes API.
        rbac_api: Client of Rbac Authorization V1 API of Kubernetes API.
        service_account_name: Name of the service account.
        namespace: Kubernetes namespace. Defaults to "default".
        role_binding_name: Name of the role binding. Defaults to "zenml-edit".
    """
    rb_manifest = build_role_binding_manifest_for_service_account(
        name=role_binding_name,
        role_name="edit",
        service_account_name=service_account_name,
        namespace=namespace,
    )
    _if_not_exists(rbac_api.create_namespaced_role_binding)(
        namespace=namespace, body=rb_manifest
    )

    sa_manifest = build_service_account_manifest(
        name=service_account_name, namespace=namespace
    )
    _if_not_exists(core_api.create_namespaced_service_account)(
        namespace=namespace,
        body=sa_manifest,
    )


def create_namespace(core_api: k8s_client.CoreV1Api, namespace: str) -> None:
    """Create a Kubernetes namespace.

    Args:
        core_api: Client of Core V1 API of Kubernetes API.
        namespace: Kubernetes namespace. Defaults to "default".
    """
    manifest = build_namespace_manifest(namespace)
    _if_not_exists(core_api.create_namespace)(body=manifest)


def create_secret(
    core_api: k8s_client.CoreV1Api,
    namespace: str,
    secret_name: str,
    data: Dict[str, Optional[str]],
) -> None:
    """Create a Kubernetes secret.

    Args:
        core_api: Client of Core V1 API of Kubernetes API.
        namespace: The namespace in which to create the secret.
        secret_name: The name of the secret to create.
        data: The secret data.
    """
    core_api.create_namespaced_secret(
        namespace=namespace,
        body=build_secret_manifest(name=secret_name, data=data),
    )


def update_secret(
    core_api: k8s_client.CoreV1Api,
    namespace: str,
    secret_name: str,
    data: Dict[str, Optional[str]],
) -> None:
    """Update a Kubernetes secret.

    Args:
        core_api: Client of Core V1 API of Kubernetes API.
        namespace: The namespace in which to update the secret.
        secret_name: The name of the secret to update.
        data: The secret data. If the value is None, the key will be removed
            from the secret.
    """
    core_api.patch_namespaced_secret(
        namespace=namespace,
        name=secret_name,
        body=build_secret_manifest(name=secret_name, data=data),
    )


def create_or_update_secret(
    core_api: k8s_client.CoreV1Api,
    namespace: str,
    secret_name: str,
    data: Dict[str, Optional[str]],
) -> None:
    """Create a Kubernetes secret if it doesn't exist, or update it if it does.

    Args:
        core_api: Client of Core V1 API of Kubernetes API.
        namespace: The namespace in which to create or update the secret.
        secret_name: The name of the secret to create or update.
        data: The secret data. If the value is None, the key will be removed
            from the secret.

    Raises:
        ApiException: If the secret creation failed for any reason other than
            the secret already existing.
    """
    try:
        create_secret(core_api, namespace, secret_name, data)
    except ApiException as e:
        if e.status != 409:
            raise
        update_secret(core_api, namespace, secret_name, data)


def delete_secret(
    core_api: k8s_client.CoreV1Api,
    namespace: str,
    secret_name: str,
) -> None:
    """Delete a Kubernetes secret.

    Args:
        core_api: Client of Core V1 API of Kubernetes API.
        namespace: The namespace in which to delete the secret.
        secret_name: The name of the secret to delete.
    """
    core_api.delete_namespaced_secret(
        name=secret_name,
        namespace=namespace,
    )


def create_and_wait_for_pod_to_start(
    core_api: k8s_client.CoreV1Api,
    pod_display_name: str,
    pod_name: str,
    pod_manifest: k8s_client.V1Pod,
    namespace: str,
    startup_max_retries: int,
    startup_failure_delay: float,
    startup_failure_backoff: float,
    startup_timeout: float,
) -> None:
    """Create a pod and wait for it to reach a desired state.

    Args:
        core_api: Client of Core V1 API of Kubernetes API.
        pod_display_name: The display name of the pod to use in logs.
        pod_name: The name of the pod to create.
        pod_manifest: The manifest of the pod to create.
        namespace: The namespace in which to create the pod.
        startup_max_retries: The maximum number of retries for the pod startup.
        startup_failure_delay: The delay between retries for the pod startup.
        startup_failure_backoff: The backoff factor for the pod startup.
        startup_timeout: The maximum time to wait for the pod to start.

    Raises:
        TimeoutError: If the pod is still in a pending state after the maximum
            wait time has elapsed.
        Exception: If the pod fails to start after the maximum number of
            retries.
    """
    retries = 0

    while retries < startup_max_retries:
        try:
            # Create and run pod.
            core_api.create_namespaced_pod(
                namespace=namespace,
                body=pod_manifest,
            )
            break
        except Exception as e:
            retries += 1
            if retries < startup_max_retries:
                logger.debug(f"The {pod_display_name} failed to start: {e}")
                message = ""
                try:
                    if isinstance(e, ApiException) and e.body:
                        exception_body = json.loads(e.body)
                        message = exception_body.get("message", "")
                except Exception:
                    pass
                logger.error(
                    f"Failed to create {pod_display_name}. "
                    f"Retrying in {startup_failure_delay} seconds..."
                    "\nReason: " + message
                    if message
                    else ""
                )
                time.sleep(startup_failure_delay)
                startup_failure_delay *= startup_failure_backoff
            else:
                logger.error(
                    f"Failed to create {pod_display_name} after "
                    f"{startup_max_retries} retries. Exiting."
                )
                raise

    # Wait for pod to start
    logger.info(f"Waiting for {pod_display_name} to start...")
    max_wait = startup_timeout
    total_wait: float = 0
    delay = startup_failure_delay
    while True:
        pod = get_pod(
            core_api=core_api,
            pod_name=pod_name,
            namespace=namespace,
        )
        if not pod or pod_is_not_pending(pod):
            break
        if total_wait >= max_wait:
            # Have to delete the pending pod so it doesn't start running
            # later on.
            try:
                core_api.delete_namespaced_pod(
                    name=pod_name,
                    namespace=namespace,
                )
            except Exception:
                pass
            raise TimeoutError(
                f"The {pod_display_name} is still in a pending state "
                f"after {total_wait} seconds. Exiting."
            )

        if total_wait + delay > max_wait:
            delay = max_wait - total_wait
        total_wait += delay
        time.sleep(delay)
        delay *= startup_failure_backoff


def get_pod_owner_references(
    core_api: k8s_client.CoreV1Api, pod_name: str, namespace: str
) -> List[k8s_client.V1OwnerReference]:
    """Get owner references for a pod.

    Args:
        core_api: Kubernetes CoreV1Api client.
        pod_name: Name of the pod.
        namespace: Kubernetes namespace.

    Returns:
        List of owner references.
    """
    pod = get_pod(core_api=core_api, pod_name=pod_name, namespace=namespace)

    if not pod or not pod.metadata or not pod.metadata.owner_references:
        return []

    return cast(
        List[k8s_client.V1OwnerReference], pod.metadata.owner_references
    )


def retry_on_api_exception(
    func: Callable[..., R],
    max_retries: int = 3,
    delay: float = 1,
    backoff: float = 1,
    fail_on_status_codes: Tuple[int, ...] = (404,),
) -> Callable[..., R]:
    """Retry a function on API exceptions.

    Args:
        func: The function to retry.
        max_retries: The maximum number of retries.
        delay: The delay between retries.
        backoff: The backoff factor.
        fail_on_status_codes: The status codes to fail on immediately.

    Returns:
        The wrapped function with retry logic.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> R:
        _delay = delay
        retries = 0
        while retries <= max_retries:
            try:
                return func(*args, **kwargs)
            except ApiException as e:
                if e.status in fail_on_status_codes:
                    raise

                retries += 1
                if retries <= max_retries:
                    logger.warning("Error calling %s: %s.", func.__name__, e)
                    time.sleep(_delay)
                    _delay *= backoff
                else:
                    raise

        raise RuntimeError(
            f"Failed to call {func.__name__} after {max_retries} retries."
        )

    return wrapper


def create_job(
    batch_api: k8s_client.BatchV1Api,
    namespace: str,
    job_manifest: k8s_client.V1Job,
) -> None:
    """Create a Kubernetes job.

    Args:
        batch_api: Kubernetes batch api.
        namespace: Kubernetes namespace.
        job_manifest: The manifest of the job to create.
    """
    retry_on_api_exception(batch_api.create_namespaced_job)(
        namespace=namespace,
        body=job_manifest,
    )


def get_job(
    batch_api: k8s_client.BatchV1Api,
    namespace: str,
    job_name: str,
) -> k8s_client.V1Job:
    """Get a job by name.

    Args:
        batch_api: Kubernetes batch api.
        namespace: Kubernetes namespace.
        job_name: The name of the job to get.

    Returns:
        The job.
    """
    return retry_on_api_exception(batch_api.read_namespaced_job)(
        name=job_name, namespace=namespace
    )


def list_jobs(
    batch_api: k8s_client.BatchV1Api,
    namespace: str,
    label_selector: Optional[str] = None,
) -> k8s_client.V1JobList:
    """List jobs in a namespace.

    Args:
        batch_api: Kubernetes batch api.
        namespace: Kubernetes namespace.
        label_selector: The label selector to use.

    Returns:
        The job list.
    """
    return retry_on_api_exception(batch_api.list_namespaced_job)(
        namespace=namespace,
        label_selector=label_selector,
    )


def update_job(
    batch_api: k8s_client.BatchV1Api,
    namespace: str,
    job_name: str,
    annotations: Dict[str, str],
) -> k8s_client.V1Job:
    """Update a job.

    Args:
        batch_api: Kubernetes batch api.
        namespace: Kubernetes namespace.
        job_name: The name of the job to update.
        annotations: The annotations to update.

    Returns:
        The updated job.
    """
    return retry_on_api_exception(batch_api.patch_namespaced_job)(
        name=job_name,
        namespace=namespace,
        body={"metadata": {"annotations": annotations}},
    )


def is_step_job(job: k8s_client.V1Job) -> bool:
    """Check if a job is a step job.

    Args:
        job: The job to check.

    Returns:
        Whether the job is a step job.
    """
    if not job.metadata or not job.metadata.annotations:
        return False

    return STEP_NAME_ANNOTATION_KEY in job.metadata.annotations


def get_container_status(
    pod: k8s_client.V1Pod, container_name: str
) -> Optional[k8s_client.V1ContainerState]:
    """Get the status of a container.

    Args:
        pod: The pod to get the container status for.
        container_name: The container name.

    Returns:
        The container status.
    """
    if not pod.status or not pod.status.container_statuses:
        return None

    for container_status in pod.status.container_statuses:
        if container_status.name == container_name:
            return container_status.state

    return None


def get_container_termination_reason(
    pod: k8s_client.V1Pod, container_name: str
) -> Optional[Tuple[int, str]]:
    """Get the termination reason for a container.

    Args:
        pod: The pod to get the termination reason for.
        container_name: The container name.

    Returns:
        The exit code and termination reason for the container.
    """
    container_state = get_container_status(pod, container_name)
    if not container_state or not container_state.terminated:
        return None

    return (
        container_state.terminated.exit_code,
        container_state.terminated.reason or "Unknown",
    )


def wait_for_job_to_finish(
    batch_api: k8s_client.BatchV1Api,
    core_api: k8s_client.CoreV1Api,
    namespace: str,
    job_name: str,
    backoff_interval: float = 1,
    maximum_backoff: float = 32,
    exponential_backoff: bool = False,
    fail_on_container_waiting_reasons: Optional[List[str]] = None,
    stream_logs: bool = True,
    container_name: Optional[str] = None,
) -> None:
    """Wait for a job to finish.

    Args:
        batch_api: Kubernetes BatchV1Api client.
        core_api: Kubernetes CoreV1Api client.
        namespace: Kubernetes namespace.
        job_name: Name of the job for which to wait.
        backoff_interval: The interval to wait between polling the job status.
        maximum_backoff: The maximum interval to wait between polling the job
            status.
        exponential_backoff: Whether to use exponential backoff.
        fail_on_container_waiting_reasons: List of container waiting reasons
            that will cause the job to fail.
        stream_logs: Whether to stream the job logs.
        container_name: Name of the container to stream logs from.

    Raises:
        RuntimeError: If the job failed or timed out.
    """
    logged_lines_per_pod: Dict[str, int] = defaultdict(int)
    finished_pods = set()

    while True:
        job: k8s_client.V1Job = retry_on_api_exception(
            batch_api.read_namespaced_job
        )(name=job_name, namespace=namespace)

        if job.status.conditions:
            for condition in job.status.conditions:
                if condition.type == "Complete" and condition.status == "True":
                    return
                if condition.type == "Failed" and condition.status == "True":
                    raise RuntimeError(
                        f"Job `{namespace}:{job_name}` failed: "
                        f"{condition.message}"
                    )

        if fail_on_container_waiting_reasons:
            pod_list: k8s_client.V1PodList = retry_on_api_exception(
                core_api.list_namespaced_pod
            )(
                namespace=namespace,
                label_selector=f"job-name={job_name}",
                field_selector="status.phase=Pending",
            )
            for pod in pod_list.items:
                container_state = get_container_status(
                    pod, container_name or "main"
                )

                if (
                    container_state
                    and (waiting_state := container_state.waiting)
                    and waiting_state.reason
                    in fail_on_container_waiting_reasons
                ):
                    retry_on_api_exception(batch_api.delete_namespaced_job)(
                        name=job_name,
                        namespace=namespace,
                        propagation_policy="Foreground",
                    )
                    raise RuntimeError(
                        f"Job `{namespace}:{job_name}` failed: "
                        f"Detected container in state "
                        f"{waiting_state.reason}"
                    )

        if stream_logs:
            try:
                pod_list = core_api.list_namespaced_pod(
                    namespace=namespace,
                    label_selector=f"job-name={job_name}",
                )
            except ApiException as e:
                logger.error("Error fetching pods: %s.", e)
                pod_list = []
            else:
                # Sort pods by creation timestamp, oldest first
                pod_list.items.sort(
                    key=lambda pod: pod.metadata.creation_timestamp,
                )

            for pod in pod_list.items:
                pod_name = pod.metadata.name
                pod_status = pod.status.phase

                if pod_name in finished_pods:
                    # We've already streamed all logs for this pod, so we can
                    # skip it.
                    continue

                if pod_status == PodPhase.PENDING.value:
                    # The pod is still pending, so we can't stream logs for it
                    # yet.
                    continue

                if pod_status in [
                    PodPhase.SUCCEEDED.value,
                    PodPhase.FAILED.value,
                ]:
                    finished_pods.add(pod_name)

                containers = pod.spec.containers
                if not container_name:
                    container_name = containers[0].name

                try:
                    response = core_api.read_namespaced_pod_log(
                        name=pod_name,
                        namespace=namespace,
                        container=container_name,
                        _preload_content=False,
                    )
                except ApiException as e:
                    logger.error("Error reading pod logs: %s.", e)
                else:
                    raw_data = response.data
                    decoded_log = raw_data.decode("utf-8", errors="replace")
                    logs = decoded_log.splitlines()
                    logged_lines = logged_lines_per_pod[pod_name]
                    if len(logs) > logged_lines:
                        for line in logs[logged_lines:]:
                            logger.info(line)
                        logged_lines_per_pod[pod_name] = len(logs)

        time.sleep(backoff_interval)
        if exponential_backoff and backoff_interval < maximum_backoff:
            backoff_interval *= 2


def check_job_status(
    batch_api: k8s_client.BatchV1Api,
    core_api: k8s_client.CoreV1Api,
    namespace: str,
    job_name: str,
    fail_on_container_waiting_reasons: Optional[List[str]] = None,
    container_name: Optional[str] = None,
) -> Tuple[JobStatus, Optional[str]]:
    """Check the status of a job.

    Args:
        batch_api: Kubernetes BatchV1Api client.
        core_api: Kubernetes CoreV1Api client.
        namespace: Kubernetes namespace.
        job_name: Name of the job for which to wait.
        fail_on_container_waiting_reasons: List of container waiting reasons
            that will cause the job to fail.
        container_name: Name of the container to check for failure.

    Returns:
        The status of the job and an error message if the job failed.
    """
    job: k8s_client.V1Job = retry_on_api_exception(
        batch_api.read_namespaced_job
    )(name=job_name, namespace=namespace)

    if job.status.conditions:
        for condition in job.status.conditions:
            if condition.type == "Complete" and condition.status == "True":
                return JobStatus.SUCCEEDED, None
            if condition.type == "Failed" and condition.status == "True":
                error_message = condition.message or "Unknown"
                container_failure_reason = None
                try:
                    pods = core_api.list_namespaced_pod(
                        label_selector=f"job-name={job_name}",
                        namespace=namespace,
                    ).items
                    # Sort pods by creation timestamp, oldest first
                    pods.sort(
                        key=lambda pod: pod.metadata.creation_timestamp,
                    )
                    if pods:
                        if (
                            termination_reason
                            := get_container_termination_reason(
                                pods[-1], container_name or "main"
                            )
                        ):
                            exit_code, reason = termination_reason
                            if exit_code != 0:
                                container_failure_reason = (
                                    f"{reason}, exit_code={exit_code}"
                                )
                except Exception:
                    pass

                if container_failure_reason:
                    error_message += f" (container failure reason: {container_failure_reason})"

                return JobStatus.FAILED, error_message

    if fail_on_container_waiting_reasons:
        pod_list: k8s_client.V1PodList = retry_on_api_exception(
            core_api.list_namespaced_pod
        )(
            namespace=namespace,
            label_selector=f"job-name={job_name}",
            field_selector="status.phase=Pending",
        )
        for pod in pod_list.items:
            container_state = get_container_status(
                pod, container_name or "main"
            )

            if (
                container_state
                and (waiting_state := container_state.waiting)
                and waiting_state.reason in fail_on_container_waiting_reasons
            ):
                retry_on_api_exception(batch_api.delete_namespaced_job)(
                    name=job_name,
                    namespace=namespace,
                    propagation_policy="Foreground",
                )
                error_message = (
                    f"Detected container in state `{waiting_state.reason}`"
                )
                return JobStatus.FAILED, error_message

    return JobStatus.RUNNING, None


def create_config_map(
    core_api: k8s_client.CoreV1Api,
    namespace: str,
    name: str,
    data: Dict[str, str],
) -> None:
    """Create a Kubernetes config map.

    Args:
        core_api: Kubernetes CoreV1Api client.
        namespace: Kubernetes namespace.
        name: Name of the config map to create.
        data: Data to store in the config map.
    """
    retry_on_api_exception(core_api.create_namespaced_config_map)(
        namespace=namespace,
        body=k8s_client.V1ConfigMap(metadata={"name": name}, data=data),
    )


def update_config_map(
    core_api: k8s_client.CoreV1Api,
    namespace: str,
    name: str,
    data: Dict[str, str],
) -> None:
    """Update a Kubernetes config map.

    Args:
        core_api: Kubernetes CoreV1Api client.
        namespace: Kubernetes namespace.
        name: Name of the config map to update.
        data: Data to store in the config map.
    """
    retry_on_api_exception(core_api.patch_namespaced_config_map)(
        namespace=namespace,
        name=name,
        body=k8s_client.V1ConfigMap(data=data),
    )


def get_config_map(
    core_api: k8s_client.CoreV1Api,
    namespace: str,
    name: str,
) -> k8s_client.V1ConfigMap:
    """Get a Kubernetes config map.

    Args:
        core_api: Kubernetes CoreV1Api client.
        namespace: Kubernetes namespace.
        name: Name of the config map to get.

    Returns:
        The config map.
    """
    return retry_on_api_exception(core_api.read_namespaced_config_map)(
        namespace=namespace,
        name=name,
    )


def delete_config_map(
    core_api: k8s_client.CoreV1Api,
    namespace: str,
    name: str,
) -> None:
    """Delete a Kubernetes config map.

    Args:
        core_api: Kubernetes CoreV1Api client.
        namespace: Kubernetes namespace.
        name: Name of the config map to delete.
    """
    retry_on_api_exception(core_api.delete_namespaced_config_map)(
        namespace=namespace,
        name=name,
    )


def get_parent_job_name(
    core_api: k8s_client.CoreV1Api,
    pod_name: str,
    namespace: str,
) -> Optional[str]:
    """Get the name of the job that created a pod.

    Args:
        core_api: Kubernetes CoreV1Api client.
        pod_name: Name of the pod.
        namespace: Kubernetes namespace.

    Returns:
        The name of the job that created the pod, or None if the pod is not
        associated with a job.
    """
    pod = get_pod(core_api, pod_name=pod_name, namespace=namespace)
    if (
        pod
        and pod.metadata
        and pod.metadata.labels
        and (job_name := pod.metadata.labels.get("job-name", None))
    ):
        return cast(str, job_name)

    return None


def apply_default_resource_requests(
    memory: str,
    cpu: Optional[str] = None,
    pod_settings: Optional[KubernetesPodSettings] = None,
) -> KubernetesPodSettings:
    """Applies default resource requests to a pod settings object.

    Args:
        memory: The memory resource request.
        cpu: The CPU resource request.
        pod_settings: The pod settings to update. A new one will be created
            if not provided.

    Returns:
        The new or updated pod settings.
    """
    resources = {
        "requests": {"memory": memory},
    }
    if cpu:
        resources["requests"]["cpu"] = cpu
    if not pod_settings:
        pod_settings = KubernetesPodSettings(resources=resources)
    elif not pod_settings.resources:
        # We can't update the pod settings in place (because it's a frozen
        # pydantic model), so we have to create a new one.
        pod_settings = KubernetesPodSettings(
            **pod_settings.model_dump(exclude_unset=True),
            resources=resources,
        )
    else:
        set_requests = pod_settings.resources.get("requests", {})
        resources["requests"].update(set_requests)
        pod_settings.resources["requests"] = resources["requests"]

    return pod_settings


# ============================================================================
# Waiting and Monitoring Functions
# ============================================================================


def wait_for_service_deletion(
    core_api: k8s_client.CoreV1Api,
    service_name: str,
    namespace: str,
    timeout: int = 60,
) -> None:
    """Wait for a Service to be fully deleted.

    Polls the Service until it returns 404, indicating deletion is complete.
    This prevents race conditions when recreating Services with immutable
    field changes.

    Args:
        core_api: Kubernetes CoreV1Api client.
        service_name: Name of the Service to wait for.
        namespace: Namespace containing the Service.
        timeout: Maximum time to wait in seconds. Default is 60.

    Raises:
        RuntimeError: If Service is not deleted within timeout.
        ApiException: If an API error occurs (other than 404).
    """
    start_time = time.time()
    backoff = 1.0
    max_backoff = 5.0

    while time.time() - start_time < timeout:
        try:
            core_api.read_namespaced_service(
                name=service_name,
                namespace=namespace,
            )
            logger.debug(
                f"Waiting for Service '{service_name}' deletion to complete..."
            )
            time.sleep(backoff)
            backoff = min(backoff * 1.5, max_backoff)
        except ApiException as e:
            if e.status == 404:
                logger.debug(f"Service '{service_name}' deletion confirmed.")
                return
            raise

    raise RuntimeError(
        f"Timeout waiting for Service '{service_name}' to be deleted after "
        f"{timeout} seconds. Service may have finalizers or the cluster may "
        f"be slow. Check Service status with kubectl."
    )


def wait_for_deployment_ready(
    apps_api: k8s_client.AppsV1Api,
    deployment_name: str,
    namespace: str,
    timeout: int,
    check_interval: float = 2.0,
) -> None:
    """Wait for a Deployment to become ready.

    Args:
        apps_api: Kubernetes AppsV1Api client.
        deployment_name: Name of the Deployment to wait for.
        namespace: Namespace containing the Deployment.
        timeout: Maximum time to wait in seconds.
        check_interval: Seconds between status checks. Default is 2.0.

    Raises:
        RuntimeError: If deployment doesn't become ready within timeout
            or encounters a failure condition.
    """
    logger.info(
        f"Waiting up to {timeout}s for deployment '{deployment_name}' "
        f"to become ready..."
    )

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            deployment = apps_api.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
            )

            if deployment.status:
                available_replicas = deployment.status.available_replicas or 0
                replicas = deployment.spec.replicas or 0

                if available_replicas == replicas and replicas > 0:
                    logger.info(
                        f"Deployment '{deployment_name}' is ready with "
                        f"{available_replicas}/{replicas} replicas available."
                    )
                    return

                if deployment.status.conditions:
                    for condition in deployment.status.conditions:
                        if (
                            condition.type == "Progressing"
                            and condition.status == "False"
                            and condition.reason == "ProgressDeadlineExceeded"
                        ):
                            raise RuntimeError(
                                f"Deployment '{deployment_name}' failed to "
                                f"progress: {condition.message}"
                            )

                logger.debug(
                    f"Deployment '{deployment_name}' status: "
                    f"{available_replicas}/{replicas} replicas available"
                )

        except ApiException as e:
            if e.status != 404:
                raise RuntimeError(
                    f"Error checking deployment status: {e}"
                ) from e

        time.sleep(check_interval)

    raise RuntimeError(
        f"Deployment '{deployment_name}' did not become ready "
        f"within {timeout} seconds"
    )


def wait_for_loadbalancer_ip(
    core_api: k8s_client.CoreV1Api,
    service_name: str,
    namespace: str,
    timeout: int = 150,
    check_interval: float = 2.0,
) -> Optional[str]:
    """Wait for a LoadBalancer service to get an external IP.

    Args:
        core_api: Kubernetes CoreV1Api client.
        service_name: Name of the LoadBalancer Service.
        namespace: Namespace containing the Service.
        timeout: Maximum time to wait in seconds. Default is 150.
        check_interval: Seconds between status checks. Default is 2.0.

    Returns:
        The external IP/hostname if assigned, None if timeout reached.
        Note: Returns None on timeout rather than raising to allow
        deployment to continue (IP might be assigned later).
    """
    logger.info(
        f"Waiting up to {timeout}s for LoadBalancer service '{service_name}' "
        f"to get an external IP..."
    )

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            service = core_api.read_namespaced_service(
                name=service_name,
                namespace=namespace,
            )

            if (
                service.status
                and service.status.load_balancer
                and service.status.load_balancer.ingress
            ):
                ingress = service.status.load_balancer.ingress[0]
                external_ip: Optional[str] = ingress.ip or ingress.hostname
                if external_ip:
                    logger.info(
                        f"LoadBalancer service '{service_name}' received "
                        f"external IP/hostname: {external_ip}"
                    )
                    return str(external_ip)

            logger.debug(
                f"LoadBalancer service '{service_name}' is still waiting "
                f"for external IP assignment..."
            )

        except ApiException as e:
            if e.status != 404:
                logger.error(f"Error checking service status: {e}")
                return None

        time.sleep(check_interval)

    logger.warning(
        f"LoadBalancer service '{service_name}' did not receive an "
        f"external IP within {timeout} seconds. The deployment is still "
        f"running, but you may need to check the service status later."
    )
    return None


def check_pod_failure_status(
    pod: k8s_client.V1Pod,
    restart_error_threshold: int = 5,
) -> Optional[str]:
    """Check if a pod has container failures indicating deployment errors.

    Args:
        pod: The Kubernetes pod to inspect.
        restart_error_threshold: Number of restarts to consider as an error.
            Default is 5.

    Returns:
        Error reason if pod has failures, None otherwise.
    """
    if not pod.status or not pod.status.container_statuses:
        return None

    # Error reasons that indicate permanent or recurring failures
    ERROR_REASONS = {
        "CrashLoopBackOff",
        "ErrImagePull",
        "ImagePullBackOff",
        "CreateContainerConfigError",
        "InvalidImageName",
        "CreateContainerError",
        "RunContainerError",
    }

    for container_status in pod.status.container_statuses:
        if container_status.state and container_status.state.waiting:
            reason = container_status.state.waiting.reason
            if reason in ERROR_REASONS:
                message = container_status.state.waiting.message or ""
                return f"{reason}: {message}".strip(": ")

        if container_status.state and container_status.state.terminated:
            reason = container_status.state.terminated.reason
            exit_code = container_status.state.terminated.exit_code
            if exit_code and exit_code != 0:
                message = container_status.state.terminated.message or ""
                return f"Container terminated with exit code {exit_code}: {reason} {message}".strip()

        if (
            container_status.last_state
            and container_status.last_state.terminated
        ):
            restart_count = container_status.restart_count or 0
            if restart_count > restart_error_threshold:
                reason = (
                    container_status.last_state.terminated.reason or "Error"
                )
                exit_code = container_status.last_state.terminated.exit_code
                return f"Container restarting ({restart_count} restarts): {reason} (exit code {exit_code})"

    return None


# ============================================================================
# Deployment Management Functions
# ============================================================================


def get_deployment(
    apps_api: k8s_client.AppsV1Api,
    name: str,
    namespace: str,
) -> Optional[k8s_client.V1Deployment]:
    """Get a Kubernetes Deployment.

    Args:
        apps_api: Kubernetes Apps V1 API client.
        name: Name of the deployment.
        namespace: Kubernetes namespace.

    Returns:
        The Deployment object, or None if not found.

    Raises:
        ApiException: If an API error occurs.
    """
    try:
        return retry_on_api_exception(
            apps_api.read_namespaced_deployment,
            fail_on_status_codes=(404,),
        )(name=name, namespace=namespace)
    except ApiException as e:
        if e.status == 404:
            return None
        raise


def create_deployment(
    apps_api: k8s_client.AppsV1Api,
    namespace: str,
    deployment_manifest: k8s_client.V1Deployment,
) -> k8s_client.V1Deployment:
    """Create a Kubernetes Deployment.

    Args:
        apps_api: Kubernetes Apps V1 API client.
        namespace: Kubernetes namespace.
        deployment_manifest: The Deployment manifest.

    Returns:
        The created Deployment.
    """
    return retry_on_api_exception(
        apps_api.create_namespaced_deployment,
        fail_on_status_codes=(404, 409),
    )(namespace=namespace, body=deployment_manifest)


def update_deployment(
    apps_api: k8s_client.AppsV1Api,
    name: str,
    namespace: str,
    deployment_manifest: k8s_client.V1Deployment,
) -> k8s_client.V1Deployment:
    """Update a Kubernetes Deployment.

    Args:
        apps_api: Kubernetes Apps V1 API client.
        name: Name of the deployment.
        namespace: Kubernetes namespace.
        deployment_manifest: The updated Deployment manifest.

    Returns:
        The updated Deployment.
    """
    return retry_on_api_exception(
        apps_api.patch_namespaced_deployment,
        fail_on_status_codes=(404,),
    )(name=name, namespace=namespace, body=deployment_manifest)


def delete_deployment(
    apps_api: k8s_client.AppsV1Api,
    name: str,
    namespace: str,
    propagation_policy: str = "Foreground",
) -> None:
    """Delete a Kubernetes Deployment.

    Args:
        apps_api: Kubernetes Apps V1 API client.
        name: Name of the deployment.
        namespace: Kubernetes namespace.
        propagation_policy: Deletion propagation policy.

    Raises:
        ApiException: If an API error occurs.
    """
    try:
        retry_on_api_exception(
            apps_api.delete_namespaced_deployment,
            fail_on_status_codes=(404,),
        )(
            name=name,
            namespace=namespace,
            propagation_policy=propagation_policy,
        )
    except ApiException as e:
        if e.status != 404:
            raise


# ============================================================================
# Service Management Functions
# ============================================================================


def get_service(
    core_api: k8s_client.CoreV1Api,
    name: str,
    namespace: str,
) -> Optional[k8s_client.V1Service]:
    """Get a Kubernetes Service.

    Args:
        core_api: Kubernetes Core V1 API client.
        name: Name of the service.
        namespace: Kubernetes namespace.

    Returns:
        The Service object, or None if not found.

    Raises:
        ApiException: If an API error occurs.
    """
    try:
        return retry_on_api_exception(
            core_api.read_namespaced_service,
            fail_on_status_codes=(404,),
        )(name=name, namespace=namespace)
    except ApiException as e:
        if e.status == 404:
            return None
        raise


def create_service(
    core_api: k8s_client.CoreV1Api,
    namespace: str,
    service_manifest: k8s_client.V1Service,
) -> k8s_client.V1Service:
    """Create a Kubernetes Service.

    Args:
        core_api: Kubernetes Core V1 API client.
        namespace: Kubernetes namespace.
        service_manifest: The Service manifest.

    Returns:
        The created Service.
    """
    return retry_on_api_exception(
        core_api.create_namespaced_service,
        fail_on_status_codes=(404, 409),
    )(namespace=namespace, body=service_manifest)


def update_service(
    core_api: k8s_client.CoreV1Api,
    name: str,
    namespace: str,
    service_manifest: k8s_client.V1Service,
) -> k8s_client.V1Service:
    """Update a Kubernetes Service.

    Args:
        core_api: Kubernetes Core V1 API client.
        name: Name of the service.
        namespace: Kubernetes namespace.
        service_manifest: The updated Service manifest.

    Returns:
        The updated Service.
    """
    return retry_on_api_exception(
        core_api.patch_namespaced_service,
        fail_on_status_codes=(404,),
    )(name=name, namespace=namespace, body=service_manifest)


def delete_service(
    core_api: k8s_client.CoreV1Api,
    name: str,
    namespace: str,
) -> None:
    """Delete a Kubernetes Service.

    Args:
        core_api: Kubernetes Core V1 API client.
        name: Name of the service.
        namespace: Kubernetes namespace.

    Raises:
        ApiException: If an API error occurs.
    """
    try:
        retry_on_api_exception(
            core_api.delete_namespaced_service,
            fail_on_status_codes=(404,),
        )(name=name, namespace=namespace)
    except ApiException as e:
        if e.status != 404:
            raise


def service_needs_recreate(
    existing_service: k8s_client.V1Service,
    new_manifest: k8s_client.V1Service,
) -> bool:
    """Check if a Service needs to be recreated due to immutable field changes.

    Args:
        existing_service: The existing Service from the cluster.
        new_manifest: The new Service manifest to apply.

    Returns:
        True if the Service needs to be deleted and recreated, False otherwise.
    """
    existing_type = existing_service.spec.type
    new_type = new_manifest.spec.type
    if existing_type != new_type:
        logger.debug(
            f"Service type changed from {existing_type} to {new_type}, "
            f"requires recreate"
        )
        return True

    # ClusterIP is immutable (except for "None" for headless services)
    existing_cluster_ip = existing_service.spec.cluster_ip
    new_cluster_ip = new_manifest.spec.cluster_ip
    if (
        existing_cluster_ip
        and new_cluster_ip
        and existing_cluster_ip != new_cluster_ip
        and existing_cluster_ip != "None"
        and new_cluster_ip != "None"
    ):
        logger.debug(
            f"Service clusterIP changed from {existing_cluster_ip} to "
            f"{new_cluster_ip}, requires recreate"
        )
        return True

    # NodePort values are immutable once assigned
    if existing_type == "NodePort" or new_type == "NodePort":
        existing_ports = existing_service.spec.ports or []
        new_ports = new_manifest.spec.ports or []

        # Build maps keyed by (port name/number, target port) -> node port
        existing_node_ports = {
            (p.name or str(p.port), p.target_port): p.node_port
            for p in existing_ports
            if p.node_port
        }
        new_node_ports = {
            (p.name or str(p.port), p.target_port): p.node_port
            for p in new_ports
            if p.node_port
        }

        for key, existing_node_port in existing_node_ports.items():
            if (
                key in new_node_ports
                and new_node_ports[key] != existing_node_port
            ):
                logger.debug(
                    f"Service nodePort changed for {key}, requires recreate"
                )
                return True

    return False


# ============================================================================
# Ingress Management Functions
# ============================================================================


def get_ingress(
    networking_api: k8s_client.NetworkingV1Api,
    name: str,
    namespace: str,
) -> Optional[k8s_client.V1Ingress]:
    """Get a Kubernetes Ingress.

    Args:
        networking_api: Kubernetes Networking V1 API client.
        name: Name of the ingress.
        namespace: Kubernetes namespace.

    Returns:
        The Ingress object, or None if not found.

    Raises:
        ApiException: If an API error occurs.
    """
    try:
        return retry_on_api_exception(
            networking_api.read_namespaced_ingress,
            fail_on_status_codes=(404,),
        )(name=name, namespace=namespace)
    except ApiException as e:
        if e.status == 404:
            return None
        raise


def create_ingress(
    networking_api: k8s_client.NetworkingV1Api,
    namespace: str,
    ingress_manifest: k8s_client.V1Ingress,
) -> k8s_client.V1Ingress:
    """Create a Kubernetes Ingress.

    Args:
        networking_api: Kubernetes Networking V1 API client.
        namespace: Kubernetes namespace.
        ingress_manifest: The Ingress manifest.

    Returns:
        The created Ingress.
    """
    return retry_on_api_exception(
        networking_api.create_namespaced_ingress,
        fail_on_status_codes=(404, 409),
    )(namespace=namespace, body=ingress_manifest)


def update_ingress(
    networking_api: k8s_client.NetworkingV1Api,
    name: str,
    namespace: str,
    ingress_manifest: k8s_client.V1Ingress,
) -> k8s_client.V1Ingress:
    """Update a Kubernetes Ingress.

    Args:
        networking_api: Kubernetes Networking V1 API client.
        name: Name of the ingress.
        namespace: Kubernetes namespace.
        ingress_manifest: The updated Ingress manifest.

    Returns:
        The updated Ingress.
    """
    return retry_on_api_exception(
        networking_api.patch_namespaced_ingress,
        fail_on_status_codes=(404,),
    )(name=name, namespace=namespace, body=ingress_manifest)


def delete_ingress(
    networking_api: k8s_client.NetworkingV1Api,
    name: str,
    namespace: str,
) -> None:
    """Delete a Kubernetes Ingress.

    Args:
        networking_api: Kubernetes Networking V1 API client.
        name: Name of the ingress.
        namespace: Kubernetes namespace.

    Raises:
        ApiException: If an API error occurs.
    """
    try:
        retry_on_api_exception(
            networking_api.delete_namespaced_ingress,
            fail_on_status_codes=(404,),
        )(name=name, namespace=namespace)
    except ApiException as e:
        if e.status != 404:
            raise


# ============================================================================
# HorizontalPodAutoscaler Management Functions
# ============================================================================


def get_hpa(
    autoscaling_api: k8s_client.AutoscalingV2Api,
    name: str,
    namespace: str,
) -> Optional[k8s_client.V1HorizontalPodAutoscaler]:
    """Get a Kubernetes HorizontalPodAutoscaler.

    Args:
        autoscaling_api: Kubernetes Autoscaling V2 API client.
        name: Name of the HPA.
        namespace: Kubernetes namespace.

    Returns:
        The HPA object, or None if not found.

    Raises:
        ApiException: If an API error occurs.

    """
    try:
        return retry_on_api_exception(
            autoscaling_api.read_namespaced_horizontal_pod_autoscaler,
            fail_on_status_codes=(404,),
        )(name=name, namespace=namespace)
    except ApiException as e:
        if e.status == 404:
            return None
        raise


def create_or_update_hpa(
    autoscaling_api: k8s_client.AutoscalingV2Api,
    namespace: str,
    hpa_manifest: Dict[str, Any],
) -> None:
    """Create or update a Kubernetes HorizontalPodAutoscaler.

    Args:
        autoscaling_api: Kubernetes Autoscaling V2 API client.
        namespace: Kubernetes namespace.
        hpa_manifest: The HPA manifest as a dictionary.

    Raises:
        ApiException: If an API error occurs.
    """
    hpa_name = hpa_manifest.get("metadata", {}).get("name")
    if not hpa_name:
        logger.warning(
            "HPA manifest is missing 'metadata.name'. Skipping HPA creation."
        )
        return

    try:
        retry_on_api_exception(
            autoscaling_api.create_namespaced_horizontal_pod_autoscaler,
            fail_on_status_codes=(404,),
        )(namespace=namespace, body=hpa_manifest)
        logger.info(f"Created HorizontalPodAutoscaler '{hpa_name}'.")
    except ApiException as e:
        if e.status == 409:
            # HPA already exists, update it
            try:
                retry_on_api_exception(
                    autoscaling_api.patch_namespaced_horizontal_pod_autoscaler,
                    fail_on_status_codes=(404,),
                )(name=hpa_name, namespace=namespace, body=hpa_manifest)
                logger.info(f"Updated HorizontalPodAutoscaler '{hpa_name}'.")
            except ApiException as patch_error:
                logger.warning(
                    f"Failed to update HPA '{hpa_name}': {patch_error}"
                )
        else:
            logger.warning(f"Failed to create HPA '{hpa_name}': {e}")


def delete_hpa(
    autoscaling_api: k8s_client.AutoscalingV2Api,
    name: str,
    namespace: str,
) -> None:
    """Delete a Kubernetes HorizontalPodAutoscaler.

    Args:
        autoscaling_api: Kubernetes Autoscaling V2 API client.
        name: Name of the HPA.
        namespace: Kubernetes namespace.

    Raises:
        ApiException: If an API error occurs.
    """
    try:
        retry_on_api_exception(
            autoscaling_api.delete_namespaced_horizontal_pod_autoscaler,
            fail_on_status_codes=(404,),
        )(name=name, namespace=namespace)
    except ApiException as e:
        if e.status == 404:
            logger.debug(
                f"HPA '{name}' not found (expected if not configured)"
            )
        else:
            logger.warning(f"Failed to delete HPA '{name}': {e}")


# ============================================================================
# Pod Management Functions
# ============================================================================


def list_pods(
    core_api: k8s_client.CoreV1Api,
    namespace: str,
    label_selector: Optional[str] = None,
) -> k8s_client.V1PodList:
    """List pods in a namespace.

    Args:
        core_api: Kubernetes Core V1 API client.
        namespace: Kubernetes namespace.
        label_selector: Optional label selector to filter pods.

    Returns:
        List of pods.
    """
    return retry_on_api_exception(
        core_api.list_namespaced_pod,
        fail_on_status_codes=(404,),
    )(namespace=namespace, label_selector=label_selector)


# ============================================================================
# Resource Conversion Utilities
# ============================================================================


def convert_resource_settings_to_k8s_format(
    resource_settings: "ResourceSettings",
) -> Tuple[Dict[str, str], Dict[str, str], int]:
    """Convert ZenML ResourceSettings to Kubernetes resource format.

    Args:
        resource_settings: The resource settings from pipeline configuration.

    Returns:
        Tuple of (requests, limits, replicas) in Kubernetes format.
        - requests: Dict with 'cpu', 'memory', and optionally 'nvidia.com/gpu' keys
        - limits: Dict with 'cpu', 'memory', and optionally 'nvidia.com/gpu' keys
        - replicas: Number of replicas

    Raises:
        ValueError: If replica configuration is invalid.
    """
    from zenml.config.resource_settings import ByteUnit

    requests: Dict[str, str] = {}
    limits: Dict[str, str] = {}

    if resource_settings.cpu_count is not None:
        cpu_value = resource_settings.cpu_count
        # Kubernetes accepts CPU as whole numbers (e.g., "2") or millicores (e.g., "500m")
        if cpu_value < 1:
            # Fractional CPUs: 0.5 → "500m"
            cpu_str = f"{int(cpu_value * 1000)}m"
        else:
            if cpu_value == int(cpu_value):
                cpu_str = str(int(cpu_value))  # 2.0 → "2"
            else:
                cpu_str = f"{int(cpu_value * 1000)}m"  # 1.5 → "1500m"

        requests["cpu"] = cpu_str
        limits["cpu"] = cpu_str

    if resource_settings.memory is not None:
        memory_value = resource_settings.get_memory(unit=ByteUnit.MIB)
        if memory_value is not None:
            # Use Gi only for clean conversions to avoid precision loss
            if memory_value >= MIB_TO_GIB and memory_value % MIB_TO_GIB == 0:
                memory_str = f"{int(memory_value / MIB_TO_GIB)}Gi"
            else:
                memory_str = f"{int(memory_value)}Mi"

            requests["memory"] = memory_str
            limits["memory"] = memory_str

    # Determine replica count from min/max settings
    # For standard K8s Deployments, we use min_replicas as the baseline
    # (autoscaling requires a separate HPA resource)
    min_r = resource_settings.min_replicas or 0
    max_r = resource_settings.max_replicas or 0

    if max_r > 0 and min_r > max_r:
        raise ValueError(
            f"min_replicas ({min_r}) cannot be greater than max_replicas ({max_r})"
        )

    replicas = min_r if min_r > 0 else (max_r if max_r > 0 else 1)

    if (
        resource_settings.gpu_count is not None
        and resource_settings.gpu_count > 0
    ):
        # GPU requests must be integers; Kubernetes auto-sets requests=limits for GPUs
        gpu_str = str(resource_settings.gpu_count)
        requests["nvidia.com/gpu"] = gpu_str
        limits["nvidia.com/gpu"] = gpu_str
        logger.info(
            f"Configured {resource_settings.gpu_count} GPU(s) per pod. "
            f"Ensure your cluster has GPU nodes with the nvidia.com/gpu resource. "
            f"You may need to install the NVIDIA device plugin: "
            f"https://github.com/NVIDIA/k8s-device-plugin"
        )

    return requests, limits, replicas


# ============================================================================
# URL Building Utilities
# ============================================================================


def build_url_from_ingress(ingress: k8s_client.V1Ingress) -> Optional[str]:
    """Extract URL from Kubernetes Ingress resource.

    Args:
        ingress: Kubernetes Ingress resource.

    Returns:
        URL from ingress rules or load balancer, or None if not available.
    """
    if not ingress.spec:
        logger.warning(
            f"Ingress '{ingress.metadata.name if ingress.metadata else 'unknown'}' "
            f"has no spec. Cannot build URL."
        )
        return None

    protocol = "https" if ingress.spec.tls else "http"

    # Try to get URL from ingress rules
    if ingress.spec.rules:
        rule = ingress.spec.rules[0]
        if rule.host and rule.http and rule.http.paths:
            path = rule.http.paths[0].path or "/"
            return f"{protocol}://{rule.host}{path}"

    # Try to get URL from load balancer status
    if (
        ingress.status
        and ingress.status.load_balancer
        and ingress.status.load_balancer.ingress
    ):
        lb_ingress = ingress.status.load_balancer.ingress[0]
        host = lb_ingress.ip or lb_ingress.hostname
        if host:
            path = "/"
            if (
                ingress.spec.rules
                and ingress.spec.rules[0].http
                and ingress.spec.rules[0].http.paths
            ):
                path = ingress.spec.rules[0].http.paths[0].path or "/"
            return f"{protocol}://{host}{path}"

    return None


def build_url_from_loadbalancer_service(
    service: k8s_client.V1Service,
) -> Optional[str]:
    """Get URL from LoadBalancer service.

    Args:
        service: Kubernetes Service resource.

    Returns:
        LoadBalancer URL or None if IP not yet assigned.
    """
    if not service.spec or not service.spec.ports:
        return None

    service_port = service.spec.ports[0].port

    if (
        service.status
        and service.status.load_balancer
        and service.status.load_balancer.ingress
    ):
        lb_ingress = service.status.load_balancer.ingress[0]
        host = lb_ingress.ip or lb_ingress.hostname
        if host:
            return f"http://{host}:{service_port}"
    return None


def build_url_from_nodeport_service(
    core_api: k8s_client.CoreV1Api,
    service: k8s_client.V1Service,
    namespace: str,
) -> Optional[str]:
    """Get URL from NodePort service.

    Args:
        core_api: Kubernetes Core V1 API client.
        service: Kubernetes Service resource.
        namespace: Kubernetes namespace.

    Returns:
        NodePort URL or None if not accessible.
    """
    if not service.spec or not service.spec.ports:
        return None

    node_port = service.spec.ports[0].node_port
    service_port = service.spec.ports[0].port
    service_name = service.metadata.name if service.metadata else "unknown"

    if not node_port:
        return None

    try:
        nodes = core_api.list_node()

        # Try to find external IP first
        for node in nodes.items:
            if node.status and node.status.addresses:
                for address in node.status.addresses:
                    if address.type == "ExternalIP":
                        logger.info(
                            f"NodePort service accessible at: http://{address.address}:{node_port}"
                        )
                        return f"http://{address.address}:{node_port}"

        # Fall back to internal IP with warning
        for node in nodes.items:
            if node.status and node.status.addresses:
                for address in node.status.addresses:
                    if address.type == "InternalIP":
                        logger.warning(
                            f"NodePort service '{service_name}' has no nodes with ExternalIP. "
                            f"The returned InternalIP URL is likely NOT accessible from outside the cluster. "
                            f"For local access, use: kubectl port-forward -n {namespace} "
                            f"service/{service_name} 8080:{service_port}"
                        )
                        return f"http://{address.address}:{node_port}"

        logger.error(
            f"NodePort service '{service_name}' deployed, but no node IPs available. "
            f"Use: kubectl port-forward -n {namespace} service/{service_name} 8080:{service_port}"
        )
        return None

    except Exception as e:
        logger.error(
            f"Failed to get node IPs for NodePort service: {e}. "
            f"Use: kubectl port-forward -n {namespace} service/{service_name} 8080:{service_port}"
        )
        return None


def build_url_from_clusterip_service(
    service: k8s_client.V1Service,
    namespace: str,
) -> str:
    """Get internal DNS URL from ClusterIP service.

    Args:
        service: Kubernetes Service resource.
        namespace: Kubernetes namespace.

    Returns:
        Internal cluster DNS URL.
    """
    service_name = service.metadata.name if service.metadata else "unknown"

    if not service.spec or not service.spec.ports:
        return f"http://{service_name}.{namespace}.svc.cluster.local"

    service_port = service.spec.ports[0].port

    logger.warning(
        f"Service '{service_name}' uses ClusterIP, which is only "
        f"accessible from within the Kubernetes cluster. "
        f"For local access, use: kubectl port-forward -n {namespace} "
        f"service/{service_name} 8080:{service_port}"
    )
    return (
        f"http://{service_name}.{namespace}.svc.cluster.local:{service_port}"
    )


def build_service_url(
    core_api: k8s_client.CoreV1Api,
    service: k8s_client.V1Service,
    namespace: str,
    ingress: Optional[k8s_client.V1Ingress] = None,
) -> Optional[str]:
    """Build URL for accessing a Kubernetes service.

    Args:
        core_api: Kubernetes Core V1 API client.
        service: Kubernetes Service resource.
        namespace: Kubernetes namespace.
        ingress: Optional Kubernetes Ingress resource.

    Returns:
        Service URL or None if not yet available.
    """
    # If ingress is configured, use it
    if ingress:
        return build_url_from_ingress(ingress)

    if not service.spec or not service.spec.type:
        service_name = service.metadata.name if service.metadata else "unknown"
        logger.warning(
            f"Service '{service_name}' has no type specified in spec. "
            f"Cannot build service URL."
        )
        return None

    # Otherwise, build URL based on service type
    service_type = service.spec.type

    if service_type == "LoadBalancer":
        return build_url_from_loadbalancer_service(service)
    elif service_type == "NodePort":
        return build_url_from_nodeport_service(core_api, service, namespace)
    elif service_type == "ClusterIP":
        return build_url_from_clusterip_service(service, namespace)

    return None
