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
from zenml.exceptions import AuthorizationException, RunStoppedException
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
from zenml.orchestrators import base_orchestrator, publish_utils
from zenml.orchestrators.dag_runner import InterruptMode, Node, NodeStatus


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
    publish_status = Mock()
    monkeypatch.setattr(
        module, "publish_pipeline_run_status_update", publish_status
    )
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
        publish_status=publish_status,
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


@pytest.mark.parametrize("target", ["root", "child", "unowned"])
def test_immediate_stop_cleans_workers_and_preserves_needed_controller(
    monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    """Stop descendants while retaining a controller needed for later cleanup.

    Args:
        monkeypatch: Pytest patching fixture.
        target: Root, child, or root with worker ownership disabled.
    """
    state = setup_stop(
        monkeypatch,
        KubernetesOrchestratorConfig(
            max_api_retries=0, skip_owner_references=target == "unowned"
        ),
    )
    state.run.child_key = "child" if target == "child" else None
    state.run.stop_mode = PipelineRunStopMode.IMMEDIATE
    child = SimpleNamespace(id=uuid4())
    state.children.append(child)
    state.batch.list_namespaced_job.return_value = k8s_client.V1JobList(
        items=[make_job("worker"), make_job("controller", controller=True)]
    )

    state.orchestrator._stop_run(state.run, graceful=False)

    deletions = state.batch.delete_namespaced_job.call_args_list
    expected = {"worker", "controller"} if target == "root" else {"worker"}
    assert {call.kwargs["name"] for call in deletions} == expected
    assert all(
        call.kwargs["propagation_policy"] == "Foreground" for call in deletions
    )
    selector = state.batch.list_namespaced_job.call_args.kwargs[
        "label_selector"
    ]
    assert str(state.run.id) in selector and str(child.id) in selector
    if target == "root":
        state.publish_status.assert_called_once_with(
            pipeline_run_id=state.run.id, status=ExecutionStatus.STOPPED
        )
    else:
        state.publish_status.assert_not_called()


@pytest.mark.parametrize("skip_owner_references", [False, True])
def test_stop_finalizes_failed_run_with_terminal_controller(
    monkeypatch: pytest.MonkeyPatch,
    skip_owner_references: bool,
) -> None:
    """A public stop request must settle work when its controller is dead.

    Args:
        monkeypatch: Pytest patching fixture.
        skip_owner_references: Whether worker ownership is disabled.
    """
    state = setup_stop(
        monkeypatch,
        KubernetesOrchestratorConfig(
            max_api_retries=0,
            skip_owner_references=skip_owner_references,
        ),
    )
    state.run.stop_mode = PipelineRunStopMode.IMMEDIATE
    state.client.zen_store.update_run.return_value = state.run
    monkeypatch.setattr(base_orchestrator, "Client", lambda: state.client)
    controller = make_job("controller", controller=True)
    controller.status = k8s_client.V1JobStatus(
        conditions=[k8s_client.V1JobCondition(type="Failed", status="True")]
    )
    state.batch.list_namespaced_job.return_value = k8s_client.V1JobList(
        items=[make_job("worker"), controller]
    )
    operations: list[str] = []
    state.batch.delete_namespaced_job.side_effect = lambda **kwargs: (
        operations.append("delete-worker")
    )
    state.publish_status.side_effect = lambda **kwargs: operations.append(
        "finalize-run"
    )

    state.orchestrator.stop_run(state.run, graceful=False)

    assert operations == ["delete-worker", "finalize-run"]
    state.batch.delete_namespaced_job.assert_called_once_with(
        name="worker", namespace="zenml", propagation_policy="Foreground"
    )
    state.publish_status.assert_called_once_with(
        pipeline_run_id=state.run.id, status=ExecutionStatus.STOPPED
    )
    assert state.run.status == ExecutionStatus.FAILED


def setup_submission(
    monkeypatch: pytest.MonkeyPatch,
    *,
    skip_owner_references: bool = False,
) -> SimpleNamespace:
    """Prepare an isolated submission with a root controller Pod owner.

    Args:
        monkeypatch: Pytest patching fixture.
        skip_owner_references: Whether to opt out of worker ownership.

    Returns:
        Stop fixtures extended with the worker's submission information.
    """
    state = setup_stop(
        monkeypatch,
        KubernetesOrchestratorConfig(
            max_api_retries=0, skip_owner_references=skip_owner_references
        ),
    )
    state.run.status = ExecutionStatus.RUNNING
    state.info = SimpleNamespace(
        pipeline_step_name="worker",
        step_run_id=uuid4(),
        run_id=state.run.id,
        run_name=state.run.name,
        snapshot=SimpleNamespace(id=uuid4(), project_id=state.run.project_id),
        pipeline=SimpleNamespace(name="pipeline"),
        config=object(),
        get_image=lambda **kwargs: "image",
    )
    monkeypatch.setattr(
        module.orchestrator_utils,
        "get_step_entrypoint_command",
        lambda **kwargs: (["python"], ["step.py"]),
    )
    monkeypatch.setattr(
        module.KubernetesOrchestrator,
        "_get_job_name",
        lambda *args, **kwargs: "worker-job",
    )
    monkeypatch.setattr(
        module.KubernetesOrchestrator,
        "_prepare_job_manifest",
        lambda *args, **kwargs: make_job("worker-job"),
    )
    monkeypatch.setattr(module.socket, "gethostname", lambda: "root-pod")
    state.core.read_namespaced_pod.side_effect = None
    state.core.read_namespaced_pod.return_value = k8s_client.V1Pod(
        metadata=k8s_client.V1ObjectMeta(
            name="root-pod",
            owner_references=[
                k8s_client.V1OwnerReference(
                    api_version="batch/v1",
                    kind="Job",
                    name="root-controller",
                    uid="root-controller-uid",
                    controller=True,
                    block_owner_deletion=True,
                )
            ],
        )
    )
    return state


@pytest.mark.parametrize("ownership", ["enabled", "disabled", "missing"])
def test_dynamic_worker_ownership(
    monkeypatch: pytest.MonkeyPatch, ownership: str
) -> None:
    """Child workers require root ownership unless it was explicitly disabled.

    Args:
        monkeypatch: Pytest patching fixture.
        ownership: Available, disabled, or missing controller ownership.
    """
    state = setup_submission(
        monkeypatch, skip_owner_references=ownership == "disabled"
    )
    state.run.child_key = "child"
    if ownership == "missing":
        state.core.read_namespaced_pod.return_value.metadata.owner_references = []
        with pytest.raises(RuntimeError, match="controller Job owner"):
            state.orchestrator.submit_isolated_step_with_allocation(
                state.info, environment={}, allocated_resource_request=None
            )
        state.batch.create_namespaced_job.assert_not_called()
        return

    state.orchestrator.submit_isolated_step_with_allocation(
        state.info, environment={}, allocated_resource_request=None
    )

    manifest = state.batch.create_namespaced_job.call_args.kwargs["body"]
    if ownership == "disabled":
        assert manifest.metadata.owner_references is None
        state.core.read_namespaced_pod.assert_not_called()
    else:
        (owner,) = manifest.metadata.owner_references
        assert (owner.kind, owner.name, owner.uid) == (
            "Job",
            "root-controller",
            "root-controller-uid",
        )
        assert owner.controller is False
        assert owner.block_owner_deletion is False


@pytest.mark.parametrize("token_invalidated", [False, True])
def test_dynamic_submission_cleans_job_created_during_stop(
    monkeypatch: pytest.MonkeyPatch, token_invalidated: bool
) -> None:
    """A stop racing with creation is cleaned before publishing metadata.

    Args:
        monkeypatch: Pytest patching fixture.
        token_invalidated: Whether the stopped run's token already expired.
    """
    state = setup_submission(monkeypatch, skip_owner_references=True)
    state.run.child_key = "child"

    def accept_late_job(**kwargs: Any) -> None:
        """Accept a worker after an immediate stop was persisted.

        Args:
            kwargs: Kubernetes creation request arguments.
        """
        state.run.stop_mode = PipelineRunStopMode.IMMEDIATE
        if token_invalidated:
            state.client.get_pipeline_run.side_effect = AuthorizationException(
                "Runtime token invalidated"
            )

    state.batch.create_namespaced_job.side_effect = accept_late_job
    expected_error = (
        AuthorizationException if token_invalidated else RunStoppedException
    )

    with pytest.raises(expected_error):
        state.orchestrator.submit_isolated_step_with_allocation(
            state.info, environment={}, allocated_resource_request=None
        )

    state.batch.delete_namespaced_job.assert_called_once_with(
        name="worker-job", namespace="zenml", propagation_policy="Foreground"
    )
    state.client.create_run_metadata.assert_not_called()


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
    state.run.stop_mode = PipelineRunStopMode.IMMEDIATE
    if operation == "list":
        state.batch.list_namespaced_job.side_effect = ApiException(status=403)
    else:
        state.batch.delete_namespaced_job.side_effect = ApiException(
            status=403
        )
    with pytest.raises(RuntimeError):
        state.orchestrator._stop_run(state.run, graceful=False)
    state.publish_status.assert_not_called()


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


def setup_entrypoint(
    monkeypatch: pytest.MonkeyPatch, *, skip_owner_references: bool = True
) -> SimpleNamespace:
    """Prepare the static entrypoint with mocked storage and Kubernetes APIs.

    Args:
        monkeypatch: Pytest patching fixture.
        skip_owner_references: Whether to opt out of worker ownership.

    Returns:
        Stop state with entrypoint dependency mocks.
    """
    state = setup_stop(
        monkeypatch,
        KubernetesOrchestratorConfig(
            max_api_retries=0, skip_owner_references=skip_owner_references
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


@pytest.mark.parametrize("lookup_fails", [False, True])
def test_static_startup_requires_controller_job_ownership(
    monkeypatch: pytest.MonkeyPatch, lookup_fails: bool
) -> None:
    """Default startup must not create unowned workers after a lookup failure.

    Args:
        monkeypatch: Pytest patching fixture.
        lookup_fails: Whether lookup raises instead of returning no owners.
    """
    state = setup_entrypoint(monkeypatch, skip_owner_references=False)
    lookup = Mock(return_value=[])
    if lookup_fails:
        lookup.side_effect = ApiException(status=403)
    monkeypatch.setattr(kube_utils, "get_pod_owner_references", lookup)

    with pytest.raises(RuntimeError, match="controller Job owner"):
        entrypoint.main()

    state.dag_runner.assert_not_called()
    state.batch.create_namespaced_job.assert_not_called()


def test_static_monitor_reuses_stop_request_from_interrupt_poll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Polling stop intent once must suffice to drain multiple retrying nodes.

    Args:
        monkeypatch: Pytest patching fixture.
    """
    state = setup_entrypoint(monkeypatch)
    state.run.snapshot.step_configurations = {
        "first": object(),
        "second": object(),
    }
    state.client.list_run_steps.return_value = SimpleNamespace(
        items=[SimpleNamespace(status=ExecutionStatus.RETRYING)]
    )

    def monitor_stopped_nodes() -> dict[str, NodeStatus]:
        """Poll the stop request, then monitor both active nodes.

        Returns:
            Terminal node states after retry cleanup.
        """
        callbacks = state.dag_runner.call_args.kwargs
        state.run.stop_mode = PipelineRunStopMode.GRACEFUL
        state.client.get_pipeline_run.reset_mock()
        assert callbacks["interrupt_function"]() == InterruptMode.GRACEFUL
        assert state.client.get_pipeline_run.call_count == 1
        result = {
            name: callbacks["node_monitoring_function"](
                Node(id=name, metadata={"job_name": name})
            )
            for name in ("first", "second")
        }
        assert result == dict.fromkeys(result, NodeStatus.CANCELLED)
        assert state.client.get_pipeline_run.call_count == 1
        return result

    state.dag_runner.return_value.run.side_effect = monitor_stopped_nodes

    entrypoint.main()

    assert state.client.list_run_steps.call_count == 2
    state.publish_status.assert_called_once_with(
        state.run.id, ExecutionStatus.STOPPED
    )
