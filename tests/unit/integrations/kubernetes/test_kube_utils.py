"""Tests for Kubernetes utility functions."""

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
