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
from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
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
            tracking_token="token1234",
            tracking_insecure_tls=True,
            databricks_host="https://databricks.com",
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


def test_mlflow_experiment_tracker_authentication() -> None:
    """Tests that the MLflow experiment tracker validates the authentication parameters."""
    # should raise because no authentication parameters are set
    with pytest.raises(ValidationError):
        MLFlowExperimentTracker(
            name="",
            id=uuid4(),
            config=MLFlowExperimentTrackerConfig(
                tracking_uri="http://localhost:5000",
            ),
            flavor="mlflow",
            type=StackComponentType.EXPERIMENT_TRACKER,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )

    # should raise because no authentication parameters are set
    with pytest.raises(ValidationError):
        MLFlowExperimentTracker(
            name="",
            id=uuid4(),
            config=MLFlowExperimentTrackerConfig(
                tracking_uri="databricks",
            ),
            flavor="mlflow",
            type=StackComponentType.EXPERIMENT_TRACKER,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )

    # should not raise because username and password are set
    with does_not_raise():
        MLFlowExperimentTracker(
            name="",
            id=uuid4(),
            config=MLFlowExperimentTrackerConfig(
                tracking_uri="http://localhost:5000",
                tracking_username="john_doe",
                tracking_password="password",
            ),
            flavor="mlflow",
            type=StackComponentType.EXPERIMENT_TRACKER,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )

    with does_not_raise():
        MLFlowExperimentTracker(
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

    # should not raise because token is set
    with does_not_raise():
        MLFlowExperimentTracker(
            name="",
            id=uuid4(),
            config=MLFlowExperimentTrackerConfig(
                tracking_uri="http://localhost:5000",
                tracking_token="token1234",
            ),
            flavor="mlflow",
            type=StackComponentType.EXPERIMENT_TRACKER,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )

    with does_not_raise():
        MLFlowExperimentTracker(
            name="",
            id=uuid4(),
            config=MLFlowExperimentTrackerConfig(
                tracking_uri="databricks",
                tracking_token="token1234",
                databricks_host="https://databricks.com",
            ),
            flavor="mlflow",
            type=StackComponentType.EXPERIMENT_TRACKER,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )


def test_mlflow_experiment_tracker_set_config(local_stack: Stack) -> None:
    """Tests that the MLflow experiment tracker sets the MLflow configuration correctly."""
    local_stack._experiment_tracker = MLFlowExperimentTracker(
        name="",
        id=uuid4(),
        config=MLFlowExperimentTrackerConfig(
            tracking_uri="http://localhost:5000",
            tracking_username="john_doe",
            tracking_password="password",
            tracking_token="token1234",
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
    assert os.environ[MLFLOW_TRACKING_TOKEN] == "token1234"
    assert os.environ[MLFLOW_TRACKING_INSECURE_TLS] == "true"

    local_stack._experiment_tracker = MLFlowExperimentTracker(
        name="",
        id=uuid4(),
        config=MLFlowExperimentTrackerConfig(
            tracking_uri="databricks",
            tracking_username="john_doe",
            tracking_password="password",
            tracking_token="token1234",
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
    assert os.environ[DATABRICKS_TOKEN] == "token1234"
    assert os.environ[DATABRICKS_HOST] == "https://databricks.com"
