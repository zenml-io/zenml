#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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


from contextlib import ExitStack as does_not_raise
from datetime import datetime
from typing import List, Optional, Tuple
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from kubernetes import client as k8s_client
from kubernetes.client import ApiException

from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.integrations.kubernetes.constants import (
    ORCHESTRATOR_ANNOTATION_KEY,
    STEP_NAME_ANNOTATION_KEY,
)
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
    KubernetesOrchestratorConfig,
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.orchestrators import KubernetesOrchestrator
from zenml.stack import Stack

K8S_CONTEXT = "kubernetes_context"


def _get_kubernetes_orchestrator(
    local: bool = False, skip_local_validations: bool = False
) -> KubernetesOrchestrator:
    """Helper function to get a Kubernetes orchestrator."""
    return KubernetesOrchestrator(
        name="",
        id=uuid4(),
        config=KubernetesOrchestratorConfig(
            kubernetes_context=K8S_CONTEXT,
            local=local,
            skip_local_validations=skip_local_validations,
        ),
        flavor="kubernetes",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _patch_k8s_clients(mocker):
    """Helper function to patch k8s clients."""

    mock_context = {"name": K8S_CONTEXT}

    def mock_load_kube_config(context: str) -> None:
        mock_context["name"] = context

    def mock_load_incluster_config() -> None:
        mock_context["name"] = "incluster"

    mocker.patch(
        "zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator.KubernetesOrchestrator.get_kube_client",
        return_value=(None),
    )
    mocker.patch(
        "kubernetes.config.load_kube_config",
        side_effect=mock_load_kube_config,
    )
    mocker.patch(
        "kubernetes.config.load_incluster_config",
        side_effect=mock_load_incluster_config,
    )

    mocker.patch(
        "kubernetes.config.list_kube_config_contexts",
        return_value=([mock_context], mock_context),
    )

    mocker.patch("kubernetes.client.CoreV1Api")
    mocker.patch("kubernetes.client.BatchV1Api")
    mocker.patch("kubernetes.client.RbacAuthorizationV1Api")


def test_kubernetes_orchestrator_remote_stack(
    mocker, s3_artifact_store, remote_container_registry
) -> None:
    """Test the remote and local kubernetes orchestrator with remote stacks."""
    _patch_k8s_clients(mocker)

    # Test remote stack with remote orchestrator
    orchestrator = _get_kubernetes_orchestrator()
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=s3_artifact_store,
            container_registry=remote_container_registry,
        ).validate()

    # Test remote stack with local orchestrator
    orchestrator = _get_kubernetes_orchestrator(local=True)
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=s3_artifact_store,
            container_registry=remote_container_registry,
        ).validate()
    orchestrator = _get_kubernetes_orchestrator(
        local=True, skip_local_validations=True
    )
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=s3_artifact_store,
            container_registry=remote_container_registry,
        ).validate()


def test_kubernetes_orchestrator_local_stack(
    mocker, local_artifact_store, local_container_registry
) -> None:
    """Test the remote and local kubernetes orchestrator with remote stacks."""
    _patch_k8s_clients(mocker)

    # Test missing container registry
    orchestrator = _get_kubernetes_orchestrator(local=True)
    with pytest.raises(StackValidationError):
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
        ).validate()

    # Test local stack with remote orchestrator
    orchestrator = _get_kubernetes_orchestrator()
    with pytest.raises(StackValidationError):
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
            container_registry=local_container_registry,
        ).validate()
    orchestrator = _get_kubernetes_orchestrator(skip_local_validations=True)
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
            container_registry=local_container_registry,
        ).validate()

    # Test local stack with local orchestrator
    orchestrator = _get_kubernetes_orchestrator(local=True)
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
            container_registry=local_container_registry,
        ).validate()


def test_kubernetes_orchestrator_uses_service_account_from_settings(mocker):
    """Test that the service account from the settings is used."""
    _patch_k8s_clients(mocker)
    orchestrator = _get_kubernetes_orchestrator(local=True)
    service_account_name = "aria-service-account"
    settings = KubernetesOrchestratorSettings(
        service_account_name=service_account_name
    )
    assert (
        orchestrator._get_service_account_name(settings)
        == service_account_name
    )


@pytest.mark.parametrize(
    "input_value,expected",
    [
        ("Allow", "Allow"),
        ("Forbid", "Forbid"),
        ("Replace", "Replace"),
        ("allow", "Allow"),
        ("forbid", "Forbid"),
        ("REPLACE", "Replace"),
        ("  Forbid  ", "Forbid"),
        (None, None),
    ],
)
def test_concurrency_policy_validation_accepts_valid_values(
    input_value, expected
):
    """Test that concurrency_policy validator normalizes valid values."""
    settings = KubernetesOrchestratorSettings(concurrency_policy=input_value)
    assert settings.concurrency_policy == expected


@pytest.mark.parametrize(
    "input_value",
    ["Invalid", "never", "always", ""],
)
def test_concurrency_policy_validation_rejects_invalid_values(input_value):
    """Test that concurrency_policy validator rejects invalid values."""
    with pytest.raises(Exception):
        KubernetesOrchestratorSettings(concurrency_policy=input_value)


ORCHESTRATOR_MODULE = (
    "zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator"
)


def _job(
    name: str, is_orchestrator: bool = False, finished: bool = False
) -> k8s_client.V1Job:
    """Creates a job as returned by the Kubernetes API."""
    annotations = (
        {ORCHESTRATOR_ANNOTATION_KEY: "orchestrator-id"}
        if is_orchestrator
        else {STEP_NAME_ANNOTATION_KEY: name}
    )
    conditions = (
        [k8s_client.V1JobCondition(type="Complete", status="True")]
        if finished
        else None
    )
    return k8s_client.V1Job(
        metadata=k8s_client.V1ObjectMeta(name=name, annotations=annotations),
        status=k8s_client.V1JobStatus(conditions=conditions),
    )


def _stop_run_immediately(
    mocker,
    is_dynamic: bool = True,
    root_run_id: Optional[str] = None,
    delete_error: Optional[Exception] = None,
) -> List[Tuple[str, str]]:
    """Stops a run immediately and records what happened, in order.

    The run has a running orchestrator job, a running step job and a finished
    step job.

    Returns:
        The deleted jobs, finalized runs and a failed stop as
        `("delete", <job name>)`, `("finalize", <run>)` and `("error", <run>)`
        tuples.
    """
    _patch_k8s_clients(mocker)
    orchestrator = _get_kubernetes_orchestrator()
    mocker.patch.object(
        orchestrator,
        "get_settings",
        return_value=KubernetesOrchestratorSettings(),
    )
    mocker.patch(f"{ORCHESTRATOR_MODULE}.depaginate", return_value=[])
    mocker.patch(
        f"{ORCHESTRATOR_MODULE}.kube_utils.list_jobs",
        return_value=k8s_client.V1JobList(
            items=[
                _job("orchestrator", is_orchestrator=True),
                _job("running-step"),
                _job("finished-step", finished=True),
            ]
        ),
    )
    actions: List[Tuple[str, str]] = []

    def _delete_job(**kwargs: str) -> None:
        if delete_error:
            raise delete_error
        actions.append(("delete", kwargs["job_name"]))

    mocker.patch(
        f"{ORCHESTRATOR_MODULE}.kube_utils.delete_job", side_effect=_delete_job
    )
    mocker.patch(
        f"{ORCHESTRATOR_MODULE}.publish_stopped_pipeline_run",
        side_effect=lambda run: actions.append(("finalize", run.name)),
    )

    run = MagicMock(root_run_id=root_run_id)
    run.name = "run"
    run.snapshot.is_dynamic = is_dynamic
    try:
        orchestrator._stop_run(run=run, graceful=False)
    except RuntimeError:
        actions.append(("error", "run"))
    return actions


def test_immediate_stop_deletes_dynamic_orchestrator_first(mocker):
    """Tests the order of an immediate stop of a dynamic run."""
    assert _stop_run_immediately(mocker, is_dynamic=True) == [
        ("delete", "orchestrator"),
        ("delete", "running-step"),
        ("finalize", "run"),
        ("delete", "running-step"),
    ]


def test_immediate_stop_keeps_static_orchestrator(mocker):
    """Tests that the orchestrator of static runs is left to stop itself."""
    assert _stop_run_immediately(mocker, is_dynamic=False) == [
        ("delete", "running-step"),
        ("finalize", "run"),
        ("delete", "running-step"),
    ]


def test_immediate_stop_of_child_run_keeps_shared_orchestrator(mocker):
    """Tests that stopping a child run doesn't stop its root run."""
    assert _stop_run_immediately(
        mocker, is_dynamic=True, root_run_id=str(uuid4())
    ) == [("delete", "running-step")]


def test_failed_immediate_stop_skips_finalization(mocker):
    """Tests that runs are not marked stopped if jobs might still run."""
    assert _stop_run_immediately(
        mocker,
        is_dynamic=False,
        delete_error=ApiException(status=500, reason="Error"),
    ) == [("error", "run")]


def test_graceful_stop_leaves_jobs_alone(mocker):
    """Tests that a graceful stop is left to the orchestrator pod."""
    _patch_k8s_clients(mocker)
    orchestrator = _get_kubernetes_orchestrator()
    list_jobs = mocker.patch(f"{ORCHESTRATOR_MODULE}.kube_utils.list_jobs")

    orchestrator._stop_run(run=MagicMock(), graceful=True)

    list_jobs.assert_not_called()
