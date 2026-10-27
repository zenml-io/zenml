"""Focused Kubernetes stop tests without cluster access."""

from contextlib import nullcontext
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from kubernetes import client as k8s_client
from kubernetes.client import ApiException

from zenml.enums import (
    ExecutionStatus,
    StackComponentType,
)
from zenml.integrations.kubernetes import kube_utils
from zenml.integrations.kubernetes.constants import (
    ORCHESTRATOR_ANNOTATION_KEY,
    STEP_NAME_ANNOTATION_KEY,
)
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
    KubernetesOrchestratorConfig,
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.orchestrators import (
    kubernetes_orchestrator as module,
)


def setup_stop(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Create an orchestrator backed only by test doubles.

    Args:
        monkeypatch: Pytest patching fixture.

    Returns:
        Run, client, APIs, and orchestrator used by a test.
    """
    run = SimpleNamespace(
        id=uuid4(),
        project_id=uuid4(),
        name="test-run",
        status=ExecutionStatus.FAILED,
        child_key=None,
        orchestrator_run_id="controller",
    )
    children: list[Any] = []
    client = Mock()
    client.get_pipeline_run.return_value = run
    client.list_pipeline_runs.side_effect = lambda **kwargs: SimpleNamespace(
        items=children if kwargs["parent_run_id"] == run.id else [],
        index=1,
        total_pages=1,
    )
    batch_api, core_api = Mock(), Mock()
    batch_api.list_namespaced_job.return_value = k8s_client.V1JobList(items=[])
    core_api.read_namespaced_pod.side_effect = ApiException(status=404)
    monkeypatch.setattr(module, "Client", lambda: client)
    monkeypatch.setattr(
        module.KubernetesOrchestrator, "get_kube_client", lambda self: None
    )
    monkeypatch.setattr(k8s_client, "BatchV1Api", lambda *args: batch_api)
    monkeypatch.setattr(k8s_client, "CoreV1Api", lambda *args: core_api)
    orchestrator = module.KubernetesOrchestrator(
        name="test",
        id=uuid4(),
        config=KubernetesOrchestratorConfig(max_api_retries=0),
        flavor="kubernetes",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    return SimpleNamespace(
        run=run,
        children=children,
        client=client,
        batch=batch_api,
        core=core_api,
        orchestrator=orchestrator,
    )


def make_job(name: str, *, controller: bool = False) -> k8s_client.V1Job:
    """Create a minimal Job with the existing ZenML annotations.

    Args:
        name: Job name.
        controller: Whether the Job runs the pipeline controller.

    Returns:
        The Job model.
    """
    return k8s_client.V1Job(
        metadata=k8s_client.V1ObjectMeta(
            name=name,
            annotations={ORCHESTRATOR_ANNOTATION_KEY: "orchestrator"}
            if controller
            else {STEP_NAME_ANNOTATION_KEY: name},
        )
    )


def test_immediate_root_stop_deletes_step_and_controller_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Root stop includes descendant workers and its controller Job.

    Args:
        monkeypatch: Pytest patching fixture.
    """
    state = setup_stop(monkeypatch)
    child = SimpleNamespace(id=uuid4())
    state.children.append(child)
    state.batch.list_namespaced_job.return_value = k8s_client.V1JobList(
        items=[make_job("step"), make_job("controller", controller=True)]
    )
    state.orchestrator._stop_run(state.run, graceful=False)
    assert {
        call.kwargs["name"]
        for call in state.batch.delete_namespaced_job.call_args_list
    } == {"step", "controller"}
    selector = state.batch.list_namespaced_job.call_args.kwargs[
        "label_selector"
    ]
    assert str(state.run.id) in selector and str(child.id) in selector
    assert all(
        call.kwargs["propagation_policy"] == "Foreground"
        for call in state.batch.delete_namespaced_job.call_args_list
    )
    state.core.list_namespaced_pod.assert_not_called()
    state.core.delete_namespaced_pod.assert_not_called()
    state.client.zen_store.update_run.assert_not_called()


def test_child_stop_preserves_shared_controller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stopping one child never terminates its shared controller.

    Args:
        monkeypatch: Pytest patching fixture.
    """
    state = setup_stop(monkeypatch)
    state.run.child_key = "child"
    state.batch.list_namespaced_job.return_value = k8s_client.V1JobList(
        items=[make_job("child-step"), make_job("controller", controller=True)]
    )
    state.orchestrator._stop_run(state.run, graceful=False)
    assert [
        call.kwargs["name"]
        for call in state.batch.delete_namespaced_job.call_args_list
    ] == ["child-step"]
    state.core.read_namespaced_pod.assert_not_called()


def test_static_controller_pod_resolves_owning_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy static run IDs identify a Pod whose owning Job must be stopped.

    Args:
        monkeypatch: Pytest patching fixture.
    """
    state = setup_stop(monkeypatch)
    state.run.orchestrator_run_id = "controller-pod"
    state.core.read_namespaced_pod.side_effect = None
    state.core.read_namespaced_pod.return_value = k8s_client.V1Pod(
        metadata=k8s_client.V1ObjectMeta(
            name="controller-pod", labels={"job-name": "controller-job"}
        )
    )
    state.orchestrator._stop_run(state.run, graceful=False)
    assert (
        state.batch.delete_namespaced_job.call_args.kwargs["name"]
        == "controller-job"
    )


def test_graceful_stop_does_not_delete_current_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The controller handles graceful drain without provider deletion here.

    Args:
        monkeypatch: Pytest patching fixture.
    """
    state = setup_stop(monkeypatch)
    state.orchestrator._stop_run(state.run, graceful=True)
    state.batch.list_namespaced_job.assert_not_called()
    state.batch.delete_namespaced_job.assert_not_called()


def test_isolated_stop_deletes_all_attempt_jobs_and_ignores_absence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A concurrent delete is harmless, and no matching Job is left out.

    Args:
        monkeypatch: Pytest patching fixture.
    """
    state = setup_stop(monkeypatch)
    attempt_id = uuid4()
    state.batch.list_namespaced_job.return_value = k8s_client.V1JobList(
        items=[make_job("one"), make_job("two")]
    )
    state.batch.delete_namespaced_job.side_effect = [
        ApiException(status=404),
        None,
    ]
    state.orchestrator.stop_isolated_step(SimpleNamespace(id=attempt_id))
    assert state.batch.delete_namespaced_job.call_count == 2
    assert (
        state.batch.list_namespaced_job.call_args.kwargs["label_selector"]
        == f"step_run_id={attempt_id}"
    )


@pytest.mark.parametrize("operation", ["list", "delete"])
def test_provider_errors_are_not_reported_as_success(
    monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    """Failure to access Kubernetes propagates to stop handling.

    Args:
        monkeypatch: Pytest patching fixture.
        operation: Provider operation configured to fail.
    """
    state = setup_stop(monkeypatch)
    if operation == "list":
        state.batch.list_namespaced_job.side_effect = ApiException(status=403)
        expected = ApiException
    else:
        state.batch.delete_namespaced_job.side_effect = ApiException(
            status=403
        )
        expected = RuntimeError
    with pytest.raises(expected):
        state.orchestrator._stop_run(state.run, graceful=False)


def test_finished_jobs_are_left_for_normal_retention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stopping work does not require removing completed Job records.

    Args:
        monkeypatch: Pytest patching fixture.
    """
    state = setup_stop(monkeypatch)
    finished = make_job("completed")
    finished.status = k8s_client.V1JobStatus(
        conditions=[k8s_client.V1JobCondition(type="Complete", status="True")]
    )
    state.batch.list_namespaced_job.return_value = k8s_client.V1JobList(
        items=[finished, make_job("controller", controller=True)]
    )
    state.orchestrator._stop_run(state.run, graceful=False)
    assert [
        call.kwargs["name"]
        for call in state.batch.delete_namespaced_job.call_args_list
    ] == ["controller"]
