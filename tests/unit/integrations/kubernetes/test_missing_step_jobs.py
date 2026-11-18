#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Tests for steps whose Kubernetes job is deleted before it is checked.

Kubernetes deletes finished jobs once `ttlSecondsAfterFinished` expires, so a
missing job must not be treated as a failure of the step by itself.
"""

import argparse
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Union
from unittest.mock import MagicMock, PropertyMock, patch
from uuid import uuid4

import pytest
from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException

from zenml.enums import ExecutionStatus, StackComponentType
from zenml.integrations.kubernetes import kube_utils
from zenml.integrations.kubernetes.flavors import (
    KubernetesStepOperatorConfig,
)
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
    KubernetesOrchestratorConfig,
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.orchestrators import (
    KubernetesOrchestrator,
    kubernetes_orchestrator_entrypoint,
)
from zenml.integrations.kubernetes.step_operators import KubernetesStepOperator
from zenml.orchestrators import dag_runner
from zenml.orchestrators.dag_runner import DagRunner, Node, NodeStatus


def _attempt(
    status: ExecutionStatus,
    heartbeat_threshold: Optional[int] = None,
    latest_heartbeat: Optional[datetime] = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        status=status,
        start_time=None,
        heartbeat_threshold=heartbeat_threshold,
        latest_heartbeat=latest_heartbeat,
    )


def _job(condition_type: Optional[str] = None) -> k8s_client.V1Job:
    conditions = []
    if condition_type:
        conditions.append(
            k8s_client.V1JobCondition(type=condition_type, status="True")
        )
    return k8s_client.V1Job(
        status=k8s_client.V1JobStatus(conditions=conditions)
    )


def _job_not_found() -> k8s_client.V1Job:
    raise ApiException(status=404, reason="Not Found")


def _list_run_steps(attempts: List[SimpleNamespace]) -> Callable[..., Any]:
    """Build a fake that returns the oldest attempt first, like the store.

    Args:
        attempts: The attempts of the step, oldest first.

    Returns:
        A replacement for `Client.list_run_steps`.
    """

    def list_run_steps(
        exclude_retried: Optional[bool] = None, **_: Any
    ) -> SimpleNamespace:
        return SimpleNamespace(
            items=[
                attempt
                for attempt in attempts
                if not (
                    exclude_retried
                    and attempt.status == ExecutionStatus.RETRIED
                )
            ]
        )

    return list_run_steps


class OrchestratorRun(NamedTuple):
    """The outcome of running the orchestrator entrypoint."""

    statuses: Dict[str, NodeStatus]
    publish_utils: MagicMock
    client: MagicMock


def _run_orchestrator(
    monkeypatch: pytest.MonkeyPatch,
    job_a_reader: Callable[[], k8s_client.V1Job],
    attempts: List[SimpleNamespace],
) -> OrchestratorRun:
    """Run the orchestrator entrypoint for the pipeline `a -> b`.

    The monitoring closures, the `DagRunner` and `kube_utils.check_job_status`
    are the real ones. Only external services and job creation are replaced.

    Args:
        monkeypatch: The pytest monkeypatch fixture.
        job_a_reader: Serves reads of the job of step `a`. Step `b` always has
            a completed job.
        attempts: The step runs of step `a` in the DB, oldest first.

    Returns:
        The final node statuses, the mocked publish utils and the mocked client.
    """
    entrypoint = kubernetes_orchestrator_entrypoint

    def read_namespaced_job(name: str, **_: Any) -> k8s_client.V1Job:
        return job_a_reader() if name == "job-a" else _job("Complete")

    mock_k8s_client = MagicMock()
    batch_api = mock_k8s_client.BatchV1Api.return_value
    batch_api.read_namespaced_job.side_effect = read_namespaced_job

    orchestrator = MagicMock(spec=KubernetesOrchestrator)
    orchestrator.get_settings.return_value = KubernetesOrchestratorSettings(
        job_monitoring_interval=0.01
    )

    client = MagicMock()
    client.active_stack.orchestrator = orchestrator
    client.list_run_steps.side_effect = _list_run_steps(attempts)
    client.get_pipeline_run.return_value.status = ExecutionStatus.RUNNING
    client.get_snapshot.return_value.pipeline_configuration.name = "pipeline"
    client.get_snapshot.return_value.step_configurations = {
        "a": SimpleNamespace(spec=SimpleNamespace(upstream_steps=[])),
        "b": SimpleNamespace(spec=SimpleNamespace(upstream_steps=["a"])),
    }

    runners: List[DagRunner] = []

    def create_dag_runner(**kwargs: Any) -> DagRunner:
        def start_without_creating_a_job(node: Node) -> NodeStatus:
            node.metadata["job_name"] = f"job-{node.id}"
            return NodeStatus.RUNNING

        kwargs["node_startup_function"] = start_without_creating_a_job
        runners.append(DagRunner(**kwargs))
        return runners[-1]

    publish_utils = MagicMock()
    for name, replacement in {
        "Client": MagicMock(return_value=client),
        "DagRunner": create_dag_runner,
        "StepRunRequestFactory": MagicMock(),
        "_get_orchestrator_job_state": MagicMock(return_value=(None, None)),
        "create_placeholder_run": MagicMock(
            return_value=MagicMock(id=uuid4())
        ),
        "fetch_step_runs_by_names": MagicMock(return_value={}),
        "get_config_environment_vars": MagicMock(return_value=({}, {})),
        "is_pipeline_logging_enabled": MagicMock(return_value=False),
        "k8s_client": mock_k8s_client,
        "parse_args": MagicMock(
            return_value=argparse.Namespace(snapshot_id=uuid4(), run_id=None)
        ),
        "publish_utils": publish_utils,
    }.items():
        monkeypatch.setattr(entrypoint, name, replacement)
    monkeypatch.setattr(kube_utils, "get_parent_job_name", MagicMock())
    monkeypatch.setattr(kube_utils, "update_job", MagicMock())

    # `DagRunner.run` sleeps 0.5s per loop, which would dominate these tests.
    real_sleep = time.sleep
    monkeypatch.setattr(
        dag_runner,
        "time",
        SimpleNamespace(
            time=time.time,
            sleep=lambda seconds: real_sleep(min(seconds, 0.001)),
        ),
    )

    entrypoint.main()

    statuses = {
        node_id: node.status for node_id, node in runners[0].nodes.items()
    }
    return OrchestratorRun(statuses, publish_utils, client)


@pytest.mark.parametrize(
    "attempts",
    [
        [_attempt(ExecutionStatus.COMPLETED)],
        [
            _attempt(ExecutionStatus.RETRIED),
            _attempt(ExecutionStatus.COMPLETED),
        ],
    ],
    ids=["first_attempt", "after_retry"],
)
def test_deleted_job_of_successful_step_does_not_fail_the_run(
    attempts: List[SimpleNamespace], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test the reported bug: the step succeeded, then its job was deleted."""
    run = _run_orchestrator(monkeypatch, _job_not_found, attempts)

    assert run.statuses == {
        "a": NodeStatus.COMPLETED,
        "b": NodeStatus.COMPLETED,
    }
    run.publish_utils.publish_failed_pipeline_run.assert_not_called()


@pytest.mark.parametrize(
    "status", [ExecutionStatus.FAILED, ExecutionStatus.RUNNING]
)
def test_deleted_job_of_unsuccessful_step_fails_the_run(
    status: ExecutionStatus, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that a missing job doesn't hide a step that did not succeed."""
    run = _run_orchestrator(monkeypatch, _job_not_found, [_attempt(status)])

    assert run.statuses == {"a": NodeStatus.FAILED, "b": NodeStatus.SKIPPED}
    run.publish_utils.publish_failed_pipeline_run.assert_called_once()


def test_deleted_job_without_step_run_publishes_failed_step_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test a step that never got far enough to create a step run."""
    run = _run_orchestrator(monkeypatch, _job_not_found, attempts=[])

    assert run.statuses == {"a": NodeStatus.FAILED, "b": NodeStatus.SKIPPED}
    run.client.zen_store.create_run_step.assert_called_once()
    request = run.client.zen_store.create_run_step.call_args.args[0]
    assert request.status == ExecutionStatus.FAILED


def test_failed_job_uses_latest_attempt_of_retried_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that a successful retry overrides a job that reports a failure."""
    run = _run_orchestrator(
        monkeypatch,
        lambda: _job("Failed"),
        [
            _attempt(ExecutionStatus.RETRIED),
            _attempt(ExecutionStatus.COMPLETED),
        ],
    )

    assert run.statuses["a"] == NodeStatus.COMPLETED


def test_heartbeat_check_uses_latest_attempt_of_retried_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that a hung retry is detected instead of the old attempt's status.

    The job completes after a few reads, so ignoring the hung attempt fails the
    assertion rather than making the test run forever.
    """
    responses = iter([_job()] * 3)
    stale = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    run = _run_orchestrator(
        monkeypatch,
        lambda: next(responses, _job("Complete")),
        [
            _attempt(ExecutionStatus.RETRIED, heartbeat_threshold=1),
            _attempt(
                ExecutionStatus.RUNNING,
                heartbeat_threshold=1,
                latest_heartbeat=stale,
            ),
        ],
    )

    assert run.statuses == {"a": NodeStatus.FAILED, "b": NodeStatus.SKIPPED}


def _step_operator() -> KubernetesStepOperator:
    return KubernetesStepOperator(
        name="",
        id=uuid4(),
        config=KubernetesStepOperatorConfig(),
        flavor="kubernetes",
        type=StackComponentType.STEP_OPERATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _orchestrator() -> KubernetesOrchestrator:
    return KubernetesOrchestrator(
        name="",
        id=uuid4(),
        config=KubernetesOrchestratorConfig(),
        flavor="kubernetes",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _get_status_without_job(
    component: Union[KubernetesStepOperator, KubernetesOrchestrator],
    jobs: List[k8s_client.V1Job],
    db_status: ExecutionStatus,
) -> ExecutionStatus:
    """Get the status the component reports when it can't read the job.

    Args:
        component: The component that ran the step.
        jobs: The jobs listed for the step run. Reading any of them fails with
            a 404.
        db_status: The status of the step run in the DB.

    Returns:
        The status reported by the component.
    """
    batch_api = MagicMock()
    batch_api.list_namespaced_job.return_value = k8s_client.V1JobList(
        items=jobs
    )
    batch_api.read_namespaced_job.side_effect = ApiException(status=404)
    step_run: Any = SimpleNamespace(id=uuid4())

    with (
        patch.object(
            type(component),
            "_k8s_batch_api",
            new_callable=PropertyMock,
            return_value=batch_api,
        ),
        patch.object(
            type(component),
            "_k8s_core_api",
            new_callable=PropertyMock,
            return_value=MagicMock(),
        ),
        patch(f"{type(component).__module__}.Client") as client,
    ):
        client.return_value.get_run_step.return_value.status = db_status
        if isinstance(component, KubernetesStepOperator):
            return component.get_status(step_run)
        return component.get_isolated_step_status(step_run)


@pytest.mark.parametrize(
    "db_status,expected_status",
    [
        (ExecutionStatus.COMPLETED, ExecutionStatus.COMPLETED),
        (ExecutionStatus.FAILED, ExecutionStatus.FAILED),
        (ExecutionStatus.RUNNING, ExecutionStatus.FAILED),
    ],
)
@pytest.mark.parametrize(
    "make_component",
    [_step_operator, _orchestrator],
    ids=["step_operator", "isolated_step"],
)
def test_missing_job_uses_finished_step_run_status(
    make_component: Callable[
        [], Union[KubernetesStepOperator, KubernetesOrchestrator]
    ],
    db_status: ExecutionStatus,
    expected_status: ExecutionStatus,
) -> None:
    """Test that only a finished step run keeps its status without a job.

    An unfinished step run can't finish without its job, so waiting for it
    would never end.
    """
    status = _get_status_without_job(
        make_component(), jobs=[], db_status=db_status
    )

    assert status == expected_status


def test_isolated_step_uses_step_run_status_if_job_is_deleted_after_listing() -> (
    None
):
    """Test that a job deleted between listing and reading it is handled."""
    listed_job = k8s_client.V1Job(
        metadata=k8s_client.V1ObjectMeta(name="job-a")
    )
    status = _get_status_without_job(
        _orchestrator(), jobs=[listed_job], db_status=ExecutionStatus.COMPLETED
    )

    assert status == ExecutionStatus.COMPLETED
