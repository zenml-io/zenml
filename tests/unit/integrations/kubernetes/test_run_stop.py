"""Tests for run cleanup ownership and finalization with mocked providers."""

from contextlib import nullcontext
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from zenml.enums import (
    ExecutionStatus,
    PipelineRunStopMode,
    StackComponentType,
)
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
    KubernetesOrchestratorConfig,
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.orchestrators import (
    kubernetes_orchestrator as module,
)
from zenml.orchestrators import base_orchestrator
from zenml.utils import run_utils


def setup_stop(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Build a controller and store that never access configured infrastructure.

    Args:
        monkeypatch: Pytest patching fixture.

    Returns:
        Test state containing the public orchestrator and captured updates.
    """
    run = SimpleNamespace(
        id=uuid4(),
        project_id=uuid4(),
        name="test-run",
        status=ExecutionStatus.FAILED,
        stop_mode=None,
        in_progress=True,
        child_key=None,
        orchestrator_run_id="controller",
        run_metadata={},
        snapshot=SimpleNamespace(stack=object()),
        get_body=lambda: SimpleNamespace(model_fields_set={"stop_mode"}),
    )
    updates: list[Any] = []
    updated_run_ids: list[Any] = []
    steps: list[Any] = []
    children: list[Any] = []
    cleanups: list[Any] = []

    def update_run(**kwargs: Any) -> SimpleNamespace:
        update = kwargs["run_update"]
        updates.append(update)
        updated_run_ids.append(kwargs["run_id"])
        if update.stop_mode:
            run.stop_mode = update.stop_mode
        return run

    client = SimpleNamespace(
        get_pipeline_run=lambda run_id, **kwargs: next(
            (child for child in children if child.id == run_id), run
        ),
        create_run_metadata=lambda **kwargs: run.run_metadata.update(
            kwargs["metadata"]
        ),
        list_pipeline_runs=lambda **kwargs: (
            children if kwargs["parent_run_id"] == run.id else []
        ),
        list_run_steps=lambda **kwargs: steps,
        zen_store=SimpleNamespace(
            update_run=update_run,
            update_run_step=lambda **kwargs: None,
        ),
    )
    monkeypatch.setattr(module, "Client", lambda: client)
    monkeypatch.setattr(base_orchestrator, "Client", lambda: client)
    monkeypatch.setattr(run_utils, "Client", lambda: client)
    monkeypatch.setattr(
        module.pagination_utils,
        "depaginate",
        lambda method, **kwargs: iter(method(**kwargs)),
    )
    monkeypatch.setattr(
        module, "stop_workloads", lambda **kwargs: cleanups.append(kwargs)
    )
    monkeypatch.setattr(
        module.KubernetesOrchestrator, "get_kube_client", lambda self: None
    )
    monkeypatch.setattr(
        module.k8s_client, "BatchV1Api", lambda *args: object()
    )
    monkeypatch.setattr(module.k8s_client, "CoreV1Api", lambda *args: object())
    monkeypatch.setattr(
        module.KubernetesOrchestrator,
        "get_settings",
        lambda *args: KubernetesOrchestratorSettings(stop_timeout=0.1),
    )
    orchestrator = module.KubernetesOrchestrator(
        name="test",
        id=uuid4(),
        config=KubernetesOrchestratorConfig(),
        flavor="kubernetes",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    return SimpleNamespace(
        run=run,
        updates=updates,
        updated_run_ids=updated_run_ids,
        steps=steps,
        children=children,
        cleanups=cleanups,
        orchestrator=orchestrator,
    )


def test_immediate_root_cleanup_includes_descendants_preserves_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verified cleanup ends activity without replacing a failed outcome."""
    state = setup_stop(monkeypatch)
    child = SimpleNamespace(id=uuid4(), status=ExecutionStatus.RUNNING)
    state.children.append(child)
    state.orchestrator.stop_run(state.run, graceful=False)
    assert state.updates[0].stop_mode == PipelineRunStopMode.IMMEDIATE
    assert state.cleanups[0]["run_ids"] == {str(state.run.id), str(child.id)}
    assert state.cleanups[0]["include_controller"] is True
    assert state.updates[-1].status == ExecutionStatus.FAILED
    assert state.updates[-1].in_progress is False
    assert state.updated_run_ids[-2:] == [child.id, state.run.id]


def test_child_cleanup_requires_shared_controller_acknowledgement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No Job remaining does not prove inline child execution terminated."""
    state = setup_stop(monkeypatch)
    state.run.child_key = "child"
    with pytest.raises(RuntimeError, match="shared controller"):
        state.orchestrator.stop_run(state.run, graceful=False)
    assert state.cleanups[0]["include_controller"] is False
    assert all(update.in_progress is None for update in state.updates)


@pytest.mark.parametrize("can_confirm", [True, False])
@pytest.mark.parametrize(
    "step_status", [ExecutionStatus.RUNNING, ExecutionStatus.FAILED]
)
def test_external_step_operator_requires_termination_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    can_confirm: bool,
    step_status: ExecutionStatus,
) -> None:
    """Deleting Kubernetes launchers alone cannot settle external workloads."""
    state = setup_stop(monkeypatch)
    cancelled = []
    operator = SimpleNamespace(
        cancel=lambda step: cancelled.append(step.id),
        get_status=lambda step: (
            ExecutionStatus.STOPPED
            if can_confirm and cancelled
            else ExecutionStatus.RUNNING
        ),
    )
    monkeypatch.setattr(
        module.Stack,
        "from_model",
        lambda model: SimpleNamespace(step_operators={"external": operator}),
    )
    step = SimpleNamespace(
        id=uuid4(),
        pipeline_run_id=state.run.id,
        status=step_status,
        config=SimpleNamespace(step_operator="external"),
    )
    state.steps.append(step)
    if can_confirm:
        state.orchestrator.stop_run(state.run, graceful=False)
        assert state.updates[-1].in_progress is False
    else:
        with pytest.raises(RuntimeError, match="step operator|Step operator"):
            state.orchestrator.stop_run(state.run, graceful=False)
        assert all(update.in_progress is None for update in state.updates)
    assert cancelled == [step.id]


def test_missing_submission_identity_is_not_confirmed_by_empty_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A submission that has not published its identity remains unresolved."""
    state = setup_stop(monkeypatch)
    state.run.orchestrator_run_id = None
    with pytest.raises(RuntimeError, match="not been acknowledged"):
        state.orchestrator.stop_run(state.run, graceful=False)
    assert all(update.in_progress is None for update in state.updates)


def test_recorded_job_name_does_not_confirm_inflight_submission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An identity recorded before create does not acknowledge API completion."""
    state = setup_stop(monkeypatch)
    state.run.orchestrator_run_id = None
    state.run.run_metadata["orchestrator_job_name"] = "pending-controller"
    with pytest.raises(RuntimeError, match="not been acknowledged"):
        state.orchestrator.stop_run(state.run, graceful=False)
    assert state.cleanups[0]["job_names"] == {"pending-controller"}
    assert all(update.in_progress is None for update in state.updates)


def test_isolated_status_propagates_discovery_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unavailable API cannot prove that a worker terminated."""
    state = setup_stop(monkeypatch)

    def fail(**kwargs: Any) -> None:
        raise RuntimeError("API unavailable")

    monkeypatch.setattr(module.kube_utils, "list_jobs", fail)
    with pytest.raises(RuntimeError, match="API unavailable"):
        state.orchestrator.get_isolated_step_status(
            SimpleNamespace(id=uuid4())
        )


def test_isolated_status_waits_for_all_matching_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One terminal Job cannot hide another replacement still running."""
    state = setup_stop(monkeypatch)
    monkeypatch.setattr(
        module.kube_utils,
        "list_jobs",
        lambda **kwargs: SimpleNamespace(
            items=[
                SimpleNamespace(metadata=SimpleNamespace(name=name))
                for name in ["completed", "running"]
            ]
        ),
    )
    monkeypatch.setattr(
        module.kube_utils,
        "check_job_status",
        lambda **kwargs: (
            module.kube_utils.JobStatus.SUCCEEDED
            if kwargs["job_name"] == "completed"
            else module.kube_utils.JobStatus.RUNNING,
            None,
        ),
    )
    assert (
        state.orchestrator.get_isolated_step_status(
            SimpleNamespace(id=uuid4())
        )
        == ExecutionStatus.RUNNING
    )


@pytest.mark.parametrize(
    "submission_outcome", ["success", "ambiguous", "aborted"]
)
def test_controller_submit_reconciles_stop_even_after_ambiguous_response(
    monkeypatch: pytest.MonkeyPatch,
    submission_outcome: str,
) -> None:
    """The submitting caller acknowledges only successful or unsent creates."""
    state = setup_stop(monkeypatch)
    state.run.orchestrator_run_id = None
    created = []

    def create_job(**kwargs: Any) -> None:
        created.append(kwargs)
        state.run.stop_mode = PipelineRunStopMode.IMMEDIATE
        if submission_outcome == "ambiguous":
            raise RuntimeError("create response lost")

    monkeypatch.setattr(module.kube_utils, "create_job", create_job)
    monkeypatch.setattr(
        module.KubernetesOrchestrator,
        "get_image",
        lambda *args, **kwargs: "image",
    )
    monkeypatch.setattr(
        module.KubernetesOrchestrator,
        "_get_job_name",
        lambda *args, **kwargs: "controller-job",
    )
    monkeypatch.setattr(
        module.KubernetesOrchestrator,
        "_prepare_job_manifest",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        module.KubernetesOrchestrator,
        "_create_auth_secret_if_necessary",
        lambda *args, **kwargs: nullcontext(),
    )
    snapshot = SimpleNamespace(
        pipeline_configuration=SimpleNamespace(name="pipeline"),
        project_id=state.run.project_id,
        schedule=None,
    )
    if submission_outcome == "aborted":
        state.run.stop_mode = PipelineRunStopMode.GRACEFUL
    expected = (
        "create response lost"
        if submission_outcome == "ambiguous"
        else "Pipeline stopped"
    )
    with pytest.raises(Exception, match=expected):
        state.orchestrator._submit_orchestrator_job(
            snapshot=snapshot,
            command=[],
            args=[],
            environment={},
            placeholder_run=state.run,
        )
    assert state.cleanups[0]["job_names"] == {"controller-job"}
    if submission_outcome == "ambiguous":
        assert not any(update.in_progress is False for update in state.updates)
    else:
        assert state.updates[-1].in_progress is False
    assert bool(created) is (submission_outcome != "aborted")
