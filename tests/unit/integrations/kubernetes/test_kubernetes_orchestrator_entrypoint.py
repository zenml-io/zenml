"""Tests for the Kubernetes orchestrator entrypoint."""

from datetime import datetime, timezone

from kubernetes import client as k8s_client

from zenml.integrations.kubernetes.constants import STEP_NAME_ANNOTATION_KEY
from zenml.integrations.kubernetes.orchestrators import (
    kubernetes_orchestrator_entrypoint as entrypoint,
)
from zenml.integrations.kubernetes.orchestrators.dag_runner import Node


def _pending_pod(
    *,
    name: str,
    step_name: str | None = None,
    job_name: str | None = None,
    reason: str = "ContainerCreating",
    message: str | None = None,
    conditions: list[k8s_client.V1PodCondition] | None = None,
    creation_timestamp: datetime | None = None,
    phase: str = "Pending",
) -> k8s_client.V1Pod:
    annotations = (
        {STEP_NAME_ANNOTATION_KEY: step_name} if step_name is not None else {}
    )
    labels = {}
    if job_name is not None:
        labels["job-name"] = job_name
    elif step_name is not None:
        labels["job-name"] = f"{step_name}-job"

    return k8s_client.V1Pod(
        metadata=k8s_client.V1ObjectMeta(
            name=name,
            annotations=annotations,
            labels=labels,
            creation_timestamp=creation_timestamp
            or datetime(2026, 5, 21, 10, 30, tzinfo=timezone.utc),
        ),
        status=k8s_client.V1PodStatus(
            phase=phase,
            conditions=conditions,
            container_statuses=[
                k8s_client.V1ContainerStatus(
                    name="main",
                    image="image",
                    image_id="",
                    ready=False,
                    restart_count=0,
                    state=k8s_client.V1ContainerState(
                        waiting=k8s_client.V1ContainerStateWaiting(
                            reason=reason,
                            message=message,
                        )
                    ),
                )
            ],
        ),
    )


def _running_pod(
    *,
    name: str,
    step_name: str,
    pod_start_time: datetime,
    container_start_time: datetime,
) -> k8s_client.V1Pod:
    return k8s_client.V1Pod(
        metadata=k8s_client.V1ObjectMeta(
            name=name,
            annotations={STEP_NAME_ANNOTATION_KEY: step_name},
            creation_timestamp=pod_start_time,
        ),
        status=k8s_client.V1PodStatus(
            phase="Running",
            start_time=pod_start_time,
            container_statuses=[
                k8s_client.V1ContainerStatus(
                    name="main",
                    image="image",
                    image_id="",
                    ready=True,
                    restart_count=0,
                    state=k8s_client.V1ContainerState(
                        running=k8s_client.V1ContainerStateRunning(
                            started_at=container_start_time
                        )
                    ),
                )
            ],
        ),
    )


def _pod_status_index(mocker, pods: list[k8s_client.V1Pod]):
    core_api = mocker.Mock()
    core_api.list_namespaced_pod.return_value = k8s_client.V1PodList(
        items=pods
    )
    return entrypoint.KubernetesRunPodStatusIndex(
        core_api=core_api,
        namespace="zenml-test",
        run_id="run-id",
        api_request_timeout=5,
    )


def test_pod_status_index_refresh_lists_run_pods_once_for_multiple_nodes(
    mocker,
) -> None:
    """Test that one pod list snapshot serves multiple running nodes."""
    core_api = mocker.Mock()
    core_api.list_namespaced_pod.return_value = k8s_client.V1PodList(
        items=[
            _pending_pod(name="first-pod", step_name="first_step"),
            _pending_pod(name="second-pod", step_name="second_step"),
        ]
    )
    info = mocker.patch.object(entrypoint.logger, "info")

    pod_status_index = entrypoint.KubernetesRunPodStatusIndex(
        core_api=core_api,
        namespace="zenml-test",
        run_id="run-id",
        api_request_timeout=5,
    )

    pod_status_index.refresh([Node(id="first_step"), Node(id="second_step")])
    pod_status_index.log_state_change(Node(id="first_step"))
    pod_status_index.log_state_change(Node(id="second_step"))

    core_api.list_namespaced_pod.assert_called_once_with(
        namespace="zenml-test",
        label_selector="run_id=run-id",
        _request_timeout=5,
    )
    assert info.call_count == 2


def test_pod_status_index_falls_back_to_job_name(mocker) -> None:
    """Test pods without exact step annotations can map through job labels."""
    info = mocker.patch.object(entrypoint.logger, "info")
    pod_status_index = _pod_status_index(
        mocker,
        [
            _pending_pod(
                name="fallback-pod",
                job_name="fallback-job",
            )
        ],
    )
    node = Node(id="fallback_step", metadata={"job_name": "fallback-job"})

    pod_status_index.refresh([node])
    pod_status_index.log_state_change(node)

    info.assert_called_once()


def test_pod_status_index_chooses_latest_active_pod(mocker) -> None:
    """Test terminal retry pods are ignored in favor of the active pod."""
    info = mocker.patch.object(entrypoint.logger, "info")
    old_terminal_pod = _pending_pod(
        name="old-pod",
        step_name="retry_step",
        creation_timestamp=datetime(2026, 5, 21, 10, 30, tzinfo=timezone.utc),
        phase="Failed",
    )
    active_pod = _pending_pod(
        name="active-pod",
        step_name="retry_step",
        creation_timestamp=datetime(2026, 5, 21, 10, 31, tzinfo=timezone.utc),
    )
    pod_status_index = _pod_status_index(
        mocker, [old_terminal_pod, active_pod]
    )

    pod_status_index.refresh([Node(id="retry_step")])
    pod_status_index.log_state_change(Node(id="retry_step"))

    assert info.call_args.args[2] == "active-pod"


def test_expected_pending_pod_logs_once_at_info_level(mocker) -> None:
    """Test expected pending states are logged once at info level."""
    pod_status_index = _pod_status_index(
        mocker,
        [_pending_pod(name="step-pod", step_name="step")],
    )
    info = mocker.patch.object(entrypoint.logger, "info")
    warning = mocker.patch.object(entrypoint.logger, "warning")
    node = Node(id="step")

    pod_status_index.refresh([node])
    pod_status_index.log_state_change(node)
    pod_status_index.log_state_change(node)

    info.assert_called_once()
    warning.assert_not_called()


def test_unschedulable_pending_pod_warning_ignores_message_for_deduplication(
    mocker,
) -> None:
    """Test unschedulable message changes do not repeat warnings."""
    first_pod = _pending_pod(
        name="step-pod",
        step_name="step",
        reason="ContainerCreating",
        conditions=[
            k8s_client.V1PodCondition(
                type="PodScheduled",
                status="False",
                reason="Unschedulable",
                message="0/1 nodes are available: insufficient cpu.",
            )
        ],
    )
    second_pod = _pending_pod(
        name="step-pod",
        step_name="step",
        reason="ContainerCreating",
        conditions=[
            k8s_client.V1PodCondition(
                type="PodScheduled",
                status="False",
                reason="Unschedulable",
                message="0/2 nodes are available: insufficient cpu.",
            )
        ],
    )
    pod_status_index = _pod_status_index(mocker, [first_pod])
    warning = mocker.patch.object(entrypoint.logger, "warning")
    node = Node(id="step")

    pod_status_index.refresh([node])
    pod_status_index.log_state_change(node)
    pod_status_index.core_api.list_namespaced_pod.return_value = (
        k8s_client.V1PodList(items=[second_pod])
    )
    pod_status_index.refresh([node])
    pod_status_index.log_state_change(node)

    warning.assert_called_once()
    assert "insufficient cpu" in warning.call_args.args[5]


def test_pending_reason_change_logs_again(mocker) -> None:
    """Test a changed pending reason emits a new log line."""
    pod_status_index = _pod_status_index(
        mocker,
        [_pending_pod(name="step-pod", step_name="step")],
    )
    info = mocker.patch.object(entrypoint.logger, "info")
    warning = mocker.patch.object(entrypoint.logger, "warning")
    node = Node(id="step")

    pod_status_index.refresh([node])
    pod_status_index.log_state_change(node)
    pod_status_index.core_api.list_namespaced_pod.return_value = (
        k8s_client.V1PodList(
            items=[
                _pending_pod(
                    name="step-pod",
                    step_name="step",
                    reason="ImagePullBackOff",
                )
            ]
        )
    )
    pod_status_index.refresh([node])
    pod_status_index.log_state_change(node)

    info.assert_called_once()
    warning.assert_called_once()


def test_running_pod_logs_start_times(mocker) -> None:
    """Test running pod logs include pod and container start times."""
    pod_start_time = datetime(2026, 5, 21, 10, 30, tzinfo=timezone.utc)
    container_start_time = datetime(2026, 5, 21, 10, 31, tzinfo=timezone.utc)
    pod_status_index = _pod_status_index(
        mocker,
        [
            _running_pod(
                name="step-pod",
                step_name="step",
                pod_start_time=pod_start_time,
                container_start_time=container_start_time,
            )
        ],
    )
    info = mocker.patch.object(entrypoint.logger, "info")
    node = Node(id="step")

    pod_status_index.refresh([node])
    pod_status_index.log_state_change(node)

    assert info.call_args.args[3] == pod_start_time
    assert info.call_args.args[4] == container_start_time


def test_pod_scheduled_condition_takes_precedence_over_waiting_reason(
    mocker,
) -> None:
    """Test scheduling conditions produce the pending diagnostic reason."""
    pod_status_index = _pod_status_index(
        mocker,
        [
            _pending_pod(
                name="step-pod",
                step_name="step",
                reason="ContainerCreating",
                conditions=[
                    k8s_client.V1PodCondition(
                        type="PodScheduled",
                        status="False",
                        reason="Unschedulable",
                        message="0/1 nodes are available.",
                    )
                ],
            )
        ],
    )
    warning = mocker.patch.object(entrypoint.logger, "warning")
    node = Node(id="step")

    pod_status_index.refresh([node])
    pod_status_index.log_state_change(node)

    assert warning.call_args.args[4] == "Unschedulable"
