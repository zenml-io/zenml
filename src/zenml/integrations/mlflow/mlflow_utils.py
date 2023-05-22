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

from typing import TYPE_CHECKING, Any, Dict, Optional

import mlflow

from zenml.logger import get_logger

if TYPE_CHECKING:
    from mlflow.entities import Experiment, Run

logger = get_logger(__name__)

ZENML_TAG_KEY = "zenml"


def get_local_mlflow_backend() -> str:
    """Gets the local MLflow backend inside the ZenML artifact store.

    Returns:
        The MLflow tracking URI for the local MLflow backend.
    """
    import os

    from zenml.client import Client

    client = Client()
    artifact_store = client.active_stack.artifact_store
    local_mlflow_tracking_uri = os.path.join(artifact_store.path, "mlruns")
    if not os.path.exists(local_mlflow_tracking_uri):
        os.makedirs(local_mlflow_tracking_uri)
    return "file:" + local_mlflow_tracking_uri


def is_zenml_run(run: "Run") -> bool:
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
    import mlflow

    active_run = mlflow.active_run()
    while active_run:
        if is_zenml_run(active_run):
            logger.debug("Stopping mlflow run %s.", active_run.info.run_id)
            mlflow.end_run(status=status)
            active_run = mlflow.active_run()
        else:
            break


def get_internal_tags() -> Dict[str, Any]:
    """Gets ZenML internal tags for MLflow runs.

    Returns:
        Internal tags.
    """
    from zenml import __version__ as zenml_version

    return {ZENML_TAG_KEY: zenml_version}


def is_databricks_tracking_uri(tracking_uri: Optional[str]) -> bool:
    """Checks whether the given tracking uri is a Databricks tracking uri.

    Args:
        tracking_uri: The tracking uri to check.

    Returns:
        `True` if the tracking uri is a Databricks tracking uri, `False`
        otherwise.
    """
    return tracking_uri == "databricks"


def is_remote_mlflow_tracking_uri(tracking_uri: Optional[str]) -> bool:
    """Checks whether the given tracking uri is remote or not.

    Args:
        tracking_uri: The tracking uri to check.

    Returns:
        `True` if the tracking uri is remote, `False` otherwise.
    """
    if not tracking_uri:
        return False
    return any(
        tracking_uri.startswith(prefix) for prefix in ["http://", "https://"]
    ) or is_databricks_tracking_uri(tracking_uri)


def set_active_experiment(
    experiment_name: str, in_databricks: bool
) -> "Experiment":
    """Sets the active MLflow experiment.

    If no experiment with this name exists, it is created and then
    activated.

    Args:
        experiment_name: Name of the experiment to activate.
        in_databricks: Whether the code is running in Databricks or not.

    Raises:
        RuntimeError: If the experiment creation or activation failed.

    Returns:
        The experiment.
    """
    import mlflow

    experiment_name = adjust_experiment_name(experiment_name, in_databricks)

    mlflow.set_experiment(experiment_name=experiment_name)
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if not experiment:
        raise RuntimeError("Failed to set active mlflow experiment.")
    return experiment


def adjust_experiment_name(experiment_name: str, in_databricks: bool) -> str:
    """Prepends a slash to the experiment name if using Databricks.

    Databricks requires the experiment name to be an absolute path within
    the Databricks workspace.

    Args:
        experiment_name: The experiment name.
        in_databricks: Whether the code is running in Databricks or not.

    Returns:
        The potentially adjusted experiment name.
    """
    if in_databricks and not experiment_name.startswith("/"):
        return f"/{experiment_name}"
    else:
        return experiment_name


def end_mlflow_runs(status: str) -> None:
    """Ends all active MLflow runs.

    Args:
        status: The status to end the runs with.
    """
    disable_autologging()
    stop_zenml_mlflow_runs(status)
    mlflow.set_tracking_uri("")


def disable_autologging() -> None:
    """Disables MLflow autologging."""
    from mlflow import (
        fastai,
        gluon,
        lightgbm,
        pytorch,
        sklearn,
        spark,
        statsmodels,
        tensorflow,
        xgboost,
    )

    # There is no way to disable auto-logging for all frameworks at once.
    # If auto-logging is explicitly enabled for a framework by calling its
    # autolog() method, it cannot be disabled by calling
    # `mlflow.autolog(disable=True)`. Therefore, we need to disable
    # auto-logging for all frameworks explicitly.

    tensorflow.autolog(disable=True)
    gluon.autolog(disable=True)
    xgboost.autolog(disable=True)
    lightgbm.autolog(disable=True)
    statsmodels.autolog(disable=True)
    spark.autolog(disable=True)
    sklearn.autolog(disable=True)
    fastai.autolog(disable=True)
    pytorch.autolog(disable=True)
