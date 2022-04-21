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

MLFLOW_ENVIRONMENT_NAME = "mlflow"
MLFLOW_STEP_ENVIRONMENT_NAME = "mlflow_step"


def get_tracking_uri() -> str:
    repo = Repository()
    tracker = repo.active_stack.experiment_tracker
    if tracker is None:
        raise ValueError(
            "Active stack does not have an experiment tracker component."
        )
    if not isinstance(tracker, MLFlowExperimentTracker):
        raise ValueError(
            "Active stack experiment tracker is not of type `mlflow`."
        )
    return tracker.get_tracking_uri()
