#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

from mlflow import (  # type: ignore
    ActiveRun,
    get_experiment_by_name,
    search_runs,
    set_experiment,
    start_run,
)

from zenml.logger import get_logger

logger = get_logger(__name__)


def get_or_create_mlflow_run(experiment_name: str, run_name: str) -> ActiveRun:
    """Get or create an MLflow ActiveRun object for the given experiment and
    run name.

    IMPORTANT: this function is not race condition proof. If two or more
    processes call it at the same time and with the same arguments, it could
    lead to a situation where two or more MLflow runs with the same name
    and different IDs are created.

    Args:
        experiment_name: the experiment name under which this runs will
            be tracked. If no MLflow experiment with this name exists, one will
            be created.
        run_name: the name of the MLflow run. If a run with this name
            does not exist, one will be created, otherwise the existing run
            will be reused

    Returns:
        ActiveRun: an active MLflow run object with the specified name
    """
    # Set which experiment is used within mlflow
    logger.debug("Setting the MLflow experiment name to %s", experiment_name)
    set_experiment(experiment_name)
    mlflow_experiment = get_experiment_by_name(experiment_name)

    # TODO [ENG-458]: find a solution to avoid race-conditions while creating
    #   the same MLflow run from parallel steps
    runs = search_runs(
        experiment_ids=[mlflow_experiment.experiment_id],
        filter_string=f'tags.mlflow.runName = "{run_name}"',
        output_format="list",
    )
    if runs:
        run_id = runs[0].info.run_id
        return start_run(
            run_id=run_id, experiment_id=mlflow_experiment.experiment_id
        )
    return start_run(
        run_name=run_name, experiment_id=mlflow_experiment.experiment_id
    )
