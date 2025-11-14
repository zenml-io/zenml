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
"""Implementation of utils specific to the MLflow integration."""

import mlflow
from mlflow.entities import Run
from packaging import version

from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)

ZENML_TAG_KEY = "zenml"


def is_mlflow_3x() -> bool:
    """Check if MLflow version is 3.x or higher.

    Returns:
        True if MLflow version is 3.x or higher, False otherwise.
    """
    return version.parse(mlflow.version.VERSION) >= version.parse("3.0.0")


def get_model_uri_from_version(
    mlflow_model_version: "mlflow.entities.model_registry.ModelVersion",
) -> str:
    """Get the model URI from an MLflow model version.

    This function handles the differences between MLflow 2.x and 3.x:
    - In MLflow 3.x, models are stored separately and we construct a runs:/ URI
    - In MLflow 2.x, we use the source path directly

    Args:
        mlflow_model_version: The MLflow model version object.

    Returns:
        The model URI that can be used to load the model.
    """
    if is_mlflow_3x() and mlflow_model_version.run_id:
        source_path = mlflow_model_version.source
        if source_path and "/artifacts/" in source_path:
            artifact_name = source_path.split("/artifacts/")[-1]
            return f"runs:/{mlflow_model_version.run_id}/{artifact_name}"
        return source_path or ""
    return mlflow_model_version.source or ""


def build_runs_uri(run_id: str, artifact_path: str) -> str:
    """Build a runs:/ URI from a run ID and artifact path.

    Args:
        run_id: The MLflow run ID.
        artifact_path: The artifact path (e.g., "model").

    Returns:
        The constructed URI.
    """
    return f"runs:/{run_id}/{artifact_path}"


def get_missing_mlflow_experiment_tracker_error() -> ValueError:
    """Returns description of how to add an MLflow experiment tracker to your stack.

    Returns:
        ValueError: If no MLflow experiment tracker is registered in the active stack.
    """
    return ValueError(
        "The active stack needs to have a MLflow experiment tracker "
        "component registered to be able to track experiments using "
        "MLflow. You can create a new stack with a MLflow experiment "
        "tracker component or update your existing stack to add this "
        "component, e.g.:\n\n"
        "  'zenml experiment-tracker register mlflow_tracker "
        "--type=mlflow'\n"
        "  'zenml stack register stack-name -e mlflow_tracker ...'\n"
    )


def get_tracking_uri() -> str:
    """Gets the MLflow tracking URI from the active experiment tracking stack component.

    # noqa: DAR401

    Returns:
        MLflow tracking URI.
    """
    from zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker import (
        MLFlowExperimentTracker,
    )

    tracker = Client().active_stack.experiment_tracker
    if tracker is None or not isinstance(tracker, MLFlowExperimentTracker):
        raise get_missing_mlflow_experiment_tracker_error()

    return tracker.get_tracking_uri()


def is_zenml_run(run: Run) -> bool:
    """Checks if a MLflow run is a ZenML run or not.

    Args:
        run: The run to check.

    Returns:
        If the run is a ZenML run.
    """
    return ZENML_TAG_KEY in run.data.tags


def stop_zenml_mlflow_runs(status: str) -> None:
    """Stops active ZenML Mlflow runs.

    This function stops all MLflow active runs until no active run exists or
    a non-ZenML run is active.

    Args:
        status: The status to set the run to.
    """
    active_run = mlflow.active_run()
    while active_run:
        if is_zenml_run(active_run):
            logger.debug("Stopping mlflow run %s.", active_run.info.run_id)
            mlflow.end_run(status=status)
            active_run = mlflow.active_run()
        else:
            break
