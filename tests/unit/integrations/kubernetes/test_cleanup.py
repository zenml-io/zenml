"""Tests for cancellation reconciliation without a Kubernetes cluster."""

from typing import Any

import pytest
from kubernetes import client as k8s_client
from kubernetes.client import ApiException

from zenml.integrations.kubernetes.constants import (
    ORCHESTRATOR_ANNOTATION_KEY,
    RUN_ID_ANNOTATION_KEY,
)
from zenml.integrations.kubernetes.orchestrators.cleanup import stop_workloads


def job(
    name: str, *, run_id: str = "run", controller: bool = False
) -> k8s_client.V1Job:
    """Build a workload with a stable backend identity.

    Args:
        name: Job name.
        run_id: Run owning the Job.
        controller: Whether this is a controller Job.

    Returns:
        A Job with discovery metadata.
    """
    return k8s_client.V1Job(
        metadata=k8s_client.V1ObjectMeta(
            name=name,
            uid=f"uid-{name}",
            labels={
                "run_id": run_id,
                **({} if controller else {"step_name": name}),
            },
            annotations={ORCHESTRATOR_ANNOTATION_KEY: "orchestrator"}
            if controller
            else {},
        )
    )


class FakeApi:
    """In-memory Kubernetes API with controllable races and failures."""

    def __init__(self, jobs: list[k8s_client.V1Job]) -> None:
        """Initialize the fake API with existing Jobs.

        Args:
            jobs: Jobs initially visible to discovery.
        """
        self.jobs = jobs
        self.pods: list[k8s_client.V1Pod] = []
        self.deleted_jobs: list[str] = []
        self.deleted_pods: list[str] = []
        self.list_calls = 0
        self.late_job: k8s_client.V1Job | None = None
        self.stuck = False
        self.discovery_error = False
        self.delete_404 = False

    def list_namespaced_job(self, **kwargs: Any) -> k8s_client.V1JobList:
        """Return the current Jobs, injecting configured discovery races.

        Args:
            **kwargs: Kubernetes request options.

        Returns:
            Current Jobs.

        Raises:
            ApiException: When discovery is configured to fail.
        """
        self.list_calls += 1
        assert 0 < kwargs["_request_timeout"] <= 10
        if self.discovery_error:
            raise ApiException(status=403, reason="Forbidden")
        if self.list_calls == 2 and self.late_job is not None:
            self.jobs.append(self.late_job)
        return k8s_client.V1JobList(items=list(self.jobs))

    def list_namespaced_pod(self, **kwargs: Any) -> k8s_client.V1PodList:
        """Return the currently visible Pods.

        Args:
            **kwargs: Kubernetes request options.

        Returns:
            Current Pods.
        """
        return k8s_client.V1PodList(items=list(self.pods))

    def delete_namespaced_job(self, name: str, **kwargs: Any) -> None:
        """Delete a Job unless its finalizer is configured to remain.

        Args:
            name: Job name.
            **kwargs: Kubernetes deletion options.

        Raises:
            ApiException: When a concurrent deletion is configured.
        """
        self.deleted_jobs.append(name)
        assert kwargs["body"].preconditions.uid == f"uid-{name}"
        if not self.stuck:
            self.jobs = [
                item for item in self.jobs if item.metadata.name != name
            ]
        if self.delete_404:
            raise ApiException(status=404)

    def delete_namespaced_pod(self, name: str, **kwargs: Any) -> None:
        """Delete a Pod unless its finalizer is configured to remain.

        Args:
            name: Pod name.
            **kwargs: Kubernetes deletion options.
        """
        self.deleted_pods.append(name)
        if not self.stuck:
            self.pods = [
                item for item in self.pods if item.metadata.name != name
            ]


def reconcile(api: FakeApi, **kwargs: Any) -> None:
    """Run bounded reconciliation against the fake API.

    Args:
        api: Fake Kubernetes API.
        **kwargs: Workload selection options.
    """
    stop_workloads(
        batch_api=api,
        core_api=api,
        namespace="test",  # type: ignore[arg-type]
        timeout=0.05,
        poll_interval=0.001,
        **kwargs,
    )


def test_cleanup_discovers_late_jobs_and_confirms_owned_pods() -> None:
    """Cleanup discovers late jobs and confirms owned pods."""
    api = FakeApi([job("first")])
    api.late_job = job("late")
    api.pods = [
        k8s_client.V1Pod(
            metadata=k8s_client.V1ObjectMeta(
                name="first-pod",
                uid="pod-uid",
                owner_references=[
                    k8s_client.V1OwnerReference(
                        api_version="batch/v1",
                        kind="Job",
                        name="first",
                        uid="uid-first",
                    )
                ],
            )
        )
    ]
    reconcile(api, run_ids={"run"})
    assert set(api.deleted_jobs) == {"first", "late"}
    assert api.deleted_pods == ["first-pod"]
    assert api.list_calls >= 4


def test_child_cleanup_preserves_shared_controller_and_other_runs() -> None:
    """Child cleanup preserves shared controller and other runs."""
    api = FakeApi(
        [
            job("controller", run_id="root", controller=True),
            job("child", run_id="child"),
            job("sibling", run_id="sibling"),
        ]
    )
    reconcile(api, run_ids={"child"}, controller_ids={"controller"})
    assert api.deleted_jobs == ["child"]


def test_scheduled_controller_without_run_label_is_discovered() -> None:
    """Scheduled controller without run label is discovered."""
    controller = job("scheduled", controller=True)
    controller.metadata.labels = {}
    controller.metadata.annotations[RUN_ID_ANNOTATION_KEY] = "run"
    api = FakeApi([controller])
    reconcile(api, run_ids={"run"}, include_controller=True)
    assert api.deleted_jobs == ["scheduled"]


def test_legacy_controller_pod_identity_resolves_owning_job() -> None:
    """Legacy controller pod identity resolves owning job."""
    controller = job("controller", run_id="unknown", controller=True)
    api = FakeApi([controller])
    api.pods = [
        k8s_client.V1Pod(
            metadata=k8s_client.V1ObjectMeta(
                name="controller-pod",
                uid="pod-uid",
                owner_references=[
                    k8s_client.V1OwnerReference(
                        api_version="batch/v1",
                        kind="Job",
                        name="controller",
                        uid="uid-controller",
                    )
                ],
            )
        )
    ]
    reconcile(api, controller_ids={"controller-pod"}, include_controller=True)
    assert api.deleted_jobs == ["controller"]


def test_isolated_cleanup_deletes_every_matching_job_and_tolerates_404() -> (
    None
):
    """Isolated cleanup deletes every matching job and tolerates 404."""
    api = FakeApi([job("one"), job("two"), job("other")])
    for item in api.jobs[:2]:
        item.metadata.labels["step_run_id"] = "attempt"
    api.delete_404 = True
    reconcile(api, step_run_id="attempt")
    assert api.deleted_jobs == ["one", "two"]


def test_stuck_finalizer_reports_incomplete_cleanup() -> None:
    """Stuck finalizer reports incomplete cleanup."""
    api = FakeApi([job("stuck")])
    api.stuck = True
    with pytest.raises(RuntimeError, match="Job/stuck"):
        reconcile(api, run_ids={"run"})


def test_discovery_error_does_not_mean_workloads_are_gone() -> None:
    """Discovery error does not mean workloads are gone."""
    api = FakeApi([])
    api.discovery_error = True
    with pytest.raises(RuntimeError, match="Forbidden"):
        reconcile(api, run_ids={"run"})
