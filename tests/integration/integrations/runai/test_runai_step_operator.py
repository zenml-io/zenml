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
import importlib.util
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from zenml.enums import ExecutionStatus, StackComponentType

RUNAI_INSTALLED = importlib.util.find_spec("runai") is not None
pytestmark = pytest.mark.skipif(
    not RUNAI_INSTALLED, reason="runai dependency is not installed."
)


if RUNAI_INSTALLED:
    from zenml.integrations.runai.client.runai_client import (
        RunAIClient,
        RunAIWorkloadNotFoundError,
        WorkloadSubmissionResult,
    )
    from zenml.integrations.runai.flavors.runai_step_operator_flavor import (
        RunAIStepOperatorConfig,
        RunAIStepOperatorSettings,
    )
    from zenml.integrations.runai.step_operators.runai_step_operator import (
        RUNAI_WORKLOAD_ID_METADATA_KEY,
        RUNAI_WORKLOAD_NAME_METADATA_KEY,
        RunAIStepOperator,
    )
else:
    RunAIClient = Any
    RunAIWorkloadNotFoundError = Exception
    WorkloadSubmissionResult = Any
    RunAIStepOperatorConfig = Any
    RunAIStepOperatorSettings = Any
    RUNAI_WORKLOAD_ID_METADATA_KEY = "workload_id"
    RUNAI_WORKLOAD_NAME_METADATA_KEY = "workload_name"
    RunAIStepOperator = Any


def _get_runai_step_operator() -> RunAIStepOperator:
    """Creates a Run:AI step operator for testing."""
    return RunAIStepOperator(
        name="runai",
        id=uuid4(),
        config=RunAIStepOperatorConfig(
            client_id="client-id",
            client_secret="client-secret",
            runai_base_url="https://my-org.run.ai",
            project_name="demo-project",
        ),
        flavor="runai",
        type=StackComponentType.STEP_OPERATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _get_step_run(workload_id: str = "workload-123") -> Any:
    """Creates a mock step run with run metadata."""
    return SimpleNamespace(
        id=uuid4(),
        run_metadata={RUNAI_WORKLOAD_ID_METADATA_KEY: workload_id},
    )


def test_submit_publishes_workload_metadata(mocker: Any) -> None:
    """Tests that submitting a step stores Run:AI workload metadata."""
    operator = _get_runai_step_operator()
    operator._client = mocker.Mock(spec=RunAIClient)
    operator._client.create_training_workload.return_value = (
        WorkloadSubmissionResult(
            workload_id="workload-123",
            workload_name="workload-name",
        )
    )

    mocker.patch.object(
        operator,
        "_resolve_project_and_cluster",
        return_value=("project-id", "cluster-id"),
    )
    mocker.patch.object(
        operator,
        "get_settings",
        return_value=RunAIStepOperatorSettings(),
    )
    publish_step_run_metadata_mock = mocker.patch(
        "zenml.integrations.runai.step_operators.runai_step_operator.publish_step_run_metadata"
    )

    step_run = SimpleNamespace(run_metadata={})
    force_write_logs = mocker.Mock()
    step_run_info = SimpleNamespace(
        pipeline_step_name="trainer",
        pipeline=SimpleNamespace(name="my-pipeline"),
        run_id=uuid4(),
        step_run_id=uuid4(),
        step_run=step_run,
        get_image=lambda key: "my-image:latest",
        force_write_logs=force_write_logs,
    )

    operator.submit(
        info=step_run_info,
        entrypoint_command=[
            "python",
            "-m",
            "zenml.entrypoints.step_entrypoint",
            "--step_name=trainer",
        ],
        environment={"ENV_KEY": "ENV_VALUE"},
    )

    force_write_logs.assert_called_once()
    operator._client.create_training_workload.assert_called_once()

    publish_step_run_metadata_mock.assert_called_once_with(
        step_run_info.step_run_id,
        {
            operator.id: {
                RUNAI_WORKLOAD_ID_METADATA_KEY: "workload-123",
                RUNAI_WORKLOAD_NAME_METADATA_KEY: "workload-name",
            }
        },
    )
    assert (
        step_run.run_metadata[RUNAI_WORKLOAD_ID_METADATA_KEY] == "workload-123"
    )
    assert (
        step_run.run_metadata[RUNAI_WORKLOAD_NAME_METADATA_KEY]
        == "workload-name"
    )


def test_get_status_maps_runai_status(mocker: Any) -> None:
    """Tests that Run:AI status strings are mapped to ZenML statuses."""
    operator = _get_runai_step_operator()
    operator._client = mocker.Mock(spec=RunAIClient)
    operator._client.get_training_workload_status.return_value = "running"

    status = operator.get_status(_get_step_run())

    assert status == ExecutionStatus.RUNNING


def test_get_status_returns_failed_for_missing_status(mocker: Any) -> None:
    """Tests that missing workload statuses are treated as failures."""
    operator = _get_runai_step_operator()
    operator._client = mocker.Mock(spec=RunAIClient)
    operator._client.get_training_workload_status.return_value = None

    status = operator.get_status(_get_step_run())

    assert status == ExecutionStatus.FAILED


def test_get_status_returns_failed_for_workload_not_found(mocker: Any) -> None:
    """Tests that missing workloads are treated as failures."""
    operator = _get_runai_step_operator()
    operator._client = mocker.Mock(spec=RunAIClient)
    operator._client.get_training_workload_status.side_effect = (
        RunAIWorkloadNotFoundError("workload-123")
    )

    status = operator.get_status(_get_step_run())

    assert status == ExecutionStatus.FAILED


def test_cancel_suspends_workload(mocker: Any) -> None:
    """Tests that canceling a step suspends the corresponding workload."""
    operator = _get_runai_step_operator()
    operator._client = mocker.Mock(spec=RunAIClient)
    step_run = _get_step_run("workload-123")

    operator.cancel(step_run)

    operator._client.suspend_training_workload.assert_called_once_with(
        "workload-123"
    )


def test_wait_returns_completed_on_success_status(mocker: Any) -> None:
    """Tests that wait returns COMPLETED when the workload succeeds."""
    operator = _get_runai_step_operator()
    operator._client = mocker.Mock(spec=RunAIClient)
    operator._client.get_training_workload_status.return_value = "succeeded"
    mocker.patch.object(
        operator,
        "get_settings",
        return_value=RunAIStepOperatorSettings(),
    )

    status = operator.wait(_get_step_run())

    assert status == ExecutionStatus.COMPLETED


def test_wait_preserves_failure_cleanup_behavior(mocker: Any) -> None:
    """Tests that wait keeps cleanup behavior when workload fails."""
    operator = _get_runai_step_operator()
    operator._client = mocker.Mock(spec=RunAIClient)
    operator._client.get_training_workload_status.return_value = "failed"
    mocker.patch.object(
        operator,
        "get_settings",
        return_value=RunAIStepOperatorSettings(),
    )
    cleanup_workload_mock = mocker.patch.object(operator, "_cleanup_workload")

    with pytest.raises(
        RuntimeError, match="workload-123 failed with status: failed"
    ):
        operator.wait(_get_step_run())

    cleanup_workload_mock.assert_called_once_with(
        operator._client, "workload-123", "failed with status: failed"
    )


def test_wait_preserves_timeout_cleanup_behavior(mocker: Any) -> None:
    """Tests that wait keeps timeout and cleanup behavior."""
    operator = _get_runai_step_operator()
    operator._client = mocker.Mock(spec=RunAIClient)
    mocker.patch.object(
        operator,
        "get_settings",
        return_value=RunAIStepOperatorSettings(workload_timeout=1),
    )
    mocker.patch(
        "zenml.integrations.runai.step_operators.runai_step_operator.time.time",
        side_effect=[0.0, 2.0],
    )
    cleanup_workload_mock = mocker.patch.object(operator, "_cleanup_workload")

    with pytest.raises(RuntimeError, match="timed out after 1 seconds"):
        operator.wait(_get_step_run())

    cleanup_workload_mock.assert_called_once_with(
        operator._client, "workload-123", "timeout"
    )
