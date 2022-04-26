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

from mlflow import (  # type: ignore[import]
    ActiveRun,
    get_experiment_by_name,
    search_runs,
    set_experiment,
    set_tracking_uri,
    start_run,
)
from mlflow.entities import Experiment  # type: ignore[import]

from zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker import (
    MLFlowExperimentTracker,
)
from zenml.logger import get_logger
from zenml.repository import Repository

logger = get_logger(__name__)


def get_missing_mlflow_experiment_tracker_error() -> ValueError:
    """Returns a detailed error that describes how to add an MLflow experiment
    tracker component to your stack."""
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
    """Gets the MLflow tracking URI from the active experiment tracking stack
    component.

    Returns:
        MLflow tracking URI.

    Raises:
        ValueError: If the active stack contains no MLflow experiment tracking
            component.
    """
    tracker = Repository().active_stack.experiment_tracker
    if tracker is None or not isinstance(tracker, MLFlowExperimentTracker):
        raise get_missing_mlflow_experiment_tracker_error()

    return tracker.get_tracking_uri()
