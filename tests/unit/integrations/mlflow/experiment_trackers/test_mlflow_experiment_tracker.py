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

import os
from contextlib import ExitStack as does_not_raise

import pytest
from pydantic import ValidationError

from zenml.artifact_stores import LocalArtifactStore
from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.integrations.gcp.artifact_stores import GCPArtifactStore
from zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker import (
    DATABRICKS_HOST,
    DATABRICKS_PASSWORD,
    DATABRICKS_TOKEN,
    DATABRICKS_USERNAME,
    MLFLOW_TRACKING_INSECURE_TLS,
    MLFLOW_TRACKING_PASSWORD,
    MLFLOW_TRACKING_TOKEN,
    MLFLOW_TRACKING_USERNAME,
    MLFlowExperimentTracker,
)
from zenml.metadata_stores import SQLiteMetadataStore
from zenml.orchestrators import LocalOrchestrator
from zenml.stack import Stack


def test_mlflow_experiment_tracker_attributes() -> None:
    """Tests that the basic attributes of the MLflow experiment tracker are set
    correctly."""
    experiment_tracker = MLFlowExperimentTracker(
        name="",
        tracking_uri="http://localhost:5000",
        tracking_username="john_doe",
        tracking_password="password",
        tracking_token="token1234",
        tracking_insecure_tls=True,
        databricks_host="https://databricks.com",
    )

    assert experiment_tracker.TYPE == StackComponentType.EXPERIMENT_TRACKER
    assert experiment_tracker.FLAVOR == "mlflow"


def test_mlflow_experiment_tracker_stack_validation() -> None:
    """Tests that the MLflow experiment tracker validates that it's stack has a
    `LocalArtifactStore` if no tracking URI is set."""
    experiment_tracker = MLFlowExperimentTracker(name="")

    local_orchestrator = LocalOrchestrator(name="")
    local_metadata_store = SQLiteMetadataStore(name="", uri="./metadata.db")
    local_artifact_store = LocalArtifactStore(name="")
    remote_artifact_store = GCPArtifactStore(name="", path="gs://my-bucket")

    with pytest.raises(StackValidationError):
        Stack(
            name="",
            orchestrator=local_orchestrator,
            metadata_store=local_metadata_store,
            artifact_store=remote_artifact_store,
            experiment_tracker=experiment_tracker,
        ).validate()

    with does_not_raise():
        Stack(
            name="",
            orchestrator=local_orchestrator,
            metadata_store=local_metadata_store,
            artifact_store=local_artifact_store,
            experiment_tracker=experiment_tracker,
        ).validate()


def test_mlflow_experiment_tracker_authentication() -> None:
    """Tests that the MLflow experiment tracker validates the authentication
    parameters."""

    # should raise because no authentication parameters are set
    with pytest.raises(ValidationError):
        MLFlowExperimentTracker(
            name="",
            tracking_uri="http://localhost:5000",
        )

    # should raise because no authentication parameters are set
    with pytest.raises(ValidationError):
        MLFlowExperimentTracker(
            name="",
            tracking_uri="databricks",
        )

    # should not raise because username and password are set
    with does_not_raise():
        MLFlowExperimentTracker(
            name="",
            tracking_uri="http://localhost:5000",
            tracking_username="john_doe",
            tracking_password="password",
        )

    with does_not_raise():
        MLFlowExperimentTracker(
            name="",
            tracking_uri="databricks",
            tracking_username="john_doe",
            tracking_password="password",
            databricks_host="https://databricks.com",
        )

    # should not raise because token is set
    with does_not_raise():
        MLFlowExperimentTracker(
            name="",
            tracking_uri="http://localhost:5000",
            tracking_token="token1234",
        )

    with does_not_raise():
        MLFlowExperimentTracker(
            name="",
            tracking_uri="databricks",
            tracking_token="token1234",
            databricks_host="https://databricks.com",
        )


def test_mlflow_experiment_tracker_set_config() -> None:
    """Tests that the MLflow experiment tracker sets the MLflow configuration
    correctly."""
    stack = Stack.default_local_stack()
    stack._experiment_tracker = MLFlowExperimentTracker(
        name="",
        tracking_uri="http://localhost:5000",
        tracking_username="john_doe",
        tracking_password="password",
        tracking_token="token1234",
        tracking_insecure_tls=True,
    )

    stack._experiment_tracker.configure_mlflow()

    assert os.environ[MLFLOW_TRACKING_USERNAME] == "john_doe"
    assert os.environ[MLFLOW_TRACKING_PASSWORD] == "password"
    assert os.environ[MLFLOW_TRACKING_TOKEN] == "token1234"
    assert os.environ[MLFLOW_TRACKING_INSECURE_TLS] == "true"

    stack._experiment_tracker = MLFlowExperimentTracker(
        name="",
        tracking_uri="databricks",
        tracking_username="john_doe",
        tracking_password="password",
        tracking_token="token1234",
        databricks_host="https://databricks.com",
    )

    stack._experiment_tracker.configure_mlflow()

    assert os.environ[DATABRICKS_USERNAME] == "john_doe"
    assert os.environ[DATABRICKS_PASSWORD] == "password"
    assert os.environ[DATABRICKS_TOKEN] == "token1234"
    assert os.environ[DATABRICKS_HOST] == "https://databricks.com"
