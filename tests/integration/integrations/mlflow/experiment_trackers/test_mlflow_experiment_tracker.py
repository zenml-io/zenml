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
"""Integration tests for the MLflow experiment tracker."""

import os
from contextlib import ExitStack as does_not_raise
from datetime import datetime
from typing import Any, Dict
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from mlflow.exceptions import MlflowException
from pydantic import ValidationError

from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker import (
    DATABRICKS_AUTH_TYPE,
    DATABRICKS_CLIENT_ID,
    DATABRICKS_CLIENT_SECRET,
    DATABRICKS_HOST,
    DATABRICKS_PASSWORD,
    DATABRICKS_USERNAME,
    LOCAL_MLFLOW_ARTIFACTS_DIRECTORY,
    LOCAL_MLFLOW_BACKEND_FILENAME,
    MLFLOW_ENABLE_DB_SDK,
    MLFLOW_TRACKING_INSECURE_TLS,
    MLFLOW_TRACKING_PASSWORD,
    MLFLOW_TRACKING_USERNAME,
    MLFlowExperimentTracker,
)
from zenml.integrations.mlflow.flavors.mlflow_experiment_tracker_flavor import (
    MLFlowExperimentTrackerConfig,
)
from zenml.stack import Stack


def test_mlflow_experiment_tracker_attributes() -> None:
    """Tests that the basic attributes of the MLflow experiment tracker are set correctly."""
    experiment_tracker = MLFlowExperimentTracker(
        name="",
        id=uuid4(),
        config=MLFlowExperimentTrackerConfig(
            tracking_uri="http://localhost:5000",
            tracking_username="john_doe",
            tracking_password="password",
            tracking_insecure_tls=True,
        ),
        flavor="mlflow",
        type=StackComponentType.EXPERIMENT_TRACKER,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )

    assert experiment_tracker.type == StackComponentType.EXPERIMENT_TRACKER
    assert experiment_tracker.flavor == "mlflow"


def test_mlflow_experiment_tracker_stack_validation(
    local_orchestrator, local_artifact_store, s3_artifact_store
) -> None:
    """Tests that the MLflow experiment tracker validates that its stack has a `LocalArtifactStore` if no tracking URI is set."""
    experiment_tracker = MLFlowExperimentTracker(
        name="",
        id=uuid4(),
        config=MLFlowExperimentTrackerConfig(),
        flavor="mlflow",
        type=StackComponentType.EXPERIMENT_TRACKER,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )

    with pytest.raises(StackValidationError):
        Stack(
            name="",
            orchestrator=local_orchestrator,
            artifact_store=s3_artifact_store,
            experiment_tracker=experiment_tracker,
            id=uuid4(),
        ).validate()

    with does_not_raise():
        Stack(
            name="",
            id=uuid4(),
            orchestrator=local_orchestrator,
            artifact_store=local_artifact_store,
            experiment_tracker=experiment_tracker,
        ).validate()


def _create_mlflow_experiment_tracker(
    config: MLFlowExperimentTrackerConfig,
) -> MLFlowExperimentTracker:
    """Creates an MLflow experiment tracker for validation tests."""
    return MLFlowExperimentTracker(
        name="",
        id=uuid4(),
        config=config,
        flavor="mlflow",
        type=StackComponentType.EXPERIMENT_TRACKER,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.mark.parametrize(
    "config",
    [
        MLFlowExperimentTrackerConfig(
            tracking_uri="http://localhost:5000",
            tracking_username="john_doe",
            tracking_password="password",
        ),
        MLFlowExperimentTrackerConfig(
            tracking_uri="http://localhost:5000",
            tracking_token="token1234",
        ),
        MLFlowExperimentTrackerConfig(
            tracking_uri="databricks",
            tracking_username="john_doe",
            tracking_password="password",
            databricks_host="https://databricks.com",
        ),
        MLFlowExperimentTrackerConfig(
            tracking_uri="databricks",
            tracking_token="token1234",
            databricks_host="https://databricks.com",
        ),
        MLFlowExperimentTrackerConfig(
            tracking_uri="databricks",
            databricks_client_id="client-id",
            databricks_client_secret="client-secret",
            databricks_host="https://databricks.com",
        ),
    ],
)
def test_mlflow_experiment_tracker_authentication_options_are_valid(
    config: MLFlowExperimentTrackerConfig,
) -> None:
    """Tests that each supported MLflow authentication option is valid."""
    with does_not_raise():
        _create_mlflow_experiment_tracker(config)


@pytest.mark.parametrize(
    "config",
    [
        {"tracking_uri": "http://localhost:5000"},
        {
            "tracking_uri": "databricks",
            "databricks_host": "https://databricks.com",
        },
        {
            "tracking_uri": "http://localhost:5000",
            "tracking_username": "john_doe",
            "tracking_password": "password",
            "tracking_token": "token1234",
        },
        {
            "tracking_uri": "databricks",
            "tracking_username": "john_doe",
            "tracking_password": "password",
            "tracking_token": "token1234",
            "databricks_host": "https://databricks.com",
        },
        {
            "tracking_uri": "databricks",
            "tracking_token": "token1234",
            "databricks_client_id": "client-id",
            "databricks_client_secret": "client-secret",
            "databricks_host": "https://databricks.com",
        },
    ],
)
def test_mlflow_experiment_tracker_requires_exactly_one_remote_authentication_method(
    config: Dict[str, str],
) -> None:
    """Tests that remote tracking requires exactly one auth method."""
    with pytest.raises(ValidationError):
        MLFlowExperimentTrackerConfig(**config)


@pytest.mark.parametrize(
    "config",
    [
        {
            "tracking_uri": "http://localhost:5000",
            "tracking_username": "john_doe",
        },
        {
            "tracking_uri": "http://localhost:5000",
            "tracking_password": "password",
        },
        {
            "tracking_uri": "databricks",
            "databricks_client_id": "client-id",
            "databricks_host": "https://databricks.com",
        },
        {
            "tracking_uri": "databricks",
            "databricks_client_secret": "client-secret",
            "databricks_host": "https://databricks.com",
        },
    ],
)
def test_mlflow_experiment_tracker_requires_complete_credential_pairs(
    config: Dict[str, str],
) -> None:
    """Tests that paired authentication credentials are configured together."""
    with pytest.raises(ValidationError):
        MLFlowExperimentTrackerConfig(**config)


@pytest.mark.parametrize(
    "config",
    [
        {
            "tracking_uri": "http://localhost:5000",
            "tracking_token": "token1234",
            "databricks_host": "https://databricks.com",
        },
        {
            "tracking_uri": "http://localhost:5000",
            "tracking_token": "token1234",
            "databricks_client_id": "client-id",
            "databricks_client_secret": "client-secret",
        },
        {
            "tracking_uri": "http://localhost:5000",
            "tracking_token": "token1234",
            "enable_unity_catalog": True,
        },
    ],
)
def test_mlflow_experiment_tracker_rejects_databricks_options_without_databricks_tracking_uri(
    config: Dict[str, Any],
) -> None:
    """Tests that Databricks options require a Databricks tracking URI."""
    with pytest.raises(ValidationError):
        MLFlowExperimentTrackerConfig(**config)


def test_mlflow_experiment_tracker_requires_databricks_host() -> None:
    """Tests that Databricks tracking requires a workspace host."""
    with pytest.raises(ValidationError):
        MLFlowExperimentTrackerConfig(
            tracking_uri="databricks",
            tracking_token="token1234",
        )


def test_mlflow_experiment_tracker_set_config(
    local_stack: Stack, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tests that the MLflow experiment tracker sets the MLflow configuration correctly."""
    for env_var in [
        DATABRICKS_AUTH_TYPE,
        DATABRICKS_CLIENT_ID,
        DATABRICKS_CLIENT_SECRET,
        MLFLOW_ENABLE_DB_SDK,
    ]:
        monkeypatch.delenv(env_var, raising=False)

    local_stack._experiment_tracker = MLFlowExperimentTracker(
        name="",
        id=uuid4(),
        config=MLFlowExperimentTrackerConfig(
            tracking_uri="http://localhost:5000",
            tracking_username="john_doe",
            tracking_password="password",
            tracking_insecure_tls=True,
        ),
        flavor="mlflow",
        type=StackComponentType.EXPERIMENT_TRACKER,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )

    local_stack._experiment_tracker.configure_mlflow()

    assert os.environ[MLFLOW_TRACKING_USERNAME] == "john_doe"
    assert os.environ[MLFLOW_TRACKING_PASSWORD] == "password"
    assert os.environ[MLFLOW_TRACKING_INSECURE_TLS] == "true"

    local_stack._experiment_tracker = MLFlowExperimentTracker(
        name="",
        id=uuid4(),
        config=MLFlowExperimentTrackerConfig(
            tracking_uri="databricks",
            tracking_username="john_doe",
            tracking_password="password",
            databricks_host="https://databricks.com",
        ),
        flavor="mlflow",
        type=StackComponentType.EXPERIMENT_TRACKER,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )

    local_stack._experiment_tracker.configure_mlflow()

    assert os.environ[DATABRICKS_USERNAME] == "john_doe"
    assert os.environ[DATABRICKS_PASSWORD] == "password"
    assert os.environ[DATABRICKS_HOST] == "https://databricks.com"

    local_stack._experiment_tracker = MLFlowExperimentTracker(
        name="",
        id=uuid4(),
        config=MLFlowExperimentTrackerConfig(
            tracking_uri="databricks",
            databricks_client_id="client-id",
            databricks_client_secret="client-secret",
            databricks_host="https://databricks.com",
        ),
        flavor="mlflow",
        type=StackComponentType.EXPERIMENT_TRACKER,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )

    local_stack._experiment_tracker.configure_mlflow()

    assert os.environ[DATABRICKS_HOST] == "https://databricks.com"
    assert os.environ[DATABRICKS_CLIENT_ID] == "client-id"
    assert os.environ[DATABRICKS_CLIENT_SECRET] == "client-secret"
    assert os.environ[DATABRICKS_AUTH_TYPE] == "oauth-m2m"
    assert os.environ[MLFLOW_ENABLE_DB_SDK] == "true"


def test_mlflow_experiment_tracker_uses_sqlite_for_local_backend(
    tmp_path, monkeypatch
) -> None:
    """Tests that the implicit local MLflow backend does not use the file store."""
    import mlflow

    artifact_store = MagicMock()
    artifact_store.path = str(tmp_path)
    stack = MagicMock()
    stack.artifact_store = artifact_store
    client = MagicMock()
    client.active_stack = stack

    monkeypatch.setattr(
        "zenml.integrations.mlflow.experiment_trackers."
        "mlflow_experiment_tracker.Client",
        lambda: client,
    )

    experiment_tracker = MLFlowExperimentTracker(
        name="",
        id=uuid4(),
        config=MLFlowExperimentTrackerConfig(),
        flavor="mlflow",
        type=StackComponentType.EXPERIMENT_TRACKER,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )

    expected_tracking_uri = "sqlite:///" + os.path.abspath(
        str(tmp_path / LOCAL_MLFLOW_BACKEND_FILENAME)
    )
    expected_artifact_path = os.path.abspath(
        str(tmp_path / LOCAL_MLFLOW_ARTIFACTS_DIRECTORY)
    )

    assert experiment_tracker.get_tracking_uri() == expected_tracking_uri
    assert experiment_tracker.local_path == expected_artifact_path

    experiment_tracker.configure_mlflow()
    experiment = experiment_tracker._set_active_experiment("test_pipeline")

    assert mlflow.get_tracking_uri() == expected_tracking_uri
    assert experiment.artifact_location == "file:" + expected_artifact_path

    mlflow.set_tracking_uri("")


@patch("mlflow.start_run")
@patch("mlflow.get_run")
@patch("mlflow.get_experiment_by_name")
@patch("mlflow.set_experiment")
def test_mlflow_experiment_tracker_handles_missing_run(
    mock_set_experiment: MagicMock,
    mock_get_experiment: MagicMock,
    mock_get_run: MagicMock,
    mock_start_run: MagicMock,
) -> None:
    """Tests that the MLflow experiment tracker handles missing runs gracefully.

    This test verifies the fix for issue #4207 where MLflow would crash
    when trying to resume a run that doesn't exist on the server.
    """
    # Setup mocks
    mock_experiment = MagicMock()
    mock_experiment.experiment_id = "test_experiment_id"
    mock_get_experiment.return_value = mock_experiment

    # Simulate a run that doesn't exist on the MLflow server
    mock_get_run.side_effect = MlflowException("RESOURCE_DOES_NOT_EXIST")

    # Create experiment tracker
    tracker = MLFlowExperimentTracker(
        name="test_tracker",
        id=uuid4(),
        config=MLFlowExperimentTrackerConfig(
            tracking_uri="file:///tmp/mlflow",
        ),
        flavor="mlflow",
        type=StackComponentType.EXPERIMENT_TRACKER,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )

    # Create a mock StepRunInfo
    mock_step_info = MagicMock()
    mock_step_info.pipeline.name = "test_pipeline"
    mock_step_info.run_name = "test_run"
    mock_step_info.pipeline_step_name = "test_step"

    # Mock get_run_id to return a stale run_id
    with patch.object(tracker, "get_run_id", return_value="stale_run_id"):
        with patch.object(
            tracker,
            "get_settings",
            return_value=MagicMock(
                experiment_name=None,
                tags={},
                nested=False,
            ),
        ):
            # This should not raise an exception, even though the run doesn't exist
            tracker.prepare_step_run(mock_step_info)

    # Verify that start_run was called with run_id=None (creating a new run)
    mock_start_run.assert_called_once()
    call_kwargs = mock_start_run.call_args[1]
    assert call_kwargs["run_id"] is None, (
        "Expected run_id to be None when run doesn't exist"
    )
    assert call_kwargs["run_name"] == "test_run"
