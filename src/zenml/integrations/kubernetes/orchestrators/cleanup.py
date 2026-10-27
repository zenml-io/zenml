# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Bounded reconciliation of Kubernetes workloads during cancellation."""

import time
from typing import Optional, Set

from kubernetes import client as k8s_client
from kubernetes.client import ApiException

from zenml.integrations.kubernetes.constants import (
    ORCHESTRATOR_ANNOTATION_KEY,
    ORCHESTRATOR_RUN_ID_ANNOTATION_KEY,
    RUN_ID_ANNOTATION_KEY,
    STEP_NAME_ANNOTATION_KEY,
)
from zenml.integrations.kubernetes.kube_utils import sanitize_label_value


def stop_workloads(
    batch_api: k8s_client.BatchV1Api,
    core_api: k8s_client.CoreV1Api,
    namespace: str,
    *,
    run_ids: Optional[Set[str]] = None,
    controller_ids: Optional[Set[str]] = None,
    job_names: Optional[Set[str]] = None,
    step_run_id: Optional[str] = None,
    step_name: Optional[str] = None,
    include_controller: bool = False,
    timeout: float = 60.0,
    api_request_timeout: Optional[float] = None,
    poll_interval: float = 0.5,
) -> None:
    """Delete matching Jobs and Pods and confirm their disappearance.

    Discovery repeats to catch submissions completing during cancellation.
    Explicit Job names also cover ambiguous submission responses. Callers must
    fence further submissions before treating this result as final cleanup.

    Args:
        batch_api: Kubernetes batch API.
        core_api: Kubernetes core API.
        namespace: Namespace containing the workloads.
        run_ids: Run IDs whose workloads belong to the cancellation scope.
        controller_ids: Backend controller Job or Pod IDs, including legacy IDs.
        job_names: Exact Job names known before submission.
        step_run_id: Restrict discovery to this isolated step attempt.
        step_name: Restrict discovery to this static step invocation.
        include_controller: Whether the scope owns the controller itself.
        timeout: Overall reconciliation deadline in seconds.
        api_request_timeout: Upper bound for an individual API request.
        poll_interval: Delay between discovery passes.

    Raises:
        RuntimeError: If discovery or deletion cannot be confirmed by the
            deadline. The error includes remaining resources or API errors.
    """
    run_ids = run_ids or set()
    controller_ids = controller_ids or set()
    known_jobs = set(job_names or ())
    known_job_uids: Set[str] = set()
    known_pods: Set[str] = set()
    deadline = time.monotonic() + timeout
    empty_passes = 0
    remaining: Set[str] = set()
    last_error: Optional[Exception] = None

    def request_timeout() -> float:
        """Return the remaining bounded API request budget.

        Returns:
            Maximum seconds for the next API request.

        Raises:
            TimeoutError: If the overall deadline has expired.
        """
        available = deadline - time.monotonic()
        if available <= 0:
            raise TimeoutError("Kubernetes cleanup deadline exceeded.")
        return min(available, api_request_timeout or 10.0)

    while time.monotonic() < deadline:
        try:
            jobs = batch_api.list_namespaced_job(
                namespace=namespace, _request_timeout=request_timeout()
            ).items
            pods = core_api.list_namespaced_pod(
                namespace=namespace, _request_timeout=request_timeout()
            ).items

            # Static legacy controller IDs are Pod names. Scheduled controller
            # Jobs may only carry the run ID in annotations, not labels.
            if include_controller:
                for pod in pods:
                    if pod.metadata and pod.metadata.name in controller_ids:
                        known_jobs.update(
                            owner.name
                            for owner in pod.metadata.owner_references or []
                            if owner.kind == "Job"
                        )
                        known_pods.add(pod.metadata.name)

            selected_jobs = []
            for job in jobs:
                metadata = job.metadata
                if not metadata:
                    continue
                labels = metadata.labels or {}
                annotations = metadata.annotations or {}
                is_controller = ORCHESTRATOR_ANNOTATION_KEY in annotations
                if is_controller and not include_controller:
                    continue
                matches = (
                    labels.get("run_id") in run_ids
                    or annotations.get(RUN_ID_ANNOTATION_KEY) in run_ids
                    or metadata.name in known_jobs
                )
                if include_controller and is_controller:
                    matches = matches or (
                        metadata.name in controller_ids
                        or annotations.get(ORCHESTRATOR_RUN_ID_ANNOTATION_KEY)
                        in controller_ids
                    )
                if step_run_id is not None:
                    matches = labels.get("step_run_id") == step_run_id
                if step_name is not None:
                    matches = matches and (
                        labels.get("step_name")
                        == sanitize_label_value(step_name)
                        or annotations.get(STEP_NAME_ANNOTATION_KEY)
                        == step_name
                    )
                if matches:
                    selected_jobs.append(job)
                    known_jobs.add(metadata.name)
                    if metadata.uid:
                        known_job_uids.add(metadata.uid)

            selected_pods = []
            for pod in pods:
                metadata = pod.metadata
                if not metadata:
                    continue
                labels = metadata.labels or {}
                owners = metadata.owner_references or []
                matches = metadata.name in known_pods or any(
                    owner.kind == "Job"
                    and (
                        owner.uid in known_job_uids or owner.name in known_jobs
                    )
                    for owner in owners
                )
                label_match = labels.get("run_id") in run_ids
                if not include_controller:
                    label_match = label_match and "step_name" in labels
                if step_run_id is not None:
                    label_match = labels.get("step_run_id") == step_run_id
                if step_name is not None:
                    label_match = label_match and labels.get(
                        "step_name"
                    ) == sanitize_label_value(step_name)
                if matches or label_match:
                    selected_pods.append(pod)
                    known_pods.add(metadata.name)

            remaining = {
                f"Job/{job.metadata.name}" for job in selected_jobs
            } | {f"Pod/{pod.metadata.name}" for pod in selected_pods}
            if not remaining:
                empty_passes += 1
                if empty_passes >= 2:
                    return
            else:
                empty_passes = 0

            errors = []
            for job in selected_jobs:
                try:
                    batch_api.delete_namespaced_job(
                        name=job.metadata.name,
                        namespace=namespace,
                        body=k8s_client.V1DeleteOptions(
                            propagation_policy="Foreground",
                            preconditions=k8s_client.V1Preconditions(
                                uid=job.metadata.uid
                            ),
                        ),
                        _request_timeout=request_timeout(),
                    )
                except ApiException as error:
                    if error.status != 404:
                        errors.append(error)
            for pod in selected_pods:
                try:
                    core_api.delete_namespaced_pod(
                        name=pod.metadata.name,
                        namespace=namespace,
                        body=k8s_client.V1DeleteOptions(
                            preconditions=k8s_client.V1Preconditions(
                                uid=pod.metadata.uid
                            ),
                        ),
                        _request_timeout=request_timeout(),
                    )
                except ApiException as error:
                    if error.status != 404:
                        errors.append(error)
            last_error = errors[0] if errors else None
        except Exception as error:
            last_error = error
            empty_passes = 0
        time.sleep(min(poll_interval, max(0, deadline - time.monotonic())))

    details = ", ".join(sorted(remaining)) or "workload discovery unconfirmed"
    if last_error is not None:
        details += f"; {last_error}"
    raise RuntimeError(
        f"Kubernetes cleanup is incomplete in namespace `{namespace}`: "
        f"{details}. Retry immediate stop after resolving the reported issue."
    )
