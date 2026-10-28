"""Focused Kubernetes stop tests without cluster access."""

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
    PipelineRunStopMode,
    StackComponentType,
)
from zenml.exceptions import AuthorizationException
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
from zenml.integrations.kubernetes.orchestrators import (
    kubernetes_orchestrator_entrypoint as entrypoint,
)
from zenml.orchestrators import publish_utils
from zenml.orchestrators.dag_runner import Node


def setup_stop(
    monkeypatch: pytest.MonkeyPatch,
    config: KubernetesOrchestratorConfig | None = None,
) -> SimpleNamespace:
    """Create an orchestrator backed only by test doubles.

    Args:
        monkeypatch: Pytest patching fixture.
        config: Optional orchestrator configuration for the test.

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
        stop_mode=None,
        snapshot=SimpleNamespace(id=uuid4(), schedule=None),
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
    monkeypatch.setattr(
        module.KubernetesOrchestrator,
        "get_settings",
        lambda self, run: KubernetesOrchestratorSettings(),
    )
    monkeypatch.setattr(k8s_client, "BatchV1Api", lambda *args: batch_api)
    monkeypatch.setattr(k8s_client, "CoreV1Api", lambda *args: core_api)
    orchestrator = module.KubernetesOrchestrator(
        name="test",
        id=uuid4(),
        config=config or KubernetesOrchestratorConfig(max_api_retries=0),
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


def test_isolated_stop_ignores_concurrent_deletion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent run-level deletion does not fail a step stop.

    Args:
        monkeypatch: Pytest patching fixture.
    """
    state = setup_stop(monkeypatch)
    attempt_id = uuid4()
    state.batch.list_namespaced_job.return_value = k8s_client.V1JobList(
        items=[make_job("step")]
    )
    state.batch.delete_namespaced_job.side_effect = ApiException(status=404)
    state.orchestrator.stop_isolated_step(SimpleNamespace(id=attempt_id))
    state.batch.delete_namespaced_job.assert_called_once_with(
        name="step", namespace="zenml", propagation_policy="Foreground"
    )
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
    else:
        state.batch.delete_namespaced_job.side_effect = ApiException(
            status=403
        )
    with pytest.raises(RuntimeError):
        state.orchestrator._stop_run(state.run, graceful=False)


def test_isolated_stop_list_failure_does_not_complete_retry_drain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dynamic graceful stopping must retry a failed Job lookup.

    Args:
        monkeypatch: Pytest patching fixture.
    """
    state = setup_stop(monkeypatch)
    state.batch.list_namespaced_job.side_effect = ApiException(status=403)
    with pytest.raises(ApiException):
        state.orchestrator.stop_isolated_step(SimpleNamespace(id=uuid4()))


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


@pytest.mark.parametrize(
    "graceful,child,scheduled,delete_status,clean_secret",
    [
        (False, False, False, None, True),
        (False, False, False, 404, True),
        (False, False, False, 403, False),
        (False, False, True, None, False),
        (False, True, False, None, False),
        (True, False, False, None, False),
    ],
)
def test_controller_stop_cleans_only_its_nonscheduled_token_secret(
    monkeypatch: pytest.MonkeyPatch,
    graceful: bool,
    child: bool,
    scheduled: bool,
    delete_status: int | None,
    clean_secret: bool,
) -> None:
    """Controller deletion replaces its finally cleanup without shared deletion.

    Args:
        monkeypatch: Pytest patching fixture.
        graceful: Whether to let the controller finish naturally.
        child: Whether only a child pipeline is stopped.
        scheduled: Whether future scheduled runs share the Secret.
        delete_status: Optional Job deletion failure status.
        clean_secret: Whether the Secret must be deleted.
    """
    state = setup_stop(
        monkeypatch,
        KubernetesOrchestratorConfig(
            max_api_retries=0, pass_zenml_token_as_secret=True
        ),
    )
    state.run.child_key = "child" if child else None
    state.run.snapshot.schedule = object() if scheduled else None
    state.batch.list_namespaced_job.return_value = k8s_client.V1JobList(
        items=[make_job("controller", controller=True)]
    )
    if delete_status:
        state.batch.delete_namespaced_job.side_effect = ApiException(
            status=delete_status
        )

    if delete_status == 403:
        with pytest.raises(RuntimeError):
            state.orchestrator._stop_run(state.run, graceful=graceful)
    else:
        state.orchestrator._stop_run(state.run, graceful=graceful)

    if clean_secret:
        state.core.delete_namespaced_secret.assert_called_once_with(
            name=f"zenml-token-{state.run.snapshot.id}", namespace="zenml"
        )
    else:
        state.core.delete_namespaced_secret.assert_not_called()


def setup_entrypoint(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Prepare the static entrypoint with mocked storage and Kubernetes APIs.

    Args:
        monkeypatch: Pytest patching fixture.

    Returns:
        Stop state with entrypoint dependency mocks.
    """
    state = setup_stop(
        monkeypatch,
        KubernetesOrchestratorConfig(
            max_api_retries=0, skip_owner_references=True
        ),
    )
    state.run.snapshot.pipeline_configuration = SimpleNamespace(name="test")
    state.run.snapshot.step_configurations = {}
    state.run.snapshot.project_id = state.run.project_id
    state.client.get_snapshot.return_value = state.run.snapshot
    state.client.active_stack = SimpleNamespace(
        orchestrator=state.orchestrator
    )
    state.client.active_user = SimpleNamespace(id=uuid4(), oidc_claims={})
    monkeypatch.setattr(entrypoint, "Client", lambda: state.client)
    monkeypatch.setattr(
        entrypoint,
        "parse_args",
        lambda: SimpleNamespace(snapshot_id=state.run.snapshot.id),
    )
    monkeypatch.setattr(
        entrypoint, "is_pipeline_logging_enabled", lambda _: False
    )
    monkeypatch.setattr(
        module.KubernetesOrchestrator,
        "get_kube_client",
        lambda self, **kwargs: SimpleNamespace(
            configuration=SimpleNamespace()
        ),
    )
    monkeypatch.setattr(k8s_client, "ApiClient", lambda *_: None)
    monkeypatch.setattr(
        kube_utils, "get_parent_job_name", lambda **_: "controller"
    )
    monkeypatch.setattr(
        entrypoint,
        "_get_orchestrator_job_state",
        lambda **_: (state.run.id, "controller-pod"),
    )
    monkeypatch.setattr(entrypoint, "_reconstruct_nodes", lambda **_: [])
    monkeypatch.setattr(entrypoint, "StepRunRequestFactory", Mock())
    monkeypatch.setattr(
        entrypoint, "get_config_environment_vars", lambda: ({}, {})
    )
    state.fetch_steps = Mock(return_value={})
    monkeypatch.setattr(
        entrypoint, "fetch_step_runs_by_names", state.fetch_steps
    )
    state.dag_runner = Mock()
    state.dag_runner.return_value.run.return_value = {}
    monkeypatch.setattr(entrypoint, "DagRunner", state.dag_runner)
    state.publish_status = Mock()
    monkeypatch.setattr(
        publish_utils,
        "publish_pipeline_run_status_update",
        state.publish_status,
    )
    return state


def test_static_stop_disambiguates_colliding_step_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A truncated label collision must not stop another step's Job.

    Args:
        monkeypatch: Pytest patching fixture.
    """
    state = setup_entrypoint(monkeypatch)
    step_name = "a" * 63 + "-requested"
    other_name = "a" * 63 + "-unrelated"
    label = kube_utils.sanitize_label_value(step_name)
    assert label == kube_utils.sanitize_label_value(other_name)
    jobs = [make_job("unrelated-job"), make_job("requested-job")]
    for job, annotation in zip(jobs, [other_name, step_name]):
        job.metadata.labels = {"step_name": label}
        job.metadata.annotations[STEP_NAME_ANNOTATION_KEY] = annotation
        job.status = k8s_client.V1JobStatus(conditions=[])
    state.batch.list_namespaced_job.return_value = k8s_client.V1JobList(
        items=jobs
    )

    def stop_requested_step() -> dict[str, Any]:
        """Run the real stop callback supplied to the mocked DAG runner.

        Returns:
            Empty terminal node states for entrypoint finalization.
        """
        state.dag_runner.call_args.kwargs["node_stop_function"](
            Node(id=step_name)
        )
        return {}

    state.dag_runner.return_value.run.side_effect = stop_requested_step
    entrypoint.main()

    state.batch.delete_namespaced_job.assert_called_once_with(
        name="requested-job",
        namespace="zenml",
        propagation_policy="Foreground",
    )


@pytest.mark.parametrize("failure", [None, "settlement", "read", "publish"])
def test_static_finalization_tolerates_invalidated_token(
    monkeypatch: pytest.MonkeyPatch, failure: str | None
) -> None:
    """Token invalidation during finalization must not crash the controller.

    Args:
        monkeypatch: Pytest patching fixture.
        failure: Finalization operation where the runtime token is invalidated.
    """
    state = setup_entrypoint(monkeypatch)
    state.run.stop_mode = PipelineRunStopMode.GRACEFUL
    error = AuthorizationException("Runtime token invalidated")
    if failure == "settlement":
        state.fetch_steps.side_effect = error
    elif failure == "read":
        state.client.get_pipeline_run.side_effect = [state.run, error]
    elif failure == "publish":
        state.publish_status.side_effect = error

    entrypoint.main()

    if failure in {"settlement", "read"}:
        state.publish_status.assert_not_called()
    else:
        state.publish_status.assert_called_once_with(
            state.run.id, ExecutionStatus.STOPPED
        )
