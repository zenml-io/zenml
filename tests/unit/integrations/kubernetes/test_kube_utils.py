"""Tests for Kubernetes utility functions."""

from typing import Any

from kubernetes import client as k8s_client

from zenml.integrations.kubernetes import kube_utils


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
    pod = k8s_client.V1Pod(
        metadata=k8s_client.V1ObjectMeta(name="step-job-pod"),
        status=k8s_client.V1PodStatus(
            conditions=[
                k8s_client.V1PodCondition(
                    type="PodScheduled",
                    status="False",
                    reason="Unschedulable",
                    message="0/2 nodes are available: 2 Insufficient cpu.",
                )
            ],
            container_statuses=[
                k8s_client.V1ContainerStatus(
                    name="main",
                    image="step-image",
                    image_id="",
                    ready=False,
                    restart_count=0,
                    state=k8s_client.V1ContainerState(
                        waiting=k8s_client.V1ContainerStateWaiting(
                            reason="ContainerCreating"
                        )
                    ),
                )
            ],
        ),
    )

    assert kube_utils.get_pod_pending_details(pod, "main") == (
        "pod `step-job-pod`; "
        "pod condition: PodScheduled, Unschedulable, "
        "message=0/2 nodes are available: 2 Insufficient cpu.; "
        "container waiting reason: ContainerCreating"
    )


def test_get_pod_pending_details_returns_none_on_unexpected_data() -> None:
    """Test that pending detail extraction is best-effort."""
    assert kube_utils.get_pod_pending_details(object(), "main") is None  # type: ignore[arg-type]


def test_check_job_status_returns_pending_details_without_failing() -> None:
    """Test that non-fatal pending pod details are returned for visibility."""
    pod = k8s_client.V1Pod(
        metadata=k8s_client.V1ObjectMeta(name="step-job-pod"),
        status=k8s_client.V1PodStatus(
            conditions=[
                k8s_client.V1PodCondition(
                    type="PodScheduled",
                    status="False",
                    reason="Unschedulable",
                    message="0/2 nodes are available: 2 Insufficient memory.",
                )
            ]
        ),
    )

    class BatchApi:
        def read_namespaced_job(self, **_: Any) -> k8s_client.V1Job:
            return k8s_client.V1Job(
                status=k8s_client.V1JobStatus(conditions=[])
            )

    class CoreApi:
        def list_namespaced_pod(self, **_: Any) -> k8s_client.V1PodList:
            return k8s_client.V1PodList(items=[pod])

    status, message = kube_utils.check_job_status(
        batch_api=BatchApi(),  # type: ignore[arg-type]
        core_api=CoreApi(),  # type: ignore[arg-type]
        namespace="default",
        job_name="step-job",
        fail_on_container_waiting_reasons=["ImagePullBackOff"],
    )

    assert status == kube_utils.JobStatus.RUNNING
    assert message == (
        "pod `step-job-pod`; "
        "pod condition: PodScheduled, Unschedulable, "
        "message=0/2 nodes are available: 2 Insufficient memory."
    )
