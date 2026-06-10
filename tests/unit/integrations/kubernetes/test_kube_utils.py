"""Tests for Kubernetes utility functions."""

from datetime import datetime, timezone
from typing import Any

from kubernetes import client as k8s_client

from zenml.integrations.kubernetes import kube_utils


def _pending_pod(
    name: str = "step-job-pod",
    creation_timestamp: datetime | None = None,
    condition_message: str | None = None,
    waiting_reason: str | None = None,
    waiting_message: str | None = None,
) -> k8s_client.V1Pod:
    conditions = []
    if condition_message:
        conditions.append(
            k8s_client.V1PodCondition(
                type="PodScheduled",
                status="False",
                reason="Unschedulable",
                message=condition_message,
            )
        )

    container_statuses = []
    if waiting_reason:
        container_statuses.append(
            k8s_client.V1ContainerStatus(
                name="main",
                image="step-image",
                image_id="",
                ready=False,
                restart_count=0,
                state=k8s_client.V1ContainerState(
                    waiting=k8s_client.V1ContainerStateWaiting(
                        reason=waiting_reason,
                        message=waiting_message,
                    )
                ),
            )
        )

    return k8s_client.V1Pod(
        metadata=k8s_client.V1ObjectMeta(
            name=name,
            creation_timestamp=creation_timestamp,
        ),
        status=k8s_client.V1PodStatus(
            conditions=conditions,
            container_statuses=container_statuses,
        ),
    )


def _check_job_status_for_pods(
    pods: list[k8s_client.V1Pod],
) -> tuple[kube_utils.JobStatus, str | None]:
    class BatchApi:
        def read_namespaced_job(self, **_: Any) -> k8s_client.V1Job:
            return k8s_client.V1Job(
                status=k8s_client.V1JobStatus(conditions=[])
            )

        def delete_namespaced_job(self, **_: Any) -> None:
            return None

    class CoreApi:
        def list_namespaced_pod(self, **_: Any) -> k8s_client.V1PodList:
            return k8s_client.V1PodList(items=pods)

    return kube_utils.check_job_status(
        batch_api=BatchApi(),  # type: ignore[arg-type]
        core_api=CoreApi(),  # type: ignore[arg-type]
        namespace="default",
        job_name="step-job",
        fail_on_container_waiting_reasons=["ImagePullBackOff"],
    )


def test_get_pod_failure_details_includes_container_and_pod_details() -> None:
    """Test that pod failure details include container and pod state."""
    pod = k8s_client.V1Pod(
        status=k8s_client.V1PodStatus(
            reason="Evicted",
            message="Pod exceeded its memory limit.",
            container_statuses=[
                k8s_client.V1ContainerStatus(
                    name="main",
                    image="step-image",
                    image_id="step-image-id",
                    ready=False,
                    restart_count=0,
                    state=k8s_client.V1ContainerState(
                        terminated=k8s_client.V1ContainerStateTerminated(
                            exit_code=137,
                            reason="OOMKilled",
                        )
                    ),
                )
            ],
        )
    )

    assert kube_utils.get_pod_failure_details(pod, "main") == (
        "container failure reason: OOMKilled, exit_code=137; "
        "pod failure reason: Evicted, message=Pod exceeded its memory limit."
    )


def test_get_pod_failure_details_returns_none_on_unexpected_data() -> None:
    """Test that failure detail extraction is best-effort."""
    assert kube_utils.get_pod_failure_details(object(), "main") is None  # type: ignore[arg-type]


def test_get_pod_pending_details_includes_scheduler_and_container_details() -> (
    None
):
    """Test that pending details include pod conditions and container state."""
    pod = _pending_pod(
        condition_message="0/2 nodes are available: 2 Insufficient cpu.",
        waiting_reason="ContainerCreating",
    )

    assert kube_utils.get_pod_pending_details(pod, "main") == (
        "pod `step-job-pod`: "
        "pod condition: PodScheduled, Unschedulable, "
        "message=0/2 nodes are available: 2 Insufficient cpu.; "
        "container waiting reason: ContainerCreating"
    )


def test_get_pod_pending_details_ignores_metadata_only_pods() -> None:
    """Test that pending details require an actual diagnostic."""
    assert kube_utils.get_pod_pending_details(_pending_pod(), "main") is None


def test_get_pod_pending_details_returns_none_on_unexpected_data() -> None:
    """Test that pending detail extraction is best-effort."""
    assert kube_utils.get_pod_pending_details(object(), "main") is None  # type: ignore[arg-type]


def test_check_job_status_returns_pending_details_without_failing() -> None:
    """Test that non-fatal pending pod details are returned for visibility."""
    status, message = _check_job_status_for_pods(
        [
            _pending_pod(
                condition_message=(
                    "0/2 nodes are available: 2 Insufficient memory."
                )
            )
        ]
    )

    assert status == kube_utils.JobStatus.RUNNING
    assert message == (
        "pod `step-job-pod`: "
        "pod condition: PodScheduled, Unschedulable, "
        "message=0/2 nodes are available: 2 Insufficient memory."
    )


def test_check_job_status_uses_later_pending_pod_with_diagnostics() -> None:
    """Test that metadata-only pods do not mask useful diagnostics."""
    status, message = _check_job_status_for_pods(
        [
            _pending_pod(
                name="metadata-only-pod",
            ),
            _pending_pod(
                name="metadata-only-pod",
                creation_timestamp=None,
            ),
            _pending_pod(
                name="diagnostic-pod",
                creation_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                condition_message=(
                    "0/2 nodes are available: 2 Insufficient cpu."
                ),
            ),
        ]
    )

    assert status == kube_utils.JobStatus.RUNNING
    assert message == (
        "pod `diagnostic-pod`: "
        "pod condition: PodScheduled, Unschedulable, "
        "message=0/2 nodes are available: 2 Insufficient cpu."
    )


def test_check_job_status_prefers_latest_pending_pod_diagnostics() -> None:
    """Test that pending details come from the latest diagnostic pod."""
    status, message = _check_job_status_for_pods(
        [
            _pending_pod(
                name="older-pod",
                creation_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                condition_message=(
                    "0/2 nodes are available: 2 Insufficient cpu."
                ),
            ),
            _pending_pod(
                name="newer-pod",
                creation_timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc),
                condition_message=(
                    "0/2 nodes are available: 2 Insufficient memory."
                ),
            ),
        ]
    )

    assert status == kube_utils.JobStatus.RUNNING
    assert message == (
        "pod `newer-pod`: "
        "pod condition: PodScheduled, Unschedulable, "
        "message=0/2 nodes are available: 2 Insufficient memory."
    )


def test_check_job_status_includes_pending_details_on_fail_fast() -> None:
    """Test that fail-fast waiting states include Kubernetes diagnostics."""
    status, message = _check_job_status_for_pods(
        [
            _pending_pod(
                creation_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                waiting_reason="ImagePullBackOff",
                waiting_message="Back-off pulling image missing-image.",
            )
        ]
    )

    assert status == kube_utils.JobStatus.FAILED
    assert message == (
        "Detected container in state `ImagePullBackOff` "
        "(pod `step-job-pod`: container waiting reason: ImagePullBackOff, "
        "message=Back-off pulling image missing-image.)"
    )
