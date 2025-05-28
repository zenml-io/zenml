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
import re
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException

from zenml.integrations.kubernetes.orchestrators.manifest_utils import (
    build_namespace_manifest,
    build_role_binding_manifest_for_service_account,
    build_secret_manifest,
    build_service_account_manifest,
)
from zenml.logger import get_logger
from zenml.utils.time_utils import utc_now

logger = get_logger(__name__)


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


def calculate_max_pod_name_length_for_namespace(namespace: str) -> int:
    """Calculate the max pod length for a certain namespace.

    Args:
        namespace: The namespace in which the pod will be created.

    Returns:
        The maximum pod name length.
    """
    # Kubernetes allows Pod names to have 253 characters. However, when
    # creating a pod they try to create a log file which is called
    # <NAMESPACE>_<POD_NAME>_<UUID>, which adds additional characters and
    # runs into filesystem limitations for filename lengths (255). We therefore
    # subtract the length of a UUID (36), the two underscores and the
    # namespace length from the max filename length.
    return 255 - 38 - len(namespace)


def sanitize_pod_name(pod_name: str, namespace: str) -> str:
    """Sanitize pod names so they conform to Kubernetes pod naming convention.

    Args:
        pod_name: Arbitrary input pod name.
        namespace: Namespace in which the Pod will be created.

    Returns:
        Sanitized pod name.
    """
    # https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#dns-subdomain-names
    pod_name = re.sub(r"[^a-z0-9-]", "-", pod_name.lower())
    pod_name = re.sub(r"^[-]+", "", pod_name)
    pod_name = re.sub(r"[-]+$", "", pod_name)
    pod_name = re.sub(r"[-]+", "-", pod_name)

    allowed_length = calculate_max_pod_name_length_for_namespace(
        namespace=namespace
    )
    return pod_name[:allowed_length]


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
    label = re.sub(r"[-]+$", "", label)
    label = re.sub(r"[-]+", "-", label)

    return label[:63]


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
        return core_api.read_namespaced_pod(name=pod_name, namespace=namespace)
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
                logger.error(
                    f"Failed to create {pod_display_name}. "
                    f"Retrying in {startup_failure_delay} seconds..."
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
