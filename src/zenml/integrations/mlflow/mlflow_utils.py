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

import os

import mlflow
from mlflow.entities import Run

from zenml.logger import get_logger

logger = get_logger(__name__)

ZENML_TAG_KEY = "zenml"


def local_mlflow_backend() -> str:
    """Gets the local MLflow backend inside the ZenML artifact store.

    Returns:
        The MLflow tracking URI for the local MLflow backend.
    """
    from zenml.client import Client

    client = Client()
    artifact_store = client.active_stack.artifact_store
    local_mlflow_tracking_uri = os.path.join(artifact_store.path, "mlruns")
    if not os.path.exists(local_mlflow_tracking_uri):
        os.makedirs(local_mlflow_tracking_uri)
    return "file:" + local_mlflow_tracking_uri


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
