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
"""Tests for the Databricks step operator."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from pytest_mock import MockerFixture

from zenml import __version__
from zenml.enums import ExecutionStatus, StackComponentType

DATABRICKS_INSTALLED = importlib.util.find_spec("databricks") is not None
pytestmark = pytest.mark.skipif(
    not DATABRICKS_INSTALLED, reason="databricks dependency is not installed."
)

if DATABRICKS_INSTALLED:
    from databricks.sdk.errors import NotFound
    from databricks.sdk.service.compute import ClusterSpec
    from databricks.sdk.service.jobs import (
        Run,
        RunLifeCycleState,
        RunResultState,
    )

    from zenml.integrations.databricks.flavors.databricks_step_operator_flavor import (
        DatabricksStepOperatorConfig,
        DatabricksStepOperatorSettings,
    )
    from zenml.integrations.databricks.step_operators.databricks_step_operator import (
        DATABRICKS_STEP_JOB_ID_METADATA_KEY,
        DATABRICKS_STEP_RUN_ID_METADATA_KEY,
        DATABRICKS_STEP_RUN_URL_METADATA_KEY,
        DATABRICKS_STEP_WHEEL_DIRECTORY_METADATA_KEY,
        DatabricksStepOperator,
    )
    from zenml.orchestrators.wheel_build_utils import get_wheel_package_name


def _get_databricks_step_operator() -> DatabricksStepOperator:
    """Create a Databricks step operator for testing."""
    return DatabricksStepOperator(
        name="databricks",
        id=uuid4(),
        config=DatabricksStepOperatorConfig(
            host="https://workspace.cloud.databricks.com",
            client_id="client-id",
            client_secret="client-secret",
        ),
        flavor="databricks",
        type=StackComponentType.STEP_OPERATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


@dataclass
class _FakeStepRun:
    """Minimal step run object used by status and cancellation tests."""

    id: UUID = field(default_factory=uuid4)
    run_metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class _SubmittedRunResponse:
    """Minimal Databricks submit response used by submission tests."""

    run_id: int | None


@dataclass
class _SubmittedRunWait:
    """Minimal Databricks wait wrapper returned by jobs.submit."""

    response: _SubmittedRunResponse
    run_id: int | None


@dataclass
class _FakePipeline:
    """Minimal pipeline object needed by step-operator submission."""

    name: str


@dataclass
class _FakeStackModel:
    """Marker stack model for patched Stack.from_model calls."""


@dataclass
class _FakeSnapshot:
    """Minimal snapshot object needed by step-operator submission."""

    id: UUID = field(default_factory=uuid4)
    stack: _FakeStackModel = field(default_factory=_FakeStackModel)


@dataclass
class _FakeDockerSettings:
    """Marker Docker settings for patched requirements calls."""


@dataclass
class _FakeResourceSettings:
    """Minimal resource settings object used for warning logic."""

    empty: bool = True


@dataclass
class _FakeStepConfig:
    """Minimal step configuration object used by submission tests."""

    docker_settings: _FakeDockerSettings = field(
        default_factory=_FakeDockerSettings
    )
    resource_settings: _FakeResourceSettings = field(
        default_factory=_FakeResourceSettings
    )


@dataclass
class _FakeStack:
    """Marker stack for patched requirements calls."""


@dataclass
class _FakeStepRunInfo:
    """Minimal step-run info object used by submission tests."""

    pipeline: _FakePipeline = field(
        default_factory=lambda: _FakePipeline(name="my-pipeline")
    )
    pipeline_step_name: str = "trainer"
    run_name: str = "my-run"
    run_id: UUID = field(default_factory=uuid4)
    snapshot: _FakeSnapshot = field(default_factory=_FakeSnapshot)
    config: _FakeStepConfig = field(default_factory=_FakeStepConfig)
    step_run: _FakeStepRun = field(default_factory=_FakeStepRun)
    step_run_id: UUID = field(default_factory=uuid4)
    force_write_logs: Mock = field(default_factory=Mock)


def _get_step_run(run_id: str = "123") -> _FakeStepRun:
    """Create a mock step run with run metadata."""
    return _FakeStepRun(
        run_metadata={
            DATABRICKS_STEP_RUN_ID_METADATA_KEY: run_id,
            DATABRICKS_STEP_WHEEL_DIRECTORY_METADATA_KEY: (
                "/Workspace/Shared/.zenml/my-pipeline/run-id/steps/step-id"
            ),
        },
    )


def _get_submitted_run(run_id: int | None = 123) -> _SubmittedRunWait:
    """Create a Databricks submit wait wrapper for testing."""
    return _SubmittedRunWait(
        response=_SubmittedRunResponse(run_id=run_id),
        run_id=run_id,
    )


def _get_cluster_spec() -> ClusterSpec:
    """Create a minimal cluster spec for submission tests."""
    return ClusterSpec(
        spark_version="16.4.x-scala2.12",
        node_type_id="Standard_D4s_v5",
        num_workers=1,
    )


def _get_run(
    life_cycle_state: RunLifeCycleState,
    result_state: Optional[RunResultState] = None,
    job_id: int = 456,
    run_id: int = 123,
    run_page_url: str = "https://workspace/jobs/runs/123",
) -> Run:
    """Create a Databricks run object for testing."""
    return Run.from_dict(
        {
            "run_id": run_id,
            "job_id": job_id,
            "run_page_url": run_page_url,
            "state": {
                "life_cycle_state": life_cycle_state.value,
                "result_state": result_state.value if result_state else None,
            },
        }
    )


def test_submit_publishes_run_metadata(mocker: MockerFixture) -> None:
    """Tests that submitting a step stores Databricks run metadata."""
    operator = _get_databricks_step_operator()
    operator._client = mocker.Mock()
    operator._client.jobs.submit.return_value = _get_submitted_run()
    operator._client.jobs.get_run.return_value = _get_run(
        RunLifeCycleState.PENDING
    )

    mocker.patch.object(
        operator,
        "get_settings",
        return_value=DatabricksStepOperatorSettings(),
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.prepare_repository_copy_for_wheel",
        return_value="/tmp/databricks-wheel",
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.create_wheel",
        return_value="/tmp/databricks-wheel/project.whl",
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.upload_wheel_to_workspace",
        return_value="/Workspace/Shared/.zenml/project.whl",
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.collect_requirements",
        return_value=["pandas==2.2.3"],
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.build_databricks_cluster_spec",
        return_value=_get_cluster_spec(),
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.build_access_control_list",
        return_value=None,
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.publish_step_run_metadata"
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.Stack.from_model",
        return_value=_FakeStack(),
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.fileio.rmtree"
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.get_databricks_wheel_source",
        return_value=None,
    )

    step_run_info = _FakeStepRunInfo()
    step_run = step_run_info.step_run

    operator.submit(
        info=step_run_info,
        entrypoint_command=[
            "entrypoint.main",
            "--entrypoint_config_source",
            "zenml.entrypoint",
            "--snapshot_id",
            str(step_run_info.snapshot.id),
        ],
        environment={"ENV_KEY": "ENV_VALUE"},
    )

    step_run_info.force_write_logs.assert_called_once()
    operator._client.jobs.submit.assert_called_once()

    assert step_run.run_metadata[DATABRICKS_STEP_RUN_ID_METADATA_KEY] == "123"
    assert step_run.run_metadata[DATABRICKS_STEP_JOB_ID_METADATA_KEY] == "456"
    assert (
        step_run.run_metadata[DATABRICKS_STEP_RUN_URL_METADATA_KEY]
        == "https://workspace/jobs/runs/123"
    )
    assert (
        step_run.run_metadata[DATABRICKS_STEP_WHEEL_DIRECTORY_METADATA_KEY]
        == f"/Workspace/Shared/.zenml/my-pipeline/"
        f"{step_run_info.run_id}/steps/{step_run_info.step_run_id}"
    )

    submitted_task = operator._client.jobs.submit.call_args.kwargs["tasks"][0]
    assert submitted_task.python_wheel_task.parameters == [
        "--entrypoint_config_source",
        "zenml.entrypoint",
        "--snapshot_id",
        str(step_run_info.snapshot.id),
        "--wheel_package",
        get_wheel_package_name(),
    ]


def test_submit_reuses_existing_databricks_wheel_source(
    mocker: MockerFixture,
) -> None:
    """Tests that nested Databricks execution reuses the installed wheel source."""
    operator = _get_databricks_step_operator()
    operator._client = mocker.Mock()
    operator._client.jobs.submit.return_value = _get_submitted_run()
    operator._client.jobs.get_run.return_value = _get_run(
        RunLifeCycleState.PENDING
    )

    mocker.patch.object(
        operator,
        "get_settings",
        return_value=DatabricksStepOperatorSettings(),
    )
    prepare_repository_copy_for_wheel_mock = mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.prepare_repository_copy_for_wheel",
        return_value="/tmp/databricks-wheel",
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.create_wheel",
        return_value="/tmp/databricks-wheel/project.whl",
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.upload_wheel_to_workspace",
        return_value="/Workspace/Shared/.zenml/project.whl",
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.collect_requirements",
        return_value=["pandas==2.2.3"],
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.build_databricks_cluster_spec",
        return_value=_get_cluster_spec(),
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.build_access_control_list",
        return_value=None,
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.publish_step_run_metadata"
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.Stack.from_model",
        return_value=_FakeStack(),
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.fileio.rmtree"
    )
    mocker.patch(
        "zenml.integrations.databricks.step_operators.databricks_step_operator.get_databricks_wheel_source",
        return_value=("/tmp/installed-wheel-source", "existing-wheel-package"),
    )

    step_run_info = _FakeStepRunInfo()

    operator.submit(
        info=step_run_info,
        entrypoint_command=["entrypoint.main"],
        environment={"ENV_KEY": "ENV_VALUE"},
    )

    prepare_repository_copy_for_wheel_mock.assert_called_once_with(
        package_name="existing-wheel-package",
        package_version=__version__,
        source_root="/tmp/installed-wheel-source",
    )


def test_get_status_maps_databricks_status(mocker: MockerFixture) -> None:
    """Tests that Databricks status values map to ZenML statuses."""
    operator = _get_databricks_step_operator()
    operator._client = mocker.Mock()
    operator._client.jobs.get_run.return_value = _get_run(
        RunLifeCycleState.RUNNING
    )

    status = operator.get_status(_get_step_run())

    assert status == ExecutionStatus.RUNNING


def test_get_status_keeps_waiting_for_retry_running(
    mocker: MockerFixture,
) -> None:
    """Tests that Databricks retry wait does not terminate the step early."""
    operator = _get_databricks_step_operator()
    operator._client = mocker.Mock()
    operator._client.jobs.get_run.return_value = _get_run(
        RunLifeCycleState.WAITING_FOR_RETRY
    )

    status = operator.get_status(_get_step_run())

    assert status == ExecutionStatus.RUNNING


def test_get_status_returns_failed_for_missing_run(
    mocker: MockerFixture,
) -> None:
    """Tests that missing Databricks runs are treated as failures."""
    operator = _get_databricks_step_operator()
    operator._client = mocker.Mock()
    operator._client.jobs.get_run.side_effect = NotFound()

    status = operator.get_status(_get_step_run())

    assert status == ExecutionStatus.FAILED


def test_cancel_cancels_run(mocker: MockerFixture) -> None:
    """Tests that canceling a step cancels the Databricks run."""
    operator = _get_databricks_step_operator()
    operator._client = mocker.Mock()

    operator.cancel(_get_step_run("123"))

    operator._client.jobs.cancel_run.assert_called_once_with(run_id=123)


def test_wait_returns_completed_on_success_status(
    mocker: MockerFixture,
) -> None:
    """Tests that wait returns COMPLETED when the run succeeds."""
    operator = _get_databricks_step_operator()
    operator._client = mocker.Mock()
    operator._client.jobs.get_run.return_value = _get_run(
        RunLifeCycleState.TERMINATED,
        RunResultState.SUCCESS,
    )

    status = operator.wait(_get_step_run())

    assert status == ExecutionStatus.COMPLETED
    operator._client.workspace.delete.assert_called_once_with(
        path="/Workspace/Shared/.zenml/my-pipeline/run-id/steps/step-id",
        recursive=True,
    )
